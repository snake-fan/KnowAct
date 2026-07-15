from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import json
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.knowact.agents.agents.simple_llm import SimpleLLMTestedAgent
from backend.knowact.agents.llm_agent import build_simple_llm_tested_agent_for_provider
from backend.knowact.agents.protocol import (
    AskDiagnosticQuestionDecision,
    DecisionPhase,
    DecisionPhaseContext,
    TestedAgent,
    TestedAgentDecision,
)
from backend.knowact.agents.providers import (
    DEFAULT_TESTED_AGENT_CLIENT_PROVIDER,
    TestedAgentClientProvider,
)
from backend.knowact.agents.tools import (
    FinalizedReconstruction,
    finalize_reconstructed_map,
    update_node_assessments,
)
from backend.knowact.agents.working_map import (
    AgentWorkingKnowledgeMap,
    initialize_working_map,
)
from backend.knowact.core.episode import EpisodeExecutionConfiguration
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import VisibleDialogueContext
from backend.knowact.core.scoring import EpisodeScoreReport
from backend.knowact.llm.config import deepseek_config_from_env, openai_config_from_env
from backend.knowact.runtime.checkpoint import (
    EpisodeRunCheckpoint,
    EpisodeRunCheckpointRepository,
    advanced_checkpoint,
)
from backend.knowact.runtime.episode_options import (
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_OPENAI_MODEL,
)
from backend.knowact.runtime.episode_repository import (
    RuntimeEpisodeBinding,
    RuntimeEpisodeRepository,
)
from backend.knowact.runtime.transcript import append_visible_turn, next_turn_id
from backend.knowact.scoring.compare import score_final_reconstruction
from backend.knowact.simulator.llm_service import build_simulator_service_for_provider
from backend.knowact.simulator.providers import (
    DEFAULT_SIMULATOR_CLIENT_PROVIDER,
    SimulatorClientProvider,
)
from backend.knowact.simulator.service import SimulatorService
from backend.knowact.simulator.turn import SimulatorTurnOptions, SimulatorTurnRequest


_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class EpisodeRunAgentKind(StrEnum):
    SIMPLE_LLM_AGENT = "simple_llm_agent"


class EpisodeRunAlreadyExistsError(FileExistsError):
    """Raised when an Episode Run would overwrite an existing run directory."""


class EpisodeRunIdError(ValueError):
    """Raised when an Episode Run id is unsafe for artifact storage."""


class UnsupportedEpisodeRunAgentKindError(ValueError):
    """Raised when the runner cannot construct the selected tested agent."""


class LegacyEpisodeExecutionConfigurationError(ValueError):
    """Raised when formal execution targets a legacy episode manifest."""


class EpisodeRunCancelledError(RuntimeError):
    """Raised after cooperative cancellation reaches a checkpoint boundary."""

    def __init__(self, *, completed_turns: int) -> None:
        super().__init__("Episode Run cancelled at a completed-turn checkpoint")
        self.completed_turns = completed_turns


class EpisodeRunArtifactError(ValueError):
    """Raised when a completed Episode Run artifact cannot be read."""


class EpisodeRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    agent_kind: EpisodeRunAgentKind = EpisodeRunAgentKind.SIMPLE_LLM_AGENT
    run_id: str | None = None
    tested_agent_client_provider: TestedAgentClientProvider = (
        DEFAULT_TESTED_AGENT_CLIENT_PROVIDER
    )
    tested_agent_model: str | None = None
    simulator_client_provider: SimulatorClientProvider = (
        DEFAULT_SIMULATOR_CLIENT_PROVIDER
    )
    simulator_model: str | None = None
    tested_agent_temperature: float | None = Field(default=None, ge=0.0)
    max_tool_retries: int = Field(default=3, ge=1)

    @field_validator("episode_id")
    @classmethod
    def _episode_id_must_be_safe(cls, value: str) -> str:
        return _validate_safe_id(value, "episode_id")

    @field_validator("run_id")
    @classmethod
    def _run_id_must_be_safe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_safe_id(value, "run_id")

    @field_validator("tested_agent_model", "simulator_model")
    @classmethod
    def _optional_model_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


