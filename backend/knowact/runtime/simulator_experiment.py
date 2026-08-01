from collections.abc import Callable
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import threading
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.knowact.authoring.map_authoring_output import (
    CandidateMapArtifactError,
    CandidateMapAuthoringRunLog,
    read_candidate_map_run,
)
from backend.knowact.core.evidence import (
    EvidenceKind,
    EvidenceRecord,
    EvidenceType,
    EvidenceVisibility,
)
from backend.knowact.core.interaction import DiagnosticQuestion
from backend.knowact.core.map import (
    KnowledgeMap,
    KnowledgeMapKind,
    MapManifest,
    MasteryLevel,
    UserKnowledgeState,
)
from backend.knowact.core.simulator_experiment import (
    ParticipantMapStateRevision,
    SimulatorExperimentClientProvider,
    SimulatorExperimentLanguage,
    SimulatorExperimentQuestionResult,
    SimulatorSelfEvaluation,
    SimulatorExperimentSession,
    SimulatorExperimentStatus,
)
from backend.knowact.simulator.llm_service import build_simulator_service_for_provider
from backend.knowact.simulator.service import SimulatorService
from backend.knowact.simulator.turn import (
    SimulatorTurnOptions,
    SimulatorTurnRequest,
)
from backend.knowact.storage.profile_contexts import load_confirmed_profile_context
from backend.knowact.storage.reviewed_graphs import load_reviewed_graph
from backend.knowact.storage.reviewed_maps import (
    ReviewedMapPromotion,
    load_reviewed_map,
    publish_reviewed_map,
)
from backend.knowact.storage.simulator_experiments import (
    create_simulator_experiment_session,
    list_question_banks,
    list_simulator_experiment_sessions,
    load_question_bank,
    load_simulator_experiment_session,
    save_simulator_experiment_session,
    write_private_map_review,
)
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.map import validate_knowledge_map


SimulatorExperimentServiceFactory = Callable[
    [SimulatorExperimentClientProvider, Path],
    SimulatorService,
]


class ParticipantMapConfirmationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_domain: str
    candidate_map_run_id: str
    map: KnowledgeMap
    map_manifest: MapManifest


class SimulatorExperimentStateError(ValueError):
    """Raised when a Simulator experiment operation violates session state."""


