# M25 Cross-Lingual Explicit Desired-Response Authority acceptance

Date: 2026-08-24  
Scope: current-turn explicit requests for how the user wants to be answered. This is a bounded multilingual surface-request mechanism, not general human understanding.

## 1. Retained failure from M24

The M24 six-turn Safari run proved the progressive graph remained stable, but its final English input — `I still cannot settle down. Just stay with me for a minute, okay?` — was classified as low-pressure clarification. A prior Chinese `先聽我說` turn reached a reasonable listening reply through the older correction mechanism while the typed M23 mode remained inactive.

The defect had two causes:

1. explicit listening/companionship requests were distributed across finite M16–M23 atoms and route cues rather than represented as one current-turn authority contract;
2. M23 eligibility depended mainly on M22 emotional/correction task shape, so an English request classified as `general_conversation` could miss the desired-response contract.

## 2. Implemented M25 mechanism

`uruha_cross_lingual_explicit_desired_response_m25` now separates five explicit response forms in Chinese, English, and Japanese:

- listening;
- companionship;
- practical help;
- playful teasing;
- low-pressure clarification.

The classifier records only typed cue IDs, language, mode, negated modes, alternatives, confidence, and an evidence digest. It does not place the raw utterance in adaptive persistence.

Negation is resolved before selection. For example:

- `不要吐槽，告訴我現在能做的方法` removes teasing, then selects practical help;
- `I do not want advice. Just listen to me.` removes practical help, then selects listening;
- `質問しないで、そばにいて` removes clarification, then selects companionship.

A current explicit request is stronger than reversible learned interaction preference. It forces the matching M18 policy, supplies a natural Japanese surface, enters the M23 mode contract even when M22 says `general_conversation`, and is audited again after the final Japanese-language guard.

Clear self-harm/risk phrases block M25 surface authority so a fixed companionship response cannot override a protected route. This is only a guard against M25 interference, not a broad safety evaluation.

## 3. Product integration

The first M25 Safari run selected the correct companionship surface but still spent 9.25 seconds in the general planner. That failure is retained. M25 was then connected to the M18 guarded adaptive fast path: an authoritative explicit response form now skips the general model while preserving functional hypothesis, pragmatic attunement, longitudinal model, public-persona appraisal, visible-Japanese guard, and M24 graph budgets.

The runtime graph adds two causal nodes:

```text
USER SIGNAL
→ explicit_desired_response_m25
→ desired_response_mode_m23
→ explicit_desired_response_surface_m25
→ UTTERANCE
```

The comparison card exposes detected mode, matched input language, negated-mode count, final surface status, M23 authority, actual route, model-call status, timing, and M24 payload budget.

## 4. Clean six-turn Safari result

The final session used a new DB, adaptive file, and log under `/tmp/uruha-m25-final.QzYXbj`.

| Turn | Evidence | Selected result | Route / model | Cognitive total |
|---:|---|---|---|---:|
| 1 | ambiguous Chinese arousal | low-pressure clarification | adaptive fast / skipped | 0.0175 s |
| 2 | Chinese explicit practical correction | practical help, matched | adaptive fast / skipped | 0.0168 s |
| 3 | similar ambiguous arousal | verified practical preference reused | adaptive fast / skipped | 0.0197 s |
| 4 | English `stay with me` | companionship, current explicit, matched | adaptive fast / skipped | 0.0179 s |
| 5 | Japanese no-question + stay | clarification negated; companionship matched | adaptive fast / skipped | 0.0200 s |
| 6 | Chinese no-company + listen | companionship negated; listening matched | adaptive fast / skipped | 0.0215 s |

The final visible replies for turns 4–6 were natural Japanese. Turn 4 demonstrates the key authority comparison: an already verified practical preference existed, but the current English companionship request overrode it rather than being forced into the old model.

At turn 6, the complete local turn was 5,321,980 bytes while the M24 browser turn was 312,914 bytes. The progressive graph retained 65 nodes and 52,500 bytes of detail without a Safari high-memory reload.

None of the six raw test utterances appears in the adaptive JSON.

## 5. Automated evidence

M25-specific contracts cover three languages, negation, current-over-stale authority, real final Japanese, protected-risk blocking, graph causality, surface audit, and M24 budgets:

```text
6 passed
```

Focused compatibility across M16–M25 and the functional/pragmatic/personhood, Japanese, proactive, route, and observatory stack:

```text
204 passed, 3 warnings in 5.89s
```

Python compilation and `git diff --check` pass.

Safari evidence:

- `analysis/m25_safari_cross_lingual_six_turn_chat_2026-08-24.jpeg`
- `analysis/m25_safari_cross_lingual_graph_2026-08-24.jpeg`
- `analysis/m25_safari_explicit_surface_node_2026-08-24.jpeg`

## 6. What M25 proves and does not prove

M25 proves a bounded product claim: for the implemented Chinese, English, and Japanese explicit response requests, current evidence can override stale learned preference, negated response forms are filtered before selection, the selected mode reaches the final Japanese reply, and the request uses the guarded fast path without deleting traceability.

It does not prove paraphrase-complete multilingual semantics, implicit desired-response understanding, correct interpretation of mixed social intent, human felt-understanding superiority, open-world safety, or a solved human-brain equation. The semantic cue inventory remains finite and manually specified.

The next product milestone is **M26 Outcome-Calibrated Implicit Desired-Response Distribution and Abstention**. It must stop treating utility-ranked alternatives as if they were calibrated beliefs: materialize a normalized mode distribution for non-explicit turns, attach scoped outcome reliability, execute an implicit mode only when evidence and calibration pass a preregistered product gate, and otherwise choose low-pressure clarification. Subsequent user feedback must visibly support, contradict, or leave the prediction unknown.