@dataclass(frozen=True)
class EpisodeRunArtifacts:
    run_dir: Path
    episode_manifest_snapshot_path: Path
    checkpoint_path: Path
    turns_dir: Path
    transcript_path: Path
    working_map_path: Path
    agent_tool_trace_path: Path
    agent_output_path: Path
    scoring_report_path: Path


@dataclass(frozen=True)
class PreparedEpisodeRun:
    run_id: str
    episode_id: str
    artifacts: EpisodeRunArtifacts


@dataclass(frozen=True)
class EpisodeRunResult:
    run_id: str
    episode_id: str
    agent_kind: EpisodeRunAgentKind
    turn_count: int
    forced_finalization: bool
    forced_finalization_fallback: bool
    artifacts: EpisodeRunArtifacts
    scoring_report: EpisodeScoreReport


TestedAgentFactory = Callable[[EpisodeRunRequest], TestedAgent]
SimulatorServiceFactory = Callable[[SimulatorClientProvider, Path], SimulatorService]
CancellationCheck = Callable[[], bool]
ProgressCallback = Callable[[int], None]


class EpisodeRunner:
    """Run registered Evaluation Episodes with turn-level resumable state."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        tested_agent_factory: TestedAgentFactory | None = None,
        simulator_service_factory: SimulatorServiceFactory | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._episode_repository = RuntimeEpisodeRepository(
            workspace_root=workspace_root
        )
        self._checkpoint_repository = EpisodeRunCheckpointRepository(
            workspace_root=workspace_root
        )
        self._tested_agent_factory = tested_agent_factory
        self._simulator_service_factory = simulator_service_factory

    def prepare_registered_episode(
        self,
        *,
        episode_id: str,
        run_id: str | None = None,
    ) -> PreparedEpisodeRun:
        binding = self._episode_repository.load_episode_binding(episode_id)
        configuration = binding.manifest.execution_configuration()
        if configuration is None:
            raise LegacyEpisodeExecutionConfigurationError(
                f"Episode {episode_id} has no execution configuration"
            )
        return self._prepare(
            binding=binding,
            configuration=configuration,
            run_id=run_id or default_episode_run_id(),
        )

    def resume_registered_episode(
        self,
        *,
        episode_id: str,
        run_id: str,
        should_cancel: CancellationCheck | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> EpisodeRunResult:
        binding = self._episode_repository.load_episode_binding(episode_id)
        configuration = binding.manifest.execution_configuration()
        if configuration is None:
            raise LegacyEpisodeExecutionConfigurationError(
                f"Episode {episode_id} has no execution configuration"
            )
        checkpoint = self._checkpoint_repository.read_validated(
            run_id=run_id,
            episode_id=episode_id,
            execution_configuration=configuration,
        )
        return self._execute(
            binding=binding,
            checkpoint=checkpoint,
            should_cancel=should_cancel or (lambda: False),
            progress_callback=progress_callback or (lambda completed_turns: None),
        )

    def run_episode(self, request: EpisodeRunRequest) -> EpisodeRunResult:
        """Compatibility entry for direct runner tests and development code."""

        binding = self._episode_repository.load_episode_binding(request.episode_id)
        configuration = binding.manifest.execution_configuration() or _request_configuration(
            request
        )
        prepared = self._prepare(
            binding=binding,
            configuration=configuration,
            run_id=request.run_id or default_episode_run_id(),
        )
        checkpoint = self._checkpoint_repository.read_validated(
            run_id=prepared.run_id,
            episode_id=request.episode_id,
            execution_configuration=configuration,
        )
        return self._execute(
            binding=binding,
            checkpoint=checkpoint,
            should_cancel=lambda: False,
            progress_callback=lambda completed_turns: None,
        )

    def _prepare(
        self,
        *,
        binding: RuntimeEpisodeBinding,
        configuration: EpisodeExecutionConfiguration,
        run_id: str,
    ) -> PreparedEpisodeRun:
        _ensure_run_dir_available(self._workspace_root, run_id)
        manifest = binding.manifest
        graph = binding.reviewed_graph.graph
        run_dir = _prepare_run_dir(self._workspace_root, run_id)
        artifacts = _artifact_paths(run_dir)
        artifacts.turns_dir.mkdir()
        _write_json(artifacts.episode_manifest_snapshot_path, manifest)
        working_map = initialize_working_map(
            episode_id=manifest.episode_id,
            benchmark_domain=manifest.benchmark_domain,
            graph_version=manifest.graph_version,
            graph=graph,
        )
        _write_json(artifacts.working_map_path, working_map)
        checkpoint = self._checkpoint_repository.initial_checkpoint(
            run_id=run_id,
            episode_id=manifest.episode_id,
            execution_configuration=configuration,
            working_map=working_map,
            max_turns=manifest.max_turns,
        )
        self._checkpoint_repository.write(checkpoint)
        return PreparedEpisodeRun(
            run_id=run_id,
            episode_id=manifest.episode_id,
            artifacts=artifacts,
        )

    def _execute(
        self,
        *,
        binding: RuntimeEpisodeBinding,
        checkpoint: EpisodeRunCheckpoint,
        should_cancel: CancellationCheck,
        progress_callback: ProgressCallback,
    ) -> EpisodeRunResult:
        manifest = binding.manifest
        graph = binding.reviewed_graph.graph
        hidden_map = binding.hidden_map.knowledge_map
        configuration = checkpoint.execution_configuration
        request = _request_from_configuration(
            episode_id=manifest.episode_id,
            run_id=checkpoint.run_id,
            configuration=configuration,
        )
        artifacts = _artifact_paths(
            _run_dir_path(self._workspace_root, checkpoint.run_id)
        )
        if should_cancel():
            raise EpisodeRunCancelledError(
                completed_turns=checkpoint.completed_turns
            )
        agent = (
            self._tested_agent_factory(request)
            if self._tested_agent_factory is not None
            else _build_tested_agent(request)
        )
        simulator_service = (
            self._simulator_service_factory(
                request.simulator_client_provider,
                self._workspace_root,
            )
            if self._simulator_service_factory is not None
            else _build_simulator_service(
                request.simulator_client_provider,
                request.simulator_model,
                self._workspace_root,
            )
        )

        visible_dialogue_context = checkpoint.visible_dialogue_context
        working_map = checkpoint.working_map
        trace = list(checkpoint.trace)
        remaining_turns = checkpoint.remaining_turns
        phase = checkpoint.phase
        final_decision: TestedAgentDecision | None = None
        finalized: FinalizedReconstruction | None = None
        forced_finalization = False
        forced_finalization_fallback = False

        while finalized is None:
            if should_cancel():
                raise EpisodeRunCancelledError(
                    completed_turns=checkpoint.completed_turns
                )
            decision_context = DecisionPhaseContext(
                phase=phase,
                remaining_diagnostic_turns=remaining_turns,
            )
            decision = agent.decide_next_action(
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=decision_context,
            )
            final_decision = decision
            trace.append(
                {
                    "event": "tested_agent_decision",
                    "phase": decision_context.phase.value,
                    "remaining_diagnostic_turns": remaining_turns,
                    "status": "accepted",
                    "decision": _model_payload(decision),
                }
            )
            if should_cancel():
                raise EpisodeRunCancelledError(
                    completed_turns=checkpoint.completed_turns
                )

            if not isinstance(decision, AskDiagnosticQuestionDecision):
                forced_finalization = phase == DecisionPhase.FORCED_FINALIZATION
                finalized = finalize_reconstructed_map(
                    working_map=working_map,
                    graph=graph,
                    visible_dialogue_context=visible_dialogue_context,
                )
                break

            if phase == DecisionPhase.FORCED_FINALIZATION or remaining_turns <= 0:
                forced_finalization = True
                forced_finalization_fallback = True
                trace.append(
                    {
                        "event": "tested_agent_decision",
                        "phase": decision_context.phase.value,
                        "remaining_diagnostic_turns": remaining_turns,
                        "status": "rejected",
                        "error": "Diagnostic questions are not allowed during forced finalization.",
                        "decision": _model_payload(decision),
                    }
                )
                finalized = finalize_reconstructed_map(
                    working_map=working_map,
                    graph=graph,
                    visible_dialogue_context=visible_dialogue_context,
                )
                break

            turn_id = next_turn_id(visible_dialogue_context)
            simulator_response = simulator_service.answer_turn(
                SimulatorTurnRequest(
                    benchmark_domain=manifest.benchmark_domain,
                    map_id=manifest.hidden_map_id,
                    client_provider=request.simulator_client_provider,
                    question=decision.question,
                    visible_dialogue_context=visible_dialogue_context,
                    turn_options=SimulatorTurnOptions(include_debug_trace=False),
                )
            )
            visible_dialogue_context = append_visible_turn(
                visible_dialogue_context=visible_dialogue_context,
                question=decision.question,
                answer=simulator_response.answer,
                observation=simulator_response.observation,
                turn_id=turn_id,
            )
            trace.append(
                {
                    "event": "interaction_turn",
                    "turn_id": turn_id,
                    "status": "recorded",
                    "question": _model_payload(decision.question),
                    "answer": _model_payload(simulator_response.answer),
                    "observation": _model_payload(simulator_response.observation),
                    "warnings": [
                        _model_payload(warning)
                        for warning in simulator_response.warnings
                    ],
                }
            )
            remaining_turns -= 1
            phase = (
                DecisionPhase.AFTER_ANSWER
                if remaining_turns > 0
                else DecisionPhase.FORCED_FINALIZATION
            )
            update_context = DecisionPhaseContext(
                phase=phase,
                remaining_diagnostic_turns=remaining_turns,
            )
            working_map, update_events = _apply_working_map_updates(
                agent=agent,
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=update_context,
                max_tool_retries=request.max_tool_retries,
            )
            trace.extend(update_events)
            completed_dialogue_turn = visible_dialogue_context.turns[-1]
            _write_json(
                artifacts.turns_dir / f"{completed_dialogue_turn.turn_id}.json",
                {
                    "turn_id": completed_dialogue_turn.turn_id,
                    "dialogue": completed_dialogue_turn,
                    "working_map_update_events": update_events,
                },
            )
            _write_json(artifacts.working_map_path, working_map)
            checkpoint = advanced_checkpoint(
                checkpoint,
                visible_dialogue_context=visible_dialogue_context,
                working_map=working_map,
                phase=phase,
                remaining_turns=remaining_turns,
                trace=trace,
            )
            self._checkpoint_repository.write(checkpoint)
            progress_callback(checkpoint.completed_turns)
            if should_cancel():
                raise EpisodeRunCancelledError(
                    completed_turns=checkpoint.completed_turns
                )

        scoring_report = score_final_reconstruction(
            graph=graph,
            ground_truth_map=hidden_map,
            submission=finalized.submission,
            scoring_profile=manifest.scoring_profile,
        )
        _write_json(artifacts.transcript_path, visible_dialogue_context)
        _write_json(artifacts.working_map_path, working_map)
        _write_json(
            artifacts.agent_tool_trace_path,
            {
                "run_id": checkpoint.run_id,
                "episode_id": manifest.episode_id,
                "agent_kind": request.agent_kind.value,
                "max_tool_retries": request.max_tool_retries,
                "events": trace,
            },
        )
        _write_json(
            artifacts.agent_output_path,
            {
                "run_id": checkpoint.run_id,
                "episode_id": manifest.episode_id,
                "agent_kind": request.agent_kind.value,
                "tested_agent_client_provider": request.tested_agent_client_provider,
                "tested_agent_model": request.tested_agent_model,
                "simulator_client_provider": request.simulator_client_provider,
                "simulator_model": request.simulator_model,
                "final_decision": _model_payload(final_decision),
                "forced_finalization": forced_finalization,
                "forced_finalization_fallback": forced_finalization_fallback,
                "finalization_warnings": [
                    _model_payload(warning) for warning in finalized.warnings
                ],
                "final_reconstruction_submission": finalized.submission,
                "final_reconstructed_knowledge_map": finalized.knowledge_map,
            },
        )
        _write_json(artifacts.scoring_report_path, scoring_report)
        self._checkpoint_repository.delete(checkpoint.run_id)
        return EpisodeRunResult(
            run_id=checkpoint.run_id,
            episode_id=manifest.episode_id,
            agent_kind=request.agent_kind,
            turn_count=len(visible_dialogue_context.turns),
            forced_finalization=forced_finalization,
            forced_finalization_fallback=forced_finalization_fallback,
            artifacts=artifacts,
            scoring_report=scoring_report,
        )


def load_completed_episode_run(
    *,
    workspace_root: Path,
    run_id: str,
) -> EpisodeRunResult:
    artifacts = _artifact_paths(_run_dir_path(workspace_root, run_id))
    try:
        manifest_payload = _read_json(artifacts.episode_manifest_snapshot_path)
        agent_output = _read_json(artifacts.agent_output_path)
        scoring_report = EpisodeScoreReport.model_validate(
            _read_json(artifacts.scoring_report_path)
        )
        transcript = VisibleDialogueContext.model_validate(
            _read_json(artifacts.transcript_path)
        )
        return EpisodeRunResult(
            run_id=run_id,
            episode_id=str(manifest_payload["episode_id"]),
            agent_kind=EpisodeRunAgentKind(agent_output["agent_kind"]),
            turn_count=len(transcript.turns),
            forced_finalization=bool(agent_output["forced_finalization"]),
            forced_finalization_fallback=bool(
                agent_output["forced_finalization_fallback"]
            ),
            artifacts=artifacts,
            scoring_report=scoring_report,
        )
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        ValidationError,
    ) as exc:
        raise EpisodeRunArtifactError(
            f"Completed Episode Run {run_id} artifacts are malformed"
        ) from exc


def default_episode_run_id() -> str:
    return "run_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _apply_working_map_updates(
    *,
    agent: TestedAgent,
    graph: KnowledgeGraph,
    working_map: AgentWorkingKnowledgeMap,
    visible_dialogue_context: VisibleDialogueContext,
    decision_context: DecisionPhaseContext,
    max_tool_retries: int,
) -> tuple[AgentWorkingKnowledgeMap, list[dict[str, Any]]]:
    update_events: list[dict[str, Any]] = []
    for attempt_index in range(1, max_tool_retries + 1):
        try:
            updates = agent.update_after_visible_answer(
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=decision_context,
            )
            updated_working_map = update_node_assessments(
                working_map=working_map,
                graph=graph,
                visible_dialogue_context=visible_dialogue_context,
                updates=updates,
            )
        except Exception as exc:
            update_events.append(
                {
                    "event": "working_map_update",
                    "phase": decision_context.phase.value,
                    "attempt_index": attempt_index,
                    "status": "rejected",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue
        update_events.append(
            {
                "event": "working_map_update",
                "phase": decision_context.phase.value,
                "attempt_index": attempt_index,
                "status": "accepted",
                "updates": [_model_payload(update) for update in updates],
            }
        )
        return updated_working_map, update_events
    update_events.append(
        {
            "event": "working_map_update",
            "phase": decision_context.phase.value,
            "status": "tool_retry_exhausted",
            "tool_retry_exhausted": True,
            "max_tool_retries": max_tool_retries,
        }
    )
    return working_map, update_events


def _request_configuration(request: EpisodeRunRequest) -> EpisodeExecutionConfiguration:
    return EpisodeExecutionConfiguration(
        agent_kind=request.agent_kind.value,
        tested_agent_client_provider=request.tested_agent_client_provider,
        tested_agent_model=request.tested_agent_model
        or _default_model(request.tested_agent_client_provider),
        simulator_client_provider=request.simulator_client_provider,
        simulator_model=request.simulator_model
        or _default_model(request.simulator_client_provider),
        tested_agent_temperature=(
            request.tested_agent_temperature
            if request.tested_agent_temperature is not None
            else 0.0
        ),
        max_tool_retries=request.max_tool_retries,
    )


def _request_from_configuration(
    *,
    episode_id: str,
    run_id: str,
    configuration: EpisodeExecutionConfiguration,
) -> EpisodeRunRequest:
    return EpisodeRunRequest(
        episode_id=episode_id,
        run_id=run_id,
        agent_kind=configuration.agent_kind,
        tested_agent_client_provider=configuration.tested_agent_client_provider,
        tested_agent_model=configuration.tested_agent_model,
        simulator_client_provider=configuration.simulator_client_provider,
        simulator_model=configuration.simulator_model,
        tested_agent_temperature=configuration.tested_agent_temperature,
        max_tool_retries=configuration.max_tool_retries,
    )


def _default_model(provider: str) -> str:
    return DEFAULT_OPENAI_MODEL if provider == "openai" else DEFAULT_DEEPSEEK_MODEL


def _build_tested_agent(request: EpisodeRunRequest) -> SimpleLLMTestedAgent:
    if request.agent_kind != EpisodeRunAgentKind.SIMPLE_LLM_AGENT:
        raise UnsupportedEpisodeRunAgentKindError(
            f"Unsupported tested agent kind: {request.agent_kind}"
        )
    if request.tested_agent_client_provider == "openai":
        config = openai_config_from_env()
        if request.tested_agent_model is not None:
            config = config.model_copy(update={"model": request.tested_agent_model})
        return build_simple_llm_tested_agent_for_provider(
            client_provider="openai",
            temperature=request.tested_agent_temperature,
            openai_config=config,
        )
    config = deepseek_config_from_env()
    if request.tested_agent_model is not None:
        config = config.model_copy(update={"model": request.tested_agent_model})
    return build_simple_llm_tested_agent_for_provider(
        client_provider="deepseek",
        temperature=request.tested_agent_temperature,
        deepseek_config=config,
    )


def _build_simulator_service(
    client_provider: SimulatorClientProvider,
    model: str | None,
    workspace_root: Path,
) -> SimulatorService:
    if client_provider == "openai":
        config = openai_config_from_env()
        if model is not None:
            config = config.model_copy(update={"model": model})
        return build_simulator_service_for_provider(
            workspace_root=workspace_root,
            client_provider="openai",
            openai_config=config,
        )
    config = deepseek_config_from_env()
    if model is not None:
        config = config.model_copy(update={"model": model})
    return build_simulator_service_for_provider(
        workspace_root=workspace_root,
        client_provider="deepseek",
        deepseek_config=config,
    )


def _prepare_run_dir(workspace_root: Path, run_id: str) -> Path:
    run_dir = _run_dir_path(workspace_root, run_id)
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise EpisodeRunAlreadyExistsError(
            f"Episode Run {run_id} already exists"
        ) from exc
    return run_dir


def _ensure_run_dir_available(workspace_root: Path, run_id: str) -> None:
    if _run_dir_path(workspace_root, run_id).exists():
        raise EpisodeRunAlreadyExistsError(f"Episode Run {run_id} already exists")


def _run_dir_path(workspace_root: Path, run_id: str) -> Path:
    return workspace_root / "experiments" / "runs" / _validate_safe_id(
        run_id, "run_id"
    )


def _artifact_paths(run_dir: Path) -> EpisodeRunArtifacts:
    return EpisodeRunArtifacts(
        run_dir=run_dir,
        episode_manifest_snapshot_path=run_dir / "episode_manifest_snapshot.json",
        checkpoint_path=run_dir / "checkpoint.json",
        turns_dir=run_dir / "turns",
        transcript_path=run_dir / "transcript.json",
        working_map_path=run_dir / "working_map.json",
        agent_tool_trace_path=run_dir / "agent_tool_trace.json",
        agent_output_path=run_dir / "agent_output.json",
        scoring_report_path=run_dir / "scoring_report.json",
    )


def _write_json(path: Path, payload: Any) -> None:
    temporary_path = path.with_name(f".{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(_json_payload(payload), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temporary_path.replace(path)


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _json_payload(payload: Any) -> Any:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json", exclude_none=True)
    if isinstance(payload, StrEnum):
        return payload.value
    if isinstance(payload, Path):
        return str(payload)
    if isinstance(payload, dict):
        return {key: _json_payload(value) for key, value in payload.items()}
    if isinstance(payload, tuple | list):
        return [_json_payload(item) for item in payload]
    return payload


def _model_payload(model: Any) -> Any:
    return _json_payload(model)


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise EpisodeRunIdError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise EpisodeRunIdError(
            f"{field_name} must contain only letters, numbers, dots, underscores, or dashes"
        )
    return value
