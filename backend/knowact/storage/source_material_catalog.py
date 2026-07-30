from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import BinaryIO

from pydantic import BaseModel, ConfigDict, Field, field_validator


SOURCE_MATERIALS_DIRNAME = "source_materials"
SOURCE_MATERIAL_METADATA_FILENAME = "metadata.json"
SOURCE_MATERIAL_MARKDOWN_FILENAME = "source.md"
MAX_MARKDOWN_SOURCE_BYTES = 20_000_000
_SAFE_SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class MaterialFileError(ValueError):
    """Raised when an uploaded Markdown source cannot be used safely."""


class MaterialFileNotFoundError(MaterialFileError):
    """Raised when a catalog source or its Markdown file does not exist."""


class MaterialFileTypeError(MaterialFileError):
    """Raised when a source is not Markdown."""


class MaterialFileSizeError(MaterialFileError):
    """Raised when a Markdown source is larger than the authoring limit."""


class MaterialFileIntegrityError(MaterialFileError):
    """Raised when stored Markdown no longer matches its catalog hash."""


class SourceMaterialRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    title: str
    storage_path: str
    storage_uri: str
    filename: str
    size_bytes: int = Field(gt=0)
    content_sha256: str | None = None
    uploaded_at: datetime
    citation: str | None = None

    @field_validator("source_id", "title", "storage_path", "storage_uri", "filename")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


@dataclass(frozen=True)
class LocalMarkdownMaterial:
    record: SourceMaterialRecord
    path: Path
    text: str

    @property
    def storage_uri(self) -> str:
        return self.record.storage_uri

    @property
    def filename(self) -> str:
        return self.record.filename

    @property
    def size_bytes(self) -> int:
        return self.record.size_bytes


def save_markdown_source_material(
    *,
    storage_root: Path,
    source_id: str,
    title: str,
    filename: str,
    content: BinaryIO,
    citation: str | None = None,
    max_size_bytes: int = MAX_MARKDOWN_SOURCE_BYTES,
) -> SourceMaterialRecord:
    if not _SAFE_SOURCE_ID_PATTERN.fullmatch(source_id):
        raise MaterialFileError(
            "source_id must contain only letters, numbers, dots, underscores, or dashes"
        )
    if not title.strip():
        raise MaterialFileError("title must not be blank")
    if Path(filename).suffix.lower() not in {".md", ".markdown"}:
        raise MaterialFileTypeError("only Markdown source material files are accepted")

    payload = content.read(max_size_bytes + 1)
    if not payload:
        raise MaterialFileError("Markdown source material file is empty")
    if len(payload) > max_size_bytes:
        raise MaterialFileSizeError(
            f"Markdown source material is larger than the {max_size_bytes}-byte limit"
        )
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MaterialFileError("Markdown source material must be UTF-8 encoded") from exc
    if not text.strip():
        raise MaterialFileError("Markdown source material contains no non-whitespace text")

    material_dir = storage_root / SOURCE_MATERIALS_DIRNAME / source_id
    material_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = material_dir / SOURCE_MATERIAL_MARKDOWN_FILENAME
    markdown_path.write_bytes(payload)

    storage_path = f"{SOURCE_MATERIALS_DIRNAME}/{source_id}/{SOURCE_MATERIAL_MARKDOWN_FILENAME}"
    record = SourceMaterialRecord(
        source_id=source_id,
        title=title.strip(),
        citation=citation.strip() if citation and citation.strip() else None,
        storage_path=storage_path,
        storage_uri=f"storage/{storage_path}",
        filename=Path(filename).name,
        size_bytes=len(payload),
        content_sha256=hashlib.sha256(payload).hexdigest(),
        uploaded_at=datetime.now(UTC),
    )
    _write_source_material_metadata(material_dir / SOURCE_MATERIAL_METADATA_FILENAME, record)
    return record


def list_source_materials(*, storage_root: Path) -> tuple[SourceMaterialRecord, ...]:
    source_materials_root = storage_root / SOURCE_MATERIALS_DIRNAME
    if not source_materials_root.exists():
        return ()

    records = []
    for metadata_path in sorted(source_materials_root.glob(f"*/{SOURCE_MATERIAL_METADATA_FILENAME}")):
        record = _read_source_material_metadata(metadata_path)
        if Path(record.storage_path).suffix.lower() in {".md", ".markdown"}:
            records.append(record)
    return tuple(sorted(records, key=lambda record: record.source_id))


def get_source_material(*, storage_root: Path, source_id: str) -> SourceMaterialRecord:
    if not _SAFE_SOURCE_ID_PATTERN.fullmatch(source_id):
        raise MaterialFileError("invalid source_id")
    metadata_path = storage_root / SOURCE_MATERIALS_DIRNAME / source_id / SOURCE_MATERIAL_METADATA_FILENAME
    if not metadata_path.exists():
        raise MaterialFileNotFoundError(f"source material {source_id} does not exist")
    record = _read_source_material_metadata(metadata_path)
    if Path(record.storage_path).suffix.lower() not in {".md", ".markdown"}:
        raise MaterialFileTypeError(
            f"source material {source_id} is a legacy non-Markdown upload; upload its Markdown version"
        )
    return record


def load_markdown_source_material(*, storage_root: Path, source_id: str) -> LocalMarkdownMaterial:
    record = get_source_material(storage_root=storage_root, source_id=source_id)
    root = storage_root.resolve()
    path = (root / record.storage_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise MaterialFileError("source material path must stay under storage/") from exc
    if not path.exists() or not path.is_file():
        raise MaterialFileNotFoundError(f"{record.storage_uri} does not exist")

    payload = path.read_bytes()
    if len(payload) != record.size_bytes:
        raise MaterialFileIntegrityError(
            f"source material {source_id} size no longer matches catalog metadata"
        )
    digest = hashlib.sha256(payload).hexdigest()
    if record.content_sha256 is not None and digest != record.content_sha256:
        raise MaterialFileIntegrityError(
            f"source material {source_id} hash no longer matches catalog metadata"
        )
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MaterialFileError("stored Markdown source is not UTF-8 encoded") from exc
    if not text.strip():
        raise MaterialFileError("stored Markdown source contains no non-whitespace text")
    return LocalMarkdownMaterial(record=record, path=path, text=text)


def _write_source_material_metadata(path: Path, record: SourceMaterialRecord) -> None:
    payload = record.model_dump(mode="json", exclude_none=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _read_source_material_metadata(path: Path) -> SourceMaterialRecord:
    with path.open(encoding="utf-8") as handle:
        return SourceMaterialRecord.model_validate(json.load(handle))
