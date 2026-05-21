# V1 primary episode result is mean mastery distance

KnowAct v1 reports episode mastery distance as the primary episode-level result: the mean per-node mastery distance over all knowledge nodes in the episode graph. Lower values indicate closer reconstruction of the hidden ground-truth knowledge map.

**Considered Options**

- Report only per-node distances.
- Convert distances into a reward-style score where higher is better.
- Use mean per-node mastery distance as the primary episode result.

**Consequences**

V1 has a simple primary metric, but reports should state clearly that lower is better and include supporting rates such as missing prediction rate and unsupported inference rate.
