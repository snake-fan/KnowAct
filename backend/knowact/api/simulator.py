from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.knowact.simulator.llm_service import (
    SimulatorServiceConfigurationError,
    build_simulator_service_for_provider,
)
from backend.knowact.simulator.providers import SimulatorClientProvider
from backend.knowact.simulator.service import SimulatorService
from backend.knowact.simulator.turn import SimulatorTurnRequest, SimulatorTurnResponse
from backend.knowact.storage.profile_contexts import ConfirmedProfileContextArtifactError
from backend.knowact.storage.reviewed_graphs import (
    ReviewedGraphArtifactError,
    ReviewedGraphNotFoundError,
)
from backend.knowact.storage.reviewed_maps import (
    ReviewedMapArtifactError,
    ReviewedMapNotFoundError,
)


SimulatorServiceFactory = Callable[[SimulatorClientProvider, Path], SimulatorService]


def build_simulator_router(
    *,
    workspace_root: Path | None = None,
    simulator_service_factory: SimulatorServiceFactory | None = None,
) -> APIRouter:
    root = workspace_root or _default_workspace_root()
    service_factory = simulator_service_factory or (
        lambda client_provider, service_root: build_simulator_service_for_provider(
            workspace_root=service_root,
            client_provider=client_provider,
        )
    )
    services_by_provider: dict[SimulatorClientProvider, SimulatorService] = {}
    router = APIRouter()

    def _answer_turn(request: SimulatorTurnRequest) -> SimulatorTurnResponse:
        try:
            service = services_by_provider.get(request.client_provider)
            if service is None:
                service = service_factory(request.client_provider, root)
                services_by_provider[request.client_provider] = service
            return service.answer_turn(request)
        except SimulatorServiceConfigurationError as exc:
            raise HTTPException(
                status_code=503,
                detail="Simulator LLM service is not configured.",
            ) from exc
        except ReviewedMapNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ReviewedGraphNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="Reviewed graph binding does not exist.",
            ) from exc
        except ReviewedMapArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail="Reviewed map artifact is malformed.",
            ) from exc
        except ReviewedGraphArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail="Reviewed graph artifact is malformed.",
            ) from exc
        except ConfirmedProfileContextArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail="Confirmed Profile Context artifact is malformed.",
            ) from exc
        except (KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail="Simulator turn request could not be satisfied by reviewed artifacts.",
            ) from exc

    @router.post(
        "/turn",
        response_model=SimulatorTurnResponse,
        summary="Answer one reviewed-map-grounded simulator turn.",
    )
    def answer_turn(request: SimulatorTurnRequest) -> SimulatorTurnResponse:
        return _answer_turn(request)

    @router.post(
        "/preview",
        response_model=SimulatorTurnResponse,
        summary="Deprecated compatibility alias for one simulator turn.",
        deprecated=True,
    )
    def answer_preview(request: SimulatorTurnRequest) -> SimulatorTurnResponse:
        return _answer_turn(request)

    return router


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]
