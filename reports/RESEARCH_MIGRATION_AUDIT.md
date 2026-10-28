# Research migration audit

Date: 2026-08-15  
Master specification SHA-256: `6f0a12f1ed5992baebae22ae10b3f614c54317bc575a86ce37761b49f85dc389`  
Repository: `/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`  
Branch / base: `codex/v2-15-pragmatic-research-showcase` / `4a06380`  
Audit mode: read-only repository inspection plus scoped contract tests; no old lock or runtime was rewritten to improve audit status.

## Executive conclusion

The repository already contains substantial memory, provenance, persona-governance, state-transition, causal-intervention, runtime-trace, Japanese-realization, preregistration, and experiment-lock machinery. It is not a blank chatbot project.

It does **not** yet implement the master specification's primary experiment: calibrated prediction of unseen future public behavior under strict temporal holdout against B0–B5 baselines. The strongest blocker is not model code or GPU. Formal target-person behavior data remain data-empty behind an intentional two-human reliability gate.

The correct migration is therefore incremental:

1. retain V2.11–V2.22 as reusable subsystem evidence;
2. introduce a clean research namespace for temporal datasets, baselines, probability metrics, and experiment registry;
3. complete M1 temporal benchmark infrastructure before adapting the current hybrid runtime;
4. never relabel replay, synthetic fixtures, or persona-style output as future-behavior evidence.

## 1. What the current project actually implements

### Repository shape

- 3,642 tracked files.
- 1,283 tracked Python files, including 605 `test_*.py` files.
- 545 tracked experiment configs, 114 tracked datasets, and 1,658 tracked reports.
- Only one tracked file under `docs/`; there is no root README or coherent install/run entrypoint for the research program.
- Most experiments live as versioned flat top-level scripts rather than importable packages.
- The current safe worktree also contains uncommitted V2.11–V2.22 research artifacts and runtime/UI modifications. The original dirty checkout was not inspected or modified for migration work.

### Runtime architecture

`uruha_brain_mac.py` is a 17,291-line cross-cutting runtime containing `MemoryManager`, `LeftBrain`, `RightBrain`, and `UruhaBrainV4_Mac`. It currently supports:

- multi-layer memory and profile state;
- working-memory ranking and provenance;
- signal interpretation and cognitive planning;
- prediction-error and pragmatic/user-model prototypes;
- response self-monitoring and repair;
- deterministic memory-grounded visible replies;
- Japanese/persona surface policy;
- episode writeback and runtime trace.

`uruha_web_ui.py` is a 3,007-line product/demo surface. `uruha_runtime.py` wraps the runtime lifecycle. This architecture is useful for later full-pipeline demonstration but is too coupled to serve directly as the new research package.

### Existing research mechanisms

- `memory_evidence_ledger.py`: grounded evidence notes, ledger reconciliation, temporal-validity-style event handling, and answer views.
- `memory_item_causal_intervention_v1.py`: item-level causal memory interventions and result accounting.
- `relation_bound_event_graph_v56.py`: typed relations and scope handling, but primarily for utterance/action commitment rather than longitudinal person-event storage.
- `uruha_personhood_loop.py`, `uruha_functional_understanding.py`: user hypotheses, verification, calibration, longitudinal profile, pragmatic state, and response-planning prototypes.
- `desired_response_comparison_v2_16.py`, `human_pragmatic_comparison_v2_14.py`: same-model comparison, fixed output contracts, candidate strategies, token accounting, and blind-packet infrastructure.
- V2.17–V2.22: long-dialogue memory replay, preference update/withdrawal, false-memory controls, runtime trace, and bounded comparison against recent/full-context LLMs.

### Existing public-persona governance

The repository has stronger pre-content governance than the current runtime architecture:

