from __future__ import annotations

import json
from collections.abc import Callable
from json import JSONDecodeError
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.knowact.agents.protocol import TestedAgent
from backend.knowact.agents.providers import TestedAgentClientProvider
from backend.knowact.core.episode import (
    EpisodeExecutionConfiguration,
    EvaluationEpisodeManifest,
    INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN,
    SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
)
from backend.knowact.core.interaction import VisibleDialogueContext
from backend.knowact.core.scoring import EpisodeScoreReport
from backend.knowact.runtime.checkpoint import EpisodeRunCheckpointRepository
from backend.knowact.runtime.episode_options import (
    EpisodeExecutionConfigurationError,
    EpisodeModelCatalog,
    build_episode_model_catalog,
    validate_execution_configuration,
)
from backend.knowact.runtime.episode_repository import (
    RuntimeEpisodeAlreadyExistsError,
    RuntimeEpisodeArtifactError,
    RuntimeEpisodeBinding,
    RuntimeEpisodeBindingError,
    RuntimeEpisodeIdentityMismatchError,
    RuntimeEpisodeIdError,
    RuntimeEpisodeNotFoundError,
    RuntimeEpisodeReviewedArtifactLoadError,
    RuntimeEpisodeRepository,
)
from backend.knowact.runtime.execution_repository import (
    EpisodeExecutionFailure,
    EpisodeExecutionNotFoundError,
    EpisodeExecutionRecord,
    EpisodeExecutionRepository,
    EpisodeExecutionRepositoryError,
    EpisodeExecutionStatus,
    EpisodeExecutionTransitionError,
    EpisodeRunQueueState,
)
from backend.knowact.runtime.queue_scheduler import (
    EpisodeEnqueueSelection,
    EpisodeRunQueueScheduler,
)
from backend.knowact.runtime.runner import (
    EpisodeRunAgentKind,
    EpisodeRunArtifactError,
    EpisodeRunIdError,
    EpisodeRunRequest,
    EpisodeRunResult,
    EpisodeRunner,
    SimulatorServiceFactory as RunnerSimulatorServiceFactory,
    UnsupportedEpisodeRunAgentKindError,
    load_completed_episode_run,
)
from backend.knowact.runtime.visibility import (
    TestedAgentVisibleEpisodeContext,
    build_tested_agent_visible_episode_context,
)
from backend.knowact.validation.exceptions import KnowActValidationError


SimpleLLMRuntimeAgentFactory = Callable[
    [TestedAgentClientProvider, float | None],
    TestedAgent,
]


class RuntimeEpisodeSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    max_turns: int
    interaction_rule: str
    scoring_profile: str
    configuration_status: Literal["configured", "legacy_missing"]
    execution_configuration: EpisodeExecutionConfiguration | None = None
    warnings: tuple["RuntimeEpisodeWarningSummary", ...] = ()


class RuntimeEpisodeRegistrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    hidden_map_id: str
    max_turns: int = Field(gt=0)
    agent_kind: Literal["simple_llm_agent"]
    tested_agent_client_provider: Literal["openai", "deepseek"]
    tested_agent_model: str
    simulator_client_provider: Literal["openai", "deepseek"]
    simulator_model: str
    tested_agent_temperature: float = Field(ge=0.0)
    max_tool_retries: int = Field(ge=1)

    @field_validator(
        "episode_id",
        "benchmark_domain",
        "graph_version",
        "hidden_map_id",
        "tested_agent_model",
        "simulator_model",
    )
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    def execution_configuration(self) -> EpisodeExecutionConfiguration:
        return EpisodeExecutionConfiguration(
            agent_kind=self.agent_kind,
            tested_agent_client_provider=self.tested_agent_client_provider,
            tested_agent_model=self.tested_agent_model,
            simulator_client_provider=self.simulator_client_provider,
            simulator_model=self.simulator_model,
            tested_agent_temperature=self.tested_agent_temperature,
            max_tool_retries=self.max_tool_retries,
        )


class RuntimeEpisodeManagementManifestSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    hidden_map_id: str
    max_turns: int
    interaction_rule: str
    scoring_profile: str
    configuration_status: Literal["configured", "legacy_missing"]
    execution_configuration: EpisodeExecutionConfiguration | None = None


class RuntimeReviewedGraphBindingSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["loaded"]
    graph_id: str
    benchmark_domain: str
    version: str
    node_count: int
    edge_count: int


class RuntimeReferenceMapBindingSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["loaded"]
    map_id: str
    user_id: str
    benchmark_domain: str
    graph_version: str
    kind: Literal["ground_truth"]
    covered_node_count: int
    profile_context_status: Literal["loaded", "missing_optional"]


class RuntimeEpisodeWarningSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str


class RuntimeReviewedArtifactBindingSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    graph: RuntimeReviewedGraphBindingSummary
    reference_map: RuntimeReferenceMapBindingSummary


class RuntimeEpisodeDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest: RuntimeEpisodeManagementManifestSummary
    reviewed_artifacts: RuntimeReviewedArtifactBindingSummary
    warnings: tuple[RuntimeEpisodeWarningSummary, ...]
    tested_agent_visible_context_preview: TestedAgentVisibleEpisodeContext


class RuntimeEpisodeRunArtifactsSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_dir: str
    episode_manifest_snapshot: str
    turns: str
    transcript: str
    working_map: str
    agent_tool_trace: str
    agent_output: str
    scoring_report: str


class RuntimeEpisodeRunResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    episode_id: str
    agent_kind: EpisodeRunAgentKind
    turn_count: int
    forced_finalization: bool
    forced_finalization_fallback: bool
    artifacts: RuntimeEpisodeRunArtifactsSummary
    scoring_report: EpisodeScoreReport


class RuntimeRunQueueRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    status: EpisodeExecutionStatus
    selectable: bool
    queue_position: int | None = None
    run_id: str | None = None
    completed_turns: int
    max_turns: int
    checkpoint_health: Literal["not_applicable", "valid", "missing", "invalid"]
    cancel_requested: bool
    failure: EpisodeExecutionFailure | None = None


class RuntimeRunQueueResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    concurrency: int
    episodes: tuple[RuntimeRunQueueRow, ...]


class RuntimeRunQueueConcurrencyRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    concurrency: int


class RuntimeRunQueueEnqueueSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    action: Literal["start_or_resume", "restart"] = "start_or_resume"

    @field_validator("episode_id")
    @classmethod
    def _episode_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class RuntimeRunQueueEnqueueRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    selections: tuple[RuntimeRunQueueEnqueueSelection, ...] = Field(min_length=1)

    @field_validator("selections")
    @classmethod
    def _episode_ids_must_be_unique(
        cls,
        value: tuple[RuntimeRunQueueEnqueueSelection, ...],
    ) -> tuple[RuntimeRunQueueEnqueueSelection, ...]:
        episode_ids = [selection.episode_id for selection in value]
        if len(episode_ids) != len(set(episode_ids)):
            raise ValueError("selections must contain unique episode ids")
        return value


class RuntimeRunQueueEnqueueOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    accepted: bool
    status: EpisodeExecutionStatus
    run_id: str | None = None
    error_code: str | None = None
    message: str | None = None


class RuntimeRunQueueEnqueueResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    outcomes: tuple[RuntimeRunQueueEnqueueOutcome, ...]


class RuntimeRunQueueEpisodeDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode: RuntimeRunQueueRow
    manifest: RuntimeEpisodeManagementManifestSummary
    result: RuntimeEpisodeRunResponse | None = None


