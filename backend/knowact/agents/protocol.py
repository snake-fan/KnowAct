from typing import Protocol

from backend.knowact.agents.tools import WorkingMapNodeAssessmentUpdate
from backend.knowact.agents.working_map import AgentWorkingKnowledgeMap
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import DiagnosticQuestion, VisibleDialogueContext


class TestedAgent(Protocol):
    """Protocol implemented by baseline and experimental tested agents."""

    def update_after_visible_answer(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
    ) -> tuple[WorkingMapNodeAssessmentUpdate, ...]:
        """Return working-map updates after the latest visible simulator answer."""

    def choose_next_question(
        self,
        *,
        graph: KnowledgeGraph,
        working_map: AgentWorkingKnowledgeMap,
        visible_dialogue_context: VisibleDialogueContext,
    ) -> DiagnosticQuestion:
        """Return the next diagnostic question."""
