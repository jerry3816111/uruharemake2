# P3-B51 temporal forecast bridge acceptance

Date: 2026-09-17

## Decision

**Protocol bridge: PASS. New source selection: NOT STARTED. Formal model execution: BLOCKED. Formal result: ABSENT.**

The 2026 related-work review did not justify a second forecasting runner. The already frozen M55/M56 stack contains the necessary temporal and fair-comparison machinery. P3-B51 makes that equivalence executable and fail-closed instead of relying on a narrative similarity claim.

## Exact mapping

| New Task A role | Existing frozen condition |
|---|---|
| Current context only | `B1_BASE_LLM` |
| Static persona prompt | `B2_PERSONA_PROMPT` |
| Retrieved pre-cutoff public history | `B3_RAG` |
| Same-information strong control | `B5_STRUCTURED_HISTORY` |
| Full explicit person-state system | `OURS_HYBRID` |

The primary comparison remains B5 versus Ours because both receive the same pre-cutoff source information. The intended difference is explicit memory/state/relationship/need/person-parameter/uncertainty/transition processing, not extra facts.

## What the executable audit checks

- the M55 temporal row contract, M56 preflight, blinded capsule freeze, pre-outcome equation artifact contract, and 2026 literature map are content-addressed;
- `prediction_cutoff < observable_behavior_start` and current outcomes cannot enter generation;
- all prediction rows are committed before a separate scorer can join outcomes;
- B1 through B5 and Ours use the same model artifact, no retry/fallback, and report actual prompt/completion tokens, latency, and peak memory;
- Brier and negative log likelihood remain co-primary proper scores;
- the same-information B5 versus Ours comparison cannot be weakened to a less informed control;
- unknown private states cannot be imputed as truth and negative results must be retained;
- this bridge authorizes no model call, target-outcome access, source selection, production-memory write, or deployment.

## Evidence

- Bridge plus directly affected M55/M56 suites: **75 passed**.
- Audit: **14/14 checks true**.
- Mapped conditions: **5**.
- Primary 2026 sources pinned in the bridge: **6**; the full non-exhaustive map contains 10 works.
- Formal model calls: **0**.
- Target outcome access: **0**.
- New public source selected: **false**.
- Formal result created: **false**.
- Audit hash: `960c9eb9e916f094e9d47406b27a47156b2c5eac7619d999b2912a0831816059`.

Adversarial tests reject a remapping that substitutes the weak B1 control for B5, any bridge-level attempt to authorize generation or outcome access, an incomplete literature provenance row, and a stale dependency hash.

## 2026 literature use boundary

The cited papers support module choices and evaluation diagnostics: long-dialogue drift and cost reporting; stable/accumulated/transient state separation; memory anchoring/selecting/bounding/enacting; temporally blind anticipation; and factor-level rather than holistic human-likeness measurement. Their published results are not evidence for UruhaBrain's performance. The related-work search also does not establish world-first priority.

## Next gate

Prospectively select and freeze one new public source using metadata and a deterministic rule without opening the target future response. Only after that freeze may a separate step define the observable-context cutoff and later unlock the response for scoring. Existing formal M56 human/reliability gates remain unchanged; B51 does not bypass them.