def build_runtime_router(
    *,
    workspace_root: Path | None = None,
    simple_llm_tested_agent_factory: SimpleLLMRuntimeAgentFactory | None = None,
    simulator_service_factory: RunnerSimulatorServiceFactory | None = None,
) -> APIRouter:
    root = workspace_root or _default_workspace_root()
    repository = RuntimeEpisodeRepository(workspace_root=root)
    execution_repository = EpisodeExecutionRepository(workspace_root=root)
    checkpoint_repository = EpisodeRunCheckpointRepository(workspace_root=root)
    runner = EpisodeRunner(
        workspace_root=root,
        tested_agent_factory=(
            _tested_agent_factory_from_simple_llm(simple_llm_tested_agent_factory)
            if simple_llm_tested_agent_factory is not None
            else None
        ),
        simulator_service_factory=simulator_service_factory,
    )
    scheduler = EpisodeRunQueueScheduler(
        episode_repository=repository,
        execution_repository=execution_repository,
        checkpoint_repository=checkpoint_repository,
        runner=runner,
    )
    provider_overrides = None
    if (
        simple_llm_tested_agent_factory is not None
        and simulator_service_factory is not None
    ):
        provider_overrides = {"openai": True, "deepseek": True}
    catalog = build_episode_model_catalog(
        available_provider_overrides=provider_overrides
    )
    router = APIRouter()
    router.add_event_handler("startup", scheduler.start)
    router.add_event_handler("shutdown", scheduler.stop)

    @router.get(
        "/episode-options",
        response_model=EpisodeModelCatalog,
        summary="List non-secret episode execution options.",
    )
    def episode_options() -> EpisodeModelCatalog:
        return catalog

    @router.get(
        "/episodes",
        response_model=tuple[RuntimeEpisodeSummary, ...],
        summary="List registered runtime episodes.",
    )
    def list_episodes() -> tuple[RuntimeEpisodeSummary, ...]:
        try:
            return tuple(
                _episode_summary(record.manifest)
                for record in repository.list_episodes()
            )
        except RuntimeEpisodeArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail(
                    "malformed_manifest",
                    "Runtime episode registry contains a malformed manifest.",
                ),
            ) from exc

    @router.post(
        "/episodes",
        response_model=RuntimeEpisodeDetail,
        status_code=status.HTTP_201_CREATED,
        summary="Register one runtime episode manifest.",
    )
    def register_episode(
        request: RuntimeEpisodeRegistrationRequest,
    ) -> RuntimeEpisodeDetail:
        try:
            configuration = request.execution_configuration()
            validate_execution_configuration(configuration, catalog)
            manifest = EvaluationEpisodeManifest(
                episode_id=request.episode_id,
                benchmark_domain=request.benchmark_domain,
                graph_version=request.graph_version,
                hidden_map_id=request.hidden_map_id,
                max_turns=request.max_turns,
                interaction_rule=INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN,
                scoring_profile=SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
                **configuration.model_dump(),
            )
            binding = repository.register_episode(manifest)
            execution_repository.initialize((manifest,))
            context = build_tested_agent_visible_episode_context(
                manifest=binding.manifest,
                graph=binding.reviewed_graph.graph,
            )
            return _episode_detail(binding=binding, context=context)
        except EpisodeExecutionConfigurationError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_execution_configuration", str(exc)),
            ) from exc
        except RuntimeEpisodeIdError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_episode_id", str(exc)),
            ) from exc
        except RuntimeEpisodeAlreadyExistsError as exc:
            raise HTTPException(
                status_code=409,
                detail=_error_detail("episode_already_exists", str(exc)),
            ) from exc
        except RuntimeEpisodeArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("malformed_manifest", str(exc)),
            ) from exc
        except RuntimeEpisodeIdentityMismatchError as exc:
            raise HTTPException(
                status_code=409,
                detail=_error_detail("identity_mismatch", str(exc)),
            ) from exc
        except RuntimeEpisodeReviewedArtifactLoadError as exc:
            raise HTTPException(
                status_code=424,
                detail=_error_detail(
                    "reviewed_artifact_loading_failure",
                    "Runtime episode reviewed artifacts could not be loaded.",
                ),
            ) from exc
        except RuntimeEpisodeBindingError as exc:
            raise HTTPException(
                status_code=424,
                detail=_error_detail(
                    "reviewed_artifact_loading_failure",
                    "Runtime episode could not be bound to reviewed artifacts.",
                ),
            ) from exc
        except KnowActValidationError as exc:
            raise HTTPException(
                status_code=500,
                detail=_error_detail(
                    "visibility_validation_failure",
                    "Runtime episode visible context failed visibility validation.",
                ),
            ) from exc

    @router.get(
        "/episodes/{episode_id}",
        response_model=RuntimeEpisodeDetail,
        summary="Read one runtime episode with tested-agent-visible context preview.",
    )
    def read_episode(episode_id: str) -> RuntimeEpisodeDetail:
        try:
            binding = repository.load_episode_binding(episode_id)
            context = build_tested_agent_visible_episode_context(
                manifest=binding.manifest,
                graph=binding.reviewed_graph.graph,
            )
            return _episode_detail(binding=binding, context=context)
        except RuntimeEpisodeIdError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_episode_id", str(exc)),
            ) from exc
        except RuntimeEpisodeNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=_error_detail("episode_not_found", str(exc)),
            ) from exc
        except RuntimeEpisodeArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("malformed_manifest", str(exc)),
            ) from exc
        except RuntimeEpisodeIdentityMismatchError as exc:
            raise HTTPException(
                status_code=409,
                detail=_error_detail("identity_mismatch", str(exc)),
            ) from exc
        except RuntimeEpisodeBindingError as exc:
            raise HTTPException(
                status_code=424,
                detail=_error_detail(
                    "reviewed_artifact_loading_failure",
                    "Runtime episode reviewed artifacts could not be loaded.",
                ),
            ) from exc
        except KnowActValidationError as exc:
            raise HTTPException(
                status_code=500,
                detail=_error_detail(
                    "visibility_validation_failure",
                    "Runtime episode visible context failed visibility validation.",
                ),
            ) from exc

    @router.get(
        "/run-queue",
        response_model=RuntimeRunQueueResponse,
        summary="Read the persistent Episode Run Queue.",
    )
    def read_run_queue() -> RuntimeRunQueueResponse:
        try:
            return _queue_response(
                state=scheduler.snapshot(),
                repository=repository,
            )
        except (RuntimeEpisodeArtifactError, EpisodeExecutionRepositoryError) as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("malformed_run_queue", str(exc)),
            ) from exc

    @router.put(
        "/run-queue/concurrency",
        response_model=RuntimeRunQueueResponse,
        summary="Update persisted global Episode Run concurrency.",
    )
    def update_run_queue_concurrency(
        request: RuntimeRunQueueConcurrencyRequest,
    ) -> RuntimeRunQueueResponse:
        try:
            return _queue_response(
                state=scheduler.set_concurrency(request.concurrency),
                repository=repository,
            )
        except EpisodeExecutionRepositoryError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_queue_concurrency", str(exc)),
            ) from exc

    @router.post(
        "/run-queue/enqueue",
        response_model=RuntimeRunQueueEnqueueResponse,
        summary="Admit selected episodes independently into the persistent queue.",
    )
    def enqueue_episodes(
        request: RuntimeRunQueueEnqueueRequest,
    ) -> RuntimeRunQueueEnqueueResponse:
        outcomes = scheduler.enqueue(
            tuple(
                EpisodeEnqueueSelection(
                    episode_id=selection.episode_id,
                    action=selection.action,
                )
                for selection in request.selections
            )
        )
        return RuntimeRunQueueEnqueueResponse(
            outcomes=tuple(
                RuntimeRunQueueEnqueueOutcome(
                    episode_id=outcome.episode_id,
                    accepted=outcome.accepted,
                    status=outcome.status,
                    run_id=outcome.run_id,
                    error_code=outcome.error_code,
                    message=outcome.message,
                )
                for outcome in outcomes
            )
        )

    @router.post(
        "/run-queue/episodes/{episode_id}/cancel",
        response_model=RuntimeRunQueueRow,
        summary="Cancel one queued or running episode.",
    )
    def cancel_episode(episode_id: str) -> RuntimeRunQueueRow:
        try:
            record = scheduler.cancel(episode_id)
            state = scheduler.snapshot()
            return _queue_row(
                manifest=repository.read_episode_manifest(episode_id),
                record=record,
                queue_positions=_queue_positions(state),
            )
        except (EpisodeExecutionNotFoundError, RuntimeEpisodeNotFoundError) as exc:
            raise HTTPException(
                status_code=404,
                detail=_error_detail("episode_not_found", str(exc)),
            ) from exc
        except EpisodeExecutionTransitionError as exc:
            raise HTTPException(
                status_code=409,
                detail=_error_detail("episode_not_cancellable", str(exc)),
            ) from exc

    @router.get(
        "/run-queue/episodes/{episode_id}",
        response_model=RuntimeRunQueueEpisodeDetail,
        summary="Read one episode's queue state and completed result.",
    )
    def read_queue_episode(episode_id: str) -> RuntimeRunQueueEpisodeDetail:
        try:
            manifest = repository.read_episode_manifest(episode_id)
            state = scheduler.snapshot()
            record = state.episodes[episode_id]
            result = None
            if record.status == EpisodeExecutionStatus.COMPLETED and record.run_id:
                result = _run_response(
                    root=root,
                    result=load_completed_episode_run(
                        workspace_root=root,
                        run_id=record.run_id,
                    ),
                )
            return RuntimeRunQueueEpisodeDetail(
                episode=_queue_row(
                    manifest=manifest,
                    record=record,
                    queue_positions=_queue_positions(state),
                ),
                manifest=_management_manifest_summary(manifest),
                result=result,
            )
        except (RuntimeEpisodeNotFoundError, KeyError, EpisodeExecutionNotFoundError) as exc:
            raise HTTPException(
                status_code=404,
                detail=_error_detail("episode_not_found", str(exc)),
            ) from exc
        except EpisodeRunArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("malformed_episode_result", str(exc)),
            ) from exc

    @router.get(
        "/runs/{run_id}/transcript",
        response_model=VisibleDialogueContext,
        summary="Read one visible Episode Run transcript.",
    )
    def read_run_transcript(run_id: str) -> VisibleDialogueContext:
        try:
            transcript_path = _run_transcript_path(root, run_id)
        except EpisodeRunIdError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_run_id", str(exc)),
            ) from exc
        if not transcript_path.exists():
            raise HTTPException(
                status_code=404,
                detail=_error_detail(
                    "episode_run_not_found",
                    "Episode Run transcript not found.",
                ),
            )
        try:
            with transcript_path.open("r", encoding="utf-8") as handle:
                return VisibleDialogueContext.model_validate(json.load(handle))
        except (JSONDecodeError, ValidationError) as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail(
                    "malformed_run_transcript",
                    "Episode Run transcript artifact is malformed.",
                ),
            ) from exc

    return router


