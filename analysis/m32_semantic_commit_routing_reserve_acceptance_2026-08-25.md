# M32 Semantic Commit Repair and Fresh Routing — Acceptance Report

## Decision

`fail_one_or_more_frozen_gates`

M32 fixes two real runtime defects: ordinary self-contained facts can enter the
semantic path on the first turn, and a semantically incomplete M31 surface is
replaced by a complete deterministic rendering of M31's canonical fields. It
also removes the lexical collision that treated `um` inside words such as
`community` or `museum` as hesitation.

The first sealed reserve nevertheless fails. M32 reliably commits the
canonical representation it receives, but that representation can already be
wrong. A complete, fluent Japanese surface is not evidence that the source
meaning was preserved.

## What changed

1. M29 accepts bounded, self-contained literal input in a fresh session as
   well as after an unlinked uncertain prediction.
2. English hesitation markers `uh` and `um` must be standalone tokens; they no
   longer match substrings in ordinary words.
3. M32 receives only M31 canonical subject, predicate, time/relation, polarity,
   and literal summary fields. It calls no additional model and stores no raw
   dialogue or raw model response.
4. If M31 rejects only the realization surface, M32 builds a deterministic
   casual Japanese commitment from those canonical fields.
5. If M31 grants authority to a surface that its own semantic self-check says
   dropped subject, predicate, relation, or polarity, M32 overrides that
   surface with the complete canonical proposition.
6. The final visible boundary rechecks M32 authority and anchors. Runtime graph
   nodes show candidate routing, M31 authorization, M32 commit/rejection, and
   final Japanese surface separately.

This is a bounded semantic-commit mechanism. It is not an independent semantic
parser, certified translation, human judgment, mind reading, or evidence of
general human-level understanding.

## Evidence separation

### Exposed development replay

The already exposed M31 reserve was used for implementation debugging only.
The final replay produced 8/9 proxy-faithful authorities, 0 false rejects, 3/3
correct incomplete abstentions, and 100% negation polarity. Median total time
was 7.6397 seconds and P95 was 8.2450 seconds. The one proxy failure was the
valid Japanese alias `列車券`, absent from the frozen slot inventory for
`火車票`; it remains scored as a failure and is not re-labelled in the raw
result.

This is post-hoc evidence, not a new holdout. Raw result:
`analysis/m32_m31_exposed_development_replay_raw_2026-08-25.json`, SHA-256
`71204a0866cd8b193779dcc44472cabd7bac4c96df83730c4e1889d07f8ababc`.

### Implementation freeze

Before the first M32 reserve execution, implementation, tests, evaluation
harness, protocol, and dataset hashes were bound in
`research/m32_implementation_freeze_2026-08-25.json`, SHA-256
`caf280ddc08e737bd93341d6a56afa59dfe4ac9fe4e562085f2665947fe71b36`.
The source-disjoint reserve dataset was sealed before implementation with
SHA-256
`4a26afa7c6b66537f93116af4f38e93980890d5958564f625527dda9babd2828`.

### First sealed reserve result

The reserve contains 15 controlled cases: Chinese, English, and Japanese each
contribute four answerable cases and one incomplete case. Nine answerable
cases are fresh-session first turns.

| Frozen gate | Required | Observed | Pass |
|---|---:|---:|:---:|
| Overall faithful authority | >= 75% | 7/12 = 58.33% | No |
| Each language | >= 75% | zh 25%, en 75%, ja 75% | No |
| Fresh-session faithful authority | >= 75% | 6/9 = 66.67% | No |
| Ordinary negation | 100% | 1/1 = 100% | Yes |
| False authority | <= 8.34% | 4/12 = 33.33% | No |
| False reject | <= 16.67% | 1/12 = 8.33% | Yes |
| Unsafe incomplete authority | 0 | 0/3 | Yes |
| Negation polarity | 100% | 100% | Yes |
| Unsupported-addition authority | 0 | 0 | Yes |
| Median total time | <= 12 s | 7.6775 s | Yes |
| P95 total time | <= 20 s | 8.9144 s | Yes |
| Raw dialogue/model response persisted | 0 | 0/0 | Yes |

Raw reserve result:
`analysis/m32_semantic_commit_routing_reserve_raw_2026-08-25.json`, SHA-256
`dccddff7851723ba7da39fdc874f90740773e767e6408dce30d3db2523bb80d4`.

## Error taxonomy from the sealed reserve

- Chinese time normalization emitted `後天` instead of Japanese `明後日`.
- Chinese `鉛筆` was generalized to `ペン`, losing the object type.
- Chinese `下週三` became Tuesday and the change operator in `改到` was
  omitted.
- English `moved to next Wednesday` became the awkward `移動した`; the frozen
  change-operator proxy did not accept it as a reliable schedule change.
- A directly answerable Japanese `しかない` quantity statement was rejected.

These are upstream source-to-canonical semantic failures. M32's deterministic
commit made several of them more visible, but cannot correct them without an
independent source-grounded constraint.

## Safari and graph evidence

An isolated Safari session, backed by temporary memory paths, verified:

- fresh English entity/relation/quantity/time input produced
  `ダニエルは火曜日にメイに赤いペン四本を渡したんだね。`;
- ordinary negation containing `community` produced
  `コミュニティセンターは日曜日に閉まらないんだね。`;
- an incomplete `Maybe the one near...` obtained no M31/M32 surface authority;
- the live graph showed
  `M31 surface mismatch -> M32 authoritative_surface_completeness_override -> surface matched`.

No formal long-term database was used. Existing Safari tabs were not closed.

## What is established

- Fresh-session literal routing and the `um` substring bug are fixed for the
  covered runtime contract.
- Canonical semantic fields can be committed to a complete Japanese surface
  without a second model call.
- M32 preserves incomplete-input abstention, polarity, unsupported-addition,
  latency, and raw-persistence gates on this reserve.
- The runtime graph makes a false M31 surface and the M32 replacement visible
  instead of hiding the correction.

## What is not established

- reliable Chinese or cross-lingual semantic normalization;
- reliable preservation of temporal expressions, fine object types, or change
  operators;
- same-model superiority, human-rated naturalness, felt understanding, or
  Uruha fidelity;
- open-domain, speech/acoustic, long-dialogue, or production readiness.

The reserve is author-constructed, not independently authored, professionally
translated, or human-rated. Slot matching is a transparent proxy and can both
miss acceptable paraphrases and overlook errors outside its inventory.

## Next milestone

M33 must not modify or reinterpret the M32 frozen result. It will add a
source-anchored semantic atom ledger, independent of the model's self-report,
for observable time, object, quantity, negation, and change relations. The
ledger must either verify the canonical structure atom by atom, provide a
bounded deterministic repair with explicit provenance, or revoke surface
authority. Direct Japanese source content should not be needlessly translated
through a model. A new source-disjoint sealed reserve is required.
