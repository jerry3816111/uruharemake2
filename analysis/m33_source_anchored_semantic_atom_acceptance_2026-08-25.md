# M33 Source-Anchored Semantic Atom Ledger — Acceptance Report

## Decision

`pass_all_frozen_gates`

M33 passes its first and only sealed reserve execution. Across 12 answerable
Chinese, English, and Japanese cases, all 12 final surfaces preserved every
required source atom. All three incomplete fragments withheld M33 authority.
Five lower-path semantic conflicts were exposed and repaired from the exact
source ledger; no unresolved source conflict reached the user-visible reply.

This is a positive result for a deliberately bounded mechanism. It establishes
that exact source constraints can prevent a model-generated canonical
self-report from validating its own semantic error on the five covered
construction families. It does not establish open-domain parsing, general
translation, felt understanding, or a human-equivalent cognitive equation.

## Why M33 was necessary

M32 showed that making a Japanese sentence complete and fluent is not enough.
Its deterministic surface faithfully rendered the canonical fields it was
given, but those fields had already lost or changed details such as `鉛筆`,
`下週三`, and the change operator in `改到`.

M33 therefore introduces an independent path:

`exact source -> typed atoms -> canonical comparison -> repair or revoke -> Japanese surface`

The model can still propose a useful canonical interpretation, but it can no
longer be the sole witness that its own interpretation preserved the source.

## What changed

1. A bounded deterministic extractor identifies observable entity, time,
   object, quantity, negation/limitation, change, and spatial-relation atoms for
   five frozen construction families.
2. Each atom carries a deterministic rule id, a source-span digest, normalized
   Japanese aliases, and provenance. The persisted ledger does not copy the raw
   source sentence.
3. M33 compares these atoms with the M31/M32 canonical representation and marks
   each required atom as supported, contradicted, unavailable, or
   not-applicable.
4. A source conflict may reach the visible surface only after bounded
   source-atom reconstruction. Otherwise authority is revoked.
5. Direct Japanese uses identity/normalization and does not make an unnecessary
   translation-model call.
6. The final Japanese guard, Uruha surface contract, incomplete-input guard,
   memory-safety plan, and raw-persistence boundary remain active.
7. The runtime graph exposes source ledger, verification, committed surface,
   and conflict-repair provenance as separate nodes.

## Evidence separation

### Exposed development replay

The already exposed M32 reserve was used only for implementation debugging.
It produced 12/12 proxy-faithful authorities, 3/3 correct incomplete
abstentions, 100% language, fresh-session, direct-Japanese, change, quantity,
polarity, and atom-trace rates, with four M33 conflict repairs. Median total
time was 8.2180 seconds and P95 was 9.3786 seconds.

This was post-hoc development evidence, not a new holdout. Raw result:
`analysis/m33_m32_exposed_development_replay_raw_2026-08-25.json`, SHA-256
`281295d00c9b82feafec4a5f6042cd0582f3d26e6cfcf2c1367c7442f867f906`.

### Implementation freeze

Before the first M33 reserve execution, implementation, tests, evaluator,
dataset, protocol, and Safari evidence hashes were bound in
`research/m33_implementation_freeze_2026-08-25.json`, SHA-256
`1db3523d213114c62e3060377e7fedd3274500089bcbf5784cd6eeee96555b1b`.
The frozen source-disjoint reserve SHA-256 is
`b86025e70692c9bfe46aaa5e984968c6c4fe279fa24ce9104ab95644177f022c`;
the protocol SHA-256 is
`c399ed361562d02ffb93c2434ca206c5e6599e407c0301d1cf3fb49a89ebab09`.

Pre-freeze evidence was 166/166 focused compatibility tests, compile and diff
checks, plus isolated Safari turns. No reserve result was known at freeze time.

### First sealed reserve result

The reserve contains 15 source-disjoint controlled cases: Chinese, English,
and Japanese each contribute four answerable cases and one incomplete case.
Six answerable cases are fresh-session first turns.

| Frozen gate | Required | Observed | Pass |
|---|---:|---:|:---:|
| Overall faithful authority | >= 75% | 12/12 = 100% | Yes |
| Each language | >= 75% | zh 100%, en 100%, ja 100% | Yes |
| Fresh-session faithful authority | >= 83.33% | 6/6 = 100% | Yes |
| Direct Japanese | 100% | 4/4 = 100% | Yes |
| Change operator | >= 66.67% | 3/3 = 100% | Yes |
| Negated/limited quantity | 100% | 3/3 = 100% | Yes |
| Required source-atom trace coverage | 100% | 100% | Yes |
| False authority | <= 8.34% | 0/12 = 0% | Yes |
| False reject | <= 16.67% | 0/12 = 0% | Yes |
| Unsafe incomplete authority | 0 | 0/3 | Yes |
| Negation polarity | 100% | 100% | Yes |
| Unsupported-addition authority | 0 | 0 | Yes |
| Unresolved source-conflict authority | 0 | 0 | Yes |
| Median total time | <= 12 s | 9.2464 s | Yes |
| P95 total time | <= 20 s | 13.2376 s | Yes |
| Raw dialogue/model response persisted | 0 | 0/0 | Yes |

