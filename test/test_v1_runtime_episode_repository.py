import json
import tempfile
import unittest
from pathlib import Path

from backend.knowact.runtime.episode_repository import (
    EPISODE_MANIFEST_FILENAME,
    RuntimeEpisodeArtifactError,
    RuntimeEpisodeBindingError,
    RuntimeEpisodeBindingWarningCode,
    RuntimeEpisodeIdError,
    RuntimeEpisodeNotFoundError,
    RuntimeProfileContextStatus,
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

    def test_load_episode_binding_reads_reviewed_artifacts_and_profile_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_a", graph_version="v1", hidden_map_id="gt_map_001")
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root)
            _write_confirmed_profile_context(workspace_root)

            binding = RuntimeEpisodeRepository(
                workspace_root=workspace_root
            ).load_episode_binding("episode_a")

        self.assertEqual("episode_a", binding.episode_id)
        self.assertEqual("v1", binding.reviewed_graph.manifest.version)
        self.assertEqual(2, len(binding.reviewed_graph.graph.nodes))
        self.assertEqual("gt_map_001", binding.hidden_map.manifest.map_id)
        self.assertEqual("synthetic_user_001", binding.hidden_map.manifest.user_id)
        self.assertEqual("synthetic_user_001", binding.profile_context.user_id)
        self.assertEqual(RuntimeProfileContextStatus.LOADED, binding.profile_context.status)
        self.assertEqual("synthetic_user_001", getattr(binding.profile_context.profile_context, "user_id"))
        self.assertEqual((), binding.warnings)

    def test_load_episode_binding_rejects_map_domain_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_a", graph_version="v1", hidden_map_id="gt_map_001")
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root, manifest_benchmark_domain="other_domain")

            with self.assertRaises(RuntimeEpisodeBindingError):
                RuntimeEpisodeRepository(
                    workspace_root=workspace_root
                ).load_episode_binding("episode_a")

    def test_load_episode_binding_rejects_map_graph_version_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_a", graph_version="v1", hidden_map_id="gt_map_001")
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root, graph_version="v2")

            with self.assertRaises(RuntimeEpisodeBindingError):
                RuntimeEpisodeRepository(
                    workspace_root=workspace_root
                ).load_episode_binding("episode_a")

    def test_load_episode_binding_rejects_missing_reviewed_graph_even_if_candidate_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_a", graph_version="v1", hidden_map_id="gt_map_001")
            _write_candidate_graph_placeholder(workspace_root)

            with self.assertRaises(RuntimeEpisodeBindingError):
                RuntimeEpisodeRepository(
                    workspace_root=workspace_root
                ).load_episode_binding("episode_a")

    def test_load_episode_binding_rejects_missing_reviewed_map_even_if_candidate_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_a", graph_version="v1", hidden_map_id="gt_map_001")
            _write_reviewed_graph(workspace_root)
            _write_candidate_map_placeholder(workspace_root)

            with self.assertRaises(RuntimeEpisodeBindingError):
                RuntimeEpisodeRepository(
                    workspace_root=workspace_root
                ).load_episode_binding("episode_a")

    def test_load_episode_binding_rejects_candidate_map_in_reviewed_map_slot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_a", graph_version="v1", hidden_map_id="gt_map_001")
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root, map_kind="candidate")

            with self.assertRaises(RuntimeEpisodeBindingError):
                RuntimeEpisodeRepository(
                    workspace_root=workspace_root
                ).load_episode_binding("episode_a")

    def test_load_episode_binding_returns_optional_missing_profile_context_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            _write_manifest(workspace_root, "episode_a", graph_version="v1", hidden_map_id="gt_map_001")
            _write_reviewed_graph(workspace_root)
            _write_reviewed_map(workspace_root)

            binding = RuntimeEpisodeRepository(
                workspace_root=workspace_root
            ).load_episode_binding("episode_a")

        self.assertEqual("synthetic_user_001", binding.profile_context.user_id)
        self.assertEqual(
            RuntimeProfileContextStatus.MISSING_OPTIONAL,
            binding.profile_context.status,
        )
        self.assertIsNone(binding.profile_context.profile_context)
        self.assertEqual(1, len(binding.warnings))
        self.assertEqual(
            RuntimeEpisodeBindingWarningCode.MISSING_PROFILE_CONTEXT,
            binding.warnings[0].code,
        )


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
    benchmark_domain: str = "classical_supervised_ml_algorithms",
    graph_version: str = "dev_fixture_v1",
    hidden_map_id: str = "dev_user_001_map",
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
        "benchmark_domain": benchmark_domain,
        "graph_version": graph_version,
        "hidden_map_id": hidden_map_id,
        "max_turns": max_turns,
        "interaction_rule": "single_diagnostic_question_per_turn",
        "scoring_profile": "squared_mastery_distance_v1",
    }
    if scoring_overrides is not None:
        payload["scoring_overrides"] = scoring_overrides
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _write_reviewed_graph(workspace_root: Path) -> None:
    graph_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "graphs"
        / "v1"
    )
    graph_dir.mkdir(parents=True)
    _write_json(
        graph_dir / "graph_manifest.json",
        {
            "graph_id": "kg_classical_supervised_ml_algorithms_v1",
            "domain": "classical_supervised_ml_algorithms",
            "version": "v1",
            "promoted_from_candidate_run": "graph_run_001",
            "nodes_file": "authored_nodes.json",
            "edges_file": "authored_edges.json",
        },
    )
    _write_json(
        graph_dir / "authored_nodes.json",
        [
            _knowledge_node("train_test_split", "Train/Test Split"),
            _knowledge_node("cross_validation", "Cross-Validation"),
        ],
    )
    _write_json(
        graph_dir / "authored_edges.json",
        [
            {
                "id": "edge_train_test_split_prerequisite_for_cross_validation",
                "source": "train_test_split",
                "target": "cross_validation",
                "type": "prerequisite_for",
                "rationale": "A held-out split motivates repeated validation splits.",
                "weight": 0.7,
                "curation_confidence": 0.8,
            }
        ],
    )


