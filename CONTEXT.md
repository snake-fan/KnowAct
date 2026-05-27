# KnowAct Domain Context

KnowAct studies whether an agent can infer and use a user's knowledge state during knowledge-grounded interaction.

## Language

**Knowledge Node**:
A user-independent knowledge unit that is stable, diagnosable, and suitable for concept-level evaluation.
_Avoid_: node state, user node

**Authoritative Source**:
A selected textbook, course material, paper, or reference used as the source basis for graph authoring.
_Avoid_: general knowledge, model memory, unsourced topic list

**Source Material Catalog**:
An authoring-only registry that gives uploaded or local source materials stable identities and storage paths.
_Avoid_: benchmark graph manifest, reviewed graph data, book-only library

**Parsed Source Markdown**:
A Markdown representation of an **Authoritative Source** used as source material during graph authoring.
_Avoid_: PDF input_file, OpenAI file_id, raw PDF prompt payload

**Source Locator**:
A minimal structured reference that identifies where a **Knowledge Node** is mentioned in an **Authoritative Source**.
_Avoid_: vague source label, invented citation, generic textbook reference, required quote span

**Source Grounding Note**:
A concise, paraphrased, source-grounded note extracted for a **Source-Grounded Node Skeleton** so later graph-authoring steps can use structured source evidence without reading full **Parsed Source Markdown**.
_Avoid_: full source excerpt, hidden chain-of-thought, unsourced model memory, long copied passage

**Source-Grounded Candidate Node**:
A draft **Knowledge Node** extracted from an **Authoritative Source** with a **Source Locator**.
_Avoid_: brainstormed node, common-sense topic, unsourced candidate

**Graph Authoring Run Log**:
A structured sidecar record of one **Graph Authoring Agent Workflow** run, capturing source metadata, step status, validation checkpoints, counts, artifact paths, redacted agent-step model outputs, parser results, and failure metadata for authoring debug.
_Avoid_: candidate graph artifact, prompt log, full source-material text, reviewed graph

**User Knowledge State**:
A user-specific state describing how a particular user appears to understand a **Knowledge Node**.
_Avoid_: node state, node

**Evidence**:
A traceable basis for judging a user's knowledge of a **Knowledge Node**.
_Avoid_: edge evidence, edge state, hidden rationale

**Evidence Record**:
A structured instance of **Evidence** with explicit type, kind, visibility, node reference, and diagnostic signal.
_Avoid_: separate evidence schema, freeform rationale, hidden chain-of-thought

**Evidence Type**:
The role or origin category of a piece of **Evidence**.
_Avoid_: evidence format, evidence source, evidence visibility

**Evidence Kind**:
The observable diagnostic form of a piece of **Evidence**, such as prior answer, worked example, self-report, misconception trace, or background fact.
_Avoid_: evidence type, evidence visibility, hidden rationale

**Evidence Visibility**:
The access boundary that determines which benchmark participant can use a piece of **Evidence**.
_Avoid_: evidence type, evidence source, prompt section

**Ground-Truth Evidence**:
The hidden **Evidence** used to justify a **User Knowledge State** in a **Ground-Truth Knowledge Map**.
_Avoid_: freeform profile note, simulator rationale, real user data

**Interaction Observation**:
Evidence produced from a visible turn in an **Evaluation Episode**.
_Avoid_: hidden evidence, profile evidence, simulator rationale

**Synthetic Evidence**:
Generated **Evidence** used as simulated support for a benchmark user's **User Knowledge State**.
_Avoid_: real observation, human data, arbitrary rationale

**Knowledge Graph**:
The user-independent domain structure made of **Knowledge Nodes** and **Knowledge Edges**.
_Avoid_: user knowledge map, user profile

**Knowledge Map**:
A user-specific or agent-reconstructed view of knowledge state over a **Knowledge Graph**.
_Avoid_: domain graph, authored graph

**Ground-Truth Knowledge Map**:
The hidden **Knowledge Map** used as the benchmark reference for a simulated or real user.
_Avoid_: user graph, true graph, ground-truth graph

**Candidate Knowledge Map**:
A draft user-specific **Knowledge Map** produced during authoring before benchmark-author review.
_Avoid_: ground-truth map, final profile, evaluation reference

**Profile Context**:
User persona, background, preferences, or task goals used to make a simulated user coherent.
_Avoid_: scored profile, knowledge map, freeform ground truth

**Reconstructed Knowledge Map**:
The **Knowledge Map** inferred by the tested agent through interaction.
_Avoid_: generated user graph, inferred graph structure, reconstructed knowledge graph

**Final Reconstructed Knowledge Map**:
The required **Reconstructed Knowledge Map** submitted by the **Tested Agent** after an **Evaluation Episode** ends.
_Avoid_: per-turn snapshot, intermediate belief state, trace

**Reconstruction Trace**:
Optional per-turn snapshots or notes showing how the **Tested Agent** updated its inferred **Knowledge Map**.
_Avoid_: required scoring output, final map, hidden rationale

**Evaluation Episode**:
A bounded interaction in which a tested agent tries to infer one user's **Ground-Truth Knowledge Map**.
_Avoid_: learning session, tutoring session, conversation

**Evaluation Episode Manifest**:
The configuration record that binds an **Evaluation Episode** to its graph, hidden map, profile context, turn budget, interaction rules, and scoring profile.
_Avoid_: loose runner args, experiment notes, prompt metadata

