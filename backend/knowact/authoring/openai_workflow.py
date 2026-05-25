from collections.abc import Sequence
from pathlib import Path

from backend.knowact.authoring.steps import (
    LLMEdgeProposalStep,
    LLMNodeExtractionStep,
    LLMNodeRubricAuthoringStep,
)
from backend.knowact.authoring.workflow import GraphAuthoringAgentWorkflow
from backend.knowact.llm.client import ModelClient, PDFModelClient
from backend.knowact.llm.config import OpenAIModelConfig, openai_config_from_env
from backend.knowact.llm.openai_client import OpenAIChatModelClient
from backend.knowact.llm.messages import ModelMessage
from backend.knowact.llm.openai_responses_client import OpenAIResponsesPDFClient


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


def build_openai_pdf_graph_authoring_workflow(
    *,
    pdf_path: Path,
    filename: str | None = None,
    config: OpenAIModelConfig | None = None,
    pdf_client: PDFModelClient | None = None,
) -> GraphAuthoringAgentWorkflow:
    if pdf_client is None:
        pdf_client = OpenAIResponsesPDFClient(config or openai_config_from_env())

    model_client = _PDFBackedModelClient(pdf_client=pdf_client, pdf_path=pdf_path, filename=filename)
    return GraphAuthoringAgentWorkflow(
        node_extraction_step=LLMNodeExtractionStep(model_client),
        node_rubric_authoring_step=LLMNodeRubricAuthoringStep(model_client),
        edge_proposal_step=LLMEdgeProposalStep(model_client),
    )


class _PDFBackedModelClient:
    def __init__(
        self,
        *,
        pdf_client: PDFModelClient,
        pdf_path: Path,
        filename: str | None = None,
    ) -> None:
        self._pdf_client = pdf_client
        self._pdf_path = pdf_path
        self._filename = filename

    def complete(
        self,
        *,
        messages: Sequence[ModelMessage],
    ) -> str:
        return self._pdf_client.complete_with_pdf(
            messages=messages,
            pdf_path=self._pdf_path,
            filename=self._filename,
            json_mode=True,
        )
