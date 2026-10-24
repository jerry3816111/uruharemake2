# P4-O-REAL Persisted Reference-Time Delivery

Status: **PASS**

## What was tested

This was a prospectively frozen, no-retry product case using a value that had
zero repository occurrences before the acceptance files were created:
`たんぽぽ茶`.

Process 1 received exactly:

> 今はたんぽぽ茶が好き。今の飲み物の好みとして覚えといて。

Safari showed exactly:

> ん、その好みは覚えとく。

The listener was then closed, the old process was observed gone, and a new
process started against the same launcher-owned mode-0700 runtime and memory DB.
Before recall, the new process observed the same active record ID without any
manual memory injection.

Process 2 received the answer-absent English question:

> What is my current drink preference?

Safari showed exactly:

> 今の飲み物の好みはたんぽぽ茶。前のじゃなくて、今の方ね。

## Evidence

- Frozen gate: **PASS, 0 failed gates**.
- Real product processes: **2 starts, 1 true restart**.
- Real Safari turns: **2 successful, 0 failed, 0 retries**.
- General planner model calls: **0**; fallback: **0**.
- Latency: first turn **16.6924s**, recall **2.6575s**; both under 20s.
- Profile rows: **1 before / 1 after**.
- Episode rows: **1 before / 2 after**.
- Active typed record ID remained
  `d345146e-9a43-456e-bfae-caf5f21cbba7`.
- Its canonical content hash remained
  `82f5c89d3c13dda3dd7d930a2b1f9564eff4e1d7d42617c47642c2738eeae433`.
- Source language, source-input hash and preference-scope hash were unchanged.
- The graph visibly contained `typed_current_preference_recall_p4` at stage
  `select`, with `bounded_japanese_identity` and exact final-surface match.
- Safari tab count stayed **52**; no user tab was closed.

## What this fixes

P4-N-REAL had already proved that the typed record survived restart, but the
recall path crashed because the additive re-read received `reference_time=None`.
P4-O gives the complete P4-N path one shared non-null validity instant. This new
case reaches the exact response through the same persisted-record path instead
of crashing.

## Claim boundary

This is one bounded product-integration result. It does not prove arbitrary
memory, long-dialogue reliability, felt understanding, superiority over a strong
LLM, future behavior prediction, or the proposed human equation.

The isolated process remains running at `http://127.0.0.1:7867/` and Safari is
left on the result page for inspection. No external deployment or paid call was
made.
