from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import RLock
from typing import Literal

from backend.knowact.runtime.checkpoint import (
    EpisodeRunCheckpointInvalidError,
    EpisodeRunCheckpointMissingError,
    EpisodeRunCheckpointRepository,
)
from backend.knowact.runtime.episode_repository import (
    RuntimeEpisodeArtifactError,
    RuntimeEpisodeNotFoundError,
    RuntimeEpisodeRepository,
)
from backend.knowact.runtime.execution_repository import (
    MAX_RUN_QUEUE_CONCURRENCY,
    EpisodeExecutionNotFoundError,
    EpisodeExecutionRecord,
    EpisodeExecutionRepository,
    EpisodeExecutionStatus,
    EpisodeExecutionTransitionError,
    EpisodeRunQueueState,
)
from backend.knowact.runtime.runner import (
    EpisodeRunCancelledError,
    EpisodeRunner,
    LegacyEpisodeExecutionConfigurationError,
)


EpisodeEnqueueAction = Literal["start_or_resume", "restart"]


@dataclass(frozen=True)
class EpisodeEnqueueSelection:
    episode_id: str
    action: EpisodeEnqueueAction = "start_or_resume"


@dataclass(frozen=True)
class EpisodeEnqueueOutcome:
    episode_id: str
    accepted: bool
    status: EpisodeExecutionStatus
    run_id: str | None
    error_code: str | None = None
    message: str | None = None


