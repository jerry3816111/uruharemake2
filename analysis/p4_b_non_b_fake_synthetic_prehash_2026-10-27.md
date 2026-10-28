# P4-B non-B synthetic pre-hash gate: fake-only partial result (2026-10-27)

## What changed and why

At committed `2bc453a`, the seven-operation fake supervisor accepted a
pre-filled binding whose source/model hashes looked valid. No process read
file bytes before W was released. The prospective O-owned amendment was
independently reviewed and frozen at `c972089` before source edits. It changes
one mechanism: an initially witnessed O child now streams a **fixed 23-byte
synthetic file**, sends a strict SHA/count plus port preproof, and P verifies
the composite proof before `W_GO`. D remains durability-only, R has already
preflighted the zero journal, and O/S_O reuse their existing IPC edges.

```text
D zero-count 0600 journal -> R zero-journal preflight
        -> O/S_O initial witness -> O real-byte synthetic SHA
        -> O pre-port witness -> P validates one composite frame + EOF
        -> W_GO -> seven injected fake opener calls -> R 0600 receipt

blocked/wrong/missing hash proof -> no W_GO/grant/HTTP -> R failure receipt
```

The opt-in `fake_prehash=True` requires the v3 injected opener and port
observer. P creates the literal fixture itself in a unique 0700 OS-temp
directory, with a 0600 fixed-name regular file; no caller chooses an input
file or expected digest. O uses no-follow directory/leaf FDs, pinned
metadata before/after, bounded 64 KiB reads, and hashes bytes actually read.
The SHA/count expectation was fixed before implementation:
`2d2078a1d31c931402d626a1321b74731099a9144b32d6aa37e6718c968e95a7`
and 23 bytes. The result/receipt expose only validated hash/count or null,
never a fixture path or contents. V1–v3/default paths stay separate.

| Gate | Before | After the v4 fake slice |
|---|---|---|
| File-read authority | binding hash strings only | O actually reads fixed synthetic bytes; P checks SHA/count before W_GO |
| Blocked read | no pre-hash stage to stall | work stop remains bounded, no W_GO/grant/opener, zero-count journal and R failure receipt when available |
| Error attribution | no pre-stage code | `pre_stage_failure_code` retains the first reason; cleanup/R failure can dominate top-level failure without erasing it |
| Resource topology | 123 pipes / 246 IPC endpoints / eight fake children | unchanged; O has exactly two additional transient file FDs during its read, checked by test |

## Verification and costs

- Red before source: v4 positive failed with `TypeError` because
  `_supervise_fake_seven_once()` had no `fake_prehash` keyword.
- New v4 focused controls: **29/29** (derived from 558 affected tests minus
  the prior 529; the final affected suite includes every v4 control). They
  verify hash/port/proof/W_GO order; seven fake sends; six worker observations;
  op7 spent; 0700/0600 artifacts; same-length changed bytes; same bytes at a
  different inode; symlink, hardlink and >1 MiB file; malformed, wrong and
  extra-wire composite proofs; O/S_O initial and abnormal exit; blocked read
  and blocked cleanup witness; R failure after both valid and blocked hash;
  printed/raised raw canary; FD cap; and v1–v3 schema isolation.
- Eight affected files, unchanged source fixtures and no pytest FD capture:
  **558/558 passed in 79.38 s**. Command:

  ```sh
  PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -s -p no:cacheprovider test_p4_b_child_local_identity_fixture_v2_preflight.py test_p4_b_child_local_identity.py test_p4_b_isolated_ollama_identity_probe.py test_p4_b_non_b_usage_parity.py test_p4_b_private_zero_turn_operator.py test_p4_b_child_local_identity_sandbox_preflight.py test_p4_b_ps_free_identity_feasibility_probe.py test_p4_b_non_b_parity_live_operator.py
  ```

- Independent read-only patch review found a v1–v3 strict-schema regression:
  newly added v4 failure codes had initially been accepted by old receipt
  validators. They are now gated to v4, with a direct rejection test. Review
  gave **GO only for this fake partial**. `git diff --check` is clean.
- Runtime/cost observations are **test** costs, not product latency: the
  focused fake span is a few seconds under a shortened synthetic deadline;
  the affected suite took 79.38 s. Reserved IPC stays 123 pipes / 246
  endpoints, eight fake children; O's hook observed an exact +2 transient
  file-FD delta between before-open and before-first-read. There were zero
  provider HTTP sockets/calls, zero model tokens, zero Safari sends,
  zero B sends, and no private model/production DB input. Synthetic failure
  artifacts are 23-byte files; any retained ones are not formal evidence of
  a live stop guarantee.

## What this cannot prove, and next gate

This is a supervised **synthetic control-path** test. It does not hash the
real 4.4 GiB model store, prove exactly one pre and one post validation,
authenticate installed source/binary/GGUF, start or check a daemon/runner,
prove physical cleanup by T0+90, exercise Safari, or compare model quality.
`physical_stop_unproven=true`, `full_gate_pass=false`, and
`b_send_authorized=false` remain fixed; public `supervise_once()` is still
  fail-closed. No provider HTTP/model, real daemon/runner, Safari or B Send is
  authorized.

The next necessary same-card gate is an independently frozen, single-variable
fake readiness/source-identity stage placed before any worker grant, with
blocked/crash/identity-drift controls and receipt/cleanup proof; only after
the full fake matrix and a committed-source audit may a **separate** live
preflight/release decision be considered. Do not promote this result to
temporal holdout, human judgment, the human-response equation, or product
completion.
