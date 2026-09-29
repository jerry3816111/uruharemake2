# M46 reviewer necessity ablation: first generation call failed

## Frozen boundary and observed result

- Freeze commit: `2d522885b939cdb9a3dfd6d8bf4a2786527b6f31`; runner commit: `e3c1c11c2180d6c7f617e5ec72c7162f26744ee8`.
- Preflight passed for the frozen 6 source-only cases, 9 challenge packets, local `qwen3.5:9b` digest, Apple M2 Pro/32 GB, and unchanged implementation hashes. This is environment/contract evidence, not model-quality evidence.
- The one-shot `generate` phase prewarmed successfully (`4.34145s`). Its **first and only** scored M51 call completed in `17.63697s` with `462` prompt and `360` completion tokens. JSON parsing failed: `Unterminated string starting at: line 19 column 17 (char 712)`.
- The response ended inside the second candidate's `effect` string. Its completion-token count equaled the frozen `num_predict=360` cap; a binding output cap is the most direct explanation for the truncated JSON. This is one observed case, not a measured general failure rate or proof that increasing the cap would pass the `20s` product gate.
- The runner wrote `generation_call_failed_partial_no_resume` and stopped: completed generated batches `0/6`, scored generation calls `1/6`, retries `0`, reviewer calls `0`, gold labels `0`. The artifact SHA-256 is `3b9556db4b337bd0ccef3305b108d1c53a9742884178cf81812e0d41dc171446` at `analysis/p4_m46_reviewer_necessity_generation_2026-09-30.json`.

## What this does and does not show

The frozen A-versus-B reviewer comparison is **INCONCLUSIVE / NOT RUN**. It gives no evidence that M46 review is worth its cost, that bypassing it is safe, or that either arm can deliver an action. The actual observation is an upstream, parseability failure of the existing two-candidate M51 packet under its frozen 360-token budget. The full product remains fail-closed; there was no Safari run, long-term-memory write, product runtime change, or external deployment. The fixed hand-authored challenge packets were not sent to the model and cannot be reported as natural M51 output.

The test was not resumed or rerun on the remaining five cases. The frozen source, model, token cap, scorer, and thresholds were not altered after seeing the response.

## Next design decision, not a retroactive repair

Keep this one-shot result intact. To answer the reviewer question with the least additional confounding, first review whether to preregister a **separate fixed-challenge-only** study: replay the already frozen 3 valid, 5 reviewer-challenge, and 1 guard-control packets; make at most 8 eligible M46 calls; compare A/B on those controlled packets only. A positive result would show bounded discrimination on hand-authored errors, not natural-generation usefulness or product eligibility. If that succeeds, separately decide whether to change **one** M51 generation resource/representation variable on new sources and re-measure tokens plus end-to-end latency; a larger cap may worsen the `20s` limit. If controlled M46 review fails, retain fail-closed behavior and reconsider the reviewer architecture before spending on generator expansion. Any new scored run requires a new prospective freeze and one-shot runner; this failed artifact must not be rewritten.
