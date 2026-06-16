import json
import tempfile
import unittest
from pathlib import Path

from backend.knowact.runtime.episode_repository import (
    EPISODE_MANIFEST_FILENAME,
    RuntimeEpisodeArtifactError,
    RuntimeEpisodeIdError,
    RuntimeEpisodeNotFoundError,
    RuntimeEpisodeRepository,
)


class V1RuntimeEpisodeRepositoryTest(unittest.TestCase):
    def test_list_episodes_reads_only_runtime_registry_manifests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_b")
            _write_manifest(workspace_root, "episode_a")
            _write_manifest(
                workspace_root,
                "domain_episode",
                root_parts=("benchmark", "domains", "demo", "episodes"),
            )
            _episode_dir(workspace_root, "no_manifest").mkdir(parents=True)

            records = RuntimeEpisodeRepository(
                workspace_root=workspace_root
            ).list_episodes()

        self.assertEqual(["episode_a", "episode_b"], [record.episode_id for record in records])
        self.assertEqual(["episode_a", "episode_b"], [record.manifest.episode_id for record in records])

    def test_read_episode_manifest_by_episode_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_a", max_turns=5)

            manifest = RuntimeEpisodeRepository(
                workspace_root=workspace_root
            ).read_episode_manifest("episode_a")

        self.assertEqual("episode_a", manifest.episode_id)
        self.assertEqual("classical_supervised_ml_algorithms", manifest.benchmark_domain)
        self.assertEqual("dev_fixture_v1", manifest.graph_version)
        self.assertEqual("dev_user_001_map", manifest.hidden_map_id)
        self.assertEqual(5, manifest.max_turns)

    def test_read_episode_rejects_not_found_and_missing_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repository = RuntimeEpisodeRepository(workspace_root=workspace_root)

            with self.assertRaises(RuntimeEpisodeNotFoundError):
                repository.read_episode_manifest("missing_episode")

            _episode_dir(workspace_root, "episode_without_manifest").mkdir(parents=True)
            with self.assertRaises(RuntimeEpisodeNotFoundError):
                repository.read_episode_manifest("episode_without_manifest")

    def test_read_episode_rejects_malformed_manifest_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            manifest_path = _episode_dir(workspace_root, "episode_bad_json") / EPISODE_MANIFEST_FILENAME
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text("{not valid json", encoding="utf-8")

            with self.assertRaises(RuntimeEpisodeArtifactError):
                RuntimeEpisodeRepository(
                    workspace_root=workspace_root
                ).read_episode_manifest("episode_bad_json")

    def test_read_episode_rejects_schema_validation_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_bad_schema", max_turns=0)

            with self.assertRaises(RuntimeEpisodeArtifactError):
                RuntimeEpisodeRepository(
                    workspace_root=workspace_root
                ).read_episode_manifest("episode_bad_schema")

    def test_read_episode_rejects_manifest_validation_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(
                workspace_root,
                "episode_with_override",
                scoring_overrides={"missing_prediction_penalty": 9},
            )

            with self.assertRaises(RuntimeEpisodeArtifactError):
                RuntimeEpisodeRepository(
                    workspace_root=workspace_root
                ).read_episode_manifest("episode_with_override")

    def test_read_episode_rejects_unsafe_episode_id(self):
        repository = RuntimeEpisodeRepository(workspace_root=Path("/tmp/unused"))

        for episode_id in ["../episode", "episode/subpath", "bad id", "", ".hidden"]:
            with self.subTest(episode_id=episode_id):
                with self.assertRaises(RuntimeEpisodeIdError):
                    repository.read_episode_manifest(episode_id)

    def test_list_episode_rejects_manifest_id_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "registry_id", payload_episode_id="payload_id")

            with self.assertRaises(RuntimeEpisodeArtifactError):
                RuntimeEpisodeRepository(workspace_root=workspace_root).list_episodes()


def _episode_dir(
    workspace_root: Path,
    episode_id: str,
    *,
    root_parts: tuple[str, ...] = ("benchmark", "runtime", "episodes"),
) -> Path:
    return workspace_root.joinpath(*root_parts, episode_id)


def _write_manifest(
    workspace_root: Path,
    episode_id: str,
    *,
    root_parts: tuple[str, ...] = ("benchmark", "runtime", "episodes"),
    payload_episode_id: str | None = None,
    max_turns: int = 3,
    scoring_overrides: dict[str, int] | None = None,
) -> Path:
    manifest_path = _episode_dir(
        workspace_root,
        episode_id,
        root_parts=root_parts,
    ) / EPISODE_MANIFEST_FILENAME
    manifest_path.parent.mkdir(parents=True)
    payload = {
        "episode_id": payload_episode_id or episode_id,
        "benchmark_domain": "classical_supervised_ml_algorithms",
        "graph_version": "dev_fixture_v1",
        "hidden_map_id": "dev_user_001_map",
        "max_turns": max_turns,
        "interaction_rule": "single_diagnostic_question_per_turn",
        "scoring_profile": "squared_mastery_distance_v1",
    }
    if scoring_overrides is not None:
        payload["scoring_overrides"] = scoring_overrides
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path
