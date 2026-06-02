import json
from textwrap import dedent

from backend.knowact.authoring.schemas import KnowledgeStateOutline
from backend.knowact.authoring.schemas import ConfirmedProfileContext
from backend.knowact.authoring.templates.common import (
    JSON_ONLY_RULES,
    MASTERY_SCALE,
    STOP_AFTER_JSON_RULES,
    TASK_DATA_BOUNDARY_RULES,
    render_sections,
)
from backend.knowact.core.evidence import EvidenceKind
from backend.knowact.core.graph import KnowledgeNode
from backend.knowact.core.map import MasteryLevel
from backend.knowact.llm.messages import ModelMessage, ModelMessageProfile, OPENAI_MESSAGE_PROFILE


def build_knowledge_state_outline_messages(
    *,
    profile_context: ConfirmedProfileContext,
    nodes: tuple[KnowledgeNode, ...],
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    allowed_mastery_levels = "\n".join(f"- {level.value}" for level in MasteryLevel)
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                dedent(
                    """
                    Role:
                    You are the Knowledge-State Outline Agent Step for candidate user-knowledge-map authoring.
                    """
                ).strip(),
                dedent(
                    """
                    Objective:
                    Draft one plausible synthetic user knowledge state for every supplied reviewed node.
                    Success means the outline covers the complete node set exactly once, uses only allowed mastery levels, and contains only node-level state fields.
                    """
                ).strip(),
                TASK_DATA_BOUNDARY_RULES,
                MASTERY_SCALE,
                dedent(
                    """
                    Task:
                    - Draft one plausible synthetic user knowledge state for every supplied reviewed node.
                    - Use the confirmed Profile Context only to keep the synthetic user coherent.
                    - Use reviewed_nodes_with_rubrics as the complete node set for this outline.
                    - Do not author evidence in this step.
                    """
                ).strip(),
                dedent(
                    """
                    Input boundary:
                    - confirmed_profile_context is person-level coherence data, not node-level mastery data.
                    - reviewed_nodes_with_rubrics is the complete reviewed node set and the only node/rubric input.
                    - Reviewed edges are intentionally not provided; do not ask for, infer, or include graph-edge data.
                    - Treat names, definitions, diagnostic goals, levels, diagnostic_signals, and simulator_behavior as rubric context for choosing plausible node states.
                    """
                ).strip(),
                dedent(
                    """
                    Process:
                    1. Read the confirmed Profile Context for background, prior experience, goals, and preferences.
                    2. For each reviewed node, inspect its definition, diagnostic_goal, L0-L5 rubric, diagnostic_signals, and simulator_behavior.
                    3. Assign one plausible mastery_level for the synthetic user on that node.
                    4. Add misconceptions only when a specific plausible misunderstanding follows from the profile and node rubric.
                    5. Add unknowns only when they clarify a real boundary, missing prerequisite, or uncertainty that later evidence authoring should support.
                    6. Check full node coverage and remove every field outside the allowed state object.
                    """
                ).strip(),
                dedent(
                    """
                    Decision rules:
                    - Keep each state node-level, not episode-level or whole-person-level.
                    - Do not force misconceptions or unknowns just to fill space.
                    - Do not make all nodes the same mastery level unless the profile and rubrics strongly justify it.
                    - If the profile is sparse, make conservative, coherent choices from the available profile fields and node rubrics.
                    - Do not output assumptions, rationales, confidence scores, evidence_refs, user_id, lifecycle kind, or edge-based consistency notes.
                    """
                ).strip(),
                dedent(
                    """
                    Return JSON with this exact top-level shape:
                    {
                      "states": [
                        {
                          "node_id": "node id from reviewed_nodes_with_rubrics",
                          "mastery_level": "one allowed mastery level",
                          "misconceptions": ["zero or more strings"],
                          "unknowns": ["zero or more strings"]
                        }
                      ]
                    }
                    """
                ).strip(),
                dedent(
                    """
                    Allowed output fields for each state object:
                    - node_id
                    - mastery_level
                    - misconceptions
                    - unknowns
                    """
                ).strip(),
                dedent(
                    """
                    Forbidden output:
                    - evidence_refs
                    - evidence ids
                    - evidence objects
                    - user identity
                    - lifecycle kind
                    - graph edges
                    - scores
                    - promotion metadata
                    - any field not listed in Allowed output fields
                    """
                ).strip(),
                dedent(
                    """
                    Node coverage:
                    - Every state.node_id must exactly match one node id from reviewed_nodes_with_rubrics.
                    - Return exactly one state object for every reviewed node.
                    - Do not omit reviewed nodes.
                    - Do not add nodes outside reviewed_nodes_with_rubrics.
                    """
                ).strip(),
                f"Allowed mastery_level values:\n{allowed_mastery_levels}",
                dedent(
                    """
                    Array rules:
                    - misconceptions must always be present, even when empty.
                    - unknowns must always be present, even when empty.
                    - Items must be nonblank strings.
                    - Do not repeat exact duplicate strings within one misconceptions or unknowns array.
                    - If an item needs quotation marks inside the text, escape them as valid JSON or rewrite without quotation marks.
                    """
                ).strip(),
                dedent(
                    """
                    Quality checks:
                    - Keep each state node-level, not episode-level.
                    - Do not force misconceptions or unknowns just to fill space.
                    - Use concise strings that help later evidence authoring and simulation.
                    """
                ).strip(),
                dedent(
                    """
                    Final check before output:
                    - Every reviewed node id appears exactly once.
                    - No unknown, duplicate, or missing node ids are present.
                    - Every mastery_level is one of the allowed values.
                    - misconceptions and unknowns are present arrays for every state.
                    - The response is exactly one JSON object with top-level key "states".
                    """
                ).strip(),
                STOP_AFTER_JSON_RULES,
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=_json_context(
                {
                    "confirmed_profile_context": profile_context.model_dump(mode="json"),
                    "reviewed_nodes_with_rubrics": [
                        node.model_dump(mode="json", exclude_none=True) for node in nodes
                    ],
                }
            ),
        ),
    )