- 3 official Uruha calibration-source reservations.
- 30 deterministic target-calibration sampling slots.
- 4 sealed final-holdout source reservations.
- 9 matched-contrast sources and a 90-slot contrast sampling frame.
- event-coding schema, codebook, manual, private-ledger tool, rights-policy bindings, and holdout access rules.
- explicit prohibition on raw media/transcript storage, private-motive inference, prompt/memory/training use, model execution, and final-holdout unsealing before gates pass.

The current formal counts are nevertheless:

- target behavior events: `0`;
- contrast behavior events: `0`;
- independent human coders: `0`;
- reliability reports: `0`;
- target persona prediction scores: `0`;
- holdout content reviews: `0`.

V7 only authorizes two distinct consenting humans to complete the same frozen 18-slot reliability pilot. V9 target calibration remains blocked until that reliability gate passes.

## 2. Parts that already match the master specification

1. Strong provenance culture: path/digest bindings, frozen configs, result locks, source IDs, and failure retention.
2. Public-persona boundary: public observable behavior is separated from private identity and hidden mental state.
3. Memory records and source trace: retrieval, passed-to-decision evidence, profile state, and visible anchors can be inspected.
4. Configurable or explicit mechanisms exist for memory ranking, validity, correction, relation scope, and selected interventions.
5. Repeated use of preregistration, single-changed-variable contracts, isolated DBs, transport accounting, and resource measurement.
6. Same-model comparison and token-audit utilities exist in V2.14–V2.22.
7. A graphical runtime observatory already demonstrates state flow and retained failures.
8. Japanese realization and output-safety boundaries are comparatively mature for the Uruha demonstration layer.

## 3. Parts that reflect the old research goal

1. The principal runtime predicts a conversational reply, not a calibrated distribution over future behavior classes.
2. State variables are optimized mainly for immediate conversational usefulness, desired-response strategy, or visible reply repair.
3. Most datasets are synthetic contracts, development replays, language/action boundary cases, memory QA, or persona-surface probes.
4. The web UI centers chat turns and memory flow rather than prediction-time cutoff, hidden future, forecast distribution, observed outcome, and calibration error.
5. Evaluation often measures contract pass/fail or answer correctness; Brier, NLL, ECE, reliability diagrams, and rolling temporal performance are absent from the main pipeline.
6. Uruha-specific behavior/style logic crosses LeftBrain, RightBrain, visible guards, and Web UI, making architecture/person parameters difficult to separate.

These components should be retained as subsystem evidence and compatibility tests, not used as the main proof of the new research objective.

## 4. Reusable modules

| Existing asset | Reuse in new architecture | Required boundary |
|---|---|---|
| Public-persona manifests and governance locks | source registry, rights boundary, sealed partitions | do not unseal or execute models before human gate |
| Public event-coding schema | seed for temporal event/ground-truth record | add prediction time, available-history cutoff, actual behavior labels, evidence type |
| `memory_evidence_ledger.py` | provenance and time-valid evidence reconciliation | separate benchmark evidence from answer-generation logic |
| Memory/profile state and validity tests | candidate `M`, `V`, and relation state adapters | no direct import of entire 17k-line runtime into benchmark core |
| Relation/event scope modules | candidate subject/relation/object extraction | generalize beyond VRM commitment and language-specific rules |
| Causal intervention runners | intervention result schema and artifact accounting | intervention must change behavior probability, not only an internal anchor |
| V2.14/V2.16 comparison harness | same-model execution, token accounting, blind packet patterns | replace desired-response labels with behavior distributions |
| Web observatory components | graphical timeline, lanes, trace cards | product/demo code must consume research artifacts read-only |
| Japanese guard and persona surface | optional Uruha language-realization layer | secondary metric only; cannot affect behavior ground truth |

## 5. Modules to refactor

