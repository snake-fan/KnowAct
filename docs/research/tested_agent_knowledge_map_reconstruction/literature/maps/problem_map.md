# Problem Map

```text
hidden user knowledge map
├── sparse and ambiguous open-ended evidence
│   ├── rubric grounding
│   ├── contradiction and hedging
│   └── direct versus incidental evidence
├── sequential belief maintenance
│   ├── cold start
│   ├── uncertainty and abstention
│   └── evolving or noisy state
├── budgeted diagnostic action
│   ├── target selection
│   ├── coherent question realization
│   └── stopping under marginal value
├── graph-structured dependencies
│   ├── useful soft inference
│   └── correlated error amplification
└── evaluation validity
    ├── hidden-state leakage
    ├── model/call-budget confounding
    ├── simulator bias
    ├── stochastic reliability
    └── final-score-only diagnosis
```

The primary scientific problem is not response generation. It is recovering a structured hidden state
while choosing which evidence to request next. The evaluation must therefore score both reconstruction
and the information-acquisition process.
