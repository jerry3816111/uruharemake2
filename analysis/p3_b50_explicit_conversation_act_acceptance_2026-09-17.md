# P3-B50 explicit conversational-act fidelity acceptance

Date: 2026-09-17

## Problem and single variable

The exposed P3-B47 case asked:

`現在先別分析，陪我吐槽一下這些註解怎麼會一直長出來。`

Before P3-B50, M25 reduced this to generic `share_arousal`. The visible reply was:

`うん。今は質問しないで、ちょっとここにいる。`

This was Japanese and performed companionship, but it did not perform the explicitly requested joint complaint. P3-B50 changes only the fidelity of this explicit current-turn conversational act. It does not infer a joint complaint from ordinary negative content and does not change crisis, refusal, memory-recall, or explicit-space authority.

## Implementation

- A cross-lingual `joint_complaint` contract distinguishes:
  - complain with the user about an observable topic;
  - generic companionship/listening;
  - teasing the user;
  - ordinary negative content;
  - negated requests.
- The existing M31 source-first authorizer now verifies that the current topic and the request to complain together survive normalization.
- A visible result must contain a source-grounded topic and actually complain. Presence-only replies, questions, or advice cannot be marked performed.
- A rejected model surface may use the already generated canonical topic only when the remaining failures are surface-anchor-only, the act is preserved, the topic appears in the canonical summary, the anchor is canonically grounded, and the topic is not a dialogue participant. The observed `私と君` counterexample is explicitly rejected.
- The final runtime trace and node graph expose `explicit_conversation_act_p3_b50` between M25 selection and the Japanese surface guard. Raw dialogue is not copied into this trace.

## Evidence

### Deterministic and contract evidence

- Focused/adjacent suite: `48 passed`.
- Expanded affected regression suite: `125 passed`.
- Cross-lingual positive requests: Chinese, English, and Japanese.
- Negative boundaries: ordinary complaint, generic companionship, teasing the user, three-language negation, crisis cue, semantic failure, participant-as-topic failure.
- Graph and compact Web trace: the B50 node is retained and connected from M25 selection toward M49/language guard.

### Local real-model evidence

All calls used local Ollama `qwen3.5:9b`; no external or paid provider was used. Thirteen development calls were made while retaining failures. Token counts were not attached to a ledger, so no token-cost claim is made.

Retained progression:

1. First three-language source-first batch: classifier 3/3, surface authorization 0/3. Anchor and act failures were retained.
2. After prompt clarification: surface authorization remained 0/3 because the model still returned anchors that were not literal substrings of both canonical summary and response.
3. After deterministic shared-anchor verification: English and Japanese authorized, Chinese remained rejected.
4. One isolated Chinese runtime produced `私と君、またかよ。いい加減にしてくれって。`. This was rejected as a valid topic after inspection and became a permanent regression boundary.
5. Final isolated Chinese runtime, with no persistent product database, produced:

   `これらの注釈、うざい、またかよ`

   The final trace reported: `joint_complaint_realized`, `surface_status=matched`, one canonically grounded topic anchor, observable complaint marker present, generic presence/question/advice absent, and M25 final surface matched. End-to-end elapsed time was 9.167 seconds for this isolated local turn.

This is exposed development evidence, not an unexposed holdout, human naturalness judgment, Safari acceptance, or proof of system advantage.

## Safety and claim boundary

- Generic `這些通知真的很煩` does not authorize the act.
- `先陪我一下` remains generic companionship.
- `吐槽我一句` remains teasing the user, not joint complaint.
- Negated joint-complaint requests do not obtain act authority.
- Crisis and protected routes stay protected.
- The local output is understandable casual Japanese, but has not received independent human naturalness/persona evaluation.
- No formal P3 comparison, M56 result, human preference result, or production-readiness conclusion is authorized by P3-B50.

