from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.knowact.authoring.map_authoring_output import (
    CandidateMapArtifactError,
    CandidateMapNotFoundError,
)
from backend.knowact.core.simulator_experiment import (
    ParticipantMapStateRevision,
    SimulatorExperimentClientProvider,
    SimulatorExperimentLanguage,
    SimulatorExperimentQuestionBankSummary,
    SimulatorExperimentSession,
    SimulatorExperimentSessionSummary,
    SimulatorSelfEvaluation,
)
from backend.knowact.runtime.simulator_experiment import (
    ParticipantMapConfirmationResult,
    SimulatorExperimentService,
    SimulatorExperimentServiceFactory,
    SimulatorExperimentStateError,
)
from backend.knowact.simulator.llm_service import SimulatorServiceConfigurationError
from backend.knowact.storage.profile_contexts import (
    ConfirmedProfileContextArtifactError,
    ConfirmedProfileContextNotFoundError,
)
from backend.knowact.storage.reviewed_graphs import (
    ReviewedGraphArtifactError,
    ReviewedGraphNotFoundError,
)
from backend.knowact.storage.reviewed_maps import (
    ReviewedMapArtifactError,
    ReviewedMapNotFoundError,
    ReviewedMapPromotionConflictError,
)
from backend.knowact.storage.simulator_experiments import (
    SimulatorExperimentArtifactError,
    SimulatorExperimentQuestionBankNotFoundError,
    SimulatorExperimentSessionConflictError,
    SimulatorExperimentSessionNotFoundError,
)
from backend.knowact.validation.exceptions import KnowActValidationError


class ParticipantMapConfirmationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    map_id: str
    revisions: tuple[ParticipantMapStateRevision, ...] = Field(min_length=1)


class CreateSimulatorExperimentSessionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    participant_code: str
    benchmark_domain: str
    map_id: str
    question_bank_id: str
    language: SimulatorExperimentLanguage
    simulator_client_provider: SimulatorExperimentClientProvider = "openai"
    sampling_seed: int | None = None
    session_id: str | None = None


class SubmitHumanAnswerRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    human_answer: str = Field(min_length=1)


class SimulatorExperimentQuestionBankListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_banks: tuple[SimulatorExperimentQuestionBankSummary, ...]


class SimulatorExperimentSessionListResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sessions: tuple[SimulatorExperimentSessionSummary, ...]


