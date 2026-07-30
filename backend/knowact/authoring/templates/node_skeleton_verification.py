from backend.knowact.authoring.schemas import NodeSkeletonVerificationInput
from backend.knowact.authoring.templates.common import (
    AUTHORING_CONTEXT,
    JSON_ONLY_RULES,
    STOP_AFTER_JSON_RULES,
    TASK_DATA_BOUNDARY_RULES,
    dump_model,
    dump_model_list,
    render_sections,
)
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage, ModelMessageProfile


def build_node_skeleton_verification_messages(
    input_data: NodeSkeletonVerificationInput,
    *,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                """
Role:
You are the independent KnowAct Node Skeleton Verification Agent Step.
""".strip(),
                """
Objective:
Audit every reconciled skeleton independently before rubric and edge authoring.
Keep a node only when its evidence supports the definition, it is inside the declared aspect, and it has high or medium value for diagnosing the representative tasks.
""".strip(),
                AUTHORING_CONTEXT,
                TASK_DATA_BOUNDARY_RULES,
                """
Input boundary:
You receive the declared scope and reconciled skeletons with source locators, grounding notes, and exact evidence excerpts. You do not receive the full source and must not add or rewrite nodes.
""".strip(),
                """
Process:
1. Check whether the evidence excerpts actually support the node definition rather than merely mentioning a nearby topic.
2. Check whether the node is inside the aspect and helps at least one representative task.
3. Check whether the node is a useful diagnostic unit rather than an incidental detail, duplicate, chapter-sized topic, or tiny notation fragment.
4. Return exactly one decision for every input id.
""".strip(),
                """
Decision rules:
- decision=keep requires grounding_status=supported, scope_status=in_scope, and diagnostic_value high or medium.
- Use remove for uncertain or unsupported grounding, boundary or out-of-scope content, or low diagnostic value.
- Do not use the target count as a quota and do not rescue weak nodes to reach it.
- Do not invent source facts or claim that a human expert reviewed the node.
""".strip(),
                """
Output contract:
Return JSON with exactly this shape:
{
  "decisions": [
    {
      "id": "exact_input_skeleton_id",
      "decision": "keep",
      "grounding_status": "supported",
      "scope_status": "in_scope",
      "diagnostic_value": "high",
      "rationale": "Concise audit rationale."
    }
  ]
}

Use the literal enum values keep/remove, supported/uncertain/unsupported, in_scope/boundary_case/out_of_scope, and high/medium/low.
""".strip(),
                """
Final check before output:
- Every input id appears exactly once and no extra id appears.
- Every keep decision satisfies all three keep conditions.
- The response contains no rewritten nodes, rubrics, edges, user states, or prose outside JSON.
""".strip(),
                STOP_AFTER_JSON_RULES,
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Audit these reconciled node skeletons.",
                f"Graph Authoring Scope:\n\n{dump_model(input_data.scope)}",
                f"Reconciled skeletons:\n\n{dump_model_list(input_data.skeletons)}",
            ),
        ),
    )
