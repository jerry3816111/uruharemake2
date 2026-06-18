# UruhaBrain Chat Context Compaction

**Date:** 2026-05-01 JST
**Author:** Codex / GPT-5.5, xhigh development handoff
**Purpose:** Reduce future chat-token load without losing project direction or implementation context.

---

## 0. Non-Negotiable Working Rule

- Future serious development work for this project should use **GPT-5.5 with extra-high reasoning**.
- Smaller models may be used only for narrow mechanical work, log reading, or draft generation.
- If Gemini CLI is used, the intended division is:
  - **Codex:** project manager, architect, reviewer, final decision maker, test/quality owner.
  - **Gemini CLI:** implementation assistant for bounded tasks when explicitly delegated.
- Do not paste the entire old chat into future sessions. Read this file plus the current reports instead.

---

## 1. True Project Goal

This project is **not primarily a VTuber imitation project**.

The research goal is to engineer and evaluate a computational approximation of the human process from:

> hearing/reading an utterance -> perception -> memory activation -> working-memory filtering -> appraisal -> prediction error -> high/low road routing -> internal reasoning -> speech planning -> surface utterance -> memory update

The Ichinose Uruha / VTuber layer exists only as a light personality substrate so the system has a stable voice and does not output neutral assistant prose. It is not the main research contribution.

The key claim to preserve:

> The system is valuable because it makes hidden cognitive intermediates explicit, traceable, adjustable, and measurable.

---

## 2. Architecture Snapshot

Current architecture is a dual-brain cognitive dialogue system.

### Runtime event loop

- Event-driven loop handles:
  - user input events
  - timer tick events
  - internal urge events
- Boredom and social_need accumulate over idle time.
- Proactive speech is possible, with cooldown/sleep-mode protection.

### Perception and memory

- User input triggers memory retrieval.
- Long-term/recent memory is filtered into bounded working memory.
- Working memory is intended to approximate limited human short-term cognitive capacity.

### Prediction error and routing

- System predicts expected next user intent/valence.
- Actual input is compared with prediction.
- High PE or high threat can trigger low-road bypass.
- Normal input uses high-road deliberative planning.

### Left brain

- Responsible for intent, appraisal, ToM/BDI, candidate plans, and Bayesian-style reranking.
- Produces explicit plan fields such as:
  - intent
  - hidden_intent
  - user_belief
  - my_hidden_knowledge
  - user_expectation
  - response_mode
  - surface_act
  - core_message_jp
  - mood/trust impact
  - candidate plans and probabilities

### Right brain

- Responsible for Japanese surface realization and persona-toned output.
- Uses v10 LoRA when loaded, but many safety/humanness behaviors are controlled by deterministic and hybrid logic.
- Latest addition: Human Speech Realization Layer.

### Human Speech Realization Layer

Added in commit `a51c7bb Implement human speech realization layer`.

Purpose: make the final reply more like a human conversational act, not just a literal answer.

It constructs and traces:

- `dialogue_act`: what the utterance socially does, e.g. comfort, tease, boundary pushback, reference probe, memory accounting.
- `content_units`: semantic payload that must be expressed.
- `style_operators`: tone operations such as blunt_soft, tease_light, care_before_advice.
- `target_length`: rough spoken length.
- `prosody_hint`: pacing/energy hint.
- `turn_opening_potential`: whether the reply should leave a small conversational hook.
- `forbidden_repetition`: recent openings and generic frames to avoid.

Runtime now stores `last_speech_plan` and pushes it to the blackboard trace.

---

## 3. Current Main Files

### Core

- `uruha_brain_mac.py`
  - Main brain controller, memory manager, LeftBrain, RightBrain, event loop, self-monitoring, trace output.
- `uruha_runtime.py`
  - Runtime state dataclasses, event state, drive state, prediction buffer, trace containers.
- `project_paths.py`
  - Centralized paths for datasets, reports, cache, logs.

### UI / interfaces

- `uruha_web_ui.py`
  - Web UI and inspection surface.
- `start_uruha_live.py`
  - Live entrypoint; not the current research focus.
- `uruha_senses.py`
  - STT/TTS related integration; currently secondary.

### Evaluation

- `run_human_speech_layer_eval.py`
  - Evaluates the Human Speech Realization Layer.
