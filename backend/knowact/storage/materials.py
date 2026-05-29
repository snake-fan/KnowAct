from dataclasses import dataclass
from pathlib import Path

MAX_RESPONSES_INPUT_FILE_BYTES = 100_000_000


class MaterialFileError(ValueError):
    """Raised when a local source material file is not usable."""


class MaterialFileNotFoundError(MaterialFileError):
    """Raised when the requested local source material file does not exist."""


class MaterialFileTypeError(MaterialFileError):
    """Raised when the requested local source material is not an accepted file type."""


class MaterialFileSizeError(MaterialFileError):
    """Raised when a local source material file is too large for the target API path."""


@dataclass(frozen=True)
class LocalPDFMaterial:
    path: Path
    storage_uri: str
    filename: str
    size_bytes: int


def resolve_pdf_material(
    *,
    storage_root: Path,
    storage_path: str,
    max_size_bytes: int = MAX_RESPONSES_INPUT_FILE_BYTES,
) -> LocalPDFMaterial:
    """Resolve a PDF material path that must stay under the local storage root."""

    if not storage_path.strip():
        raise MaterialFileError("storage_path must not be blank")

    requested_path = Path(storage_path)
    if requested_path.is_absolute():
        raise MaterialFileError("storage_path must be relative to storage/")

    root = storage_root.resolve()
    path = (root / requested_path).resolve()
    try:
        relative_path = path.relative_to(root)
    except ValueError as exc:
        raise MaterialFileError("storage_path must stay under storage/") from exc

    if not path.exists():
        raise MaterialFileNotFoundError(
            f"storage/{relative_path.as_posix()} does not exist"
        )
    if not path.is_file():
        raise MaterialFileError(f"storage/{relative_path.as_posix()} is not a file")
    if path.suffix.lower() != ".pdf":
        raise MaterialFileTypeError("only PDF source material files are accepted")

    size_bytes = path.stat().st_size
    if size_bytes <= 0:
        raise MaterialFileError("PDF source material file is empty")
    if size_bytes > max_size_bytes:
        raise MaterialFileSizeError(
            f"PDF source material is {size_bytes} bytes; limit is {max_size_bytes} bytes"
        )

    return LocalPDFMaterial(
        path=path,
        storage_uri=f"storage/{relative_path.as_posix()}",
        filename=path.name,
        size_bytes=size_bytes,
    )
