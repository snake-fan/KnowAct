from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
from typing import BinaryIO

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.knowact.storage.materials import (
    MAX_RESPONSES_INPUT_FILE_BYTES,
    MaterialFileError,
    MaterialFileSizeError,
    MaterialFileTypeError,
)


SOURCE_MATERIALS_DIRNAME = "source_materials"
SOURCE_MATERIAL_METADATA_FILENAME = "metadata.json"
SOURCE_MATERIAL_PDF_FILENAME = "original.pdf"


class SourceMaterialRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    title: str
    storage_path: str
    storage_uri: str
    filename: str
    size_bytes: int = Field(gt=0)
    uploaded_at: datetime
    citation: str | None = None

    @field_validator("source_id", "title", "storage_path", "storage_uri", "filename")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


def save_pdf_source_material(
    *,
    storage_root: Path,
    source_id: str,
    title: str,
    filename: str,
    content: BinaryIO,
    citation: str | None = None,
    max_size_bytes: int = MAX_RESPONSES_INPUT_FILE_BYTES,
) -> SourceMaterialRecord:
    if not title.strip():
        raise MaterialFileError("title must not be blank")
    if Path(filename).suffix.lower() != ".pdf":
        raise MaterialFileTypeError("only PDF source material files are accepted")

    material_dir = storage_root / SOURCE_MATERIALS_DIRNAME / source_id
    material_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = material_dir / SOURCE_MATERIAL_PDF_FILENAME

    with pdf_path.open("wb") as handle:
        shutil.copyfileobj(content, handle)

    size_bytes = pdf_path.stat().st_size
    if size_bytes <= 0:
        pdf_path.unlink(missing_ok=True)
        raise MaterialFileError("PDF source material file is empty")
    if size_bytes > max_size_bytes:
        pdf_path.unlink(missing_ok=True)
        raise MaterialFileSizeError(
            f"PDF source material is {size_bytes} bytes; limit is {max_size_bytes} bytes"
        )

    storage_path = f"{SOURCE_MATERIALS_DIRNAME}/{source_id}/{SOURCE_MATERIAL_PDF_FILENAME}"
    record = SourceMaterialRecord(
        source_id=source_id,
        title=title,
        citation=citation,
        storage_path=storage_path,
        storage_uri=f"storage/{storage_path}",
        filename=Path(filename).name,
        size_bytes=size_bytes,
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
        records.append(_read_source_material_metadata(metadata_path))
    return tuple(sorted(records, key=lambda record: record.source_id))


def get_source_material(*, storage_root: Path, source_id: str) -> SourceMaterialRecord:
    metadata_path = storage_root / SOURCE_MATERIALS_DIRNAME / source_id / SOURCE_MATERIAL_METADATA_FILENAME
    if not metadata_path.exists():
        raise MaterialFileError(f"source material {source_id} does not exist")
    return _read_source_material_metadata(metadata_path)


def _write_source_material_metadata(path: Path, record: SourceMaterialRecord) -> None:
    payload = record.model_dump(mode="json", exclude_none=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _read_source_material_metadata(path: Path) -> SourceMaterialRecord:
    with path.open(encoding="utf-8") as handle:
        return SourceMaterialRecord.model_validate(json.load(handle))
