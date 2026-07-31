# Evidence Map

| Design decision | Strongest evidence | What remains unverified in KnowAct |
|---|---|---|
| sequential state should be explicit and updated each turn | P001, P005, P006, P007, P009 | whether probabilistic node beliefs beat hard prompted labels |
| target selection should be separated from question wording | P003, P008 | whether expected information gain can be estimated for open answers |
| early-turn performance is a first-class outcome | P003, P004 | stability across graph size, domain, and simulator model |
| reconstruction and downstream action need separate metrics | P005, P009 | whether good maps causally improve later interaction choices |
| abstention and cost belong in the policy | P008 | how to calibrate `unknown` under squared mastery loss |
| process metrics and repeated trials are required | P012, P013 | which reliability statistic best fits node-map reconstruction |
| simulator claims require human-linked validation | P011 | behavior and agent-ranking agreement in KnowAct domains |
| apparent mental-state reasoning needs control conditions | P014 | controls for graph-copying, verbosity, and answer-style shortcuts |
| graph edges may support soft inference | no direct complete anchor | relation-specific transforms, attenuation, and robustness to bad edges |

The final row is the key research gap. It is not licensed by citation and must be experimentally earned.
