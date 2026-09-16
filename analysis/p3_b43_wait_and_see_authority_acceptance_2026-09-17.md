# P3-B43 explicit wait-and-see authority acceptance

Date: 2026-09-17

## Outcome

**PASS for the bounded exposed-development repair.** B42 u4 explicitly requested a neutral
wait-and-see organization instead of optimistic reassurance, but the product returned generic presence.

- immutable before: `そっか。まあ、今はうちがここにいる。`
- isolated four-turn product replay after:
  `うん。期待していいとも断られたとも決めず、今回はいったん様子見でいいだろ。`
- added model calls: 0;
- factual long-term writes: 0;
- runtime graph: one connected `wait_and_see_authority_p3` node before `selected_plan`.

The surface keeps both relational outcomes open. It does not claim the senior is interested, rejecting
the user or privately motivated in any particular way.

## Selection boundary

Both same-turn clauses are required: explicit rejection of false reassurance, and a direct request to
jointly frame the situation as wait-and-see. Source-disjoint Chinese, English and Japanese positives
passed. The route fails closed for wait-and-see alone, negation, script/example text, a third-person
report, a VRM/function command, protected risk text and a mere historical delay statement. Safety has
priority.

Only typed cues and digests enter the trace. The neutral relationship framing is not written as a fact,
stable preference or private-state claim. Ordinary turn-episode persistence remains unchanged.

## Verification

- 12 focused classifier/plan/surface/graph tests passed;
- 1 isolated actual-product B42 four-turn replay passed in 19.87 seconds;
- 100 wait-and-see, playful-guess, shared-amusement, current-request, explicit-space,
  repeated-refusal and Japanese-guard tests passed in 101.65 seconds with 9 dependency warnings;
- `git diff --check` passed.

## Evidence boundary

B43 was derived from exposed B42 and therefore cannot validate case03 or establish advantage. The B42
run remains immutable. Because all three B33 cases now have visible outputs, the next comparison data
must be a new prospective batch with scoring requirements frozen before generation; tuning or grading
the old cases would only measure repair of known examples.

