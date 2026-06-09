from pathlib import Path

from backend.knowact.core.interaction import (
    CoarseObservationMetadata,
    VisibleObservationKind,
    VisibleSimulatorAnswer,
)
from backend.knowact.llm.client import ModelClientError
from backend.knowact.logging_config import get_knowact_logger
from backend.knowact.simulator.checks import (
    HeuristicSimulatorAnswerValidator,
    SimulatorAnswerValidator,
)
from backend.knowact.simulator.context_builder import (
    SimulatorContextBuilder,
    SimulatorTurnContext,
)
from backend.knowact.simulator.expression import (
    SimulatorExpressionContext,
    SimulatorExpressionContextBuilder,
)
from backend.knowact.simulator.fallbacks import (
    multiple_question_clarification,
    no_grounding_answer,
    simulator_safe_fallback,
)
from backend.knowact.simulator.generators import (
    RuleBasedAnswerGenerator,
    SimulatorAnswerGenerator,
)
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


_LOGGER = get_knowact_logger("simulator.service")


class SimulatorService:
    def __init__(
        self,
        *,
        workspace_root: Path,
        generator: SimulatorAnswerGenerator | None = None,
        validator: SimulatorAnswerValidator | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._grounder = RuleBasedQuestionGrounder()
        self._context_builder = SimulatorContextBuilder()
        self._policy = RuleBasedAnswerPolicy()
        self._expression_builder = SimulatorExpressionContextBuilder()
        self._generator = generator or RuleBasedAnswerGenerator()
        self._validator = validator or HeuristicSimulatorAnswerValidator()

    def answer_preview(self, request: SimulatorPreviewRequest) -> SimulatorPreviewResponse:
        visible_turns = _visible_dialogue_turn_count(request)
        _LOGGER.info(
            "Simulator preview workflow started benchmark_domain=%s map_id=%s client_provider=%s question_id=%s visible_dialogue_turns=%d include_debug_trace=%s",
            request.benchmark_domain,
            request.map_id,
            request.client_provider,
            request.question.question_id,
            visible_turns,
            request.preview_options.include_debug_trace,
        )
        try:
            manifest = load_reviewed_map_manifest(
                workspace_root=self._workspace_root,
                benchmark_domain=request.benchmark_domain,
                map_id=request.map_id,
            )
            _LOGGER.info(
                "Simulator preview map manifest loaded benchmark_domain=%s map_id=%s graph_version=%s user_id=%s",
                manifest.benchmark_domain,
                manifest.map_id,
                manifest.graph_version,
                manifest.user_id,
            )
            graph_artifacts = load_reviewed_graph(
                workspace_root=self._workspace_root,
                benchmark_domain=manifest.benchmark_domain,
                version=manifest.graph_version,
            )
            _LOGGER.info(
                "Simulator preview reviewed graph loaded benchmark_domain=%s graph_version=%s nodes=%d edges=%d",
                manifest.benchmark_domain,
                manifest.graph_version,
                len(graph_artifacts.graph.nodes),
                len(graph_artifacts.graph.edges),
            )

            _LOGGER.info(
                "Question grounding started benchmark_domain=%s map_id=%s visible_dialogue_turns=%d",
                manifest.benchmark_domain,
                manifest.map_id,
                visible_turns,
            )
            grounding = self._grounder.ground(
                question=request.question,
                graph=graph_artifacts.graph,
                visible_dialogue_context=request.visible_dialogue_context,
            )
            _LOGGER.info(
                "Question grounding succeeded benchmark_domain=%s map_id=%s grounded_nodes=%d integrated_question=%s multiple_question=%s label_seeking=%s",
                manifest.benchmark_domain,
                manifest.map_id,
                len(grounding.grounded_node_ids),
                grounding.is_integrated_question,
                grounding.is_multiple_question,
                grounding.is_label_seeking,
            )

            if not grounding.has_grounding:
                warnings, debug_trace_available = self._apply_debug_trace_preview_options(
                    warnings=(),
                    request=request,
                )
                _LOGGER.info(
                    "Simulator preview workflow succeeded benchmark_domain=%s map_id=%s observation_kind=%s warnings=%d debug_trace_available=%s fallback_reason=%s",
                    manifest.benchmark_domain,
                    manifest.map_id,
                    VisibleObservationKind.NON_ANSWER.value,
                    len(warnings),
                    debug_trace_available,
                    "no_grounding",
                )
                return SimulatorPreviewResponse(
                    answer=no_grounding_answer(),
                    observation=CoarseObservationMetadata(kind=VisibleObservationKind.NON_ANSWER),
                    warnings=warnings,
                    debug_trace_available=debug_trace_available,
                )
            if grounding.is_multiple_question:
                warnings, debug_trace_available = self._apply_debug_trace_preview_options(
                    warnings=(),
                    request=request,
                )
                _LOGGER.info(
                    "Simulator preview workflow succeeded benchmark_domain=%s map_id=%s observation_kind=%s warnings=%d debug_trace_available=%s fallback_reason=%s",
                    manifest.benchmark_domain,
                    manifest.map_id,
                    VisibleObservationKind.CLARIFICATION.value,
                    len(warnings),
                    debug_trace_available,
                    "multiple_question",
                )
                return SimulatorPreviewResponse(
                    answer=multiple_question_clarification(),
                    observation=CoarseObservationMetadata(
                        kind=VisibleObservationKind.CLARIFICATION
                    ),
                    warnings=warnings,
                    debug_trace_available=debug_trace_available,
                )

            map_artifacts = load_reviewed_map(
                workspace_root=self._workspace_root,
                benchmark_domain=request.benchmark_domain,
                map_id=request.map_id,
            )
            _LOGGER.info(
                "Simulator preview reviewed map loaded benchmark_domain=%s map_id=%s states=%d evidence_records=%d",
                manifest.benchmark_domain,
                manifest.map_id,
                len(map_artifacts.knowledge_map.states),
                len(map_artifacts.knowledge_map.evidence),
            )
            profile_context, warnings = self._load_optional_profile_context(
                benchmark_domain=manifest.benchmark_domain,
                user_id=manifest.user_id,
            )

            _LOGGER.info(
                "Simulator context build started benchmark_domain=%s map_id=%s grounded_nodes=%d",
                manifest.benchmark_domain,
                manifest.map_id,
                len(grounding.grounded_node_ids),
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
            _LOGGER.info(
                "Simulator context built benchmark_domain=%s map_id=%s grounded_nodes=%d simulator_only_evidence_records=%d visible_dialogue_turns=%d",
                manifest.benchmark_domain,
                manifest.map_id,
                len(simulator_context.grounded_nodes),
                _simulator_only_evidence_count(simulator_context),
                visible_turns,
            )

            _LOGGER.info(
                "Answer intent derivation started benchmark_domain=%s map_id=%s grounded_nodes=%d",
                manifest.benchmark_domain,
                manifest.map_id,
                len(simulator_context.grounded_nodes),
            )
            intent = self._policy.derive_intent(
                question_text=request.question.text,
                simulator_context=simulator_context,
            )
            _LOGGER.info(
                "Answer intent derived benchmark_domain=%s map_id=%s node_intents=%d hidden_evidence_refs=%d",
                manifest.benchmark_domain,
                manifest.map_id,
                len(intent.node_intents),
                len(intent.hidden_evidence_refs),
            )

            _LOGGER.info(
                "Expression context build started benchmark_domain=%s map_id=%s node_intents=%d has_profile_context=%s",
                manifest.benchmark_domain,
                manifest.map_id,
                len(intent.node_intents),
                profile_context is not None,
            )
            expression_context = self._expression_builder.build(
                intent=intent,
                simulator_context=simulator_context,
                profile_context=profile_context,
            )
            _LOGGER.info(
                "Expression context built benchmark_domain=%s map_id=%s expression_nodes=%d evidence_signals=%d visible_dialogue_turns=%d has_style_hint=%s",
                manifest.benchmark_domain,
                manifest.map_id,
                len(expression_context.nodes),
                _expression_evidence_signal_count(expression_context),
                len(expression_context.visible_dialogue_turns),
                expression_context.style_hint is not None,
            )
            answer = self._generate_validated_answer(
                expression_context,
                benchmark_domain=manifest.benchmark_domain,
                map_id=manifest.map_id,
            )
            warnings, debug_trace_available = self._apply_debug_trace_preview_options(
                warnings=warnings,
                request=request,
            )
            _LOGGER.info(
                "Simulator preview workflow succeeded benchmark_domain=%s map_id=%s observation_kind=%s warnings=%d debug_trace_available=%s answer_chars=%d",
                manifest.benchmark_domain,
                manifest.map_id,
                VisibleObservationKind.ANSWER.value,
                len(warnings),
                debug_trace_available,
                len(answer.text),
            )
            return SimulatorPreviewResponse(
                answer=answer,
                observation=CoarseObservationMetadata(kind=VisibleObservationKind.ANSWER),
                warnings=warnings,
                debug_trace_available=debug_trace_available,
            )
        except Exception as exc:
            _LOGGER.error(
                "Simulator preview workflow failed benchmark_domain=%s map_id=%s error_type=%s",
                request.benchmark_domain,
                request.map_id,
                type(exc).__name__,
            )
            raise

    def _generate_validated_answer(
        self,
        expression_context: SimulatorExpressionContext,
        *,
        benchmark_domain: str,
        map_id: str,
    ) -> VisibleSimulatorAnswer:
        _LOGGER.info(
            "Simulator answer generation started benchmark_domain=%s map_id=%s generator=%s expression_nodes=%d",
            benchmark_domain,
            map_id,
            type(self._generator).__name__,
            len(expression_context.nodes),
        )
        try:
            candidate_answer = self._generator.render(expression_context)
        except (ModelClientError, TimeoutError) as exc:
            _LOGGER.warning(
                "Simulator answer generation failed benchmark_domain=%s map_id=%s generator=%s error_type=%s fallback=safe",
                benchmark_domain,
                map_id,
                type(self._generator).__name__,
                type(exc).__name__,
            )
            return simulator_safe_fallback()
        _LOGGER.info(
            "Simulator answer generation succeeded benchmark_domain=%s map_id=%s answer_chars=%d",
            benchmark_domain,
            map_id,
            len(candidate_answer.text),
        )

        _LOGGER.info(
            "Simulator answer validation started benchmark_domain=%s map_id=%s validator=%s answer_chars=%d",
            benchmark_domain,
            map_id,
            type(self._validator).__name__,
            len(candidate_answer.text),
        )
        try:
            validation = self._validator.validate(
                candidate_answer=candidate_answer,
                expression_context=expression_context,
            )
        except (ModelClientError, TimeoutError) as exc:
            _LOGGER.warning(
                "Simulator answer validation unavailable benchmark_domain=%s map_id=%s validator=%s error_type=%s fallback=safe",
                benchmark_domain,
                map_id,
                type(self._validator).__name__,
                type(exc).__name__,
            )
            return simulator_safe_fallback()

        _LOGGER.info(
            "Simulator answer validation completed benchmark_domain=%s map_id=%s passed=%s blocking_reasons=%d intent_coverage_notes=%d",
            benchmark_domain,
            map_id,
            validation.passed,
            len(validation.blocking_safety_reasons),
            len(validation.intent_coverage_notes),
        )
        if not validation.passed:
            _LOGGER.warning(
                "Simulator answer validation failed benchmark_domain=%s map_id=%s blocking_reasons=%d fallback=safe",
                benchmark_domain,
                map_id,
                len(validation.blocking_safety_reasons),
            )
            return simulator_safe_fallback()
        return candidate_answer

    def _apply_debug_trace_preview_options(
        self,
        *,
        warnings: tuple[SimulatorPreviewWarning, ...],
        request: SimulatorPreviewRequest,
    ) -> tuple[tuple[SimulatorPreviewWarning, ...], bool | None]:
        if not request.preview_options.include_debug_trace:
            return warnings, None
        _LOGGER.info(
            "Simulator debug trace preview requested benchmark_domain=%s map_id=%s status=unavailable",
            request.benchmark_domain,
            request.map_id,
        )
        return (
            warnings
            + (
                SimulatorPreviewWarning(
                    code=SimulatorPreviewWarningCode.DEBUG_TRACE_UNAVAILABLE,
                    message=(
                        "Debug trace content is not persisted by the stateless "
                        "preview endpoint."
                    ),
                ),
            ),
            False,
        )

    def _load_optional_profile_context(
        self,
        *,
        benchmark_domain: str,
        user_id: str,
    ) -> tuple[object | None, tuple[SimulatorPreviewWarning, ...]]:
        _LOGGER.info(
            "Simulator profile context load started benchmark_domain=%s user_id=%s",
            benchmark_domain,
            user_id,
        )
        try:
            profile_context = load_confirmed_profile_context(
                workspace_root=self._workspace_root,
                benchmark_domain=benchmark_domain,
                user_id=user_id,
            )
        except ConfirmedProfileContextNotFoundError:
            _LOGGER.info(
                "Simulator profile context missing benchmark_domain=%s user_id=%s",
                benchmark_domain,
                user_id,
            )
            return (
                None,
                (
                    SimulatorPreviewWarning(
                        code=SimulatorPreviewWarningCode.MISSING_PROFILE_CONTEXT,
                        message="Profile context is unavailable; preview used neutral wording.",
                    ),
                ),
            )
        _LOGGER.info(
            "Simulator profile context loaded benchmark_domain=%s user_id=%s background_items=%d prior_experience_items=%d goals=%d preferences=%d",
            benchmark_domain,
            user_id,
            len(getattr(profile_context, "background", ())),
            len(getattr(profile_context, "prior_experience", ())),
            len(getattr(profile_context, "goals", ())),
            len(getattr(profile_context, "preferences", ())),
        )
        return profile_context, ()


def _visible_dialogue_turn_count(request: SimulatorPreviewRequest) -> int:
    if request.visible_dialogue_context is None:
        return 0
    return len(request.visible_dialogue_context.turns)


def _simulator_only_evidence_count(simulator_context: SimulatorTurnContext) -> int:
    return sum(
        len(node_context.simulator_only_evidence)
        for node_context in simulator_context.grounded_nodes
    )


def _expression_evidence_signal_count(expression_context: SimulatorExpressionContext) -> int:
    return sum(len(node.evidence_signals) for node in expression_context.nodes)
