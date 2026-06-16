from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
import re

from pydantic import ValidationError

from backend.knowact.core.episode import EvaluationEpisodeManifest
from backend.knowact.core.map import KnowledgeMapKind
from backend.knowact.runtime.visibility import (
    TestedAgentVisibleEpisodeContext,
    build_tested_agent_visible_episode_context,
)
from backend.knowact.storage.profile_contexts import (
    ConfirmedProfileContextArtifactError,
    ConfirmedProfileContextNotFoundError,
    load_confirmed_profile_context,
)
from backend.knowact.storage.reviewed_graphs import (
    ReviewedGraphArtifactError,
    ReviewedGraphArtifacts,
    ReviewedGraphNotFoundError,
    load_reviewed_graph,
)
from backend.knowact.storage.reviewed_maps import (
    ReviewedMapArtifactError,
    ReviewedMapArtifacts,
    ReviewedMapNotFoundError,
    load_reviewed_map,
)
from backend.knowact.validation.episode import validate_episode_manifest
from backend.knowact.validation.exceptions import KnowActValidationError
from backend.knowact.validation.map import validate_knowledge_map


EPISODE_MANIFEST_FILENAME = "episode_manifest.json"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class RuntimeEpisodeIdError(ValueError):
    """Raised when an episode id is unsafe for registry lookup."""


class RuntimeEpisodeNotFoundError(FileNotFoundError):
    """Raised when a runtime episode or its manifest cannot be found."""


class RuntimeEpisodeArtifactError(ValueError):
    """Raised when a runtime episode manifest cannot be parsed or validated."""


class RuntimeEpisodeBindingError(ValueError):
    """Raised when reviewed artifacts cannot be bound to a runtime episode."""


class RuntimeEpisodeReviewedArtifactLoadError(RuntimeEpisodeBindingError):
    """Raised when a reviewed artifact dependency cannot be loaded safely."""


class RuntimeEpisodeIdentityMismatchError(RuntimeEpisodeBindingError):
    """Raised when reviewed artifact identities do not match the episode manifest."""


class RuntimeEpisodeVisibilityError(RuntimeEpisodeBindingError):
    """Raised when a tested-agent-visible context fails visibility validation."""


class RuntimeProfileContextStatus(StrEnum):
    LOADED = "loaded"
    MISSING_OPTIONAL = "missing_optional"


class RuntimeEpisodeBindingWarningCode(StrEnum):
    MISSING_PROFILE_CONTEXT = "missing_profile_context"


@dataclass(frozen=True)
class RuntimeEpisodeRecord:
    episode_id: str
    manifest: EvaluationEpisodeManifest
    episode_dir: Path
    manifest_path: Path


@dataclass(frozen=True)
class RuntimeEpisodeBindingWarning:
    code: RuntimeEpisodeBindingWarningCode
    message: str


@dataclass(frozen=True)
class RuntimeProfileContextBinding:
    benchmark_domain: str
    user_id: str
    status: RuntimeProfileContextStatus
    profile_context: object | None = None


@dataclass(frozen=True)
class RuntimeEpisodeBinding:
    episode_id: str
    manifest: EvaluationEpisodeManifest
    reviewed_graph: ReviewedGraphArtifacts
    hidden_map: ReviewedMapArtifacts
    profile_context: RuntimeProfileContextBinding
    warnings: tuple[RuntimeEpisodeBindingWarning, ...]


