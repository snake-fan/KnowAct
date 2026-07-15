from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.knowact.agents.protocol import DecisionPhase
from backend.knowact.agents.working_map import AgentWorkingKnowledgeMap
from backend.knowact.core.episode import EpisodeExecutionConfiguration
from backend.knowact.core.interaction import VisibleDialogueContext


CHECKPOINT_FILENAME = "checkpoint.json"
_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class EpisodeRunCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = 1
    run_id: str
    episode_id: str
    execution_configuration: EpisodeExecutionConfiguration
    visible_dialogue_context: VisibleDialogueContext
    working_map: AgentWorkingKnowledgeMap
    phase: DecisionPhase
    remaining_turns: int = Field(ge=0)
    completed_turns: int = Field(ge=0)
    trace: tuple[dict[str, Any], ...] = ()
    updated_at: str


class EpisodeRunCheckpointError(ValueError):
    """Base error for unusable resumable Episode Run state."""


class EpisodeRunCheckpointMissingError(EpisodeRunCheckpointError):
    """Raised when a resumable run has no checkpoint."""


class EpisodeRunCheckpointInvalidError(EpisodeRunCheckpointError):
    """Raised when a checkpoint cannot be parsed or does not match its episode."""


class EpisodeRunCheckpointRepository:
    def __init__(self, *, workspace_root: Path) -> None:
        self._workspace_root = workspace_root

    def initial_checkpoint(
        self,
        *,
        run_id: str,
        episode_id: str,
        execution_configuration: EpisodeExecutionConfiguration,
        working_map: AgentWorkingKnowledgeMap,
        max_turns: int,
    ) -> EpisodeRunCheckpoint:
        return EpisodeRunCheckpoint(
            run_id=_safe_id(run_id, "run_id"),
            episode_id=_safe_id(episode_id, "episode_id"),
            execution_configuration=execution_configuration,
            visible_dialogue_context=VisibleDialogueContext(),
            working_map=working_map,
            phase=DecisionPhase.INITIAL_QUESTION,
            remaining_turns=max_turns,
            completed_turns=0,
            trace=(),
            updated_at=_timestamp(),
        )

    def write(self, checkpoint: EpisodeRunCheckpoint) -> None:
        path = self.path(checkpoint.run_id)
        if not path.parent.is_dir():
            raise EpisodeRunCheckpointInvalidError(
                f"Episode Run directory {checkpoint.run_id} does not exist"
            )
        _write_json(path, checkpoint.model_dump(mode="json", exclude_none=True))

    def read(self, run_id: str) -> EpisodeRunCheckpoint:
        path = self.path(run_id)
        if not path.is_file():
            raise EpisodeRunCheckpointMissingError(
                f"Episode Run {run_id} checkpoint does not exist"
            )
        try:
            with path.open(encoding="utf-8") as handle:
                return EpisodeRunCheckpoint.model_validate(json.load(handle))
        except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise EpisodeRunCheckpointInvalidError(
                f"Episode Run {run_id} checkpoint is malformed"
            ) from exc

    def read_validated(
        self,
        *,
        run_id: str,
        episode_id: str,
        execution_configuration: EpisodeExecutionConfiguration,
    ) -> EpisodeRunCheckpoint:
        checkpoint = self.read(run_id)
        if checkpoint.run_id != run_id or checkpoint.episode_id != episode_id:
            raise EpisodeRunCheckpointInvalidError(
                "Episode Run checkpoint identity does not match queue state"
            )
        if checkpoint.execution_configuration != execution_configuration:
            raise EpisodeRunCheckpointInvalidError(
                "Episode Run checkpoint execution configuration does not match manifest"
            )
        if checkpoint.completed_turns != len(
            checkpoint.visible_dialogue_context.turns
        ):
            raise EpisodeRunCheckpointInvalidError(
                "Episode Run checkpoint progress is inconsistent"
            )
        return checkpoint

    def delete(self, run_id: str) -> None:
        path = self.path(run_id)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise EpisodeRunCheckpointInvalidError(
                f"Episode Run {run_id} checkpoint could not be removed"
            ) from exc

    def path(self, run_id: str) -> Path:
        return (
            self._workspace_root
            / "experiments"
            / "runs"
            / _safe_id(run_id, "run_id")
            / CHECKPOINT_FILENAME
        )


def advanced_checkpoint(
    checkpoint: EpisodeRunCheckpoint,
    *,
    visible_dialogue_context: VisibleDialogueContext,
    working_map: AgentWorkingKnowledgeMap,
    phase: DecisionPhase,
    remaining_turns: int,
    trace: list[dict[str, Any]],
) -> EpisodeRunCheckpoint:
    return checkpoint.model_copy(
        update={
            "visible_dialogue_context": visible_dialogue_context,
            "working_map": working_map,
            "phase": phase,
            "remaining_turns": remaining_turns,
            "completed_turns": len(visible_dialogue_context.turns),
            "trace": tuple(trace),
            "updated_at": _timestamp(),
        }
    )


def _write_json(path: Path, payload: Any) -> None:
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        temporary_path.replace(path)
    except OSError as exc:
        raise EpisodeRunCheckpointInvalidError(
            f"Episode Run checkpoint {path.name} could not be written"
        ) from exc


def _safe_id(value: str, field_name: str) -> str:
    if not value.strip() or not _SAFE_ID_PATTERN.fullmatch(value):
        raise EpisodeRunCheckpointInvalidError(f"Unsafe {field_name}")
    return value


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()
