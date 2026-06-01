import json

from pydantic import ValidationError

from backend.knowact.authoring.schemas import GeneratedProfileContext


class ProfileContextOutputParseError(RuntimeError):
    """Raised when profile-context model output cannot be parsed."""


def parse_profile_context_authoring_output(raw_output: str) -> GeneratedProfileContext:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ProfileContextOutputParseError(
            "Profile Context authoring output was not valid JSON: "
            f"{exc.msg} at line {exc.lineno} column {exc.colno}"
        ) from exc

    try:
        return GeneratedProfileContext.model_validate(payload)
    except ValidationError as exc:
        raise ProfileContextOutputParseError(
            f"Profile Context authoring output did not match GeneratedProfileContext: {exc}"
        ) from exc
