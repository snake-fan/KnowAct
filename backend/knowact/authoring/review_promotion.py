from pathlib import Path
import json

from pydantic import ValidationError

from backend.knowact.authoring.map_authoring_output import (
    CandidateMapArtifactError,
    CandidateMapAuthoringRunLog,
    discard_candidate_map_run,
    read_candidate_map_run,
)
from backend.knowact.authoring.validation import (
    validate_candidate_edges,
    validate_complete_candidate_nodes,
)
from backend.knowact.core.evidence import EvidenceType, EvidenceVisibility
from backend.knowact.core.graph import GraphManifest
from backend.knowact.core.map import (
    KnowledgeMap,
    KnowledgeMapKind,
    MapManifest,
    MasteryLevel,
)
from backend.knowact.storage.profile_contexts import load_confirmed_profile_context
from backend.knowact.storage.reviewed_graphs import (
    CandidateGraphArtifactError,
    ReviewedGraphPromotion,
    load_candidate_graph,
    load_reviewed_graph,
    publish_reviewed_graph,
    read_optional_manifest_sources,
)
from backend.knowact.storage.reviewed_maps import (
    ReviewedMapPromotion,
    publish_reviewed_map,
)
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.map import validate_knowledge_map


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


def promote_candidate_map(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    run_id: str,
    map_id: str,
) -> ReviewedMapPromotion:
    candidate_map, artifact_paths = read_candidate_map_run(
        workspace_root=workspace_root,
        benchmark_domain=benchmark_domain,
        run_id=run_id,
    )
    run_log = _read_candidate_map_run_log(
        workspace_root=workspace_root,
        workflow_log_uri=artifact_paths.workflow_log_uri,
    )
    _validate_candidate_map_run_identity(
        benchmark_domain=benchmark_domain,
        run_id=run_id,
        candidate_map=candidate_map,
        run_log=run_log,
    )
    reviewed_graph = load_reviewed_graph(
        workspace_root=workspace_root,
        benchmark_domain=benchmark_domain,
        version=run_log.graph_version,
    )
    load_confirmed_profile_context(
        workspace_root=workspace_root,
        benchmark_domain=benchmark_domain,
        user_id=run_log.user_id,
    )
    reviewed_map = KnowledgeMap(
        user_id=candidate_map.user_id,
        kind=KnowledgeMapKind.GROUND_TRUTH,
        states=candidate_map.states,
        evidence=candidate_map.evidence,
    )
    try:
        validate_knowledge_map(reviewed_map, reviewed_graph.graph)
        _validate_mastery_sensitive_simulator_evidence_minimums(reviewed_map)
    except KnowActValidationError as exc:
        raise CandidateMapArtifactError(str(exc)) from exc

    manifest = MapManifest(
        map_id=map_id,
        user_id=run_log.user_id,
        benchmark_domain=benchmark_domain,
        graph_version=run_log.graph_version,
        promoted_from_candidate_run=run_id,
    )
    promotion = publish_reviewed_map(
        workspace_root=workspace_root,
        benchmark_domain=benchmark_domain,
        map_id=map_id,
        manifest=manifest,
        knowledge_map=reviewed_map,
    )
    discard_candidate_map_run(
        workspace_root=workspace_root,
        benchmark_domain=benchmark_domain,
        run_id=run_id,
    )
    return promotion


def _read_candidate_map_run_log(
    *,
    workspace_root: Path,
    workflow_log_uri: str,
) -> CandidateMapAuthoringRunLog:
    try:
        with (workspace_root / workflow_log_uri).open(encoding="utf-8") as handle:
            run_log = CandidateMapAuthoringRunLog.model_validate(json.load(handle))
        if run_log.status != "succeeded":
            raise ValueError("Candidate map run did not succeed")
    except (OSError, ValueError, ValidationError) as exc:
        raise CandidateMapArtifactError(str(exc)) from exc
    return run_log


def _validate_candidate_map_run_identity(
    *,
    benchmark_domain: str,
    run_id: str,
    candidate_map: KnowledgeMap,
    run_log: CandidateMapAuthoringRunLog,
) -> None:
    if run_log.benchmark_domain != benchmark_domain:
        raise CandidateMapArtifactError(
            "Candidate map workflow log benchmark_domain does not match artifact path"
        )
    if run_log.run_id != run_id:
        raise CandidateMapArtifactError("Candidate map workflow log run_id does not match artifact path")
    if run_log.user_id != candidate_map.user_id:
        raise CandidateMapArtifactError("Candidate map user_id does not match workflow log")


def _validate_mastery_sensitive_simulator_evidence_minimums(reviewed_map: KnowledgeMap) -> None:
    evidence_by_id = {record.id: record for record in reviewed_map.evidence}
    for state in reviewed_map.states:
        simulator_only_count = sum(
            1
            for evidence_ref in state.evidence_refs
            if evidence_by_id[evidence_ref].evidence_type == EvidenceType.GROUND_TRUTH_PROFILE
            and evidence_by_id[evidence_ref].visibility == EvidenceVisibility.SIMULATOR_ONLY
        )
        required_count = _minimum_evidence_count(state.mastery_level)
        if simulator_only_count < required_count:
            raise KnowActValidationError(
                f"Ground-truth state for node {state.node_id} requires at least {required_count} "
                "simulator-only evidence records"
            )


def _minimum_evidence_count(mastery_level: MasteryLevel) -> int:
    if mastery_level in (MasteryLevel.L2, MasteryLevel.L3):
        return 2
    return 1
