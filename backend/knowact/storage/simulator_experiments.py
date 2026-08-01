import json
from hashlib import sha256
from pathlib import Path
import re
import tempfile

from pydantic import ValidationError

from backend.knowact.core.simulator_experiment import (
    SimulatorExperimentQuestionBank,
    SimulatorExperimentQuestionBankSummary,
    SimulatorExperimentSession,
    SimulatorExperimentSessionSummary,
    SimulatorQuestionBankQualityReview,
)
from backend.knowact.validation.simulator_question_bank import (
    SimulatorQuestionBankQualityError,
    validate_question_bank_quality_review,
)


QUESTION_BANKS_RELATIVE_DIR = Path("benchmark/question_banks")
QUESTION_BANK_REVIEWS_DIRNAME = "reviews"
PRIVATE_SESSIONS_RELATIVE_DIR = Path(
    "experiments/02_simulator_human_validity/results/private/sessions"
)
PRIVATE_MAP_REVIEWS_RELATIVE_DIR = Path(
    "experiments/02_simulator_human_validity/results/private/map_reviews"
)
SESSION_FILENAME = "session.json"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class SimulatorExperimentQuestionBankNotFoundError(FileNotFoundError):
    """Raised when a requested Simulator experiment question bank is unavailable."""


class SimulatorExperimentSessionNotFoundError(FileNotFoundError):
    """Raised when a requested Simulator experiment session is unavailable."""


class SimulatorExperimentSessionConflictError(FileExistsError):
    """Raised when a Simulator experiment session id would be overwritten."""


class SimulatorExperimentArtifactError(ValueError):
    """Raised when a Simulator experiment artifact is malformed."""


def list_question_banks(
    *,
    workspace_root: Path,
) -> tuple[SimulatorExperimentQuestionBankSummary, ...]:
    bank_root = workspace_root / QUESTION_BANKS_RELATIVE_DIR
    if not bank_root.exists():
        return ()
    summaries: list[SimulatorExperimentQuestionBankSummary] = []
    for path in sorted(bank_root.glob("*.json")):
        try:
            bank = _read_question_bank(path)
        except SimulatorExperimentArtifactError:
            continue
        summaries.append(
            SimulatorExperimentQuestionBankSummary(
                bank_id=bank.bank_id,
                version=bank.version,
                benchmark_domain=bank.benchmark_domain,
                title=bank.title,
                question_count=len(bank.questions),
            )
        )
    return tuple(summaries)


def load_question_bank(
    *,
    workspace_root: Path,
    bank_id: str,
) -> SimulatorExperimentQuestionBank:
    bank_id = _validate_safe_id(bank_id, "bank_id")
    bank_root = workspace_root / QUESTION_BANKS_RELATIVE_DIR
    for path in sorted(bank_root.glob("*.json")):
        bank = _read_question_bank(path)
        if bank.bank_id == bank_id:
            return bank
    raise SimulatorExperimentQuestionBankNotFoundError(
        f"Simulator experiment question bank {bank_id} does not exist"
    )


def create_simulator_experiment_session(
    *,
    workspace_root: Path,
    session: SimulatorExperimentSession,
) -> Path:
    _validate_safe_id(session.session_id, "session_id")
    session_dir = workspace_root / PRIVATE_SESSIONS_RELATIVE_DIR / session.session_id
    if session_dir.exists():
        raise SimulatorExperimentSessionConflictError(
            f"Simulator experiment session {session.session_id} already exists"
        )
    session_dir.mkdir(parents=True, exist_ok=False)
    session_path = session_dir / SESSION_FILENAME
    _write_json_atomic(session_path, session.model_dump(mode="json"))
    return session_path


