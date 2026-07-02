from collections.abc import Callable
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.agents.agents.simple_llm import SimpleLLMTestedAgent
from backend.knowact.agents.llm_agent import (
    TestedAgentConfigurationError,
    build_simple_llm_tested_agent_for_provider,
)
from backend.knowact.agents.protocol import (
    DecisionPhase,
    DecisionPhaseContext,
    TestedAgentDecision,
)
from backend.knowact.agents.providers import (
    DEFAULT_TESTED_AGENT_CLIENT_PROVIDER,
    TestedAgentClientProvider,
)
from backend.knowact.agents.tools import (
    WorkingMapNodeAssessmentUpdate,
    update_node_assessments,
    validate_working_map,
)
from backend.knowact.agents.working_map import (
    AgentWorkingKnowledgeMap,
    initialize_working_map,
)
from backend.knowact.core.graph import KnowledgeGraph
from backend.knowact.core.interaction import VisibleDialogueContext
from backend.knowact.llm.client import ModelClientError
from backend.knowact.storage.reviewed_graphs import (
    ReviewedGraphArtifactError,
    ReviewedGraphNotFoundError,
    load_reviewed_graph,
)
from backend.knowact.validation.exceptions import KnowActValidationError


SimpleLLMTestedAgentFactory = Callable[
    [TestedAgentClientProvider, float | None],
    SimpleLLMTestedAgent,
]


class SimpleLLMTestedAgentTurnTestRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    episode_id: str
    benchmark_domain: str
    graph_version: str
    client_provider: TestedAgentClientProvider = DEFAULT_TESTED_AGENT_CLIENT_PROVIDER
    temperature: float | None = Field(default=None, ge=0.0)
    decision_context: DecisionPhaseContext = Field(
        default_factory=lambda: DecisionPhaseContext(
            phase=DecisionPhase.INITIAL_QUESTION,
            remaining_diagnostic_turns=1,
        )
    )
    visible_dialogue_context: VisibleDialogueContext = Field(
        default_factory=VisibleDialogueContext
    )
    working_map: AgentWorkingKnowledgeMap | None = None

    @field_validator("episode_id", "benchmark_domain", "graph_version")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class SimpleLLMTestedAgentTurnTestResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_kind: Literal["simple_llm"] = "simple_llm"
    client_provider: TestedAgentClientProvider
    episode_id: str
    benchmark_domain: str
    graph_version: str
    decision_context: DecisionPhaseContext
    updates: tuple[WorkingMapNodeAssessmentUpdate, ...] = Field(default_factory=tuple)
    working_map: AgentWorkingKnowledgeMap
    decision: TestedAgentDecision


def build_tested_agents_router(
    *,
    workspace_root: Path | None = None,
    simple_llm_tested_agent_factory: SimpleLLMTestedAgentFactory | None = None,
) -> APIRouter:
    root = workspace_root or _default_workspace_root()
    agent_factory = simple_llm_tested_agent_factory or (
        lambda client_provider, temperature: build_simple_llm_tested_agent_for_provider(
            client_provider=client_provider,
            temperature=temperature,
        )
    )
    router = APIRouter()

    @router.post(
        "/simple-llm/turn-test",
        response_model=SimpleLLMTestedAgentTurnTestResponse,
        summary="Ask the Simple LLM tested agent for one test decision.",
    )
    def run_simple_llm_turn_test(
        request: SimpleLLMTestedAgentTurnTestRequest,
    ) -> SimpleLLMTestedAgentTurnTestResponse:
        try:
            graph = load_reviewed_graph(
                workspace_root=root,
                benchmark_domain=request.benchmark_domain,
                version=request.graph_version,
            ).graph
            working_map = _working_map_for_request(request=request, graph=graph)
            agent = agent_factory(request.client_provider, request.temperature)
            updates = agent.update_after_visible_answer(
                graph=graph,
                working_map=working_map,
                visible_dialogue_context=request.visible_dialogue_context,
                decision_context=request.decision_context,
            )
            updated_working_map = update_node_assessments(
                working_map=working_map,
                graph=graph,
                visible_dialogue_context=request.visible_dialogue_context,
                updates=updates,
            )
            decision = agent.decide_next_action(
                graph=graph,
                working_map=updated_working_map,
                visible_dialogue_context=request.visible_dialogue_context,
                decision_context=request.decision_context,
            )
            return SimpleLLMTestedAgentTurnTestResponse(
                client_provider=request.client_provider,
                episode_id=request.episode_id,
                benchmark_domain=request.benchmark_domain,
                graph_version=request.graph_version,
                decision_context=request.decision_context,
                updates=updates,
                working_map=updated_working_map,
                decision=decision,
            )
        except TestedAgentConfigurationError as exc:
            raise HTTPException(
                status_code=503,
                detail=_error_detail(
                    "tested_agent_not_configured",
                    "Simple LLM tested agent service is not configured.",
                ),
            ) from exc
        except ReviewedGraphNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=_error_detail("reviewed_graph_not_found", str(exc)),
            ) from exc
        except ReviewedGraphArtifactError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail(
                    "malformed_reviewed_graph",
                    "Reviewed graph artifact is malformed.",
                ),
            ) from exc
        except KnowActValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_working_map_update", str(exc)),
            ) from exc
        except ModelClientError as exc:
            raise HTTPException(
                status_code=502,
                detail=_error_detail("tested_agent_model_error", str(exc)),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=_error_detail("invalid_tested_agent_request", str(exc)),
            ) from exc

    return router


def _working_map_for_request(
    *,
    request: SimpleLLMTestedAgentTurnTestRequest,
    graph: KnowledgeGraph,
) -> AgentWorkingKnowledgeMap:
    if request.working_map is None:
        working_map = initialize_working_map(
            episode_id=request.episode_id,
            benchmark_domain=request.benchmark_domain,
            graph_version=request.graph_version,
            graph=graph,
        )
    else:
        working_map = request.working_map

    _validate_working_map_binding(request=request, working_map=working_map)
    validate_working_map(working_map, graph)
    return working_map


def _validate_working_map_binding(
    *,
    request: SimpleLLMTestedAgentTurnTestRequest,
    working_map: AgentWorkingKnowledgeMap,
) -> None:
    if working_map.episode_id != request.episode_id:
        raise ValueError("working_map.episode_id must match request episode_id")
    if working_map.benchmark_domain != request.benchmark_domain:
        raise ValueError(
            "working_map.benchmark_domain must match request benchmark_domain"
        )
    if working_map.graph_version != request.graph_version:
        raise ValueError("working_map.graph_version must match request graph_version")


def _error_detail(error_code: str, message: str) -> dict[str, str]:
    return {"error_code": error_code, "message": message}


def _default_workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]
