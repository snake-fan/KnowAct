# Implementation Contract

## 1. Code layout

```text
backend/knowact/agents/
├── agents/
│   ├── evidence_calibrated.py   # tested-agent orchestration and parsers
│   ├── question_bank.py         # fixed/random experimental bank policies
│   └── simple_llm.py            # existing baseline
├── belief.py                    # normalized six-level belief and Bayes update
├── question_selection.py        # typed candidates and deterministic utility
├── templates/
│   └── evidence_calibrated.py   # executable evidence/candidate prompts
├── tools.py                     # validated working-map updates/finalization
└── working_map.py               # checkpoint-persisted categorical + posterior state
```

Tests are split by responsibility rather than one end-to-end fixture:

```text
test/
├── test_v1_evidence_calibrated_agent.py
├── test_v1_question_selection.py
└── test_v1_question_bank_agents.py
```

## 2. Persisted state

`WorkingMapNodeAssessment` gains an optional `mastery_belief`. It is optional for backward compatibility with existing checkpoints and `simple_llm_agent`; ECDA writes it after an evidence update.

The belief stores six probabilities in fixed L0–L5 order and validates:

- finite values;
- every value in `[0, 1]`;
- sum equal to one within tolerance;
- deterministic entropy and mode projection.

## 3. Evidence output contract

The model returns:

```json
{
  "updates": [
    {
      "node_id": "node id",
      "answer_likelihood": {
        "l0": 0.9,
        "l1": 0.8,
        "l2": 0.4,
        "l3": 0.1,
        "l4": 0.05,
        "l5": 0.05
      },
      "observed_behavior": "what the visible answer demonstrated",
      "supporting_turn_ids": ["turn_01"],
      "contradiction": false
    }
  ]
}
```

Likelihood values are relative observation likelihoods and need not sum to one. At least one must be positive. The parser rejects unknown fields and malformed vectors.

## 4. Question-candidate output contract

The model returns `ask_diagnostic_question` with at least three typed candidates, or `finalize_reconstruction` with a reason. Each candidate contains a `DiagnosticQuestion`, `DiagnosticQuestionPlan`, and normalized utility components.

The code, not the LLM, validates graph IDs and selects the maximum utility. Model-generated chain-of-thought is neither requested nor stored.

## 5. Failure behavior

- Invalid JSON or schema: raise `ModelClientError`; runtime retry policy applies.
- Invalid graph target: reject the whole candidate output; do not silently remove targets.
- Invalid likelihood: reject the update; do not fall back to a guessed mastery.
- Zero evidence likelihood mass: reject the update.
- Diffuse posterior: preserve `unknown` rather than force L0.
- No valid candidate: finalize with an explicit reason.
- Forced-finalization phase: no model call for another question.

## 6. Runtime registration

`evidence_calibrated_agent` is a formal runtime kind because it needs only resources already frozen in the Episode Manifest: model/provider settings, graph, working map, dialogue, and turn budget.

Fixed/random bank agents are implemented as policy components but are not formal runtime kinds yet. Formal registration requires adding immutable question-bank ID/version/hash to the Episode Manifest, repository binding validation, and run artifacts. Registering them earlier would make experiments irreproducible.

## 7. Verification checklist

- [ ] belief normalization, entropy, Bayes update, legacy prior, and projection tests;
- [ ] parser rejects malformed or unknown-node evidence;
- [ ] deterministic utility and stable tie-breaking tests;
- [ ] forced finalization performs no question call;
- [ ] checkpoint round-trip retains mastery beliefs;
- [ ] visibility payload contains no hidden map/profile/simulator trace;
- [ ] fixed/random policies do not repeat a bank item and random selection is resume-stable;
- [ ] full repository test suite passes;
- [ ] paper method status distinguishes implemented ECDA mechanisms from unimplemented MapProbe
      components without implying comparative validation.

## 8. Deferred work

- versioned expert question-bank storage and manifest binding;
- learned answer-outcome model trained only on training episodes;
- joint graph posterior rather than independent node marginals;
- independent verifier provider configuration;
- experiment runner for paired multi-agent sweeps and statistical reports.

These are excluded from the first implementation slice because they require new benchmark artifacts or experiment infrastructure, not merely another prompt.