def _episode_summary(manifest: EvaluationEpisodeManifest) -> RuntimeEpisodeSummary:
    configuration = manifest.execution_configuration()
    warnings = ()
    if configuration is None:
        warnings = (
            RuntimeEpisodeWarningSummary(
                code="execution_configuration_missing",
                message="This legacy episode is read-only and cannot enter Run Queue.",
            ),
        )
    return RuntimeEpisodeSummary(
        episode_id=manifest.episode_id,
        benchmark_domain=manifest.benchmark_domain,
        graph_version=manifest.graph_version,
        max_turns=manifest.max_turns,
        interaction_rule=manifest.interaction_rule,
        scoring_profile=manifest.scoring_profile,
        configuration_status=(
            "legacy_missing" if configuration is None else "configured"
        ),
        execution_configuration=configuration,
        warnings=warnings,
    )


def _management_manifest_summary(
    manifest: EvaluationEpisodeManifest,
) -> RuntimeEpisodeManagementManifestSummary:
    configuration = manifest.execution_configuration()
    return RuntimeEpisodeManagementManifestSummary(
        episode_id=manifest.episode_id,
        benchmark_domain=manifest.benchmark_domain,
        graph_version=manifest.graph_version,
        hidden_map_id=manifest.hidden_map_id,
        max_turns=manifest.max_turns,
        interaction_rule=manifest.interaction_rule,
        scoring_profile=manifest.scoring_profile,
        configuration_status=(
            "legacy_missing" if configuration is None else "configured"
        ),
        execution_configuration=configuration,
    )


