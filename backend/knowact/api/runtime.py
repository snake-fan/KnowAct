import json
from collections.abc import Callable
from json import JSONDecodeError
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.knowact.core.episode import (
    EvaluationEpisodeManifest,
    INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN,
    SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
)
from backend.knowact.core.interaction import VisibleDialogueContext
from backend.knowact.core.scoring import EpisodeScoreReport
from backend.knowact.agents.protocol import TestedAgent
from backend.knowact.agents.providers import (
    DEFAULT_TESTED_AGENT_CLIENT_PROVIDER,
    TestedAgentClientProvider,
)
from backend.knowact.agents.llm_agent import TestedAgentConfigurationError
from backend.knowact.llm.client import ModelClientError
from backend.knowact.runtime.episode_repository import (
    RuntimeEpisodeAlreadyExistsError,
    RuntimeEpisodeArtifactError,
    RuntimeEpisodeBindingError,
    RuntimeEpisodeBinding,
    RuntimeEpisodeIdentityMismatchError,
    RuntimeEpisodeIdError,
    RuntimeEpisodeNotFoundError,
    RuntimeEpisodeReviewedArtifactLoadError,
    RuntimeEpisodeRepository,
)
from backend.knowact.runtime.runner import (
    EpisodeRunAgentKind,
    EpisodeRunAlreadyExistsError,
    EpisodeRunIdError,
    EpisodeRunRequest,
    EpisodeRunResult,
    EpisodeRunner,
    SimulatorServiceFactory as RunnerSimulatorServiceFactory,
    UnsupportedEpisodeRunAgentKindError,
)
from backend.knowact.runtime.visibility import (
    TestedAgentVisibleEpisodeContext,
    build_tested_agent_visible_episode_context,
)
from backend.knowact.simulator.llm_service import SimulatorServiceConfigurationError
from backend.knowact.simulator.providers import (
    DEFAULT_SIMULATOR_CLIENT_PROVIDER,
    SimulatorClientProvider,
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


class RuntimeEpisodeRegistrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    hidden_map_id: str
    max_turns: int = Field(gt=0)

    @field_validator(
        "episode_id",
        "benchmark_domain",
        "graph_version",
        "hidden_map_id",
    )
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class RuntimeEpisodeManagementManifestSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    hidden_map_id: str
    max_turns: int
    interaction_rule: str
    scoring_profile: str


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


class RuntimeEpisodeRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str | None = None
    agent_kind: EpisodeRunAgentKind
    tested_agent_client_provider: TestedAgentClientProvider = (
        DEFAULT_TESTED_AGENT_CLIENT_PROVIDER
    )
    simulator_client_provider: SimulatorClientProvider = (
        DEFAULT_SIMULATOR_CLIENT_PROVIDER
    )
    tested_agent_temperature: float | None = Field(default=None, ge=0.0)
    max_tool_retries: int = Field(default=3, ge=1)

    @field_validator("run_id")
    @classmethod
    def _run_id_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class RuntimeEpisodeRunArtifactsSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_dir: str
    episode_manifest_snapshot: str
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


def build_runtime_router(
    *,
    workspace_root: Path | None = None,
    simple_llm_tested_agent_factory: SimpleLLMRuntimeAgentFactory | None = None,
    simulator_service_factory: RunnerSimulatorServiceFactory | None = None,
) -> APIRouter:
    root = workspace_root or _default_workspace_root()
    repository = RuntimeEpisodeRepository(workspace_root=root)
    runner = EpisodeRunner(
        workspace_root=root,
        tested_agent_factory=(
            _tested_agent_factory_from_simple_llm(simple_llm_tested_agent_factory)
            if simple_llm_tested_agent_factory is not None
            else None
        ),
        simulator_service_factory=simulator_service_factory,
    )
    router = APIRouter()

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
            manifest = EvaluationEpisodeManifest(
                episode_id=request.episode_id,
                benchmark_domain=request.benchmark_domain,
                graph_version=request.graph_version,
                hidden_map_id=request.hidden_map_id,
                max_turns=request.max_turns,
                interaction_rule=INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN,
                scoring_profile=SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
            )
            binding = repository.register_episode(manifest)
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
        except RuntimeEpisodeAlreadyExistsError as exc:
            raise HTTPException(
                status_code=409,
                detail=_error_detail("episode_already_exists", str(exc)),
            ) from exc
        except RuntimeEpisodeArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail(
                    "malformed_manifest",
                    "Runtime episode manifest is malformed.",
                ),
            ) from exc
        except RuntimeEpisodeReviewedArtifactLoadError as exc:
            raise HTTPException(
                status_code=424,
                detail=_error_detail(
                    "reviewed_artifact_loading_failure",
                    "Runtime episode reviewed artifacts could not be loaded.",
                ),
            ) from exc
        except RuntimeEpisodeIdentityMismatchError as exc:
            raise HTTPException(
                status_code=409,
                detail=_error_detail(
                    "identity_mismatch",
                    "Runtime episode manifest does not match reviewed artifact identities.",
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
    def read_episode(
        episode_id: str,
    ) -> RuntimeEpisodeDetail:
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
                detail=_error_detail(
                    "malformed_manifest",
                    "Runtime episode manifest is malformed.",
                ),
            ) from exc
        except RuntimeEpisodeReviewedArtifactLoadError as exc:
            raise HTTPException(
                status_code=424,
                detail=_error_detail(
                    "reviewed_artifact_loading_failure",
                    "Runtime episode reviewed artifacts could not be loaded.",
                ),
            ) from exc
        except RuntimeEpisodeIdentityMismatchError as exc:
            raise HTTPException(
                status_code=409,
                detail=_error_detail(
                    "identity_mismatch",
                    "Runtime episode manifest does not match reviewed artifact identities.",
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

    @router.post(
        "/episodes/{episode_id}/runs",
        response_model=RuntimeEpisodeRunResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Run one registered runtime episode.",
    )
    def run_episode(
        episode_id: str,
        request: RuntimeEpisodeRunRequest,
    ) -> RuntimeEpisodeRunResponse:
        try:
            result = runner.run_episode(
                EpisodeRunRequest(
                    episode_id=episode_id,
                    run_id=request.run_id,
                    agent_kind=request.agent_kind,
                    tested_agent_client_provider=request.tested_agent_client_provider,
                    simulator_client_provider=request.simulator_client_provider,
                    tested_agent_temperature=request.tested_agent_temperature,
                    max_tool_retries=request.max_tool_retries,
                )
            )
            return _run_response(root=root, result=result)
        except RuntimeEpisodeIdError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_episode_id", str(exc)),
            ) from exc
        except EpisodeRunIdError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_run_id", str(exc)),
            ) from exc
        except EpisodeRunAlreadyExistsError as exc:
            raise HTTPException(
                status_code=409,
                detail=_error_detail("episode_run_already_exists", str(exc)),
            ) from exc
        except RuntimeEpisodeNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=_error_detail("episode_not_found", str(exc)),
            ) from exc
        except RuntimeEpisodeArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail(
                    "malformed_manifest",
                    "Runtime episode manifest is malformed.",
                ),
            ) from exc
        except RuntimeEpisodeIdentityMismatchError as exc:
            raise HTTPException(
                status_code=409,
                detail=_error_detail(
                    "identity_mismatch",
                    "Runtime episode manifest does not match reviewed artifact identities.",
                ),
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
        except UnsupportedEpisodeRunAgentKindError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("unsupported_agent_kind", str(exc)),
            ) from exc
        except (TestedAgentConfigurationError, SimulatorServiceConfigurationError) as exc:
            raise HTTPException(
                status_code=503,
                detail=_error_detail(
                    "runtime_service_not_configured",
                    "Episode Run provider-backed runtime service is not configured.",
                ),
            ) from exc
        except ModelClientError as exc:
            raise HTTPException(
                status_code=502,
                detail=_error_detail("runtime_model_error", str(exc)),
            ) from exc
        except KnowActValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_episode_run", str(exc)),
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
                detail=_error_detail("episode_run_not_found", "Episode Run transcript not found."),
            )

        try:
            with transcript_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return VisibleDialogueContext.model_validate(payload)
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
    return RuntimeEpisodeSummary(
        episode_id=manifest.episode_id,
        benchmark_domain=manifest.benchmark_domain,
        graph_version=manifest.graph_version,
        max_turns=manifest.max_turns,
        interaction_rule=INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN,
        scoring_profile=SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
    )


def _episode_detail(
    *,
    binding: RuntimeEpisodeBinding,
    context: TestedAgentVisibleEpisodeContext,
) -> RuntimeEpisodeDetail:
    graph = binding.reviewed_graph.graph
    reference_map = binding.hidden_map.knowledge_map
    return RuntimeEpisodeDetail(
        manifest=RuntimeEpisodeManagementManifestSummary(
            episode_id=binding.manifest.episode_id,
            benchmark_domain=binding.manifest.benchmark_domain,
            graph_version=binding.manifest.graph_version,
            hidden_map_id=binding.manifest.hidden_map_id,
            max_turns=binding.manifest.max_turns,
            interaction_rule=INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN,
            scoring_profile=SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
        ),
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
        warnings=tuple(
            RuntimeEpisodeWarningSummary(
                code=warning.code.value,
                message=warning.message,
            )
            for warning in binding.warnings
        ),
        tested_agent_visible_context_preview=context,
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
