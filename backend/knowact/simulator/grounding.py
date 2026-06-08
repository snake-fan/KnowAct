from pydantic import BaseModel, ConfigDict, Field

from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import DiagnosticQuestion, VisibleDialogueContext


class QuestionGroundingResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    grounded_node_ids: tuple[str, ...] = Field(default_factory=tuple)
    is_integrated_question: bool = False
    is_multiple_question: bool = False
    is_label_seeking: bool = False

    @property
    def has_grounding(self) -> bool:
        return bool(self.grounded_node_ids)


class RuleBasedQuestionGrounder:
    def ground(
        self,
        *,
        question: DiagnosticQuestion,
        graph: KnowledgeGraph,
        visible_dialogue_context: VisibleDialogueContext | None = None,
    ) -> QuestionGroundingResult:
        haystack = _normalize_for_matching(question.text)
        if visible_dialogue_context is not None:
            haystack = " ".join(
                (
                    haystack,
                    *(
                        _normalize_for_matching(turn.question.text)
                        for turn in visible_dialogue_context.turns[-1:]
                    ),
                )
            )

        grounded_node_ids: list[str] = []
        for node in graph.nodes:
            terms = [
                node.id,
                node.name,
                node.definition or "",
                node.diagnostic_goal or "",
                *node.diagnostic_signals,
            ]
            if any(_normalize_for_matching(term) in haystack for term in terms if term):
                grounded_node_ids.append(node.id)

        is_multiple_question = _looks_like_multiple_questions(question.text)
        return QuestionGroundingResult(
            grounded_node_ids=tuple(grounded_node_ids),
            is_integrated_question=len(grounded_node_ids) > 1 and not is_multiple_question,
            is_multiple_question=is_multiple_question,
            is_label_seeking=_looks_like_label_seeking(question.text),
        )


def _looks_like_multiple_questions(question_text: str) -> bool:
    return question_text.count("?") > 1


def _looks_like_label_seeking(question_text: str) -> bool:
    normalized = _normalize_for_matching(question_text)
    label_terms = (
        "mastery level",
        "evidence id",
        "state table",
        "knowledge map",
        "ground truth",
    )
    return any(term in normalized for term in label_terms)


def _normalize_for_matching(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else " " for character in value)
