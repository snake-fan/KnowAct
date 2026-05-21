# V1 baselines are fixed, random, and simple LLM agents

KnowAct v1 limits baseline agents to a fixed-question baseline, a random-question baseline, and a simple LLM agent. This keeps the first benchmark focused on validating the graph-bound simulator, active diagnosis loop, final reconstruction output, and structured scoring.

**Considered Options**

- Include oracle, passive summarization, teaching, and complex ToM architectures in v1.
- Start with fixed-question, random-question, and simple LLM baselines.

**Consequences**

V1 has fewer comparisons, but the baseline set is enough to check whether adaptive diagnostic question selection improves reconstruction over simple strategies.
