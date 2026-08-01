import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from backend.knowact.core.simulator_experiment import SimulatorExperimentQuestion
from backend.knowact.storage.simulator_experiments import (
    SimulatorExperimentArtifactError,
    list_question_banks,
    load_question_bank,
)


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BANKS = {
    "economy_atomic_v2": "Economy",
    "islp_atomic_v2": "ISLP",
    "ostep_atomic_v2": "OSTEP",
}


class V1SimulatorQuestionBankTest(unittest.TestCase):
    def test_catalog_contains_eighty_reviewed_questions_for_each_domain(self):
        summaries = list_question_banks(workspace_root=WORKSPACE_ROOT)

        self.assertEqual(EXPECTED_BANKS, {
            summary.bank_id: summary.benchmark_domain for summary in summaries
        })
        for summary in summaries:
            self.assertEqual(80, summary.question_count)
            bank = load_question_bank(
                workspace_root=WORKSPACE_ROOT,
                bank_id=summary.bank_id,
            )
            self.assertEqual(80, len(bank.questions))
            self.assertTrue(
                all(not question.reviewed_target_node_ids for question in bank.questions)
            )
            self.assertTrue(
                all(question.source_reference_ids for question in bank.questions)
            )

    def test_question_schema_rejects_more_than_one_ask(self):
        with self.assertRaisesRegex(ValidationError, "multiple requested operations"):
            SimulatorExperimentQuestion.model_validate(
                {
                    "question_id": "TEST_Q001",
                    "target_concept": "test_concept",
                    "question_type": "explanation",
                    "cognitive_operation": "explain",
                    "prompts": {
                        "en": (
                            "Identify overfitting and explain why it harms test error?"
                        ),
                        "zh_cn": "什么是过拟合？",
                    },
                    "source_reference_ids": ["test-source"],
                    "reviewed_target_node_ids": [],
                }
            )

    def test_content_change_without_a_new_review_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            bank_root = workspace_root / "benchmark" / "question_banks"
            review_root = bank_root / "reviews"
            review_root.mkdir(parents=True)
            source_bank = (
                WORKSPACE_ROOT
                / "benchmark"
                / "question_banks"
                / "economy_atomic_v2.json"
            )
            source_review = (
                WORKSPACE_ROOT
                / "benchmark"
                / "question_banks"
                / "reviews"
                / "economy_atomic_v2.quality_review.json"
            )
            destination_bank = bank_root / source_bank.name
            shutil.copy2(source_bank, destination_bank)
            shutil.copy2(source_review, review_root / source_review.name)

            payload = json.loads(destination_bank.read_text(encoding="utf-8"))
            payload["questions"][0]["prompts"]["en"] = (
                "Which GDP measure best indicates whether real output increased?"
            )
            destination_bank.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                SimulatorExperimentArtifactError,
                "content hash does not match",
            ):
                load_question_bank(
                    workspace_root=workspace_root,
                    bank_id="economy_atomic_v2",
                )


if __name__ == "__main__":
    unittest.main()
