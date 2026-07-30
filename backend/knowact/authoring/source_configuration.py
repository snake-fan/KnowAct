import json
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from backend.knowact.authoring.schemas import GraphAuthoringScope
from backend.knowact.storage.source_material_catalog import (
    SOURCE_MATERIAL_METADATA_FILENAME,
    SOURCE_MATERIALS_DIRNAME,
    MaterialFileError,
    SourceMaterialRecord,
    get_source_material,
)


FIXED_GRAPH_AUTHORING_SOURCE_IDS = ("Economy", "ISLP", "OSTEP")


class GraphAuthoringSourceConfigurationError(MaterialFileError):
    """Raised when a filesystem-managed graph source has invalid authoring metadata."""


class QuestionBankReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    url: str
    scope_note: str

    @field_validator("title", "url", "scope_note")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("url")
    @classmethod
    def _must_be_http_url(cls, value: str) -> str:
        if not value.startswith(("https://", "http://")):
            raise ValueError("must be an HTTP(S) URL")
        return value


class GraphAuthoringSourceMetadata(SourceMaterialRecord):
    """One fixed research source plus its complete graph-authoring configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metadata_version: Literal["1.0"]
    benchmark_domain: str
    content_sha256: str
    graph_authoring_scope: GraphAuthoringScope
    question_bank_method: Literal["reference_grounded_original_questions"]
    question_bank_sources: tuple[QuestionBankReference, ...] = Field(min_length=1)

    @field_validator("benchmark_domain")
    @classmethod
    def _benchmark_domain_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("content_sha256")
    @classmethod
    def _content_hash_must_be_sha256(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError("must be a 64-character SHA-256 digest")
        try:
            int(value, 16)
        except ValueError as exc:
            raise ValueError("must be a hexadecimal SHA-256 digest") from exc
        return value.lower()

    @model_validator(mode="after")
    def _validate_fixed_research_contract(self) -> "GraphAuthoringSourceMetadata":
        if self.source_id not in FIXED_GRAPH_AUTHORING_SOURCE_IDS:
            raise ValueError(
                "source_id must be one of "
                + ", ".join(FIXED_GRAPH_AUTHORING_SOURCE_IDS)
            )
        if self.benchmark_domain != self.source_id:
            raise ValueError("benchmark_domain must equal source_id for fixed research sources")
        expected_parent = Path(SOURCE_MATERIALS_DIRNAME) / self.source_id
        if Path(self.storage_path).parent != expected_parent:
            raise ValueError("storage_path must stay inside the source_id directory")
        if self.storage_uri != f"storage/{self.storage_path}":
            raise ValueError("storage_uri must equal storage/{storage_path}")
        if Path(self.storage_path).name != self.filename:
            raise ValueError("filename must match the storage_path filename")
        if len(self.graph_authoring_scope.representative_tasks) < 50:
            raise ValueError("graph_authoring_scope must contain at least 50 representative tasks")
        normalized_tasks = {
            task.strip().casefold()
            for task in self.graph_authoring_scope.representative_tasks
        }
        if len(normalized_tasks) != len(self.graph_authoring_scope.representative_tasks):
            raise ValueError("graph_authoring_scope representative tasks must be unique")
        return self

    def source_record(self) -> SourceMaterialRecord:
        return SourceMaterialRecord.model_validate(self.model_dump())


def list_graph_authoring_source_metadata(
    *,
    storage_root: Path,
) -> tuple[GraphAuthoringSourceMetadata, ...]:
    source_root = storage_root / SOURCE_MATERIALS_DIRNAME
    if not source_root.exists():
        return ()

    configured_sources: list[GraphAuthoringSourceMetadata] = []
    for metadata_path in sorted(source_root.glob(f"*/{SOURCE_MATERIAL_METADATA_FILENAME}")):
        try:
            payload = _read_json_object(metadata_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise GraphAuthoringSourceConfigurationError(
                f"invalid source metadata at {metadata_path}: {exc}"
            ) from exc
        if "graph_authoring_scope" not in payload:
            continue
        configured_sources.append(
            _validate_source_metadata(payload, metadata_path=metadata_path)
        )
    return tuple(sorted(configured_sources, key=lambda item: item.source_id))


def load_graph_authoring_source_metadata(
    *,
    storage_root: Path,
    source_id: str,
) -> GraphAuthoringSourceMetadata:
    record = get_source_material(storage_root=storage_root, source_id=source_id)
    metadata_path = (
        storage_root
        / SOURCE_MATERIALS_DIRNAME
        / record.source_id
        / SOURCE_MATERIAL_METADATA_FILENAME
    )
    try:
        payload = _read_json_object(metadata_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise GraphAuthoringSourceConfigurationError(
            f"invalid source metadata for {source_id}: {exc}"
        ) from exc
    if "graph_authoring_scope" not in payload:
        raise GraphAuthoringSourceConfigurationError(
            f"source material {source_id} has no graph_authoring_scope configuration"
        )
    metadata = _validate_source_metadata(payload, metadata_path=metadata_path)
    if metadata.source_record() != record:
        raise GraphAuthoringSourceConfigurationError(
            f"source material {source_id} metadata is internally inconsistent"
        )
    return metadata


def _read_json_object(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("metadata root must be a JSON object")
    return payload


def _validate_source_metadata(
    payload: dict[str, object],
    *,
    metadata_path: Path,
) -> GraphAuthoringSourceMetadata:
    try:
        return GraphAuthoringSourceMetadata.model_validate(payload)
    except ValidationError as exc:
        raise GraphAuthoringSourceConfigurationError(
            f"invalid graph-authoring source metadata at {metadata_path}: {exc}"
        ) from exc
