# P3-B7 canary baseline acceptance

Date: 2026-09-14

Status: **FAILED_RETAINED / NO QUALITY COMPARISON**

## What ran

The frozen one-turn input was sent to the same local `qwen2.5:7b` model under
the same shared persona and generation options. The direct condition completed.
The deliberate condition completed its draft call, then terminated after the
critique provider call because the provider prompt count did not equal the
offline reservation. No retry was made.

| Condition / stage | Outcome | Prompt tokens | Completion tokens | Provider wall |
|---|---:|---:|---:|---:|
| direct / direct | complete | 248 | 42 | 3.445567 s |
| deliberate / draft | complete | 222 | 32 | 1.298907 s |
| deliberate / critique | terminal `provider_prompt_count_mismatch` | unavailable | unavailable | unavailable |
| deliberate / revise | not attempted | — | — | — |

Provider-call evidence is therefore 3 attempts, 2 immutable completions, and 1
immutable post-transport contract failure. Known completed usage is 470 prompt
tokens and 74 completion tokens. The failed provider response usage was not
retained by the first failure serializer, so it is not estimated.

The generic CLI failure artifact reports zero calls because its refusal summary
does not inspect checkpoint evidence. That counter is not authoritative for this
post-transport failure. The six immutable intent, complete, and failure records
are the authoritative evidence. Correct failure accounting is required before a
later released run.

## Locked output evidence

Product from P3-B6:

`最近退社後は常に不機嫌で何もしたくないんだね。`

Direct baseline:

`仕事帰りにそんな気分になるのは辛いですね。何か特別なことをして気分転換はいかがでしょうか。例えば散歩をしたり、好きな本を読んだり。`

Deliberate draft only, not a final reply:

`仕事のストレスが溜まっているのかもしれません。休憩時間はゆっくり休んで、気分転換してみるのもいいですよ。`

These may be inspected as concrete artifacts, but must not be scored as a
three-condition comparison. The separated annotation remains unread because
both baseline final outputs were not locked.

## Root cause and scope

The prior P3-B3 tokenizer probe included assistant messages followed by a user
message, but did not verify the deliberate call shape whose visible request ends
with an assistant private draft. The exact-count gate therefore correctly found
that the earlier binding evidence did not generalize to every real comparison
stage. This is an experiment-infrastructure failure, not evidence that any reply
condition is better or worse.

The first pre-provider empty-history failure is separately retained in
`p3_b7_canary_baselines_pre_provider_failure_2026-09-14.json`; it had zero provider
calls. The later failure described here occurred after provider intents existed,
so this exact deliberate request is terminal and will not be rerun.

## Decision

P3-B7 does not pass. P3-B8 must first bind tokenizer counts for every exact stage
shape (including assistant-ending private scratch), and retain expected and actual
usage on post-transport failure. Any next quality canary must use a new, unexecuted
source turn with a newly locked product output; the failed P3-B7 case may not be
silently recycled into a successful comparison.

This result establishes only that the current exact-accounting design is capable
of rejecting unsupported tokenizer generalization. It establishes no baseline
winner, human preference, holdout performance, or general UruhaBrain advantage.

