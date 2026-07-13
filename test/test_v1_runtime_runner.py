import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.knowact.agents.agents.simple_llm import SimpleLLMTestedAgent
from backend.knowact.llm.client import ModelClientMetadata
from backend.knowact.llm.messages import OPENAI_MESSAGE_PROFILE, ModelMessage
from backend.knowact.runtime.runner import (
    EpisodeRunAlreadyExistsError,
    EpisodeRunRequest,
    EpisodeRunner,
)
from backend.knowact.scoring.compare import (
    score_final_reconstruction as real_score_final_reconstruction,
)
from backend.knowact.simulator.service import SimulatorService
from test.test_v1_runtime_episode_repository import (
    _write_confirmed_profile_context,
    _write_manifest,
    _write_reviewed_graph,
    _write_reviewed_map,
)


class V1RuntimeRunnerTest(unittest.TestCase):
    def test_runner_completes_simple_llm_episode_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_runnable_episode(workspace_root, max_turns=1)
            runner, model_client = _runner_with_fake_simple_llm(
                workspace_root,
                responses=(
                    _ask_train_test_split_question_output(),
                    _train_test_split_l4_update_output(),
                ),
            )

            result = runner.run_episode(
                EpisodeRunRequest(
                    episode_id="episode_a",
                    run_id="run_001",
                    agent_kind="simple_llm_agent",
                    tested_agent_client_provider="deepseek",
                    simulator_client_provider="openai",
                    tested_agent_temperature=0.1,
                )
            )

            transcript = _read_json(result.artifacts.transcript_path)
            turn_log = _read_json(result.artifacts.turns_dir / "turn_001.json")
            working_map = _read_json(result.artifacts.working_map_path)
            trace = _read_json(result.artifacts.agent_tool_trace_path)
            agent_output = _read_json(result.artifacts.agent_output_path)
            scoring_report = _read_json(result.artifacts.scoring_report_path)

        self.assertEqual("run_001", result.run_id)
        self.assertEqual("episode_a", result.episode_id)
        self.assertEqual("simple_llm_agent", result.agent_kind)
        self.assertEqual(1, result.turn_count)
        self.assertTrue(result.forced_finalization)
        self.assertFalse(result.forced_finalization_fallback)
        self.assertEqual(2, len(model_client.messages))
        self.assertEqual([0.1, 0.1], model_client.temperatures)

        self.assertEqual(1, len(transcript["turns"]))
        self.assertEqual(transcript["turns"][0], turn_log["dialogue"])
        self.assertEqual("turn_001", turn_log["turn_id"])
        self.assertEqual(
            "accepted",
            turn_log["working_map_update_events"][-1]["status"],
        )
        self.assertEqual(
            "train_test_split",
            turn_log["working_map_update_events"][-1]["updates"][0]["node_id"],
        )
        self.assertEqual("turn_001", transcript["turns"][0]["turn_id"])
        self.assertEqual("answer", transcript["turns"][0]["observation"]["kind"])
        transcript_text = json.dumps(transcript, sort_keys=True)
        for hidden_fragment in (
            "debug_trace_id",
            "grounded_node_ids",
            "answer_blueprint",
            "mastery_level",
            "evidence_refs",
            "simulator_only",
            "gt_map_001",
            "synthetic_user_001",
        ):
            with self.subTest(hidden_fragment=hidden_fragment):
                self.assertNotIn(hidden_fragment, transcript_text)

        states_by_node = {state["node_id"]: state for state in working_map["states"]}
        self.assertEqual("L4", states_by_node["train_test_split"]["assessed_mastery_level"])
        self.assertEqual(
            ("turn_001",),
            tuple(states_by_node["train_test_split"]["supporting_turn_ids"]),
        )
        self.assertEqual(
            "unknown",
            states_by_node["cross_validation"]["assessed_mastery_level"],
        )

        self.assertEqual("deepseek", agent_output["tested_agent_client_provider"])
        self.assertEqual("openai", agent_output["simulator_client_provider"])
        self.assertTrue(agent_output["forced_finalization"])
        self.assertFalse(agent_output["forced_finalization_fallback"])
        predictions = {
            prediction["node_id"]: prediction
            for prediction in agent_output["final_reconstruction_submission"][
                "predictions"
            ]
        }
        self.assertEqual("L4", predictions["train_test_split"]["predicted_mastery"])
        self.assertEqual("unknown", predictions["cross_validation"]["predicted_mastery"])
        self.assertEqual(
            "squared_mastery_distance_v1",
            scoring_report["scoring_profile"],
        )
        self.assertAlmostEqual(18.0, scoring_report["episode_mastery_distance"])
        self.assertAlmostEqual(0.5, scoring_report["missing_prediction_rate"])
        self.assertAlmostEqual(0.5, scoring_report["exact_match_rate"])

        self.assertEqual("run_001", trace["run_id"])
        self.assertEqual("episode_a", trace["episode_id"])
        self.assertIn(
            "working_map_update",
            {event["event"] for event in trace["events"]},
        )

    def test_runner_persists_completed_turn_and_working_map_before_scoring(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_runnable_episode(workspace_root, max_turns=1)
            runner, _ = _runner_with_fake_simple_llm(
                workspace_root,
                responses=(
                    _ask_train_test_split_question_output(),
                    _train_test_split_l4_update_output(),
                ),
            )
            observed_artifacts: list[tuple[dict, dict]] = []

            def inspect_artifacts_before_scoring(**kwargs):
                run_dir = workspace_root / "experiments" / "runs" / "run_incremental"
                observed_artifacts.append(
                    (
                        _read_json(run_dir / "turns" / "turn_001.json"),
                        _read_json(run_dir / "working_map.json"),
                    )
                )
                return real_score_final_reconstruction(**kwargs)

            with patch(
                "backend.knowact.runtime.runner.score_final_reconstruction",
                side_effect=inspect_artifacts_before_scoring,
            ):
                runner.run_episode(
                    EpisodeRunRequest(
                        episode_id="episode_a",
                        run_id="run_incremental",
                    )
                )

        self.assertEqual(1, len(observed_artifacts))
        turn_log, working_map = observed_artifacts[0]
        self.assertEqual("turn_001", turn_log["turn_id"])
        self.assertEqual("accepted", turn_log["working_map_update_events"][-1]["status"])
        states_by_node = {state["node_id"]: state for state in working_map["states"]}
        self.assertEqual(
            "L4",
            states_by_node["train_test_split"]["assessed_mastery_level"],
        )

    def test_runner_rejects_reusing_run_id_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_runnable_episode(workspace_root, max_turns=1)
            existing_run_dir = workspace_root / "experiments" / "runs" / "run_001"
            existing_run_dir.mkdir(parents=True)
            runner, _ = _runner_with_fake_simple_llm(
                workspace_root,
                responses=(_ask_train_test_split_question_output(),),
            )

            with self.assertRaises(EpisodeRunAlreadyExistsError):
                runner.run_episode(
                    EpisodeRunRequest(
                        episode_id="episode_a",
                        run_id="run_001",
                    )
                )

    def test_runner_marks_update_retry_exhausted_and_scores_current_working_map(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_runnable_episode(workspace_root, max_turns=1)
            runner, _ = _runner_with_fake_simple_llm(
                workspace_root,
                responses=(
                    _ask_train_test_split_question_output(),
                    _unknown_node_update_output(),
                    _unknown_node_update_output(),
                    _unknown_node_update_output(),
                ),
            )

            result = runner.run_episode(
                EpisodeRunRequest(
                    episode_id="episode_a",
                    run_id="run_retry_exhausted",
                    max_tool_retries=3,
                )
            )

            trace = _read_json(result.artifacts.agent_tool_trace_path)
            working_map = _read_json(result.artifacts.working_map_path)
            scoring_report = _read_json(result.artifacts.scoring_report_path)

        rejected_update_events = [
            event
            for event in trace["events"]
            if event["event"] == "working_map_update"
            and event["status"] == "rejected"
        ]
        self.assertEqual(3, len(rejected_update_events))
        self.assertTrue(
            any(
                event["status"] == "tool_retry_exhausted"
                and event["tool_retry_exhausted"]
                for event in trace["events"]
            )
        )
        self.assertTrue(result.forced_finalization)
        self.assertEqual(
            {"unknown"},
            {
                state["assessed_mastery_level"]
                for state in working_map["states"]
            },
        )
        self.assertAlmostEqual(36.0, scoring_report["episode_mastery_distance"])
        self.assertAlmostEqual(1.0, scoring_report["missing_prediction_rate"])


class _FakeModelClient:
    message_profile = OPENAI_MESSAGE_PROFILE
    metadata = ModelClientMetadata(
        provider="fake",
        model_name="fake-simple-llm-agent",
        message_profile=OPENAI_MESSAGE_PROFILE.name,
    )

    def __init__(self, *, responses: tuple[str, ...]) -> None:
        self._responses = list(responses)
        self.messages: list[tuple[ModelMessage, ...]] = []
        self.temperatures: list[float | None] = []

    def complete(
        self,
        *,
        messages,
        temperature: float | None = None,
    ) -> str:
        self.messages.append(tuple(messages))
        self.temperatures.append(temperature)
        if not self._responses:
            raise AssertionError("No fake model response configured")
        return self._responses.pop(0)


def _runner_with_fake_simple_llm(
    workspace_root: Path,
    *,
    responses: tuple[str, ...],
) -> tuple[EpisodeRunner, _FakeModelClient]:
    model_client = _FakeModelClient(responses=responses)
    runner = EpisodeRunner(
        workspace_root=workspace_root,
        tested_agent_factory=lambda request: SimpleLLMTestedAgent(
            model_client=model_client,
            temperature=request.tested_agent_temperature,
        ),
        simulator_service_factory=lambda provider, root: SimulatorService(
            workspace_root=root
        ),
    )
    return runner, model_client


def _write_runnable_episode(workspace_root: Path, *, max_turns: int) -> None:
    _write_manifest(
        workspace_root,
        "episode_a",
        graph_version="v1",
        hidden_map_id="gt_map_001",
        max_turns=max_turns,
    )
    _write_reviewed_graph(workspace_root)
    _write_reviewed_map(workspace_root)
    _write_confirmed_profile_context(workspace_root)


def _ask_train_test_split_question_output() -> str:
    return json.dumps(
        {
            "action": "ask_diagnostic_question",
            "question": {
                "text": "How would you decide whether a Train/Test Split is appropriate?",
                "question_id": "q_train_test_split",
            },
        }
    )


def _train_test_split_l4_update_output() -> str:
    return json.dumps(
        {
            "updates": [
                {
                    "node_id": "train_test_split",
                    "assessed_mastery_level": "L4",
                    "diagnostic_confidence": "high",
                    "assessment_note": "The user gave a held-out evaluation answer.",
                    "supporting_turn_ids": ["turn_001"],
                }
            ]
        }
    )


def _unknown_node_update_output() -> str:
    return json.dumps(
        {
            "updates": [
                {
                    "node_id": "not_in_graph",
                    "assessed_mastery_level": "L4",
                    "diagnostic_confidence": "high",
                    "assessment_note": "This update should be rejected.",
                    "supporting_turn_ids": ["turn_001"],
                }
            ]
        }
    )


def _read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    unittest.main()
