# V1 graph authoring is Markdown-only and aspect-scoped

> Update: ADR 0059 supersedes this ADR's upload endpoint and request-supplied-scope decisions. The three fixed filesystem-managed sources now load their scopes from versioned metadata; the Markdown-only, evidence-grounded workflow decisions below remain in force.

KnowAct v1 accepts manually prepared UTF-8 Markdown as the only graph-authoring source format. Conversion from the three selected books to Markdown happens outside KnowAct and is not part of the benchmark implementation. The repository therefore has no document parser, conversion service, temporary object-storage transport, or document-format-specific dependency.

Every `POST /api/authoring/graph-candidates` request must identify one uploaded Markdown source and provide a `Graph Authoring Scope`: `aspect_name`, `aspect_description`, one or more `representative_tasks`, optional `excluded_topics`, `target_node_count`, and `max_node_count`. The initial design target is approximately 20 nodes, represented as `target_node_count = 20` and `max_node_count = 24`. The target is not a quota: a run may return fewer nodes when the source does not support 20 representative diagnostic concepts, but it must never exceed the declared maximum.

The scoped authoring path is:

1. deterministically derive and validate Markdown source segments;
2. extract aspect-relevant segment drafts with an exact short `evidence_excerpt`;
3. mechanically verify that each excerpt occurs in the source segment;
4. reconcile, deduplicate, and select a representative graph-wide skeleton set under the node budget;
5. independently verify grounding, scope fit, and diagnostic value, removing candidates that do not satisfy all keep criteria;
6. author L0--L5 diagnostic rubrics for retained nodes;
7. propose precision-first typed edges and run structural graph validation.

Reconciliation preserves draft and segment provenance plus unchanged evidence excerpts. The explicit scope, unverified reconciliation result, independent verification decisions, retained skeletons, model traces, and parser results are stored as candidate-run intermediate artifacts. A segment extraction may make at most three attempts when deterministic local validation rejects only its 12-draft upper bound or exact evidence membership; each attempt is retained in the segment trace. Parse, schema, budget, verifier-contract, rubric, graph-validation, and all semantic errors otherwise fail closed; the workflow does not silently skip a failed segment, fabricate replacement nodes, or let later steps self-approve repairs. Automatic semantic repair remains deferred.

This design uses competency questions to bound the ontology by intended use, evidence-centered design to keep diagnostic claims separate from source claims, staged extract--canonicalize patterns from LLM-based KG construction, and proposer--verifier separation for a precision-oriented candidate set. These foundations motivate the workflow but do not establish that it is the best extractor. A small construction sanity study and expert review are still required before a candidate graph is used in the main benchmark.

This decision replaces the former in-project document-conversion design and supersedes ADR 0052's whole-book extraction budget and ADR 0053's full-source graph scope. The remaining ADR 0052 decisions about deterministic segmentation, provenance, fail-closed validation, and staged rubric/edge authoring continue to apply where they do not conflict with this ADR.

**Considered Options**

- Keep PDF upload and own the conversion/parser infrastructure inside KnowAct.
- Upload manually prepared Markdown but still extract a broad whole-book graph.
- Upload manually prepared Markdown and require an explicit aspect plus representative-task and node-budget contract.

**Consequences**

The runnable chain is smaller, reproducible, and independent of a parser service. Scope and evidence are inspectable, graph size is controlled by usefulness rather than source length, and weak nodes cannot be retained merely to reach 20. The author must prepare Markdown and define representative tasks before a run. The current verifier filters candidates but does not automatically repair them, and neither structural validation nor LLM self-checking replaces independent domain-expert review.