**Benchmark Domain**:
The subject area covered by a v1 authored graph and its evaluation episodes.
_Avoid_: multi-domain suite, unrelated topic mix, general knowledge

**Classical Supervised ML Algorithms Domain**:
The v1 **Benchmark Domain** covering classical supervised machine learning algorithms and their core evaluation concepts.
_Avoid_: deep learning, reinforcement learning, unsupervised learning, all machine learning

**V1 Graph Size Target**:
The target size of 30-50 **Knowledge Nodes** for the first v1 authored graph.
_Avoid_: toy graph, full curriculum, unbounded graph

**Episode Knowledge Graph**:
The **Authored Knowledge Graph** used as the domain structure for one **Evaluation Episode**.
_Avoid_: target node set, scoring subset, context-only graph

**Map Coverage Requirement**:
The requirement that a **Knowledge Map** account for every **Knowledge Node** in the **Episode Knowledge Graph**.
_Avoid_: partial map, sampled nodes, scoring subset

**Turn Budget**:
The explicitly configured maximum number of interaction turns allowed in an **Evaluation Episode**.
_Avoid_: graph-derived budget, unlimited conversation, implicit budget

**Interaction Turn**:
One tested-agent diagnostic question followed by one user simulator answer.
_Avoid_: multi-question batch, compound questionnaire, free chat segment

**Diagnostic Question**:
A question asked by the **Tested Agent** to gather evidence about a user's **User Knowledge State**.
_Avoid_: teaching prompt, explanation, recommendation

**Structured Map Comparison**:
An automatic comparison between a **Ground-Truth Knowledge Map** and a **Reconstructed Knowledge Map** over quantifiable user-state fields.
_Avoid_: LLM judge, subjective profile review, evaluator agent

**Scoring Profile**:
The fixed scoring configuration used to compute **Episode Mastery Distance** and supporting metrics.
_Avoid_: per-episode scoring override, evaluator prompt, custom metric bundle

**Mastery Level Distance**:
The distance assigned by the **Mastery Distance Function** between predicted and ground-truth mastery levels for the same **Knowledge Node**.
_Avoid_: subjective similarity, LLM-judged closeness, graph distance

**Episode Mastery Distance**:
The mean **Mastery Level Distance** across all **Knowledge Nodes** in an **Episode Knowledge Graph**.
_Avoid_: accuracy, reward, subjective score

**Mastery Distance Function**:
The explicit scoring function that maps two mastery levels to a non-negative **Mastery Level Distance**.
_Avoid_: linear penalty, LLM judge, subjective similarity

**Exact Mastery Bonus**:
An optional reward applied when **Mastery Level Distance** is zero.
_Avoid_: primary exact-match metric, separate evaluator score

**Missing Prediction**:
A scored **Knowledge Node** for which the **Reconstructed Knowledge Map** provides no **User Knowledge State**.
_Avoid_: L0, unknown mastery, unsupported inference

**Unsupported Inference**:
A predicted **User Knowledge State** that lacks a tested-agent-visible **Evidence Record** reference.
_Avoid_: missing prediction, wrong prediction, hidden rationale

**Active Knowledge-State Diagnosis**:
An interaction task where the tested agent asks diagnostic questions to infer a user's **Knowledge Map**.
_Avoid_: teaching, tutoring, general chat

**Static User Knowledge State**:
The assumption that a user's **User Knowledge State** does not change during an **Evaluation Episode**.
_Avoid_: learned state, updated user knowledge

**Tested Agent**:
The agent evaluated by trying to infer a **Reconstructed Knowledge Map** through an **Evaluation Episode**.
_Avoid_: user simulator, benchmark author, evaluator

**Fixed-Question Baseline**:
A baseline that asks diagnostic questions in a predefined order without adapting to user answers.
_Avoid_: adaptive agent, random baseline, oracle baseline

**Random-Question Baseline**:
A baseline that selects diagnostic questions randomly within the episode constraints.
_Avoid_: adaptive agent, fixed questionnaire, oracle baseline

**Simple LLM Agent**:
A baseline **Tested Agent** that uses the visible graph and dialogue history with a simple prompt to choose diagnostic questions and produce a final map.
_Avoid_: ToM architecture, oracle agent, teaching agent

**User Simulator**:
The actor that answers **Diagnostic Questions** according to a hidden **Ground-Truth Knowledge Map** and hidden evidence.
_Avoid_: evaluator, data-table oracle, tested agent

**Simulator Answer Ambiguity**:
Natural uncertainty, partial correctness, hesitation, or misconception in a **User Simulator** answer.
_Avoid_: random behavior, evasive answer, state drift

**Visibility Boundary**:
The boundary between benchmark data visible to the **Tested Agent** and benchmark reference data hidden from it.
_Avoid_: prompt setup, context window contents, hidden prompt

**Knowledge Edge**:
A user-independent relationship from one **Knowledge Node** to another within the domain knowledge structure.
_Avoid_: user edge, user relation

**Knowledge Edge Identity**:
A stable identifier for a **Knowledge Edge** that allows graph operations, diffing, and scoring to refer to the same domain relationship.
_Avoid_: ad hoc edge reference, implicit tuple reference

