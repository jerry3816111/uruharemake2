# P3-B46 prospective v3 failed-run acceptance

## Outcome

The released one-time run was executed once and stopped on the first case as specified. It did not fail because Ollama or the isolated product worker was unavailable. It retained a real visible-output failure:

- top-level status: `failed_retained_no_retry`;
- contract code: `p3_b46_case_worker_failed_no_retry`;
- completed cases: 1 of 3;
- generated condition-turn outputs: 8;
- real provider calls: 5 (one product call and four direct calls);
- measured usage: 1,857 prompt tokens and 240 completion tokens;
- measured wall time: 40.379055 seconds;
- annotation accesses during generation: 0;
- production-database accesses: 0.

The checkpoint tree, case result, run commitment and top-level failure result are hash-bound by
`research/p3_b46_prospective_v3_failed_run_freeze_2026-09-17.json`. The release must not be rerun.

## Actual visible outputs

| Turn | UruhaBrain product | Same-model direct baseline |
| --- | --- | --- |
| u1 | `寝てないのか、考え事で止まんないのか、まずそこだけどっち？` | `そうですね、第三版が完成したなら進捗が進んだことでしょう。何か問題はありますか？` |
| u2 | `寝てないのか、考え事で止まんないのか、まずそこだけどっち？` | `好的，那你可以開始進行下一步的修改了。有什麼需要確認的地方隨時告訴我。` |
| u3 | `ん、その話もう少し聞かせて。` | `大変そう呢，继续应付这些注解得花不少时间和精力吧。加油哦！` |
| u4 | `うん。今は質問しないで、ちょっとここにいる。そのくらいでいいだろ。` | `そうそう、気分を変えて吐槽するのもいいね。何が特に不満なのか、具体的に話してみよう。` |

## What the structural gate proved

The product preserved a natural-Japanese-only visible surface for all four turns. The direct baseline did not: u2 was Chinese and u3 mixed Japanese and Chinese. All eight outputs were nonempty, all four paired views matched, the case used only localhost, the isolated product database remained separate from production, and the session/memory path was preserved.

The gate does **not** establish that the product understood the conversation. Even before opening the frozen semantic rubric, the visible outputs expose a likely product defect: u1 and u2 repeat an unrelated prior-topic response, u3 is generic, and u4 offers presence instead of joining the explicitly requested complaint. The direct baseline also violates the requested Japanese output surface. These observations will be checked only against the rubric that was frozen before generation.

## Why no retry or three-case score exists

The preregistered runner treats failure of any required case structural check as terminal. Case 01 failed the all-eight-Japanese check because the direct baseline leaked Chinese, so cases 02 and 03 were never started. Changing that behavior and rerunning the same exposed source would violate the released no-retry boundary. Therefore:

- there is no three-case batch comparison;
- there is no system-winner conclusion;
- there is no human-preference evidence;
- there is no formal temporal-holdout evidence;
- the retained case can support a post-lock developer-rubric diagnosis only.

## Next gate

P3-B47 may open the already frozen annotation file only for case 01 and produce a deterministic, evidence-linked diagnostic grade. It must keep surface compliance separate from semantic success, mark cases 02 and 03 as unavailable rather than zero, and derive one single-variable repair target. It may not regenerate, tune against, or claim improvement on the exposed v3 case.
