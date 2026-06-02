import json
from textwrap import dedent

from backend.knowact.authoring.schemas import KnowledgeStateOutline
from backend.knowact.authoring.schemas import ConfirmedProfileContext
from backend.knowact.authoring.templates.common import JSON_ONLY_RULES, render_sections
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
                "You are the Knowledge-State Outline Agent Step.",
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
                "You are the Ground-Truth Evidence Authoring Agent Step.",
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
