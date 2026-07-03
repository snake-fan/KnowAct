from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import json
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import VisibleDialogueContext
from backend.knowact.core.scoring import EpisodeScoreReport
from backend.knowact.runtime.episode_repository import RuntimeEpisodeRepository
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


class EpisodeRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    agent_kind: EpisodeRunAgentKind = EpisodeRunAgentKind.SIMPLE_LLM_AGENT
    run_id: str | None = None
    tested_agent_client_provider: TestedAgentClientProvider = (
        DEFAULT_TESTED_AGENT_CLIENT_PROVIDER
    )
    simulator_client_provider: SimulatorClientProvider = (
        DEFAULT_SIMULATOR_CLIENT_PROVIDER
    )
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


@dataclass(frozen=True)
class EpisodeRunArtifacts:
    run_dir: Path
    episode_manifest_snapshot_path: Path
    transcript_path: Path
    working_map_path: Path
    agent_tool_trace_path: Path
    agent_output_path: Path
    scoring_report_path: Path


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


class EpisodeRunner:
    """Run registered Evaluation Episodes and persist formal run artifacts."""

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
        self._tested_agent_factory = tested_agent_factory or _build_tested_agent
        self._simulator_service_factory = (
            simulator_service_factory or _build_simulator_service
        )

    def run_episode(self, request: EpisodeRunRequest) -> EpisodeRunResult:
        run_id = request.run_id or default_episode_run_id()
        _ensure_run_dir_available(self._workspace_root, run_id)

        binding = self._episode_repository.load_episode_binding(request.episode_id)
        manifest = binding.manifest
        graph = binding.reviewed_graph.graph
        hidden_map = binding.hidden_map.knowledge_map
        agent = self._tested_agent_factory(request)
        simulator_service = self._simulator_service_factory(
            request.simulator_client_provider,
            self._workspace_root,
        )

        working_map = initialize_working_map(
            episode_id=manifest.episode_id,
            benchmark_domain=manifest.benchmark_domain,
            graph_version=manifest.graph_version,
            graph=graph,
        )
        visible_dialogue_context = VisibleDialogueContext()
        trace: list[dict[str, Any]] = []
        final_decision: TestedAgentDecision | None = None
        finalized: FinalizedReconstruction | None = None
        remaining_turns = manifest.max_turns
        phase = DecisionPhase.INITIAL_QUESTION
        forced_finalization_fallback = False
        forced_finalization = False

        while finalized is None:
            decision_context = DecisionPhaseContext(
                phase=phase,
                remaining_diagnostic_turns=remaining_turns,
            )
            if phase != DecisionPhase.INITIAL_QUESTION:
                working_map = _apply_working_map_updates(
                    agent=agent,
                    graph=graph,
                    working_map=working_map,
                    visible_dialogue_context=visible_dialogue_context,
                    decision_context=decision_context,
                    max_tool_retries=request.max_tool_retries,
                    trace=trace,
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

        scoring_report = score_final_reconstruction(
            graph=graph,
            ground_truth_map=hidden_map,
            submission=finalized.submission,
            scoring_profile=manifest.scoring_profile,
        )

        run_dir = _prepare_run_dir(self._workspace_root, run_id)
        artifacts = _artifact_paths(run_dir)
        _write_json(artifacts.episode_manifest_snapshot_path, manifest)
        _write_json(artifacts.transcript_path, visible_dialogue_context)
        _write_json(artifacts.working_map_path, working_map)
        _write_json(
            artifacts.agent_tool_trace_path,
            {
                "run_id": run_id,
                "episode_id": manifest.episode_id,
                "agent_kind": request.agent_kind.value,
                "max_tool_retries": request.max_tool_retries,
                "events": trace,
            },
        )
        _write_json(
            artifacts.agent_output_path,
            {
                "run_id": run_id,
                "episode_id": manifest.episode_id,
                "agent_kind": request.agent_kind.value,
                "tested_agent_client_provider": request.tested_agent_client_provider,
                "simulator_client_provider": request.simulator_client_provider,
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

        return EpisodeRunResult(
            run_id=run_id,
            episode_id=manifest.episode_id,
            agent_kind=request.agent_kind,
            turn_count=len(visible_dialogue_context.turns),
            forced_finalization=forced_finalization,
            forced_finalization_fallback=forced_finalization_fallback,
            artifacts=artifacts,
            scoring_report=scoring_report,
        )


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
    trace: list[dict[str, Any]],
) -> AgentWorkingKnowledgeMap:
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
            trace.append(
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

        trace.append(
            {
                "event": "working_map_update",
                "phase": decision_context.phase.value,
                "attempt_index": attempt_index,
                "status": "accepted",
                "updates": [_model_payload(update) for update in updates],
            }
        )
        return updated_working_map

    trace.append(
        {
            "event": "working_map_update",
            "phase": decision_context.phase.value,
            "status": "tool_retry_exhausted",
            "tool_retry_exhausted": True,
            "max_tool_retries": max_tool_retries,
        }
    )
    return working_map


def _build_tested_agent(request: EpisodeRunRequest) -> SimpleLLMTestedAgent:
    if request.agent_kind == EpisodeRunAgentKind.SIMPLE_LLM_AGENT:
        return build_simple_llm_tested_agent_for_provider(
            client_provider=request.tested_agent_client_provider,
            temperature=request.tested_agent_temperature,
        )
    raise UnsupportedEpisodeRunAgentKindError(
        f"Unsupported tested agent kind: {request.agent_kind}"
    )


def _build_simulator_service(
    client_provider: SimulatorClientProvider,
    workspace_root: Path,
) -> SimulatorService:
    return build_simulator_service_for_provider(
        workspace_root=workspace_root,
        client_provider=client_provider,
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
    run_dir = _run_dir_path(workspace_root, run_id)
    if run_dir.exists():
        raise EpisodeRunAlreadyExistsError(f"Episode Run {run_id} already exists")


def _run_dir_path(workspace_root: Path, run_id: str) -> Path:
    run_id = _validate_safe_id(run_id, "run_id")
    return workspace_root / "experiments" / "runs" / run_id


def _artifact_paths(run_dir: Path) -> EpisodeRunArtifacts:
    return EpisodeRunArtifacts(
        run_dir=run_dir,
        episode_manifest_snapshot_path=run_dir / "episode_manifest_snapshot.json",
        transcript_path=run_dir / "transcript.json",
        working_map_path=run_dir / "working_map.json",
        agent_tool_trace_path=run_dir / "agent_tool_trace.json",
        agent_output_path=run_dir / "agent_output.json",
        scoring_report_path=run_dir / "scoring_report.json",
    )


def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(_json_payload(payload), handle, indent=2, ensure_ascii=False)
        handle.write("\n")


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
