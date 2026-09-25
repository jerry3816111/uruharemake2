# P4-AU real source-bound current-action delivery: formal FAIL

The prospectively frozen two-turn private-runtime/Safari gate is **FAIL**. Both turns were executed exactly once in one isolated session at port `7884`; the inputs will not be rerun and the frozen gate will not be changed.

## Observable result

Turn 1 input:

> 我今晚腦中的想法像排隊一樣不停冒出來，怎麼都慢不下來。

Turn 1 visible reply:

> 今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？

Turn 2 input:

> 你先問清楚是對的；我現在需要一個能立刻做的步驟。

Turn 2 visible reply:

> 今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。

The formal result failed six frozen metrics: M45 delivery, M46 verification/content/surface, M39 practical surface act, and the prohibition on another generic promise or clarification.

## What this real product path did prove

- Turn 1 executed `calibrate_need`, registered exact M44 receipt `p1-1-c47bcaefa644b5b4`, exposed six P4-AG candidates, and locked the next-turn outcome.
- Turn 2 linked the user's support to that exact earlier action and independently detected the current `solve_regulation` / `practical_help` request.
- P4-AU added the exact prior user problem as `prior:1`; digest `e0fcdf502c58532a` matches Turn 1. It used zero assistant sources and zero private-inference sources.
- The P4-AU blackboard node was index `50`, before M50 `51`, M53 `55`, M46 `56`, M45 `57`, and utterance `69`. Safari showed and expanded the real `prior_source_linked` node.
- Both replies were natural Japanese, both turns wrote durable isolated episodes, and the private Chroma store contained exactly two embeddings.
- P4-AU itself added zero model calls, zero factual-memory writes, and no raw dialogue to its trace.

This supports one narrow claim: a real product path can preserve exact previous-user problem evidence across a feedback-plus-request turn and make it available before existing action planning, without treating assistant text or inferred psychology as the task source.

## What failed

Source handoff was not enough to produce a delivered action. M45 had three allowed user clauses and made one completed model call (`711` prompt tokens, `288` completion tokens). It generated two distinct state-changing candidates, but both had zero structurally valid candidates.

The selected candidate proposed grouping the currently racing thoughts and contained two quoted labels. M53 found neither label verbatim in the user sources and did not recognize either as a neutral structural role: `named_label_count=2`, `exact_source_count=0`, `neutral_role_count=0`, `unsupported_count=2`. It therefore raised `unsupported_concrete_scaffold_label_m53`; M46 was `plan_rejected`, M45 was `withheld_goal_plan_failed`, and M39 correctly failed closed on `practical_action_not_delivered_m45`.

The pre-M39 sentence—`いや、今すぐできる一個だけ、一緒に決めよ。そのくらいでいいだろ。`—still did not perform an action. The final visible sentence asked for more context again. Turn 2 took `20.7275s`, slightly above the `20s` target, although latency was recorded rather than used to excuse the failure.

This separates four different claims:

1. the system recognized feedback about its previous action;
2. it retained the exact problem source across turns;
3. it formed a source-safe actionable plan;
4. it actually expressed an immediately executable action.

The first two passed in this case. The latter two failed. Therefore this result is not evidence of felt understanding, human usefulness, a recovered human equation, natural-distribution generalization, or superiority over a matched strong LLM.

## Next bounded correction

This pair is exposed development evidence only and must not be rerun. The next prospective task should change one boundary inside M53: distinguish truly source-neutral operational role labels from invented concrete topic categories. It must keep invented `「環境」「経済」「社会」`-style labels blocked, leave M46 independent review and M39/M45 fail-closed behavior intact, add no model call, and freeze new cases before implementation. A later new Safari pair is required; passing offline controls cannot rewrite this FAIL.
