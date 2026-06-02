import json
from pathlib import Path
import re

from pydantic import ValidationError

from backend.knowact.authoring.schemas import ConfirmedProfileContext


CONFIRMED_PROFILE_CONTEXT_FILENAME = "profile_context.json"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ConfirmedProfileContextNotFoundError(FileNotFoundError):
    """Raised when a confirmed Profile Context snapshot does not exist."""


class ConfirmedProfileContextArtifactError(ValueError):
    """Raised when a confirmed Profile Context snapshot is malformed."""


def load_confirmed_profile_context(
    *,
    workspace_root: Path,
    benchmark_domain: str,
    user_id: str,
) -> ConfirmedProfileContext:
    benchmark_domain = _validate_safe_id(benchmark_domain, "benchmark_domain")
    user_id = _validate_safe_id(user_id, "user_id")
    profile_path = (
        workspace_root
        / "benchmark"
        / "domains"
        / benchmark_domain
        / "users"
        / user_id
        / CONFIRMED_PROFILE_CONTEXT_FILENAME
    )
    if not profile_path.exists():
        raise ConfirmedProfileContextNotFoundError(
            f"Confirmed Profile Context user_id {user_id} does not exist"
        )
    try:
        with profile_path.open(encoding="utf-8") as handle:
            profile_context = ConfirmedProfileContext.model_validate(json.load(handle))
        if profile_context.benchmark_domain != benchmark_domain:
            raise ValueError("Confirmed Profile Context benchmark_domain does not match artifact path")
        if profile_context.user_id != user_id:
            raise ValueError("Confirmed Profile Context user_id does not match artifact path")
    except (OSError, ValueError, ValidationError) as exc:
        raise ConfirmedProfileContextArtifactError(str(exc)) from exc
    return profile_context


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} must contain only letters, numbers, dots, underscores, or dashes"
        )
    return value
