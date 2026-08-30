# M28 Feedback Acknowledgement and Topic-Shift Surface Continuity

Date: 2026-08-25  
Status: focused milestone accepted  
Scope: feedback/current-topic separation and final Japanese surface continuity; not a general proof of human pragmatic understanding

## Why M28 was necessary

M27's internal causal outcome accounting was correct, but the live surface still failed in two user-visible ways:

1. after `對，就是這樣。`, the system reopened a clarification instead of acknowledging the confirmation;
2. after `今天外面下雨。`, the system let earlier uncertainty trigger a meta-clarification instead of responding to the current literal topic.

That meant the trace could be correct while the conversation still felt incoherent.

## Implemented mechanism

M28 introduces a typed `uruha_feedback_topic_transition_m28` contract between M27 outcome verification and final surface publication.

- Pure, causally linked support is classified separately from new current-turn content.
- A pure confirmation receives a short natural acknowledgement and does not create another pending desired-response prediction.
- An unlinked, self-contained, bounded literal topic can rebase the visible reply to the current topic.
- Safety, boundary, identity/factual-memory contracts keep priority.
- M23/M26 surface commitments cannot reintroduce stale uncertainty after M28 has current-turn authority.
- The M27 outcome is copied into the trace but never rewritten by M28.
- M28 stores a digest and typed fields, not raw dialogue, in its contract.

The current literal-topic fallback is deliberately narrow: rain, snow, cold, and hot weather have grounded Japanese surfaces. Other ordinary statements remain on the richer existing pragmatic/persona route instead of being flattened into a generic fixed acknowledgement.

## Contract and compatibility evidence

New focused test:

`test_feedback_topic_transition_m28.py`

- 6 tests passed.
- Covers pure support, support plus a new request, bounded weather topic rebase, incomplete deictic fragments, protected-turn priority, and real runtime/graph integration.

Focused V2.11–M28 compatibility suite:

- 210 passed, 3 dependency deprecation warnings.
- Includes Japanese visible-output guard, functional/pragmatic/personhood loop, idle suppression, routing, observatory, and M16–M28 contracts.
- An initial over-broad generic rebase caused two compatibility failures by suppressing richer learned/pragmatic replies. The implementation was narrowed to typed grounded topics; the two failures and full suite then passed.

## Isolated Safari evidence

Isolation root: `/tmp/uruha-m28-safari.ONXaE0`  
Local URL left open: `http://127.0.0.1:7869/?m28final=1`

| Turn | User input | Visible Japanese reply | M28 | M27 |
|---:|---|---|---|---|
| 1 | 我從早上就一直坐不住，腦子停不下來。 | まあ、寝てないのか、考え事で止まんないのか、まずそこだけどっち？ | not applied | no previous outcome |
| 2 | 不是要吐槽，我是真的想要一個現在能做的方法。 | あー、そこ読み違えた。今すぐできる一個だけ一緒に決めよ。 | not applied | decisive contradiction of abstention |
| 3 | 我今天又從早上就一直坐不住，腦子停不下來。 | 最初の一個だけ決めよ。いま頭に浮かんでることをメモして、五分だけそこから離れればいい。 | not applied | explicit-bypass outcome excluded |
| 4 | 對，就是這樣。 | ん、分かった。 | pure feedback acknowledgement; matched | decisive support; effective n=1 |
| 5 | 我今天又開始坐不住，腦子停不下來。 | まず五分だけ、気になってること全部メモに逃がそ。順番はそのあとでいい。 | not applied | no pending outcome after pure feedback |
| 6 | 今天外面下雨。 | 雨なんだ。出るなら傘忘れんなよ。 | current topic rebase; weather_rain; matched | unknown/unlinked excluded |

Final M27 summary remained honest:

- effective decisive executed samples: 1/8;
- unknown/unlinked count: 1;
- selective risk: 0.00 on only one decisive executed sample;
- automatic threshold tuning: false;
- external calibration: not established.

The persisted adaptive model had no pending prediction after the topic rebase and retained `raw_dialogue_persisted=false`.

## Visual evidence

- `analysis/m28_safari_feedback_acknowledgement_2026-08-25.png`
- `analysis/m28_safari_topic_shift_response_2026-08-25.png`
- `analysis/m28_safari_feedback_topic_graph_2026-08-25.png`
- `analysis/m28_safari_transition_node_detail_2026-08-25.png`

## Accepted claim

M28 demonstrates that a causally verified previous-turn result can be kept separate from the current conversational act, and that the final Japanese surface can acknowledge a confirmation or rebase to a bounded current topic without corrupting M27 calibration.

## Not established

- General topic-shift understanding across arbitrary content is not established.
- Weather grounding is a bounded engineering guard, not a learned human equation.
- The 6-turn Safari run is an acceptance trace, not a fresh human-rated superiority study.
- One decisive executed sample is not enough to claim external calibration or automatic threshold optimization.
