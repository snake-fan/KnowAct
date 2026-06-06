from pydantic import BaseModel, ConfigDict, Field

from backend.knowact.core.evidence import EvidenceRecord, EvidenceVisibility
from backend.knowact.core.graph import KnowledgeGraph, KnowledgeNode
from backend.knowact.core.interaction import VisibleDialogueContext
from backend.knowact.core.map import KnowledgeMap, UserKnowledgeState
from backend.knowact.simulator.grounding import QuestionGroundingResult


class GroundedSimulatorNodeContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node: KnowledgeNode
    state: UserKnowledgeState
    simulator_only_evidence: tuple[EvidenceRecord, ...] = Field(default_factory=tuple)


class SimulatorTurnContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_domain: str
    map_id: str
    graph_version: str
    user_id: str
    grounded_nodes: tuple[GroundedSimulatorNodeContext, ...]
    visible_dialogue_context: VisibleDialogueContext | None = None


class SimulatorContextBuilder:
    def build(
        self,
        *,
        benchmark_domain: str,
        map_id: str,
        graph_version: str,
        user_id: str,
        graph: KnowledgeGraph,
        knowledge_map: KnowledgeMap,
        grounding: QuestionGroundingResult,
        visible_dialogue_context: VisibleDialogueContext | None = None,
    ) -> SimulatorTurnContext:
        nodes_by_id = {node.id: node for node in graph.nodes}
        states_by_node_id = knowledge_map.state_by_node_id
        evidence_by_id = {evidence.id: evidence for evidence in knowledge_map.evidence}
        grounded_contexts: list[GroundedSimulatorNodeContext] = []
        for node_id in grounding.grounded_node_ids:
            node = nodes_by_id[node_id]
            state = states_by_node_id[node_id]
            simulator_only_evidence = tuple(
                evidence
                for evidence_id in state.evidence_refs
                if (evidence := evidence_by_id.get(evidence_id)) is not None
                and evidence.node_id == node_id
                and evidence.visibility == EvidenceVisibility.SIMULATOR_ONLY
            )
            grounded_contexts.append(
                GroundedSimulatorNodeContext(
                    node=node,
                    state=state,
                    simulator_only_evidence=simulator_only_evidence,
                )
            )

        return SimulatorTurnContext(
            benchmark_domain=benchmark_domain,
            map_id=map_id,
            graph_version=graph_version,
            user_id=user_id,
            grounded_nodes=tuple(grounded_contexts),
            visible_dialogue_context=visible_dialogue_context,
        )