- `run_cognitive_mediator_eval.py`
  - Evaluates cognitive mediator flow.
- `stress_eval_10000.py`
  - 10k stress test.
- `build_unified_eval_summary.py`
  - Builds unified metrics summary.
- `build_research_vnext_90plus_report.py`
  - Builds research 90+ readiness report.
- Other important evals:
  - `cognitive_architecture_eval.py`
  - `runtime_dynamics_eval.py`
  - `long_dialogue_memory_eval.py`
  - `reply_diversity_eval.py`
  - `eval_v2_human_answer.py`
  - `run_formal_brain_benchmarks.py`

### Reports

- `reports/human_speech_layer_eval_report_zh.md`
- `reports/cognitive_mediator_eval_report_zh.md`
- `reports/stress_eval_report_10000.json`
- `reports/unified_eval_summary_zh.md`
- `reports/research_vnext_90plus_diagnostic_report_zh.md`

---

## 4. Latest Known Metrics

After Human Speech Realization Layer commit `a51c7bb`:

### Human Speech Layer

- case_count: 6
- pass_rate: 1.0
- speech_plan_presence_rate: 1.0
- dialogue_act_match_rate: 1.0
- semantic_anchor_hit_rate: 1.0
- content_density_pass_rate: 1.0
- english_leak_rate: 0.0

### Cognitive Mediator Eval

- case_count: 5
- pass_rate: 1.0
- attention_frame_rate: 1.0
- appraisal_frame_rate: 1.0
- self_monitor_rate: 1.0

### 10k Stress

- overall_pass_rate: 1.0
- unique_reply_ratio: 0.1306
- top_20_reply_concentration: 0.2359
- forbidden_leak_rate: 0.0

### Research 90+ Diagnostic

- research_cognitive_readiness_score: 95.66
- research_90_plus_defensible: true
- surface_dialogue_alignment_score: 85.32

Important interpretation:

- The cognitive architecture is research-defensible at 90+ by the current internal rubric.
- Surface dialogue is much improved but still below the cognitive architecture score.
- Formal DailyDialog dialog-act/emotion metrics may remain lower because the system is intentionally persona/pragmatics-oriented, not generic DailyDialog imitation.

---

## 5. Historical Development Compression

### Early stage

- Project began as Uruha right-brain LoRA experiments.
- V7 overfit badly due to aggressive LoRA settings and small dataset.
- V8/V10 improved, but the user realized the real issue was not only the right-brain model; the whole left-brain/right-brain pipeline needed to produce better plans.

### Major pivot

The project shifted from “make Uruha imitate a VTuber” to:

> implement a human-like cognitive pipeline and use a persona only as the surface soul.

### Middle stage

Added or refined:

- working memory
- high/low road routing
- prediction error
- emotion/trust state
- Bayesian multi-plan selection
- BDI / ToM scratchpad
- background consolidation
- autonomous drive loop
- traceable runtime blackboard
- regression and stress evals

### Gemini/Codex collaboration stage

- Gemini was used as implementation assistant for bounded tasks.
- Codex acted as PM/reviewer/final integrator.
- Several UI regression trust issues were reviewed/fixed around stale diff reports and baseline provenance.
- Root project reports and README were added/cleaned.

### Current stage

- Main bottleneck moved from “does the brain route correctly?” to “does the speech feel like human conversation?”
- Human Speech Realization Layer was implemented to bridge cognition to utterance.

---

## 6. Current Strengths

- Architecture is explicit and traceable.
- High/low road and PE routing are testable.
- Working-memory and memory-causal tests exist.
- 10k stress stability is strong.
- Human speech layer now makes the right brain expose social speech intent before wording.
- Reports are reproducible and can be regenerated.

---

## 7. Current Weaknesses / Do Not Ignore

### 1. Monolithic core file

`uruha_brain_mac.py` is too large. It is workable but expensive for future agents.

Best future refactor:

- `memory_engine.py`
- `leftbrain_planner.py`
- `rightbrain_speech.py`
- `runtime_loop.py`
- `evaluation_hooks.py`

Do not do this refactor casually; first lock tests.

### 2. Some metrics are internal proxies

Research score is useful, but not equivalent to biological validation.

For teacher/research presentation, clearly say:

- This is an engineering approximation of cognitive functional stages.
- It is not a direct neural simulation.
- The value is observability and testability of intermediate cognitive-like states.

