from typing import Literal

from backend.knowact.authoring.steps import (
    LLMEdgeProposalStep,
    LLMNodeSkeletonReconciliationStep,
    LLMNodeRubricAuthoringStep,
    LLMSegmentNodeExtractionStep,
)
from backend.knowact.authoring.workflow import GraphAuthoringAgentWorkflow
from backend.knowact.llm.client import ModelClient
from backend.knowact.llm.config import (
    DeepSeekModelConfig,
    OpenAIModelConfig,
    deepseek_config_from_env,
    openai_config_from_env,
)
from backend.knowact.llm.deepseek_client import DeepSeekChatModelClient
from backend.knowact.llm.openai_client import OpenAIChatModelClient

GraphAuthoringClientProvider = Literal["openai", "deepseek"]
DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER = "openai"


def build_graph_authoring_workflow(
    *,
    model_client: ModelClient,
) -> GraphAuthoringAgentWorkflow:
    return GraphAuthoringAgentWorkflow(
        segment_node_extraction_step=LLMSegmentNodeExtractionStep(model_client),
        node_skeleton_reconciliation_step=LLMNodeSkeletonReconciliationStep(model_client),
        node_rubric_authoring_step=LLMNodeRubricAuthoringStep(model_client),
        edge_proposal_step=LLMEdgeProposalStep(model_client),
        model_metadata=getattr(model_client, "metadata", None),
    )


def build_graph_authoring_workflow_for_provider(
    client_provider: GraphAuthoringClientProvider = DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER,
    *,
    openai_config: OpenAIModelConfig | None = None,
    deepseek_config: DeepSeekModelConfig | None = None,
) -> GraphAuthoringAgentWorkflow:
    if client_provider == "openai":
        return build_graph_authoring_workflow(
            model_client=OpenAIChatModelClient(openai_config or openai_config_from_env())
        )
    if client_provider == "deepseek":
        return build_graph_authoring_workflow(
            model_client=DeepSeekChatModelClient(deepseek_config or deepseek_config_from_env())
        )
    raise ValueError(f"Unsupported graph authoring client provider: {client_provider}")


def build_openai_graph_authoring_workflow(
    *,
    config: OpenAIModelConfig | None = None,
    model_client: ModelClient | None = None,
) -> GraphAuthoringAgentWorkflow:
    if model_client is None:
        model_client = OpenAIChatModelClient(config or openai_config_from_env())

    return build_graph_authoring_workflow(model_client=model_client)
