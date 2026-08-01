# KnowAct Experiments

[中文](README.zh-CN.md)

`experiments/` is the canonical home for executable study protocols, study
materials, generated run artifacts, and result reports. Literature reviews and
method evidence remain under `docs/research/`.

## Experiment register

| ID | Experiment | Design | Materials | Results |
| --- | --- | --- | --- | --- |
| 01 | Expert validation of Knowledge Graph scientific validity | Prepared for Economy, ISLP, and OSTEP candidate graphs | Offline HTML + JSON review and confirmation packages prepared | Not run |
| 02 | SAGE Simulator personal fidelity | Simplified protocol and automated flow implemented | Three 80-item atomic bilingual banks with author-side reviews; graph binding, expert review, and pilot pending | Not run |
| 03 | Tested-agent Knowledge Map reconstruction | Prepared | Freeze checklist only | Not run |

## Directory contract

Each experiment contains:

- `design/`: preregistration-oriented questions, hypotheses, protocol, analysis,
  and claim boundaries;
- `materials/`: instruments, question sets, manifests, scripts, and data
  dictionaries used to execute the protocol;
- `results/`: result templates, aggregate analyses, reports, and generated run
  artifacts.

Runtime control state is not a scientific result. Experiment 03 therefore keeps
its queue state under `03_agent_reconstruction/runtime/`, next to but separate
from `results/`.

## Status and evidence rules

An empty template or implemented code path is not an experiment result. Every
experiment README states whether its design, materials, data collection,
analysis, and report are complete.

The three experiments support different claims:

1. Experiment 01 assesses the content validity of a frozen reviewed graph.
2. Experiment 02 currently asks whether Simulator answers represent a
   participant after participant-confirmed Profile and Map review; expert blind
   rating is deferred.
3. Experiment 03 measures how accurately tested agents reconstruct hidden user
   Knowledge Maps under a fixed interaction budget.

Experiment 03 may run before Experiment 02 is complete for engineering smoke
tests. Its scientific conclusion must then be limited to performance against a
synthetic benchmark, not performance against human users.

## Data handling

Do not commit participant identifiers, consent records, raw human responses, or
private Profile Context data. Store them in access-controlled locations named
`private/` or `raw/`; these paths are ignored by Git.

Commit only de-identified aggregate results that satisfy the study consent,
ethics review, and release plan. Model credentials remain in the root `.env`
and must never appear in experiment manifests or reports.

## Generated runtime artifacts

Formal Episode Runs for Experiment 03 are generated under:

```text
experiments/03_agent_reconstruction/results/runs/{run_id}/
```

The persistent queue control file is generated under:

```text
experiments/03_agent_reconstruction/runtime/run_queue.json
```

Private Experiment 02 sessions and Map revision traces are generated under:

```text
experiments/02_simulator_human_validity/results/private/sessions/{session_id}/
experiments/02_simulator_human_validity/results/private/map_reviews/{map_id}.json
```

These paths replace the legacy `experiments/runs/` and
`experiments/runtime/` layout.
