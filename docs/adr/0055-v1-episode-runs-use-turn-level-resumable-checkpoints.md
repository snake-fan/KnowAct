# V1 Episode Runs use turn-level resumable checkpoints

KnowAct v1 persists a temporary **Episode Run Checkpoint** after every completed **Interaction Turn**. A completed turn contains one visible diagnostic question and simulator answer followed by the tested agent's accepted or exhausted working-map update. The checkpoint records the visible dialogue context, current working map, next decision phase, remaining diagnostic turns, and trace progress needed to continue the same Episode Run identity.

The runtime also writes an initial checkpoint after reserving the run id and directory but before any provider call. It contains the initial working map, empty visible dialogue, initial decision phase, full turn budget, and run configuration, so a failure during the first turn remains resumable from the beginning of that same run.

The initial checkpoint copies the immutable **Episode Execution Configuration** from the registered episode: `agent_kind`, `tested_agent_client_provider`, `tested_agent_model`, `simulator_client_provider`, `simulator_model`, `tested_agent_temperature`, and `max_tool_retries`. Resume validation requires those values to match the episode manifest. Resuming, and explicit restart after checkpoint failure, cannot switch models or parameters; a different configuration requires a newly registered episode.

The runtime writes the durable per-turn artifact and current working map before atomically replacing the checkpoint, so the latest valid checkpoint is authoritative for resumable progress. If a crash leaves a turn, working-map, or trace file ahead of that checkpoint, the file is uncommitted and must be ignored or deterministically replaced when the turn replays. After backend interruption, startup reconciliation marks any episode left `running` as `failed`; it does not automatically resume. When the benchmark author selects that failed episode again, the queue scheduler resumes the same `run_id` from the latest valid checkpoint. User-cancelled episodes follow the same manual resume path.

If interruption occurs after a turn starts but before its checkpoint commits, the runtime discards that turn's transient state and re-executes the whole turn from the previous checkpoint. External model calls therefore have at-least-once execution semantics and may be repeated after a narrowly timed interruption. KnowAct does not claim exactly-once behavior across provider calls.

If a resumable failed or cancelled episode has a missing or malformed checkpoint, normal enqueueing rejects that episode alone and leaves it `failed` with `checkpoint_invalid`. The runtime must not silently overwrite its existing run directory. The benchmark author may explicitly choose **Episode Run Restart**, which preserves the old run artifacts, assigns a new run id to the same registered episode, and creates a fresh initial checkpoint. Successfully completed episodes remain non-rerunnable.

**Considered Options**

- Treat every backend interruption as a terminal episode failure and require a new run identity.
- Persist only episode status and restart an interrupted Episode Run from its first turn.
- Persist turn-level Episode Run checkpoints and resume the same run from the last completed turn.

**Consequences**

Long multi-turn runs can survive backend restarts without discarding completed turns, including failures before the first turn completes. Recovery is explicit rather than automatic: interrupted and cancelled episodes remain selectable and resume the same run when re-enqueued. The runner must separate resumable state from terminal artifacts and define a stable resume entry point. A narrowly timed interruption may repeat one turn's external model calls, but partial dialogue or working-map updates never become committed progress. Corrupt resume state is surfaced and requires an explicit new-run restart instead of silent replacement. After successful finalization and scoring, the runtime removes only resume-specific checkpoint and scheduling state. Formal run artifacts remain durable: per-turn records, transcript, working map, agent tool trace, agent output, and scoring report.