class SimulatorExperimentService:
    def __init__(
        self,
        *,
        workspace_root: Path,
        simulator_service_factory: SimulatorExperimentServiceFactory | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._simulator_service_factory = simulator_service_factory or (
            lambda provider, root: build_simulator_service_for_provider(
                workspace_root=root,
                client_provider=provider,
            )
        )
        self._simulator_services: dict[SimulatorExperimentClientProvider, SimulatorService] = {}
        self._session_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def list_question_banks(self):
        return list_question_banks(workspace_root=self._workspace_root)

    def list_sessions(self):
        return list_simulator_experiment_sessions(workspace_root=self._workspace_root)

    def load_session(self, session_id: str) -> SimulatorExperimentSession:
        return load_simulator_experiment_session(
            workspace_root=self._workspace_root,
            session_id=session_id,
        )

    def confirm_participant_map(
        self,
        *,
        benchmark_domain: str,
        candidate_map_run_id: str,
        map_id: str,
        revisions: tuple[ParticipantMapStateRevision, ...],
    ) -> ParticipantMapConfirmationResult:
        candidate_map, artifact_paths = read_candidate_map_run(
            workspace_root=self._workspace_root,
            benchmark_domain=benchmark_domain,
            run_id=candidate_map_run_id,
        )
        run_log = _read_candidate_map_run_log(
            workspace_root=self._workspace_root,
            workflow_log_uri=artifact_paths.workflow_log_uri,
        )
        if run_log.run_id != candidate_map_run_id:
            raise CandidateMapArtifactError(
                "Candidate map workflow log run_id does not match artifact path"
            )
        if run_log.benchmark_domain != benchmark_domain:
            raise CandidateMapArtifactError(
                "Candidate map workflow log benchmark_domain does not match artifact path"
            )
        if run_log.user_id != candidate_map.user_id:
            raise CandidateMapArtifactError(
                "Candidate map user_id does not match workflow log"
            )

        graph_artifacts = load_reviewed_graph(
            workspace_root=self._workspace_root,
            benchmark_domain=benchmark_domain,
            version=run_log.graph_version,
        )
        load_confirmed_profile_context(
            workspace_root=self._workspace_root,
            benchmark_domain=benchmark_domain,
            user_id=run_log.user_id,
        )
        reviewed_map = _build_participant_reviewed_map(
            map_id=map_id,
            user_id=run_log.user_id,
            candidate_map=candidate_map,
            revisions=revisions,
            graph=graph_artifacts.graph,
        )
        validate_knowledge_map(reviewed_map, graph_artifacts.graph)
        _validate_simulator_evidence_minimums(reviewed_map)

        manifest = MapManifest(
            map_id=map_id,
            user_id=run_log.user_id,
            benchmark_domain=benchmark_domain,
            graph_version=run_log.graph_version,
            promoted_from_candidate_run=candidate_map_run_id,
        )
        promotion = publish_reviewed_map(
            workspace_root=self._workspace_root,
            benchmark_domain=benchmark_domain,
            map_id=map_id,
            manifest=manifest,
            knowledge_map=reviewed_map,
        )
        _write_participant_map_review(
            workspace_root=self._workspace_root,
            promotion=promotion,
            candidate_map_run_id=candidate_map_run_id,
            candidate_map=candidate_map,
            revisions=revisions,
        )
        return ParticipantMapConfirmationResult(
            benchmark_domain=benchmark_domain,
            candidate_map_run_id=candidate_map_run_id,
            map=promotion.knowledge_map,
            map_manifest=promotion.manifest,
        )

    def create_session(
        self,
        *,
        participant_code: str,
        benchmark_domain: str,
        map_id: str,
        question_bank_id: str,
        language: SimulatorExperimentLanguage,
        simulator_client_provider: SimulatorExperimentClientProvider,
        sampling_seed: int | None = None,
        session_id: str | None = None,
    ) -> SimulatorExperimentSession:
        reviewed_map = load_reviewed_map(
            workspace_root=self._workspace_root,
            benchmark_domain=benchmark_domain,
            map_id=map_id,
        )
        load_confirmed_profile_context(
            workspace_root=self._workspace_root,
            benchmark_domain=benchmark_domain,
            user_id=reviewed_map.manifest.user_id,
        )
        bank = load_question_bank(
            workspace_root=self._workspace_root,
            bank_id=question_bank_id,
        )
        if bank.benchmark_domain != benchmark_domain:
            raise SimulatorExperimentStateError(
                "Question bank benchmark_domain does not match reviewed map"
            )
        if len(bank.questions) < 20:
            raise SimulatorExperimentStateError(
                "Simulator experiment question bank must contain at least 20 questions"
            )

        resolved_session_id = session_id or f"simtest_{uuid4().hex[:16]}"
        resolved_seed = (
            sampling_seed
            if sampling_seed is not None
            else _stable_sampling_seed(resolved_session_id)
        )
        sampled_questions = random.Random(resolved_seed).sample(list(bank.questions), 20)
        session = SimulatorExperimentSession(
            session_id=resolved_session_id,
            participant_code=participant_code,
            status=SimulatorExperimentStatus.IN_PROGRESS,
            benchmark_domain=benchmark_domain,
            graph_version=reviewed_map.manifest.graph_version,
            profile_context_user_id=reviewed_map.manifest.user_id,
            map_id=map_id,
            question_bank_id=bank.bank_id,
            question_bank_version=bank.version,
            language=language,
            simulator_client_provider=simulator_client_provider,
            sampling_seed=resolved_seed,
            questions=tuple(
                SimulatorExperimentQuestionResult(
                    question_id=question.question_id,
                    target_concept=question.target_concept,
                    question_type=question.question_type,
                    prompts=question.prompts,
                    selected_prompt=question.prompts.for_language(language),
                    reviewed_target_node_ids=question.reviewed_target_node_ids,
                )
                for question in sampled_questions
            ),
            created_at=datetime.now(timezone.utc),
        )
        create_simulator_experiment_session(
            workspace_root=self._workspace_root,
            session=session,
        )
        return session

    def submit_human_answer(
        self,
        *,
        session_id: str,
        question_id: str,
        human_answer: str,
    ) -> SimulatorExperimentSession:
        with self._session_lock(session_id):
            session = self.load_session(session_id)
            _ensure_session_in_progress(session)
            question_index = _question_index(session, question_id)
            question = session.questions[question_index]
            if question.self_evaluation is not None:
                raise SimulatorExperimentStateError(
                    "Evaluated questions cannot be answered again"
                )
            if question.human_answer is not None and question.human_answer != human_answer:
                raise SimulatorExperimentStateError(
                    "Human answer is immutable after Simulator generation starts"
                )

            question_with_human_answer = question.model_copy(
                update={
                    "human_answer": human_answer,
                    "simulator_error": None,
                }
            )
            session = _replace_question(
                session,
                question_index,
                question_with_human_answer,
            )
            save_simulator_experiment_session(
                workspace_root=self._workspace_root,
                session=session,
            )

            if question.simulator_answer is not None:
                return session

            try:
                simulator_response = self._simulator_service(
                    session.simulator_client_provider
                ).answer_turn(
                    SimulatorTurnRequest(
                        benchmark_domain=session.benchmark_domain,
                        map_id=session.map_id,
                        client_provider=session.simulator_client_provider,
                        question=DiagnosticQuestion(
                            question_id=question.question_id,
                            text=question.selected_prompt,
                        ),
                        turn_options=SimulatorTurnOptions(include_debug_trace=True),
                    )
                )
            except Exception as exc:
                failed_question = question_with_human_answer.model_copy(
                    update={"simulator_error": type(exc).__name__}
                )
                failed_session = _replace_question(
                    session,
                    question_index,
                    failed_question,
                )
                save_simulator_experiment_session(
                    workspace_root=self._workspace_root,
                    session=failed_session,
                )
                raise

            answered_question = question_with_human_answer.model_copy(
                update={
                    "simulator_answer": simulator_response.answer.text,
                    "observation_kind": simulator_response.observation.kind.value,
                    "warning_codes": tuple(
                        warning.code.value for warning in simulator_response.warnings
                    ),
                    "debug_trace_id": simulator_response.debug_trace_id,
                    "simulator_error": None,
                }
            )
            answered_session = _replace_question(
                session,
                question_index,
                answered_question,
            )
            save_simulator_experiment_session(
                workspace_root=self._workspace_root,
                session=answered_session,
            )
            return answered_session

    def save_self_evaluation(
        self,
        *,
        session_id: str,
        question_id: str,
        evaluation: SimulatorSelfEvaluation,
    ) -> SimulatorExperimentSession:
        with self._session_lock(session_id):
            session = self.load_session(session_id)
            _ensure_session_in_progress(session)
            question_index = _question_index(session, question_id)
            question = session.questions[question_index]
            if question.human_answer is None or question.simulator_answer is None:
                raise SimulatorExperimentStateError(
                    "Both human and Simulator answers are required before self-evaluation"
                )
            evaluated_question = question.model_copy(
                update={"self_evaluation": evaluation}
            )
            updated_session = _replace_question(
                session,
                question_index,
                evaluated_question,
            )
            save_simulator_experiment_session(
                workspace_root=self._workspace_root,
                session=updated_session,
            )
            return updated_session

    def complete_session(self, session_id: str) -> SimulatorExperimentSession:
        with self._session_lock(session_id):
            session = self.load_session(session_id)
            _ensure_session_in_progress(session)
            incomplete_question_ids = tuple(
                question.question_id
                for question in session.questions
                if question.human_answer is None
                or question.simulator_answer is None
                or question.self_evaluation is None
            )
            if incomplete_question_ids:
                raise SimulatorExperimentStateError(
                    "All 20 question pairs require human answers, Simulator answers, "
                    "and self-evaluations before completion"
                )
            completed_session = session.model_copy(
                update={
                    "status": SimulatorExperimentStatus.COMPLETED,
                    "completed_at": datetime.now(timezone.utc),
                }
            )
            save_simulator_experiment_session(
                workspace_root=self._workspace_root,
                session=completed_session,
            )
            return completed_session

    def _simulator_service(
        self,
        provider: SimulatorExperimentClientProvider,
    ) -> SimulatorService:
        service = self._simulator_services.get(provider)
        if service is None:
            service = self._simulator_service_factory(provider, self._workspace_root)
            self._simulator_services[provider] = service
        return service

    def _session_lock(self, session_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._session_locks.setdefault(session_id, threading.Lock())


def _read_candidate_map_run_log(
    *,
    workspace_root: Path,
    workflow_log_uri: str,
) -> CandidateMapAuthoringRunLog:
    try:
        with (workspace_root / workflow_log_uri).open(encoding="utf-8") as handle:
            run_log = CandidateMapAuthoringRunLog.model_validate(json.load(handle))
        if run_log.status != "succeeded":
            raise ValueError("Candidate map run did not succeed")
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        raise CandidateMapArtifactError(str(exc)) from exc
    return run_log


def _build_participant_reviewed_map(
    *,
    map_id: str,
    user_id: str,
    candidate_map: KnowledgeMap,
    revisions: tuple[ParticipantMapStateRevision, ...],
    graph,
) -> KnowledgeMap:
    revision_by_node_id = {revision.node_id: revision for revision in revisions}
    if len(revision_by_node_id) != len(revisions):
        raise KnowActValidationError(
            "Participant map review contains duplicate node revisions"
        )
    if set(revision_by_node_id) != graph.node_ids:
        missing = sorted(graph.node_ids - set(revision_by_node_id))
        unknown = sorted(set(revision_by_node_id) - graph.node_ids)
        raise KnowActValidationError(
            f"Participant map review must cover the reviewed graph exactly; "
            f"missing={missing}, unknown={unknown}"
        )
    if candidate_map.user_id != user_id:
        raise KnowActValidationError(
            "Candidate map user_id does not match participant review identity"
        )

    states: list[UserKnowledgeState] = []
    evidence: list[EvidenceRecord] = []
    for node in graph.nodes:
        revision = revision_by_node_id[node.id]
        node_evidence = _participant_review_evidence(
            map_id=map_id,
            node=node,
            revision=revision,
        )
        evidence.extend(node_evidence)
        states.append(
            UserKnowledgeState(
                node_id=node.id,
                mastery_level=revision.mastery_level,
                evidence_refs=tuple(record.id for record in node_evidence),
                misconceptions=revision.misconceptions,
                unknowns=revision.unknowns,
            )
        )

    return KnowledgeMap(
        user_id=user_id,
        kind=KnowledgeMapKind.GROUND_TRUTH,
        states=tuple(states),
        evidence=tuple(evidence),
    )


def _participant_review_evidence(
    *,
    map_id: str,
    node,
    revision: ParticipantMapStateRevision,
) -> tuple[EvidenceRecord, ...]:
    rubric_boundary = (
        node.levels.get(revision.mastery_level.value)
        or node.diagnostic_goal
        or node.definition
        or node.name
    )
    signals = [
        "Participant self-review confirmed this capability boundary: "
        f"{rubric_boundary}"
    ]
    if revision.review_note:
        signals[0] += f" Review note: {revision.review_note}"
    if revision.mastery_level in (MasteryLevel.L2, MasteryLevel.L3):
        if revision.misconceptions:
            signals.append(
                "Participant self-review identified this misconception: "
                + "; ".join(revision.misconceptions)
            )
        elif revision.unknowns:
            signals.append(
                "Participant self-review identified this unresolved boundary: "
                + "; ".join(revision.unknowns)
            )
        else:
            signals.append(
                "Participant self-review confirmed partial knowledge with limits "
                "beyond the described capability boundary."
            )

    return tuple(
        EvidenceRecord(
            id=f"ev_{map_id}_{node.id}_{ordinal:02d}",
            node_id=node.id,
            evidence_type=EvidenceType.GROUND_TRUTH_PROFILE,
            evidence_kind=EvidenceKind.SELF_REPORT,
            visibility=EvidenceVisibility.SIMULATOR_ONLY,
            signal=signal,
            turn_id=None,
        )
        for ordinal, signal in enumerate(signals, start=1)
    )


def _validate_simulator_evidence_minimums(knowledge_map: KnowledgeMap) -> None:
    for state in knowledge_map.states:
        required = 2 if state.mastery_level in (MasteryLevel.L2, MasteryLevel.L3) else 1
        if len(state.evidence_refs) < required:
            raise KnowActValidationError(
                f"Ground-truth state for node {state.node_id} requires at least "
                f"{required} simulator-only evidence records"
            )


def _write_participant_map_review(
    *,
    workspace_root: Path,
    promotion: ReviewedMapPromotion,
    candidate_map_run_id: str,
    candidate_map: KnowledgeMap,
    revisions: tuple[ParticipantMapStateRevision, ...],
) -> None:
    write_private_map_review(
        workspace_root=workspace_root,
        map_id=promotion.manifest.map_id,
        payload={
            "schema_version": "knowact.participant_map_review.v1",
            "candidate_map_run_id": candidate_map_run_id,
            "map_manifest": promotion.manifest.model_dump(mode="json"),
            "candidate_states": [
                state.model_dump(mode="json") for state in candidate_map.states
            ],
            "participant_revisions": [
                revision.model_dump(mode="json") for revision in revisions
            ],
            "confirmed_map": promotion.knowledge_map.model_dump(mode="json"),
        },
    )


def _stable_sampling_seed(session_id: str) -> int:
    digest = hashlib.sha256(session_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def _ensure_session_in_progress(session: SimulatorExperimentSession) -> None:
    if session.status != SimulatorExperimentStatus.IN_PROGRESS:
        raise SimulatorExperimentStateError(
            f"Simulator experiment session {session.session_id} is already completed"
        )


def _question_index(
    session: SimulatorExperimentSession,
    question_id: str,
) -> int:
    for index, question in enumerate(session.questions):
        if question.question_id == question_id:
            return index
    raise SimulatorExperimentStateError(
        f"Question {question_id} is not part of session {session.session_id}"
    )


def _replace_question(
    session: SimulatorExperimentSession,
    question_index: int,
    question: SimulatorExperimentQuestionResult,
) -> SimulatorExperimentSession:
    questions = list(session.questions)
    questions[question_index] = question
    return session.model_copy(update={"questions": tuple(questions)})
