# P4 final/reload graph evidence delivery: prospective freeze

Status: preimplementation design and developer-authored product probe. The
previous semantic-ledger T0–T8 Safari batch remains **whole-batch strict
FAIL**. Its raw output and frozen judgments are not to be replayed, repaired,
or reclassified as a new pass.

## Before evidence and single attributable intervention

T0/T2/T4/T6 returned a final source-bound two-act terminal receipt and
bounded correct visible content, but the *final* Safari node graph showed only
EVENT→M31→M32 (three nodes/two arrows), never the new ledger/action graph.
`uruha_web_ui._run_turn` initially renders from the full brain turn, which
contains the actual `episode_doc`. `_finalize_surface_delivery` then replaces
that HTML using an `observatory_result` without `episode_doc`; the renderer
intentionally requires the saved episode's final utterance and fails closed.
The log-reload constructor also drops already-logged `logic` and lacks the
episode witness. This is a Web evidence-delivery defect, not proof that the
renderer or source-bound transaction is wrong. The causal diagnosis is from
read-only code path plus T raw/UI observation; the correction itself has not
yet passed a new Web experiment.

**Only changed core variable:** convey the genuine brain-returned episode
witness through the server-side final graph render and the local log-reload
render, along with already-existing `logic` for reload. The semantic ledger,
renderer verification, source/certificate, actor handling, protected route,
M31/M32, model parameters, memory writes, and final utterance stay unchanged.
No generated or reconstructed stand-in episode is allowed. The local JSONL
may persist `episode_doc` only when the real terminal ledger was delivered;
it is already a private 0600 raw-turn log, but this does duplicate sensitive
User/reply/summary/mood material and must be measured. The episode document
must **not** be added to browser cognition/memory/client-turn JSON or graph
node details. If the witness is missing, inconsistent, or tampered, new
ledger/action nodes must remain absent. No DB readback is newly claimed.

Allowed files: `uruha_web_ui.py`, a focused Web evidence-plumbing test,
this plan, paired dataset, preimplementation/product SHA manifests, result
report, and the top of `CURRENT_TASK.md`. Existing renderer or ledger code,
frozen T files/results, model prompts and DB are not allowed changes. A thin
opt-in entry/controller is reused unchanged. No external deployment.

## Frozen fresh probes, gates, and limits

The paired JSON contains G0–G3 in one new isolated product session. G0/G2
are supported mixed positives with distinct inner quote and outer recall
dates; G1 is a direct-User source and actor control; G3 is an unsupported
quote/negative graph control. G0 must show dated honest unknown, G2 only the
direct G1 User place; all supported quotes keep the exact date/state. G1 must
not turn User `私` into character `うち`. G3 gets no new terminal authority,
model call, or ledger nodes, and its old-path reply still must not falsely
assert quoted content or omit the requested recall. These content/safety
conditions are not weakened merely because the changed variable is graph
delivery. Any visible, actor, source, safety, or latency failure makes the
**whole product batch strict FAIL**; report a narrower graph result separately.

For each supported positive, final delivery **and page reload** must show
native, clickable EVENT→M31→M32 plus distinct ledger, rewrite, recall and
terminal nodes, with **six native `is-atomic-delivery` arrows**; inspect and
save per-turn Safari screenshot/AX evidence rather than substituting a local
renderer reconstruction. G1/G3 must show zero ledger/action nodes/arrows,
including after reload. A reload must display the latest actual turn, not
stale positive data. Never display raw episode text in new node details.

All four cases have one send/zero retries. Bubble, raw reply, final guard,
blackboard utterance, RightBrain history where applicable, and isolated
SQLite `turn_episode` text must match each turn. Profile facts stay zero rows
at T0_ready and after every turn; episode IDs grow 0→4, unique. Preserve
source/retraction/protection boundaries. Delivery-complete User wait must be
≤20.000 s per turn; added mixed rewrite calls/completion tokens remain zero
for supported positives, and Web plumbing itself adds **zero** model calls.
Record actual per-turn latency, available token receipts, raw SHA, saved
episode-witness duplication bytes, and browser payload budgets; full-system
tokens are not assumed available. No higher cost cap or softer quality bar.

Zero-model contracts use synthetic delivered and negative results **not**
G0–G3 answers: final render with genuine witness yields the existing verified
graph; omission/tampering yields none; reload uses a real logged witness and
logic, while missing/tampered fields fail closed; ordinary/protected log
records do not gain a new episode field; browser JSON and graph details do
not expose raw episode. These contracts are not model/Safari evidence.

Before code, verify dataset exact strings have zero collision in other
datasets, syntax/role/source preflight, SHA and commit/push/PR head. Then
implement one variable, run focused and affected neighboring tests, freeze
product hashes, diff review, commit/push/PR head **before** first new model
turn. New launcher-owned 0700 root, zero-turn same-PID ready/planned stop,
official-SHA private offline ONNX prewarm, T0_ready empty DB/profile, then
new Safari tab G0–G3 in order. Save final and reload visual evidence each
turn, raw/SQLite/profile snapshots, stop only the owned PID and close only
the newly-created tab. Failure stays failure; no G/T/N/Q/S replay to tune.

This graph delivery is a necessary P4 visual-trace component, not a claim of
general human understanding, strong-LLM superiority, human preference,
temporal prediction, semantic equivalence, or full product completion.