class EpisodeRunQueueScheduler:
    """Persist and dispatch independent Episode Runs inside one process."""

    def __init__(
        self,
        *,
        episode_repository: RuntimeEpisodeRepository,
        execution_repository: EpisodeExecutionRepository,
        checkpoint_repository: EpisodeRunCheckpointRepository,
        runner: EpisodeRunner,
    ) -> None:
        self._episode_repository = episode_repository
        self._execution_repository = execution_repository
        self._checkpoint_repository = checkpoint_repository
        self._runner = runner
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_RUN_QUEUE_CONCURRENCY,
            thread_name_prefix="knowact-episode",
        )
        self._lock = RLock()
        self._active: dict[str, Future[None]] = {}
        self._started = False
        self._stopped = False

    def start(self) -> None:
        with self._lock:
            if self._started or self._stopped:
                return
            manifests = tuple(
                record.manifest for record in self._episode_repository.list_episodes()
            )
            self._execution_repository.initialize(manifests)
            self._execution_repository.reconcile_startup()
            self._started = True
            self._schedule_locked()

    def stop(self) -> None:
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
        self._executor.shutdown(wait=False, cancel_futures=False)

    def snapshot(self) -> EpisodeRunQueueState:
        self.start()
        return self._execution_repository.snapshot()

    def set_concurrency(self, concurrency: int) -> EpisodeRunQueueState:
        self.start()
        state = self._execution_repository.set_concurrency(concurrency)
        with self._lock:
            self._schedule_locked()
        return state

    def enqueue(
        self,
        selections: tuple[EpisodeEnqueueSelection, ...],
    ) -> tuple[EpisodeEnqueueOutcome, ...]:
        self.start()
        with self._lock:
            outcomes = tuple(self._admit(selection) for selection in selections)
            self._schedule_locked()
        return outcomes

    def cancel(self, episode_id: str) -> EpisodeExecutionRecord:
        self.start()
        with self._lock:
            record = self._execution_repository.cancel(episode_id)
            self._schedule_locked()
        return record

    def _admit(self, selection: EpisodeEnqueueSelection) -> EpisodeEnqueueOutcome:
        episode_id = selection.episode_id
        try:
            manifest = self._episode_repository.read_episode_manifest(episode_id)
            configuration = manifest.execution_configuration()
            if configuration is None:
                raise LegacyEpisodeExecutionConfigurationError(
                    f"Episode {episode_id} has no execution configuration"
                )
            record = self._execution_repository.record(episode_id)
            if selection.action == "restart":
                if (
                    record.status != EpisodeExecutionStatus.FAILED
                    or record.checkpoint_health not in {"missing", "invalid"}
                ):
                    raise EpisodeExecutionTransitionError(
                        f"Episode {episode_id} does not require restart"
                    )
                prepared = self._runner.prepare_registered_episode(
                    episode_id=episode_id
                )
                record = self._execution_repository.restart_and_enqueue(
                    episode_id=episode_id,
                    run_id=prepared.run_id,
                )
            elif record.status == EpisodeExecutionStatus.READY:
                prepared = self._runner.prepare_registered_episode(
                    episode_id=episode_id
                )
                record = self._execution_repository.enqueue(
                    episode_id=episode_id,
                    run_id=prepared.run_id,
                )
            else:
                if record.run_id is None:
                    raise EpisodeRunCheckpointMissingError(
                        "Resumable episode has no run id"
                    )
                checkpoint = self._checkpoint_repository.read_validated(
                    run_id=record.run_id,
                    episode_id=episode_id,
                    execution_configuration=configuration,
                )
                record = self._execution_repository.enqueue(
                    episode_id=episode_id,
                    run_id=record.run_id,
                    completed_turns=checkpoint.completed_turns,
                )
            return EpisodeEnqueueOutcome(
                episode_id=episode_id,
                accepted=True,
                status=record.status,
                run_id=record.run_id,
            )
        except EpisodeRunCheckpointMissingError:
            self._mark_checkpoint_invalid(episode_id, health="missing")
            return self._rejected(
                episode_id,
                "checkpoint_invalid",
                "The saved checkpoint is missing. Select restart to create a new run id.",
            )
        except EpisodeRunCheckpointInvalidError:
            self._mark_checkpoint_invalid(episode_id, health="invalid")
            return self._rejected(
                episode_id,
                "checkpoint_invalid",
                "The saved checkpoint is invalid. Select restart to create a new run id.",
            )
        except LegacyEpisodeExecutionConfigurationError as exc:
            return self._rejected(
                episode_id,
                "execution_configuration_missing",
                str(exc),
            )
        except RuntimeEpisodeNotFoundError as exc:
            return EpisodeEnqueueOutcome(
                episode_id=episode_id,
                accepted=False,
                status=EpisodeExecutionStatus.FAILED,
                run_id=None,
                error_code="episode_not_found",
                message=str(exc),
            )
        except OSError:
            return self._rejected(
                episode_id,
                "episode_preparation_failed",
                "The Episode Run could not be prepared. No queue state was changed.",
            )
        except (
            RuntimeEpisodeArtifactError,
            EpisodeExecutionNotFoundError,
            EpisodeExecutionTransitionError,
            ValueError,
        ) as exc:
            return self._rejected(
                episode_id,
                "episode_not_eligible",
                str(exc),
            )

    def _mark_checkpoint_invalid(
        self,
        episode_id: str,
        *,
        health: Literal["missing", "invalid"],
    ) -> None:
        try:
            self._execution_repository.set_checkpoint_invalid(
                episode_id,
                health=health,
            )
        except EpisodeExecutionNotFoundError:
            pass

    def _rejected(
        self,
        episode_id: str,
        error_code: str,
        message: str,
    ) -> EpisodeEnqueueOutcome:
        try:
            record = self._execution_repository.record(episode_id)
            status = record.status
            run_id = record.run_id
        except EpisodeExecutionNotFoundError:
            status = EpisodeExecutionStatus.FAILED
            run_id = None
        return EpisodeEnqueueOutcome(
            episode_id=episode_id,
            accepted=False,
            status=status,
            run_id=run_id,
            error_code=error_code,
            message=message,
        )

    def _schedule_locked(self) -> None:
        if not self._started or self._stopped:
            return
        self._active = {
            episode_id: future
            for episode_id, future in self._active.items()
            if not future.done()
        }
        concurrency = self._execution_repository.snapshot().concurrency
        while len(self._active) < concurrency:
            queued = self._execution_repository.next_queued()
            if queued is None or queued.run_id is None:
                return
            self._execution_repository.mark_running(queued.episode_id)
            try:
                future = self._executor.submit(
                    self._run_episode,
                    queued.episode_id,
                    queued.run_id,
                )
            except RuntimeError:
                self._execution_repository.mark_failed(
                    queued.episode_id,
                    code="scheduler_dispatch_failed",
                    message="The Episode Run could not be dispatched. Re-enqueue it to resume.",
                    checkpoint_health="valid",
                )
                continue
            self._active[queued.episode_id] = future
            future.add_done_callback(
                lambda completed, episode_id=queued.episode_id: self._worker_finished(
                    episode_id
                )
            )

    def _run_episode(self, episode_id: str, run_id: str) -> None:
        try:
            result = self._runner.resume_registered_episode(
                episode_id=episode_id,
                run_id=run_id,
                should_cancel=lambda: self._execution_repository.is_cancel_requested(
                    episode_id
                ),
                progress_callback=lambda completed_turns: self._execution_repository.update_progress(
                    episode_id,
                    completed_turns,
                ),
            )
            self._execution_repository.mark_completed(
                episode_id,
                result.turn_count,
            )
        except EpisodeRunCancelledError as exc:
            self._execution_repository.mark_cancelled(
                episode_id,
                exc.completed_turns,
            )
        except EpisodeRunCheckpointMissingError:
            self._execution_repository.set_checkpoint_invalid(
                episode_id,
                health="missing",
            )
        except EpisodeRunCheckpointInvalidError:
            self._execution_repository.set_checkpoint_invalid(
                episode_id,
                health="invalid",
            )
        except Exception as exc:
            self._execution_repository.mark_failed(
                episode_id,
                code=_safe_error_code(exc),
                message=_safe_error_message(exc),
                checkpoint_health="valid",
            )

    def _worker_finished(self, episode_id: str) -> None:
        with self._lock:
            self._active.pop(episode_id, None)
            self._schedule_locked()


def _safe_error_code(exc: Exception) -> str:
    name = type(exc).__name__
    if name.endswith("ConfigurationError"):
        return "runtime_service_not_configured"
    if name.endswith("ModelClientError"):
        return "runtime_model_error"
    return "episode_run_failed"


def _safe_error_message(exc: Exception) -> str:
    code = _safe_error_code(exc)
    if code == "runtime_service_not_configured":
        return "A configured runtime provider is unavailable."
    if code == "runtime_model_error":
        return "A model provider request failed. Re-enqueue the episode to resume."
    return "The Episode Run failed. Re-enqueue it to resume from its checkpoint."
