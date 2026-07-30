# V1 node extraction uses deterministic Markdown segments

> Amended by ADR 0058 for the explicit aspect scope, exact evidence excerpts, and approximately-20-node budget. ADR 0059 replaces the uploaded-source wording with fixed filesystem-managed sources.

Accepted. Graph authoring derives deterministic, non-overlapping `Parsed Source Segments` from one uploaded Markdown source before any model extraction call. Each segment preserves a run-local sequential id, shallow heading path, source locator, character count, and full segment text for replay. Character-based segmentation remains an internal implementation detail; request callers do not tune segment thresholds.

Each segment is processed independently by the `Node Extraction Agent Step`. A segment may return zero drafts, but a parse, schema, locator, or evidence-membership failure stops the entire run rather than silently skipping that segment. Bounded extraction calls may run concurrently, while draft ids, outputs, and traces are assembled in original source order.

Segment drafts are thin source-reading artifacts, not final nodes. They carry name, definition, source locator, grounding note, and one exact evidence excerpt. They must not contain mastery rubrics, graph edges, user states, or ungrounded downstream judgments.

All validated drafts then enter one global `Node Skeleton Reconciliation Agent Step`. It merges duplicates, adjusts obviously unsuitable granularity, selects representative aspect-specific concepts under the declared target and maximum, and records supporting draft ids, supporting segment ids, and unchanged evidence excerpts. Code verifies that every segment id and excerpt belongs to that skeleton's declared supporting drafts. The target is not a quota.

An independent `Node Skeleton Verification Agent Step` runs after reconciliation and before rubric authoring. It emits exactly one keep/remove decision per skeleton based on source support, scope fit, and diagnostic value. Only supported, in-scope, high- or medium-value skeletons continue. The workflow fails if no skeleton survives or if the verifier violates its decision contract.

When artifacts are enabled, the run records segments, drafts, reconciliation provenance, verification decisions, retained skeletons, and per-step raw/parser traces. The only final candidate graph review outputs remain `candidate_nodes.json` and `candidate_edges.json`; intermediate files support audit and debugging but are not evaluation-ready graph data.

**Consequences**

The workflow bounds model context, makes source membership mechanically checkable, and prevents proposer self-approval at the skeleton gate. Non-overlapping segments can still miss concepts that cross boundaries, exact excerpt membership does not prove semantic entailment, and global reconciliation can become a context bottleneck if the domain expands. Those risks require empirical checks or later design changes rather than unsupported implementation claims.