def load_simulator_experiment_session(
    *,
    workspace_root: Path,
    session_id: str,
) -> SimulatorExperimentSession:
    session_id = _validate_safe_id(session_id, "session_id")
    session_path = (
        workspace_root / PRIVATE_SESSIONS_RELATIVE_DIR / session_id / SESSION_FILENAME
    )
    if not session_path.exists():
        raise SimulatorExperimentSessionNotFoundError(
            f"Simulator experiment session {session_id} does not exist"
        )
    try:
        with session_path.open(encoding="utf-8") as handle:
            return SimulatorExperimentSession.model_validate(json.load(handle))
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        raise SimulatorExperimentArtifactError(str(exc)) from exc


def save_simulator_experiment_session(
    *,
    workspace_root: Path,
    session: SimulatorExperimentSession,
) -> Path:
    _validate_safe_id(session.session_id, "session_id")
    session_path = (
        workspace_root
        / PRIVATE_SESSIONS_RELATIVE_DIR
        / session.session_id
        / SESSION_FILENAME
    )
    if not session_path.exists():
        raise SimulatorExperimentSessionNotFoundError(
            f"Simulator experiment session {session.session_id} does not exist"
        )
    _write_json_atomic(session_path, session.model_dump(mode="json"))
    return session_path


def list_simulator_experiment_sessions(
    *,
    workspace_root: Path,
) -> tuple[SimulatorExperimentSessionSummary, ...]:
    session_root = workspace_root / PRIVATE_SESSIONS_RELATIVE_DIR
    if not session_root.exists():
        return ()
    summaries: list[SimulatorExperimentSessionSummary] = []
    for session_dir in sorted(session_root.iterdir()):
        if not session_dir.is_dir():
            continue
        try:
            session = load_simulator_experiment_session(
                workspace_root=workspace_root,
                session_id=session_dir.name,
            )
        except (SimulatorExperimentSessionNotFoundError, SimulatorExperimentArtifactError):
            continue
        summaries.append(
            SimulatorExperimentSessionSummary(
                session_id=session.session_id,
                participant_code=session.participant_code,
                status=session.status,
                benchmark_domain=session.benchmark_domain,
                map_id=session.map_id,
                language=session.language,
                answered_questions=sum(
                    question.simulator_answer is not None for question in session.questions
                ),
                evaluated_questions=sum(
                    question.self_evaluation is not None for question in session.questions
                ),
                question_count=len(session.questions),
                created_at=session.created_at,
                completed_at=session.completed_at,
            )
        )
    return tuple(sorted(summaries, key=lambda item: item.created_at, reverse=True))


def write_private_map_review(
    *,
    workspace_root: Path,
    map_id: str,
    payload: dict[str, object],
) -> Path:
    map_id = _validate_safe_id(map_id, "map_id")
    review_path = workspace_root / PRIVATE_MAP_REVIEWS_RELATIVE_DIR / f"{map_id}.json"
    if review_path.exists():
        raise SimulatorExperimentSessionConflictError(
            f"Participant map review for {map_id} already exists"
        )
    review_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(review_path, payload)
    return review_path


def _read_question_bank(path: Path) -> SimulatorExperimentQuestionBank:
    try:
        bank_bytes = path.read_bytes()
        bank = SimulatorExperimentQuestionBank.model_validate(
            json.loads(bank_bytes.decode("utf-8"))
        )
        review_path = (
            path.parent
            / QUESTION_BANK_REVIEWS_DIRNAME
            / f"{bank.bank_id}.quality_review.json"
        )
        review = SimulatorQuestionBankQualityReview.model_validate(
            json.loads(review_path.read_text(encoding="utf-8"))
        )
        validate_question_bank_quality_review(
            bank=bank,
            review=review,
            bank_content_sha256=sha256(bank_bytes).hexdigest(),
        )
        return bank
    except (
        OSError,
        UnicodeDecodeError,
        ValueError,
        ValidationError,
        json.JSONDecodeError,
        SimulatorQuestionBankQualityError,
    ) as exc:
        raise SimulatorExperimentArtifactError(f"{path.name}: {exc}") from exc


def _write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


def _validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} must contain only letters, numbers, dots, underscores, or dashes"
        )
    return value