**Part-Of Knowledge Edge**:
A **Knowledge Edge** where the source **Knowledge Node** is a structural component of the target **Knowledge Node**.
_Avoid_: topic membership, category membership

**Prerequisite-For Knowledge Edge**:
A **Knowledge Edge** where absence of the source **Knowledge Node** predictably blocks or weakens higher-level understanding of the target **Knowledge Node**.
_Avoid_: strict necessary condition, absolute gate

**Supports Knowledge Edge**:
A **Knowledge Edge** where the source **Knowledge Node** improves explanation, transfer, or diagnostic confidence for the target **Knowledge Node** without being a prerequisite.
_Avoid_: weak prerequisite, generic relatedness

**Contrasts-With Knowledge Edge**:
A symmetric **Knowledge Edge** where two **Knowledge Nodes** are commonly understood by comparing their boundaries, failure modes, or mutually clarifying differences.
_Avoid_: opposite, mutually exclusive concept

**Knowledge Edge Rationale**:
A concise explanation of why a **Knowledge Edge** is a valid domain relationship.
_Avoid_: user evidence, interaction observation

**Curation Confidence**:
The confidence value on a **Knowledge Edge** indicating how likely the edge is to be a valid domain relationship; agent-authored candidates may carry an initial suggested value, and reviewed authored edges carry the benchmark author's accepted value.
_Avoid_: user confidence, mastery confidence

**Knowledge Edge Weight**:
The authored strength of the relationship represented by a **Knowledge Edge**.
_Avoid_: curation confidence, user confidence

**Effective Relationship Strength**:
A derived relationship score computed from **Knowledge Edge Weight** and **Curation Confidence**.
_Avoid_: authored edge field, stored strength

**Knowledge Edge Type**:
One of the canonical relationship kinds allowed for a **Knowledge Edge**.
_Avoid_: related_to, used_for, freeform relation

**Authored Knowledge Graph**:
The authoritative domain graph containing only explicitly curated **Knowledge Nodes** and **Knowledge Edges**.
_Avoid_: inferred graph, expanded graph

**Authored Graph Data Files**:
The reviewed node and edge JSON list files that store an **Authored Knowledge Graph** as separate data files.
_Avoid_: combined graph blob, manifest-only graph, candidate files

**Graph Manifest**:
An optional metadata file that can name a graph version and reference its separate authored node and edge files.
_Avoid_: combined node/edge storage, scoring override, source of node contents

**Graph File Layout**:
The repository or dataset directory structure used to place graph data files.
_Avoid_: v1 schema requirement, implicit domain versioning, hardcoded path convention

**Candidate Knowledge Graph**:
A draft graph produced during authoring before benchmark-author review.
_Avoid_: authored graph, evaluation graph, benchmark ground truth

**Candidate Graph Review Workbench**:
A research workbench surface where a benchmark author reviews, visualizes, and edits a **Candidate Knowledge Graph** before any promotion decision.
_Avoid_: automatic graph promotion, evaluation runtime, graph scoring UI

**Candidate Node Inventory**:
The source-grounded list of candidate **Knowledge Nodes** considered during graph authoring.
_Avoid_: brainstormed topic list, final graph, unsourced curriculum outline

**Source-Grounded Node Skeleton**:
A partial **Knowledge Node** draft containing the source-grounded concept identity, source locator, and concise **Source Grounding Notes** before diagnostic rubrics are authored.
_Avoid_: final node, complete rubric, unsourced topic

**Graph Authoring Pipeline**:
The workflow that produces and reviews a **Candidate Knowledge Graph** before it becomes an **Authored Knowledge Graph**.
_Avoid_: evaluation runtime, tested agent loop, scoring pipeline

**Graph Authoring Agent Workflow**:
The single agent workflow that accelerates graph authoring by extracting source-grounded node skeletons, authoring node rubrics, and proposing edges for review, then outputs node and edge JSON list files.
_Avoid_: manual-only inventory, evaluation runtime, automatic authored graph

**Graph Authoring Intermediate Artifacts**:
Structured per-run artifacts produced between **Graph Authoring Agent Workflow** steps so later steps can consume prior workflow results without re-reading full **Parsed Source Markdown**.
_Avoid_: final graph authoring output files, reviewed graph data, freeform log text, full source-material copy

**Graph Authoring Output Files**:
The two JSON list files produced by the **Graph Authoring Agent Workflow** for benchmark-author review: one node list and one edge list.
_Avoid_: single review artifact, validation report as final output, embedded candidate status

**Graph Authoring Edge List**:
The graph-authoring output file containing plain **Knowledge Edge** objects that connect two **Knowledge Nodes**.
_Avoid_: node rubric duplicate, textbook source list, user-state relation

**Node Extraction Agent Step**:
The step in the **Graph Authoring Agent Workflow** that reads **Authoritative Sources** and extracts **Source-Grounded Node Skeletons** with **Source Locators**.
_Avoid_: separate workflow, manual brainstorm, final authored graph

**Node Rubric Authoring Agent Step**:
The step in the **Graph Authoring Agent Workflow** that turns **Source-Grounded Node Skeletons** into complete candidate **Knowledge Nodes** with diagnostic goals and L0-L5 rubrics.
_Avoid_: source extraction, edge proposal, user map generation

