# V1 uses an episode-centric persistent run queue

KnowAct v1 uses a persistent backend **Episode Run Queue**, not a user-facing or backend **Episode Run Batch** resource. The new runtime workbench loads registered **Evaluation Episodes** as rows. A benchmark author selects eligible rows and submits one enqueue command; the backend loads each episode's immutable execution configuration, changes each selected episode to `queued`, and executes queued episodes with bounded parallelism.

Each current-schema registered episode exposes exactly one **Episode Execution Status**: `ready`, `queued`, `running`, `completed`, `failed`, or `cancelled`. Only `ready`, `failed`, and `cancelled` episodes are selectable. `queued` and `running` episodes already have active work, while a successfully scored `completed` episode is permanently locked. Repeating the same setup requires registering a new `episode_id`. Legacy manifests without immutable execution configuration are excluded from this state model and from the queue.

Failed and cancelled episodes may be enqueued again to resume the same Episode Run identity from its latest valid checkpoint. They retain the same run id and run-artifact directory rather than creating another attempt. One enqueue command requires unique episode ids and schedules each selected episode once. It carries episode identities only because every registered episode already owns immutable execution configuration under ADR-0057.

One enqueue command may mix `ready`, `failed`, and `cancelled` episodes. Each uses the immutable configuration selected during Episode Manifest Registration, including when an invalid checkpoint requires explicit restart. `Run Queue` has no agent/provider/temperature form; it distinguishes new, resumed, and restart-required selections by status and checkpoint health only.

Enqueue admission is per episode rather than atomic across the selection. Status-ineligible episodes have no checkbox in the UI. For the selected eligible rows, valid episodes enter the queue even if another selected episode is rejected; the API returns an accepted or rejected outcome for every selection. A resumable episode with a missing or malformed checkpoint is rejected alone, remains `failed` with `checkpoint_invalid`, and does not block the others.

A checkpoint-invalid row offers an explicit **Episode Run Restart** path. When the benchmark author selects and confirms restart, the runtime preserves the old run directory, assigns a new run id to the same registered episode, writes a fresh initial checkpoint, and enqueues it from the beginning. It never silently overwrites corrupt resume state. This exception does not make successfully completed episodes rerunnable.

Failure is isolated per episode and does not stop other queued or running episodes. Cancellation is also episode-specific: queued work cancels immediately, while running work stops cooperatively after its current completed-turn checkpoint without force-killing an in-flight provider call. A completed episode displays its independent Episode Run result; the initial design does not create batch history, batch reports, or cross-episode score aggregation.

The initial workbench exposes a `Cancel` action on each `queued` or `running` row. It does not provide cancel-all or selection-wide cancellation. A cancelled episode becomes selectable again and joins the FIFO tail when re-enqueued.

Parallelism is controlled by one persisted global queue-concurrency setting, defaulting to `3` with an allowed range of `3` through `8`. Raising the value may dispatch more queued episodes immediately. Lowering it never cancels already running episodes; the scheduler pauses new dispatch until the active count naturally falls below the new limit.

Queue ordering is stable FIFO by enqueue time. Episodes selected in one enqueue command enter in their current workbench-list order. Re-enqueued `failed` or `cancelled` episodes join the tail, and backend restart restores the persisted order without reprioritization.

The frontend polls episode execution state approximately every two seconds while any episode is queued or running. Refreshing the page reloads persisted episode state. WebSockets and server-sent events are deferred because progress changes only at queue and completed-turn boundaries.

The queue workbench uses an episode-list/detail layout. Its left side shows a checkbox when the episode is eligible, the episode id, execution status, and queue position or completed-turn progress. Its right side shows one selected episode: completed episodes reuse the existing score, visible transcript, per-node comparison, and artifact views; running episodes show run id plus turn and resume progress; failed episodes show a safe structured error; other states show manifest and reviewed-artifact binding.

The new frontend module is named `Run Queue` and is the only formal Episode Run entry point. The existing `Episodes` module retains manifest registration, immutable execution-configuration authoring, episode listing, and reviewed-artifact binding inspection but removes its single-run controls. Runtime navigation orders these modules as `Simulator`, `Episodes`, then `Run Queue`.

**Considered Options**

- Let the frontend issue concurrent single-run requests and retain state only in browser memory.
- Create persistent Episode Run Batch resources and present or hide their batch membership.
- Persist one backend run queue while keeping lifecycle and results episode-centric.

**Consequences**

The UI matches the benchmark author's mental model: select episodes, enqueue them, and inspect one status and result per episode. Queue persistence and bounded scheduling improve throughput and survive page refreshes without adding batch identities or batch reports. Completed episodes are unambiguous one-shot experiment units, but repeated trials require new episode registrations. Failed and cancelled episodes normally preserve work by resuming the same checkpointed run. Per-episode admission preserves throughput when one selected row is invalid, while explicit restart provides a safe escape hatch for corrupt checkpoint state without overwriting the failed run's artifacts.
