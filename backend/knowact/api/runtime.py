from pathlib import Path

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
    RuntimeEpisodeIdError,
    RuntimeEpisodeNotFoundError,
    RuntimeEpisodeRepository,
)
from backend.knowact.runtime.visibility import TestedAgentVisibleEpisodeContext


class RuntimeEpisodeSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    max_turns: int
    interaction_rule: str
    scoring_profile: str


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
                detail="Runtime episode registry contains a malformed manifest.",
            ) from exc

    @router.get(
        "/episodes/{episode_id}",
        response_model=TestedAgentVisibleEpisodeContext,
        summary="Read the tested-agent-visible context for one runtime episode.",
    )
    def read_episode(
        episode_id: str,
    ) -> TestedAgentVisibleEpisodeContext:
        try:
            return repository.build_tested_agent_visible_context(episode_id)
        except RuntimeEpisodeIdError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeEpisodeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeEpisodeArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail="Runtime episode manifest is malformed.",
            ) from exc
        except RuntimeEpisodeBindingError as exc:
            raise HTTPException(
                status_code=422,
                detail="Runtime episode could not be bound to reviewed artifacts.",
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


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]
