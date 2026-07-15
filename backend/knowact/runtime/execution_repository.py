from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
import json
from pathlib import Path
from threading import RLock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.knowact.core.episode import EvaluationEpisodeManifest


RUN_QUEUE_STATE_VERSION = 1
DEFAULT_RUN_QUEUE_CONCURRENCY = 3
MIN_RUN_QUEUE_CONCURRENCY = 3
MAX_RUN_QUEUE_CONCURRENCY = 8


class EpisodeExecutionStatus(StrEnum):
    READY = "ready"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


CheckpointHealth = Literal["not_applicable", "valid", "missing", "invalid"]


class EpisodeExecutionFailure(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str


class EpisodeExecutionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    status: EpisodeExecutionStatus = EpisodeExecutionStatus.READY
    max_turns: int = Field(gt=0)
    completed_turns: int = Field(default=0, ge=0)
    run_id: str | None = None
    prior_run_ids: tuple[str, ...] = ()
    queue_order: int | None = Field(default=None, ge=1)
    checkpoint_health: CheckpointHealth = "not_applicable"
    cancel_requested: bool = False
    failure: EpisodeExecutionFailure | None = None
    enqueued_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class EpisodeRunQueueState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = RUN_QUEUE_STATE_VERSION
    concurrency: int = Field(
        default=DEFAULT_RUN_QUEUE_CONCURRENCY,
        ge=MIN_RUN_QUEUE_CONCURRENCY,
        le=MAX_RUN_QUEUE_CONCURRENCY,
    )
    next_queue_order: int = Field(default=1, ge=1)
    episodes: dict[str, EpisodeExecutionRecord] = Field(default_factory=dict)


class EpisodeExecutionRepositoryError(ValueError):
    """Raised when persisted Episode Run Queue state is unusable."""


class EpisodeExecutionTransitionError(EpisodeExecutionRepositoryError):
    """Raised when a requested episode status transition is not legal."""


class EpisodeExecutionNotFoundError(EpisodeExecutionRepositoryError):
    """Raised when queue state has no current-schema episode record."""


class EpisodeExecutionRepository:
    def __init__(self, *, workspace_root: Path) -> None:
        self._path = workspace_root / "experiments" / "runtime" / "run_queue.json"
        self._lock = RLock()

    def initialize(self, manifests: tuple[EvaluationEpisodeManifest, ...]) -> None:
        with self._lock:
            state = self._load()
            episodes = dict(state.episodes)
            changed = False
            for manifest in manifests:
                if manifest.is_legacy or manifest.episode_id in episodes:
                    continue
                episodes[manifest.episode_id] = EpisodeExecutionRecord(
                    episode_id=manifest.episode_id,
                    max_turns=manifest.max_turns,
                )
                changed = True
            if changed or not self._path.exists():
                self._write(state.model_copy(update={"episodes": episodes}))

    def snapshot(self) -> EpisodeRunQueueState:
        with self._lock:
            return self._load()

    def record(self, episode_id: str) -> EpisodeExecutionRecord:
        state = self.snapshot()
        try:
            return state.episodes[episode_id]
        except KeyError as exc:
            raise EpisodeExecutionNotFoundError(
                f"Episode {episode_id} has no execution state"
            ) from exc

    def set_concurrency(self, concurrency: int) -> EpisodeRunQueueState:
        if not MIN_RUN_QUEUE_CONCURRENCY <= concurrency <= MAX_RUN_QUEUE_CONCURRENCY:
            raise EpisodeExecutionRepositoryError(
                f"Queue concurrency must be between {MIN_RUN_QUEUE_CONCURRENCY} and {MAX_RUN_QUEUE_CONCURRENCY}"
            )
        with self._lock:
            state = self._load().model_copy(update={"concurrency": concurrency})
            self._write(state)
            return state

    def enqueue(
        self,
        *,
        episode_id: str,
        run_id: str,
        completed_turns: int | None = None,
    ) -> EpisodeExecutionRecord:
        with self._lock:
            state = self._load()
            current = _record(state, episode_id)
            if current.status not in {
                EpisodeExecutionStatus.READY,
                EpisodeExecutionStatus.FAILED,
                EpisodeExecutionStatus.CANCELLED,
            }:
                raise EpisodeExecutionTransitionError(
                    f"Episode {episode_id} cannot be enqueued from {current.status.value}"
                )
            record = current.model_copy(
                update={
                    "status": EpisodeExecutionStatus.QUEUED,
                    "run_id": run_id,
                    "completed_turns": (
                        current.completed_turns
                        if completed_turns is None
                        else completed_turns
                    ),
                    "queue_order": state.next_queue_order,
                    "checkpoint_health": "valid",
                    "cancel_requested": False,
                    "failure": None,
                    "enqueued_at": _timestamp(),
                    "started_at": None,
                    "finished_at": None,
                }
            )
            self._replace(
                state,
                record,
                next_queue_order=state.next_queue_order + 1,
            )
            return record

    def restart_and_enqueue(
        self,
        *,
        episode_id: str,
        run_id: str,
    ) -> EpisodeExecutionRecord:
        with self._lock:
            state = self._load()
            current = _record(state, episode_id)
            if current.status != EpisodeExecutionStatus.FAILED:
                raise EpisodeExecutionTransitionError(
                    f"Episode {episode_id} can restart only from failed"
                )
            if current.checkpoint_health not in {"missing", "invalid"}:
                raise EpisodeExecutionTransitionError(
                    f"Episode {episode_id} does not require restart"
                )
            prior_run_ids = current.prior_run_ids
            if current.run_id is not None:
                prior_run_ids = (*prior_run_ids, current.run_id)
            record = current.model_copy(
                update={
                    "status": EpisodeExecutionStatus.QUEUED,
                    "run_id": run_id,
                    "prior_run_ids": prior_run_ids,
                    "completed_turns": 0,
                    "queue_order": state.next_queue_order,
                    "checkpoint_health": "valid",
                    "cancel_requested": False,
                    "failure": None,
                    "enqueued_at": _timestamp(),
                    "started_at": None,
                    "finished_at": None,
                }
            )
            self._replace(
                state,
                record,
                next_queue_order=state.next_queue_order + 1,
            )
            return record

    def mark_running(self, episode_id: str) -> EpisodeExecutionRecord:
        return self._transition(
            episode_id,
            allowed={EpisodeExecutionStatus.QUEUED},
            update={
                "status": EpisodeExecutionStatus.RUNNING,
                "queue_order": None,
                "started_at": _timestamp(),
            },
        )

    def update_progress(self, episode_id: str, completed_turns: int) -> None:
        with self._lock:
            state = self._load()
            current = _record(state, episode_id)
            if current.status != EpisodeExecutionStatus.RUNNING:
                return
            self._replace(
                state,
                current.model_copy(update={"completed_turns": completed_turns}),
            )

    def mark_completed(self, episode_id: str, completed_turns: int) -> None:
        self._transition(
            episode_id,
            allowed={EpisodeExecutionStatus.RUNNING},
            update={
                "status": EpisodeExecutionStatus.COMPLETED,
                "completed_turns": completed_turns,
                "checkpoint_health": "not_applicable",
                "cancel_requested": False,
                "failure": None,
                "finished_at": _timestamp(),
            },
        )

    def mark_failed(
        self,
        episode_id: str,
        *,
        code: str,
        message: str,
        checkpoint_health: CheckpointHealth = "valid",
    ) -> None:
        with self._lock:
            state = self._load()
            current = _record(state, episode_id)
            self._replace(
                state,
                current.model_copy(
                    update={
                        "status": EpisodeExecutionStatus.FAILED,
                        "queue_order": None,
                        "checkpoint_health": checkpoint_health,
                        "cancel_requested": False,
                        "failure": EpisodeExecutionFailure(
                            code=code,
                            message=message,
                        ),
                        "finished_at": _timestamp(),
                    }
                ),
            )

    def cancel(self, episode_id: str) -> EpisodeExecutionRecord:
        with self._lock:
            state = self._load()
            current = _record(state, episode_id)
            if current.status == EpisodeExecutionStatus.QUEUED:
                record = current.model_copy(
                    update={
                        "status": EpisodeExecutionStatus.CANCELLED,
                        "queue_order": None,
                        "cancel_requested": False,
                        "finished_at": _timestamp(),
                    }
                )
            elif current.status == EpisodeExecutionStatus.RUNNING:
                record = current.model_copy(update={"cancel_requested": True})
            else:
                raise EpisodeExecutionTransitionError(
                    f"Episode {episode_id} cannot be cancelled from {current.status.value}"
                )
            self._replace(state, record)
            return record

    def mark_cancelled(self, episode_id: str, completed_turns: int) -> None:
        self._transition(
            episode_id,
            allowed={EpisodeExecutionStatus.RUNNING},
            update={
                "status": EpisodeExecutionStatus.CANCELLED,
                "completed_turns": completed_turns,
                "cancel_requested": False,
                "failure": None,
                "finished_at": _timestamp(),
            },
        )

    def is_cancel_requested(self, episode_id: str) -> bool:
        try:
            return self.record(episode_id).cancel_requested
        except EpisodeExecutionNotFoundError:
            return False

    def next_queued(self) -> EpisodeExecutionRecord | None:
        queued = [
            record
            for record in self.snapshot().episodes.values()
            if record.status == EpisodeExecutionStatus.QUEUED
        ]
        return min(queued, key=lambda item: item.queue_order or 0, default=None)

    def reconcile_startup(self) -> None:
        with self._lock:
            state = self._load()
            episodes = dict(state.episodes)
            changed = False
            for episode_id, record in episodes.items():
                if record.status != EpisodeExecutionStatus.RUNNING:
                    continue
                episodes[episode_id] = record.model_copy(
                    update={
                        "status": EpisodeExecutionStatus.FAILED,
                        "cancel_requested": False,
                        "failure": EpisodeExecutionFailure(
                            code="backend_restarted",
                            message="The backend stopped while this episode was running. Re-enqueue it to resume from its checkpoint.",
                        ),
                        "finished_at": _timestamp(),
                    }
                )
                changed = True
            if changed:
                self._write(state.model_copy(update={"episodes": episodes}))

    def set_checkpoint_invalid(
        self,
        episode_id: str,
        *,
        health: Literal["missing", "invalid"],
    ) -> None:
        self.mark_failed(
            episode_id,
            code="checkpoint_invalid",
            message="The saved checkpoint is missing or invalid. Select restart to create a new run id.",
            checkpoint_health=health,
        )

    def _transition(
        self,
        episode_id: str,
        *,
        allowed: set[EpisodeExecutionStatus],
        update: dict[str, object],
    ) -> EpisodeExecutionRecord:
        with self._lock:
            state = self._load()
            current = _record(state, episode_id)
            if current.status not in allowed:
                raise EpisodeExecutionTransitionError(
                    f"Episode {episode_id} cannot transition from {current.status.value}"
                )
            record = current.model_copy(update=update)
            self._replace(state, record)
            return record

    def _replace(
        self,
        state: EpisodeRunQueueState,
        record: EpisodeExecutionRecord,
        *,
        next_queue_order: int | None = None,
    ) -> None:
        episodes = dict(state.episodes)
        episodes[record.episode_id] = record
        update: dict[str, object] = {"episodes": episodes}
        if next_queue_order is not None:
            update["next_queue_order"] = next_queue_order
        self._write(state.model_copy(update=update))

    def _load(self) -> EpisodeRunQueueState:
        if not self._path.exists():
            return EpisodeRunQueueState()
        try:
            with self._path.open(encoding="utf-8") as handle:
                return EpisodeRunQueueState.model_validate(json.load(handle))
        except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise EpisodeExecutionRepositoryError(
                "Episode Run Queue state is malformed"
            ) from exc

    def _write(self, state: EpisodeRunQueueState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with temporary_path.open("w", encoding="utf-8") as handle:
                json.dump(
                    state.model_dump(mode="json", exclude_none=True),
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
                handle.write("\n")
            temporary_path.replace(self._path)
        except OSError as exc:
            raise EpisodeExecutionRepositoryError(
                "Episode Run Queue state could not be written"
            ) from exc


def _record(state: EpisodeRunQueueState, episode_id: str) -> EpisodeExecutionRecord:
    try:
        return state.episodes[episode_id]
    except KeyError as exc:
        raise EpisodeExecutionNotFoundError(
            f"Episode {episode_id} has no execution state"
        ) from exc


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
