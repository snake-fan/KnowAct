from pathlib import Path

from backend.knowact.core.interaction import (
    CoarseObservationMetadata,
    VisibleDialogueContext,
    VisibleObservationKind,
    VisibleSimulatorAnswer,
)
from backend.knowact.llm.client import ModelClientError
from backend.knowact.logging_config import get_knowact_logger
from backend.knowact.simulator.context_builder import (
    SimulatorContextBuilder,
    SimulatorTurnContext,
)
from backend.knowact.simulator.debug_trace import (
    ANSWER_GENERATION_STEP,
    ANSWER_POLICY_STEP,
    QUESTION_GROUNDING_STEP,
    SimulatorDebugTraceRecorder,
    active_simulator_debug_trace,
    current_debug_trace_recorder,
    error_payload,
    question_trace_id_from_request,
    simulator_model_step,
)
from backend.knowact.simulator.fallbacks import (
    simulator_safe_fallback,
)
from backend.knowact.simulator.generators import (
    RuleBasedAnswerGenerator,
    SimulatorAnswerGenerator,
)
from backend.knowact.simulator.grounding import (
    QuestionGrounder,
    RuleBasedQuestionGrounder,
)
from backend.knowact.simulator.policy import (
    RuleBasedAnswerPolicy,
    SimulatorAnswerBlueprint,
    SimulatorAnswerPolicy,
    SimulatorPolicyResult,
    SimulatorResponseMode,
)
from backend.knowact.simulator.turn import (
    SimulatorTurnRequest,
    SimulatorTurnResponse,
    SimulatorTurnTestResponse,
    SimulatorTurnWarning,
    SimulatorTurnWarningCode,
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
_MAX_ANSWER_GENERATION_ATTEMPTS = 2


class SimulatorService:
    def __init__(
        self,
        *,
        workspace_root: Path,
        grounder: QuestionGrounder | None = None,
        policy: SimulatorAnswerPolicy | None = None,
        generator: SimulatorAnswerGenerator | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._grounder = grounder or RuleBasedQuestionGrounder()
        self._context_builder = SimulatorContextBuilder()
        self._fallback_policy = RuleBasedAnswerPolicy()
        self._policy = policy or self._fallback_policy
        self._generator = generator or RuleBasedAnswerGenerator()

    def answer_turn(self, request: SimulatorTurnRequest) -> SimulatorTurnResponse:
        return self._answer_turn(request, expose_grounded_node_ids=False)

    def answer_turn_test(
        self, request: SimulatorTurnRequest
    ) -> SimulatorTurnTestResponse:
        response = self._answer_turn(request, expose_grounded_node_ids=True)
        if not isinstance(response, SimulatorTurnTestResponse):
            raise TypeError("turn test workflow did not produce test response")
        return response

    def _answer_turn(
        self,
        request: SimulatorTurnRequest,
        *,
        expose_grounded_node_ids: bool,
    ) -> SimulatorTurnResponse | SimulatorTurnTestResponse:
        visible_turns = _visible_dialogue_turn_count(request)
        question_trace_id = question_trace_id_from_request(request.question.question_id)
        trace_recorder = SimulatorDebugTraceRecorder(
            workspace_root=self._workspace_root,
            benchmark_domain=request.benchmark_domain,
            map_id=request.map_id,
            question_trace_id=question_trace_id,
        )
        trace_recorder.prepare_output_dir()
        trace_recorder.set_request(
            {
                "benchmark_domain": request.benchmark_domain,
                "map_id": request.map_id,
                "client_provider": request.client_provider,
                "question": request.question.model_dump(mode="json"),
                "question_trace_id": question_trace_id,
                "visible_dialogue_turns": visible_turns,
                "include_debug_trace": request.turn_options.include_debug_trace,
            }
        )
        _LOGGER.info(
            "Simulator turn workflow started benchmark_domain=%s map_id=%s client_provider=%s question_id=%s trace_id=%s visible_dialogue_turns=%d include_debug_trace=%s",
            request.benchmark_domain,
            request.map_id,
            request.client_provider,
            request.question.question_id,
            question_trace_id,
            visible_turns,
            request.turn_options.include_debug_trace,
        )
        with active_simulator_debug_trace(trace_recorder):
            try:
                artifact_loading: dict[str, object] = {}
                manifest = load_reviewed_map_manifest(
                    workspace_root=self._workspace_root,
                    benchmark_domain=request.benchmark_domain,
                    map_id=request.map_id,
                )
                trace_recorder.set_artifact_bindings(
                    {
                        "graph_version": manifest.graph_version,
                        "user_id": manifest.user_id,
                        "reviewed_map_manifest_uri": _reviewed_map_manifest_uri(
                            benchmark_domain=manifest.benchmark_domain,
                            map_id=manifest.map_id,
                        ),
                    }
                )
                artifact_loading["map_manifest"] = {
                    "status": "loaded",
                    "graph_version": manifest.graph_version,
                    "user_id": manifest.user_id,
                }
                trace_recorder.set_workflow_section("artifact_loading", artifact_loading)
                _LOGGER.info(
                    "Simulator turn map manifest loaded benchmark_domain=%s map_id=%s graph_version=%s user_id=%s",
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
                trace_recorder.set_artifact_bindings(
                    {
                        "reviewed_graph_dir_uri": _reviewed_graph_dir_uri(
                            benchmark_domain=manifest.benchmark_domain,
                            graph_version=manifest.graph_version,
                        ),
                    }
                )
                artifact_loading["reviewed_graph"] = {
                    "status": "loaded",
                    "nodes": len(graph_artifacts.graph.nodes),
                    "edges": len(graph_artifacts.graph.edges),
                }
                trace_recorder.set_workflow_section("artifact_loading", artifact_loading)
                _LOGGER.info(
                    "Simulator turn reviewed graph loaded benchmark_domain=%s graph_version=%s nodes=%d edges=%d",
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
                with simulator_model_step(QUESTION_GROUNDING_STEP):
                    grounding = self._grounder.ground(
                        question=request.question,
                        graph=graph_artifacts.graph,
                        visible_dialogue_context=request.visible_dialogue_context,
                    )
                trace_recorder.set_workflow_section(
                    "grounding",
                    {
                        **grounding.model_dump(mode="json"),
                        "grounding_source": grounding.grounding_source,
                        "fallback_reason": grounding.fallback_reason,
                        "has_grounding": grounding.has_grounding,
                        "grounded_node_count": len(grounding.grounded_node_ids),
                    },
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

                if not grounding.has_grounding or grounding.is_multiple_question:
                    simulator_context = _minimal_simulator_context(
                        manifest=manifest,
                        visible_dialogue_context=request.visible_dialogue_context,
                    )
                    trace_recorder.set_workflow_section(
                        "simulator_context",
                        _simulator_context_trace_payload(simulator_context),
                    )
                    policy_result = self._derive_policy_result(
                        question_text=request.question.text,
                        simulator_context=simulator_context,
                        grounding=grounding,
                    )
                    trace_recorder.set_workflow_section(
                        "policy",
                        _policy_result_trace_payload(policy_result),
                    )
                    trace_recorder.set_workflow_section(
                        "answer_generation_input",
                        _answer_generation_input_trace_payload(
                            intent=policy_result.intent,
                            visible_dialogue_context=request.visible_dialogue_context,
                            style_hint=None,
                            regeneration_guidance=(),
                        ),
                    )
                    answer = self._generate_answer(
                        intent=policy_result.intent,
                        visible_dialogue_context=request.visible_dialogue_context,
                        style_hint=None,
                        benchmark_domain=manifest.benchmark_domain,
                        map_id=manifest.map_id,
                    )
                    observation = CoarseObservationMetadata(
                        kind=_observation_kind_for_response_mode(
                            policy_result.intent.response_mode
                        )
                    )
                    response = self._build_turn_response(
                        request=request,
                        trace_recorder=trace_recorder,
                        answer=answer,
                        observation=observation,
                        warnings=(),
                        grounded_node_ids=(
                            grounding.grounded_node_ids
                            if expose_grounded_node_ids
                            else None
                        ),
                    )
                    _LOGGER.info(
                        "Simulator turn workflow succeeded benchmark_domain=%s map_id=%s observation_kind=%s warnings=%d debug_trace_available=%s response_mode=%s",
                        manifest.benchmark_domain,
                        manifest.map_id,
                        observation.kind.value,
                        len(response.warnings),
                        response.debug_trace_available,
                        policy_result.intent.response_mode.value,
                    )
                    return response

                map_artifacts = load_reviewed_map(
                    workspace_root=self._workspace_root,
                    benchmark_domain=request.benchmark_domain,
                    map_id=request.map_id,
                )
                trace_recorder.set_artifact_bindings(
                    {
                        "reviewed_map_uri": _reviewed_map_uri(
                            benchmark_domain=manifest.benchmark_domain,
                            map_id=manifest.map_id,
                        ),
                    }
                )
                artifact_loading["reviewed_map"] = {
                    "status": "loaded",
                    "states": len(map_artifacts.knowledge_map.states),
                    "evidence_records": len(map_artifacts.knowledge_map.evidence),
                }
                trace_recorder.set_workflow_section("artifact_loading", artifact_loading)
                _LOGGER.info(
                    "Simulator turn reviewed map loaded benchmark_domain=%s map_id=%s states=%d evidence_records=%d",
                    manifest.benchmark_domain,
                    manifest.map_id,
                    len(map_artifacts.knowledge_map.states),
                    len(map_artifacts.knowledge_map.evidence),
                )
                profile_context, warnings = self._load_optional_profile_context(
                    benchmark_domain=manifest.benchmark_domain,
                    user_id=manifest.user_id,
                )
                if profile_context is not None:
                    trace_recorder.set_artifact_bindings(
                        {
                            "confirmed_profile_context_uri": _confirmed_profile_context_uri(
                                benchmark_domain=manifest.benchmark_domain,
                                user_id=manifest.user_id,
                            ),
                        }
                    )
                trace_recorder.set_workflow_section(
                    "profile_context",
                    {
                        "available": profile_context is not None,
                        "warning_codes": tuple(warning.code.value for warning in warnings),
                    },
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
                trace_recorder.set_workflow_section(
                    "simulator_context",
                    _simulator_context_trace_payload(simulator_context),
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
                    "Answer blueprint derivation started benchmark_domain=%s map_id=%s grounded_nodes=%d",
                    manifest.benchmark_domain,
                    manifest.map_id,
                    len(simulator_context.grounded_nodes),
                )
                policy_result = self._derive_policy_result(
                    question_text=request.question.text,
                    simulator_context=simulator_context,
                    grounding=grounding,
                )
                trace_recorder.set_workflow_section(
                    "policy",
                    _policy_result_trace_payload(policy_result),
                )
                _LOGGER.info(
                    "Answer blueprint derived benchmark_domain=%s map_id=%s response_mode=%s content_units=%d policy_source=%s",
                    manifest.benchmark_domain,
                    manifest.map_id,
                    policy_result.intent.response_mode.value,
                    len(policy_result.intent.content_units),
                    policy_result.trace.policy_source,
                )

                style_hint = _style_hint(profile_context)
                trace_recorder.set_workflow_section(
                    "answer_generation_input",
                    _answer_generation_input_trace_payload(
                        intent=policy_result.intent,
                        visible_dialogue_context=request.visible_dialogue_context,
                        style_hint=style_hint,
                        regeneration_guidance=(),
                    ),
                )
                _LOGGER.info(
                    "Answer generation input prepared benchmark_domain=%s map_id=%s content_units=%d supporting_cues=%d visible_dialogue_turns=%d has_style_hint=%s",
                    manifest.benchmark_domain,
                    manifest.map_id,
                    len(policy_result.intent.content_units),
                    _supporting_signal_count(policy_result.intent),
                    _visible_dialogue_turn_count(request),
                    style_hint is not None,
                )
                answer = self._generate_answer(
                    intent=policy_result.intent,
                    visible_dialogue_context=request.visible_dialogue_context,
                    style_hint=style_hint,
                    benchmark_domain=manifest.benchmark_domain,
                    map_id=manifest.map_id,
                )
                observation = CoarseObservationMetadata(
                    kind=_observation_kind_for_response_mode(
                        policy_result.intent.response_mode
                    )
                )
                response = self._build_turn_response(
                    request=request,
                    trace_recorder=trace_recorder,
                    answer=answer,
                    observation=observation,
                    warnings=warnings,
                    grounded_node_ids=(
                        grounding.grounded_node_ids
                        if expose_grounded_node_ids
                        else None
                    ),
                )
                _LOGGER.info(
                    "Simulator turn workflow succeeded benchmark_domain=%s map_id=%s observation_kind=%s warnings=%d debug_trace_available=%s answer_chars=%d",
                    manifest.benchmark_domain,
                    manifest.map_id,
                    observation.kind.value,
                    len(response.warnings),
                    response.debug_trace_available,
                    len(answer.text),
                )
                return response
            except Exception as exc:
                trace_recorder.write_debug_trace(
                    status="failed",
                    error=error_payload(exc),
                )
                _LOGGER.error(
                    "Simulator turn workflow failed benchmark_domain=%s map_id=%s error_type=%s",
                    request.benchmark_domain,
                    request.map_id,
                    type(exc).__name__,
                )
                raise

    def _build_turn_response(
        self,
        *,
        request: SimulatorTurnRequest,
        trace_recorder: SimulatorDebugTraceRecorder,
        answer: VisibleSimulatorAnswer,
        observation: CoarseObservationMetadata,
        warnings: tuple[SimulatorTurnWarning, ...],
        grounded_node_ids: tuple[str, ...] | None,
    ) -> SimulatorTurnResponse | SimulatorTurnTestResponse:
        trace_recorder.set_visible_output(
            {
                "answer": answer.model_dump(mode="json"),
                "observation": observation.model_dump(mode="json"),
            }
        )
        trace_recorder.set_warnings(
            tuple(warning.model_dump(mode="json") for warning in warnings)
        )
        trace_recorder.write_debug_trace(status="succeeded")
        include_debug_trace = request.turn_options.include_debug_trace
        response_fields = {
            "answer": answer,
            "observation": observation,
            "warnings": warnings,
            "debug_trace_id": trace_recorder.trace_id if include_debug_trace else None,
            "debug_trace_available": True if include_debug_trace else None,
        }
        if grounded_node_ids is None:
            return SimulatorTurnResponse(**response_fields)
        return SimulatorTurnTestResponse(
            **response_fields,
            grounded_node_ids=grounded_node_ids,
        )

    def _derive_policy_result(
        self,
        *,
        question_text: str,
        simulator_context: SimulatorTurnContext,
        grounding,
    ) -> SimulatorPolicyResult:
        try:
            with simulator_model_step(ANSWER_POLICY_STEP):
                return self._policy.derive(
                    question_text=question_text,
                    simulator_context=simulator_context,
                    grounding=grounding,
                )
        except (ModelClientError, TimeoutError, ValueError) as exc:
            if self._policy is self._fallback_policy:
                raise
            _LOGGER.warning(
                "Simulator answer policy failed policy=%s error_type=%s fallback=rule_based",
                type(self._policy).__name__,
                type(exc).__name__,
            )
            fallback_result = self._fallback_policy.derive(
                question_text=question_text,
                simulator_context=simulator_context,
                grounding=grounding,
            )
            return fallback_result.model_copy(
                update={
                    "trace": fallback_result.trace.model_copy(
                        update={
                            "policy_source": "rule_based_fallback",
                            "fallback_reason": type(exc).__name__,
                        }
                    )
                }
            )

    def _generate_answer(
        self,
        *,
        intent: SimulatorAnswerBlueprint,
        visible_dialogue_context: VisibleDialogueContext | None,
        style_hint: str | None,
        benchmark_domain: str,
        map_id: str,
    ) -> VisibleSimulatorAnswer:
        regeneration_guidance: tuple[str, ...] = ()
        for attempt_index in range(_MAX_ANSWER_GENERATION_ATTEMPTS):
            attempt_number = attempt_index + 1
            _LOGGER.info(
                "Simulator answer generation started benchmark_domain=%s map_id=%s generator=%s content_units=%d attempt=%d",
                benchmark_domain,
                map_id,
                type(self._generator).__name__,
                len(intent.content_units),
                attempt_number,
            )
            try:
                with simulator_model_step(
                    ANSWER_GENERATION_STEP,
                    attempt_index=attempt_number,
                ):
                    candidate_answer = self._generator.render(
                        intent=intent,
                        visible_dialogue_context=visible_dialogue_context,
                        style_hint=style_hint,
                        regeneration_guidance=regeneration_guidance,
                    )
            except (ModelClientError, TimeoutError) as exc:
                _append_generation_attempt(
                    {
                        "attempt_index": attempt_number,
                        "generator": type(self._generator).__name__,
                        "status": "generation_failed",
                        "error": error_payload(exc),
                    }
                )
                if attempt_number < _MAX_ANSWER_GENERATION_ATTEMPTS:
                    _LOGGER.warning(
                        "Simulator answer generation failed benchmark_domain=%s map_id=%s generator=%s error_type=%s retry=answer_generation",
                        benchmark_domain,
                        map_id,
                        type(self._generator).__name__,
                        type(exc).__name__,
                    )
                    regeneration_guidance = _merge_regeneration_guidance(
                        regeneration_guidance,
                        (
                            "Previous generation returned unusable output. Return valid JSON with one safe visible answer.",
                        ),
                    )
                    continue
                _LOGGER.warning(
                    "Simulator answer generation failed benchmark_domain=%s map_id=%s generator=%s error_type=%s fallback=safe",
                    benchmark_domain,
                    map_id,
                    type(self._generator).__name__,
                    type(exc).__name__,
                )
                fallback = simulator_safe_fallback()
                _set_fallback_trace("answer_generation_failed", fallback)
                return fallback
            _LOGGER.info(
                "Simulator answer generation succeeded benchmark_domain=%s map_id=%s answer_chars=%d",
                benchmark_domain,
                map_id,
                len(candidate_answer.text),
            )
            _append_generation_attempt(
                {
                    "attempt_index": attempt_number,
                    "generator": type(self._generator).__name__,
                    "status": "generated",
                    "candidate_answer_chars": len(candidate_answer.text),
                }
            )
            return candidate_answer
        fallback = simulator_safe_fallback()
        _set_fallback_trace("answer_generation_exhausted", fallback)
        return fallback

    def _load_optional_profile_context(
        self,
        *,
        benchmark_domain: str,
        user_id: str,
    ) -> tuple[object | None, tuple[SimulatorTurnWarning, ...]]:
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
                    SimulatorTurnWarning(
                        code=SimulatorTurnWarningCode.MISSING_PROFILE_CONTEXT,
                        message="Profile context is unavailable; simulator used neutral wording.",
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


def _visible_dialogue_turn_count(request: SimulatorTurnRequest) -> int:
    if request.visible_dialogue_context is None:
        return 0
    return len(request.visible_dialogue_context.turns)


def _simulator_only_evidence_count(simulator_context: SimulatorTurnContext) -> int:
    return sum(
        len(node_context.simulator_only_evidence)
        for node_context in simulator_context.grounded_nodes
    )


def _supporting_signal_count(intent: SimulatorAnswerBlueprint) -> int:
    return sum(len(unit.supporting_cues) for unit in intent.content_units)


def _append_generation_attempt(payload: dict[str, object]) -> None:
    recorder = current_debug_trace_recorder()
    if recorder is None:
        return
    recorder.append_generation_attempt(payload)


def _set_fallback_trace(reason: str, answer: VisibleSimulatorAnswer) -> None:
    recorder = current_debug_trace_recorder()
    if recorder is None:
        return
    recorder.set_fallback(
        {
            "reason": reason,
            "answer": answer.model_dump(mode="json"),
        }
    )


def _simulator_context_trace_payload(
    simulator_context: SimulatorTurnContext,
) -> dict[str, object]:
    return {
        "benchmark_domain": simulator_context.benchmark_domain,
        "map_id": simulator_context.map_id,
        "graph_version": simulator_context.graph_version,
        "user_id": simulator_context.user_id,
        "grounded_node_count": len(simulator_context.grounded_nodes),
        "simulator_only_evidence_records": _simulator_only_evidence_count(
            simulator_context
        ),
        "visible_dialogue_turns": (
            0
            if simulator_context.visible_dialogue_context is None
            else len(simulator_context.visible_dialogue_context.turns)
        ),
        "grounded_nodes": tuple(
            {
                "node_id": node_context.state.node_id,
                "node_name": node_context.node.name,
                "mastery_level": node_context.state.mastery_level.value,
                "evidence_refs": node_context.state.evidence_refs,
                "evidence_kinds": tuple(
                    evidence.evidence_kind.value
                    for evidence in node_context.simulator_only_evidence
                ),
            }
            for node_context in simulator_context.grounded_nodes
        ),
    }


def _policy_result_trace_payload(
    policy_result: SimulatorPolicyResult,
) -> dict[str, object]:
    return {
        "answer_blueprint": policy_result.intent.model_dump(mode="json"),
        "decision_trace": policy_result.trace.model_dump(mode="json"),
    }


def _answer_generation_input_trace_payload(
    *,
    intent: SimulatorAnswerBlueprint,
    visible_dialogue_context: VisibleDialogueContext | None,
    style_hint: str | None,
    regeneration_guidance: tuple[str, ...],
) -> dict[str, object]:
    return {
        "content_units": len(intent.content_units),
        "supporting_cues": _supporting_signal_count(intent),
        "visible_dialogue_turns": _visible_dialogue_turn_count_for_context(
            visible_dialogue_context
        ),
        "has_style_hint": style_hint is not None,
        "regeneration_guidance": regeneration_guidance,
    }


def _minimal_simulator_context(
    *,
    manifest,
    visible_dialogue_context,
) -> SimulatorTurnContext:
    return SimulatorTurnContext(
        benchmark_domain=manifest.benchmark_domain,
        map_id=manifest.map_id,
        graph_version=manifest.graph_version,
        user_id=manifest.user_id,
        grounded_nodes=(),
        visible_dialogue_context=visible_dialogue_context,
    )


def _observation_kind_for_response_mode(
    response_mode: SimulatorResponseMode,
) -> VisibleObservationKind:
    if response_mode == SimulatorResponseMode.CLARIFICATION:
        return VisibleObservationKind.CLARIFICATION
    if response_mode in (
        SimulatorResponseMode.NON_ANSWER,
        SimulatorResponseMode.SAFE_NON_ANSWER,
    ):
        return VisibleObservationKind.NON_ANSWER
    return VisibleObservationKind.ANSWER


def _reviewed_map_manifest_uri(*, benchmark_domain: str, map_id: str) -> str:
    return (
        f"benchmark/domains/{benchmark_domain}/maps/{map_id}/map_manifest.json"
    )


def _reviewed_map_uri(*, benchmark_domain: str, map_id: str) -> str:
    return f"benchmark/domains/{benchmark_domain}/maps/{map_id}/map.json"


def _reviewed_graph_dir_uri(*, benchmark_domain: str, graph_version: str) -> str:
    return f"benchmark/domains/{benchmark_domain}/graphs/{graph_version}"


def _confirmed_profile_context_uri(*, benchmark_domain: str, user_id: str) -> str:
    return (
        f"benchmark/domains/{benchmark_domain}/users/{user_id}/profile_context.json"
    )


def _visible_dialogue_turn_count_for_context(
    visible_dialogue_context: VisibleDialogueContext | None,
) -> int:
    if visible_dialogue_context is None:
        return 0
    return len(visible_dialogue_context.turns)


def _style_hint(profile_context: object | None) -> str | None:
    if profile_context is None:
        return None
    preferences = getattr(profile_context, "preferences", ())
    if any("concrete" in preference.lower() for preference in preferences):
        return "Use plain wording with a concrete phrasing preference."
    return "Use neutral first-person wording."


def _merge_regeneration_guidance(
    existing_guidance: tuple[str, ...],
    new_guidance: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*existing_guidance, *new_guidance)))