1. Extract research-neutral schemas and metrics into a new package rather than extending `uruha_brain_mac.py`.
2. Add an adapter boundary between existing Uruha runtime state and the future `HumanState` schema.
3. Separate event semantic extraction from state transition and behavior prediction.
4. Separate probability prediction from language realization.
5. Replace flat ad-hoc result writing with a single experiment artifact contract.
6. Make Web visualizations load immutable result artifacts instead of recomputing or mutating formal experiments.
7. Introduce person parameters and evidence as data/config, removing target-specific rules from architecture code over time.

## 6. Modules to deprecate from the primary research path

Deprecation here means “not primary evidence,” not deletion:

- fixed replay demonstrations as evidence of general capability;
- exact-string answer scorers as the primary behavior metric;
- a single aggregate “research maturity” score combining incompatible evidence levels;
- prompt-only post-hoc explanations that are not tied to intervention effects;
- UI-only pass labels not bound to frozen metrics;
- repeated same-case beverage remediation as evidence of semantic generalization;
- VRM, voice, proactive speech, and function-calling expansion before temporal prediction is valid.

## 7. Missing research-critical components

1. A versioned longitudinal target dataset with prediction times and observable future outcomes.
2. Strict temporal dataset builder and index-level future-leakage validator.
3. Frozen hierarchical behavior taxonomy with ambiguity/multi-label policy.
4. B0–B5 baseline interface under documented information and compute budgets.
5. A common probability-output schema before language realization.
6. Brier, NLL, ECE, reliability diagrams, Top-k, Macro/weighted F1, MRR/NDCG.
7. Person-independent `HumanState` schema and timestamped snapshots.
8. Explicit/configurable and learned transition-model families T0–T3.
9. Hybrid behavior predictor trained or estimated from data rather than arbitrary final weights.
10. Full component ablation and probability-level intervention runner.
11. Rolling cutoff evaluation, historical-data scaling, and second-person transfer.
12. One reproducible CLI and standardized result directory.

## 8. Data leakage risks

- Current public source manifests are partition-aware, but no end-to-end temporal dataset builder verifies every memory, summary, embedding, prompt example, and parameter against prediction time.
- Foundation models may already know public Uruha events from pretraining.
- Several existing development observations were reviewed in 2026 and cannot automatically serve as evidence available at an earlier prediction cutoff.
- Existing static persona prompts may summarize observations that occur after a test event.
- A later public post or clip may retrospectively describe an earlier event.
- Reusing frozen holdouts across multiple remediation cycles creates development exposure even if the raw source stays sealed.
- Model output, scorer design, and human coding must remain mutually hidden until their respective freezes.

Required mitigation: outcome-stripped event records, evidence-only mode, per-record temporal assertions, index manifest hashes, access logs, prompt/config binding, and invalidation of any run with leakage.

## 9. Evaluation weaknesses

1. The formal Uruha behavior dataset is currently empty.
2. Existing V2.22 comparison has five checkpoints in one preference-revision family; it is not an independent semantic or temporal holdout.
3. Some baseline outputs are reused across remediation versions rather than freshly regenerated.
4. Existing scorer negation parsing mislabels some semantically negative answers.
5. Human felt-understanding ratings and target-person behavior annotations are incomplete.
6. Current benchmarks often mix architecture mechanics, language contracts, replay, and human evidence in adjacent reports.
7. Resource comparisons are frequently non-token-parity because the hybrid runtime emits large hidden planning payloads.
8. Existing explanation traces show retrieval and decision passage but not always a full-generation probability change under removal/replacement.

## 10. Reproducibility audit

Scoped public-persona contract command:

```text
python -m unittest -q [16 public-persona manifest/governance/coding modules]
```

Result on 2026-08-15:

```text
Ran 203 tests
202 passed, 1 failed
```

The single failure is `test_public_persona_observation_v2.PublicPersonaObservationV2Tests.test_harness_lock_hashes_match`. The frozen V2 harness expects `project_paths.py` SHA `aaeddf...`, while current HEAD contains `9a5621...`. The observation auditor, tests, preregistration, source registry, and observation dataset still match their frozen hashes. This is historical cross-experiment path-registry drift, not evidence that the formal target dataset contains behavior labels. The old lock was intentionally not rewritten during audit.