def _episode_detail(
    *,
    binding: RuntimeEpisodeBinding,
    context: TestedAgentVisibleEpisodeContext,
) -> RuntimeEpisodeDetail:
    graph = binding.reviewed_graph.graph
    reference_map = binding.hidden_map.knowledge_map
    warnings = [
        RuntimeEpisodeWarningSummary(
            code=warning.code.value,
            message=warning.message,
        )
        for warning in binding.warnings
    ]
    if binding.manifest.is_legacy:
        warnings.append(
            RuntimeEpisodeWarningSummary(
                code="execution_configuration_missing",
                message="This legacy episode is read-only and cannot enter Run Queue.",
            )
        )
    return RuntimeEpisodeDetail(
        manifest=_management_manifest_summary(binding.manifest),
        reviewed_artifacts=RuntimeReviewedArtifactBindingSummary(
            graph=RuntimeReviewedGraphBindingSummary(
                status="loaded",
                graph_id=binding.reviewed_graph.manifest.graph_id,
                benchmark_domain=binding.reviewed_graph.manifest.domain,
                version=binding.reviewed_graph.manifest.version,
                node_count=len(graph.nodes),
                edge_count=len(graph.edges),
            ),
            reference_map=RuntimeReferenceMapBindingSummary(
                status="loaded",
                map_id=binding.hidden_map.manifest.map_id,
                user_id=binding.hidden_map.manifest.user_id,
                benchmark_domain=binding.hidden_map.manifest.benchmark_domain,
                graph_version=binding.hidden_map.manifest.graph_version,
                kind=reference_map.kind.value,
                covered_node_count=len(reference_map.states),
                profile_context_status=binding.profile_context.status.value,
            ),
        ),
        warnings=tuple(warnings),
        tested_agent_visible_context_preview=context,
    )


