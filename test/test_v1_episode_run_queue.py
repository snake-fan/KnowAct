import json
import tempfile
import unittest
from pathlib import Path

from backend.knowact.agents.working_map import initialize_working_map
from backend.knowact.core.episode import EvaluationEpisodeManifest
from backend.knowact.runtime.checkpoint import (
    EpisodeRunCheckpointInvalidError,
    EpisodeRunCheckpointRepository,
)
from backend.knowact.runtime.episode_options import (
    EpisodeExecutionConfigurationError,
    build_episode_model_catalog,
    validate_execution_configuration,
)
from backend.knowact.runtime.execution_repository import (
    EpisodeExecutionRepository,
    EpisodeExecutionRepositoryError,
    EpisodeExecutionStatus,
)
from backend.knowact.storage.reviewed_graphs import load_reviewed_graph
from test.test_v1_runtime_episode_repository import (
    _execution_configuration_payload,
    _write_reviewed_graph,
)


class V1EpisodeRunQueueTest(unittest.TestCase):
    def test_queued_cancellation_is_immediate_and_reenqueue_joins_tail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = EpisodeExecutionRepository(
                workspace_root=Path(temp_dir)
            )
            repository.initialize((_manifest("episode_a"), _manifest("episode_b")))
            repository.enqueue(episode_id="episode_a", run_id="run_a")
            cancelled = repository.cancel("episode_a")
            repository.enqueue(episode_id="episode_b", run_id="run_b")
            resumed = repository.enqueue(episode_id="episode_a", run_id="run_a")

        self.assertEqual(EpisodeExecutionStatus.CANCELLED, cancelled.status)
        self.assertEqual(EpisodeExecutionStatus.QUEUED, resumed.status)
        self.assertGreater(resumed.queue_order, 1)

    def test_execution_state_excludes_legacy_and_persists_fifo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repository = EpisodeExecutionRepository(workspace_root=workspace_root)
            repository.initialize(
                (
                    _manifest("episode_legacy", configured=False),
                    _manifest("episode_a"),
                    _manifest("episode_b"),
                )
            )

            repository.enqueue(episode_id="episode_a", run_id="run_a")
            repository.enqueue(episode_id="episode_b", run_id="run_b")
            first = repository.next_queued()
            repository.mark_running("episode_a")
            repository.update_progress("episode_a", 1)

            reloaded = EpisodeExecutionRepository(workspace_root=workspace_root)
            reloaded.reconcile_startup()
            state = reloaded.snapshot()
            next_after_restart = reloaded.next_queued()

        self.assertNotIn("episode_legacy", state.episodes)
        self.assertEqual("episode_a", first.episode_id)
        self.assertEqual(EpisodeExecutionStatus.FAILED, state.episodes["episode_a"].status)
        self.assertEqual("backend_restarted", state.episodes["episode_a"].failure.code)
        self.assertEqual(1, state.episodes["episode_a"].completed_turns)
        self.assertEqual(EpisodeExecutionStatus.QUEUED, state.episodes["episode_b"].status)
        self.assertEqual("episode_b", next_after_restart.episode_id)

    def test_concurrency_is_persisted_and_constrained_to_three_through_eight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repository = EpisodeExecutionRepository(workspace_root=workspace_root)
            repository.initialize((_manifest("episode_a"),))

            repository.set_concurrency(8)
            persisted = EpisodeExecutionRepository(
                workspace_root=workspace_root
            ).snapshot()

            for invalid in (2, 9):
                with self.subTest(invalid=invalid):
                    with self.assertRaises(EpisodeExecutionRepositoryError):
                        repository.set_concurrency(invalid)

        self.assertEqual(8, persisted.concurrency)

    def test_checkpoint_validates_episode_identity_and_immutable_configuration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_reviewed_graph(workspace_root)
            graph = load_reviewed_graph(
                workspace_root=workspace_root,
                benchmark_domain="classical_supervised_ml_algorithms",
                version="v1",
            ).graph
            manifest = _manifest("episode_a")
            configuration = manifest.execution_configuration()
            working_map = initialize_working_map(
                episode_id=manifest.episode_id,
                benchmark_domain=manifest.benchmark_domain,
                graph_version=manifest.graph_version,
                graph=graph,
            )
            run_dir = workspace_root / "experiments" / "runs" / "run_a"
            run_dir.mkdir(parents=True)
            repository = EpisodeRunCheckpointRepository(workspace_root=workspace_root)
            checkpoint = repository.initial_checkpoint(
                run_id="run_a",
                episode_id="episode_a",
                execution_configuration=configuration,
                working_map=working_map,
                max_turns=3,
            )
            repository.write(checkpoint)

            loaded = repository.read_validated(
                run_id="run_a",
                episode_id="episode_a",
                execution_configuration=configuration,
            )
            changed = configuration.model_copy(
                update={"tested_agent_model": "different-model"}
            )
            with self.assertRaises(EpisodeRunCheckpointInvalidError):
                repository.read_validated(
                    run_id="run_a",
                    episode_id="episode_a",
                    execution_configuration=changed,
                )

        self.assertEqual(0, loaded.completed_turns)
        self.assertEqual(3, loaded.remaining_turns)

    def test_model_catalog_hides_secrets_and_rejects_unavailable_provider(self):
        catalog = build_episode_model_catalog(
            {
                "OPENAI_API_KEY": "secret-value",
                "KNOWACT_OPENAI_MODEL": "model-a",
                "KNOWACT_OPENAI_MODELS": "model-b,model-a",
            }
        )
        serialized = json.dumps(catalog.model_dump(mode="json"), sort_keys=True)
        openai = catalog.provider("openai")
        deepseek = catalog.provider("deepseek")

        self.assertTrue(openai.available)
        self.assertEqual(("model-a", "model-b"), openai.models)
        self.assertFalse(deepseek.available)
        self.assertNotIn("secret-value", serialized)
        configuration = _manifest("episode_a").execution_configuration().model_copy(
            update={
                "simulator_client_provider": "deepseek",
                "simulator_model": "deepseek-v4-flash",
            }
        )
        with self.assertRaises(EpisodeExecutionConfigurationError):
            validate_execution_configuration(configuration, catalog)


def _manifest(
    episode_id: str,
    *,
    configured: bool = True,
) -> EvaluationEpisodeManifest:
    payload = {
        "episode_id": episode_id,
        "benchmark_domain": "classical_supervised_ml_algorithms",
        "graph_version": "v1",
        "hidden_map_id": "gt_map_001",
        "max_turns": 3,
        "interaction_rule": "single_diagnostic_question_per_turn",
        "scoring_profile": "squared_mastery_distance_v1",
    }
    if configured:
        payload.update(_execution_configuration_payload())
    return EvaluationEpisodeManifest.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
