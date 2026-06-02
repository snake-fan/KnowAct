from pydantic import BaseModel, ConfigDict

from backend.knowact.authoring.openai_workflow import (
    DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER,
    GraphAuthoringClientProvider,
)
from backend.knowact.authoring.logging import redact_logged_text
from backend.knowact.authoring.parsers.profile_context import parse_profile_context_authoring_output
from backend.knowact.authoring.schemas import CandidateProfileContext, ProfileContextAuthoringInput
from backend.knowact.authoring.templates.profile_context import build_profile_context_authoring_messages
from backend.knowact.llm.client import ModelClient, ModelClientMetadata
from backend.knowact.llm.config import deepseek_config_from_env, openai_config_from_env
from backend.knowact.llm.deepseek_client import DeepSeekChatModelClient
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE
from backend.knowact.llm.openai_client import OpenAIChatModelClient
from backend.knowact.logging_config import get_knowact_logger


PROFILE_CONTEXT_AUTHORING_WORKFLOW_NAME = "Profile Context Authoring Workflow"
_LOGGER = get_knowact_logger("authoring.profile_context")


class ProfileContextAuthoringWorkflowResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_profile_context: CandidateProfileContext
    model_raw_output: str
    parser_output: dict[str, object]
    model_metadata: ModelClientMetadata | None = None


class ProfileContextAuthoringWorkflow:
    def __init__(self, *, model_client: ModelClient) -> None:
        self._model_client = model_client

    def run(self, input_data: ProfileContextAuthoringInput) -> ProfileContextAuthoringWorkflowResult:
        metadata = getattr(self._model_client, "metadata", None)
        _LOGGER.info(
            "Profile context authoring workflow started benchmark_domain=%s model_provider=%s model_name=%s",
            input_data.benchmark_domain,
            metadata.provider if metadata is not None else None,
            metadata.model_name if metadata is not None else None,
        )
        try:
            message_profile = getattr(self._model_client, "message_profile", OPENAI_MESSAGE_PROFILE)
            _LOGGER.info(
                "Profile context authoring model call started benchmark_domain=%s has_domain_summary=%s",
                input_data.benchmark_domain,
                input_data.domain_summary is not None,
            )
            raw_output = self._model_client.complete(
                messages=build_profile_context_authoring_messages(
                    input_data,
                    message_profile=message_profile,
                )
            )
            _LOGGER.info(
                "Profile context authoring model call succeeded benchmark_domain=%s raw_output_chars=%d",
                input_data.benchmark_domain,
                len(raw_output),
            )
            generated = parse_profile_context_authoring_output(raw_output)
            _LOGGER.info(
                "Profile context authoring parser succeeded benchmark_domain=%s background_items=%d prior_experience_items=%d goals=%d preferences=%d",
                input_data.benchmark_domain,
                len(generated.background),
                len(generated.prior_experience),
                len(generated.goals),
                len(generated.preferences),
            )
            candidate = CandidateProfileContext(
                benchmark_domain=input_data.benchmark_domain,
                **generated.model_dump(),
            )
            _LOGGER.info(
                "Profile context authoring workflow succeeded benchmark_domain=%s",
                input_data.benchmark_domain,
            )
            return ProfileContextAuthoringWorkflowResult(
                candidate_profile_context=candidate,
                model_raw_output=redact_logged_text(raw_output),
                parser_output=generated.model_dump(mode="json"),
                model_metadata=metadata,
            )
        except Exception as exc:
            _LOGGER.error(
                "Profile context authoring workflow failed benchmark_domain=%s error_type=%s message=%s",
                input_data.benchmark_domain,
                type(exc).__name__,
                redact_logged_text(str(exc)),
            )
            raise


def build_profile_context_authoring_workflow(
    *,
    model_client: ModelClient,
) -> ProfileContextAuthoringWorkflow:
    return ProfileContextAuthoringWorkflow(model_client=model_client)


def build_profile_context_authoring_workflow_for_provider(
    client_provider: GraphAuthoringClientProvider = DEFAULT_GRAPH_AUTHORING_CLIENT_PROVIDER,
) -> ProfileContextAuthoringWorkflow:
    if client_provider == "openai":
        return build_profile_context_authoring_workflow(
            model_client=OpenAIChatModelClient(openai_config_from_env())
        )
    if client_provider == "deepseek":
        return build_profile_context_authoring_workflow(
            model_client=DeepSeekChatModelClient(deepseek_config_from_env())
        )
    raise ValueError(f"Unsupported profile-context authoring client provider: {client_provider}")
