from dataclasses import dataclass
import json
from pathlib import Path
import re

from pydantic import ValidationError

from backend.knowact.core.episode import EvaluationEpisodeManifest
from backend.knowact.validation.episode import validate_episode_manifest
from backend.knowact.validation.exceptions import KnowActValidationError


EPISODE_MANIFEST_FILENAME = "episode_manifest.json"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class RuntimeEpisodeIdError(ValueError):
    """Raised when an episode id is unsafe for registry lookup."""


class RuntimeEpisodeNotFoundError(FileNotFoundError):
    """Raised when a runtime episode or its manifest cannot be found."""


class RuntimeEpisodeArtifactError(ValueError):
    """Raised when a runtime episode manifest cannot be parsed or validated."""


@dataclass(frozen=True)
class RuntimeEpisodeRecord:
    episode_id: str
    manifest: EvaluationEpisodeManifest
    episode_dir: Path
    manifest_path: Path


class RuntimeEpisodeRepository:
    """Read runnable Evaluation Episode manifests from the runtime registry."""

    def __init__(self, *, workspace_root: Path) -> None:
        self._registry_root = workspace_root / "benchmark" / "runtime" / "episodes"

    def list_episodes(self) -> tuple[RuntimeEpisodeRecord, ...]:
        if not self._registry_root.exists():
            return ()

        records: list[RuntimeEpisodeRecord] = []
        for episode_dir in sorted(self._registry_root.iterdir()):
            manifest_path = episode_dir / EPISODE_MANIFEST_FILENAME
            if not episode_dir.is_dir() or not manifest_path.exists():
                continue
            episode_id = _validate_safe_id(episode_dir.name, "episode_id")
            records.append(
                _load_episode_record(
                    episode_id=episode_id,
                    episode_dir=episode_dir,
                    manifest_path=manifest_path,
                )
            )
        return tuple(records)

    def read_episode(self, episode_id: str) -> RuntimeEpisodeRecord:
        episode_id = _validate_safe_id(episode_id, "episode_id")
        episode_dir = self._registry_root / episode_id
        manifest_path = episode_dir / EPISODE_MANIFEST_FILENAME
        if not episode_dir.is_dir() or not manifest_path.exists():
            raise RuntimeEpisodeNotFoundError(
                f"Runtime episode {episode_id} does not exist"
            )
        return _load_episode_record(
            episode_id=episode_id,
            episode_dir=episode_dir,
            manifest_path=manifest_path,
        )

    def read_episode_manifest(self, episode_id: str) -> EvaluationEpisodeManifest:
        return self.read_episode(episode_id).manifest


def _load_episode_record(
    *,
    episode_id: str,
    episode_dir: Path,
    manifest_path: Path,
) -> RuntimeEpisodeRecord:
    try:
        with manifest_path.open(encoding="utf-8") as handle:
            manifest = EvaluationEpisodeManifest.model_validate(json.load(handle))
        validate_episode_manifest(manifest)
        if manifest.episode_id != episode_id:
            raise ValueError("Episode manifest episode_id does not match registry path")
    except (
        OSError,
        ValueError,
        ValidationError,
        KnowActValidationError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeEpisodeArtifactError(str(exc)) from exc

    return RuntimeEpisodeRecord(
        episode_id=episode_id,
        manifest=manifest,
        episode_dir=episode_dir,
        manifest_path=manifest_path,
    )


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise RuntimeEpisodeIdError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise RuntimeEpisodeIdError(
            f"{field_name} must contain only letters, numbers, dots, underscores, or dashes"
        )
    return value
