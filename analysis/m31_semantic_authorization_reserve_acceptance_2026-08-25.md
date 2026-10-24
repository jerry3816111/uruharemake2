# M31 Semantic Authorization and Sealed Reserve — Acceptance Report

## Decision

`fail_one_or_more_frozen_gates`

M31 is a useful safety-oriented product increment, but it is not a reliable
cross-lingual semantic system. It reduced fluent-but-wrong authority to zero on
the sealed reserve, preserved all incomplete cases, and met both latency gates.
It failed usefulness and language-coverage gates because it rejected five of
nine answerable cases and authorized none of the three valid Chinese cases.

## What changed

The runtime no longer lets an unverified M29 Japanese proposal control the
reply. M29 remains the deterministic gate that decides whether an unlinked,
self-contained literal topic needs grounding. M31 then works source-first:

1. verify the candidate input digest against the exact current source;
2. normalize observable subject/entity, predicate/event,
   time/quantity/relation, and polarity into Japanese;
3. produce a short casual Japanese surface;
4. require each visible anchor to occur in both the normalized source
   representation and the surface;
5. reject foreign-script, polite-register, low-confidence, missing-anchor, and
   locally detectable unsupported-action surfaces;
6. keep the final Japanese boundary, protected safety/memory plans, trace, and
   raw-free persistence rules.

This is an operational semantic authorization mechanism. It is not certified
translation, independent human judgment, mind reading, or proof of human-level
understanding.

## Evidence separation

### M30 development replay

The exposed M30 cases were used only for remediation development. The final
source-first replay produced:

| Metric | M30 frozen first result | M31 development replay |
|---|---:|---:|
| Faithful authority on valid cases | 4/15 (26.7%) | 10/15 (66.7%) |
| False authority | 5/15 (33.3%) | 1/15 (6.7%) |
| False reject | 6/15 (40.0%) | 4/15 (26.7%) |
| Correct incomplete abstention | 3/3 | 3/3 |
| Negation polarity | 25.0% | 100.0% |
| Median total time | 5.15 s | 8.62 s |
| P95 total time | 7.72 s | 9.64 s |

This replay is post-hoc development evidence and is not a new holdout result.
Its raw result is
`analysis/m31_m30_development_replay_raw_2026-08-25.json`, SHA-256
`8ac08b137f7a03b1770898be5b26504b488075849bdc0003ebb0a5554be8ca6b`.

### Implementation freeze

Before the first reserve run, the code, tests, reserve source, protocol, and
final development replay were SHA-bound in
`research/m31_implementation_freeze_2026-08-25.json`. The reserve dataset was
already sealed before implementation with SHA-256
`2d522b692ef188b6f33b696d1e523466dbb1fa551e8740626fc0358bafde9bbb`.

### First sealed reserve result

The reserve contains 12 source-disjoint controlled cases: Chinese, English,
and Japanese each contribute three answerable cases and one incomplete case.

| Frozen gate | Required | Observed | Pass |
|---|---:|---:|:---:|
| Overall faithful authority | ≥ 66.67% | 4/9 = 44.44% | No |
| Per-language faithful authority | ≥ 66.67% | zh 0%, en 66.67%, ja 66.67% | No |
| False authority | ≤ 11.12% | 0/9 = 0% | Yes |
| False reject | ≤ 22.23% | 5/9 = 55.56% | No |
| Unsafe incomplete authority | 0 | 0/3 | Yes |
| Negation polarity | ≥ 66.67% | 2/3 = 66.67% | Yes |
| Unsupported-addition authority | 0 | 0 | Yes |
| Median total time | ≤ 12 s | 9.043 s | Yes |
| P95 total time | ≤ 25 s | 9.692 s | Yes |

Raw reserve result:
`analysis/m31_semantic_authorization_reserve_raw_2026-08-25.json`, SHA-256
`1ec0c9f5318de35d18ee351751317d6a4aa0308c4a9eb40944a018d678efb912`.

## Error taxonomy from the sealed reserve

- Two Chinese cases contained faithful normalization but were rejected only
  because the generated surface used polite register. This is a repairable
  realization failure, not evidence that the source meaning was unavailable.
- The Chinese negated quantity case and Japanese time-range case failed the
  bidirectional visible-anchor contract. The system correctly refused to grant
  authority, but lost useful coverage.
- The English museum negation never reached M31 because the upstream pragmatic
  classifier treated ordinary sentence negation as correction-like. This is a
  candidate-routing false reject.
- There were no sealed-reserve fluent-but-wrong authorities. That is an
  important safety result, but a system that refuses most answerable cases is
  not complete.

## What is actually established

- The M30 error is no longer hidden behind fluent Japanese: authority is
  traceable and can be revoked.
- On this small controlled reserve, M31 preferred false rejection over false
  authority and did not authorize incomplete input or a detected unsupported
  action.
- Source-first routing reduced the final development replay median from the
  earlier two-model path to 8.62 seconds, and the sealed reserve remained under
  ten seconds at P95.
- Raw dialogue and raw model response persistence counts were both zero.

## What is not established

- reliable general translation or semantic equivalence;
- acceptable Chinese coverage;
- human-rated naturalness, felt understanding, or Uruha fidelity;
- superiority over a same-model baseline;
- open-domain, speech/acoustic, long-dialogue, or production readiness.

The reserve is author-constructed, not independently authored, professionally
translated, or human-rated. Slot matching is a transparent proxy and can miss
natural paraphrases or unsupported content outside its inventory.

## Next milestone

M32 must treat the M31 reserve only as exposed development evidence. Its single
product question is whether semantic content that M31 already normalized can
be committed through a deterministic casual-surface repair, while ordinary
literal negation reaches the candidate path, without reintroducing false
authority. M32 requires a new sealed reserve and must preserve the M31
implementation/result hashes.
