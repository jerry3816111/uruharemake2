# P4 browser-bound graph hydration: prospective product freeze

Status: **preimplementation**. The exposed G0–G3 Web evidence-delivery
batch remains whole-batch **strict FAIL**; T/N/Q/S results also remain FAIL.
Do not replay any old question or relabel its judgment after this change.
This is a developer-authored Web product probe, not formal holdout evidence.

## Before, causal target, and one core variable

In G0/G2, final Safari visibly showed the genuine bounded-slot ledger,
rewrite/recall/terminal nodes and six native arrows (2/2), but pressing
reload produced an empty graph (0/2). Read-only code inspection shows
`build_demo()` computes `flow_html` once at server construction; there is no
page-load callback. `_observatory_result_from_log_record` can render the
private row offline, but that never reaches the reloaded page. G1/G3 reveal
separate actor/unsupported-route reply defects and are **not** this fix.

**Only changed core variable:** on page load, hydrate the current browser's
last delivered graph from the latest private same-run log row, authorized by
a browser-bound signed receipt. The semantic ledger, reply generation,
source/actor policy, M31/M32, memory write, model settings and renderer
verification remain unchanged. Chat bubbles/history are not restored.

The security reason for the receipt is concrete: graph `USER SIGNAL` contains
raw `user_text`. Server-global latest-row and runtime-session checks alone
would expose one browser's dialogue to another browser on localhost. In
Gradio 6.5.1, `BrowserState` persists within a browser across reload. On
final text/audio delivery only, save a compact `{schema, session_id,
turn_index, mac}` receipt to BrowserState; HMAC-SHA256 uses a process-only
random key over the exact latest JSONL record. No raw episode, HMAC key, or
full graph is newly written into browser state; the signed receipt does not
grant access to older turns. Initial HTML is always empty. A page-load
callback reads **only the last row** of an owner-owned 0700/0600 regular
one-link JSONL; requires the browser receipt, current runtime session and
turn index, intact row MAC, and existing witness/source verification; then
returns its graph. Missing/forged/stale receipt, modified/incomplete latest
row, nonprivate/symlink/hardlink log, old session or reset must return an
empty graph. It must **not scan backward** to a previous positive. A latest
negative may show its own old verified producer graph but **zero** new
ledger/action nodes, not a stale prior positive.

The HMAC key is a separate process-only secret, **not** Gradio's
`BrowserState.secret` (frontend-visible storage machinery). Gradio 6.5.1
does not save falsy BrowserState values, so reset must overwrite with a
truthy, explicitly unauthorized tombstone, not `None` or `""`. Reset joins
the same Gradio human-turn concurrency lane. A pending text/audio send also
carries its enqueue-time runtime session ID; a late final cannot mint a
receipt if reset changed that ID. This protects the browser receipt, not
the whole global conversation runtime against multiple simultaneous users.

This is a localhost single-user product boundary and an accidental
cross-browser-display guard, **not** multi-user authentication. Same-origin
tabs may share browser localStorage; a program restart invalidates the
process-key receipt and leaves reload blank. Other global runtime/debug
surfaces are not made multi-user safe. No external deployment.

Allowed changes: `uruha_web_ui.py`, a focused hydration contract test,
this plan, paired dataset and SHA manifests, top of `CURRENT_TASK.md`,
and a result report. Existing ledger/renderer, generator brain, protected
route, formal DB, G/T frozen artifacts and thin product entry/controller
are outside scope. A small UI wrapper may append BrowserState output to
text/audio final delivery without changing existing public handler arities;
all partial yields must skip receipt updates. Reset clears browser receipt;
proactive/failed/empty turns never mint one.

## Frozen H0–H3 probes and gates

The paired JSON freezes one fresh isolated same-PID Safari session. H0/H2
are supported quote-rewrite + past-place positives with distinct inner/
outer dates; H1 is direct-User source and actor control; H3 is unsupported
`検討中` negative. These strings, dates and place were checked against prior
dataset JSON before implementation (exact collisions zero). H0 must give a
dated honest unknown; H2 must use **only** H1's direct User place. Supported
quotes retain the exact date and pending state. H1 must not transfer User
`私` to Uruha `うち`. H3 gets no new ledger/terminal authority or added model
call, and its ordinary reply still must not assert quoted content as fact
or omit H1 recall. Known G failures do not soften these gates.

After each single send (zero retries), observe the final Safari bubble and
the actual colored graph, then reload the *same browser*. H0/H2 must show
the current EVENT→M31→M32 plus distinct ledger/rewrite/recall/terminal
nodes and six native `is-atomic-delivery` arrows **both final and reload**.
H1/H3 must show zero new ledger/action nodes/arrows both times, and after
reload the producer EVENT must belong to that latest H turn, never H0/H2.
A second fresh browser context with no receipt must show no previous private
graph. Graph raw-episode text must not be newly exposed. Record Safari
screenshots and AX as actual local artifacts if the UI tool supports it;
otherwise mark the frozen saved-visual gate unmet, never call tool output a
stored PNG.

Bubble, raw reply, final guard, blackboard utterance, RightBrain history
where independently available, and isolated SQLite episode must be checked
per turn. Profile remains zero facts; unique episode IDs grow 0→4 after
T0_ready. Preserve source, actor, quote, retraction and protected boundaries.
Each delivery-complete User wait ≤20.000 s; H0/H2 constrained realization
adds zero model calls/completion tokens, and hydration adds zero. Record
actual per-turn latency, raw SHA, log/witness bytes, receipt size, graph HTML
size, page-load time and available token receipts. Full-system tokens cannot
be inferred if not instrumented. Any content, safety, graph, storage,
privacy, latency or cost gate failure makes the **whole batch strict FAIL**;
report any narrower graph success separately.

## Verification order and stop rule

First check exact dataset collisions, before-code SHA, precise Git status,
then commit/push the frozen plan/dataset/manifest and PR head. Implement
only the one variable. Zero-model contracts must cover BrowserState wiring
and final-only receipt for text/audio, reset/empty/proactive skip, correct
same-browser latest reload, absent/forged/old receipt, tampered/truncated
latest row, nonprivate/symlink/hardlink log, stale-positive non-revival and
no raw witness in browser receipt. Run focused and affected neighboring
regressions, including reset-during-inflight/queued-send rejection and a
real Safari reset→reload check that the tombstone replaced the receipt.
Compile/diff review and product SHA precede commit/push and model use.
Then create a **new** launcher-owned 0700 root: 0-turn same-PID HTTP ready/
planned stop, official-SHA private offline ONNX prewarm, explicit empty
T0_ready profile, one new Safari tab and H0–H3 in order. Save per-turn
DB/profile and UI evidence; planned-stop only owned PID and close only our
new tab. Do not revisit H cases to chase a pass. At most two reasoned fixes
for this item; persistent failure becomes `REVIEW_REQUIRED`, not silent
contract relaxation.

This is a necessary visual product interaction. It cannot prove general
human pragmatic understanding, strong-LLM superiority, human preference,
temporal prediction, full VRM/Function Calling integration, or completion
of the long-term Goal.
