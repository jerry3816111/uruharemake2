# P3-B22 humor versus action-consent surface acceptance

Date: 2026-09-15

## Outcome

**PASS for the bounded exposed-development repair.**

B21 showed that the product saw `可以吐槽我` but lost `不要把玩笑當成我答應照做` and emitted
an unrelated brain-activity tease. The single implementation variable was M39's bounded current-source
frame and its already-existing `playful_tease` repair. No model, baseline, scoring rubric, memory rule,
or locked output was changed.

M39 now records `humor_not_action_consent` only when the same visible input both permits humor and
denies that humor grants agreement, permission, compliance, or action authority. If an upstream
`playful_tease` surface requires repair, it now emits:

> ツッコミはする。でも、その冗談を同意扱いするほど雑じゃないって。

The prior B20 output was:

> 脳みそ元気すぎだろ。少し落ち着けって。

The new sentence keeps the invited light teasing and explicitly refuses to convert the joke into
consent. The trace stores only the typed observable concept and source/reply digests, not raw dialogue
or a claim about private mental state.

## Verification

- Three Chinese/English/Japanese developer regression variants produced the same bounded Japanese
  semantic commitment when given the stale arousal candidate.
- Six negative controls containing only a humor invitation or only a non-consent statement did not
  activate the combined concept.
- A fresh subprocess loaded the actual `uruha_web_ui_product` entry in an ephemeral P3 workspace and
  ran Chinese, English and Japanese turns. Each selected `playful_tease`, produced the new Japanese
  reply, and retained exactly one M39 node before `utterance` in the runtime graph.
- The actual product test used zero model calls, zero network attempts, zero transport rejections and
  a DB path inside the temporary case workspace; the workspace was removed by the test context.
- 73 M39/surface/action/trace affected tests passed in 44.82 s.
- 182 P3 and adjacent adaptive-policy product regressions passed in 38.94 s with 9 dependency warnings.

This is a repair derived from an exposed developer case and semantic variants written by the same
developer. It demonstrates that the implementation now preserves this explicit current-turn boundary;
it is not an independent holdout, human felt-understanding result, or evidence that open-language
humor and consent are solved. B20 and B21 remain immutable and negative.
