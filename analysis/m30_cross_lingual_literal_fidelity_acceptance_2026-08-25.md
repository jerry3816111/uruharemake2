# M30 Cross-Lingual Semantic Fidelity Holdout and Error Taxonomy

Status date: 2026-08-25  
Decision: **failed one or more frozen gates**  
Engineering status: diagnostic milestone complete; M29 generalized authority is not yet reliable  
Claim boundary: controlled semantic-slot proxy frozen before first run, but authored after M29 development and not independently annotated

## 1. Why M30 was necessary

M29 checks that an exact source span exists and declared Japanese anchors reach the visible reply. Those checks establish traceability, but they do not independently prove that the Japanese subject, predicate, time, quantity, relation, or polarity mean the same thing as the source.

M30 therefore froze a controlled 18-case construction holdout before the first model run:

- Chinese, English, and Japanese: 6 cases each.
- 15 self-contained cases where authority is expected.
- 3 incomplete cases where fail-closed abstention is expected.
- Semantic stressors: entity, time, quantity, negation, relation, and incomplete reference.
- Frozen hash: `1dce6689ec4a672e87495502b86e90ff9430b25b65fc3dcd2614bbfcad73352e`.
- Frozen gates were written before model execution and were not changed after the result.

## 2. Frozen success gates

| Gate | Threshold | Result |
|---|---:|---:|
| overall faithful rate on valid cases | ≥ 80% | **26.67% fail** |
| each language faithful rate | ≥ 60% | zh 20%, en 20%, ja 40% — **fail** |
| false-authority rate on valid cases | ≤ 10% | **33.33% fail** |
| false-reject rate on valid cases | ≤ 20% | **40.00% fail** |
| unsafe authority on incomplete cases | 0 | **0 pass** |
| negation polarity accuracy | ≥ 80% | **25.00% fail** |
| median projection latency | ≤ 8 s | **5.1547 s pass** |
| p95 projection latency | ≤ 15 s | **7.7157 s pass** |

Raw result hash: `addbf8b63fb6b5f113dac91150c9ad5a264fc78c15086e3c7ec5522062cb8365`.

## 3. Outcome matrix

```text
15 authority-expected cases
├─ 4 faithful authority       26.67%
├─ 5 false authority          33.33%
└─ 6 false reject             40.00%

3 incomplete cases
└─ 3 true abstention         100.00%
```

The important result is not merely low accuracy. M29 currently fails in two different engineering directions:

1. **False reject:** useful current content is discarded because a surface-anchor check fails or an over-broad cue rule blocks the candidate.
2. **False authority:** a fluent Japanese reply gets visible authority even though a frozen semantic slot is missing or wrong.

These require different fixes. Relaxing the gate to improve coverage would make false authority worse; tightening the gate without a better semantic verifier would increase false rejection.

## 4. Representative errors

| Case | Observed result | Error |
|---|---|---|
| Chinese doctor/time | `王医生水曜日三点来ね。` | loses `午後`; malformed predicate |
| Chinese next-Tuesday meeting | `会議は来週二に。` | loses Tuesday morphology and the fact that the meeting changed |
| Chinese Friday negation | no projection | the generic `不是` cue exclusion blocks a literal negation case |
| English older sister | `年上の妹が大阪に住んでる` | contradicts `older sister` by producing `妹` |
| English one ticket | `チケット一つだけね。` | meaning is roughly one, but misses the frozen ticket counter proxy; this shows the proxy is stricter than human semantic equivalence |
| Japanese Friday-not-Thursday contrast | visible response preserves contrast | contract polarity is `affirmed`, so the structured representation disagrees with its own surface |

One additional blind spot was observed: `猫は机の下にいる。` received the extra reaction `探してあげる。`. The frozen slot proxy still marked this case faithful because all required source facts were present; therefore the 26.67% score may still underestimate unsupported additions. This was not retroactively added to the frozen scoring rule.

## 5. What passed

- All three incomplete cases failed closed; no unsafe incomplete authority occurred.
- Median and p95 local projection latency passed the frozen limits.
- No raw dialogue or raw model response was persisted in any result row.
- The evaluator separates false authority, false reject, and true abstention rather than collapsing them into one accuracy number.
- Protocol, source hash, result rows, and gates are reproducible.

## 6. What this changes about M29's claim

M29 remains a valid product demonstration of a generalized, traceable surface contract. M30 shows that it cannot yet be called a reliable generalized semantic-grounding mechanism.

Allowed claim:

> UruhaBrain can expose and enforce source/Japanese surface anchors for new cross-lingual topics, and it safely abstains on the three frozen incomplete cases.

Disallowed claim:

> The current M29 projection reliably preserves arbitrary cross-lingual meaning.

The three successful Safari examples are demonstrations, not reliability evidence.

## 7. Visual evidence

Safari visualization: `analysis/m30_safari_fidelity_error_taxonomy_2026-08-25.jpeg`. The live runtime page shows the frozen M30 outcome matrix directly above the actual M29/M28/M27 node graph, so the successful demo path and its current reliability limit remain visible together.

## 8. Next engineering milestone

M31 should add a semantic authorization layer before surface authority:

1. remove the over-broad literal-negation candidate block without weakening explicit-correction authority;
2. require canonical polarity and structured source-to-Japanese slot verification;
3. keep surface-anchor mismatch fail closed, but distinguish repairable realization mismatch from semantic mismatch;
4. reject unsupported additions separately from missing slots;
5. preserve this M30 result unchanged as development evidence;
6. use a new sealed reserve set for confirmation, because repairing against these 18 cases turns them into development data.

No M31 remediation may be reported as a holdout confirmation on the same M30 cases.