def build_ground_truth_evidence_messages(
    *,
    profile_context: ConfirmedProfileContext,
    nodes: tuple[KnowledgeNode, ...],
    state_outlines: tuple[KnowledgeStateOutline, ...],
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    allowed_evidence_kinds = "\n".join(f"- {kind.value}" for kind in EvidenceKind)
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                dedent(
                    """
                    Role:
                    You are the Ground-Truth Evidence Authoring Agent Step for candidate user-knowledge-map authoring.
                    """
                ).strip(),
                dedent(
                    """
                    Objective:
                    Draft hidden simulator-support evidence for the supplied node batch only.
                    Success means every batch node receives enough concrete evidence for its target mastery level, and every evidence object stays inside the exact output schema.
                    """
                ).strip(),
                TASK_DATA_BOUNDARY_RULES,
                dedent(
                    """
                    Task:
                    - Return hidden simulator-support evidence for the supplied node batch only.
                    - Use the confirmed Profile Context only to keep the synthetic user coherent.
                    - Use batch_state_outlines as the source of each node's target mastery level.
                    """
                ).strip(),
                dedent(
                    """
                    Input boundary:
                    - confirmed_profile_context is person-level coherence data.
                    - batch_nodes_with_rubrics is the only node/rubric context available for this batch.
                    - batch_state_outlines is the only source for target mastery_level, misconceptions, and unknowns.
                    - Do not ask for, infer, or include other nodes, reviewed edges, complete-graph context, existing evidence ids, or promotion metadata.
                    """
                ).strip(),
                dedent(
                    """
                    Process:
                    1. Match every batch_state_outline to its node in batch_nodes_with_rubrics.
                    2. For each node, inspect mastery_level, misconceptions, unknowns, and the node rubric.
                    3. Draft enough hidden evidence records to meet the mastery-sensitive minimum for that node.
                    4. Choose the broad evidence_kind that best describes each signal's function.
                    5. Keep each signal concrete enough for a simulator to answer consistently.
                    6. Remove duplicate (evidence_kind, signal) pairs within each node.
                    """
                ).strip(),
                dedent(
                    """
                    Decision rules:
                    - Evidence is hidden-profile support for simulator behavior, not visible conversation data.
                    - Prefer signals that explain capabilities, limits, misconceptions, or uncertainty implied by the outline and profile.
                    - For L0-L1, misconception_trace, weak prior_answer, self_report, or background_fact can be useful when grounded in the synthetic profile.
                    - For L2-L3, include enough capability and boundary evidence to support partial but incomplete understanding.
                    - For L4-L5, use worked_example, strong prior_answer, or reflective self_report when plausible.
                    - Do not invent fine-grained evidence_kind values; put surface detail in signal.
                    """
                ).strip(),
                dedent(
                    """
                    Return JSON with this exact top-level shape:
                    {
                      "evidence": [
                        {
                          "node_id": "node id from this batch",
                          "evidence_kind": "one allowed value",
                          "signal": "specific hidden evidence signal"
                        }
                      ]
                    }
                    """
                ).strip(),
                dedent(
                    """
                    Allowed output fields for each evidence object:
                    - node_id
                    - evidence_kind
                    - signal
                    """
                ).strip(),
                dedent(
                    """
                    Forbidden output:
                    - evidence ids
                    - evidence_type
                    - visibility
                    - turn_id
                    - lifecycle kind
                    - user identity
                    - mastery updates
                    - graph edges
                    - scores
                    - promotion metadata
                    - any field not listed in Allowed output fields
                    """
                ).strip(),
                dedent(
                    """
                    Node boundary:
                    - Every evidence.node_id must exactly match one node_id from batch_nodes_with_rubrics.
                    - Do not reference nodes outside this batch.
                    - Do not infer or include evidence for neighboring graph nodes.
                    """
                ).strip(),
                dedent(
                    """
                    Evidence count per node:
                    For each node, inspect its target mastery_level from batch_state_outlines:
                    - L0-L1: at least 1 evidence record
                    - L2-L3: at least 2 evidence records
                    - L4-L5: at least 1 evidence record
                    """
                ).strip(),
                f"Allowed evidence_kind values:\n{allowed_evidence_kinds}",
                dedent(
                    """
                    evidence_kind is a functional role, not a surface format:
                    - Use prior_answer for answer-like evidence such as quiz answers, written responses, verbal explanations, discussion comments, multiple-choice answers, true/false answers, or theorem references.
                    - Use worked_example for evidence where the user applies a concept in an example, calculation, code sketch, model-selection proposal, diagnostic exercise, pipeline description, residual-plot interpretation, or example analysis.
                    - Use self_report for the user's own claims about confidence, experience, goals, preferences, or uncertainty.
                    - Use misconception_trace for evidence of a wrong belief, boundary confusion, faulty assumption, or repeated error pattern.
                    - Use background_fact for stable profile facts or prior exposure that support simulator behavior.

                    Put the specific surface form in signal; never invent fine-grained evidence_kind values such as quiz_answer, verbal_explanation, discussion_comment, written_response, concept_explanation, residual_plot_interpretation, or theorem_reference.
                    """
                ).strip(),
                dedent(
                    """
                    Quality checks:
                    - Avoid exactly duplicated (evidence_kind, signal) pairs for one node.
                    - Make each signal concrete enough for a simulator to answer consistently.
                    - Keep signals hidden-profile evidence, not visible interaction observations.
                    """
                ).strip(),
                dedent(
                    """
                    Final check before output:
                    - Every evidence.node_id belongs to batch_nodes_with_rubrics.
                    - Every node meets its required evidence count.
                    - Every evidence_kind is one allowed value.
                    - No evidence ids, visibility, evidence_type, turn_id, user identity, lifecycle kind, scores, or extra fields are present.
                    - The response is exactly one JSON object with top-level key "evidence".
                    """
                ).strip(),
                STOP_AFTER_JSON_RULES,
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=_json_context(
                {
                    "confirmed_profile_context": profile_context.model_dump(mode="json"),
                    "batch_nodes_with_rubrics": [
                        node.model_dump(mode="json", exclude_none=True) for node in nodes
                    ],
                    "batch_state_outlines": [
                        state.model_dump(mode="json") for state in state_outlines
                    ],
                }
            ),
        ),
    )


def _json_context(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)
