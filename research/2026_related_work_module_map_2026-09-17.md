# 2026 related-work module map for UruhaBrain

Checked: 2026-09-17. This is a non-exhaustive primary-source search, not a world-first certificate.

## Research question retained

UruhaBrain asks whether public historical observations plus current context can support an interpretable, updateable individual-state model that predicts a person's response or behavior in unseen future situations better than a matched LLM without that model. 一ノ瀬うるは is the reference-person case, not the general architecture.

The defensible novelty candidate is the evaluated combination, not any one component:

`public evidence -> provenance-bound memory/person state -> context-conditioned probabilistic response or behavior prediction -> temporal ground truth -> prediction error and correction`

Do not write that no prior work has any of these ideas. A safer statement is:

> In the non-exhaustive literature search documented here, we did not identify one prior system that jointly evaluates public-evidence reconstruction of a specific person, persistent and correctable cognitive state, source-bounded response realization, and temporally blind future-behavior prediction under a matched-model ablation.

That sentence remains a search result, not a guaranteed claim of global priority.

## What can be cited and what it supports

| Work | Publication status | Component that UruhaBrain may reuse or compare | What it does not prove for UruhaBrain |
|---|---|---|---|
| [PersonaForge](https://aclanthology.org/2026.findings-acl.386/) | Findings of ACL 2026 | Three-layer personality architecture, dual-process workspace, 50-turn drift measurement, human correlation, and token-overhead reporting | It does not prove public-person reconstruction or temporally blind future behavior prediction |
| [Beyond Static Persona Consistency: Dynamic Persona Coherence](https://aclanthology.org/2026.acl-long.1336/) | ACL 2026 long paper | Separate long-term identity, mid-term accumulated meaning/stress, and short-term affect; closed-loop critic/repository/suppressor correction | Its correction target is persona coherence, not verified prediction of a real person's unseen future |
| [ThinkPersona](https://aclanthology.org/2026.acl-long.449/) | ACL 2026 long paper | Persona graphs linking life trajectories, values, relationships, and events; grounded Question-Reasoning-Answer supervision | Interview-derived persona graphs are not the same as incomplete public evidence, and the task is role-playing rather than future-event forecasting |
| [Memory-Driven Role-Playing](https://aclanthology.org/2026.findings-acl.1175/) | Findings of ACL 2026 | Four diagnostic stages—Anchoring, Selecting, Bounding, Enacting—for checking whether persona memory is retrieved and used, plus bilingual MRBench | It evaluates persona-knowledge use, not UruhaBrain's full state/prediction/correction loop |
| [PersonaVLM](https://openaccess.thecvf.com/content/CVPR2026/html/Nie_PersonaVLM_Long-Term_Personalized_Multimodal_LLMs_CVPR_2026_paper.html) | CVPR 2026 | Chronological multimodal memory extraction, retrieval-based multi-turn reasoning, evolving personality alignment, and Persona-MME long-term evaluation | It personalizes an assistant to a user; it is not evidence that a public reference-person's future behavior can be reconstructed |
| [Persistent Personas?](https://aclanthology.org/2026.eacl-long.246/) | EACL 2026 long paper | Over-100-round evaluation of persona fidelity, instruction-following, and safety; evidence that long-dialogue degradation must be measured | It diagnoses persistence and trade-offs, not the UruhaBrain mechanism or advantage |
| [PsyMem](https://aclanthology.org/2026.tacl-1.24/) | TACL 2026 | Fine-grained psychological indicators and explicit memory-control alignment; role-play human-likeness/fidelity evaluation | Novel-derived characters and aligned training do not validate public-person facts or causal latent-state claims |
| [HumanLLM](https://aclanthology.org/2026.acl-long.1783/) | ACL 2026 long paper | Psychological patterns as interacting causal forces; pattern-level checklists that separate simulation fidelity from socially desirable output | Its scenarios are synthetic and do not establish one real individual's hidden mental variables |
| [Action-Guided Attention for Video Action Anticipation](https://proceedings.iclr.cc/paper_files/paper/2026/hash/5354d0b74b75801015e9d1e8326e7c19-Abstract-Conference.html) | ICLR 2026 | Past actions -> latent-intention inference -> future action anticipation; unseen-test generalization and counterfactual analysis | It forecasts video actions, not a persistent person's language, memory, and relationship-conditioned behavior |
| [SPIRIT](https://arxiv.org/abs/2603.27056) | arXiv preprint, not treated here as peer-reviewed conference evidence | Public social-media posts -> semi-structured traits, beliefs, values, lived experience -> specific-person opinion simulation | The authors frame it as simulation rather than prediction; it does not supply UruhaBrain's full temporal memory and correction loop |

## Direct consequences for implementation and evaluation

1. Use PersonaForge and Persistent Personas to define long-dialogue drift, persona fidelity, instruction following, safety, and actual token overhead. Do not claim that a 50-turn replay alone proves human understanding.
2. Use Memory-Driven Role-Playing's Anchoring/Selecting/Bounding/Enacting split to diagnose memory failure. A good final answer cannot hide a wrong source selection.
3. Use Dynamic Persona Coherence, ThinkPersona, PsyMem, and HumanLLM to justify separating stable identity, accumulated/relationship state, short affect, evidence-grounded personal history, and interacting cognitive factors. Each state still needs an operational definition and ablation.
4. Use PersonaVLM only for the multimodal memory pipeline and long-term personalization comparison. Its benchmark result cannot be copied as evidence about Uruha.
5. Use Action-Guided Attention to justify temporally blind anticipation and counterfactual inspection. The actual UruhaBrain task must evaluate probability distributions over future behavior categories, not exact future sentences or an hour-long generated video.
6. Use SPIRIT as the closest public-data persona-construction comparison, but label it a preprint and preserve the difference between simulation and future prediction.

## Next falsifiable experiment

### Task A: context-conditioned response forecasting

- Historical public data is available only before a frozen cutoff.
- The future situation is shown, but the reference person's actual response is hidden.
- Conditions use the same base model and resource cap:
  1. current context only;
  2. persona prompt;
  3. retrieved public history;
  4. full UruhaBrain state and memory.
- Output is a preregistered probability distribution over response/speech-act categories plus bounded rationale variables. The actual response is unlocked only after commitment.

### Task B: open-loop future behavior forecasting

- A target public video is split into observed context and hidden future by time.
- Historical persona construction uses only material published before the target cutoff.
- Prediction horizons should include short and long windows rather than only `2 hours -> 1 hour`.
- Score topic, action, speech act, interaction target, and coarse affect separately. Exact wording is not a success criterion.
- Compare degradation as the horizon increases and run ablations for memory, state, relationship, and persona components.

### Failure interpretation

- If context-only is equal or better, the added cognitive state has not shown predictive value and should be simplified.
- If retrieval alone matches the full system, the state variables have not shown incremental value.
- If gains disappear on temporal holdout or another person, the result is case-specific rather than a general person-modeling framework.
- If outputs are plausible but probabilities are uncalibrated, the system has a generation demo, not a reliable forecasting model.