**Node Rubric Input Scope**:
The allowed context for v1 node rubric authoring: **Source-Grounded Node Skeletons**, their **Source Locators**, their **Source Grounding Notes**, and the global **MasteryScale**.
_Avoid_: full Parsed Source Markdown, source-material text parameter, unreviewed neighboring nodes, candidate edges, graph traversal context, profile context

**Edge Proposal Agent Step**:
The step in the **Graph Authoring Agent Workflow** that proposes candidate **Knowledge Edges** after candidate nodes are available.
_Avoid_: separate workflow, final authored graph, automatic edge acceptance

**Edge Proposal Input Scope**:
The allowed context for v1 edge proposal: complete candidate **Knowledge Nodes**, including node rubrics, source locators, and **Source Grounding Notes**, plus workflow-produced source-grounded intermediate information.
_Avoid_: full Parsed Source Markdown, source-material text parameter, hidden user maps, profile context, scoring results, automatic edge acceptance

**Precision-First Edge Proposal**:
The v1 edge proposal policy that prefers fewer, clearer candidate **Knowledge Edges** over broad recall of weakly related node pairs.
_Avoid_: broad relatedness harvesting, speculative edge dump, recall-first edge list

**Candidate Edge Confidence Threshold**:
A numeric cutoff that would decide whether a candidate **Knowledge Edge** is allowed into `candidate_edges.json` based on `curation_confidence`.
_Avoid_: v1 inclusion rule, replacement for rationale review, hidden filtering rule

**Map Authoring Pipeline**:
The workflow that produces and reviews a **Candidate Knowledge Map** before it becomes a **Ground-Truth Knowledge Map**.
_Avoid_: evaluation runtime, tested agent reconstruction, simulator answer generation

**Derived Knowledge Relationship**:
A non-authoritative relationship inferred from traversal or reasoning over the **Authored Knowledge Graph**.
_Avoid_: ground-truth edge, authored edge

## Relationships

