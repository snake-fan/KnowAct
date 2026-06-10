from textwrap import dedent

from backend.knowact.core.interaction import (
    VisibleDialogueContext,
    VisibleSimulatorAnswer,
)
from backend.knowact.llm.messages import (
    ModelMessage,
    ModelMessageProfile,
    OPENAI_MESSAGE_PROFILE,
)
from backend.knowact.simulator.policy import SimulatorAnswerIntent
from backend.knowact.simulator.templates.common import (
    SIMULATOR_CONTEXT,
    SIMULATOR_JSON_ONLY_RULES,
    SIMULATOR_STOP_AFTER_JSON_RULES,
    SIMULATOR_TASK_DATA_BOUNDARY_RULES,
    dump_json_payload,
    render_sections,
)


def build_answer_validation_messages(
    *,
    candidate_answer: VisibleSimulatorAnswer,
    intent: SimulatorAnswerIntent,
    visible_dialogue_context: VisibleDialogueContext | None = None,
    style_hint: str | None = None,
    regeneration_guidance: tuple[str, ...] = (),
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    payload = {
        "candidate_answer": candidate_answer.model_dump(mode="json"),
        "answer_intent": intent.model_dump(mode="json"),
        "visible_dialogue_turns": _visible_dialogue_payload(visible_dialogue_context),
        "style_hint": style_hint,
        "regeneration_guidance": regeneration_guidance,
        "blocking_safety_checks": (
            "benchmark mastery labels",
            "hidden evidence identifiers or reference fields",
            "full-map, hidden-state, state-table, or debug-trace dumps",
            "benchmark assessment fields",
            "new facts, examples, prior-experience claims, or ability claims not in context",
        ),
        "intent_coverage_checks": (
            "answer preserves response mode, primary stance, and node decisions",
            "answer uses only de-identified answer focus, boundary focus, and supporting signals",
            "answer remains natural first-person self-report",
            "answer uses visible dialogue only for continuity",
            "answer follows regeneration guidance when present",
        ),
    }
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                dedent(
                    """
                    Role:
                    You are the Simulator Answer Validation Agent for KnowAct v1.
                    You judge whether one candidate simulator answer is safe to
                    expose to the tested agent and sufficiently covers the
                    supplied answer intent.
                    """
                ).strip(),
                dedent(
                    """
                    Objective:
                    Return one structured pass/fail decision. Success means every
                    unsafe answer fails closed, safe answers are accepted only when
                    they preserve the intended stance, and all notes stay concise
                    enough for hidden debug use.
                    """
                ).strip(),
                SIMULATOR_CONTEXT,
                SIMULATOR_TASK_DATA_BOUNDARY_RULES,
                dedent(
                    """
                    Inputs:
                    - candidate_answer.text: the proposed visible answer.
                    - answer_intent: de-identified expected answer plan.
                    - visible_dialogue_turns, style_hint, and
                      regeneration_guidance: runtime wording context.
                    - blocking_safety_checks: safety categories that must fail.
                    - intent_coverage_checks: usefulness categories to inspect.
                    """
                ).strip(),
                dedent(
                    """
                    Process:
                    1. Inspect candidate_answer for benchmark leakage, hidden
                       artifacts, unsupported claims, and schema/internal language.
                    2. Compare candidate_answer to response_mode,
                       answer_strategy, primary_stance, node decisions,
                       answer_focus, boundary_focus, and supporting_signals.
                    3. Check whether visible dialogue was used only for continuity.
                    4. Set passed=false if any blocking safety issue appears.
                    5. Set passed=false if the answer does not preserve the core
                       stance or invents unsupported content.
                    6. Write concise blocking_safety_reasons and
                       intent_coverage_notes; do not include hidden internals.
                    7. Return only the JSON object described below.
                    """
                ).strip(),
                dedent(
                    """
                    Blocking safety rules:
                    - Fail if the answer reveals benchmark labels, hidden evidence
                      identifiers, evidence reference fields, hidden maps, state
                      tables, scoring or assessment fields, debug traces, manifest
                      data, user ids, map ids, or graph-version references.
                    - Fail if the answer claims facts, examples, prior experience,
                      or abilities that are absent from the de-identified context.
                    - Fail if the answer says it has read hidden benchmark
                      artifacts or explains simulator validation internals.
                    """
                ).strip(),
                dedent(
                    """
                    Intent coverage rules:
                    - The answer should preserve the supplied response mode,
                      uncertainty, partial knowledge, misconception, not-knowing,
                      or correct understanding when those decisions are supplied.
                    - The answer may paraphrase evidence signals, but it must not
                      contradict them.
                    - Weak wording is acceptable only when it still communicates
                      the intended knowledge posture.
                    - If coverage is weak but not unsafe, include an intent note;
                      if the core stance is missing or contradicted, fail.
                    """
                ).strip(),
                dedent(
                    """
                    Output contract:
                    Return JSON with exactly this shape:
                    {
                      "passed": true,
                      "blocking_safety_reasons": [],
                      "intent_coverage_notes": ["concise note"],
                      "fallback_guidance": null
                    }
                    """
                ).strip(),
                dedent(
                    """
                    Example:
                    Candidate answer: "I know the idea in broad strokes, but I
                    still mix up validation and final testing."
                    Expected JSON:
                    {
                      "passed": true,
                      "blocking_safety_reasons": [],
                      "intent_coverage_notes": ["Preserves partial understanding."],
                      "fallback_guidance": null
                    }
                    """
                ).strip(),
                dedent(
                    """
                    Final check before output:
                    - passed is false for any blocking safety issue.
                    - passed is false when core stance coverage is missing.
                    - reasons and notes are concise strings.
                    - fallback_guidance is null when passed is true.
                    - The response is exactly one JSON object with the four
                      required top-level keys.
                    """
                ).strip(),
                SIMULATOR_STOP_AFTER_JSON_RULES,
                SIMULATOR_JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=dump_json_payload(payload),
        ),
    )


def _visible_dialogue_payload(
    visible_dialogue_context: VisibleDialogueContext | None,
) -> tuple[dict[str, str], ...]:
    if visible_dialogue_context is None:
        return ()
    return tuple(
        {
            "question_text": turn.question.text,
            "answer_text": turn.answer.text,
            "observation_kind": turn.observation.kind.value,
        }
        for turn in visible_dialogue_context.turns
    )
