# P4-B M21 text-turn fail-closed — prospective freeze

## Before evidence and scope

At committed HEAD `d38fc37`, the B gate now records a post-admission
pre-SDK identity failure, but `LeftBrain.think` catches every M21 exception
and returns a normal fallback plan. A zero-model isolated Brain reproduction
with a fake `P4BResourceGateError("prompt_upper_bound_unavailable")` returned
the visible Japanese reply `どの選択を捨てたくないのか、まずそこから整理しよ。`,
reported `error_fallback`, and saved **one episode**. That is a real
source/fake counterexample to B whole-turn fail-closed, not a true B Send.

Separately, `_submit_text_impl` currently emits a pending assistant `"..."`
before `_run_turn`; a fake `_run_turn` exception then propagates without a
final UI cleanup update. Thus merely re-raising M21 would leave a misleading
pending role bubble. The fixed B child sets a private boot state before Web
import and owns the same gated compute ledger; ordinary non-B Web/Brain
behavior must remain unchanged.

The **single product variable** is B-only text-turn failure propagation and
surface cleanup. The validated private mode must be passed from the Brain
constructor into LeftBrain independently of the mutable gate reference; if a
B gate is removed/replaced mid-turn, M21 must still rethrow the resulting
exception instead of entering fallback. A gate-bearing test LeftBrain also
rethrows. The exception must propagate through `run_turn_debug` before
`emit_response_if_ready` and `save_episode`; B rethrow happens before the
existing `print(...{exception})` so private details are not newly logged.

In the fixed B Web state, text submission must add **no new assistant bubble**
during pending or terminal failure (old history may already contain assistant
turns). On a B turn exception it must restore the exact original history and
unstripped input message, clear pending debug/graph/memory/state, show a fixed
generic non-role status without exception text, and return existing terminal
status `error`. Successful B text submission must preserve its new user row,
append exactly one assistant row, and stream the real reply. Existing
exact-input rejection takes priority if both arms are present. Non-B M21
fallback and Web pending/streaming behavior stay unchanged.

Allowed product files: `uruha_brain_mac.py`, `uruha_web_ui.py`. Allowed tests:
one new `test_p4_b_m21_text_turn_fail_closed_zero_model.py` and, if the
constructor kwarg needs assertions, `test_p4_b_private_constructor_seam.py`.
This freeze,
one result note, `CURRENT_TASK.md` may change. Do not change gate/admission,
token oracle, B controller, prompts, persona, memory implementation, formal
data, baseline, or frozen historical results.

## Predeclared acceptance and negative controls

1. Red-before/green-after isolated M21 tests: gated errors (at least gate
   denial and private binding/identity error) propagate as their original
   types under private mode, even if the gate reference drops/swaps after
   construction; no fallback plan or episode/final reply. A gate-bearing
   test planner without constructor mode is also conservative. Non-B identical
   fake transport/model error retains ordinary `error_fallback` and episode.
2. In an isolated fake Brain→`web._run_turn` path with private 0700 log dir,
   thrown M21 failure produces a raw-free `terminal_error` compute receipt
   with zero provider calls; private failure file is 0600; no conversation
   JSONL and no saved episode. In an unsafe/unwritable log dir, do not claim a
   written receipt. This file's append/close is not crash-durable fsync proof.
3. In a fake B text UI generator, pending and final failure updates have no
   **new** assistant row; prior history (including an old assistant) and the
   exact unstripped input are restored, pending debug/graph/memory/state is
   cleared, fixed generic status appears, and `finish_human_turn` runs once
   with terminal `error`, not delivered. Run through
   `submit_text_browser_bound`/`_with_browser_graph_receipt` and assert all
   updates have the 14-field browser shape and a safe graph-receipt slot.
   A successful B fake path still preserves its user row and streams exactly
   one actual assistant reply. Non-B pending `"..."` and ordinary behavior
   stay as before, including a non-B `_run_turn` exception still raising.
   With both B and exact-input arms present but no valid permit, the existing
   exact-input rejection must occur before B pending/turn handling. Do not
   test this as native Safari.
4. Run focused tests, adjacent M21, Web compute/attribution/submission tests,
   syntax and diff checks. Zero real Ollama, Web service/Safari Send,
   production DB, download, deployment and human evaluation. Review exact
   paths, preserve unrelated `output/graduate_application_report/`, scoped
   commit/push PR #435 and verify exact head.

This is a fake/contract B **text** fail-closed gate, not full product release.
The Web compute-failure writer is best effort; a successful append in a
validated private directory is not crash-durable proof. The Brain may already
have updated transient state or queried memory before M21, so this is not a
whole-turn state rollback. A failure after `emit_response_if_ready` may have
already written an episode; the zero-episode claim applies only to thrown M21
errors. Audio, other non-M21 B failure routes, post-response gate terminals
(including missing provider usage), production token bound, true
daemon/runner identity, full source/effect closure, 20-second Safari delivery
and A author ratings remain separate.
