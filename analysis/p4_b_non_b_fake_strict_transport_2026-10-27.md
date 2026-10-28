# P4-B non-B fake strict transport: bounded partial result (2026-10-27)

## Claim and before/after

This is the single-variable continuation of the exact P4-B non-B supervisor
freeze, prospectively amended and independently design-reviewed at `247fd3d`.
It adds an **opt-in, injected fake** W-owned HTTP transport policy. It does not
perform real HTTP, call a model, start a daemon/runner, authorize Safari or
authorize B Send. Public `supervise_once()` remains fail-closed.

| Evidence | Before (`247fd3d`) | After this slice |
|---|---|---|
| Supervised W transport | 7 injected callback results; proxy/redirect were callback *claims* | 7 W-owned `Request` objects through injected fake opener; empty proxy handler and denying redirect handler installed-inventory checks before/after each fake exchange |
| Ordered transport subproof | no v3 schema/proof; positive v3 red test failed at unknown `fake_opener_factory` keyword | W v3 summary and parent independently rehash seven received request/grant/result rows; `transport_gate_proven=true`, `transport_policy_calls=7` only on matching proof |
| Failure behavior | v1/v2 callback contract only | v3 failure receipt keeps fixed code and `transport_gate_proven=false`; R-only later failure does not erase an already-proven W subverdict |
| Resource boundary | 123 pipes / 246 reserved IPC endpoints in port-enabled v2 | same 123 / 246 and same eight children; no additional pipe or process |

The positive fake test observes seven unique opener markers, the existing six
identity observations, an op7 spent bit and seven ordered 0600 journal entries;
the run directory is 0700 and the v3 R receipt is 0600. The v3 result and
receipt keep `physical_stop_unproven=true`, `full_gate_pass=false`,
`b_send_authorized=false` even when the fake subproof passes.

```text
W builds exact loopback Request + empty-proxy/no-redirect policy
  -> D durably acknowledges one-use issue
  -> injected fake opener returns bounded bytes (no socket)
  -> W sends raw-free result hash
  -> P rehashes seven received request/grant/result rows
  -> R writes independent 0600 success/failure receipt
  -> fake-only subverdict; live release remains NO-GO
```

## Verification and preserved failures

- Before source wiring, the new v3 positive was red: `_supervise_fake_seven_once`
  rejected `fake_opener_factory` (`TypeError`). That proves the new tests did
  not merely exercise the old callback path.
- `PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -s
  -p no:cacheprovider test_p4_b_non_b_parity_live_operator.py -k
  test_fake_seven_transport_v3`: **42/42 pass**, 237 deselected. Controls
  include no-socket sentinels; proxy/redirect/3xx-handler tamper before and
  after; request, nonce, URL, status, body-size faults; blocked fake opener at
  each of seven ordinals; raw stdout/stderr canary; missing/corrupt W summary
  and received result-frame mutation; R receipt failure; old v1/v2 positives;
  FD cap, exact 2 MiB response and >256 KiB request boundary.
- Full operator file: **279/279 pass** in the same `-s`/no-cache mode
  (independent read-only reviewer). Eight affected files, same mode: **529/529
  pass in 70.37 s**. Compile and `git diff --check` pass. This is test runtime,
  not product latency.

  ```sh
  PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -s -p no:cacheprovider test_p4_b_child_local_identity_fixture_v2_preflight.py test_p4_b_child_local_identity.py test_p4_b_isolated_ollama_identity_probe.py test_p4_b_non_b_usage_parity.py test_p4_b_private_zero_turn_operator.py test_p4_b_child_local_identity_sandbox_preflight.py test_p4_b_ps_free_identity_feasibility_probe.py test_p4_b_non_b_parity_live_operator.py
  ```
- A first positive failure was the synthetic preparation slack producing a
  fake timeout above 2 s; W now caps this fake per-call timeout at 2 s while
  also respecting remaining work/grant time. A raw-output control then found
  inherited Python stream wrappers bypassed numeric fd redirection; W v3 now
  redirects both layers. Independent patch review found a competing custom
  `http_error_302` handler gap; handler inventory now rejects it, with a
  negative test. These failures were not hidden by weakening assertions.
- Pytest's default output capture initially caused an early FD-reservation
  failure in both the new positive and unchanged v2 positive under this Mac's
  soft 256-FD limit. The same tests pass with `-s -p no:cacheprovider`; no
  resource limit or production gate was relaxed. Default-capture behavior is
  **not** evidence of product failure or of a higher live FD ceiling.

The new v3 controls used **0 real HTTP sockets, 0 provider/model calls, 0 paid
tokens, 0 Safari sends, 0 B sends**. Their sentinels prohibit socket object
creation, connect/connect_ex and stdlib real opener paths. Synthetic fake
output is not a fresh model-quality result.

## Exact evidence boundary and next gate

Independent read-only patch review: **GO for this fake-only v3 slice**. A fake
opener can still ignore the supplied handler policy; no actual proxy bypass,
redirect behavior, network bytes, installed model/source identity, physical
cleanup within T0+90, Safari graph, full-pipeline response, strong-LLM lift
or human judgment was measured. Thus this report does not release committed-
source live preflight or one real attempt.

The next necessary same-card work is to close the remaining frozen fake matrix
(blocked hash/readiness/observer/journal/cleanup and source/model/runner
identity witnesses), obtain independent review, then perform read-only
committed-source preflight. Real HTTP/Safari/B Send need a **separate** live GO.
Do not reclassify these tests as formal temporal holdout or complete the Goal.