## 11. Proposed migration phases

```text
Phase 0  research definition and claim boundary        [implemented in migration worktree]
Phase 1  repository/data/evaluation audit              [this report]
M1       temporal benchmark + B0–B3 + observatory
M2       B4/B5 strong-history baselines
M3       structured memory and HumanState adapter
M4       explicit T0–T3 transition models
M5       probabilistic Ours predictor + calibration
M6       ablation and intervention faithfulness
M7       rolling cutoffs and data scaling
M8       second-person transfer
M9       optional language/voice/VRM full runtime
```

Each formal experiment requires a separate preregistration and frozen result. Failed gates remain visible and do not silently authorize the next phase.

## 12. Expected breaking changes

- Primary APIs will change from free-form reply generation to event/state/probability records.
- Existing persona prompt and visible reply logic will become a downstream adapter.
- Some top-level scripts will remain historical but stop receiving new features.
- New datasets will require explicit prediction time and source-time fields that old synthetic datasets do not contain.
- Formal results will no longer be summarized by one maturity score.
- A future clean worktree/branch is preferable after audit because the current worktree contains a large uncommitted V2.11–V2.22 stack.

Backward compatibility should be maintained through adapters and regression tests; working code must not be deleted before a formal migration decision.

## 13. Dependency graph

```text
Master specification
        |
        +--> research definitions / annotation / leakage policy
        |
        +--> source manifest + rights boundary
                 |
                 +--> frozen event taxonomy + human coding reliability
                           |
                           +--> temporal dataset builder + leakage tests
                                      |
                                      +--> B0-B3 baseline benchmark (M1)
                                      |          |
                                      |          +--> Temporal Prediction Observatory
                                      |
                                      +--> B4-B5 strong baselines
                                      |
                                      +--> structured HumanState + transitions
                                                   |
                                                   +--> Ours probability predictor
                                                              |
                                                              +--> calibration
                                                              +--> ablation/intervention
                                                              +--> rolling/scaling/transfer
                                                              +--> language/VRM demo adapter
```

## 14. Suggested first implementation milestone

**M1 Temporal Prediction Observatory** must produce:

- common temporal record and probability schemas;
- strict cutoff and leakage validator;
- experiment registry/config snapshot contract;
- B0 prior, B1 base LLM, B2 persona prompt, B3 RAG interfaces;
- Top-k/F1/Brier/NLL/ECE metrics;
- deterministic synthetic/development fixtures for tests only;
- a single reproducible runner;
- a graphical cutoff/prediction/outcome comparison;
- an explicit `DATA GATE BLOCKED` state for formal Uruha results until human coding is authorized.

M1 must not unseal the Uruha holdout, start forbidden model execution on protected persona data, or claim predictive improvement from fixtures.

## 15. Completion rubric and one-week impact

Two percentages must remain separate:

### Engineering roadmap

Current audited estimate: **about 25%** of the master architecture is reusable or partially implemented. Memory, trace, persona governance, realization, and experiment locking are strong; temporal dataset construction, common baselines, calibrated behavior prediction, rolling evaluation, and transfer are missing.

If M1 infrastructure and graphical observatory pass all gates, engineering roadmap completion becomes **about 40–45%**. The gain is large because a valid benchmark determines whether every later component has research value.

### Scientific proof

Current audited estimate: **about 10–15%**. Existing work supports bounded mechanisms and development comparisons, not unseen future Uruha behavior.

M1 with fixtures only leaves scientific proof near **15%**. M1 with independently coded, temporally valid Uruha pilot ground truth can raise it to roughly **20–25%**, but still cannot prove H1–H7 because Ours, rolling cutoffs, full interventions, scaling, and transfer remain unfinished.

These percentages are roadmap accounting, not statistical confidence and not a claim that a human has been reconstructed.
