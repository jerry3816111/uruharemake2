# P3-B24 speaker-qualified preference recall acceptance

Date: 2026-09-16

## Outcome

**PASS for the bounded exposed-development repair.**

The immutable B23 case05 product trace already contained the correct selected episode and a correct
planner core for the user's own preference, but that evidence had no visible authority. The existing
P2 speaker adapter only handled explicit quoted-source questions. Self-monitoring then produced an
instruction-like repair, and the Japanese guard correctly failed closed to the generic clarification
`ん、その話もう少し聞かせて。`.

The single product variable in B24 adds a bounded `speaker_qualified_fact` contract for an explicit
first-person past-preference question. It can answer only when the already-selected recent or working
memory contains exactly one category-matching, explicitly first-person preference and the value has a
bounded Japanese realization. It does not scan unselected storage, ask a model to infer a speaker,
write a factual memory, or retain raw input in its trace. Missing, third-party-only, ambiguous, and
unsupported-localization cases produce a short Japanese abstention instead of a guess.

During actual-product integration, an explicit `other's, not mine` correction was already rendered
correctly by existing M32. B24 was narrowed rather than adding a second competing authority for that
act.

## Actual isolated product evidence

The test loaded the real `uruha_web_ui_product` install path inside an ephemeral workspace, with model
loading disabled and a selected source-disjoint memory item:

- selected memory: Taro likes red bowls; the user explicitly said they prefer black coffee;
- user query: `What kind of coffee did I say I prefer?`;
- visible reply: `あんたが好みって言ってたのはブラックコーヒー。`;
- selected contract: `resolved_unique_user_preference`;
- planner model call attempted: `false`;
- graph: exactly one connected `speaker_qualified_fact_p3` node before `selected_plan`;
- node privacy: no raw remembered sentence, only typed status, digests and selected provenance.

The same isolated product instance then received an owner correction outside the new classifier:

- user input: `The hiking plan was Taro's, not mine—keep that straight.`;
- visible reply: `ハイキング計画はタロウのもので、うちのものではないんだね。`;
- route: existing `semantic_commit_repair_m32`;
- planner model call attempted: `false`.

This second turn verifies non-interference; it is not claimed as a new B24 ability.

## Verification

- 21 focused tests passed in 13.46 seconds. They cover Chinese, English and Japanese questions;
  source-disjoint first-person evidence; third-party, metalinguistic, unselected, missing, multiple and
  unsupported-value controls; safety precedence; idempotent raw-free graph materialization; and the
  actual product install path.
- 130 product-surface, request-authority, refusal, speaker-recall, Japanese-guard and observatory
  affected tests passed in 62.58 seconds with 9 dependency warnings.
- 193 P3 comparison, output-lock, adaptive-policy and route-adjacent tests passed in 39.53 seconds
  with 8 dependency warnings.
- `git diff --check` passed.

## Evidence boundary

B24 is a repair derived from the exposed B23 failure and developer-authored semantic variants. It is
not a fresh holdout, human felt-understanding result, open-domain preference resolver, production UI
acceptance, or evidence that UruhaBrain is better than the direct baseline. Its localization set is
deliberately bounded and unknown values abstain. The B23 output lock remains immutable and failed;
neither its output nor its score was changed or rerun.
