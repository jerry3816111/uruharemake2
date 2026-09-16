# P3-B31 shared-amusement surface authority acceptance

Date: 2026-09-17

## Outcome

**PASS for the bounded exposed-development repair.**

B28 case06 turn 4 explicitly said `別に困ってない、ただ笑ってほしかっただけ。`, but the
product replied `ん、そこもう少しだけ聞かせて。`. The existing M25 classifier recognized
requests for a tease or joke, but not the distinct two-clause act “I am not asking for help; share
the laugh with me.” The uncertainty path therefore continued asking for clarification.

B31 adds one product-only current-turn authority after the existing P2/P3 adapters. It selects only
when both observable clauses are present: an explicit rejection of problem-solving / statement of no
trouble, and a direct request for shared amusement. It does not infer a stable humor preference or
private state, add a model call, or write a factual long-term memory.

## Actual before and after

- immutable B28 before: `ん、そこもう少しだけ聞かせて。`
- B31 isolated product after: `あー、そっちね。解決じゃなくて一緒に笑ってほしかったのか。なにそれ、ちょっと笑う。`
- planner route: `deterministic_rule_plan`
- general planner model call attempted: `false`
- visible contract: `matched`
- graph: exactly one connected `shared_amusement_authority_p3` node before `selected_plan`
- M25 trace: current explicit response authority with required surface `matched`
- M23 trace: selected mode `shared_amusement`
- writes: ordinary `turn_episode` only; `fact_memory_write_count=0`

The isolated runtime replayed all four case06 user turns in order. The final surface contained no
follow-up question, help offer, unsupported event detail, English or Chinese visible fragment. The
workspace used temporary adaptive-model, Chroma and Web-log paths; it did not open the production
database or add the test dialogue to formal memory.

## Boundary controls

Source-disjoint Chinese, English and Japanese positive forms were accepted. The contract failed
closed for each of the following:

- a generic `笑ってください。` instruction without the no-solve clause;
- an explicit `do not laugh` negation;
- quoted / script / example text;
- a third-person report;
- a VRM/avatar expression command;
- a protected self-harm cue;
- an ordinary statement that a cat incident was funny.

The final visible guard also refuses to override a runtime `safety_sensitive` route. Raw dialogue is
not stored in the contract or graph node; the node contains typed cue names, digests, boundary and
surface status.

## Verification

- 13 focused classifier, authority and graph tests passed before runtime execution.
- 1 isolated actual-product case06 replay passed in 23.56 seconds.
- 101 shared-amusement, M23/M25, current-request, refusal, explicit-space, speaker-attribution and
  speaker-qualified-fact tests passed in 70.86 seconds with 8 dependency warnings.
- `git diff --check` passed.

## Evidence boundary

B31 is a repair derived from an exposed B28 failure. Its multilingual variants are developer-authored
controls, not an unexposed temporal holdout or human felt-understanding result. The deterministic
surface proves that this explicit act now has bounded authority; it does not prove open-world humor
understanding, improvement over the direct baseline, or generalization to implicit requests. B28
and the permanently inconclusive B29 remain immutable.