Raw reserve result:
`analysis/m33_source_anchored_semantic_atom_reserve_raw_2026-08-25.json`,
SHA-256
`6744a8e7d7f6725a637dd0d5d1d43ea9a1216787d388c6ab0edf63cf86c6047e`.

## Concrete sealed examples

### Chinese source/canonical conflict

- Source: `抽屜裡沒有兩把剪刀。`
- Required atoms: drawer, scissors, two, negation.
- Lower canonical path conflicted with the source.
- M33 visible result: `引き出しには二本のはさみがないんだね。`

### English source/canonical conflict

- Source: `Priya meets Omar at 3:30 p.m. the day after tomorrow.`
- Required atoms: Priya, Omar, 3:30 p.m., day after tomorrow, meeting.
- Lower canonical path conflicted with the source.
- M33 visible result: `プリヤは明後日の午後3時半にオマールと会うんだね。`

### Direct Japanese identity path

- Source: `引き出しには青い封筒が二枚しかない。`
- Required atoms: drawer, blue envelopes, two, limitation.
- M31 translation inference was skipped.
- M33 visible result: `引き出しには青い封筒が二枚しかないんだね。`

### Incomplete input

- Source: `The folder beside the...`
- M33 result: no source-atom surface authority.
- The ordinary conversational fallback remained responsible for the visible
  Japanese response; M33 did not invent the missing object or relation.

## Safari and graph evidence

An isolated Safari session used temporary memory and log paths. It verified:

- Chinese `盒子裡沒有三支鉛筆。` exposed an M31 object conflict (`ペン`),
  then M33 restored `鉛筆` in `箱には三本の鉛筆がないんだね。`;
- Japanese `この棚にはノートが三冊しかない。` used the direct identity
  path and produced `この棚にはノートが三冊しかないんだね。`;
- incomplete English obtained no M29/M31/M32/M33 surface authority;
- the live graph showed the actual input -> source atoms -> verification ->
  M33 commitment -> visible utterance path.

Screenshots:

- `analysis/m33_safari_source_atom_conflict_graph_2026-08-25.png`
- `analysis/m33_safari_source_atom_full_graph_2026-08-25.png`

No existing Safari tabs were closed. Formal long-term memory was not used.

After the sealed result, the observatory received a presentation-only green
result strip that reads the immutable raw result. This did not change the M33
extractor, evaluator, reserve, protocol, thresholds, or sealed raw result.

## What is established

- For the five frozen construction families, the system has a source-derived
  constraint independent of model self-report.
- All required source atoms remained traceable to the final Japanese surface on
  the first sealed reserve.
- When the lower model path disagreed with the exact source, the disagreement
  became visible and was repaired rather than hidden.
- Direct Japanese avoided unnecessary translation inference.
- Incomplete input, polarity, unsupported additions, latency, and raw
  persistence remained within their frozen gates.

## What is not established

- open-domain semantic parsing or general multilingual translation;
- robustness to paraphrases or constructions outside the five rule families;
- acoustic tone, pause, prosody, or other speech evidence;
- communicative intent, desired response, felt understanding, or human-like
  cognition;
- same-model superiority, human preference, independent replication, or
  production readiness.

The reserve is author-constructed, not independently authored, professionally
translated, or human-rated. Slot and atom matching is a transparent proxy and
cannot score errors outside the frozen inventory.

## Next milestone

M34 will use trustworthy literal atoms as observations, not as the final
meaning. It will build a counterfactual pragmatic branch ledger for ambiguous
human messages: literal state, candidate communicative goals, evidence from
the current turn and relationship memory, expected desired-response branch,
observable next-turn prediction, and a bounded alternative. A later user turn
must be able to support or refute the branch and update it without rewriting
the original evidence.

The M34 intervention test will keep the current utterance fixed while changing
only the valid prior context. Success means the system changes its selected
response mode and prediction for a traceable reason; failure means it merely
rephrases the same literal answer, ignores relevant history, or overcommits to
an unverified mental-state claim.