### 3. Human feedback regression data is still underpopulated

The real next scientific bottleneck is true human-labeled failure cases.

Need at least:

- 50 human annotations
- 30 replayable regression cases
- taxonomy coverage for low-density, missed-vibe, ghost-memory, wrong-register, generic-refusal

### 4. Surface speech still deserves real conversation QA

Even if 10k metrics are good, humans can still notice:

- slightly unnatural Japanese
- too much defensive structure
- reply is correct but not chatty
- missing cultural joke
- too much “answering” instead of co-presence

---

## 8. Recommended Next Work

### Phase A: preserve and reduce context load

1. In new chats, paste only the bootstrap section below.
2. Ask the agent to read:
   - this file
   - `reports/research_vnext_90plus_diagnostic_report_zh.md`
   - `reports/unified_eval_summary_zh.md`
   - recent git log
3. Avoid pasting old conversation history.

### Phase B: human feedback loop

1. Use Web UI to collect real conversations.
2. Mark bad replies manually.
3. Convert them into regression cases.
4. Patch only from real failure clusters.
5. Run diff report after every patch.

### Phase C: modularization only after regression safety

Before splitting the giant file:

1. Run all core evals and save reports.
2. Create a baseline snapshot.
3. Split one module at a time.
4. Require zero metric regression.

### Phase D: academic report cleanup

The research report should emphasize:

- human cognitive-process approximation
- functional decomposition
- traceability
- reproducibility
- limitations
- why persona is only a surface stabilizer

If discussing Chomsky:

- Present Universal Grammar as historically influential.
- State that strong nativist interpretations are contested by usage-based, statistical learning, constructivist, and cognitive-functional approaches.
- Avoid saying it was simply “proven false”; the accurate position is “partly revised, heavily debated, and no longer uncontested as the sole explanation of language acquisition.”

---

## 9. Minimal Bootstrap Prompt For New Chat

Use this in a fresh Codex/Gemini session:

```text
You are working on /Users/jerrychang/Desktop/uruharemake2.
Read CHAT_CONTEXT_COMPACTION_2026-05-01.md first. Do not ask me to paste the old chat.
This project is not mainly VTuber imitation; it is a research/engineering attempt to approximate the human cognitive process from input to utterance.
Use GPT-5.5 with extra-high reasoning for serious development decisions.
Latest important commit: a51c7bb Implement human speech realization layer.
Before coding, inspect git status and avoid touching unrelated dirty files.
For validation, prefer:
- python3 -m py_compile relevant files
- run_human_speech_layer_eval.py
- run_cognitive_mediator_eval.py
- stress_eval_10000.py when needed
- build_unified_eval_summary.py
- build_research_vnext_90plus_report.py
Do not optimize only for benchmark numbers; preserve conversational human-likeness and traceability.
```

---

## 10. Commands For Quick Validation

```bash
cd /Users/jerrychang/Desktop/uruharemake2
python3 -m py_compile uruha_runtime.py uruha_brain_mac.py project_paths.py
URUHA_SKIP_AUTO_VENV=1 /Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_human_speech_layer_eval.py
URUHA_SKIP_AUTO_VENV=1 /Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_cognitive_mediator_eval.py
URUHA_SKIP_AUTO_VENV=1 /Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python stress_eval_10000.py
URUHA_SKIP_AUTO_VENV=1 /Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python build_unified_eval_summary.py
URUHA_SKIP_AUTO_VENV=1 /Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python build_research_vnext_90plus_report.py
```

---

## 11. What Future Agents Should Not Do

- Do not re-litigate whether the project is “about Ichinose Uruha.” It is not the main point.
- Do not add new cognitive-science buzzwords unless they become testable data structures or metrics.
- Do not modify TTS/Whisper/live pipeline unless the user explicitly switches back to live integration.
- Do not delete memory DB or old git history.
- Do not flatten the system back into a single prompt.
- Do not hide uncertainty in reports; separate engineering proxy metrics from biological claims.

---

## 12. Current Best One-Sentence Description

UruhaBrain is a traceable dual-brain cognitive dialogue architecture that approximates human-like response formation through working memory, appraisal, prediction error, high/low-road routing, BDI planning, Bayesian candidate selection, human speech realization, and memory consolidation, with a lightweight persona layer used only to make the final utterance feel embodied.
