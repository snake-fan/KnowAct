# Evidence Synthesis and the SAGE Workflow

## Proposed Name

**SAGE — Scoped Answer Generation from Epistemic State**

The name is descriptive before it is rhetorical:

- **Scoped:** a question is grounded on the public graph before any hidden state
  is read.
- **Answer Generation:** the observable product is a bounded answer, not an
  omniscient profile report.
- **Epistemic State:** content comes from reviewed node-level mastery,
  misconception, uncertainty, and evidence, not from a free-form persona.

SAGE names a workflow and information contract. It does not imply a new
cognitive theory or a learned model.

## Current Implementation

The current simulator already implements four separable stages:

1. the grounder sees the public graph, the question, and limited visible
   history;
2. the context builder retrieves hidden state and evidence only for directly
   grounded nodes;
3. the answer policy creates and validates a de-identified structured
   blueprint;
4. the generator receives the blueprint, visible dialogue, and an optional
   style hint, with bounded retry and safe fallback on provider or parse
   failure.

There is currently **no independent post-generation semantic validator**.
Therefore the implemented boundary reduces direct raw-field exposure, but does
not by itself establish semantic fidelity or adversarial non-leakage.

## Formal Workflow

Let the reviewed public graph be
\(\mathcal{G}=(\mathcal{V},\mathcal{E})\), the hidden reviewed user map be
\(\mathcal{M}^{\star}\), the current question be \(q_t\), and tested-agent-visible
history be \(\mathcal{H}^{vis}_{t-1}\).

### 1. Public-scope grounding

\[
S_t = g(q_t,\mathcal{G},\mathcal{H}^{vis}_{t-1}).
\]

The grounder returns directly licensed nodes or a structured rejection. It
cannot choose a convenient target after observing hidden mastery.

### 2. Minimal hidden-context retrieval

\[
C_t = R(\mathcal{M}^{\star}, Z; S_t),
\]

where \(Z\) contains simulator-only reviewed evidence. Retrieval is limited to
\(S_t\); graph neighbors are not implicitly disclosed.

### 3. Epistemic abstraction

\[
B_t = \pi(C_t,q_t).
\]

The answer policy maps raw local state into a de-identified blueprint containing
permitted claims, uncertainty, misconception cues, answer shape, and overclaim
limits.

### 4. Surface realization

\[
a_t \sim p_{\phi}
  \left(\cdot \mid B_t,\mathcal{H}^{vis}_{t-1},\eta\right),
\]

where \(\eta\) is optional style context. The generator does not receive
\(\mathcal{M}^{\star}\), raw evidence identifiers, mastery labels, or scoring
fields.

### 5. Failure closure

Schema-invalid policies and failed, timed-out, empty, or malformed generations
enter bounded repair or a safe fallback. No unparsed provider response should
be silently promoted to a normal observation.

## Why These Stages Are Scientifically Motivated

| SAGE decision | Evidence pattern | Limitation | Required KnowAct test |
| --- | --- | --- | --- |
| Ground before hidden access | Grounded dialogue and programmable-flow work shows value in explicit selection before realization | Grounding accuracy does not establish human behavior | target-node precision, compound-question rejection, off-target stress test |
| Retrieve only local state | Simulator work shows unconstrained models invent goals and behavior | Context isolation does not prove output non-leakage | forbidden-field scan, canary fields, adversarial label-seeking probes |
| Use an epistemic blueprint | Student-simulation work shows helpful models overperform low-ability users | A correct schema may still encode the wrong boundary | human–simulator mastery distance, over/understatement rates |
| Separate content and style | Planning and controllable-generation work supports plan-to-text decomposition | Transfer from stories or task plans is structural only | no-blueprint and no-style ablations |
| Keep persona secondary | Persona and demographic studies report limited or distorted conditioning | Aggregate effects may differ from individual fidelity | paired no-style/full-style self-fidelity comparison |
| Validate as a proxy | User-simulator and arena work distinguishes direct fidelity from downstream rankings | Rank agreement can hide shared absolute bias | state fidelity plus matched human agent-rank agreement |

## Competing Explanations and Falsifiable Hypotheses

### H-S1: Scope isolation

Compared with a monolithic role prompt, SAGE will reduce disclosures of
unlicensed nodes and hidden fields without increasing fallback enough to erase
diagnostic coverage.

### H-S2: Epistemic fidelity

Compared with persona-only and no-blueprint controls, SAGE answers will reduce
absolute human–simulator expressed-mastery error and signed overperformance,
especially for low-mastery and misconception-bearing nodes.

### H-S3: Boundary expression

SAGE will better preserve uncertainty, “do not know” boundaries, and reviewed
misconceptions than a helpful assistant prompted to role-play a learner.

### H-S4: Style non-interference

Profile Context will improve perceived expression authenticity without
materially shifting rated mastery, correctness, misconception, or uncertainty.

### H-S5: Proxy validity

Agent effect directions and rankings under SAGE will agree with matched human
episodes within predeclared uncertainty. Naturalness alone cannot support this
hypothesis.

All five hypotheses may fail independently.

## Baselines and Ablations

| Condition | What it tests |
| --- | --- |
| Monolithic role prompt | Whether staged information contracts add value beyond prompting |
| Persona-only prompt | Whether style/background can substitute for reviewed epistemic state |
| SAGE without blueprint | Whether raw local context causes overstatement or leakage |
| SAGE without reviewed evidence | Whether mastery labels alone can produce diagnostic detail |
| SAGE without style context | Whether style affects authenticity without changing content |
| SAGE with rule/template realization | Whether the LLM surface generator adds fidelity or only fluency |
| SAGE with full-map context | Offline, isolated safety ablation for the value of scope minimization |
| Full SAGE | Combined workflow |

The full-map and raw-state conditions are unsafe for routine benchmark runtime.
They may run only in an isolated validation harness whose outputs are never
shown to tested agents.

## Claim Ladder

1. **Structural access claim:** verified by code, contracts, and tests.
2. **Output safety claim:** requires adversarial leakage experiments.
3. **State-fidelity claim:** requires held-out human answers and blinded ratings.
4. **Proxy-validity claim:** requires matched human and simulator agent
   comparisons.
5. **Human-like cognition claim:** out of scope and not implied by any result.

The paper should report the highest completed level and explicitly withhold all
higher claims.
