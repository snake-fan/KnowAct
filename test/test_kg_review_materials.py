import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = REPOSITORY_ROOT / "experiments" / "01_kg_scientific_validity"
BUILDER_PATH = EXPERIMENT_ROOT / "tools" / "build_review_pages.py"
REVIEW_PAGES_ROOT = EXPERIMENT_ROOT / "materials" / "review_pages"


def _load_builder():
    spec = importlib.util.spec_from_file_location("kg_review_page_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _embedded_json(path: Path, element_id: str):
    raw_html = path.read_text(encoding="utf-8")
    match = re.search(
        rf'<script id="{re.escape(element_id)}" type="application/json">(.*?)</script>',
        raw_html,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"Missing embedded JSON element {element_id} in {path}")
    return json.loads(match.group(1))


class KgReviewMaterialsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = _load_builder()

    def test_three_review_pages_are_bound_to_the_current_candidate_graphs(self):
        expected = {
            "Economy": (22, 20, 50),
            "ISLP": (21, 29, 50),
            "OSTEP": (24, 28, 50),
        }

        for graph_spec in self.builder.GRAPH_SPECS:
            page_path = REVIEW_PAGES_ROOT / graph_spec.output_filename
            package = _embedded_json(page_path, "review-package")
            graph = package["graph"]

            self.assertEqual("knowact.kg_review_package.v1", package["schema_version"])
            self.assertEqual("candidate_graph", package["review_input_kind"])
            self.assertEqual(graph_spec.domain, graph["domain"])
            self.assertEqual(graph_spec.candidate_run_id, graph["candidate_run_id"])
            self.assertEqual(expected[graph_spec.domain], (
                graph["node_count"],
                graph["edge_count"],
                graph["representative_task_count"],
            ))
            self.assertRegex(graph["graph_fingerprint"], r"^sha256:[a-f0-9]{64}$")
            self.assertEqual(graph["node_count"], len(package["nodes"]))
            self.assertEqual(graph["edge_count"], len(package["edges"]))
            self.assertEqual(
                graph["representative_task_count"],
                len(package["scope"]["representative_tasks"]),
            )
            self.assertGreater(len(package["scope"]["review_scope_summary"]), 80)

    def test_comparison_page_contains_exactly_the_same_three_frozen_packages(self):
        packages = _embedded_json(
            REVIEW_PAGES_ROOT / "compare_and_confirm.html",
            "review-packages",
        )
        self.assertEqual(["Economy", "ISLP", "OSTEP"], [item["graph"]["domain"] for item in packages])

        review_fingerprints = {
            _embedded_json(REVIEW_PAGES_ROOT / spec.output_filename, "review-package")[
                "graph"
            ]["graph_fingerprint"]
            for spec in self.builder.GRAPH_SPECS
        }
        comparison_fingerprints = {
            item["graph"]["graph_fingerprint"] for item in packages
        }
        self.assertEqual(review_fingerprints, comparison_fingerprints)

    def test_generated_pages_are_current(self):
        outputs = self.builder.build_outputs()
        self.assertTrue(self.builder.check_outputs(outputs))

    def test_review_pages_explain_every_node_and_edge_review_label(self):
        expected_fields = {
            "scope_fit",
            "granularity",
            "diagnostic_usefulness",
            "rubric_quality",
            "relation_validity",
            "type_correct",
            "replacement_type",
            "direction_correct",
            "provenance_class",
            "decision",
            "proposed_change",
            "rationale",
        }
        for graph_spec in self.builder.GRAPH_SPECS:
            raw_html = (REVIEW_PAGES_ROOT / graph_spec.output_filename).read_text(
                encoding="utf-8"
            )
            self.assertEqual(2, raw_html.count('"标签速查 / Label guide"'))
            self.assertIn("图谱知识范围 / Graph knowledge scope", raw_html)
            self.assertIn('class="scope-summary"', raw_html)
            self.assertNotIn('class="scope-tag"', raw_html)
            self.assertNotIn("<h4>Excluded topics</h4>", raw_html)
            self.assertNotIn("<h4>Review boundary</h4>", raw_html)
            for field in expected_fields:
                self.assertIn(f'field: "{field}"', raw_html)

    def test_json_schemas_are_parseable_and_csv_forms_are_retired(self):
        schema_root = EXPERIMENT_ROOT / "materials" / "schemas"
        review_schema = json.loads(
            (schema_root / "kg_review_submission.schema.json").read_text(encoding="utf-8")
        )
        confirmation_schema = json.loads(
            (schema_root / "kg_review_confirmation.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            "knowact.kg_review_submission.v3",
            review_schema["properties"]["schema_version"]["const"],
        )
        self.assertEqual(
            "knowact.kg_review_confirmation.v3",
            confirmation_schema["properties"]["schema_version"]["const"],
        )
        reviewer_schema = review_schema["properties"]["reviewer"]
        expected_reviewer_fields = {
            "reviewer_id",
            "role",
            "experience_band",
            "introduction",
        }
        self.assertEqual(expected_reviewer_fields, set(reviewer_schema["required"]))
        self.assertEqual(expected_reviewer_fields, set(reviewer_schema["properties"]))
        self.assertFalse(reviewer_schema["additionalProperties"])
        self.assertNotIn("review_period", review_schema["required"])
        self.assertNotIn("review_period", review_schema["properties"])
        node_review_schema = review_schema["$defs"]["node_review"]
        edge_review_schema = review_schema["$defs"]["edge_review"]
        self.assertNotIn("source_support", node_review_schema["required"])
        self.assertNotIn("source_support", node_review_schema["properties"])
        self.assertNotIn("review_minutes", node_review_schema["required"])
        self.assertNotIn("review_minutes", node_review_schema["properties"])
        self.assertNotIn("review_minutes", edge_review_schema["required"])
        self.assertNotIn("review_minutes", edge_review_schema["properties"])

        input_review_schema = confirmation_schema["properties"]["input_reviews"]["items"]
        self.assertIn("reviewer_id", input_review_schema["required"])
        self.assertNotIn("reviewer_code", input_review_schema["properties"])
        self.assertEqual([], list((EXPERIMENT_ROOT / "materials").glob("*.csv")))


if __name__ == "__main__":
    unittest.main()
