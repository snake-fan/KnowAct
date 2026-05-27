import json
import tempfile
import unittest
from pathlib import Path

from backend.knowact.authoring.logging import GraphAuthoringWorkflowRunError
from backend.knowact.authoring.output import (
    GraphAuthoringIntermediateArtifactWriter,
    write_graph_authoring_output,
    write_graph_authoring_run_log,
)
from backend.knowact.authoring.openai_workflow import build_openai_graph_authoring_workflow
from backend.knowact.authoring.parsers.graph_authoring import (
    AuthoringOutputParseError,
    parse_node_rubric_authoring_output,
)
from backend.knowact.authoring.schemas import (
    EdgeProposalInput,
    NodeRubricAuthoringInput,
    NodeRubricAuthoringResult,
    NodeRubricPatch,
    SourceGroundedNodeSkeleton,
    SourceMaterial,
)
from backend.knowact.authoring.templates.edge_proposal import build_edge_proposal_messages
from backend.knowact.authoring.templates.node_extraction import build_node_extraction_messages
from backend.knowact.authoring.templates.node_rubric_authoring import build_node_rubric_authoring_messages
from backend.knowact.authoring.workflow import GraphAuthoringAgentWorkflow
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode, SourceLocator
from backend.knowact.core.map import MasteryLevel
from backend.knowact.llm.messages import DEEPSEEK_MESSAGE_PROFILE
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.graph import validate_knowledge_graph


