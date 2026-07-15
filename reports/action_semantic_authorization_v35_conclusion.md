# V35 semantic action authorization conclusion

## Question

Could a smaller local model safely approve already-proposed VRM actions better than the V34 lexical validator?

## Best comparable result

| version | changed variable | Qwen2.5 proposals: exact / recall / false | Qwen3.5 proposals: exact / recall / false | 4B p50 | result |
|---|---|---:|---:|---:|---|
| V34 | hand-written lexical validator | 80.6% / 59.4% / 0.0% | 77.8% / 59.4% / 2.8% | n/a | FAIL |
| V35 | schema supplied only through Ollama `format` | 55.6% / 0.0% / 0.0% | 55.6% / 0.0% / 0.0% | 1.58-1.65s | FAIL: parse 0% |
| V35.1 | exact JSON fields added to text contract | **83.3% / 71.9% / 0.0%** | **88.9% / 81.2% / 0.0%** | 3.76-3.80s | FAIL |
| V35.2 | complete 15-call ontology added | 75.0% / 59.4% / 2.8% | 80.6% / 68.8% / 2.8% | 4.07-4.35s | FAIL |
| V35.3 | ontology filtered to proposed calls | 80.6% / 71.9% / 2.8% | 86.1% / 81.2% / 2.8% | 3.85-3.91s | FAIL |

All rows use the same retired V34 cases, raw proposals, candidate artifacts, seed, scoring code, and preregistered gates. These are development comparisons, not confirmation evidence.

## What was learned

1. A smaller model is not automatically better for a narrow role. The 0.8B and 2B authorizers lost substantial meaning and did not satisfy the safety gates.
2. The first V35 failure was an interface bug, not a capacity result. Ollama returned valid JSON without enforcing the requested fields; spelling out the fields restored parsing.
3. Supplying every tool definition created irrelevant-context interference and higher latency. Relevance filtering recovered part of the loss but did not pass.
4. A call-by-call approver has a structural ceiling. It can remove a bad proposal but cannot restore an action omitted by the proposer, and independent verdicts can lose negation or coordination scope across clauses.

## Decision

- Do not integrate V34, V35, V35.1, V35.2, or V35.3 into runtime action execution.
- Do not author a fresh confirmation holdout because no development candidate passed.
- Stop adding prompts or phrase aliases to the per-proposed-call authorizer.

## Next architecture boundary

V36 should parse the complete utterance once into an observable action-intent frame:

```text
user utterance
  -> current request state
  -> positive / negated / cancelled action clauses
  -> exact evidence spans
  -> deterministic allowlist compiler
  -> environment-disabled VRM calls
```

This representation can recover multiple requested actions, preserve the scope of negation and cancellation, and still prevent the model from directly executing arbitrary functions.