def build_experiments_router(
    *,
    workspace_root: Path | None = None,
    simulator_service_factory: SimulatorExperimentServiceFactory | None = None,
) -> APIRouter:
    root = workspace_root or _default_workspace_root()
    service = SimulatorExperimentService(
        workspace_root=root,
        simulator_service_factory=simulator_service_factory,
    )
    router = APIRouter()

    @router.get(
        "/simulator-tests/question-banks",
        response_model=SimulatorExperimentQuestionBankListResponse,
        summary="List versioned bilingual Simulator test question banks.",
    )
    def list_simulator_test_question_banks() -> SimulatorExperimentQuestionBankListResponse:
        return SimulatorExperimentQuestionBankListResponse(
            question_banks=service.list_question_banks()
        )

    @router.post(
        "/simulator-tests/participant-maps/{benchmark_domain}/{candidate_map_run_id}/confirmation",
        response_model=ParticipantMapConfirmationResult,
        summary="Publish one participant-reviewed map for Simulator testing.",
    )
    def confirm_participant_map(
        benchmark_domain: str,
        candidate_map_run_id: str,
        request: ParticipantMapConfirmationRequest,
    ) -> ParticipantMapConfirmationResult:
        try:
            return service.confirm_participant_map(
                benchmark_domain=benchmark_domain,
                candidate_map_run_id=candidate_map_run_id,
                map_id=request.map_id,
                revisions=request.revisions,
            )
        except (
            CandidateMapNotFoundError,
            ReviewedGraphNotFoundError,
            ConfirmedProfileContextNotFoundError,
        ) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ReviewedMapPromotionConflictError, SimulatorExperimentSessionConflictError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (
            CandidateMapArtifactError,
            ReviewedGraphArtifactError,
            ConfirmedProfileContextArtifactError,
            KnowActValidationError,
            ValueError,
        ) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get(
        "/simulator-tests/sessions",
        response_model=SimulatorExperimentSessionListResponse,
        summary="List resumable private Simulator test sessions.",
    )
    def list_simulator_test_sessions() -> SimulatorExperimentSessionListResponse:
        return SimulatorExperimentSessionListResponse(sessions=service.list_sessions())

    @router.post(
        "/simulator-tests/sessions",
        response_model=SimulatorExperimentSession,
        status_code=201,
        summary="Create one 20-question Simulator test session.",
    )
    def create_simulator_test_session(
        request: CreateSimulatorExperimentSessionRequest,
    ) -> SimulatorExperimentSession:
        try:
            return service.create_session(
                participant_code=request.participant_code,
                benchmark_domain=request.benchmark_domain,
                map_id=request.map_id,
                question_bank_id=request.question_bank_id,
                language=request.language,
                simulator_client_provider=request.simulator_client_provider,
                sampling_seed=request.sampling_seed,
                session_id=request.session_id,
            )
        except (
            ReviewedMapNotFoundError,
            ConfirmedProfileContextNotFoundError,
            SimulatorExperimentQuestionBankNotFoundError,
        ) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SimulatorExperimentSessionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (
            ReviewedMapArtifactError,
            ConfirmedProfileContextArtifactError,
            SimulatorExperimentArtifactError,
            SimulatorExperimentStateError,
            ValueError,
        ) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get(
        "/simulator-tests/sessions/{session_id}",
        response_model=SimulatorExperimentSession,
        summary="Read one resumable private Simulator test session.",
    )
    def read_simulator_test_session(session_id: str) -> SimulatorExperimentSession:
        try:
            return service.load_session(session_id)
        except SimulatorExperimentSessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (SimulatorExperimentArtifactError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post(
        "/simulator-tests/sessions/{session_id}/questions/{question_id}/answer",
        response_model=SimulatorExperimentSession,
        summary="Save the human answer, then generate and save the matching Simulator answer.",
    )
    def answer_simulator_test_question(
        session_id: str,
        question_id: str,
        request: SubmitHumanAnswerRequest,
    ) -> SimulatorExperimentSession:
        try:
            return service.submit_human_answer(
                session_id=session_id,
                question_id=question_id,
                human_answer=request.human_answer.strip(),
            )
        except SimulatorExperimentSessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SimulatorExperimentStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except SimulatorServiceConfigurationError as exc:
            raise HTTPException(
                status_code=503,
                detail="Simulator LLM service is not configured.",
            ) from exc
        except (
            ReviewedMapNotFoundError,
            ReviewedGraphNotFoundError,
            ConfirmedProfileContextNotFoundError,
        ) as exc:
            raise HTTPException(status_code=424, detail=str(exc)) from exc
        except (
            ReviewedMapArtifactError,
            ReviewedGraphArtifactError,
            ConfirmedProfileContextArtifactError,
            SimulatorExperimentArtifactError,
            ValueError,
        ) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.put(
        "/simulator-tests/sessions/{session_id}/questions/{question_id}/self-evaluation",
        response_model=SimulatorExperimentSession,
        summary="Save the participant's comparison of their answer and the Simulator answer.",
    )
    def save_simulator_test_self_evaluation(
        session_id: str,
        question_id: str,
        evaluation: SimulatorSelfEvaluation,
    ) -> SimulatorExperimentSession:
        try:
            return service.save_self_evaluation(
                session_id=session_id,
                question_id=question_id,
                evaluation=evaluation,
            )
        except SimulatorExperimentSessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SimulatorExperimentStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (SimulatorExperimentArtifactError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post(
        "/simulator-tests/sessions/{session_id}/completion",
        response_model=SimulatorExperimentSession,
        summary="Complete one fully answered and self-evaluated Simulator test session.",
    )
    def complete_simulator_test_session(
        session_id: str,
    ) -> SimulatorExperimentSession:
        try:
            return service.complete_session(session_id)
        except SimulatorExperimentSessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SimulatorExperimentStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (SimulatorExperimentArtifactError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]
