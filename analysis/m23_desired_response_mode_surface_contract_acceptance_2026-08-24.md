# M23 Desired Response Mode Inference and Surface Contract acceptance

Date: 2026-08-24  
Scope: bounded product mechanism for emotional-bid response form; not mind reading, universal pragmatic understanding, or evidence of superiority over a general LLM.

## 1. Product gap inherited from M22

M22 decides the broad task shape and route. It does not answer the user's central interaction question inside one emotional disclosure: does this person currently want listening, a practical step, companionship, playful teasing, physiological care, or a low-pressure clarification?

M18 already ranked internal policies, but the selected policy was not one typed contract joining task shape, evidence authority, alternatives, uncertainty, correction history, and final visible Japanese. M23 closes that product path.

## 2. Implemented mechanism

The live dialogue controller now materializes `uruha_desired_response_mode_m23` for M22 emotional bids and explicit corrections. It maps the existing response policies onto six user-centered modes:

| Mode | Operational meaning |
|---|---|
| `physiological_care` | respond to explicit sleep or physical-strain evidence first |
| `practical_help` | provide one bounded action the user can do now |
| `listening` | receive the disclosure without forcing a solution |
| `companionship` | stay with or share the moment |
| `playful_tease` | use bounded familiar teasing only with current or verified evidence |
| `low_pressure_clarification` | ask one short natural question when the desired response form is underdetermined |

The authority order is:

```text
current explicit correction
> current explicit request
> verified reversible interaction preference
> bounded pragmatic inference
> uncertainty-guarded clarification
```

The trace contains the selected mode, all six ranked alternatives, fixed structured evidence atoms, uncertainty and band, authority, utility margin, revoked policy, and the final surface contract. It does not copy raw dialogue into the M23 record and never promotes the inference into factual long-term memory.

`ensure_desired_response_mode_reaches_surface` commits an authorized mode to the actual Japanese reply, then audits the post-language-guard result. A graph label cannot claim success if the final visible reply performed a different response form.

## 3. Causal-scope correction defect found and repaired

The first real four-turn Safari run is retained as a failed validation. Turns 1–3 appeared correct, but turn 4 revealed that the old teasing preference survived inside the original arousal-disclosure scope. The later practical-help correction had updated only the immediate `relationship_play` scope, so a similar arousal disclosure revived the stale teasing mode.

M23 now records the structured scope IDs that causally supported a pending response. When that response is explicitly contradicted, the replacement atoms, dimensions, and scoped reliability are applied to those causal scopes as a reversible correction. The raw utterance is not copied. The trace exposes `causal_scope_repairs_m23` rather than hiding the repair.

After repair, both relevant scopes contain `humor_invitation=0.03` and `solution_request=0.98`; the next similar ambiguous disclosure selects practical help rather than resurrecting teasing.

## 4. Clean isolated Safari acceptance

Runtime isolation:

- database: `/tmp/uruha-m23-final.VCeoun/db`
- adaptive model: `/tmp/uruha-m23-final.VCeoun/adaptive.json`
- Web trace: `/tmp/uruha-m23-final.VCeoun/web.jsonl`
- local-only URL: `http://127.0.0.1:7866/?m23final=1`
- idle-visible proactive speech disabled;
- no production or formal long-term-memory database used.

### Turn 1: uncertainty is not treated as knowledge

```text
User: 我從早上就一直坐不住，腦子停不下來。
UruhaBrain: まあ、寝てないのか、考え事で止まんないのか、まずそこだけどっち？
```

```text
mode: low_pressure_clarification
authority: uncertainty_guarded_clarification
uncertainty: 0.95 high
alternatives: 6
surface: matched
brain work: 1.1491s
```

### Turn 2: explicit desire for teasing revokes the clarifier

```text
User: 不是要方法啦，我是在等你吐槽我，平常不是都會互相吐槽嗎？
UruhaBrain: あ、そっちか。さっきは読みすぎた。じゃあ言うけど、朝から脳内だけ二十四時間営業かよ。
```

```text
feedback: contradicted
revoked policy: calibrate_need
mode: playful_tease
authority: current_explicit_correction
surface: matched
brain work: 1.1330s
```

### Turn 3: a second correction replaces teasing with help

```text
User: 不，這次不是要吐槽，我是真的要一個現在能做的方法。
UruhaBrain: あー、そこ読み違えた。今すぐできる一個だけ一緒に決めよ。
```

```text
feedback: contradicted
revoked policy: playful_tease
mode: practical_help
authority: current_explicit_correction
causal scope repairs: 1
surface: matched
brain work: 1.1979s
```

### Turn 4: the repaired model governs the next similar disclosure

```text
User: 我今天又從早上就一直坐不住，腦子停不下來。
UruhaBrain: 今すぐなら、頭の中を一回メモに全部出して、五分だけ呼吸整えよ。
```

```text
mode: practical_help
authority: verified_reversible_preference
uncertainty: 0.34 low
surface: matched
general model: skipped
brain work: 1.2592s
```

The adaptive file has two decisive revisions, `raw_dialogue_persisted=false`, and no factual-memory write for the desired-response inference. The production database was not used.

Evidence images:

- `analysis/m23_safari_low_pressure_mode_2026-08-24.jpeg`
- `analysis/m23_safari_mode_correction_chat_2026-08-24.jpeg`
- `analysis/m23_safari_practical_repair_2026-08-24.jpeg`
- `analysis/m23_safari_causal_scope_repair_2026-08-24.jpeg`
- `analysis/m23_safari_mode_contract_graph_2026-08-24.jpeg`

The final four-turn card and the correction-turn full node graph are separate images. Expanding/scrolling the very large graph after the four-turn final state caused Safari to show its high-memory reload banner. This does not change the logged controller result, but it is an unresolved product defect and becomes M24's first target.

## 5. Automated evidence

M23-specific contracts cover six alternatives, uncertainty guard, real surface commitment, non-emotional isolation, causal-scope correction/reuse, graph nodes, comparison card, and raw-dialogue boundary:

```text
5 passed
```

Compatibility suite covering M23 through M16, functional/pragmatic/personhood loops, visible Japanese, idle suppression, proactive behavior, route logic, and observatory rendering:

```text
182 passed, 3 warnings
```

Python compilation and `git diff --check` pass.

## 6. What M23 proves and does not prove

M23 proves a bounded engineering claim: for the implemented emotional-bid cases, the real runtime exposes six response-form alternatives, selects under an explicit evidence hierarchy, commits the chosen mode to the final Japanese reply, accepts repeated correction, repairs the causal interaction scopes, and reuses the corrected mode without writing a private-state guess as factual memory.

It does **not** prove that these six modes exhaust human desired responses, that finite multilingual cues generalize to arbitrary conversation, that the system reads private mental state, that the chosen answer is always what a human wanted, or that it beats a strong LLM in blind preference. Current-mode correctness is verified only where the next user turn supplies decisive feedback; unknown feedback remains unknown.

## 7. Next product milestone

M24 is **Safari-Scale Progressive Runtime Graph and Trace Payload Budget**. The full M23 cognition trace is useful but grows into a page that Safari can reload for high memory use. M24 must keep the human-readable mode card and visible causal path, defer or summarize heavy node payloads until clicked, bound retained turn/detail data, prove the graph remains inspectable, and rerun a multi-turn Safari session without losing chat or triggering a high-memory reload. It must not remove traceability merely to make the page smaller.
