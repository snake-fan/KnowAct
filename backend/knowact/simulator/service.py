from pathlib import Path

from backend.knowact.core.interaction import (
    CoarseObservationMetadata,
    VisibleObservationKind,
)
from backend.knowact.simulator.context_builder import SimulatorContextBuilder
from backend.knowact.simulator.expression import SimulatorExpressionContextBuilder
from backend.knowact.simulator.fallbacks import (
    multiple_question_clarification,
    no_grounding_answer,
)
from backend.knowact.simulator.generators import RuleBasedAnswerGenerator
from backend.knowact.simulator.grounding import RuleBasedQuestionGrounder
from backend.knowact.simulator.policy import RuleBasedAnswerPolicy
from backend.knowact.simulator.preview import (
    SimulatorPreviewRequest,
    SimulatorPreviewResponse,
    SimulatorPreviewWarning,
    SimulatorPreviewWarningCode,
)
from backend.knowact.storage.profile_contexts import (
    ConfirmedProfileContextNotFoundError,
    load_confirmed_profile_context,
)
from backend.knowact.storage.reviewed_graphs import load_reviewed_graph
from backend.knowact.storage.reviewed_maps import (
    load_reviewed_map,
    load_reviewed_map_manifest,
)


class SimulatorService:
    def __init__(self, *, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._grounder = RuleBasedQuestionGrounder()
        self._context_builder = SimulatorContextBuilder()
        self._policy = RuleBasedAnswerPolicy()
        self._expression_builder = SimulatorExpressionContextBuilder()
        self._generator = RuleBasedAnswerGenerator()

    def answer_preview(self, request: SimulatorPreviewRequest) -> SimulatorPreviewResponse:
        manifest = load_reviewed_map_manifest(
            workspace_root=self._workspace_root,
            benchmark_domain=request.benchmark_domain,
            map_id=request.map_id,
        )
        graph_artifacts = load_reviewed_graph(
            workspace_root=self._workspace_root,
            benchmark_domain=manifest.benchmark_domain,
            version=manifest.graph_version,
        )

        grounding = self._grounder.ground(
            question=request.question,
            graph=graph_artifacts.graph,
            visible_dialogue_context=request.visible_dialogue_context,
        )
        if not grounding.has_grounding:
            return SimulatorPreviewResponse(
                answer=no_grounding_answer(),
                observation=CoarseObservationMetadata(kind=VisibleObservationKind.NON_ANSWER),
                warnings=(),
            )
        if grounding.is_multiple_question:
            return SimulatorPreviewResponse(
                answer=multiple_question_clarification(),
                observation=CoarseObservationMetadata(
                    kind=VisibleObservationKind.CLARIFICATION
                ),
                warnings=(),
            )

        map_artifacts = load_reviewed_map(
            workspace_root=self._workspace_root,
            benchmark_domain=request.benchmark_domain,
            map_id=request.map_id,
        )
        profile_context, warnings = self._load_optional_profile_context(
            benchmark_domain=manifest.benchmark_domain,
            user_id=manifest.user_id,
        )

        simulator_context = self._context_builder.build(
            benchmark_domain=manifest.benchmark_domain,
            map_id=manifest.map_id,
            graph_version=manifest.graph_version,
            user_id=manifest.user_id,
            graph=graph_artifacts.graph,
            knowledge_map=map_artifacts.knowledge_map,
            grounding=grounding,
            visible_dialogue_context=request.visible_dialogue_context,
        )
        intent = self._policy.derive_intent(
            question_text=request.question.text,
            simulator_context=simulator_context,
        )
        expression_context = self._expression_builder.build(
            intent=intent,
            simulator_context=simulator_context,
            profile_context=profile_context,
        )
        answer = self._generator.render(expression_context)

        return SimulatorPreviewResponse(
            answer=answer,
            observation=CoarseObservationMetadata(kind=VisibleObservationKind.ANSWER),
            warnings=warnings,
        )

    def _load_optional_profile_context(
        self,
        *,
        benchmark_domain: str,
        user_id: str,
    ) -> tuple[object | None, tuple[SimulatorPreviewWarning, ...]]:
        try:
            profile_context = load_confirmed_profile_context(
                workspace_root=self._workspace_root,
                benchmark_domain=benchmark_domain,
                user_id=user_id,
            )
        except ConfirmedProfileContextNotFoundError:
            return (
                None,
                (
                    SimulatorPreviewWarning(
                        code=SimulatorPreviewWarningCode.MISSING_PROFILE_CONTEXT,
                        message="Profile context is unavailable; preview used neutral wording.",
                    ),
                ),
            )
        return profile_context, ()
