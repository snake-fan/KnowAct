# V1 tested agents use working-map semantic tools

KnowAct v1 tested agents maintain an agent-owned working knowledge map during an evaluation episode and submit a final reconstructed knowledge map through semantic tools rather than editing graph/map JSON directly or letting the runtime infer the reconstruction. This keeps active diagnosis as the tested-agent capability under evaluation while allowing the runtime to enforce visibility, turn budget, schema validation, retry limits, transcript-to-evidence wrapping, and scoring without changing the agent's judgments.
