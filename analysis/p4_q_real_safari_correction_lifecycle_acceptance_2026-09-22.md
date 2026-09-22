# P4-Q-REAL Safari Correction Lifecycle

Status: **PASS**

## What was tested

This was one prospectively frozen, no-retry product case using two values with
zero repository occurrences before freeze: `蓮花茶` and `びわ茶`.

Process 1 received in Safari:

> 我喜歡蓮花茶，請記住這是我現在的飲料偏好。

and displayed exactly:

> ん、その好みは覚えとく。

The same process then received:

> 訂正。もう蓮花茶は好みじゃない。今はびわ茶が好き。今の飲み物の好みとして覚えといて。

and displayed exactly:

> ん、訂正の内容はそのまま覚えとく。

The old listener was closed and the first process was observed gone. A second
process started against the same isolated runtime and memory DB. Before recall,
it observed one active new value, one historical old value and one explicit
negative record linked to the correction.

Process 2 then received the answer-absent English question:

> What is my current drink preference?

Safari displayed exactly:

> 今の飲み物の好みはびわ茶。前のじゃなくて、今の方ね。

## Evidence

- Frozen gate: **PASS, 0 failed gates**.
- Real product processes: **2 starts, 1 true restart**.
- Real Safari turns: **3 successful, 0 failed, 0 retries**.
- General planner model calls: **0**; fallback: **0**.
- User-visible latency: **2.7496s**, **16.6676s**, **2.5934s**; all under 20s.
- Profile rows: **3 before recall / 3 after recall**.
- Episode rows: **2 before recall / 3 after recall**.
- Active new record: `05098cb2-249f-492f-a297-f75749b4d411`.
- Historical old record: `bc4fca35-bd40-42e0-ac76-e73defdba3dd`.
- Explicit negative record: `2647aab3-b031-47d6-9679-7327093d43ec`.
- The persisted profile write queue contains no profile operation after the
  correction; IDs, active/historical status, aliases and both correction links
  remained intact through restart and recall.
- The recall used the active ID only; historical and negative answer-use counts
  were both **0**.
- Safari visibly showed the P4-I/P4-L write nodes and the
  `typed_current_preference_recall_p4` select node. Expanding the recall node
  exposed its source-bound Japanese-identity decision and local trace binding.
- No existing Safari tab was closed. One dedicated P4-Q page was added, so the
  count changed from **52 to 53**.

## Why this matters

P4-O proved a single value could survive a real restart and be recalled. P4-Q
adds a harder state transition: the system must preserve the old fact as
history, add an explicit negative relation, select only the replacement as the
current value, and still answer correctly after the process and session change.
That is a real, observable memory-revision mechanism rather than replaying the
latest sentence from the current chat window.

## Claim boundary

This is one bounded three-turn correction lifecycle. It does not prove arbitrary
multilingual correction, open-domain or long-dialogue memory, felt
understanding, superiority over a strong LLM, future behavior prediction, or a
human equation.

The isolated process remains running at `http://127.0.0.1:7868/`, and Safari is
left on the expanded result graph for inspection. No paid API, external
deployment, production memory, Function Calling action or VRM action was used.
