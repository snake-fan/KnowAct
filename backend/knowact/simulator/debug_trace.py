from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import shutil
from typing import Any


SIMULATOR_TRACE_ROOT_DIRNAME = "simulator"
DEBUG_TRACE_FILENAME = "debug_trace.json"
AGENT_TRACES_DIRNAME = "agent_traces"
MODEL_RAW_OUTPUT_FILENAME = "model_raw_output.txt"
PARSER_OUTPUT_FILENAME = "parser_output.json"

ANSWER_POLICY_STEP = "answer_policy"
ANSWER_GENERATION_STEP = "answer_generation"
ANSWER_VALIDATION_STEP = "answer_validation"

_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_ACTIVE_RECORDER: ContextVar["SimulatorDebugTraceRecorder | None"] = ContextVar(
    "active_simulator_debug_trace_recorder",
    default=None,
)
_ACTIVE_MODEL_STEP: ContextVar["_ActiveModelStep | None"] = ContextVar(
    "active_simulator_model_step",
    default=None,
)


@dataclass(frozen=True)
class _ActiveModelStep:
    step_name: str
    attempt_index: int | None = None


class SimulatorDebugTraceRecorder:
    def __init__(
        self,
        *,
        workspace_root: Path,
        benchmark_domain: str,
        map_id: str,
        question_trace_id: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self.benchmark_domain = validate_safe_id(benchmark_domain, "benchmark_domain")
        self.map_id = validate_safe_id(map_id, "map_id")
        self.trace_id = validate_safe_id(question_trace_id, "question_id")
        self._clock = clock or _utc_now
        self._started_at = self._clock()
        self._output_dir = (
            workspace_root
            / "benchmark"
            / "domains"
            / self.benchmark_domain
            / SIMULATOR_TRACE_ROOT_DIRNAME
            / self.map_id
            / self.trace_id
        )
        self._payload: dict[str, Any] = {
            "trace_kind": "simulator_turn",
            "trace_id": self.trace_id,
            "started_at": _isoformat(self._started_at),
            "request": {},
            "artifact_bindings": {
                "benchmark_domain": self.benchmark_domain,
                "map_id": self.map_id,
            },
            "artifact_paths": {},
            "workflow": {},
            "model_steps": {},
            "generation_attempts": [],
        }

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    @property
    def debug_trace_path(self) -> Path:
        return self._output_dir / DEBUG_TRACE_FILENAME

    def prepare_output_dir(self) -> None:
        if self._output_dir.exists():
            shutil.rmtree(self._output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._payload["artifact_paths"] = {
            "output_dir_uri": self._relative_uri(self._output_dir),
            "debug_trace_uri": self._relative_uri(self.debug_trace_path),
            "agent_traces_dir_uri": self._relative_uri(
                self._output_dir / AGENT_TRACES_DIRNAME
            ),
        }

    def set_request(self, payload: dict[str, Any]) -> None:
        self._payload["request"] = payload

    def set_artifact_bindings(self, payload: dict[str, Any]) -> None:
        self._payload["artifact_bindings"] = {
            **self._payload["artifact_bindings"],
            **payload,
        }

    def set_workflow_section(self, section_name: str, payload: dict[str, Any]) -> None:
        self._payload["workflow"][section_name] = payload

    def append_generation_attempt(self, payload: dict[str, Any]) -> None:
        self._payload["generation_attempts"].append(payload)

    def set_fallback(self, payload: dict[str, Any]) -> None:
        self._payload["fallback"] = payload

    def set_visible_output(self, payload: dict[str, Any]) -> None:
        self._payload["visible_output"] = payload

    def set_warnings(self, warnings: tuple[dict[str, Any], ...]) -> None:
        self._payload["warnings"] = list(warnings)

    def write_model_raw_output(
        self,
        *,
        step_name: str,
        raw_output: str,
        attempt_index: int | None = None,
    ) -> None:
        step_dir = self._model_step_dir(step_name=step_name, attempt_index=attempt_index)
        step_dir.mkdir(parents=True, exist_ok=True)
        output_path = step_dir / MODEL_RAW_OUTPUT_FILENAME
        output_path.write_text(raw_output, encoding="utf-8")
        self._model_step_payload(
            step_name=step_name,
            attempt_index=attempt_index,
        )["model_raw_output_uri"] = self._relative_uri(output_path)

    def write_parser_output(
        self,
        *,
        step_name: str,
        status: str,
        output: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        attempt_index: int | None = None,
    ) -> None:
        step_dir = self._model_step_dir(step_name=step_name, attempt_index=attempt_index)
        step_dir.mkdir(parents=True, exist_ok=True)
        output_path = step_dir / PARSER_OUTPUT_FILENAME
        payload = {
            "status": status,
            "output": output,
            "error": error,
        }
        _write_json_payload(output_path, payload)
        step_payload = self._model_step_payload(
            step_name=step_name,
            attempt_index=attempt_index,
        )
        step_payload["parser_output_uri"] = self._relative_uri(output_path)
        step_payload["parser_status"] = status

    def write_debug_trace(
        self,
        *,
        status: str,
        error: dict[str, Any] | None = None,
    ) -> Path:
        self._payload["status"] = status
        self._payload["completed_at"] = _isoformat(self._clock())
        if error is not None:
            self._payload["error"] = error
        _write_json_payload(self.debug_trace_path, self._payload)
        return self.debug_trace_path

    def _model_step_payload(
        self,
        *,
        step_name: str,
        attempt_index: int | None,
    ) -> dict[str, Any]:
        key = _model_step_key(step_name=step_name, attempt_index=attempt_index)
        model_steps = self._payload["model_steps"]
        if key not in model_steps:
            model_steps[key] = {
                "step_name": step_name,
                "attempt_index": attempt_index,
            }
        return model_steps[key]

    def _model_step_dir(self, *, step_name: str, attempt_index: int | None) -> Path:
        if attempt_index is None:
            return self._output_dir / AGENT_TRACES_DIRNAME / step_name
        return (
            self._output_dir
            / AGENT_TRACES_DIRNAME
            / step_name
            / f"attempt_{attempt_index:03d}"
        )

    def _relative_uri(self, path: Path) -> str:
        return path.relative_to(self._workspace_root).as_posix()


@contextmanager
def active_simulator_debug_trace(
    recorder: SimulatorDebugTraceRecorder,
) -> Iterator[None]:
    token = _ACTIVE_RECORDER.set(recorder)
    try:
        yield
    finally:
        _ACTIVE_RECORDER.reset(token)


@contextmanager
def simulator_model_step(
    step_name: str,
    *,
    attempt_index: int | None = None,
) -> Iterator[None]:
    token = _ACTIVE_MODEL_STEP.set(
        _ActiveModelStep(step_name=step_name, attempt_index=attempt_index)
    )
    try:
        yield
    finally:
        _ACTIVE_MODEL_STEP.reset(token)


def current_debug_trace_recorder() -> SimulatorDebugTraceRecorder | None:
    return _ACTIVE_RECORDER.get()


def record_model_raw_output(raw_output: str) -> None:
    recorder = _ACTIVE_RECORDER.get()
    active_step = _ACTIVE_MODEL_STEP.get()
    if recorder is None or active_step is None:
        return
    recorder.write_model_raw_output(
        step_name=active_step.step_name,
        attempt_index=active_step.attempt_index,
        raw_output=raw_output,
    )


def record_parser_success(output: dict[str, Any]) -> None:
    recorder = _ACTIVE_RECORDER.get()
    active_step = _ACTIVE_MODEL_STEP.get()
    if recorder is None or active_step is None:
        return
    recorder.write_parser_output(
        step_name=active_step.step_name,
        attempt_index=active_step.attempt_index,
        status="succeeded",
        output=output,
    )


def record_parser_failure(exc: Exception) -> None:
    recorder = _ACTIVE_RECORDER.get()
    active_step = _ACTIVE_MODEL_STEP.get()
    if recorder is None or active_step is None:
        return
    recorder.write_parser_output(
        step_name=active_step.step_name,
        attempt_index=active_step.attempt_index,
        status="failed",
        error=error_payload(exc),
    )


def question_trace_id_from_request(question_id: str | None) -> str:
    if question_id is not None:
        return validate_safe_id(question_id, "question_id")
    return "question_" + _utc_now().strftime("%Y%m%dT%H%M%S%fZ")


def validate_safe_id(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if not _SAFE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{field_name} must contain only letters, numbers, dots, underscores, or dashes"
        )
    return value


def error_payload(exc: Exception) -> dict[str, str]:
    return {
        "error_type": type(exc).__name__,
        "message": str(exc),
    }


def _model_step_key(*, step_name: str, attempt_index: int | None) -> str:
    if attempt_index is None:
        return step_name
    return f"{step_name}.attempt_{attempt_index:03d}"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _write_json_payload(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