def _queue_response(
    *,
    state: EpisodeRunQueueState,
    repository: RuntimeEpisodeRepository,
) -> RuntimeRunQueueResponse:
    positions = _queue_positions(state)
    manifests = {
        record.episode_id: record.manifest
        for record in repository.list_episodes()
        if not record.manifest.is_legacy
    }
    return RuntimeRunQueueResponse(
        concurrency=state.concurrency,
        episodes=tuple(
            _queue_row(
                manifest=manifests[episode_id],
                record=record,
                queue_positions=positions,
            )
            for episode_id, record in state.episodes.items()
            if episode_id in manifests
        ),
    )


def _queue_positions(state: EpisodeRunQueueState) -> dict[str, int]:
    queued = sorted(
        (
            record
            for record in state.episodes.values()
            if record.status == EpisodeExecutionStatus.QUEUED
        ),
        key=lambda record: record.queue_order or 0,
    )
    return {record.episode_id: index + 1 for index, record in enumerate(queued)}


def _queue_row(
    *,
    manifest: EvaluationEpisodeManifest,
    record: EpisodeExecutionRecord,
    queue_positions: dict[str, int],
) -> RuntimeRunQueueRow:
    return RuntimeRunQueueRow(
        episode_id=manifest.episode_id,
        benchmark_domain=manifest.benchmark_domain,
        graph_version=manifest.graph_version,
        status=record.status,
        selectable=record.status
        in {
            EpisodeExecutionStatus.READY,
            EpisodeExecutionStatus.FAILED,
            EpisodeExecutionStatus.CANCELLED,
        },
        queue_position=queue_positions.get(manifest.episode_id),
        run_id=record.run_id,
        completed_turns=record.completed_turns,
        max_turns=record.max_turns,
        checkpoint_health=record.checkpoint_health,
        cancel_requested=record.cancel_requested,
        failure=record.failure,
    )


def _run_response(
    *,
    root: Path,
    result: EpisodeRunResult,
) -> RuntimeEpisodeRunResponse:
    artifacts = result.artifacts
    return RuntimeEpisodeRunResponse(
        run_id=result.run_id,
        episode_id=result.episode_id,
        agent_kind=result.agent_kind,
        turn_count=result.turn_count,
        forced_finalization=result.forced_finalization,
        forced_finalization_fallback=result.forced_finalization_fallback,
        artifacts=RuntimeEpisodeRunArtifactsSummary(
            run_dir=_relative_path(root, artifacts.run_dir),
            episode_manifest_snapshot=_relative_path(
                root,
                artifacts.episode_manifest_snapshot_path,
            ),
            turns=_relative_path(root, artifacts.turns_dir),
            transcript=_relative_path(root, artifacts.transcript_path),
            working_map=_relative_path(root, artifacts.working_map_path),
            agent_tool_trace=_relative_path(root, artifacts.agent_tool_trace_path),
            agent_output=_relative_path(root, artifacts.agent_output_path),
            scoring_report=_relative_path(root, artifacts.scoring_report_path),
        ),
        scoring_report=result.scoring_report,
    )


def _relative_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _run_transcript_path(root: Path, run_id: str) -> Path:
    safe_run_id = _validate_runtime_run_id(run_id)
    return root / "experiments" / "runs" / safe_run_id / "transcript.json"


def _validate_runtime_run_id(run_id: str) -> str:
    try:
        request = EpisodeRunRequest(
            episode_id="validation_probe",
            run_id=run_id,
        )
        return request.run_id or run_id
    except ValueError as exc:
        raise EpisodeRunIdError(str(exc)) from exc


def _tested_agent_factory_from_simple_llm(
    simple_llm_tested_agent_factory: SimpleLLMRuntimeAgentFactory,
):
    def _factory(request: EpisodeRunRequest) -> TestedAgent:
        if request.agent_kind != EpisodeRunAgentKind.SIMPLE_LLM_AGENT:
            raise UnsupportedEpisodeRunAgentKindError(
                f"Unsupported tested agent kind: {request.agent_kind}"
            )
        return simple_llm_tested_agent_factory(
            request.tested_agent_client_provider,
            request.tested_agent_temperature,
        )

    return _factory


def _error_detail(error_code: str, message: str) -> dict[str, str]:
    return {"error_code": error_code, "message": message}


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]
