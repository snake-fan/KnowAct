from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.knowact.simulator.preview import SimulatorPreviewRequest, SimulatorPreviewResponse
from backend.knowact.simulator.service import SimulatorService
from backend.knowact.storage.profile_contexts import ConfirmedProfileContextArtifactError
from backend.knowact.storage.reviewed_graphs import (
    ReviewedGraphArtifactError,
    ReviewedGraphNotFoundError,
)
from backend.knowact.storage.reviewed_maps import (
    ReviewedMapArtifactError,
    ReviewedMapNotFoundError,
)


def build_simulator_router(*, workspace_root: Path | None = None) -> APIRouter:
    root = workspace_root or _default_workspace_root()
    service = SimulatorService(workspace_root=root)
    router = APIRouter()

    @router.post(
        "/preview",
        response_model=SimulatorPreviewResponse,
        summary="Preview one reviewed-map-grounded simulator answer.",
    )
    def answer_preview(request: SimulatorPreviewRequest) -> SimulatorPreviewResponse:
        try:
            return service.answer_preview(request)
        except (ReviewedMapNotFoundError, ReviewedGraphNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (
            ReviewedMapArtifactError,
            ReviewedGraphArtifactError,
            ConfirmedProfileContextArtifactError,
            KeyError,
            ValueError,
        ) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]
