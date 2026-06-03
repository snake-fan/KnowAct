from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import tempfile

from pydantic import BaseModel, ValidationError

from backend.knowact.core.map import GroundTruthMapManifest, KnowledgeMap


GROUND_TRUTH_MAP_FILENAME = "ground_truth_map.json"
MAP_MANIFEST_FILENAME = "map_manifest.json"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ReviewedMapPromotionConflictError(FileExistsError):
    """Raised when promotion would overwrite an immutable reviewed map id."""


@dataclass(frozen=True)
class ReviewedMapPromotion:
    manifest: GroundTruthMapManifest
    ground_truth_map: KnowledgeMap
    output_dir: Path
    map_manifest_path: Path
    ground_truth_map_path: Path


def publish_reviewed_ground_truth_map(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    map_id: str,
    manifest: GroundTruthMapManifest,
    ground_truth_map: KnowledgeMap,
) -> ReviewedMapPromotion:
    benchmark_domain = _validate_safe_id(benchmark_domain, "benchmark_domain")
    map_id = _validate_safe_id(map_id, "map_id")
    map_root = workspace_root / "benchmark" / "domains" / benchmark_domain / "ground_truth_maps"
    output_dir = map_root / map_id
    if output_dir.exists():
        raise ReviewedMapPromotionConflictError(f"Ground-truth map id {map_id} already exists")
    existing_map_id = _find_existing_map_id_for_candidate_run(
        map_root=map_root,
        run_id=manifest.promoted_from_candidate_run,
    )
    if existing_map_id is not None:
        raise ReviewedMapPromotionConflictError(
            f"Candidate map run {manifest.promoted_from_candidate_run} was already "
            f"promoted as ground-truth map {existing_map_id}"
        )

    map_root.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{map_id}.", dir=map_root))
    try:
        _write_json_model(staging_dir / GROUND_TRUTH_MAP_FILENAME, ground_truth_map)
        _write_json_model(staging_dir / MAP_MANIFEST_FILENAME, manifest)
        _publish_staged_directory(staging_dir, output_dir)
    except Exception:
        _remove_path(staging_dir)
        raise

    return ReviewedMapPromotion(
        manifest=manifest,
        ground_truth_map=ground_truth_map,
        output_dir=output_dir,
        map_manifest_path=output_dir / MAP_MANIFEST_FILENAME,
        ground_truth_map_path=output_dir / GROUND_TRUTH_MAP_FILENAME,
    )


def _publish_staged_directory(staging_dir: Path, output_dir: Path) -> None:
    if output_dir.exists():
        raise ReviewedMapPromotionConflictError(
            f"Ground-truth map id {output_dir.name} already exists"
        )
    staging_dir.replace(output_dir)


def _find_existing_map_id_for_candidate_run(*, map_root: Path, run_id: str) -> str | None:
    if not map_root.exists():
        return None
    for entry in sorted(map_root.iterdir()):
        manifest_path = entry / MAP_MANIFEST_FILENAME
        if not entry.is_dir() or not manifest_path.exists():
            continue
        try:
            with manifest_path.open(encoding="utf-8") as handle:
                manifest = GroundTruthMapManifest.model_validate(json.load(handle))
        except (OSError, ValueError, ValidationError, json.JSONDecodeError):
            continue
        if manifest.promoted_from_candidate_run == run_id:
            return manifest.map_id
    return None


def _write_json_model(path: Path, model: BaseModel) -> None:
    payload = model.model_dump(mode="json")
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} must contain only letters, numbers, dots, underscores, or dashes"
        )
    return value
