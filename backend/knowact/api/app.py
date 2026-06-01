from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from backend.knowact.api.authoring import build_authoring_router
from backend.knowact.authoring.openai_workflow import (
    GraphAuthoringClientProvider,
    build_graph_authoring_workflow_for_provider,
)
from backend.knowact.authoring.profile_context import (
    ProfileContextAuthoringWorkflow,
    build_profile_context_authoring_workflow_for_provider,
)
from backend.knowact.authoring.sources import MinerUHTTPSourceParser, SourceParser
from backend.knowact.authoring.workflow import GraphAuthoringAgentWorkflow


GraphAuthoringWorkflowFactory = Callable[[GraphAuthoringClientProvider], GraphAuthoringAgentWorkflow]
ProfileContextAuthoringWorkflowFactory = Callable[
    [GraphAuthoringClientProvider],
    ProfileContextAuthoringWorkflow,
]


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    service: str


def create_app(
    *,
    graph_authoring_workflow_factory: GraphAuthoringWorkflowFactory | None = None,
    profile_context_authoring_workflow_factory: ProfileContextAuthoringWorkflowFactory | None = None,
    source_parser: SourceParser | None = None,
    workspace_root: Path | None = None,
) -> FastAPI:
    app = FastAPI(
        title="KnowAct Backend",
        version="0.1.0",
        description="KnowAct benchmark backend API for development and research workflows.",
    )

    app.include_router(
        build_authoring_router(
            graph_authoring_workflow_factory=graph_authoring_workflow_factory
            or build_graph_authoring_workflow_for_provider,
            profile_context_authoring_workflow_factory=profile_context_authoring_workflow_factory
            or build_profile_context_authoring_workflow_for_provider,
            source_parser=source_parser or MinerUHTTPSourceParser(),
            workspace_root=workspace_root,
        ),
        prefix="/api/authoring",
        tags=["authoring"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="knowact-backend")

    return app
