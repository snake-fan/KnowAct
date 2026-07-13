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
                    You derive one compact answer blueprint from the grounded
                    diagnostic situation. You do not write the final visible
                    answer and you do not restate fixed runtime safety rules.
                    """
                ).strip(),
                dedent(
                    """
                    Objective:
                    Analyze the directly grounded node rubrics, hidden map state,
                    grounded simulator-only evidence, grounding flags, and visible
                    dialogue. Return one downstream-safe Simulator Answer Plan
                    that directs answer generation without exposing hidden
                    benchmark artifacts or repeating fields the runtime can set.
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
                    - runtime_response_mode: the deterministic mode selected from
                      grounding. Use it when planning content, but do not output it.
                    - fallback_plan: deterministic baseline plan you may improve.
                    """
                ).strip(),
                dedent(
                    """
                    Process:
                    1. Read runtime_response_mode and grounding flags.
                    2. For each directly grounded node, decide what the synthetic
                       user can express, what limitation or misconception should
                       appear, and which evidence signals may support content.
                    3. Compress repeated capability, limitation, misconception,
                       unknown, and evidence cues into one node-level content
                       unit with direct fields for claim, boundary, mistaken
                       belief, uncertainty, support, and overclaim limits.
                    4. Use node rubrics and simulator behavior to align the plan,
                       but do not copy mastery labels into the output.
                    5. Use simulator-only evidence as content support, but do not
                       include evidence ids or evidence reference fields.
                    6. Do not add new user facts, prior experiences, examples,
                       evidence, or abilities that are not supported by inputs.
                    7. Return only the strict JSON object described below.
                    """
                ).strip(),
                dedent(
                    """
                    Visibility rules:
                    - The output is consumed by generation, so it
                      must not contain mastery labels such as L0-L5.
                    - Do not include node ids, user ids, map ids, graph versions,
                      hidden evidence ids, evidence_refs, state tables, map dumps,
                      scoring fields, manifests, or debug-trace details.
                    - Use node names and de-identified evidence signals only.
                    - If runtime_response_mode is clarification or non_answer,
                      return an empty content_units array.
                    """
                ).strip(),
                dedent(
                    """
                    Output contract:
                    Return JSON with exactly this shape:
                    {
                      "primary_stance": "partial_understanding",
                      "answer_shape": {
                        "voice": "first_person",
                        "integration_mode": "single_node",
                        "max_sentences": 2
                      },
                      "answer_strategy": "one concise content strategy",
                      "content_units": [
                        {
                          "node_name": "visible node name",
                          "stance": "partial_understanding",
                          "core_claim": "what the user can directly express",
                          "boundary": "what remains weak or incomplete",
                          "mistaken_belief": null,
                          "uncertainty": "what the user is unsure about",
                          "supporting_cues": ["zero or more de-identified signals"],
                          "avoid_overclaiming": ["claims the generator must not imply"]
                        }
                      ]
                    }
                    """
                ).strip(),
                dedent(
                    """
                    Allowed enum values:
                    - stance: correct_understanding, partial_understanding,
                      uncertain_understanding, not_knowing, misconception.
                    - answer_shape.voice: first_person.
                    - answer_shape.integration_mode: single_node,
                      integrated_multi_node, clarification, non_answer.
                    """
                ).strip(),
                dedent(
                    """
                    Final check before output:
                    - JSON matches the schema exactly and contains no extra keys.
                    - The output does not include schema_version, question_text,
                      response_mode, fixed generation rules, or visibility guards.
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
                    "runtime_response_mode": fallback_intent.response_mode.value,
                    "grounded_nodes": _grounded_nodes_payload(simulator_context),
                    "visible_dialogue_turns": _visible_dialogue_payload(simulator_context),
                    "fallback_plan": fallback_intent.model_dump(
                        mode="json",
                        exclude={"schema_version", "question_text", "response_mode"},
                    ),
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
