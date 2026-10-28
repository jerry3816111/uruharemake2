# P4 Han-only visible Japanese boundary: prospective repair freeze

Status: prospective product repair, **not** a change to the prior codec result,
research holdout, or natural-Japanese quality claim. Same-model review is
design feedback, not independent human evaluation.

## Before and one variable

The fresh isolated 2026-10-27 native Safari turn is recorded in
`analysis/p4_private_trace_codec_fresh_safari_result_2026-10-27.md`. Chinese
input asking which first action to take yielded `整理筆記本` in the selected
`core_message_jp`, assistant bubble, persisted row, and node graph. M49 said
`not_required`; final `visible_language_guard` recorded `changed=false` and
no rejection. Self-monitor separately detected low content density and
post-check said the reply did not cover focus. The storage codec did not
introduce this phrase.

The single changed variable is **the evidence threshold for certifying a
Han-only final surface as Japanese**. `uruha_brain_mac.py` currently treats
any `[一-龠]` as a Japanese glyph. Finite Chinese-residue regexes in
`rightbrain_language_quality.py` cannot enumerate ambiguous common Han
strings such as `整理筆記本`. In the user-visible guard and its already-connected
M49 language check, a surface containing Han but no hiragana/katakana must
therefore be treated as *unverified Japanese*, even if no known Chinese-only
glyph or phrase is present. This is a cautious *insufficient evidence* reason,
not a declaration that every kanji-only phrase is Chinese. Do not change
global `has_japanese`, model prompt, planner, selected act, memory, codec,
baseline, or formal data in this task.

## Contract and scope

Allowed source: the final user-visible rejection method in
`uruha_brain_mac.py` and the existing M49 reason set that uses the same
checker; focused tests for the guard/M49/integration, this freeze, result,
and `CURRENT_TASK.md`. Preserve known Japanese mixed-kana output, persona,
identity, protected scenes, actor/source anchors, and the existing source-first
M49 authorization contract. A rejected candidate must not be turned into a
made-up Japanese translation: use existing source-first repair only when its
authorization passes, otherwise the existing safe Japanese fallback.
No fixture-specific `整理筆記本` substitution or new generic nagging sentence.

Before source edit, run affected unchanged-source tests and add red contracts:
(1) Han-only ambiguous candidate from the observed Chinese input must have a
new explicit rejection reason and may not be published unchanged;
(2) an ordinary M49 path must not say `not_required` for that candidate;
(3) normal kana-bearing Japanese remains accepted;
(4) protected/failed authorization cannot silently accept the Han-only
candidate or fabricate a semantic claim. A short all-kanji genuinely
Japanese expression may be conservatively rejected; record that tradeoff
rather than claiming perfect language identification. Existing broader
affected suites must stay green, and no historical SHA-locked file changes.
The new reason must enter both the final guard checker and M49's existing
language-repair reason set. M49 may make at most **one** additional existing
source-first authorizer call on an ordinary turn, with no retry. Test a
Chinese-source example, an English-source Han candidate, kana-bearing
Japanese control, and a legitimate all-kanji Japanese phrase such as `継続`
as a measured conservative false rejection; do not weaken `has_bad_language`
or claim perfect language identification.

Engineering gate: zero visible Han-only leak in these exact contracts,
traceable guard/M49 reasons, no regression in directly adjacent tests, zero
new raw-memory write from the checker, and bounded model cost measured.
Then run **a new isolated native-Safari turn** with Chinese input; inspect the
visible reply, decoded persisted row, and graph after reload. A language PASS
requires natural Japanese in the bubble and graph, not merely a Japanese
fallback keyword. The separate usefulness gate requires the reply to answer
which concrete first step to take without invented context. If language passes
but usefulness fails, retain product acceptance FAIL and open a separately
frozen source/answer-quality task. Any live turn is exposed development data,
not holdout. Do not run P4-B real runner or write formal DB.
