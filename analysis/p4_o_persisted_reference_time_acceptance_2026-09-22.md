# P4-O Persisted Reference-Time Acceptance

Status: **PASS OFFLINE ONLY**

## What changed

The failure was not lost memory. P4-J created a private default time for its first
validity read, while P4-N later reused the caller's original `None` for a second
persisted read. `uruha_persisted_reference_time_p4.py` now creates one effective
time before entering P4-N and passes that exact value through the complete path.

The fix is additive. Released P4-N files were not rewritten:

- P4-N adapter SHA-256 remains
  `bd7389af47aa62b69571f1e9382c1d362c277a417bd2e5c265c4b302d6339ec8`.
- Released product entry SHA-256 remains
  `842169743c3c8d8cc0d0c9e6d0747690b08add7e7aa8709b287f00f909e9e694`.
- The new opt-in entry is `uruha_web_ui_product_p4_o.py`.

## Before / after evidence

The frozen development value was `ごぼう茶`, written by the real typed writer
to a new temporary `chromadb.PersistentClient` collection.

- Before: the record count was one, but omitted `reference_time` produced
  `ValueError: reference_time must be an ISO datetime or datetime instance`.
- After: the same frozen input returned
  `今の飲み物の好みはごぼう茶。前のじゃなくて、今の方ね。` with
  `bounded_japanese_identity`, the same active memory ID and no record mutation.
- An explicit caller time reached the complete path byte-for-byte.
- A record was answerable before `valid_until` and unavailable immediately after it.

## Verification

- P4-O dedicated: **6 passed, 0 failed**.
- P4-I through P4-O affected regression: **45 files, 196 passed, 0 failed**.
- Isolated product-entry import: imported, reused the released runtime, and installed
  `uruha_persisted_reference_time_p4.build_with_persisted_reference_time_p4`.
- Model calls: **0**. Paid API calls: **0**. Product turns: **0**.

Two invalid environment attempts are retained in the JSON result. One lacked
`colorama`; one prepended an incompatible system `peft`/`transformers` pair. Neither
reached test execution and neither is counted as a pass or functional failure.

## Rejected edits retained

The first direct edit fixed behavior but changed the released P4-N adapter hash
(`55 passed / 2 failed`). The second additive install changed the released product
entry hash (`50 passed / 1 failed`). Both edits were reverted, were never committed,
and did not cause old evidence hashes to be rewritten. The accepted architecture is
a new adapter plus a new product entry.

## Claim boundary

This closes one deterministic integration defect offline. It does not yet prove
Safari delivery, arbitrary/open-domain recall, long-dialogue reliability, felt
understanding, advantage over a strong LLM, or the proposed human equation. A new,
separately frozen value is required for P4-O-REAL; the failed `そば茶` case is not rerun.
