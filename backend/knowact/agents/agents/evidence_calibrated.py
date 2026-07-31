from __future__ import annotations

import json
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from backend.knowact.agents.base import BaseTestedAgent
from backend.knowact.agents.belief import MasteryBelief, MasteryLikelihood
from backend.knowact.agents.protocol import (
    AskDiagnosticQuestionDecision,
    DecisionPhase,
    DecisionPhaseContext,
    DiagnosticUtilityTrace,
    FinalizeReconstructionDecision,
    TestedAgentDecision,
)
from backend.knowact.agents.question_selection import (
    DiagnosticCandidate,
    DiagnosticCandidateError,
    DiagnosticUtilityWeights,
    select_diagnostic_candidate,
)
from backend.knowact.agents.templates.evidence_calibrated import (
    build_diagnostic_candidate_messages,
    build_evidence_likelihood_messages,
)
from backend.knowact.agents.tools import WorkingMapNodeAssessmentUpdate
from backend.knowact.agents.working_map import (
    AgentWorkingKnowledgeMap,
    AssessedMasteryLevel,
    DiagnosticConfidence,
)
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import DiagnosticQuestion, VisibleDialogueContext
from backend.knowact.llm.client import ModelClient, ModelClientError
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessageProfile


class EvidenceCalibratedLLMTestedAgent(BaseTestedAgent):
    """LLM evidence interpretation with deterministic belief/action decisions."""

    def __init__(
        self,
        *,
        model_client: ModelClient,
        temperature: float | None = None,
        commitment_threshold: float = 0.35,
        utility_weights: DiagnosticUtilityWeights | None = None,
    ) -> None:
        if not 0.0 <= commitment_threshold <= 1.0:
            raise ValueError("commitment_threshold must be between 0 and 1")
        self._model_client = model_client
        self._temperature = temperature
        self._commitment_threshold = commitment_threshold
        self._utility_weights = utility_weights or DiagnosticUtilityWeights()

    def assess_after_visible_answer(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> tuple[WorkingMapNodeAssessmentUpdate, ...]:
        raw_output = self._model_client.complete(
            messages=build_evidence_likelihood_messages(
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=decision_context,
                message_profile=_message_profile_for(self._model_client),
            ),
            temperature=self._temperature,
        )
        evidence = parse_evidence_likelihood_output(raw_output)
        _validate_evidence_updates(
            evidence.updates,
            graph=graph,
            visible_dialogue_context=visible_dialogue_context,
        )
        states = working_map.assessment_by_node_id
        updates: list[WorkingMapNodeAssessmentUpdate] = []
        for item in evidence.updates:
            current = states[item.node_id]
            prior = current.mastery_belief or MasteryBelief.from_categorical_state(
                assessed_mastery_level=current.assessed_mastery_level.value,
                diagnostic_confidence=current.diagnostic_confidence.value,
            )
            posterior = prior.bayes_update(item.answer_likelihood)
            mastery, confidence = posterior.project(
                commitment_threshold=self._commitment_threshold
            )
            note = item.observed_behavior
            if item.contradiction:
                note = f"Contradictory visible evidence: {note}"
            updates.append(
                WorkingMapNodeAssessmentUpdate(
                    node_id=item.node_id,
                    assessed_mastery_level=AssessedMasteryLevel(mastery),
                    diagnostic_confidence=DiagnosticConfidence(confidence),
                    assessment_note=note,
                    supporting_turn_ids=_stable_union(
                        current.supporting_turn_ids,
                        item.supporting_turn_ids,
                    ),
                    mastery_belief=posterior,
                )
            )
        return tuple(updates)

    def decide_next_action(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> TestedAgentDecision:
        if (
            decision_context.phase == DecisionPhase.FORCED_FINALIZATION
            or decision_context.remaining_diagnostic_turns == 0
        ):
            return super().decide_next_action(
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=decision_context,
            )

        raw_output = self._model_client.complete(
            messages=build_diagnostic_candidate_messages(
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=visible_dialogue_context,
                decision_context=decision_context,
                message_profile=_message_profile_for(self._model_client),
            ),
            temperature=self._temperature,
        )
        proposal = parse_diagnostic_candidate_output(raw_output)
        if proposal.action == "finalize_reconstruction":
            return FinalizeReconstructionDecision(reason=proposal.reason)

        asked_question_ids = {
            turn.question.question_id
            for turn in visible_dialogue_context.turns
            if turn.question.question_id is not None
        }
        try:
            selected = select_diagnostic_candidate(
                proposal.candidates,
                graph=graph,
                asked_question_ids=asked_question_ids,
                weights=self._utility_weights,
            )
        except DiagnosticCandidateError as exc:
            raise ModelClientError(
                "Evidence-calibrated agent returned invalid diagnostic candidates"
            ) from exc
        return AskDiagnosticQuestionDecision(
            question=selected.candidate.question,
            diagnostic_plan=selected.candidate.diagnostic_plan.model_copy(
                update={
                    "utility_trace": DiagnosticUtilityTrace(
                        estimated_information_gain=(
                            selected.candidate.estimated_information_gain
                        ),
                        coverage_gain=selected.candidate.coverage_gain,
                        graph_leverage=selected.candidate.graph_leverage,
                        redundancy=selected.candidate.redundancy,
                        complexity=selected.candidate.complexity,
                        outcome_model_confidence=(
                            selected.candidate.outcome_model_confidence
                        ),
                        selected_utility=selected.utility,
                    )
                }
            ),
        )

    def select_diagnostic_question(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
        decision_context: DecisionPhaseContext,
    ) -> DiagnosticQuestion | None:
        decision = self.decide_next_action(
            graph=graph,
            working_map=working_map,
            visible_dialogue_context=visible_dialogue_context,
            decision_context=decision_context,
        )
        if isinstance(decision, FinalizeReconstructionDecision):
            return None
        return decision.question


class EvidenceLikelihoodUpdate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    answer_likelihood: MasteryLikelihood
    observed_behavior: str
    supporting_turn_ids: tuple[str, ...] = Field(min_length=1)
    contradiction: bool = False

    @field_validator("node_id", "observed_behavior")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("supporting_turn_ids")
    @classmethod
    def _turn_ids_must_be_unique_and_nonblank(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if any(not turn_id.strip() for turn_id in value):
            raise ValueError("supporting turn ids must not be blank")
        if len(value) != len(set(value)):
            raise ValueError("supporting turn ids must be unique")
        return value


class EvidenceLikelihoodOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    updates: tuple[EvidenceLikelihoodUpdate, ...] = ()


class DiagnosticCandidateOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: Literal["ask_diagnostic_question", "finalize_reconstruction"]
    candidates: tuple[DiagnosticCandidate, ...] = ()
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def _optional_reason_must_not_be_blank(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def _action_matches_candidates(self) -> Self:
        if self.action == "ask_diagnostic_question" and len(self.candidates) < 3:
            raise ValueError("ask action requires at least three candidates")
        if self.action == "finalize_reconstruction" and self.candidates:
            raise ValueError("finalize action must not include candidates")
        return self


def parse_evidence_likelihood_output(raw_output: str) -> EvidenceLikelihoodOutput:
    return _parse_model_output(
        raw_output,
        model=EvidenceLikelihoodOutput,
        output_name="evidence likelihoods",
    )


def parse_diagnostic_candidate_output(raw_output: str) -> DiagnosticCandidateOutput:
    return _parse_model_output(
        raw_output,
        model=DiagnosticCandidateOutput,
        output_name="diagnostic candidates",
    )


def _validate_evidence_updates(
    updates: tuple[EvidenceLikelihoodUpdate, ...],
    *,
    graph: KnowledgeGraph,
    visible_dialogue_context: VisibleDialogueContext,
) -> None:
    node_ids = [update.node_id for update in updates]
    if len(node_ids) != len(set(node_ids)):
        raise ModelClientError(
            "Evidence-calibrated agent returned duplicate node evidence"
        )
    unknown_node_ids = set(node_ids) - graph.node_ids
    if unknown_node_ids:
        raise ModelClientError(
            "Evidence-calibrated agent evidence references unknown graph nodes"
        )
    visible_turn_ids = {
        turn.turn_id
        for turn in visible_dialogue_context.turns
        if turn.turn_id is not None
    }
    cited_turn_ids = {
        turn_id for update in updates for turn_id in update.supporting_turn_ids
    }
    if cited_turn_ids - visible_turn_ids:
        raise ModelClientError(
            "Evidence-calibrated agent evidence references unknown visible turns"
        )


def _parse_model_output(raw_output: str, *, model, output_name: str):
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ModelClientError(
            f"Evidence-calibrated agent returned invalid JSON for {output_name}"
        ) from exc
    if not isinstance(payload, dict):
        raise ModelClientError(
            f"Evidence-calibrated agent returned a non-object for {output_name}"
        )
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ModelClientError(
            f"Evidence-calibrated agent returned invalid {output_name}"
        ) from exc


def _stable_union(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*left, *right)))


def _message_profile_for(model_client: ModelClient) -> ModelMessageProfile:
    return getattr(model_client, "message_profile", OPENAI_MESSAGE_PROFILE)
