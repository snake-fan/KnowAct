from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from backend.knowact.core.episode import (
    EvaluationEpisodeManifest,
    INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN,
    SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
)
from backend.knowact.runtime.episode_repository import (
    RuntimeEpisodeArtifactError,
    RuntimeEpisodeBindingError,
    RuntimeEpisodeBinding,
    RuntimeEpisodeIdentityMismatchError,
    RuntimeEpisodeIdError,
    RuntimeEpisodeNotFoundError,
    RuntimeEpisodeReviewedArtifactLoadError,
    RuntimeEpisodeRepository,
)
from backend.knowact.runtime.visibility import (
    TestedAgentVisibleEpisodeContext,
    build_tested_agent_visible_episode_context,
)
from backend.knowact.validation.exceptions import KnowActValidationError


class RuntimeEpisodeSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
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
    benchmark_domain: str
    graph_version: str
    kind: Literal["ground_truth"]
    covered_node_count: int


class RuntimeReviewedArtifactBindingSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    graph: RuntimeReviewedGraphBindingSummary
    reference_map: RuntimeReferenceMapBindingSummary


class RuntimeEpisodeDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest: RuntimeEpisodeSummary
    reviewed_artifacts: RuntimeReviewedArtifactBindingSummary
    tested_agent_visible_context_preview: TestedAgentVisibleEpisodeContext


def build_runtime_router(*, workspace_root: Path | None = None) -> APIRouter:
    root = workspace_root or _default_workspace_root()
    repository = RuntimeEpisodeRepository(workspace_root=root)
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
        manifest=_episode_summary(binding.manifest),
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
                benchmark_domain=binding.hidden_map.manifest.benchmark_domain,
                graph_version=binding.hidden_map.manifest.graph_version,
                kind=reference_map.kind.value,
                covered_node_count=len(reference_map.states),
            ),
        ),
        tested_agent_visible_context_preview=context,
    )


def _error_detail(error_code: str, message: str) -> dict[str, str]:
    return {"error_code": error_code, "message": message}


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]
