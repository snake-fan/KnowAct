import json
from collections.abc import Sequence


AUTHORING_CONTEXT = """
KnowAct v1 is an active knowledge-state diagnosis benchmark. Graph authoring
produces reviewable candidate graph data for benchmark authors; it does not
produce evaluation ground truth and it must not bypass human review.

Keep these domain boundaries explicit:
- Knowledge Graph = user-independent objective knowledge structure.
- Knowledge Node = stable, diagnosable, source-grounded concept plus diagnostic rubric.
- Knowledge Edge = objective relationship between two nodes.
- Knowledge Map / User Knowledge State / Evidence = user-specific data; do not put these into graph nodes or edges.
- Candidate status belongs to filenames, directories, or review state; never add candidate/review fields to JSON objects.
""".strip()


SOURCE_GROUNDING_RULES = """
Source-grounding rules:
- Use only the uploaded original PDF and source locators from earlier workflow steps.
- Do not brainstorm nodes, rubrics, or edges from model memory.
- Every node or skeleton must be traceable to at least one source_id and locator.
- Source locators are lightweight audit references, not quote stores. Chapter, section, page, slide, paragraph, or equivalent locator is enough when it lets a reviewer find the concept.
- Do not invent quotes, exact spans, page numbers, or source metadata that are not visible in the PDF or provided as source_id metadata.
""".strip()


NODE_DESIGN_RULES = """
Knowledge Node design rules:
- The node should be explainable: a user can say what it means.
- The node should be diagnosable with roughly 1-3 focused diagnostic questions.
- The node should have moderate granularity: not a whole field/chapter and not a tiny token, symbol, index, or wording detail.
- The node should be stable across the domain, not a temporary phrasing from one passage.
- The node should support definition, example, application, comparison, and boundary reasoning.
- v1 currently uses type "concept"; do not invent a taxonomy.
""".strip()


MASTERY_SCALE = """
Global L0-L5 MasteryScale:
- L0: no effective understanding or wrong recognition. The user cannot identify the concept or confuses it with unrelated ideas.
- L1: term recognition / recall. The user can repeat terms, keywords, or definitions but depends on memorization.
- L2: basic explanation. The user can explain the core meaning in their own words but handles simple examples and has unclear boundaries.
- L3: structured understanding. The user can relate the concept to neighboring concepts, prerequisites, contrasts, conditions, and common mistakes.
- L4: application and transfer. The user can use the concept in new problems and decide when it applies.
- L5: reflective / generative understanding. The user can critique assumptions, teach, abstract, generate examples, and design counterexamples.
""".strip()


NODE_SCHEMA_CONTRACT = """
Return KnowledgeNode objects that match the current parser contract:
- id: stable snake_case machine id.
- name: human-readable concept name.
- type: "concept".
- definition: concise source-grounded definition.
- diagnostic_goal: the overall diagnostic target for this node.
- levels: object with exactly keys L0, L1, L2, L3, L4, L5. Each value is a non-empty node-specific description string.
- diagnostic_signals: non-empty list of observable answer signals useful for distinguishing mastery levels.
- simulator_behavior: concise knowledge-state response behavior for a simulator; do not include persona, preferences, or hidden labels.
- source_locators: non-empty list of simple source references.
""".strip()


JSON_ONLY_RULES = """
Output rules:
- Return only valid JSON.
- Do not wrap JSON in Markdown fences.
- Do not include commentary, reasoning notes, review notes, or debug logs.
- Do not add fields outside the requested schema.
""".strip()


EDGE_TYPE_RULES = """
Canonical Knowledge Edge types:
- part_of: source is a structural component of target. It is not a generic topic/category relation.
- prerequisite_for: source is a cognitive prerequisite for target. Missing source usually weakens or blocks stable L3+ understanding of target, though L1/L2 may still be possible.
- supports: source strengthens explanation, transfer, or diagnostic confidence for target, but is not a prerequisite. Do not use supports as a generic relatedness label.
- contrasts_with: source and target clarify each other through boundaries, failure modes, or differences. It is symmetric, but store one edge only with source/target in lexicographic node-id order.

If a pair is only in the same chapter, merely topically adjacent, speculative, or hard to type clearly, omit it.
""".strip()


EDGE_SCHEMA_CONTRACT = """
Return KnowledgeEdge objects that match the parser contract:
- id: stable id, preferably edge_{source}_{type}_{target}.
- source: source node id.
- target: target node id.
- type: one of part_of, prerequisite_for, supports, contrasts_with.
- rationale: objective reason why the relationship holds. Do not describe user evidence or diagnostic questions.
- weight: relationship strength from 0.0 to 1.0.
- curation_confidence: confidence that this edge annotation is valid from 0.0 to 1.0. This is for review and calibration, not a hard inclusion threshold.
""".strip()


def render_sections(*sections: str) -> str:
    return "\n\n".join(section.strip() for section in sections if section.strip())


def dump_model_list(items: Sequence[object]) -> str:
    payload = [
        item.model_dump(mode="json", exclude_none=True) if hasattr(item, "model_dump") else item
        for item in items
    ]
    return json.dumps(payload, indent=2, sort_keys=True)


def render_uploaded_pdf_source_reference(source_materials: Sequence[object]) -> str:
    source_ids: list[str] = []
    for item in source_materials:
        source_id = getattr(item, "source_id", None)
        if isinstance(source_id, str) and source_id.strip():
            source_ids.append(source_id)

    if not source_ids:
        return "Use the uploaded original PDF as the authoritative source."
    if len(source_ids) == 1:
        return (
            "Use the uploaded original PDF as the authoritative source. "
            f'For source_locators that cite it, write source_id "{source_ids[0]}".'
        )
    formatted_source_ids = ", ".join(f'"{source_id}"' for source_id in source_ids)
    return (
        "Use the uploaded original PDFs as the authoritative sources. "
        f"For source_locators, use the matching source_id from: {formatted_source_ids}."
    )
