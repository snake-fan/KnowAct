import json
import unittest
from pathlib import Path

from backend.knowact.core.episode import EvaluationEpisodeManifest
from backend.knowact.core.graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode
from backend.knowact.core.map import KnowledgeMap
from backend.knowact.validation.episode import validate_episode_manifest
from backend.knowact.validation.graph import validate_knowledge_graph
from backend.knowact.validation.map import validate_knowledge_map


FIXTURE_DIR = Path("benchmark/fixtures/dev_classical_supervised_ml_algorithms")


class V1DevelopmentFixturesTest(unittest.TestCase):
    def test_development_graph_map_and_episode_manifest_validate(self):
        nodes = [
            KnowledgeNode.model_validate(raw_node)
            for raw_node in _load_json("authored_nodes.json")
        ]
        edges = [
            KnowledgeEdge.model_validate(raw_edge)
            for raw_edge in _load_json("authored_edges.json")
        ]
        graph = KnowledgeGraph(nodes=nodes, edges=edges)
        ground_truth_map = KnowledgeMap.model_validate(_load_json("ground_truth_map.json"))
        manifest = EvaluationEpisodeManifest.model_validate(_load_json("episode_manifest.json"))

        validate_knowledge_graph(graph)
        validate_knowledge_map(ground_truth_map, graph)
        validate_episode_manifest(manifest)


def _load_json(filename: str):
    with (FIXTURE_DIR / filename).open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    unittest.main()
