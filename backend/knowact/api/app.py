from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from backend.knowact.api.authoring import build_authoring_router
from backend.knowact.authoring.openai_workflow import build_openai_pdf_graph_authoring_workflow
from backend.knowact.authoring.workflow import GraphAuthoringAgentWorkflow


PDFGraphAuthoringWorkflowFactory = Callable[[Path, str | None], GraphAuthoringAgentWorkflow]


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    service: str


def create_app(
    *,
    pdf_graph_authoring_workflow_factory: PDFGraphAuthoringWorkflowFactory | None = None,
    workspace_root: Path | None = None,
) -> FastAPI:
    app = FastAPI(
        title="KnowAct Backend",
        version="0.1.0",
        description="KnowAct benchmark backend API for development and research workflows.",
    )

    app.include_router(
        build_authoring_router(
            pdf_graph_authoring_workflow_factory=pdf_graph_authoring_workflow_factory
            or _build_openai_pdf_graph_authoring_workflow,
            workspace_root=workspace_root,
        ),
        prefix="/api/authoring",
        tags=["authoring"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="knowact-backend")

    return app


def _build_openai_pdf_graph_authoring_workflow(
    pdf_path: Path,
    filename: str | None = None,
) -> GraphAuthoringAgentWorkflow:
    return build_openai_pdf_graph_authoring_workflow(pdf_path=pdf_path, filename=filename)