class V1GraphAuthoringWorkflowTest(unittest.TestCase):
    def test_graph_authoring_workflow_writes_exactly_candidate_node_and_edge_lists(self):
        workflow = GraphAuthoringAgentWorkflow(
            node_extraction_step=FixtureNodeExtractionStep(),
            node_rubric_authoring_step=FixtureNodeRubricAuthoringStep(),
            edge_proposal_step=FixtureEdgeProposalStep(),
        )

        result = workflow.run([_source_material()])

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            nodes_path, edges_path = write_graph_authoring_output(result, output_dir)

            self.assertEqual({"candidate_nodes.json", "candidate_edges.json"}, {path.name for path in output_dir.iterdir()})

            raw_nodes = _load_json(nodes_path)
            raw_edges = _load_json(edges_path)
            self.assertEqual(5, len(raw_nodes))
            self.assertEqual(4, len(raw_edges))

            for raw_node in raw_nodes:
                self.assertNotIn("candidate", raw_node)
                self.assertNotIn("candidate_status", raw_node)
                self.assertNotIn("review_status", raw_node)
                self.assertIn("definition", raw_node)
                self.assertEqual({level.value for level in MasteryLevel}, set(raw_node["levels"].keys()))

            for raw_edge in raw_edges:
                self.assertNotIn("definition", raw_edge)
                self.assertNotIn("diagnostic_goal", raw_edge)
                self.assertNotIn("levels", raw_edge)
                self.assertNotIn("source_locators", raw_edge)
                self.assertNotIn("candidate_status", raw_edge)

            graph = KnowledgeGraph(
                nodes=tuple(KnowledgeNode.model_validate(raw_node) for raw_node in raw_nodes),
                edges=tuple(KnowledgeEdge.model_validate(raw_edge) for raw_edge in raw_edges),
            )
            validate_knowledge_graph(graph)

    def test_graph_authoring_workflow_records_structured_run_log(self):
        workflow = GraphAuthoringAgentWorkflow(
            node_extraction_step=FixtureNodeExtractionStep(),
            node_rubric_authoring_step=FixtureNodeRubricAuthoringStep(),
            edge_proposal_step=FixtureEdgeProposalStep(),
        )
        source_material = _source_material()

        run_result = workflow.run_with_log([source_material], run_id="dev_run_001")

        run_log = run_result.run_log
        self.assertEqual("dev_run_001", run_log.run_id)
        self.assertEqual("Graph Authoring Agent Workflow", run_log.workflow_name)
        self.assertEqual("succeeded", run_log.status)
        self.assertIsNotNone(run_log.completed_at)
        self.assertEqual(1, len(run_log.source_materials))
        self.assertEqual("isl_python", run_log.source_materials[0].source_id)
        self.assertEqual("Development fixture excerpt", run_log.source_materials[0].citation)
        self.assertFalse(hasattr(run_log.source_materials[0], "text"))

        entries_by_name = {entry.entry_name: entry for entry in run_log.entries}
        self.assertEqual(
            {
                "node_extraction",
                "validate_source_grounded_node_skeletons",
                "node_rubric_authoring",
                "validate_complete_candidate_nodes",
                "edge_proposal",
                "validate_candidate_edges",
            },
            set(entries_by_name),
        )
        self.assertEqual({"source_materials": 1}, entries_by_name["node_extraction"].input_counts)
        self.assertEqual({"skeletons": 5}, entries_by_name["node_extraction"].output_counts)
        self.assertEqual(
            {"node_rubric_patches": 5, "candidate_nodes": 5},
            entries_by_name["node_rubric_authoring"].output_counts,
        )
        self.assertEqual({"candidate_edges": 4}, entries_by_name["edge_proposal"].output_counts)
        self.assertEqual("passed", entries_by_name["validate_candidate_edges"].validation_result)

        serialized_log = json.dumps(run_log.model_dump(mode="json", exclude_none=True))
        self.assertNotIn(source_material.text, serialized_log)
        self.assertNotIn("Source material:", serialized_log)

    def test_graph_authoring_workflow_canonicalizes_contrasts_with_edges_in_code(self):
        workflow = GraphAuthoringAgentWorkflow(
            node_extraction_step=FixtureNodeExtractionStep(),
            node_rubric_authoring_step=FixtureNodeRubricAuthoringStep(),
            edge_proposal_step=ReversedContrastsEdgeProposalStep(),
        )

        result = workflow.run([_source_material()])

        self.assertEqual(1, len(result.candidate_edges))
        edge = result.candidate_edges[0]
        self.assertEqual("edge_linear_regression_contrasts_with_logistic_regression", edge.id)
        self.assertEqual("linear_regression", edge.source)
        self.assertEqual("logistic_regression", edge.target)
        validate_knowledge_graph(KnowledgeGraph(nodes=result.candidate_nodes, edges=result.candidate_edges))

    def test_graph_authoring_run_log_can_be_written_as_sidecar_artifact(self):
        workflow = GraphAuthoringAgentWorkflow(
            node_extraction_step=FixtureNodeExtractionStep(),
            node_rubric_authoring_step=FixtureNodeRubricAuthoringStep(),
            edge_proposal_step=FixtureEdgeProposalStep(),
        )
        run_result = workflow.run_with_log([_source_material()], run_id="dev_run_001")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            log_path = write_graph_authoring_run_log(run_result.run_log, output_dir)

            self.assertEqual("workflow_log.json", log_path.name)
            raw_log = _load_json(log_path)
            self.assertEqual("dev_run_001", raw_log["run_id"])
            self.assertEqual("succeeded", raw_log["status"])
            self.assertEqual(6, len(raw_log["entries"]))

    def test_graph_authoring_workflow_writes_validated_intermediate_artifacts(self):
        workflow = GraphAuthoringAgentWorkflow(
            node_extraction_step=FixtureNodeExtractionStep(),
            node_rubric_authoring_step=FixtureNodeRubricAuthoringStep(),
            edge_proposal_step=FixtureEdgeProposalStep(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            run_result = workflow.run_with_log(
                [_source_material()],
                run_id="intermediate_run_001",
                intermediate_artifact_writer=GraphAuthoringIntermediateArtifactWriter(output_dir),
            )

            entries_by_name = {entry.entry_name: entry for entry in run_result.run_log.entries}
            skeleton_uri = entries_by_name["validate_source_grounded_node_skeletons"].artifact_uris[
                "source_grounded_node_skeletons"
            ]
            rubric_uri = entries_by_name["validate_complete_candidate_nodes"].artifact_uris[
                "node_rubric_patches"
            ]
            node_uri = entries_by_name["validate_complete_candidate_nodes"].artifact_uris[
                "candidate_nodes_pre_edge"
            ]
            edge_uri = entries_by_name["validate_candidate_edges"].artifact_uris[
                "candidate_edges_canonical"
            ]

            self.assertEqual("intermediate/source_grounded_node_skeletons.json", skeleton_uri)
            self.assertEqual("intermediate/node_rubric_patches.json", rubric_uri)
            self.assertEqual("intermediate/candidate_nodes_pre_edge.json", node_uri)
            self.assertEqual("intermediate/candidate_edges_canonical.json", edge_uri)
            self.assertEqual(
                "train_test_split",
                _load_json(output_dir / skeleton_uri)[0]["id"],
            )
            self.assertIn("source_grounding_notes", _load_json(output_dir / skeleton_uri)[0])
            self.assertEqual(
                "train_test_split",
                _load_json(output_dir / rubric_uri)[0]["id"],
            )
            self.assertEqual(5, len(_load_json(output_dir / node_uri)))
            self.assertEqual(4, len(_load_json(output_dir / edge_uri)))

    def test_graph_authoring_workflow_rejects_incomplete_candidate_node_rubrics(self):
        workflow = GraphAuthoringAgentWorkflow(
            node_extraction_step=FixtureNodeExtractionStep(),
            node_rubric_authoring_step=IncompleteNodeRubricAuthoringStep(),
            edge_proposal_step=FixtureEdgeProposalStep(),
        )

        with self.assertRaises(GraphAuthoringWorkflowRunError) as context:
            workflow.run([_source_material()])
        self.assertIsInstance(context.exception.cause, KnowActValidationError)
        self.assertEqual("failed", context.exception.run_log.status)
        failed_entry = context.exception.run_log.entries[-1]
        self.assertEqual("validate_complete_candidate_nodes", failed_entry.entry_name)
        self.assertEqual("failed", failed_entry.status)
        self.assertEqual("failed", failed_entry.validation_result)
        self.assertEqual("KnowActValidationError", failed_entry.error.error_type)
        self.assertIn("exactly L0-L5", failed_entry.error.message)

    def test_graph_authoring_workflow_redacts_sensitive_error_messages_in_run_log(self):
        workflow = GraphAuthoringAgentWorkflow(
            node_extraction_step=SecretFailingNodeExtractionStep(),
            node_rubric_authoring_step=FixtureNodeRubricAuthoringStep(),
            edge_proposal_step=FixtureEdgeProposalStep(),
        )

        with self.assertRaises(GraphAuthoringWorkflowRunError) as context:
            workflow.run_with_log([_source_material()], run_id="bad_run_001")

        raw_log = context.exception.run_log.model_dump(mode="json", exclude_none=True)
        serialized_log = json.dumps(raw_log)
        self.assertIn("sk-[REDACTED]", serialized_log)
        self.assertIn("api_key=[REDACTED]", serialized_log)
        self.assertNotIn("sk-testsecret123456", serialized_log)
        self.assertNotIn("api_key=visible-secret", serialized_log)

    def test_openai_workflow_builder_wires_llm_steps_behind_model_client_interface(self):
        model_client = FakeRawJSONWorkflowModelClient()
        workflow = build_openai_graph_authoring_workflow(model_client=model_client)

        result = workflow.run([_source_material()])

        self.assertEqual(("train_test_split",), tuple(node.id for node in result.candidate_nodes))
        self.assertEqual(
            ("chapter_2",),
            tuple(locator.locator for locator in result.candidate_nodes[0].source_locators),
        )
        self.assertEqual(
            ["Node Extraction Agent Step", "Node Rubric Authoring Agent Step", "Edge Proposal Agent Step"],
            model_client.prompt_markers,
        )

    def test_llm_agent_steps_record_raw_model_output_and_parser_output_in_run_log(self):
        model_client = FakeRawJSONWorkflowModelClient()
        workflow = build_openai_graph_authoring_workflow(model_client=model_client)

        run_result = workflow.run_with_log([_source_material()], run_id="trace_run_001")

        entries_by_name = {entry.entry_name: entry for entry in run_result.run_log.entries}
        node_extraction_trace = entries_by_name["node_extraction"].agent_trace
        self.assertIsNotNone(node_extraction_trace)
        self.assertIn('"skeletons"', node_extraction_trace.model_raw_output)
        self.assertEqual("succeeded", node_extraction_trace.parser_result.status)
        self.assertEqual(
            "train_test_split",
            node_extraction_trace.parser_result.output["skeletons"][0]["id"],
        )

        rubric_trace = entries_by_name["node_rubric_authoring"].agent_trace
        self.assertIsNotNone(rubric_trace)
        self.assertEqual("succeeded", rubric_trace.parser_result.status)
        self.assertEqual("train_test_split", rubric_trace.parser_result.output["nodes"][0]["id"])
        self.assertNotIn("source_locators", rubric_trace.parser_result.output["nodes"][0])
        self.assertEqual(1, len(rubric_trace.batch_traces))
        self.assertEqual("batch_001", rubric_trace.batch_traces[0].batch_name)
        self.assertEqual({"skeletons": 1}, rubric_trace.batch_traces[0].input_counts)

        edge_trace = entries_by_name["edge_proposal"].agent_trace
        self.assertIsNotNone(edge_trace)
        self.assertEqual("succeeded", edge_trace.parser_result.status)
        self.assertEqual({"edges": []}, edge_trace.parser_result.output)

    def test_written_run_log_externalizes_agent_trace_artifacts(self):
        model_client = FakeRawJSONWorkflowModelClient()
        workflow = build_openai_graph_authoring_workflow(model_client=model_client)
        run_result = workflow.run_with_log([_source_material()], run_id="trace_run_001")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            log_path = write_graph_authoring_run_log(run_result.run_log, output_dir)

            raw_log = _load_json(log_path)
            entries_by_name = {entry["entry_name"]: entry for entry in raw_log["entries"]}
            node_trace = entries_by_name["node_extraction"]["agent_trace"]
            self.assertNotIn("model_raw_output", node_trace)
            self.assertEqual(
                "agent_traces/node_extraction/model_raw_output.txt",
                node_trace["model_raw_output_uri"],
            )
            self.assertNotIn("output", node_trace["parser_result"])
            self.assertEqual(
                "agent_traces/node_extraction/parser_output.json",
                node_trace["parser_result"]["output_uri"],
            )

            raw_output_path = output_dir / node_trace["model_raw_output_uri"]
            parser_output_path = output_dir / node_trace["parser_result"]["output_uri"]
            self.assertIn('"skeletons"', raw_output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                "train_test_split",
                _load_json(parser_output_path)["skeletons"][0]["id"],
            )

            rubric_trace = entries_by_name["node_rubric_authoring"]["agent_trace"]
            rubric_batch_trace = rubric_trace["batch_traces"][0]
            self.assertEqual(
                "agent_traces/node_rubric_authoring/batch_001/model_raw_output.txt",
                rubric_batch_trace["model_raw_output_uri"],
            )
            self.assertEqual(
                "agent_traces/node_rubric_authoring/batch_001/parser_output.json",
                rubric_batch_trace["parser_result"]["output_uri"],
            )
            self.assertTrue((output_dir / rubric_batch_trace["model_raw_output_uri"]).exists())

    def test_llm_agent_step_parse_failures_record_raw_model_output_in_run_log(self):
        workflow = build_openai_graph_authoring_workflow(model_client=InvalidJSONGraphModelClient())

        with self.assertRaises(GraphAuthoringWorkflowRunError) as context:
            workflow.run_with_log([_source_material()], run_id="bad_json_run_001")

        failed_entry = context.exception.run_log.entries[-1]
        self.assertEqual("node_extraction", failed_entry.entry_name)
        self.assertEqual("AuthoringOutputParseError", failed_entry.error.error_type)
        self.assertIn("not valid JSON", failed_entry.error.message)
        self.assertIsNotNone(failed_entry.agent_trace)
        self.assertEqual("I cannot return JSON for this request.", failed_entry.agent_trace.model_raw_output)
        self.assertEqual("failed", failed_entry.agent_trace.parser_result.status)
        self.assertEqual(
            "AuthoringOutputParseError",
            failed_entry.agent_trace.parser_result.error.error_type,
        )

    def test_node_rubric_parser_rejects_missing_required_rubric_fields(self):
        raw_output = json.dumps(
            {
                "nodes": [
                    {
                        "id": "train_test_split",
                        "levels": {
                            "L0": "Does not recognize train/test split.",
                            "L1": "Recognizes the term but cannot explain its purpose.",
                        },
                        "diagnostic_signals": [
                            "Explains the purpose of separating training and test data."
                        ],
                        "simulator_behavior": (
                            "Answer naturally about train/test split without naming mastery labels."
                        ),
                    }
                ]
            }
        )

        with self.assertRaises(AuthoringOutputParseError):
            parse_node_rubric_authoring_output(raw_output)

    def test_graph_authoring_templates_are_split_and_include_knowledge_graph_guardrails(self):
        source_materials = [_source_material()]

        extraction_prompt = _render_prompt(build_node_extraction_messages(source_materials))
        self.assertIn("Source-Grounded Node Skeletons", extraction_prompt)
        self.assertIn("roughly 1-3 focused diagnostic questions", extraction_prompt)
        self.assertIn("Do not output diagnostic_goal", extraction_prompt)
        self.assertIn("Parsed Source Markdown", extraction_prompt)
        self.assertIn('"skeletons"', extraction_prompt)

        skeletons = FixtureNodeExtractionStep().run(source_materials)
        rubric_prompt = _render_prompt(
            build_node_rubric_authoring_messages(
                NodeRubricAuthoringInput(skeletons=skeletons)
            )
        )
        self.assertIn("Global L0-L5 MasteryScale", rubric_prompt)
        self.assertIn("Do not use candidate edges", rubric_prompt)
        self.assertIn("positive signs, negative signs, and common misconceptions", rubric_prompt)
        self.assertIn("Do not output name, type, definition, or source_locators", rubric_prompt)
        self.assertIn("source_grounding_notes", rubric_prompt)
        self.assertIn('"L5"', rubric_prompt)
        self.assertNotIn(source_materials[0].text, rubric_prompt)

        candidate_nodes = FixtureNodeRubricAuthoringStep().run(
            NodeRubricAuthoringInput(skeletons=skeletons)
        ).candidate_nodes
        edge_prompt = _render_prompt(
            build_edge_proposal_messages(
                EdgeProposalInput(
                    candidate_nodes=candidate_nodes,
                    source_grounded_node_skeletons=skeletons,
                )
            )
        )
        self.assertIn("precision-first", edge_prompt)
        self.assertIn("part_of", edge_prompt)
        self.assertIn("prerequisite_for", edge_prompt)
        self.assertIn("supports", edge_prompt)
        self.assertIn("contrasts_with", edge_prompt)
        self.assertIn("curation_confidence", edge_prompt)
        self.assertIn("source_grounding_notes", edge_prompt)
        self.assertIn("Omit weak, speculative, merely related", edge_prompt)
        self.assertNotIn("lexicographic", edge_prompt)
        self.assertNotIn("node-id order", edge_prompt)
        self.assertNotIn(source_materials[0].text, edge_prompt)

        self.assertIn("Parsed Source Markdown", extraction_prompt)
        self.assertIn('source_id "isl_python"', extraction_prompt)
        self.assertIn(source_materials[0].text, extraction_prompt)
        self.assertNotIn("uploaded original PDF", extraction_prompt)
        for prompt in (rubric_prompt, edge_prompt):
            self.assertNotIn("Parsed Source Markdown for source_id", prompt)
            self.assertIn("isl_python", prompt)
            self.assertNotIn("uploaded original PDF", prompt)

    def test_graph_authoring_templates_render_high_priority_instructions_for_message_profile(self):
        source_materials = [_source_material()]

        default_messages = build_node_extraction_messages(source_materials)
        deepseek_messages = build_node_extraction_messages(
            source_materials,
            message_profile=DEEPSEEK_MESSAGE_PROFILE,
        )

        self.assertEqual("developer", default_messages[0].role)
        self.assertEqual("system", deepseek_messages[0].role)
        self.assertEqual("user", deepseek_messages[1].role)


class FixtureNodeExtractionStep:
    def run(self, source_materials):
        self._assert_source_material(source_materials)
        return tuple(
            SourceGroundedNodeSkeleton(
                id=node_id,
                name=name,
                definition=definition,
                source_locators=(
                    SourceLocator(source_id="isl_python", locator=locator, note="Development fixture locator"),
                ),
                source_grounding_notes=(
                    f"The fixture source describes {name} in {locator}.",
                ),
            )
            for node_id, name, definition, locator in [
                (
                    "train_test_split",
                    "Train Test Split",
                    "Separating data into training and test sets to estimate out-of-sample performance.",
                    "chapter_2",
                ),
                (
                    "linear_regression",
                    "Linear Regression",
                    "A supervised regression method that models a quantitative response as a linear function.",
                    "chapter_3",
                ),
                (
                    "logistic_regression",
                    "Logistic Regression",
                    "A supervised classification method that models class probabilities through a logistic link.",
                    "chapter_4",
                ),
                (
                    "bias_variance_tradeoff",
                    "Bias Variance Tradeoff",
                    "The relationship between model flexibility, systematic error, variance, and test error.",
                    "chapter_2",
                ),
                (
                    "confusion_matrix",
                    "Confusion Matrix",
                    "A table of predicted and true classes used to inspect classification outcomes.",
                    "chapter_4",
                ),
            ]
        )

    def _assert_source_material(self, source_materials):
        if len(source_materials) != 1 or source_materials[0].source_id != "isl_python":
            raise AssertionError("fixture expected ISL Python source material")


class SecretFailingNodeExtractionStep:
    def run(self, source_materials):
        raise RuntimeError("failed with sk-testsecret123456 and api_key=visible-secret")


class FixtureNodeRubricAuthoringStep:
    def run(self, input_data):
        candidate_nodes = tuple(
            _complete_candidate_node(skeleton) for skeleton in input_data.skeletons
        )
        return NodeRubricAuthoringResult(
            rubric_patches=tuple(
                NodeRubricPatch.model_validate(_rubric_patch_payload(node))
                for node in candidate_nodes
            ),
            candidate_nodes=candidate_nodes,
        )


class IncompleteNodeRubricAuthoringStep:
    def run(self, input_data):
        candidate_nodes = tuple(
            _complete_candidate_node(skeleton, include_l5=False)
            for skeleton in input_data.skeletons
        )
        return NodeRubricAuthoringResult(
            rubric_patches=tuple(
                NodeRubricPatch.model_validate(_rubric_patch_payload(node))
                for node in candidate_nodes
            ),
            candidate_nodes=candidate_nodes,
        )


class FixtureEdgeProposalStep:
    def run(self, input_data):
        return (
            KnowledgeEdge(
                id="edge_bias_variance_tradeoff_supports_train_test_split",
                source="bias_variance_tradeoff",
                target="train_test_split",
                type="supports",
                rationale="Bias-variance reasoning helps explain why held-out performance matters.",
                weight=0.7,
                curation_confidence=0.85,
            ),
            KnowledgeEdge(
                id="edge_train_test_split_supports_linear_regression",
                source="train_test_split",
                target="linear_regression",
                type="supports",
                rationale="Train/test split helps diagnose whether a fitted linear model generalizes.",
                weight=0.7,
                curation_confidence=0.9,
            ),
            KnowledgeEdge(
                id="edge_confusion_matrix_supports_logistic_regression",
                source="confusion_matrix",
                target="logistic_regression",
                type="supports",
                rationale="A confusion matrix helps evaluate thresholded logistic regression predictions.",
                weight=0.75,
                curation_confidence=0.88,
            ),
            KnowledgeEdge(
                id="edge_linear_regression_contrasts_with_logistic_regression",
                source="linear_regression",
                target="logistic_regression",
                type="contrasts_with",
                rationale="The two methods are commonly compared by response type, link function, and output interpretation.",
                weight=0.8,
                curation_confidence=0.9,
            ),
        )


class ReversedContrastsEdgeProposalStep:
    def run(self, input_data):
        return (
            KnowledgeEdge(
                id="edge_logistic_regression_contrasts_with_linear_regression",
                source="logistic_regression",
                target="linear_regression",
                type="contrasts_with",
                rationale="The two methods are compared by response type, link function, and output interpretation.",
                weight=0.8,
                curation_confidence=0.9,
            ),
        )


class FakeRawJSONWorkflowModelClient:
    def __init__(self):
        self.prompt_markers = []
        self._skeleton = SourceGroundedNodeSkeleton(
            id="train_test_split",
            name="Train Test Split",
            definition="Separating data into training and test sets to estimate out-of-sample performance.",
            source_locators=(
                SourceLocator(source_id="isl_python", locator="chapter_2", note="Development fixture locator"),
            ),
            source_grounding_notes=(
                "The fixture source introduces train/test split as a way to estimate out-of-sample performance.",
            ),
        )

    def complete(self, *, messages):
        developer_prompt = messages[0].content
        if "Node Extraction Agent Step" in developer_prompt:
            self.prompt_markers.append("Node Extraction Agent Step")
            return json.dumps({"skeletons": [self._skeleton.model_dump(mode="json")]})
        if "Node Rubric Authoring Agent Step" in developer_prompt:
            self.prompt_markers.append("Node Rubric Authoring Agent Step")
            node = _complete_candidate_node(self._skeleton)
            return json.dumps({"nodes": [_rubric_patch_payload(node)]})
        if "Edge Proposal Agent Step" in developer_prompt:
            self.prompt_markers.append("Edge Proposal Agent Step")
            return json.dumps({"edges": []})
        raise AssertionError(f"unexpected prompt: {developer_prompt}")


class InvalidJSONGraphModelClient(FakeRawJSONWorkflowModelClient):
    def complete(self, *, messages):
        self.prompt_markers.append("Node Extraction Agent Step")
        return "I cannot return JSON for this request."


def _complete_candidate_node(
    skeleton: SourceGroundedNodeSkeleton,
    *,
    include_l5: bool = True,
) -> KnowledgeNode:
    levels = {
        "L0": f"Does not recognize {skeleton.name}.",
        "L1": f"Recognizes {skeleton.name} but cannot explain it.",
        "L2": f"Can give a shallow procedural description of {skeleton.name}.",
        "L3": f"Can explain and use the core idea of {skeleton.name}.",
        "L4": f"Connects {skeleton.name} to model assessment and related concepts.",
    }
    if include_l5:
        levels["L5"] = f"Can transfer {skeleton.name} reasoning to nuanced cases."

    return KnowledgeNode(
        id=skeleton.id,
        name=skeleton.name,
        type=skeleton.type,
        definition=skeleton.definition,
        source_locators=skeleton.source_locators,
        diagnostic_goal=f"Assess whether the user can explain and apply {skeleton.name}.",
        levels=levels,
        diagnostic_signals=(
            f"Explains the core purpose of {skeleton.name}.",
            f"Uses {skeleton.name} in a concrete supervised learning scenario.",
        ),
        simulator_behavior=f"Answer naturally about {skeleton.name} without naming mastery labels.",
    )


def _rubric_patch_payload(node: KnowledgeNode) -> dict[str, object]:
    return {
        "id": node.id,
        "diagnostic_goal": node.diagnostic_goal,
        "levels": node.levels,
        "diagnostic_signals": list(node.diagnostic_signals),
        "simulator_behavior": node.simulator_behavior,
    }


def _source_material() -> SourceMaterial:
    return SourceMaterial(
        source_id="isl_python",
        title="An Introduction to Statistical Learning with Applications in Python",
        citation="Development fixture excerpt",
        text=(
            "Chapter 2 introduces train/test split and the bias-variance tradeoff. "
            "Chapter 3 covers linear regression. Chapter 4 covers logistic regression "
            "and confusion matrices."
        ),
    )


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _render_prompt(messages) -> str:
    return "\n\n".join(message.content for message in messages)


if __name__ == "__main__":
    unittest.main()