- A **Knowledge Node** exists independently of any user.
- A v1 **Knowledge Node** should be grounded in an **Authoritative Source** through a **Source Locator**.
- A **Source Material Catalog** identifies available authoring inputs; it is not itself reviewed benchmark graph data.
- A v1 **Source Locator** only needs to point to where the concept is mentioned, such as chapter, section, pages, URL, lecture, slide, paragraph, or reference entry.
- A v1 **Source Locator** does not require quoted text, evidence spans, exact text offsets, or paragraph-level precision when coarser location is enough for review.
- A **Candidate Node Inventory** contains **Source-Grounded Candidate Nodes**, not brainstormed topics.
- A **Source-Grounded Node Skeleton** is not a complete **Knowledge Node** because it lacks node-specific diagnostic rubrics.
- A **Source-Grounded Node Skeleton** should include stable identity fields such as `id`, `name`, `type`, `definition`, and `source`.
- **Knowledge Nodes** do not belong to built-in hierarchy levels.
- A **Knowledge Graph** contains user-independent **Knowledge Nodes** and **Knowledge Edges**.
- A **Knowledge Map** represents user-specific or reconstructed knowledge state over a **Knowledge Graph**.
- A **Candidate Knowledge Map** must be reviewed before it becomes a **Ground-Truth Knowledge Map**.
- **Profile Context** may guide generation of a **Candidate Knowledge Map**.
- **Profile Context** should be consistent with the **Ground-Truth Knowledge Map** but is not part of **Episode Mastery Distance**.
- A v1 **Evaluation Episode** should be declared by an **Evaluation Episode Manifest**.
- An **Evaluation Episode Manifest** references the **Episode Knowledge Graph**, **Ground-Truth Knowledge Map**, optional **Profile Context**, **Turn Budget**, interaction rules, and scoring profile.
- V1 uses one fixed **Scoring Profile**, `squared_mastery_distance_v1`.
- An **Evaluation Episode Manifest** may reference the v1 **Scoring Profile** but must not override it.
- V1 targets one **Benchmark Domain** before multi-domain expansion.
- The first v1 **Benchmark Domain** is **Classical Supervised ML Algorithms Domain**.
- The primary v1 **Authoritative Source** is *An Introduction to Statistical Learning with Applications in Python*.
- The first v1 graph should contain enough **Knowledge Nodes** to distinguish different user knowledge structures.
- The first v1 graph targets 30-50 **Knowledge Nodes**.
- A **Ground-Truth Knowledge Map** and a **Reconstructed Knowledge Map** are compared over the same **Authored Knowledge Graph** in v1.
- In v1, each **User Knowledge State** in a **Reconstructed Knowledge Map** should be backed by one or more tested-agent-visible **Evidence Records**.
- V1 scoring uses the **Final Reconstructed Knowledge Map**.
- A **Reconstruction Trace** is optional and not required for primary v1 scoring.
- V1 scoring uses **Structured Map Comparison** rather than a separate evaluator agent.
- **Structured Map Comparison** focuses on quantifiable **User Knowledge State** fields such as mastery level and confidence.
- **Mastery Level Distance** is the primary v1 comparison signal for mastery-level scoring.
- **Episode Mastery Distance** is the primary v1 episode-level result and lower is better.
- The v1 **Mastery Distance Function** maps L0-L5 to scores 0-5 and uses squared score distance.
- **Exact Mastery Bonus** may be derived from zero **Mastery Level Distance**.
- In v1, **Structured Map Comparison** scores every **Knowledge Node** in the **Episode Knowledge Graph**.
- In v1, the **Ground-Truth Knowledge Map** must satisfy the **Map Coverage Requirement**.
- In v1, the **Final Reconstructed Knowledge Map** should satisfy the **Map Coverage Requirement**; missing nodes are handled as **Missing Predictions**.
- A v1 **Evaluation Episode** has an explicit **Turn Budget**.
- The v1 **Turn Budget** is not derived from the number of **Knowledge Nodes** in the **Episode Knowledge Graph**.
- A v1 **Interaction Turn** contains one primary **Diagnostic Question**.
- The user simulator answers only the primary **Diagnostic Question** in an **Interaction Turn**.
- The **User Simulator** uses hidden map and evidence to generate natural answers, not structured benchmark labels.
- The **User Simulator** must not directly reveal mastery labels, hidden evidence ids, or the full **Ground-Truth Knowledge Map**.
- **Simulator Answer Ambiguity** is allowed when it is consistent with the hidden map and evidence.
- **Simulator Answer Ambiguity** must not change the user's hidden mastery state or evade all diagnosis.
- A **Missing Prediction** receives the maximum penalty defined by the **Mastery Distance Function**.
- The v1 **Missing Prediction** distance penalty is 36.
- A **Missing Prediction** must not be treated as L0 because L0 is a real **User Knowledge State**.
- An **Unsupported Inference** does not override **Mastery Level Distance** in v1.
- **Unsupported Inference** is reported as a separate diagnostic or penalty metric.
- V1 baselines are **Fixed-Question Baseline**, **Random-Question Baseline**, and **Simple LLM Agent**.
- Oracle, passive summarization, teaching, and complex ToM architectures are outside the v1 baseline set.
- `userstate` belongs to a **Knowledge Map**, not to the **Knowledge Graph**.
- `userstate` describes a user's knowledge of **Knowledge Nodes**, not **Knowledge Edges**.
- A v1 **Evaluation Episode** measures **Active Knowledge-State Diagnosis**, not teaching or tutoring.
- **Static User Knowledge State** means the **Ground-Truth Knowledge Map** remains fixed throughout a v1 **Evaluation Episode**.
- In v1, the **Visibility Boundary** allows the **Tested Agent** to see the **Authored Knowledge Graph**.
- In v1, the **Visibility Boundary** hides the **Ground-Truth Knowledge Map** from the **Tested Agent**.
- A **Knowledge Edge** exists independently of any user.
- A **Knowledge Edge Identity** refers to a stable domain relationship, not a user's inferred relationship.
- A **Knowledge Edge** connects two **Knowledge Nodes**.
- KnowAct uses `part_of`, `prerequisite_for`, `supports`, and `contrasts_with` as its canonical **Knowledge Edge Types**.
- For directed **Knowledge Edges**, the source **Knowledge Node** provides the structural or cognitive contribution and the target **Knowledge Node** receives it.
- A **Knowledge Edge** connects **Knowledge Nodes**, not mastery levels.
- A **Part-Of Knowledge Edge** represents composition, not classification or topic grouping.
- A **Knowledge Node** may be the source of multiple **Part-Of Knowledge Edges** when it is a component of multiple wholes.
- A **Prerequisite-For Knowledge Edge** represents cognitive dependency, not an absolute impossibility of partial understanding.
- A **Supports Knowledge Edge** strengthens understanding of a target without predictably blocking higher-level understanding when absent.
- A **Contrasts-With Knowledge Edge** is semantically symmetric and should not be duplicated in both directions.
- A **Contrasts-With Knowledge Edge** is stored with source and target ordered lexicographically by node id.
- A **Knowledge Edge Rationale** explains the domain relationship itself, not a user's understanding of it or how to probe a user.
- Diagnostic goals belong to **Knowledge Nodes**, not **Knowledge Edges**.
- **Curation Confidence** belongs to a **Knowledge Edge**, not to a user's knowledge state.
- **Curation Confidence** is represented as a required value from 0.0 to 1.0.
- On candidate **Knowledge Edges**, **Curation Confidence** may be an initial value suggested by the graph authoring workflow.
- On authored **Knowledge Edges**, **Curation Confidence** is the reviewed or revised value accepted by the benchmark author.
- Low **Curation Confidence** signals that a **Knowledge Edge** needs review before being treated as stable benchmark ground truth.
- **Knowledge Edge Weight** describes relationship strength and is distinct from **Curation Confidence**.
- **Knowledge Edge Weight** belongs to the authored graph and is not a task-specific scoring weight.
- **Knowledge Edge Weight** is represented as a required value from 0.0 to 1.0.
- **Effective Relationship Strength** is derived when needed and is not stored on the **Knowledge Edge**.
- A **Derived Knowledge Relationship** must not be treated as part of the **Authored Knowledge Graph**.
- A **Candidate Knowledge Graph** must be reviewed before it becomes an **Authored Knowledge Graph**.
- A **Candidate Graph Review Workbench** may edit candidate graph artifacts, but it does not make them reviewed **Authored Graph Data Files**.
- Review edits in a **Candidate Graph Review Workbench** may update the current **Candidate Knowledge Graph** artifacts in place while preserving candidate status.
- A **Candidate Knowledge Graph** should be built from a **Candidate Node Inventory** extracted from **Authoritative Sources**.
- An **Authored Knowledge Graph** is stored as separate **Authored Graph Data Files** for nodes and edges.
- V1 **Authored Graph Data Files** are typically `authored_nodes.json` and `authored_edges.json`.
- A **Graph Manifest** may reference separate **Authored Graph Data Files** for graph id, version, source, and file binding metadata.
- A **Graph Manifest** must not inline or replace the node and edge JSON lists.
- V1 does not prescribe a **Graph File Layout** yet; directory paths will be specified later by the benchmark author.
- Code and documentation should not assume a fixed graph directory path until **Graph File Layout** is explicitly defined.
- The v1 **Graph Authoring Pipeline** is implemented through a **Graph Authoring Agent Workflow**.
- The **Graph Authoring Agent Workflow** contains a **Node Extraction Agent Step**, a **Node Rubric Authoring Agent Step**, and an **Edge Proposal Agent Step**.
- The **Node Extraction Agent Step** may read the authoritative PDF or source material directly rather than relying on pre-cut chunks.
- In v1, the **Node Extraction Agent Step** is the only **Graph Authoring Agent Workflow** step that reads full **Parsed Source Markdown** directly.
- Later **Graph Authoring Agent Workflow** steps should not receive source-material text as an input parameter.
- The **Node Extraction Agent Step** is responsible for producing **Source-Grounded Node Skeletons** with **Source Locators**.
- The **Node Rubric Authoring Agent Step** runs after node extraction and before final node output.
- The **Node Rubric Authoring Agent Step** is responsible for `diagnostic_goal`, L0-L5 `levels`, diagnostic signals, and `simulator_behavior`.
- The v1 **Node Rubric Authoring Agent Step** must stay within the **Node Rubric Input Scope**.
- The v1 **Node Rubric Authoring Agent Step** must not use unreviewed neighboring nodes or candidate edges as rubric-generation context.
- The **Edge Proposal Agent Step** runs after candidate nodes are available in the same workflow.
- The v1 **Edge Proposal Agent Step** may use complete candidate **Knowledge Nodes**, including node rubrics, as edge-proposal context.
- The v1 **Edge Proposal Agent Step** must stay within the **Edge Proposal Input Scope**.
- The v1 **Edge Proposal Agent Step** uses **Precision-First Edge Proposal**.
- A candidate **Knowledge Edge** should only enter `candidate_edges.json` when it has a clear canonical edge type and a clear **Knowledge Edge Rationale**.
- Weakly related, speculative, or merely associated node pairs should be omitted from `candidate_edges.json`.
- V1 does not use a fixed **Candidate Edge Confidence Threshold**.
- Candidate **Knowledge Edge** inclusion is decided by precision-first rationale quality, not by a numeric `curation_confidence` cutoff.
- `curation_confidence` remains required on candidate **Knowledge Edges** as a review and calibration signal.
- Candidate **Knowledge Edges** proposed from rubrics still require benchmark-author review before becoming authored graph data.
- A **Graph Authoring Agent Workflow** produces **Graph Authoring Output Files**, not an automatically accepted **Authored Knowledge Graph**.
- **Graph Authoring Intermediate Artifacts** may be persisted for replay, debugging, and downstream workflow-step input, but they are not **Graph Authoring Output Files**.
- V1 **Graph Authoring Output Files** are exactly two JSON list files: one **Knowledge Node** list and one **Knowledge Edge** list.
- The filenames or enclosing review directory for **Graph Authoring Output Files** may include candidate status.
- Individual **Knowledge Node** and **Knowledge Edge** objects in **Graph Authoring Output Files** must use the normal object schemas and must not include candidate status fields.
- A **Graph Authoring Edge List** contains **Knowledge Edge** objects with edge fields such as `source`, `target`, `type`, `rationale`, `weight`, and `curation_confidence`.
- A **Graph Authoring Edge List** must not duplicate node-level rubric fields such as `definition`, `diagnostic_goal`, `levels`, or source locators.
- Validation notes may exist as intermediate workflow logs, but they are not part of the final **Graph Authoring Output Files** contract.
- V1 evaluation uses only **Authored Knowledge Graphs**, not unreviewed **Candidate Knowledge Graphs**.
- The **Graph Authoring Pipeline** is outside v1 evaluation runtime.
- V1 evaluation uses only reviewed **Ground-Truth Knowledge Maps**, not unreviewed **Candidate Knowledge Maps**.
- The **Map Authoring Pipeline** is outside v1 evaluation runtime.
- **Knowledge Edges** guide exploration and diagnosis of **Knowledge Nodes** rather than describing user state.
- **Evidence** refers to **Knowledge Nodes**, not **Knowledge Edges**.
- In v1, all evidence uses a shared **Evidence Record** structure.
- **Evidence Type** describes where evidence comes from or what role it plays.
- **Evidence Kind** describes the observable diagnostic form of evidence.
- KnowAct v1 uses `prior_answer`, `worked_example`, `self_report`, `misconception_trace`, and `background_fact` as initial **Evidence Kind** values.
- **Evidence Visibility** describes who can access evidence during a benchmark run.
- **Ground-Truth Evidence** belongs to the benchmark reference data and is hidden from the **Tested Agent**.
- **Ground-Truth Evidence** should use simulator-only or evaluator-only visibility, not tested-agent visibility.
- An **Interaction Observation** is visible to the **Tested Agent** when it comes from the agent's own interaction history.
- **Synthetic Evidence** may support a **Ground-Truth Knowledge Map**, but it must be treated as simulated benchmark data rather than real user data.
- A **User Knowledge State** references exactly one **Knowledge Node**.
- A user can have at most one current **User Knowledge State** for a given **Knowledge Node**.
- In v1, each **User Knowledge State** in a **Ground-Truth Knowledge Map** should be backed by one or more pieces of **Ground-Truth Evidence**.
- User-specific understanding of a **Knowledge Edge** is not modeled as edge state in v1.