def _write_reviewed_map(
    workspace_root: Path,
    *,
    manifest_benchmark_domain: str = "classical_supervised_ml_algorithms",
    graph_version: str = "v1",
    map_kind: str = "ground_truth",
) -> None:
    map_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "maps"
        / "gt_map_001"
    )
    map_dir.mkdir(parents=True)
    _write_json(
        map_dir / "map_manifest.json",
        {
            "map_id": "gt_map_001",
            "user_id": "synthetic_user_001",
            "benchmark_domain": manifest_benchmark_domain,
            "graph_version": graph_version,
            "promoted_from_candidate_run": "map_run_001",
        },
    )
    _write_json(
        map_dir / "map.json",
        {
            "user_id": "synthetic_user_001",
            "kind": map_kind,
            "states": [
                {
                    "node_id": "train_test_split",
                    "mastery_level": "L4",
                    "evidence_refs": ["ev_gt_map_001_train_test_split_001"],
                    "misconceptions": [],
                    "unknowns": [],
                },
                {
                    "node_id": "cross_validation",
                    "mastery_level": "L1",
                    "evidence_refs": ["ev_gt_map_001_cross_validation_001"],
                    "misconceptions": ["Treats each fold as a separate final test set."],
                    "unknowns": ["How folds rotate validation data."],
                },
            ],
            "evidence": [
                _ground_truth_evidence(
                    "ev_gt_map_001_train_test_split_001",
                    "train_test_split",
                    "The user can explain held-out evaluation and leakage risks.",
                ),
                _ground_truth_evidence(
                    "ev_gt_map_001_cross_validation_001",
                    "cross_validation",
                    "The user has heard of cross-validation but cannot describe fold rotation.",
                ),
            ],
        },
    )


def _write_confirmed_profile_context(workspace_root: Path) -> None:
    profile_path = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "users"
        / "synthetic_user_001"
        / "profile_context.json"
    )
    profile_path.parent.mkdir(parents=True)
    _write_json(
        profile_path,
        {
            "user_id": "synthetic_user_001",
            "benchmark_domain": "classical_supervised_ml_algorithms",
            "summary": "A practical beginner with limited statistical foundations.",
            "background": ["Has followed introductory sklearn examples."],
            "prior_experience": ["Can run basic estimator workflows."],
            "goals": ["Understand model evaluation."],
            "preferences": ["Prefers concrete examples."],
        },
    )


def _write_candidate_graph_placeholder(workspace_root: Path) -> None:
    candidate_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "candidate_graphs"
        / "v1"
    )
    candidate_dir.mkdir(parents=True)
    _write_json(candidate_dir / "candidate_nodes.json", [])
    _write_json(candidate_dir / "candidate_edges.json", [])


def _write_candidate_map_placeholder(workspace_root: Path) -> None:
    candidate_dir = (
        workspace_root
        / "benchmark"
        / "domains"
        / "classical_supervised_ml_algorithms"
        / "candidate_maps"
        / "gt_map_001"
    )
    candidate_dir.mkdir(parents=True)
    _write_json(candidate_dir / "candidate_map.json", {"kind": "candidate"})


def _knowledge_node(node_id: str, name: str) -> dict[str, object]:
    return {
        "id": node_id,
        "name": name,
        "type": "concept",
        "definition": f"Definition for {name}.",
        "source_locators": [{"source_id": "isl_python", "locator": "chapter 5"}],
        "diagnostic_goal": f"Diagnose understanding of {name}.",
        "levels": {f"L{index}": f"L{index} rubric for {name}." for index in range(6)},
        "diagnostic_signals": [f"Can discuss {name}."],
        "simulator_behavior": f"Answer consistently about {name}.",
    }


def _ground_truth_evidence(
    evidence_id: str,
    node_id: str,
    signal: str,
) -> dict[str, object]:
    return {
        "id": evidence_id,
        "node_id": node_id,
        "evidence_type": "ground_truth_profile",
        "evidence_kind": "prior_answer",
        "visibility": "simulator_only",
        "signal": signal,
    }


def _write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
