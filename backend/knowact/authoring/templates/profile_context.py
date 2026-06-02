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
                "Generate one structured profile for a hypothetical person in a given subject area.",
                """
Expand the rough person description into a coherent, realistic profile by
filling the requested fields.

Task requirements:
- Preserve the facts in the rough description.
- Add only conservative, plausible details that help connect the person's background, prior experience, goals, and preferences.
- Use the subject area and optional subject-area summary only to keep the profile relevant.
- Keep each statement concise, concrete, and internally consistent.

Scope limits:
- Describe person-level context only.
- Do not produce a topic-by-topic knowledge assessment, proficiency ratings, scores, levels, misconceptions, unknowns, evidence records, or a study plan.
- Do not invent specific institutions, employers, credentials, achievements, demographic attributes, or personal history unless the rough description provides them.
- Do not add an identifier or any field outside the requested JSON shape.
""".strip(),
                """
Return JSON with this exact shape:
{
  "summary": "One to three sentences summarizing the person.",
  "background": ["At least one nonblank background item."],
  "prior_experience": ["Zero or more nonblank prior-experience items."],
  "goals": ["At least one nonblank goal item."],
  "preferences": ["Zero or more nonblank preference items."]
}

The complete response must include exactly these five fields.
""".strip(),
                JSON_ONLY_RULES,
            ),
        ),
        ModelMessage(
            role="user",
            content=render_sections(
                "Create the structured person profile from the following inputs.",
                f"Subject area: {input_data.benchmark_domain}",
                f"Rough person description: {input_data.rough_description}",
                (
                    f"Optional subject-area summary: {input_data.domain_summary}"
                    if input_data.domain_summary is not None
                    else ""
                ),
                """
Before returning JSON, check that the profile is coherent, grounded in the
provided description, and limited to person-level context.
""".strip(),
            ),
        ),
    )
