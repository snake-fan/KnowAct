# V1 run-queue scheduling is single-process and file-backed

KnowAct v1 runs one **Episode Run Queue Scheduler** inside the FastAPI application process. It uses one bounded thread pool with at most `8` workers and persists episode execution state, queue state, the global concurrency setting, and **Episode Run Checkpoints** on the local filesystem. On startup it preserves queued work and FIFO positions for automatic scheduling, while episodes left `running` by the interrupted process become `failed` for explicit user-controlled resume.

The global concurrency setting defaults to `3` and accepts values from `3` through `8`. Raising it can dispatch additional queued episodes immediately. Lowering it is non-destructive: already running episodes continue, and the scheduler withholds new dispatch until the active count falls below the new setting.

**Considered Options**

- Let the browser own concurrent single-run requests.
- Introduce Redis plus an external worker system such as Celery for the first queue slice.
- Use one in-process bounded scheduler aligned with the existing local artifact repositories and add distributed infrastructure only when deployment requirements justify it.

**Consequences**

The initial implementation adds no external service dependency and is suitable for the current I/O-bound model-call workload and local research workbench. Dynamic concurrency can tune provider pressure without terminating in-flight research runs. Turn-level checkpoints allow restart recovery within the supported single-process deployment. Running multiple FastAPI worker processes against the same queue state is unsupported because it could double-dispatch episodes; multi-process locking, distributed leases, and external queues are deferred.
