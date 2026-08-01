import json
from hashlib import sha256
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.knowact.api.app import create_app
from backend.knowact.authoring.map_authoring_output import (
    CandidateMapAuthoringRunLog,
    read_candidate_map_run,
)
from backend.knowact.simulator.service import SimulatorService


DOMAIN = "test_domain"
GRAPH_VERSION = "v1"
USER_ID = "participant_001"
CANDIDATE_RUN_ID = "candidate_map_001"
MAP_ID = "participant_map_001"
BANK_ID = "test_bilingual_v1"


class V1SimulatorExperimentTest(unittest.TestCase):
    def test_standalone_participant_frontend_origin_can_be_explicitly_allowed(self):
        client = TestClient(
            create_app(cors_origins=("https://study.example.org/",))
        )

        response = client.get(
            "/health",
            headers={"Origin": "https://study.example.org"},
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "https://study.example.org",
            response.headers["access-control-allow-origin"],
        )

    def test_participant_flow_confirms_map_samples_twenty_questions_and_persists_results(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_experiment_fixture(workspace_root)
            client = TestClient(
                create_app(
                    workspace_root=workspace_root,
                    simulator_service_factory=lambda _provider, root: SimulatorService(
                        workspace_root=root
                    ),
                )
            )

            banks_response = client.get(
                "/api/experiments/simulator-tests/question-banks"
            )
            self.assertEqual(200, banks_response.status_code)
            self.assertEqual(
                [BANK_ID],
                [
                    bank["bank_id"]
                    for bank in banks_response.json()["question_banks"]
                ],
            )

            map_response = client.post(
                f"/api/experiments/simulator-tests/participant-maps/"
                f"{DOMAIN}/{CANDIDATE_RUN_ID}/confirmation",
                json={
                    "map_id": MAP_ID,
                    "revisions": [
                        {
                            "node_id": "train_test_split",
                            "mastery_level": "L2",
                            "misconceptions": [],
                            "unknowns": [
                                "When a separate validation set is necessary."
                            ],
                            "review_note": "I understand the basic held-out idea.",
                        }
                    ],
                },
            )
            self.assertEqual(200, map_response.status_code, map_response.text)
            published_map = map_response.json()["map"]
            self.assertEqual("ground_truth", published_map["kind"])
            self.assertEqual(2, len(published_map["evidence"]))
            self.assertTrue(
                all(
                    evidence["visibility"] == "simulator_only"
                    for evidence in published_map["evidence"]
                )
            )

            session_response = client.post(
                "/api/experiments/simulator-tests/sessions",
                json={
                    "session_id": "simtest_001",
                    "participant_code": "P001",
                    "benchmark_domain": DOMAIN,
                    "map_id": MAP_ID,
                    "question_bank_id": BANK_ID,
                    "language": "en",
                    "simulator_client_provider": "openai",
                    "sampling_seed": 17,
                },
            )
            self.assertEqual(201, session_response.status_code, session_response.text)
            session = session_response.json()
            self.assertEqual(20, len(session["questions"]))
            self.assertEqual(
                20,
                len({question["question_id"] for question in session["questions"]}),
            )
            self.assertTrue(
                all(
                    question["selected_prompt"] == question["prompts"]["en"]
                    for question in session["questions"]
                )
            )

            evaluation = {
                "content_similarity": 4,
                "knowledge_level_similarity": 4,
                "boundary_similarity": 5,
                "style_similarity": 3,
                "overall_representativeness": 4,
                "replacement_judgement": "minor_bias",
                "comment": "Close enough for this pilot.",
            }
            for question in session["questions"]:
                answer_response = client.post(
                    f"/api/experiments/simulator-tests/sessions/simtest_001/"
                    f"questions/{question['question_id']}/answer",
                    json={"human_answer": "I would keep a held-out test set."},
                )
                self.assertEqual(200, answer_response.status_code, answer_response.text)
                answered_question = _question(
                    answer_response.json(),
                    question["question_id"],
                )
                self.assertEqual(
                    "I would keep a held-out test set.",
                    answered_question["human_answer"],
                )
                self.assertTrue(answered_question["simulator_answer"])
                self.assertEqual("answer", answered_question["observation_kind"])
                self.assertTrue(answered_question["debug_trace_id"])

                evaluation_response = client.put(
                    f"/api/experiments/simulator-tests/sessions/simtest_001/"
                    f"questions/{question['question_id']}/self-evaluation",
                    json=evaluation,
                )
                self.assertEqual(
                    200,
                    evaluation_response.status_code,
                    evaluation_response.text,
                )

            completion_response = client.post(
                "/api/experiments/simulator-tests/sessions/simtest_001/completion"
            )
            self.assertEqual(200, completion_response.status_code)
            self.assertEqual("completed", completion_response.json()["status"])
            self.assertIsNotNone(completion_response.json()["completed_at"])

            saved_session = _load_json(
                workspace_root
                / "experiments"
                / "02_simulator_human_validity"
                / "results"
                / "private"
                / "sessions"
                / "simtest_001"
                / "session.json"
            )
            self.assertEqual("completed", saved_session["status"])
            self.assertTrue(
                (
                    workspace_root
                    / "experiments"
                    / "02_simulator_human_validity"
                    / "results"
                    / "private"
                    / "map_reviews"
                    / f"{MAP_ID}.json"
                ).exists()
            )

    def test_session_cannot_complete_before_all_self_evaluations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_experiment_fixture(workspace_root)
            client = TestClient(
                create_app(
                    workspace_root=workspace_root,
                    simulator_service_factory=lambda _provider, root: SimulatorService(
                        workspace_root=root
                    ),
                )
            )
            _confirm_map(client)
            create_response = client.post(
                "/api/experiments/simulator-tests/sessions",
                json={
                    "session_id": "simtest_incomplete",
                    "participant_code": "P002",
                    "benchmark_domain": DOMAIN,
                    "map_id": MAP_ID,
                    "question_bank_id": BANK_ID,
                    "language": "zh-CN",
                    "sampling_seed": 9,
                },
            )
            self.assertEqual(201, create_response.status_code)
            session = create_response.json()
            self.assertTrue(
                all(
                    question["selected_prompt"] == question["prompts"]["zh_cn"]
                    for question in session["questions"]
                )
            )

            completion_response = client.post(
                "/api/experiments/simulator-tests/sessions/"
                "simtest_incomplete/completion"
            )
            self.assertEqual(409, completion_response.status_code)
            self.assertIn("All 20 question pairs", completion_response.json()["detail"])


def _confirm_map(client: TestClient) -> None:
    response = client.post(
        f"/api/experiments/simulator-tests/participant-maps/"
        f"{DOMAIN}/{CANDIDATE_RUN_ID}/confirmation",
        json={
            "map_id": MAP_ID,
            "revisions": [
                {
                    "node_id": "train_test_split",
                    "mastery_level": "L4",
                    "misconceptions": [],
                    "unknowns": [],
                    "review_note": None,
                }
            ],
        },
    )
    if response.status_code != 200:
        raise AssertionError(response.text)


def _write_experiment_fixture(workspace_root: Path) -> None:
    graph_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / DOMAIN
        / "graphs"
        / GRAPH_VERSION
    )
    graph_dir.mkdir(parents=True)
    _write_json(
        graph_dir / "graph_manifest.json",
        {
            "graph_id": "kg_test_domain_v1",
            "domain": DOMAIN,
            "version": GRAPH_VERSION,
            "promoted_from_candidate_run": "graph_candidate_001",
            "nodes_file": "authored_nodes.json",
            "edges_file": "authored_edges.json",
            "source": [],
        },
    )
    _write_json(
        graph_dir / "authored_nodes.json",
        [
            {
                "id": "train_test_split",
                "name": "Train/Test Split",
                "type": "concept",
                "definition": "Separating data for model fitting and held-out evaluation.",
                "source_locators": [
                    {"source_id": "fixture", "locator": "test"}
                ],
                "diagnostic_goal": "Explain the purpose of held-out evaluation.",
                "levels": {
                    "L0": "Cannot identify a held-out split.",
                    "L1": "Recognizes training and test data as different sets.",
                    "L2": "Explains that test data estimates performance on unseen cases.",
                    "L3": "Distinguishes training, validation, and final testing.",
                    "L4": "Diagnoses leakage and selection bias in evaluation.",
                    "L5": "Designs evaluation under distribution shift and repeated selection.",
                },
                "diagnostic_signals": ["train/test split", "held-out test set"],
                "simulator_behavior": "Answer consistently about held-out evaluation.",
            }
        ],
    )
    _write_json(graph_dir / "authored_edges.json", [])

    profile_dir = (
        workspace_root / "benchmark" / "domains" / DOMAIN / "users" / USER_ID
    )
    profile_dir.mkdir(parents=True)
    _write_json(
        profile_dir / "profile_context.json",
        {
            "benchmark_domain": DOMAIN,
            "user_id": USER_ID,
            "summary": "A participant in a Simulator validation pilot.",
            "background": ["Has studied introductory machine learning."],
            "prior_experience": ["Used a train/test split in a tutorial."],
            "goals": ["Understand model evaluation."],
            "preferences": ["Prefers concise explanations."],
        },
    )

    candidate_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / DOMAIN
        / "candidate_maps"
        / CANDIDATE_RUN_ID
    )
    candidate_dir.mkdir(parents=True)
    _write_json(
        candidate_dir / "candidate_map.json",
        {
            "user_id": USER_ID,
            "kind": "candidate",
            "states": [
                {
                    "node_id": "train_test_split",
                    "mastery_level": "L3",
                    "evidence_refs": ["candidate_ev_01", "candidate_ev_02"],
                    "misconceptions": [],
                    "unknowns": [],
                }
            ],
            "evidence": [
                {
                    "id": "candidate_ev_01",
                    "node_id": "train_test_split",
                    "evidence_type": "ground_truth_profile",
                    "evidence_kind": "self_report",
                    "visibility": "simulator_only",
                    "signal": "Candidate evidence one.",
                    "turn_id": None,
                },
                {
                    "id": "candidate_ev_02",
                    "node_id": "train_test_split",
                    "evidence_type": "ground_truth_profile",
                    "evidence_kind": "self_report",
                    "visibility": "simulator_only",
                    "signal": "Candidate evidence two.",
                    "turn_id": None,
                },
            ],
        },
    )
    _, artifact_paths = read_candidate_map_run(
        workspace_root=workspace_root,
        benchmark_domain=DOMAIN,
        run_id=CANDIDATE_RUN_ID,
    )
    run_log = CandidateMapAuthoringRunLog(
        run_id=CANDIDATE_RUN_ID,
        workflow_name="fixture",
        status="succeeded",
        benchmark_domain=DOMAIN,
        graph_version=GRAPH_VERSION,
        user_id=USER_ID,
        evidence_batch_size=5,
        sampling_temperature=0.7,
        artifact_paths=artifact_paths,
    )
    _write_json(
        candidate_dir / "workflow_log.json",
        run_log.model_dump(mode="json"),
    )

    bank_dir = workspace_root / "benchmark" / "question_banks"
    bank_dir.mkdir(parents=True)
    bank_path = bank_dir / "test_bilingual_v1.json"
    _write_json(
        bank_path,
        {
            "schema_version": "knowact.simulator_question_bank.v2",
            "bank_id": BANK_ID,
            "version": "2.0",
            "benchmark_domain": DOMAIN,
            "title": {
                "en": "Test bilingual question bank",
                "zh_cn": "测试双语题库",
            },
            "questions": [
                {
                    "question_id": f"TEST_Q{index:03d}",
                    "target_concept": "train_test_split",
                    "question_type": "explanation",
                    "cognitive_operation": "explain",
                    "prompts": {
                        "en": (
                            f"Question {index}: How does a Train/Test Split support "
                            "held-out evaluation?"
                        ),
                        "zh_cn": (
                            f"问题 {index}：Train/Test Split 如何支持留出评估？"
                        ),
                    },
                    "source_reference_ids": ["fixture-source"],
                    "reviewed_target_node_ids": ["train_test_split"],
                }
                for index in range(1, 22)
            ],
        },
    )
    _write_json(
        bank_dir / "reviews" / f"{BANK_ID}.quality_review.json",
        {
            "schema_version": "knowact.question_bank_quality_review.v1",
            "bank_id": BANK_ID,
            "bank_version": "2.0",
            "benchmark_domain": DOMAIN,
            "bank_content_sha256": sha256(bank_path.read_bytes()).hexdigest(),
            "review_method_version": "atomic_roleplay_screening_v1",
            "screened_at": "2026-08-01",
            "expert_review_status": "pending",
            "sources": [
                {
                    "source_id": "fixture-source",
                    "title": "Test fixture source",
                    "url": "https://example.org/test-fixture",
                    "authority": "Synthetic test-only source.",
                    "relevance": "Supports the train/test split fixture.",
                    "evidence_used": "Provides a stable schema test reference.",
                    "transfer_limits": "Not benchmark evidence and not for release.",
                    "decision": "accepted",
                }
            ],
            "question_reviews": [
                {
                    "question_id": f"TEST_Q{index:03d}",
                    "role": "introductory machine-learning student",
                    "trial_answer": (
                        "A held-out test set estimates performance on unseen data."
                    ),
                    "assessed_mastery_level": "L3",
                    "cognitive_signal": (
                        "The answer explains the held-out evaluation purpose."
                    ),
                    "answer_word_count": 9,
                    "atomicity_pass": True,
                    "brevity_pass": True,
                    "cognitive_signal_pass": True,
                    "bilingual_equivalence_pass": True,
                    "decision": "accepted",
                }
                for index in range(1, 22)
            ],
        },
    )


def _question(session: dict, question_id: str) -> dict:
    return next(
        question
        for question in session["questions"]
        if question["question_id"] == question_id
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
