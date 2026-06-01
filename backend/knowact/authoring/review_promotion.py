from pathlib import Path

from backend.knowact.authoring.validation import (
    validate_candidate_edges,
    validate_complete_candidate_nodes,
)
from backend.knowact.core.graph import GraphManifest
from backend.knowact.storage.reviewed_graphs import (
    CandidateGraphArtifactError,
    ReviewedGraphPromotion,
    load_candidate_graph,
    publish_reviewed_graph,
    read_optional_manifest_sources,
)
from backend.knowact.validation.exceptions import KnowActValidationError


def promote_candidate_graph(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    run_id: str,
    version: str,
) -> ReviewedGraphPromotion:
    candidate_graph = load_candidate_graph(
        workspace_root=workspace_root,
        benchmark_domain=benchmark_domain,
        run_id=run_id,
    )
    try:
        validate_complete_candidate_nodes(candidate_graph.nodes)
        validate_candidate_edges(candidate_graph.nodes, candidate_graph.edges)
    except KnowActValidationError as exc:
        raise CandidateGraphArtifactError(str(exc)) from exc

    manifest = GraphManifest(
        graph_id=f"kg_{benchmark_domain}_{version}",
        domain=benchmark_domain,
        version=version,
        promoted_from_candidate_run=run_id,
        source=read_optional_manifest_sources(candidate_graph.candidate_dir),
    )
    return publish_reviewed_graph(
        workspace_root=workspace_root,
        benchmark_domain=benchmark_domain,
        version=version,
        manifest=manifest,
        nodes=candidate_graph.nodes,
        edges=candidate_graph.edges,
    )
