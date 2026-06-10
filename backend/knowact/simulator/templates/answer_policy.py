from textwrap import dedent
from typing import Any

from backend.knowact.llm.messages import (
    ModelMessage,
    ModelMessageProfile,
    OPENAI_MESSAGE_PROFILE,
)
from backend.knowact.simulator.context_builder import SimulatorTurnContext
from backend.knowact.simulator.grounding import QuestionGroundingResult
from backend.knowact.simulator.templates.common import (
    SIMULATOR_CONTEXT,
    SIMULATOR_JSON_ONLY_RULES,
    SIMULATOR_STOP_AFTER_JSON_RULES,
    SIMULATOR_TASK_DATA_BOUNDARY_RULES,
    dump_json_payload,
    render_sections,
)


def build_answer_policy_messages(
    *,
    question_text: str,
    simulator_context: SimulatorTurnContext,
    grounding: QuestionGroundingResult,
    fallback_intent: Any,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                dedent(
                    """
                    Role:
                    You are the Simulator Answer Policy Agent for KnowAct v1.
                    You derive one structured answer-content decision from the
                    grounded diagnostic situation. You do not write the final
                    visible answer.
                    """
                ).strip(),
                dedent(
                    """
                    Objective:
                    Analyze the directly grounded node rubrics, hidden map state,
                    grounded simulator-only evidence, grounding flags, and visible
                    dialogue. Return one downstream-safe Simulator Answer Intent
                    that directs answer generation without exposing hidden
                    benchmark artifacts.
                    """
                ).strip(),
                SIMULATOR_CONTEXT,
                SIMULATOR_TASK_DATA_BOUNDARY_RULES,
                dedent(
                    """
                    Inputs:
                    - question_text: the current diagnostic question.
                    - grounding: visible-graph grounding flags and grounded node ids.
                    - grounded_nodes: directly grounded node rubrics, simulator
                      behavior, hidden user state, and simulator-only evidence.
                    - visible_dialogue_turns: prior visible dialogue for follow-up
                      interpretation only.
                    - fallback_intent: deterministic baseline shape you may improve.
                    """
                ).strip(),
                dedent(
                    """
                    Process:
                    1. Decide response_mode: answer, clarification, label_refusal,
                       non_answer, or safe_non_answer.
                    2. For each directly grounded node, decide what the synthetic
                       user can express, what limitation or misconception should
                       appear, and which evidence signals may support content.
                    3. Use node rubrics and simulator behavior to align the
                       capability and limitation summaries, but do not copy
                       mastery labels into the output.
                    4. Use simulator-only evidence as content support, but do not
                       include evidence ids or evidence reference fields.
                    5. Do not add new user facts, prior experiences, examples,
                       evidence, or abilities that are not supported by inputs.
                    6. Return only the strict JSON object described below.
                    """
                ).strip(),
                dedent(
                    """
                    Visibility rules:
                    - The output is consumed by expression and generation, so it
                      must not contain mastery labels such as L0-L5.
                    - Do not include node ids, user ids, map ids, graph versions,
                      hidden evidence ids, evidence_refs, state tables, map dumps,
                      scoring fields, manifests, or debug-trace details.
                    - Use node names and de-identified evidence signals only.
                    """
                ).strip(),
                dedent(
                    """
                    Output contract:
                    Return JSON with exactly this shape:
                    {
                      "question_text": "current question",
                      "response_mode": "answer",
                      "primary_stance": "partial_understanding",
                      "overall_directive": "one concise directive",
                      "node_decisions": [
                        {
                          "node_name": "visible node name",
                          "stance": "partial_understanding",
                          "capability_summary": "what the user can express",
                          "limitation_summary": "what remains weak or wrong",
                          "misconception_cues": ["zero or more cues"],
                          "unknown_cues": ["zero or more cues"],
                          "evidence_signals": ["zero or more de-identified signals"],
                          "generation_directives": ["zero or more directives"]
                        }
                      ],
                      "generation_directives": ["global generation directives"],
                      "visibility_guards": ["global forbidden content guards"]
                    }
                    """
                ).strip(),
                dedent(
                    """
                    Allowed enum values:
                    - response_mode: answer, clarification, label_refusal,
                      non_answer, safe_non_answer.
                    - stance: correct_understanding, partial_understanding,
                      uncertain_understanding, not_knowing, misconception.
                    """
                ).strip(),
                dedent(
                    """
                    Final check before output:
                    - JSON matches the schema exactly and contains no extra keys.
                    - The output does not contain mastery labels, hidden ids, or
                      state-table language.
                    - The answer content is grounded only in directly grounded
                      nodes and supplied evidence signals.
                    - The response is exactly one JSON object.
                    """
                ).strip(),
                SIMULATOR_STOP_AFTER_JSON_RULES,
                SIMULATOR_JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=dump_json_payload(
                {
                    "question_text": question_text,
                    "grounding": grounding.model_dump(mode="json"),
                    "grounded_nodes": _grounded_nodes_payload(simulator_context),
                    "visible_dialogue_turns": _visible_dialogue_payload(simulator_context),
                    "fallback_intent": fallback_intent.model_dump(mode="json"),
                }
            ),
        ),
    )


def _grounded_nodes_payload(simulator_context: SimulatorTurnContext) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "node_name": context.node.name,
            "definition": context.node.definition,
            "diagnostic_goal": context.node.diagnostic_goal,
            "levels": context.node.levels,
            "diagnostic_signals": context.node.diagnostic_signals,
            "simulator_behavior": context.node.simulator_behavior,
            "hidden_state": {
                "mastery_level": context.state.mastery_level.value,
                "misconceptions": context.state.misconceptions,
                "unknowns": context.state.unknowns,
            },
            "simulator_only_evidence": tuple(
                {
                    "evidence_kind": evidence.evidence_kind.value,
                    "signal": evidence.signal,
                }
                for evidence in context.simulator_only_evidence
            ),
        }
        for context in simulator_context.grounded_nodes
    )


def _visible_dialogue_payload(simulator_context: SimulatorTurnContext) -> tuple[dict[str, str], ...]:
    if simulator_context.visible_dialogue_context is None:
        return ()
    return tuple(
        {
            "question_text": turn.question.text,
            "answer_text": turn.answer.text,
            "observation_kind": turn.observation.kind.value,
        }
        for turn in simulator_context.visible_dialogue_context.turns
    )
