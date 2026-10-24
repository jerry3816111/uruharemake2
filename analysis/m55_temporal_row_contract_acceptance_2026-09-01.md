# M55 Temporal Row Contract Acceptance · 2026-09-01

## Decision

**Temporal-row engineering gate: PASS. M55 real-person pilot: still BLOCKED. M56: NOT AUTHORIZED.**

This milestone closes one necessary engineering gap without manufacturing human evidence. It freezes a
machine-checkable boundary between what the predictor may see and the observable behavior that only
becomes available after the prediction. The live human evidence remains zero.

## The validity gap found

The frozen V9 event record has a whole-event start and end, but that is not enough for prospective
prediction. An event may already contain the target person's response. Relabeling the event start as a
prediction cutoff would therefore let the answer leak into the input.

The downstream M55 row now requires four separate fields:

1. `observable_input_start_seconds`;
2. `prediction_cutoff_seconds`;
3. `observable_behavior_start_seconds`;
4. `observable_behavior_end_seconds`.

Their order must be:

```text
event start <= observable input start < prediction cutoff
prediction cutoff < observable behavior start < behavior end <= event end
```

The audit correctly reports that the current V9 record alone is not compilable and that these four
fields require a separate boundary extension. V7/V9 frozen schemas, slots, ledgers, result locks, and
human thresholds were not changed.

## What was implemented

- `configs/m55_temporal_row_contract_v1.json` SHA-binds Equation V1, the event schema, V6 behavior
  codebook, V9 sampling frame, V9 source metadata, and V9 result lock.
- All nine Equation V1 variables have an explicit observable, pre-cutoff-derived, or unavailable
  status. `transient_state` and `goal_need_state` remain unavailable rather than being guessed.
- `m55_temporal_row_contract.py` validates an explicitly supplied private record pack and compiles it
  into the existing temporal-dataset schema. It does not read public media or private ledgers by
  default.
- Unexpected fields, raw/verbatim payload keys, invalid or overlapping boundaries, unrecognized
  labels, false attestations, and fake human review fail closed.
- Only completed earlier outcomes may enter history. The current row's outcome remains hidden from
  the current model view.
- Synthetic fixtures can test the compiler but set both model execution and formal target claim to
  false. Real-row compilation is refused until the actual V7 and V9 human gates pass.
- The readiness audit now includes a separate `30/30 cutoff -> future rows` gate and serves a read-only
  local visualization of `observable input X -> locked cutoff -> unseen behavior Y`.

## Evidence

### Deterministic and contract evidence

- contract: PASS;
- bound artifacts: 6;
- Equation V1 variables crosswalked: 9;
- required record fields: 22;
- focused plus compatibility suite: **46/46 passed**;
- Python compilation and `git diff --check`: PASS.

The first attempts with the system Python 3.14 and the bundled workspace Python could not start pytest
because pytest was absent in those environments. The project test environment at Python 3.12 was then
used; this is an environment-selection miss, not a failed or passed research test.

### Synthetic compiler evidence

- synthetic rows: 2;
- temporal history rows: 2;
- checked prior-history references: 1;
- future leakage violations: 0;
- current-outcome-summary leaks: 0;
- dataset hash: `39c29b28c4013035f456b7141598a4ddc036129354162c2d0b7851eb61dd1f23`;
- audit hash: `1187a54107ae898ac31b06d337a3be151e1de420ed963f0e278602cebc247c27`;
- model execution authorized: false;
- formal target claim: false.

This proves the compiler contract only. It is not a human label, a prediction result, or evidence of
Uruha similarity.

### Live readiness evidence

- pre-content readiness: PASS;
- V7 ledgers: 0/18 and 0/18;
- V9 independently reviewed target events: 0/30;
- valid real temporal prediction rows: 0/30;
- sealed-future sources in the target frame: 0;
- M55 real-person pilot complete: false;
- M56 authorized: false;
- active blocker: `complete_two_independent_v7_18_slot_ledgers`;
- readiness report hash: `1cf31879f06d72dc36b5283a1cbb966a44621a6c17e6218bc60911ac188d0fa2`.

### Safari graphical evidence

The local read-only page was opened in Safari and visually checked at
`http://127.0.0.1:7903/temporal`. It showed the three-part X/cutoff/Y flow, all nine variable cards,
contract PASS, current V9 alone not compilable, zero real rows, and M56 forbidden. An existing blank
tab was reused, so no tab was added or closed. No private record, source URL, or session token appears
on the page.

## Remaining limitation and exact continuation

Attestations and field validation cannot by themselves prove that a human paraphrase semantically
contains no outcome hint. Independent human coding and review remain necessary. The next safe
engineering unit is a private, two-coder boundary-extension collection instrument that writes the four
new timestamps without modifying frozen V9. It may be prepared and tested with synthetic fixtures, but
must not consume Uruha target content until V7 reliability passes.

After two distinct humans pass V7, the same independent method may code V9 and the boundary extension.
Only 30 independently reviewed, leakage-free temporal rows may complete M55. A separate preregistered
M56 protocol is still required before any model comparison.

## Claim boundary

This pass supports only: machine-checkable prospective row boundaries, explicit Equation V1
missingness, deterministic compilation, and fail-closed leakage checks. It does not validate Equation
V1 on a real person, infer private mental states, prove a biological human-brain equation, establish
persona equivalence, or show an advantage over a language-model baseline.
