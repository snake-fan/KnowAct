from backend.knowact.authoring.schemas import ProfileContextAuthoringInput
from backend.knowact.authoring.templates.common import JSON_ONLY_RULES, render_sections
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage, ModelMessageProfile


def build_profile_context_authoring_messages(
    input_data: ProfileContextAuthoringInput,
    *,
    message_profile: ModelMessageProfile = OPENAI_MESSAGE_PROFILE,
) -> tuple[ModelMessage, ...]:
    return (
        ModelMessage(
            role=message_profile.high_priority_instruction_role,
            content=render_sections(
                "You are the KnowAct Profile Context Authoring Agent Step.",
                """
KnowAct v1 uses a Profile Context as a reviewable synthetic-user persona basis
for later map authoring and simulation. This step expands a benchmark author's
rough description into one structured candidate artifact. It does not author a
Knowledge Map.

Keep these boundaries explicit:
- Do not assign a user_id. Formal synthetic-user identity is assigned only after benchmark-author confirmation.
- Do not output Knowledge Nodes, node rubrics, Knowledge Edges, mastery levels, misconceptions, unknowns, evidence, or per-node state.
- Use only the benchmark domain identity, rough description, and optional limited domain summary provided by the benchmark author.
- Produce coherent persona context that a benchmark author can inspect and edit before confirmation.
""".strip(),
                """
Return JSON with this exact shape:
{
  "summary": "Readable synthetic-user summary.",
  "background": ["At least one nonblank background item."],
  "prior_experience": ["Zero or more nonblank prior-experience items."],
  "goals": ["At least one nonblank goal item."],
  "preferences": ["Zero or more nonblank preference items."]
}

The complete response must include exactly these five fields. Do not add benchmark_domain or user_id; workflow code controls benchmark-domain identity.
""".strip(),
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Generate one reviewable Profile Context candidate.",
                f"Benchmark domain: {input_data.benchmark_domain}",
                f"Rough description: {input_data.rough_description}",
                (
                    f"Optional limited domain summary: {input_data.domain_summary}"
                    if input_data.domain_summary is not None
                    else ""
                ),
                """
Before returning JSON, check that the candidate is coherent, editable, and free
of formal user identity and node-level knowledge-state data.
""".strip(),
            ),
        ),
    )
