# M55 Real-Person Longitudinal Pilot Readiness · 2026-09-01

## Decision

**Pre-content readiness: PASS. M55 real-person pilot: BLOCKED. M56: NOT AUTHORIZED.**

This is a real evidence boundary, not an implementation excuse. Equation V1 is valid, the three
official Uruha calibration sources have publication dates, the 30 content-free target slots are frozen,
and all sealed future sources are excluded. The missing evidence is human observation: the prerequisite
V7 ledgers remain 0/18 and 0/18, no independent reliability result exists, and the Uruha target lane
therefore remains 0 coded events and 0 human coders.

## Why the earlier V7 step is necessary

M55 must label observable behavior consistently before fitting or judging the equation. If only one
person decides what counts as a context, action, relationship signal, or ambiguity, a model may appear
accurate merely because the same subjective interpretation built and scored the data. V7 tests the
codebook on 18 frozen slots from contrast people before anyone is allowed to code Uruha's 30 calibration
slots. The gate requires two distinct people, independent ledgers, mean temporal IoU at least 0.5, and
every primary nominal Krippendorff alpha at least 0.667.

Two people are enough for this gate; it is not a large participant study. Model-generated or copied
labels cannot count as the second person. Synthetic tests establish that the tooling computes the
statistics, not that real people agree.

## What Codex completed now

- joined the M54 Equation V1 contract to the frozen V7/V9 source and reliability chain;
- verified hash-bound pre-content artifacts, three dated official target sources, 30 balanced target
  slots, and zero sealed-future sources in the frame;
- measured live private-ledger progress without copying their contents into Git or the report;
- added a fail-closed rule that refuses M56 when human reliability or target events are absent;
- added an outsider-readable graphical gate: M54 → V7 → V9 → M55 → M56;
- started isolated local sites for coder-01 and coder-02. Safari currently shows coder-01 at 0/18;
  coder-02 must be completed by a different person on the same Mac and neither answer set is visible to
  the other.

## Current counts

| Evidence | Current | Required before M56 |
|---|---:|---:|
| Equation V1 contract | pass | pass |
| Official Uruha calibration sources | 3 | 3 |
| Frozen Uruha calibration slots | 30 | 30 |
| Sealed future sources in frame | 0 | 0 |
| V7 independently completed ledgers | 0/2 | 2/2 |
| V7 completed slots | 0/18, 0/18 | 18/18, 18/18 |
| V7 reliability result | unavailable | preregistered pass |
| Uruha independently coded calibration events | 0/30 | 30/30 |
| Uruha human coders | 0 | 2 |

## Claim boundary

This checkpoint proves that the data gate is explicit, reproducible, future-isolated, and not silently
filled by a model. It contains no real-person behavior labels and therefore cannot support Equation V1
validity, persona similarity, human understanding, LLM advantage, or M56 model comparison.

## Exact continuation

1. coder-01 and a different coder-02 independently complete the same frozen 18 V7 slots;
2. run and freeze the existing V7 reliability analyzer;
3. if reliability fails, revise the codebook only, preserve both original ledgers, freeze a new pilot,
   and retry without touching Uruha target data;
4. if reliability passes, unlock the existing V9 two-coder site and code the 30 frozen Uruha slots;
5. only after 30 independently reviewed target events exist may M55 build cutoff→future rows and allow
   M56 B0–B5/Ours model execution.
