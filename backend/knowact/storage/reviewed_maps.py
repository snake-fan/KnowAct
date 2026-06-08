from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import tempfile

from pydantic import BaseModel, ValidationError

from backend.knowact.core.map import KnowledgeMap, MapManifest


MAP_FILENAME = "map.json"
MAP_MANIFEST_FILENAME = "map_manifest.json"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ReviewedMapPromotionConflictError(FileExistsError):
    """Raised when promotion would overwrite an immutable reviewed map id."""


class ReviewedMapNotFoundError(FileNotFoundError):
    """Raised when a reviewed map snapshot cannot be found."""


class ReviewedMapArtifactError(ValueError):
    """Raised when a reviewed map snapshot has malformed artifacts."""


@dataclass(frozen=True)
class ReviewedMapPromotion:
    manifest: MapManifest
    knowledge_map: KnowledgeMap
    output_dir: Path
    map_manifest_path: Path
    map_path: Path


@dataclass(frozen=True)
class ReviewedMapArtifacts:
    manifest: MapManifest
    knowledge_map: KnowledgeMap
    map_dir: Path


def load_reviewed_map(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    map_id: str,
) -> ReviewedMapArtifacts:
    benchmark_domain = _validate_safe_id(benchmark_domain, "benchmark_domain")
    map_id = _validate_safe_id(map_id, "map_id")
    map_dir = workspace_root / "benchmark" / "domains" / benchmark_domain / "maps" / map_id
    if not map_dir.exists() or not map_dir.is_dir():
        raise ReviewedMapNotFoundError(f"Reviewed map {map_id} does not exist")

    manifest_path = map_dir / MAP_MANIFEST_FILENAME
    map_path = map_dir / MAP_FILENAME
    if not manifest_path.exists() or not map_path.exists():
        raise ReviewedMapNotFoundError(f"Reviewed map {map_id} is missing map artifacts")

    try:
        with manifest_path.open(encoding="utf-8") as handle:
            manifest = MapManifest.model_validate(json.load(handle))
        with map_path.open(encoding="utf-8") as handle:
            knowledge_map = KnowledgeMap.model_validate(json.load(handle))
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        raise ReviewedMapArtifactError(str(exc)) from exc

    if manifest.map_id != map_id:
        raise ReviewedMapArtifactError(
            f"Reviewed map directory {map_id} contains manifest for {manifest.map_id}"
        )
    if manifest.benchmark_domain != benchmark_domain:
        raise ReviewedMapArtifactError(
            f"Reviewed map {map_id} belongs to benchmark domain {manifest.benchmark_domain}"
        )
    return ReviewedMapArtifacts(
        manifest=manifest,
        knowledge_map=knowledge_map,
        map_dir=map_dir,
    )


def load_reviewed_map_manifest(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    map_id: str,
) -> MapManifest:
    benchmark_domain = _validate_safe_id(benchmark_domain, "benchmark_domain")
    map_id = _validate_safe_id(map_id, "map_id")
    map_dir = workspace_root / "benchmark" / "domains" / benchmark_domain / "maps" / map_id
    if not map_dir.exists() or not map_dir.is_dir():
        raise ReviewedMapNotFoundError(f"Reviewed map {map_id} does not exist")

    manifest_path = map_dir / MAP_MANIFEST_FILENAME
    if not manifest_path.exists():
        raise ReviewedMapNotFoundError(f"Reviewed map {map_id} is missing map manifest")

    try:
        with manifest_path.open(encoding="utf-8") as handle:
            manifest = MapManifest.model_validate(json.load(handle))
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        raise ReviewedMapArtifactError(str(exc)) from exc

    if manifest.map_id != map_id:
        raise ReviewedMapArtifactError(
            f"Reviewed map directory {map_id} contains manifest for {manifest.map_id}"
        )
    if manifest.benchmark_domain != benchmark_domain:
        raise ReviewedMapArtifactError(
            f"Reviewed map {map_id} belongs to benchmark domain {manifest.benchmark_domain}"
        )
    return manifest


def publish_reviewed_map(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    map_id: str,
    manifest: MapManifest,
    knowledge_map: KnowledgeMap,
) -> ReviewedMapPromotion:
    benchmark_domain = _validate_safe_id(benchmark_domain, "benchmark_domain")
    map_id = _validate_safe_id(map_id, "map_id")
    map_root = workspace_root / "benchmark" / "domains" / benchmark_domain / "maps"
    output_dir = map_root / map_id
    if output_dir.exists():
        raise ReviewedMapPromotionConflictError(f"Map id {map_id} already exists")
    existing_map_id = _find_existing_map_id_for_candidate_run(
        map_root=map_root,
        run_id=manifest.promoted_from_candidate_run,
    )
    if existing_map_id is not None:
        raise ReviewedMapPromotionConflictError(
            f"Candidate map run {manifest.promoted_from_candidate_run} was already "
            f"promoted as map {existing_map_id}"
        )

    map_root.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{map_id}.", dir=map_root))
    try:
        _write_json_model(staging_dir / MAP_FILENAME, knowledge_map)
        _write_json_model(staging_dir / MAP_MANIFEST_FILENAME, manifest)
        _publish_staged_directory(staging_dir, output_dir)
    except Exception:
        _remove_path(staging_dir)
        raise

    return ReviewedMapPromotion(
        manifest=manifest,
        knowledge_map=knowledge_map,
        output_dir=output_dir,
        map_manifest_path=output_dir / MAP_MANIFEST_FILENAME,
        map_path=output_dir / MAP_FILENAME,
    )


def find_reviewed_map_id_for_candidate_run(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    run_id: str,
) -> str | None:
    benchmark_domain = _validate_safe_id(benchmark_domain, "benchmark_domain")
    run_id = _validate_safe_id(run_id, "run_id")
    map_root = workspace_root / "benchmark" / "domains" / benchmark_domain / "maps"
    return _find_existing_map_id_for_candidate_run(map_root=map_root, run_id=run_id)


def _publish_staged_directory(staging_dir: Path, output_dir: Path) -> None:
    if output_dir.exists():
        raise ReviewedMapPromotionConflictError(
            f"Map id {output_dir.name} already exists"
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
                manifest = MapManifest.model_validate(json.load(handle))
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
