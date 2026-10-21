# P4 User-first-person actor/deixis surface: prospective product freeze

Status: **preimplementation; no new model or Safari result**. H0–H3 remains
whole-batch strict FAIL. This is a developer-authored product repair, not a
formal holdout or a claim of general speaker understanding. Do not replay
H/G/T/N/Q/S prompts or change their labels.

## Before, one variable, and boundary

H1 User said `私は2035年9月23日の集合場所を橙色の遊歩道の入口に決めた。`.
M31 carried User's `私` into its canonical source summary; M32 produced
`私は…決めたんだね。`; the final language guard unconditionally changed that
to `うちは…決めたんだね。`, and M39 accepted it. Safari, private JSONL, guard
trace, graph and SQLite all showed the wrong visible actor. This is not a
browser graph hydration defect. The earlier G1 and T1/T8 show the same
class of error, but their exposed prompts are not development data here.

**Single changed core variable:** role-aware first-person realization at
the final user-visible surface. For an exact current-User first-person
echo, use source-bound second-person deixis (or omit the subject) rather
than treating User `私` as Uruha `うち`. Preserve actual Uruha self-reference
as `うち`, and preserve attributed `私` inside balanced Japanese quotation.
The repair must be deterministic, add no model calls, and expose only a
bounded actor certificate in the existing private guard trace. Do not
change M31/M32 extraction, chosen act, memory retrieval/write rules,
semantic ledger, graph architecture, browser receipt, model settings or
protected-route policy. The internal M32 candidate may remain mis-deictic;
this item proves or falsifies the *final visible* actor boundary only.

The positive transduction is narrowly admitted only when the current raw
User turn is one unquoted `私は…` statement, its exact SHA matches the
current-turn source-role and M31 certificates, the M32 `response_jp`
equals the raw selected visible candidate, and that candidate equals the
User proposition plus M32's bounded acknowledgment suffix `んだね。` or
`ね。`. Preserve the full proposition and substitute only the deictic
subject. Missing/stale proof, changed proposition, quotation, reported
speech, correction/uncertainty or multiple actors must not be rewritten as
a User fact. An apparent direct-User `私は…んだね` echo without the full
certificate should fail closed to a short, non-attributive Japanese reply;
it must not become Uruha's autobiographical fact. Neither the old
`_sanitize_reply` nor the final normalizer may blindly convert quoted `私`.
Do not use P4-T's inferred `speaker_ownership` alone as proof: a
`友達向け` rewrite can be classified as third-party even when the friend did
not speak. Require the raw outer-turn certificate and exact source digest.
This does not certify all Japanese quote syntax or arbitrary paraphrases.

Allowed code: `uruha_brain_mac.py` and a focused
`test_p4_user_first_person_actor_surface.py`; allowed records: this plan,
the paired dataset, two SHA manifests, top of `CURRENT_TASK.md`, and a
result report. No original dirty checkout, private/formal DB, old frozen
artifacts, unrelated output, external deploy, or new permanent dashboard.

## Frozen cases and success/failure

The paired JSON fixes five fresh Safari turns in one new isolated session,
each once, zero retries. Dates/place have zero prior dataset-JSON exact-date
hits as checked before implementation. A0 is a direct User `私` choice and
the required M32-coverage case; A1 asks recall from only that User source;
A2 is an attributed first-person quotation; A3 is real Uruha self-identity;
A4 is an unsupported mixed quote/recall negative. A0 must retain the date,
place and User actor and must not say `うちは` chose it. If M32 does not
actually select an exact echo in A0, this batch lacks the intended product
coverage and cannot pass. A1 must recall only the directly sourced place.
A2 must not reassign the quoted `私` to User or Uruha. A3 must affirm Uruha
identity in natural Japanese. A4 must not assign quoted action to a speaker,
assert unsupported pending content as fact, or revive stale verified ledger
nodes; known older-route failure remains a hard content gate, not an excuse.

Zero-model contracts freeze direct positive, same-day/different-place and
same-place/different-day near misses, altered proposition/digest, missing
M32 proof, reported/quoted source, quoted candidate, actual Uruha
self-reference (including a User who first decides and then asks what
Uruha herself chose), private-life word, and Chinese/English/Japanese
input non-regression. The positive certificate is Japanese direct-source
only; other-language actor understanding is **not** established by this
item. Direct current-User repair must be traceable from original
candidate through final guard, M39, downstream actor overlays, episode and
final Safari bubble/graph. The guard's final hash must match the delivered
reply after all overlays; a post-guard change is failure, not a pass;
on no proof, no fabricated owner. Product gates: 5/5 final natural Japanese,
identity/source/quote/safety, 5 distinct isolated episodes, no profile fact
pollution, final bubble = private raw log = final guard = graph utterance,
per-turn delivery-complete wait <=20.000 s, zero extra model calls, and
actual available token/latency/storage costs. Inspect each final and reload
graph in Safari; no old positive on A4. Save native visual artifacts if
supported; if not, mark the saved-visual gate unmet. Any gate failure makes
the **whole batch strict FAIL**, with narrower actor success separately
stated. A0 test success alone is not human understanding or LLM advantage.

## Order and stop rule

Freeze this plan, dataset and their SHA in a plan-only commit/push, verify
PR #435 head, then implement the one actor variable. Run focused and
affected adjacent zero-model tests, compile/diff review and product SHA;
commit/push before real generation. Only then use a new launcher-owned
0700 root, same-PID zero-turn HTTP ready/planned stop, official-SHA ONNX
private offline prewarm, explicit empty T0, and real Safari A0–A4. Record
complete raw SHA, trace/episode/profile and cost; planned-stop only owned
PID and close only our new tab. At most two reasoned fix batches; if the
actor item still fails, preserve minimal counterexample and
`REVIEW_REQUIRED`. H3's older unsupported mixed-reply path is a separate
future variable; this batch must not quietly fix it or relabel H.
