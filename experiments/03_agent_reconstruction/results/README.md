# Experiment 03 Results

[中文](README.zh-CN.md)

No confirmatory reconstruction experiment has been run.

The runtime writes one directory per Episode Run:

```text
results/runs/{run_id}/
├── episode_manifest_snapshot.json
├── turns/
├── transcript.json
├── working_map.json
├── agent_tool_trace.json
├── agent_output.json
└── scoring_report.json
```

`checkpoint.json` may exist while a run is resumable and is removed after
successful completion. Generated run directories are ignored by Git.

Future aggregate outputs should separate:

- `analysis/`: reproducible de-identified tables and statistical artifacts;
- `reports/`: paper-ready aggregate reports;
- `raw/` or `private/`: any restricted data that must never be committed.

Do not interpret an empty directory, a passing unit test, or a completed
engineering smoke run as comparative evidence.
