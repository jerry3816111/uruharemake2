# P3-B45 prospective v3 immutable execution contract acceptance

Date: 2026-09-17

## Outcome

**PASS for zero-call execution-contract and checkpoint-mechanics readiness.**

The prospective v3 batch now has a fixed 24-step order: three cases in source order, four turns in
each case, and `product_system` followed by `full_history_direct` for every turn. The contract binds
the B44 source digest, the already-committed rubric digest without opening that rubric, the exact
model and generation options, session boundaries, resource limits and the product snapshot.

This stage did not execute UruhaBrain or the direct baseline. A later signed release and a real
runner remain necessary.

## Product and data immutability

- source SHA-256: `8980e85d321d3f3e1997a31be184a47bc4390428f85c92f4a8ef12f266ae011d`;
- committed rubric SHA-256: `c72c648b39a7b149bb75640fea76f1635b248cb6249eb8015d11f9df29e9603f`;
- product snapshot: `0cab07b44aa47adb3866a9ba1aa317b71a5d3091`;
- 107 root-level local Python files reachable from `uruha_web_ui_product.py` were recursively
  discovered from that Git commit and all 107 current bytes matched;
- annotation-file reads during preflight and rehearsal: 0.

The direct baseline remains the same `qwen2.5:7b` model and frozen direct-v2 instruction. Both
conditions retain identical source order and visible-history policy. No post-source product tuning
is allowed before the first v3 run.

## Crash and retry contract

Every actual provider transport must first persist an immutable intent. A complete checkpoint binds
request hash, output hash, exact usage and transport evidence. On restart:

- a valid complete checkpoint is reused without a model call;
- intent without complete is terminal and cannot be recalled;
- transport failure is terminal;
- mutated, unexpected or out-of-order checkpoint state fails closed;
- retry count and fallback count are both zero.

The deterministic fake-transport audit verified fresh 24-call completion, 24/24 complete reuse,
post-complete crash recovery with 5 reused and 19 new calls, intent-only refusal after 4 earlier
calls, and one terminal transport failure that was not retried.

## Verification

- 9 focused B45 tests passed in 31.03 seconds;
- 105 B44/B45/shared comparison tests passed in 62.97 seconds;
- 10/10 preflight checks and 4/4 mechanical-audit checks passed;
- 24 logical condition steps, 12 paired views and 3 declared product restart points;
- 0 real model calls, 0 network calls, 0 paid calls and 0 production database access;
- `git diff --check` passed.

## Claim boundary and next gate

B45 proves that the inputs, product version and recovery policy are fixed and that the journal state
machine behaves correctly under fake failures. It is not evidence that the real product runner
writes every provider-call checkpoint correctly, and it provides no reply-quality or product-
advantage result. B46 must implement and test that real adapter, bind it in a separate release, then
execute the batch once without annotation access.
