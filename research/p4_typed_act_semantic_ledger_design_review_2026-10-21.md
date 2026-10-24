# P4 typed act semantic ledger: post-S design decision

Status: design review after the two prospective Q/S correction batches exhausted
the stop rule. S remains **strict FAIL / REVIEW_REQUIRED**. This is a new,
bounded product item, not a third rewrite-prompt or validator patch, formal
holdout, same-model baseline comparison, or claim of general understanding.

## Evidence and alternatives

S3's frozen input requested a soft rewrite of a quote about **2027-02-11**
being `調整中`, plus recall of the User's place on **2027-02-10**. The sole
structurally delivered atomic answer dropped `2027`, changed `調整中` to
`決めてない`, and used `その日` for the recall. Mixed semantic delivery was 0/5,
though two eligible M31=true/M32=true variants occurred. The raw/Safari result
and evidence limits remain in
`analysis/p4_typed_mixed_atomic_rewrite_style_scope_fresh_product_probe_result_2026-10-21.md`.

The existing `uruha_mixed_act_lineage_p4.py` records two action types/spans but
no semantic obligations. `uruha_typed_mixed_atomic_delivery_p4.py` passes the
whole quote to a free rewrite and directly concatenates its output with the
source certificate's answer. The shared number filter rejects *new* numbers,
not dropped years; the local contrast filter treats different unsettled states
as equivalent. The source certificate's unknown answer says `その日`. Thus a
shape-valid transaction can be semantically wrong without a transport bug.

| Option | Potential gain | Reason not selected now |
|---|---|---|
| Another prompt/regex correction | Small implementation | Q/S stop rule exhausted; no general proof and S3 crosses existing filters. |
| Free per-act generation plus model verifier | Broader language coverage | Extra model calls, correlated verifier error, and likely >20 s tail latency need a separate budgeted experiment. |
| Isolate M31/M32 actor/authority | Important independent repair | Cannot alone preserve quote meaning or distinguish the two dates. |
| **Typed act ledger + constrained realization** | Immutable, inspectable date/state/source obligations before expression; zero added rewrite calls for the supported class | Deliberately narrow; unsupported wording abstains, and slot fidelity is not general semantic equivalence. |

Decision: choose the last option as a **new architecture item**. It is an
opt-in sidecar to the existing lineage and terminal transaction, not a change
to M31/M32 status or source/protected guards. Independent read-only review
located reusable source-role spans/digests, producer IDs, source binding and
guard/episode rollback; that review did not modify code or independently
certify the design's future success.

## One causal variable and boundaries

Replace the *mixed terminal realization method* for a precisely recognized
class of two-action turns. Before any surface wording, bind two immutable
action records to the event ID, cycle, raw digest and existing action IDs:

1. `quoted_rewrite`: current User's quoted *object* (not a fact assertion),
   exact absolute date, exact pending-state token, quote digest, and certified
   friend-facing soft-style cue. First supported syntax is
   `YYYY年M月D日の集合場所はまだ{相談中|調整中|確認中}です` (validated calendar date).
   Realization retains all source characters before final `です` and changes
   only that copula to `なんだ`. It must never send the quote to a free rewrite
   model, add a place, remove the year, or substitute one state for another.
   This finite transformation is a narrow language contract, not an answer
   keyed to any probe string or a general Japanese paraphraser.
   The raw quote span/digest must be rechecked and **raw quote must equal its
   NFKC-normalized form** before this first version realizes it; otherwise
   abstain. This avoids silently changing full-width source characters while
   claiming exact preservation.
2. `past_user_place_recall`: a *different* outer date anchor, explicit
   User-source status and existing provenance binding. Source-backed output
   may reuse only the certified answer; unknown/retracted/third-party status
   must name the **outer date** rather than say `その日`, without inventing a
   place. Bind the new per-act text to the source certificate digest and
   rederive/recheck it at the final guard. Do not change the old source
   certificate or mistake its old `authorized_reply_sha256` for the new text.

Only two separately realized and checked action receipts may be assembled
into a terminal candidate. Public trace/graph may show action IDs, digest,
bounded slot types and verification status, but not raw quote or private
memory text. The status is `bounded_slot_fidelity_verified`, while
`semantic_equivalence_certified` remains **false**. Unrecognized grammar,
ambiguous date/source, malformed lineage, lost source, protected or competing
route fails closed before any new model call or terminal priority. The old
final Japanese guard, history rollback, episode/utterance equality and native
graph verification remain required. No inferred User psychology is persisted.

This single variable intentionally does **not** fix ordinary seed-turn
`私`→`うち` actor reversal, M32=false admission, single-rewrite wording, or
protected-route legacy speech. They remain adjacent hard observations; their
recurrence prevents a full product PASS. Do not weaken those gates merely to
show a success on the new subpath.

## Falsifiable prospective execution

The separate plan and paired T0–T8 developer-authored data must be committed
and SHA-frozen before implementation. The fresh examples change dates,
locations and wording from N/Q/S; repository-wide exact prompt collision is
checked before code. In particular, an unknown-source example with **different
inner and outer dates** must show both dates attached to their proper acts,
with the exact pending-state token and no invented location. A known-source
example must retain direct User provenance; friend/retraction cases must not
be laundered into a User fact. Unsupported/protected cases must not gain new
terminal authority. These are narrow source/slot claims, not a semantic
equivalence metric for open-domain Japanese.

Expected new rewrite cost for the supported class is **0 calls/0 completion
tokens** rather than the current maximum one call (S used three added calls,
371 prompt + 62 completion tokens total). This is a design target, not an
observed product saving. Keep actual per-turn runtime ≤20.000 s and record
whole-system token cost as unavailable unless a trustworthy ledger exists.
After code and zero-model regression, freeze product hashes, then run once per
case in a new isolated local Web/Safari session, inspect actual action arrows,
reply/guard/utterance/history/SQLite/profile, and preserve raw evidence.
Any hard failure is strict FAIL. A lower-layer test, renderer projection or
partial positive example cannot be called product acceptance.

Formal strong-LLM comparison, human preference, temporal holdout, VRM and
Function Calling unified acceptance remain separate pending gates. Even a
bounded PASS cannot prove a human reaction equation or full Goal completion.