class RuntimeEpisodeRepository:
    """Read runnable Evaluation Episode manifests from the runtime registry."""

    def __init__(self, *, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
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

    def load_episode_binding(self, episode_id: str) -> RuntimeEpisodeBinding:
        record = self.read_episode(episode_id)
        return _bind_episode_record(
            workspace_root=self._workspace_root,
            record=record,
        )

    def build_tested_agent_visible_context(
        self,
        episode_id: str,
    ) -> TestedAgentVisibleEpisodeContext:
        binding = self.load_episode_binding(episode_id)
        try:
            return build_tested_agent_visible_episode_context(
                manifest=binding.manifest,
                graph=binding.reviewed_graph.graph,
            )
        except KnowActValidationError as exc:
            raise RuntimeEpisodeVisibilityError(str(exc)) from exc


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


def _bind_episode_record(
    *,
    workspace_root: Path,
    record: RuntimeEpisodeRecord,
) -> RuntimeEpisodeBinding:
    manifest = record.manifest
    try:
        reviewed_graph = load_reviewed_graph(
            workspace_root=workspace_root,
            benchmark_domain=manifest.benchmark_domain,
            version=manifest.graph_version,
        )
    except (ReviewedGraphNotFoundError, ReviewedGraphArtifactError) as exc:
        raise RuntimeEpisodeReviewedArtifactLoadError(
            f"Reviewed graph {manifest.graph_version} cannot be loaded"
        ) from exc

    try:
        hidden_map = load_reviewed_map(
            workspace_root=workspace_root,
            benchmark_domain=manifest.benchmark_domain,
            map_id=manifest.hidden_map_id,
        )
    except (ReviewedMapNotFoundError, ReviewedMapArtifactError) as exc:
        raise RuntimeEpisodeReviewedArtifactLoadError(
            f"Reviewed hidden map {manifest.hidden_map_id} cannot be loaded"
        ) from exc

    try:
        _validate_runtime_episode_artifact_binding(
            manifest=manifest,
            reviewed_graph=reviewed_graph,
            hidden_map=hidden_map,
        )
    except RuntimeEpisodeBindingError:
        raise

    profile_context, warnings = _load_profile_context_binding(
        workspace_root=workspace_root,
        benchmark_domain=hidden_map.manifest.benchmark_domain,
        user_id=hidden_map.manifest.user_id,
    )
    return RuntimeEpisodeBinding(
        episode_id=record.episode_id,
        manifest=manifest,
        reviewed_graph=reviewed_graph,
        hidden_map=hidden_map,
        profile_context=profile_context,
        warnings=warnings,
    )


def _validate_runtime_episode_artifact_binding(
    *,
    manifest: EvaluationEpisodeManifest,
    reviewed_graph: ReviewedGraphArtifacts,
    hidden_map: ReviewedMapArtifacts,
) -> None:
    map_manifest = hidden_map.manifest
    if map_manifest.benchmark_domain != manifest.benchmark_domain:
        raise RuntimeEpisodeIdentityMismatchError(
            "Reviewed map manifest benchmark_domain does not match episode manifest"
        )
    if map_manifest.graph_version != manifest.graph_version:
        raise RuntimeEpisodeIdentityMismatchError(
            "Reviewed map manifest graph_version does not match episode manifest"
        )
    if hidden_map.knowledge_map.kind != KnowledgeMapKind.GROUND_TRUTH:
        raise RuntimeEpisodeReviewedArtifactLoadError(
            "Runtime episodes require a reviewed ground-truth hidden map"
        )
    if hidden_map.knowledge_map.user_id != map_manifest.user_id:
        raise RuntimeEpisodeIdentityMismatchError(
            "Reviewed map user_id does not match reviewed map manifest"
        )
    try:
        validate_knowledge_map(hidden_map.knowledge_map, reviewed_graph.graph)
    except KnowActValidationError as exc:
        raise RuntimeEpisodeReviewedArtifactLoadError(str(exc)) from exc


def _load_profile_context_binding(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    user_id: str,
) -> tuple[RuntimeProfileContextBinding, tuple[RuntimeEpisodeBindingWarning, ...]]:
    try:
        profile_context = load_confirmed_profile_context(
            workspace_root=workspace_root,
            benchmark_domain=benchmark_domain,
            user_id=user_id,
        )
    except ConfirmedProfileContextNotFoundError:
        return (
            RuntimeProfileContextBinding(
                benchmark_domain=benchmark_domain,
                user_id=user_id,
                status=RuntimeProfileContextStatus.MISSING_OPTIONAL,
                profile_context=None,
            ),
            (
                RuntimeEpisodeBindingWarning(
                    code=RuntimeEpisodeBindingWarningCode.MISSING_PROFILE_CONTEXT,
                    message=(
                        "Profile context is unavailable; runtime binding derived "
                        "the profile identity from the reviewed map manifest."
                    ),
                ),
            ),
        )
    except ConfirmedProfileContextArtifactError as exc:
        raise RuntimeEpisodeReviewedArtifactLoadError(
            "Confirmed Profile Context cannot be loaded"
        ) from exc

    return (
        RuntimeProfileContextBinding(
            benchmark_domain=benchmark_domain,
            user_id=user_id,
            status=RuntimeProfileContextStatus.LOADED,
            profile_context=profile_context,
        ),
        (),
    )


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise RuntimeEpisodeIdError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise RuntimeEpisodeIdError(
            f"{field_name} must contain only letters, numbers, dots, underscores, or dashes"
        )
    return value
