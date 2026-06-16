from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.knowact.core.episode import (
    EvaluationEpisodeManifest,
    INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN,
    SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
)
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import VisibleDialogueContext
from backend.knowact.validation.exceptions import KnowActValidationError


FORBIDDEN_TESTED_AGENT_VISIBLE_CONTEXT_KEYS = frozenset(
    {
        "answer_blueprint",
        "debug_trace",
        "debug_trace_available",
        "debug_trace_id",
        "debug_trace_payload",
        "evidence",
        "evidence_ids",
        "evidence_kind",
        "evidence_refs",
        "evidence_type",
        "grounded_node_ids",
        "hidden_map",
        "hidden_map_id",
        "include_debug_trace",
        "map_id",
        "map_manifest",
        "mastery_level",
        "profile_context",
        "raw_debug_trace",
        "simulator_context",
        "simulator_only",
        "states",
        "turn_options",
        "user_id",
        "visibility",
    }
)


class TestedAgentVisibleEpisodeContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    max_turns: int
    interaction_rule: Literal["single_diagnostic_question_per_turn"]
    scoring_profile: Literal["squared_mastery_distance_v1"]
    graph: KnowledgeGraph
    visible_dialogue_context: VisibleDialogueContext = Field(
        default_factory=VisibleDialogueContext
    )


def build_tested_agent_visible_episode_context(
    *,
    manifest: EvaluationEpisodeManifest,
    graph: KnowledgeGraph,
) -> TestedAgentVisibleEpisodeContext:
    context = TestedAgentVisibleEpisodeContext(
        episode_id=manifest.episode_id,
        benchmark_domain=manifest.benchmark_domain,
        graph_version=manifest.graph_version,
        max_turns=manifest.max_turns,
        interaction_rule=INTERACTION_RULE_SINGLE_DIAGNOSTIC_QUESTION_PER_TURN,
        scoring_profile=SCORING_PROFILE_SQUARED_MASTERY_DISTANCE_V1,
        graph=graph,
        visible_dialogue_context=VisibleDialogueContext(),
    )
    validate_tested_agent_visible_episode_context(context)
    return context


def validate_tested_agent_visible_episode_context(
    context: TestedAgentVisibleEpisodeContext,
) -> None:
    payload = context.model_dump(mode="json", exclude_none=True)
    forbidden_keys = _find_forbidden_keys(payload)
    if forbidden_keys:
        raise KnowActValidationError(
            "Tested-agent-visible episode context contains hidden fields: "
            + ", ".join(sorted(forbidden_keys))
        )


def _find_forbidden_keys(payload: Any) -> set[str]:
    if isinstance(payload, Mapping):
        found = {
            key
            for key in payload
            if key in FORBIDDEN_TESTED_AGENT_VISIBLE_CONTEXT_KEYS
        }
        for value in payload.values():
            found.update(_find_forbidden_keys(value))
        return found
    if isinstance(payload, list | tuple):
        found: set[str] = set()
        for item in payload:
            found.update(_find_forbidden_keys(item))
        return found
    return set()
