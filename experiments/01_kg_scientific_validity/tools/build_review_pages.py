#!/usr/bin/env python3
"""Build the frozen offline HTML packages for the three KG expert reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = EXPERIMENT_ROOT.parents[1]
TEMPLATE_ROOT = EXPERIMENT_ROOT / "templates"
OUTPUT_ROOT = EXPERIMENT_ROOT / "materials" / "review_pages"

PACKAGE_SCHEMA_VERSION = "knowact.kg_review_package.v1"


@dataclass(frozen=True)
class GraphSpec:
    domain: str
    candidate_run_id: str
    output_filename: str
    review_scope_summary: str


# These bindings are intentionally explicit. A newly generated candidate run must
# not silently replace the graph that an expert has already started reviewing.
GRAPH_SPECS = (
    GraphSpec(
        domain="Economy",
        candidate_run_id="kg_metadata_v1_economy_20260730_contract_retry_v6",
        output_filename="economy_kg_review.html",
        review_scope_summary=(
            "这张图谱聚焦《The Economy》前四单元的入门经济学基础，覆盖资本主义制度与长期增长、"
            "技术进步和工业革命、人口与马尔萨斯停滞、稀缺条件下的可行集合与个体选择，以及"
            "策略互动、纳什均衡、公共品和社会偏好等内容。评审重点是这些概念是否被组织成适合"
            "诊断学习者理解水平的知识单元，并由合理的先修、支持、组成或对比关系连接起来。"
        ),
    ),
    GraphSpec(
        domain="ISLP",
        candidate_run_id="kg_metadata_v1_islp_20260730_evidence_v2",
        output_filename="islp_kg_review.html",
        review_scope_summary=(
            "这张图谱聚焦《An Introduction to Statistical Learning》第 2 章相关小节与第 3 章"
            "的统计学习和线性回归基础，覆盖预测与推断目标、模型灵活性与泛化、训练误差和测试误差、"
            "偏差—方差权衡，以及简单和多元线性回归的建模、系数解释、统计推断与诊断。评审重点是"
            "这些知识是否足以支持对学习者概念理解、方法选择和回归结果解释能力的区分。"
        ),
    ),
    GraphSpec(
        domain="OSTEP",
        candidate_run_id="kg_metadata_v1_ostep_20260730_robust_v2",
        output_filename="ostep_kg_review.html",
        review_scope_summary=(
            "这张图谱聚焦《Operating Systems: Three Easy Pieces》中操作系统与 CPU 虚拟化的"
            "基础内容，覆盖操作系统目标、进程抽象与进程 API、受限直接执行、上下文切换，以及"
            "周转时间和响应时间等调度指标、典型调度策略与多级反馈队列。评审重点是这些概念、"
            "机制和策略之间的关系是否准确，并能否用于诊断学习者对进程执行与 CPU 调度的理解。"
        ),
    ),
)


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"Cannot read required review input: {path}") from exc


def _read_json(path: Path) -> Any:
    try:
        return json.loads(_read_bytes(path))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON review input: {path}: {exc}") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _artifact_binding(path: Path) -> dict[str, str]:
    raw = _read_bytes(path)
    return {
        "repository_path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "sha256": _sha256_bytes(raw),
    }


def _graph_fingerprint(binding: dict[str, Any]) -> str:
    canonical = json.dumps(
        binding,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{_sha256_bytes(canonical)}"


def _assert_nonblank(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{label} must be a nonblank string")


def _validate_package(package: dict[str, Any]) -> None:
    graph = package["graph"]
    nodes = package["nodes"]
    edges = package["edges"]
    scope = package["scope"]

    if not isinstance(nodes, list) or not nodes:
        raise RuntimeError(f"{graph['domain']} review package has no nodes")
    if not isinstance(edges, list):
        raise RuntimeError(f"{graph['domain']} review package edges must be a list")
    if not isinstance(scope["representative_tasks"], list) or not scope["representative_tasks"]:
        raise RuntimeError(f"{graph['domain']} review package has no representative tasks")
    _assert_nonblank(scope.get("review_scope_summary"), f"{graph['domain']} review scope summary")

    node_ids: list[str] = []
    for node in nodes:
        _assert_nonblank(node.get("id"), "node.id")
        _assert_nonblank(node.get("name"), f"node[{node.get('id')}].name")
        _assert_nonblank(node.get("definition"), f"node[{node.get('id')}].definition")
        if set(node.get("levels", {})) != {f"L{level}" for level in range(6)}:
            raise RuntimeError(f"Node {node['id']} must contain exactly L0-L5")
        if not node.get("source_locators"):
            raise RuntimeError(f"Node {node['id']} must contain source locators")
        node_ids.append(node["id"])

    if len(node_ids) != len(set(node_ids)):
        raise RuntimeError(f"{graph['domain']} review package has duplicate node ids")

    node_id_set = set(node_ids)
    edge_ids: list[str] = []
    for edge in edges:
        _assert_nonblank(edge.get("id"), "edge.id")
        if edge.get("source") not in node_id_set or edge.get("target") not in node_id_set:
            raise RuntimeError(f"Edge {edge['id']} references an unknown node")
        edge_ids.append(edge["id"])

    if len(edge_ids) != len(set(edge_ids)):
        raise RuntimeError(f"{graph['domain']} review package has duplicate edge ids")

    if graph["node_count"] != len(nodes) or graph["edge_count"] != len(edges):
        raise RuntimeError(f"{graph['domain']} review package counts are inconsistent")
    if graph["representative_task_count"] != len(scope["representative_tasks"]):
        raise RuntimeError(f"{graph['domain']} representative task count is inconsistent")


def build_review_package(spec: GraphSpec) -> dict[str, Any]:
    candidate_root = (
        REPOSITORY_ROOT
        / "benchmark"
        / "domains"
        / spec.domain
        / "candidate_graphs"
        / spec.candidate_run_id
    )
    nodes_path = candidate_root / "candidate_nodes.json"
    edges_path = candidate_root / "candidate_edges.json"
    metadata_path = (
        REPOSITORY_ROOT / "storage" / "source_materials" / spec.domain / "metadata.json"
    )

    nodes = _read_json(nodes_path)
    edges = _read_json(edges_path)
    metadata = _read_json(metadata_path)
    scope = metadata["graph_authoring_scope"]

    binding = {
        "domain": spec.domain,
        "candidate_run_id": spec.candidate_run_id,
        "candidate_nodes": _artifact_binding(nodes_path),
        "candidate_edges": _artifact_binding(edges_path),
        "source_metadata": _artifact_binding(metadata_path),
        "source_content_sha256": metadata["content_sha256"],
    }

    package = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "review_input_kind": "candidate_graph",
        "graph": {
            "domain": spec.domain,
            "candidate_run_id": spec.candidate_run_id,
            "review_package_id": f"{spec.domain}:{spec.candidate_run_id}",
            "graph_fingerprint": _graph_fingerprint(binding),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "representative_task_count": len(scope["representative_tasks"]),
            "artifact_binding": binding,
        },
        "source": {
            "source_id": metadata["source_id"],
            "title": metadata["title"],
            "citation": metadata["citation"],
            "storage_uri": metadata["storage_uri"],
            "content_sha256": metadata["content_sha256"],
        },
        "scope": {
            "aspect_name": scope["aspect_name"],
            "aspect_description": scope["aspect_description"],
            "review_scope_summary": spec.review_scope_summary,
            "representative_tasks": scope["representative_tasks"],
            "excluded_topics": scope["excluded_topics"],
            "target_node_count": scope["target_node_count"],
            "max_node_count": scope["max_node_count"],
        },
        "nodes": nodes,
        "edges": edges,
    }
    _validate_package(package)
    return package


def _json_for_html(value: Any) -> str:
    # Keep the JSON directly parseable while preventing data from closing its
    # application/json script element.
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _render_template(template_name: str, replacements: dict[str, str]) -> str:
    template_path = TEMPLATE_ROOT / template_name
    rendered = _read_bytes(template_path).decode("utf-8")
    for token, value in replacements.items():
        rendered = rendered.replace(f"{{{{{token}}}}}", value)
    unresolved = [token for token in replacements if f"{{{{{token}}}}}" in rendered]
    if unresolved:
        raise RuntimeError(f"Unresolved template tokens in {template_path}: {unresolved}")
    return rendered


def build_outputs() -> dict[Path, str]:
    packages = [build_review_package(spec) for spec in GRAPH_SPECS]
    outputs: dict[Path, str] = {}

    for spec, package in zip(GRAPH_SPECS, packages, strict=True):
        title = f"{spec.domain} Candidate KG Expert Review"
        outputs[OUTPUT_ROOT / spec.output_filename] = _render_template(
            "kg_review_page.template.html",
            {
                "PAGE_TITLE": title,
                "REVIEW_PACKAGE_JSON": _json_for_html(package),
            },
        )

    outputs[OUTPUT_ROOT / "compare_and_confirm.html"] = _render_template(
        "kg_compare_confirm.template.html",
        {
            "PAGE_TITLE": "KnowAct KG Review Comparison and Confirmation",
            "REVIEW_PACKAGES_JSON": _json_for_html(packages),
        },
    )
    return outputs


def write_outputs(outputs: dict[Path, str]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(REPOSITORY_ROOT)}")


def check_outputs(outputs: dict[Path, str]) -> bool:
    stale: list[Path] = []
    for path, expected in outputs.items():
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError:
            stale.append(path)
            continue
        if actual != expected:
            stale.append(path)

    if stale:
        for path in stale:
            print(f"stale or missing: {path.relative_to(REPOSITORY_ROOT)}", file=sys.stderr)
        print(
            "Run experiments/01_kg_scientific_validity/tools/build_review_pages.py "
            "to regenerate the frozen pages.",
            file=sys.stderr,
        )
        return False

    print(f"verified {len(outputs)} frozen KG review pages")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when a generated page does not match its current frozen inputs",
    )
    args = parser.parse_args()

    try:
        outputs = build_outputs()
        if args.check:
            return 0 if check_outputs(outputs) else 1
        write_outputs(outputs)
        return 0
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
