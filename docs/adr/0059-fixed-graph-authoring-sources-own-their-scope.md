# Fixed graph-authoring sources own their scope

KnowAct graph authoring is a small research workflow over exactly three source configurations: `Economy`, `ISLP`, and `OSTEP`. It is not a general-purpose document-ingestion product. A benchmark author places the prepared UTF-8 Markdown directly under `storage/source_materials/{source_id}/` and maintains a colocated `metadata.json`; the frontend does not upload, edit, or assemble source configuration.

For these sources, `benchmark_domain` must equal `source_id`. The metadata records the Markdown path, size, hash, and citation together with the complete `Graph Authoring Scope`: aspect name and description, domain-specific exclusions, soft target and hard maximum node counts, and at least 50 representative diagnostic questions. It also records the public references used to construct the question bank and identifies the questions as reference-grounded original questions rather than copied exercises.

`GET /api/authoring/source-materials` lists only filesystem entries with valid graph-authoring metadata. `POST /api/authoring/graph-candidates` accepts only `source_id`, optional `run_id`, and request-level `client_provider`; the backend loads and validates every other authoring input from metadata. Legacy request fields such as `benchmark_domain` and `scope` are rejected. The Knowledge Graph workbench exposes only Source, Run ID, and Provider for generation.

The three metadata files are versioned for research reproducibility, while the source Markdown remains local and ignored by Git. Configuration validation fails closed when source/domain identity differs, fewer than 50 representative questions are present, a source reference is invalid, node budgets are inconsistent, or the recorded Markdown hash does not match the local file.

Representative questions may be adapted from the conceptual coverage and task styles of official textbooks, courses, and exercise collections, but are written as original diagnostic prompts. Public reference URLs and scope notes remain in metadata so a reviewer can audit the basis of the bank. The bank bounds graph coverage; it is not itself benchmark evidence, an automatically accepted evaluation set, or a substitute for expert review.

This decision supersedes the upload endpoint and request-supplied-scope parts of ADR 0058. ADR 0058's Markdown-only source format, evidence grounding, staged extraction, fail-closed validation, node-budget semantics, and human-review requirement continue to apply.

**Considered Options**

- Keep a generic frontend product flow with source upload and a long per-run scope form.
- Infer all scope fields afresh from only a source id on every run.
- Keep exactly three filesystem-managed, versioned metadata configurations and expose only run-varying fields.

**Consequences**

Routine runs become shorter and less error-prone, repeated runs use the same auditable research scope, and the question-bank provenance is inspectable. Adding or changing a domain now requires an intentional metadata edit and validation rather than a frontend action. This is a deliberate trade-off for a three-domain research project, not a reusable ingestion platform.
