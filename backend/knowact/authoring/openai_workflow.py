from backend.knowact.authoring.steps import (
    LLMEdgeProposalStep,
    LLMNodeExtractionStep,
    LLMNodeRubricAuthoringStep,
)
from backend.knowact.authoring.workflow import GraphAuthoringAgentWorkflow
from backend.knowact.llm.client import ModelClient
from backend.knowact.llm.config import OpenAIModelConfig, openai_config_from_env
from backend.knowact.llm.openai_client import OpenAIChatModelClient


def build_openai_graph_authoring_workflow(
    *,
    config: OpenAIModelConfig | None = None,
    model_client: ModelClient | None = None,
) -> GraphAuthoringAgentWorkflow:
    if model_client is None:
        model_client = OpenAIChatModelClient(config or openai_config_from_env())

    return GraphAuthoringAgentWorkflow(
        node_extraction_step=LLMNodeExtractionStep(model_client),
        node_rubric_authoring_step=LLMNodeRubricAuthoringStep(model_client),
        edge_proposal_step=LLMEdgeProposalStep(model_client),
    )
