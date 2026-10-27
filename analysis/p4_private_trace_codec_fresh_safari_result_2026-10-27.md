# P4 private trace codec: fresh isolated native-Safari result

Status: **private-row codec and graph reload PASS for one fresh product turn;
visible natural-Japanese and useful-reply gate FAIL**. This is a separate
product acceptance tier from the zero-model contracts in
`analysis/p4_private_trace_lossless_codec_zero_model_result_2026-10-27.md`.
It does not authorize P4-B's real runner or a 50-turn conclusion.

## Isolation and exact observation

- Ran the released isolated product launcher preflight with a new 0700 runtime
  root at `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-imng03ha`, then its loopback Web app at `127.0.0.1:7895`. Preflight's sandbox checks passed before a model call or Safari action; private DB and log paths were directed under that root. The original dirty checkout and formal DB were not intentionally used.
- Opened **one** new native-Safari tab, leaving 52 pre-existing tabs alone. Sent one text turn: `桌上有兩本筆記本，我現在只想先整理一件東西。你會叫我先做什麼？`
- The visible assistant bubble was **`整理筆記本`**. This is Chinese and does not say which notebook or concrete first action. The user-visible natural-Japanese and useful-answer gates **FAIL**, regardless of storage success.
- The live node graph displayed the same USER SIGNAL and UTTERANCE. After a native Safari reload, the graph again displayed this input and `整理筆記本` from the persisted row. This is observed UI/AX evidence of graph hydration, not a durable screenshot. The chat bubble itself did not persist across reload; the graph did.
- Closed only the newly opened `7895` tab (Safari count returned 53→52; original `7894` tab became active), interrupted this run's exact server session, and verified no `7895` listener or process 27682 remained. The isolated runtime root was preserved as evidence, not deleted.

## Disk and decoded trace checks

The new private `web_logs/conversation.jsonl` has 0700 parent directories and
0600 file mode. It contains exactly **one row, 282,296 bytes**, SHA-256
`6bbee45c39d0eaf35ff0f150f7bdc9cb42fc64089d7105d807122badfd5d96b7`.
The persisted `cognition_trace` is a string with codec
`zlib-json-base64-v1`; its descriptor declares **895,780** uncompressed trace
bytes and SHA-256
`3625b7b37805debeeefc4673ce45daffc843ac5987424ffc9257709441907e51`.
The production strict decoder accepts it as a complete logical trace object.
The same logical row serialized without codec is **1,004,873 bytes** versus
282,296 persisted bytes (**71.91% less**). This is one fresh row, not a
long-conversation estimate or generalized capacity result.

The decoded row is session `20261027_205627_e030b354`, turn 1, input mode
`text`, and has **77** runtime blackboard events. Its `visible_language_guard`
reports `changed=false`, `repair_action=none`, empty rejection reasons, and
both original/final reply `整理筆記本`; M39 records `accepted_verified_surface`.
This is direct evidence that the visible-language guard did **not** catch the
Chinese-only final reply. It is not evidence that compression caused the
language failure; storage codec and reply generation are separate variables.

Read-only path inspection found the selected plan's `core_message_jp` already
equal to `整理筆記本`; UI and codec did not introduce it. The current guard in
`uruha_brain_mac.py` accepts any Han character as a possible Japanese glyph,
while the finite Chinese-specific patterns in `rightbrain_language_quality.py`
do not match this phrase. M49 therefore recorded `not_required` and made no
repair attempt. Independently, self-monitor reported
`low_speech_content_density` and post-check recorded
`did_reply_cover_focus=false`, but the reply was still emitted. A language
boundary repair alone cannot claim to fix that usefulness gap.

## Claim boundary and next gate

The codec's one-turn real writer → private disk → strict reader → Safari graph
reload path passed. Natural Japanese, answer usefulness, multi-turn memory,
50-turn cost, screenshot proof, and P4-B real process containment remain
unproved or failed as stated above. Preserve this negative example. The next
single-variable task should first freeze and test the actual final-surface
language decision path against short Han-only Chinese replies, without
altering codec or weakening the baseline. Before claiming a repair, run
red/green contracts and another isolated Web/Safari turn with a natural
Japanese, actionable reply and consistent graph. Do not reuse this exposed
turn as holdout.
