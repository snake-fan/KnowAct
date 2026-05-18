# KnowAct Domain Context

KnowAct studies whether an agent can infer and use a user's knowledge state during knowledge-grounded interaction.

## Language

**Knowledge Node**:
A user-independent knowledge unit that is stable, diagnosable, and suitable for concept-level evaluation.
_Avoid_: node state, user node

**User Knowledge State**:
A user-specific state describing how a particular user appears to understand a **Knowledge Node**.
_Avoid_: node state, node

**Evidence**:
A traceable basis for judging a user's knowledge of a **Knowledge Node**.
_Avoid_: edge evidence, edge state, hidden rationale

**Knowledge Graph**:
The user-independent domain structure made of **Knowledge Nodes** and **Knowledge Edges**.
_Avoid_: user knowledge map, user profile

**Knowledge Map**:
A user-specific or agent-reconstructed view of knowledge state over a **Knowledge Graph**.
_Avoid_: domain graph, authored graph

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
The benchmark author's confidence that a **Knowledge Edge** is a valid domain relationship.
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

**Derived Knowledge Relationship**:
A non-authoritative relationship inferred from traversal or reasoning over the **Authored Knowledge Graph**.
_Avoid_: ground-truth edge, authored edge

## Relationships

- A **Knowledge Node** exists independently of any user.
- **Knowledge Nodes** do not belong to built-in hierarchy levels.
- A **Knowledge Graph** contains user-independent **Knowledge Nodes** and **Knowledge Edges**.
- A **Knowledge Map** represents user-specific or reconstructed knowledge state over a **Knowledge Graph**.
- `userstate` belongs to a **Knowledge Map**, not to the **Knowledge Graph**.
- `userstate` describes a user's knowledge of **Knowledge Nodes**, not **Knowledge Edges**.
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
- Low **Curation Confidence** signals that a **Knowledge Edge** needs review before being treated as stable benchmark ground truth.
- **Knowledge Edge Weight** describes relationship strength and is distinct from **Curation Confidence**.
- **Knowledge Edge Weight** belongs to the authored graph and is not a task-specific scoring weight.
- **Knowledge Edge Weight** is represented as a required value from 0.0 to 1.0.
- **Effective Relationship Strength** is derived when needed and is not stored on the **Knowledge Edge**.
- A **Derived Knowledge Relationship** must not be treated as part of the **Authored Knowledge Graph**.
- **Knowledge Edges** guide exploration and diagnosis of **Knowledge Nodes** rather than describing user state.
- **Evidence** refers to **Knowledge Nodes**, not **Knowledge Edges**.
- A **User Knowledge State** references exactly one **Knowledge Node**.
- A user can have at most one current **User Knowledge State** for a given **Knowledge Node**.
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
- "part_of" can mean either structural composition or topic/category membership; resolved: **Part-Of Knowledge Edge** means structural composition only.
- "prerequisite_for" can sound like an absolute requirement; resolved: **Prerequisite-For Knowledge Edge** means a cognitive dependency that limits higher-level understanding when absent.
- "supports" can collapse into generic relatedness; resolved: **Supports Knowledge Edge** requires a specific contribution to explanation, transfer, or diagnostic confidence.
- "contrasts_with" can sound like opposition or mutual exclusion; resolved: **Contrasts-With Knowledge Edge** means a symmetric contrast used to clarify boundaries.
- "related_to" and "used_for" are too broad for benchmark evaluation; resolved: **Knowledge Edge Type** is limited to the canonical edge types.
- "relations" is too broad as a graph collection name; resolved: use `edges` for collections of **Knowledge Edges**.
- "user edge state" would add a separate user-specific state object for every relationship; resolved: v1 keeps user state and evidence at the **Knowledge Node** level.
- "transitive edge" can blur authored ground truth with inferred structure; resolved: v1 ground truth includes only explicitly authored **Knowledge Edges**.
- "node hierarchy" suggests built-in levels among **Knowledge Nodes**; resolved: **Knowledge Nodes** are flat diagnosable units, while **Knowledge Edges** express relationships between them.
- "confidence" can mean curation confidence or user-state confidence; resolved: **Curation Confidence** is the author's confidence in an edge's validity.
- "weight" can mean relationship strength or author confidence; resolved: **Knowledge Edge Weight** means relationship strength, while **Curation Confidence** means confidence in validity.
