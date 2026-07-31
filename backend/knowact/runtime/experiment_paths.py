from __future__ import annotations

from pathlib import Path


AGENT_RECONSTRUCTION_EXPERIMENT_DIRECTORY = "03_agent_reconstruction"


def agent_reconstruction_experiment_root(workspace_root: Path) -> Path:
    return (
        workspace_root
        / "experiments"
        / AGENT_RECONSTRUCTION_EXPERIMENT_DIRECTORY
    )


def episode_run_root(workspace_root: Path) -> Path:
    return (
        agent_reconstruction_experiment_root(workspace_root)
        / "results"
        / "runs"
    )


def episode_run_dir(workspace_root: Path, run_id: str) -> Path:
    return episode_run_root(workspace_root) / run_id


def run_queue_state_path(workspace_root: Path) -> Path:
    return (
        agent_reconstruction_experiment_root(workspace_root)
        / "runtime"
        / "run_queue.json"
    )
