# Memory cue-driven extractive fallback V4 preregistration

## Why this experiment exists

V3 showed that a highlighted second read increased evidence recall from 68.75% to
72.92% but recovered 0 of 15 triggered answers. Repeating the same extractor is
therefore not the next justified runtime change.

V4 tests a different cognitive mechanism: the question acts as a retrieval cue,
and the fallback exposes only a small set of exact user utterances to the answer
model. It does not summarize, rewrite, or admit assistant guesses.

The design is motivated by encoding-specific retrieval cues, source monitoring,
selective retrieval, and extractive context compression. The exact paper links are
bound in the preregistration JSON.

## Frozen data

- 16 new scenarios x beginning/middle/end = 48 cases.
- 36 answerable and 12 genuinely unanswerable cases.
- 24 development and 24 transfer cases; transfer remains internal diagnostic data.
- Exact scenario ID and question reuse from V1, V2, and V3: 0.
- Dataset SHA-256: `ac744e0f9493ffb4ba470754e8473d04238be4e86c06fbcd6b8b67b155de130a`.
- Cases SHA-256: `44b3f662775e5819ddeaa9fd3af4ff2990dd6687fc01a9cc64d4ae7e51b690e6`.

## Frozen preimplementation audit

| Existing component | Result before V4 treatment code | Tuning after freeze |
|---|---:|---:|
| Query-aware user-turn selector | 91/96 gold utterances; 96 selected; 5 false positives | forbidden |
| Candidate sufficiency on answerable cases | 33/36 | forbidden |
| Candidate rejection on unanswerable cases | 12/12 | forbidden |

The three known sufficiency misses are all the same natural phrase, `three mornings
a week`. They remain in the frozen set and the gate remains unchanged so V4 cannot
manufacture a perfect precondition after looking at the data.

## Conditions

| ID | Shared primary path | Only changed component |
|---|---|---|
| A | Existing full-session pipeline | No provenance gate or fallback |
| P | User-only ledger plus sufficiency gate | Fixed abstention when insufficient |
| R | Same as P | Highlighted full-context model reread |
| E | Same as P | Exact query-aligned user utterances, then direct source-only answer |

The key causal comparisons are `R - P` and `E - P`: both start from the same
primary path and differ only in what happens after primary insufficiency.

## Promotion boundary

E must strictly improve answerable and overall pass rates over P, keep 12/12
unanswerable abstention, introduce no family or position regression, recover at
least one triggered case, and cost no more than R. Passing only authorizes a new
untouched evaluation. It never authorizes a runtime change by itself.