## Example dialogue

> **Dev:** "Should we store confidence on the **Knowledge Node**?"
> **Domain expert:** "No. The **Knowledge Node** is the concept itself; confidence belongs to the **User Knowledge State** for that concept."

> **Dev:** "If a user does not understand active learning, does the prerequisite edge from epistemic uncertainty disappear?"
> **Domain expert:** "No. The **Knowledge Edge** is part of the domain structure; v1 uses it to guide diagnosis of **Knowledge Nodes**, not to create edge-level user state."

## Flagged ambiguities

- "node state" can mean either the stable properties of a **Knowledge Node** or a user's changing understanding of it; resolved: user-specific properties belong to **User Knowledge State**.
- "relation" can mean either a domain-level **Knowledge Edge** or a user's understanding of that relationship; resolved: domain-level relationships are **Knowledge Edges**.
- "Knowledge Map" and "Knowledge Graph" can be conflated; resolved: **Knowledge Graph** is user-independent structure, while **Knowledge Map** is user-specific or reconstructed state.
- "user knowledge graph" can sound like a user-specific graph structure; resolved: v1 compares **Ground-Truth Knowledge Map** and **Reconstructed Knowledge Map** over the same **Authored Knowledge Graph**.
- "interaction" can include teaching, tutoring, diagnosis, or open-ended chat; resolved: v1 focuses on **Active Knowledge-State Diagnosis**.
- "user simulator learns during the conversation" would make the benchmark target move; resolved: v1 uses **Static User Knowledge State** within an **Evaluation Episode**.
- "agent has the graph" can be confused with seeing the user's answers; resolved: v1 exposes the **Authored Knowledge Graph** while hiding the **Ground-Truth Knowledge Map**.
- "evaluation" can imply a subjective LLM judge; resolved: v1 uses **Structured Map Comparison** for primary scoring.
- "exact match" can look like a separate primary scoring metric; resolved: v1 uses **Mastery Level Distance** as the main signal, with exact match as optional zero-distance bonus.
- "mastery distance" can imply linear penalty over L0-L5; resolved: v1 uses squared distance over explicit L0-L5 scores.
- "episode score" can imply a reward where higher is better; resolved: v1 primary result is **Episode Mastery Distance**, where lower is better.
- "turn budget" can be inferred from graph size; resolved: v1 uses an explicit **Turn Budget** configured per **Evaluation Episode**.
- "episode config" can be scattered across runner arguments; resolved: v1 uses an **Evaluation Episode Manifest**.
- "scoring profile" can imply per-episode custom metrics; resolved: v1 uses fixed `squared_mastery_distance_v1` for comparability.
- "benchmark domain" can imply a multi-domain suite; resolved: v1 starts with one domain and defers multi-domain calibration.
- "machine learning algorithms" is too broad for v1; resolved: the first domain is classical supervised ML algorithms with enough nodes for profile differentiation.
- "enough knowledge nodes" is vague; resolved: the first v1 graph targets 30-50 **Knowledge Nodes**.
- "authoritative source" can remain underspecified; resolved: v1 starts from *An Introduction to Statistical Learning with Applications in Python*.
- "one turn" can hide multiple questions; resolved: v1 **Interaction Turn** allows one primary **Diagnostic Question**.
- "user simulator" can be mistaken for a state oracle; resolved: v1 **User Simulator** produces natural answers without exposing hidden labels or evidence ids.
- "ambiguous simulator answer" can mean random inconsistency; resolved: v1 allows natural ambiguity only when grounded in hidden map and evidence.
- "scored node set" can imply an extra scoring configuration; resolved: v1 scores all **Knowledge Nodes** in the **Episode Knowledge Graph**.
- "partial knowledge map" can imply a valid ground-truth reference; resolved: v1 **Ground-Truth Knowledge Map** must cover every node in the **Episode Knowledge Graph**.
- "missing prediction" can be confused with L0 mastery; resolved: missing output is a prediction failure, while L0 is a user knowledge state.
- "unsupported inference" can be confused with wrong prediction; resolved: unsupported inference is a lack of visible evidence support and is reported separately from **Mastery Level Distance**.
- "part_of" can mean either structural composition or topic/category membership; resolved: **Part-Of Knowledge Edge** means structural composition only.
- "prerequisite_for" can sound like an absolute requirement; resolved: **Prerequisite-For Knowledge Edge** means a cognitive dependency that limits higher-level understanding when absent.
- "supports" can collapse into generic relatedness; resolved: **Supports Knowledge Edge** requires a specific contribution to explanation, transfer, or diagnostic confidence.
- "contrasts_with" can sound like opposition or mutual exclusion; resolved: **Contrasts-With Knowledge Edge** means a symmetric contrast used to clarify boundaries.
- "related_to" and "used_for" are too broad for benchmark evaluation; resolved: **Knowledge Edge Type** is limited to the canonical edge types.
- "relations" is too broad as a graph collection name; resolved: use `edges` for collections of **Knowledge Edges**.
- "user edge state" would add a separate user-specific state object for every relationship; resolved: v1 keeps user state and evidence at the **Knowledge Node** level.
- "transitive edge" can blur authored ground truth with inferred structure; resolved: v1 ground truth includes only explicitly authored **Knowledge Edges**.
- "LLM-generated graph" can sound evaluation-ready; resolved: generated graphs are **Candidate Knowledge Graphs** until reviewed into **Authored Knowledge Graphs**.
- "authored graph file" can sound like one combined JSON blob; resolved: v1 stores authored nodes and authored edges as separate JSON list files.
- "graph manifest" can sound like the graph data itself; resolved: a **Graph Manifest** is optional metadata that references separate graph data files.
- "graph file layout" can sound like part of the v1 schema; resolved: v1 fixes file contents and split storage, while directory layout is deferred.
- "graph authoring agent" can sound like it bypasses review; resolved: the **Graph Authoring Agent Workflow** produces **Graph Authoring Output Files** for benchmark-author review.
- "graph authoring workflow" can be split into separate tasks; resolved: v1 uses one **Graph Authoring Agent Workflow** with node extraction, node rubric authoring, and edge proposal steps.
- "node extraction" can sound like it produces full candidate nodes; resolved: v1 node extraction produces **Source-Grounded Node Skeletons**, then node rubrics are authored in a later step.
- "node rubric context" can accidentally include unreviewed graph structure; resolved: v1 rubric authoring uses only **Node Rubric Input Scope**, not neighboring nodes or candidate edges.
- "edge proposal context" can be confused with rubric context; resolved: v1 edge proposal may use complete candidate node rubrics because it runs after rubric authoring and remains subject to review.
- "edge proposal" can become recall-first relatedness harvesting; resolved: v1 uses **Precision-First Edge Proposal** and omits weak or speculative relations.
- "precision-first" can sound like a fixed confidence threshold; resolved: v1 has no fixed **Candidate Edge Confidence Threshold** and uses rationale quality instead.
- "source preprocessing" can imply the node step only consumes pre-cut chunks; resolved: v1 allows the **Node Extraction Agent Step** to read the authoritative source directly and extract locators.
- "candidate artifact" can imply candidate fields inside every output object; resolved: candidate status belongs to the filename, directory, or review state, not to **Knowledge Node** or **Knowledge Edge** object contents.
- "validation report" can sound like a required final graph-authoring output; resolved: v1 final graph-authoring output is only the node JSON list and edge JSON list.
- "edge content" can be confused with node content; resolved: edge list items use the **Knowledge Edge** schema, not the **Knowledge Node** rubric schema.
- "LLM-generated user map" can sound evaluation-ready; resolved: generated maps are **Candidate Knowledge Maps** until reviewed into **Ground-Truth Knowledge Maps**.
- "persona" can sound like part of the scored map; resolved: **Profile Context** constrains map generation and simulation style but does not enter v1 primary scoring.
- "candidate node inventory" can sound like a brainstormed list; resolved: v1 candidate nodes must be source-grounded and carry **Source Locators**.
- "source" can be too vague to audit; resolved: use **Source Locators** that identify the source location for each **Knowledge Node**.
- "source locator" can sound like an exact excerpt requirement; resolved: v1 source locators only need simple source references and do not require `quote`, `evidence_span`, or exact offsets.
- "node hierarchy" suggests built-in levels among **Knowledge Nodes**; resolved: **Knowledge Nodes** are flat diagnosable units, while **Knowledge Edges** express relationships between them.
- "confidence" can mean curation confidence or user-state confidence; resolved: **Curation Confidence** is the author's confidence in an edge's validity.
- "candidate curation confidence" can sound like final author judgment; resolved: candidate values may be agent suggestions, while authored values are benchmark-author reviewed.
- "weight" can mean relationship strength or author confidence; resolved: **Knowledge Edge Weight** means relationship strength, while **Curation Confidence** means confidence in validity.
- "evidence" can mean real human observation or generated benchmark support; resolved: **Synthetic Evidence** is allowed in v1 but must remain traceable simulated data.
- "ground-truth evidence schema" and "interaction observation schema" can drift apart; resolved: v1 uses one shared **Evidence Record** structure with different type and visibility values.
- "reconstructed state" can mean an unsupported guess; resolved: v1 **Reconstructed Knowledge Map** states must cite tested-agent-visible **Evidence Records**.
- "reconstruction trace" can be mistaken for required scoring output; resolved: v1 requires only the **Final Reconstructed Knowledge Map** for primary scoring.
- "baseline" can expand into many comparison agents; resolved: v1 uses only fixed-question, random-question, and simple LLM baselines.
- "evidence type" and "evidence visibility" can be conflated; resolved: type describes role or origin, while visibility describes access boundary.
- "evidence kind" and "evidence type" can be conflated; resolved: kind describes observable diagnostic form, while type describes origin or lifecycle role.
