# Method Map

| Method family | Representative papers | Strength | Missing piece for KnowAct |
|---|---|---|---|
| recurrent / deep knowledge tracing | P001, P002 | sequential latent-state update | explicit full-map beliefs and active open-ended probes |
| cognitive diagnosis + CAT | P003, P004 | informative item selection and early diagnosis | natural-language evidence and zero-history operation |
| conversational diagnosis | P005, P006, P007 | interpretable stage decomposition and memory | target selection optimized for reconstruction |
| dynamic profiling | P008, P009, P010 | selective acquisition, profile update, downstream use | graph-indexed ordinal mastery and diagnostic rubrics |
| interactive-agent evaluation | P011, P012, P013 | simulator validation, end-state checks, reliability, process metrics | direct hidden-user-state outcome |
| construct controls | P014 | isolates inference from superficial cues | budgeted interaction and persistent reconstruction |

Proposed synthesis:

```text
visible answer
  -> rubric-grounded evidence record
  -> explicit ordinal node beliefs
  -> typed attenuated graph messages
  -> utility-scored target plan
  -> verified diagnostic question
  -> stop or repeat
```
