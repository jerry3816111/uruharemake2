# Development-first roadmap

Status date: 2026-09-02
Historical research source: `/Users/jerrychang/Downloads/RESEARCH_SPEC_FOR_CODEX.md`  
Execution mode: build the working system first; research is retained only as validation and claim control.

## 2026-09-01 human-response-equation validation override

The active objective is no longer another local reply patch. M1–M53 remain immutable engineering and
research evidence, including their failures, while M54 starts a bounded attempt to validate an
interpretable person-specific human-response equation. The equation predicts an observable behavior
distribution from only pre-cutoff evidence; inferred emotion, need, relationship, and persona states
remain model variables rather than private mental facts.

The dependency order is fixed:

1. **M54** — freeze Equation V1, measurement, provenance, intervention, update, and claim contracts;
2. **M55** — build a timestamped real-person longitudinal pilot with independent coding reliability;
3. **M56** — run strict unseen-future B0–B5/Ours comparison under matched model and resource controls;
4. **M57** — localize perception, retrieval, state, decision, and realization error with oracle substitution;
5. **M58** — change one falsified variable and use a new sealed holdout;
6. **M59** — run memory/state/relationship/person-parameter ablation and counterfactual intervention;
7. **M60** — prospectively test target-user desired-response match and correction retention;
8. **M61** — transfer the unchanged core equation to a second real person;
9. **M62** — replicate the decisive result on a second base model and close the graphical evidence audit.

M54 passed its contract gate on 2026-09-01; see
`analysis/m54_human_response_equation_v1_acceptance_2026-09-01.md`. M55 pre-content readiness also
passes, but its real-person pilot is blocked at the frozen two-human V7 reliability gate: both ledgers
are 0/18, so Uruha target events and coders remain zero and M56 is not authorized. See
`analysis/m55_real_person_longitudinal_readiness_2026-09-01.md`.

The M55 temporal-row engineering contract also passes; see
`analysis/m55_temporal_row_contract_acceptance_2026-09-01.md`. It discovered that V9 whole-event
start/end cannot establish a prospective cutoff without possible target-behavior leakage, so four
separate input/cutoff/behavior boundaries are now required. The compiler and graphical audit pass on
synthetic engineering rows, but real temporal rows remain 0/30. This does not change M55 or M56
authorization.

The private two-coder boundary-extension instrument now also passes its engineering gate; see
`analysis/m55_boundary_extension_tool_acceptance_2026-09-01.md`. Each coder's separate ledger is bound
to that coder's V9 entry, real use remains V7-gated, stale sources and synthetic/real confusion fail
closed, and cross-coder comparison reveals only hashes and temporal differences. Software never
averages the two answers or creates an adjudicated row. The graphical demo is synthetic; human V7
progress remains 0/18 and 0/18, Uruha temporal rows remain 0/30, and M56 remains forbidden.

The downstream explicit-adjudication and record-assembly instrument also passes its engineering gate;
see `analysis/m55_boundary_adjudication_tool_acceptance_2026-09-01.md`. It requires a human submit for
every pair even when the two answers match, permits only accept-A, accept-B, or a manual resolution,
retains four source-entry hashes, and rejects automatic averaging, label choice, or text merge. A
complete synthetic ledger exports a 22-field temporal pack with zero claimed humans and cannot
authorize M55 or M56. Real use remains V7-gated; real adjudicated rows remain 0/30.

The M56 blinded same-model fair-comparison preflight is now also frozen before any real outcome or model
generation; see `analysis/m56_fair_comparison_preflight_acceptance_2026-09-01.md`. It fixes all seven
B0–B5/Ours conditions, the B5 versus Ours primary contrast, answer-key isolation, SHA commitment order,
same-model/hardware/decoding controls, declared token budgets, and joint Brier/NLL success gates. Contract
engineering and Safari visualization pass, but this is not an M56 run: model calls and target-outcome
access are both zero, M55 remains incomplete, and M56 execution remains forbidden.

The M56 capability-separated execution capsule and separate scorer now pass their engineering gate; see
`analysis/m56_blinded_execution_capsule_acceptance_2026-09-01.md`. Each condition is reduced to its exact
authorized view, B5/Ours source objects must hash identically, B4 summary and Ours semantic costs are
counted, all rows are committed before a separately validated outcome join, and token imbalance can block
a formal pass. Synthetic adversarial and Safari evidence pass, but formal model calls and target-outcome
access remain zero. This completed the capability-separated execution/scoring shell, but its fixture still
used arbitrary 64-character Ours provenance placeholders.

The M56.1 pre-outcome Equation artifact overlay now closes that engineering gap; see
`analysis/m56_pre_outcome_equation_artifacts_acceptance_2026-09-02.md`. From the exact B5/Ours source
object it deterministically materializes content-addressed observable-history fit, nine-variable state,
and cross-cutoff transition artifacts; unavailable `S/R/N` remain null, only Ours receives the payload,
and a wrapper receipt/scorer binds and revalidates the full content before answer joining. The frozen
M54–M56 files were not modified. Synthetic adversarial tests and Safari visualization pass with zero
artifact model calls, zero target-outcome access, and zero private-state fabrication. This still does not
complete the M55 human gate, authorize a real M56 run, or create an M56 result; the current overlay remains
synthetic-only until a separately frozen real-data execution authorization can reuse the same semantics.

The M56.2 formal real-data activation envelope now supplies that separately frozen authorization boundary;
see `analysis/m56_2_real_data_activation_envelope_acceptance_2026-09-02.md`. It obtains readiness only from
the standard live V7/V9/M55 evidence chain, binds frozen dependencies plus the local model and hardware,
separates generation, commitments, scoring, and telemetry under a Git-ignored private run root, and permits
at most one no-retry generation lease through a short-lived single-use receipt. A structurally valid or
synthetic packet cannot create authority. The controller is intentionally denied now: V7 remains 0/18 and
0/18, V9 and real temporal rows remain 0/30, and formal calls/results remain zero/absent. This is activation-
control engineering evidence, not real-person predictive validity, Equation V1 validity, an M56 comparison,
full-pipeline readiness, production readiness, or a solved human-response equation.

The M56.3 lease-gated formal generation runner now supplies the next frozen execution boundary; see
`analysis/m56_3_lease_gated_generation_runner_acceptance_2026-09-02.md`. It accepts only a run identifier,
revalidates the M56.2 consumed lease, freezes B4-summary plus 30-by-7 prediction order, gives every permitted
model task one transport attempt with no retry or fallback, and records actual token, latency, CPU, memory,
provider-duration, model-identity, and content-hash fields. Generation has no scoring capability. Only a
complete 210-row submission may create a SHA commitment and then a capability for the separate scorer. The
current live state is intentionally denied: V7 is still 0/18 and 0/18, V9 and real rows are 0/30, and lease,
formal calls, commitment, scoring release, and result are all absent. Mock mechanics and a no-call rehearsal
are engineering evidence only. A process interruption after model calls but before commitment currently
terminally fails the run and requires a newly human-authorized run rather than automatic recovery; this avoids
hidden retry but can waste compute. M56.3 therefore adds no predictive-validity or resource-performance result.

The M56.4 separate formal scorer now closes the post-commit execution path; see
`analysis/m56_4_separate_formal_scorer_acceptance_2026-09-02.md`. Its only public parameter is a run id. It
revalidates the M56.2 authority chain, the complete M56.3 submission/commitment/release and every actual call
resource before it opens the private outcome compartment. A B5/Ours prompt-token difference above the frozen
5% threshold blocks before outcome access and cannot be bypassed with a caller flag. After that gate, the
scorer uses the frozen seven conditions, B5-versus-Ours primary comparison, proper scores, paired tests and
success rule, performs zero model calls, and immutably commits either a positive or retained negative scoped
decision. Current scoring is deliberately denied: V7 is 0/18 and 0/18, V9 and real rows are 0/30, and no
prediction release, outcome access, score report or result commitment exists. Test-only real-shaped mechanics
remain zero-human engineering evidence. A token-imbalanced future run would need a separately frozen
prospective exact-token sensitivity execution before any outcome access. M56.4 adds no predictive-validity or
resource-performance result.

The M56.5 crash-safe no-retry continuation overlay now closes the ordinary process-interruption gap left by M56.3;
see `analysis/m56_5_crash_safe_no_retry_continuation_acceptance_2026-09-02.md`. It commits the recovery mode before
the schedule, writes one immutable invocation intent before each single transport attempt, and atomically checkpoints
the validated step result together with actual call telemetry. A complete checkpoint is reused without another call;
an intent without a complete checkpoint is ambiguous and terminal. Fault injection shows an interrupted and an
uninterrupted forged 30-row run both use exactly 180 calls and yield identical summaries, predictions and ledger;
M56.3 and M56.4 compatibility remain valid. Current live authority is unchanged: V7 is 0/18 and 0/18, V9 and real
rows are 0/30, and formal calls, outcome access, commitment, release and result are zero or absent. M56.5 is recovery
engineering only, not human evidence, actual resource/performance evidence, Equation V1 validity, full-pipeline
readiness, production readiness or a solved human-response equation.

M62 is the optimistic completion line. Honest data/codebook/equation/transfer/replication retries may use
M63–M75, but every retry requires a new sealed source and retained prior failure. M75 is a hard stop: the
research must conclude either with bounded positive evidence or rejection of the current equation. A
negative result is completion; endlessly adding milestones is not. Product maintenance continues only
where needed for valid measurement, safety, natural Japanese, latency, Web traceability, or later
voice/VRM/Function Calling integration.

## 2026-08-24 development-first override

The user no longer needs this project packaged as a paper. M1–M15 remain immutable evidence and engineering history, but they are not the active product backlog. Formal-person data gates continue to block scientific claims about Uruha or human equivalence; they do **not** block safe engineering of a clearly labelled operational user model.

The active development sequence is:

1. integrate desired-response inference into the real dialogue runtime;
2. learn from explicit cross-turn support, contradiction, and uncertainty;
3. persist only structured, reversible model parameters, separate from factual memory;
4. make the updated variables and their causal use visible in the runtime node graph;
5. validate with isolated multi-turn regressions and retained failure cases;
6. then improve real conversation quality, latency, safety, voice, and embodiment in that order.

**M16–M29 are complete as bounded product milestones.** A real dialogue turn now creates an inspectable desired-response prediction, linked feedback can update or withdraw it, and structured experience can be reused at exact/domain/relationship levels only after auditable negative-transfer gates. M19 removed Web background cognition from the human-message queue. M20 made explicit correction authoritative over a stale clarifier. M21 added bounded planning, M22 added one typed task-shape decision, M23 binds response alternatives to final Japanese, M24 keeps the graph stable in Safari, M25 lets explicit response-form requests override stale preference, M26 requires implicit execution gates, M27 accounts for only causally linked outcomes under a minimum evidence guard, M28 separates previous-turn feedback from bounded current-topic surface action, and M29 generalizes that current-topic action through fail-closed source/Japanese anchor projection. The latest acceptance evidence is `analysis/m29_generalized_literal_topic_projection_acceptance_2026-08-25.md`.

M23 completed these bounded requirements:

1. within an M22 emotional bid, infer whether the desired response mode is listening, practical help, playful teasing, companionship, or low-pressure clarification;
2. separate explicit current-turn evidence from reversible learned interaction preference;
3. retain alternatives, evidence, uncertainty, and blocked negative-transfer reasons internally without dumping them into the visible reply;
4. make the chosen mode a real surface contract so graph selection and final Japanese output cannot diverge;
5. accept explicit correction on the next turn, withdraw the stale mode, and avoid writing the inference as factual long-term memory;
6. validate source-disjoint multilingual multi-turn cases and retain safety, factual grounding, identity, and Japanese guards.

M23 addresses the user's central interaction example: the same arousal statement may be asking for a method, waiting for a tease, wanting company, or only wanting to be heard. It is a desired-response mechanism milestone, not a claim of mind reading or universal pragmatic understanding. Its first four-turn Safari run exposed stale teasing that revived from the original causal scope; the final implementation repairs every structured causal scope linked to the contradicted response before reuse.

M24 completed these bounded browser requirements:

1. keep the M23 summary card, causal node path, and click-through evidence;
2. stop rendering every large nested trace body eagerly into the page;
3. define and expose retained-turn, node-count, HTML-size, and detail-payload budgets;
4. disclose bounded node detail only when the user opens an inspector, while retaining the complete source in local JSONL;
5. rerun a multi-turn Safari dialogue without losing chat to the high-memory reload banner;
6. retain deterministic rendering tests and an honest traceability audit so performance is not achieved by deleting evidence.

M25 closes the retained M24 cross-language defect for the implemented explicit cues. M26 closes the narrower operational defect in which the highest implicit utility could be treated as sufficient authority: it now normalizes alternatives, uses scoped outcome reliability, and abstains when evidence is insufficient. It does not establish population calibration, paraphrase-complete semantics, or private-state inference.

M30–M32 are complete negative diagnostic/remediation milestones and retain their frozen failures. M33 is complete as a bounded positive milestone: its exact-source atom ledger passed its first sealed reserve at 12/12 faithful authorities and 3/3 safe incomplete abstentions. M34 is also complete as a bounded positive milestone: 4/4 byte-identical-current counterfactual pairs diverged under verified reversible context, and all support／contradiction／unknown outcomes were traced correctly. M35 is complete as a frozen failed comparison: current desired-response accuracy was 25% for the current-turn-only baseline and 75% for the longitudinal system at exact scored prompt-token parity, but seven gates failed and the feedback-policy metric was invalidated by a frozen annotation audit defect. M36 is complete as a second frozen failed comparison: annotation integrity passed, while the same-model current-policy observation was 16.67% versus 83.33% at exact token parity; seven mechanism/revision/surface gates still failed. M37–M53 continued the source-bounded runtime, correction, surface, and actionable-help line; their bounded passes and retained failures remain historical evidence in the handoff. The active equation-validation dependency is now **M55 Timestamped Real-Person Longitudinal Pilot** after M54 passed its contract gate.

## Active product milestones

| Milestone | Product result | Status |
|---|---|---|
| M16 | real runtime prediction → feedback → correction → persistence → reuse, visible in node graph | complete bounded milestone |
| M17 | context-scoped adaptive experience plus usable latency budget | complete bounded milestone |
| M18 | hierarchical context transfer plus composable policy coverage without losing safety or traceability | complete bounded milestone |
| M19 | human input priority over background cognition, with honest end-to-end queue timing | complete bounded milestone |
| M20 | explicit-correction authority plus lightweight streaming and one final graph commit | complete bounded milestone |
| M21 | bounded slow-path planning with stage timing and guarded fallback | complete bounded milestone |
| M22 | typed semantic routing with overlap and misclassification audit | complete bounded milestone |
| M23 | emotional-bid desired response mode inference, surface execution, causal-scope correction, and reuse | complete bounded milestone |
| M24 | Safari-scale progressive runtime graph and trace payload budget | complete bounded milestone |
| M25 | cross-lingual explicit desired-response authority, negation, final Japanese execution, and fast path | complete bounded milestone |
| M26 | operational implicit desired-response distribution, abstention gate, and outcome update | complete bounded milestone |
| M27 | causal outcome calibration ledger, effective-sample guard, and selective reliability display | complete bounded milestone |
| M28 | feedback acknowledgement and clean topic-shift surface continuity without stale uncertainty | complete bounded milestone |
| M29 | generalized literal-topic anchor projection and grounded Japanese surface without phrase-inventory growth | complete bounded milestone |
| M30 | frozen cross-lingual semantic-fidelity holdout, false-authority audit, and error taxonomy | complete negative diagnostic milestone; reliability gate failed |
| M31 | semantic authorization, unsupported-addition guard, and sealed reserve confirmation | complete negative diagnostic milestone; coverage gate failed |
| M32 | deterministic semantic commit, fresh routing, and sealed reserve confirmation | complete negative diagnostic milestone; source-semantic gate failed |
| M33 | source-anchored semantic atom ledger, bounded conflict repair, direct-Japanese identity path, and sealed reserve confirmation | complete bounded positive milestone |
| M34 | counterfactual pragmatic branch ledger with context intervention and next-turn verification | complete bounded positive milestone |
| M35 | same-model current-turn baseline vs longitudinal pragmatic system with cost and correction audit | complete frozen failed milestone; +50pp current proxy observation, seven gates failed |
| M36 | annotation-integrity validator plus compositional multilingual arousal/response-form/correction linkage | complete frozen failed milestone; +66.66pp current proxy observation, seven gates failed |
| M37 | typed observable-trigger → response-policy relation with morphology/paraphrase normalization | complete bounded milestone |
| M38–M53 | guarded correction, surface integrity, evidence delivery, and source-bounded actionable-help sequence | completed bounded/failed sequence; see handoff for each claim boundary |
| M54 | machine-checkable candidate human-response equation, read-only runtime coverage, and intervention contract | complete contract milestone; no real-person validity claim |
| M55 | timestamped real-person longitudinal pilot, codebook, provenance, reliability, and missingness | pre-content, temporal, boundary, and adjudication tools ready; real rows 0/30; blocked on two-human reliability and target coding |
| M56 | blinded B0–B5/Ours same-model comparison with outcome isolation and matched resource controls | protocol, capability-separated execution/scorer, and real content-addressed pre-outcome Equation artifact overlay frozen; real execution blocked; 0 formal model calls and no formal result |

Research work is now limited to the smallest evidence needed to answer: did the implemented mechanism change actual system behavior as intended, did it avoid corrupting factual memory, and what remains unproven? New paper-style preregistration, venue positioning, and broad statistical packages are out of scope unless the user explicitly restores them.

## Fixed boundary

`M1 Temporal Prediction Observatory` is the permanent end marker of the one-week showcase. Its frozen V1 failure, V1.1 engineering result, report, raw artifacts, and Safari screenshots must not be rewritten or absorbed into later claims.

## Historical research completion definition (validation reference only)

The project is complete only when all required evidence tracks are satisfied or explicitly reported as failed scientific hypotheses:

1. temporally valid longitudinal data and annotation reliability;
2. B0–B5 strong baselines under documented information and resource budgets;
3. structured memory with provenance, validity, decay, importance, relevance, salience, and uncertainty;
4. person-independent timestamped `HumanState` snapshots;
5. T0–T3 transition families;
6. behavior logits, calibrated probabilities, and a hybrid `Ours` predictor before language realization;
7. strict unseen-future and rolling-cutoff evaluation;
8. component ablation and probability-level intervention evidence;
9. history-volume scaling and diminishing-return analysis;
10. second-person transfer without target-specific core-logic rewrites;
11. downstream natural-language/persona/human evaluation and full-runtime cost/safety checks;
12. a final claim table that retains negative results and never equates the system with a private mind, consciousness, or the real person.

A well-executed negative result may complete a hypothesis test. It does not authorize silently removing a component or changing a gate after results are seen.

## Dependency-ordered execution

| Stage | Required output | Current status | Next gate |
|---|---|---|---|
| M0 | research definition, hypotheses, variables, ethics, leakage | complete | retained |
| M1 | temporal schema, B0–B3, metrics, frozen runner, observatory | complete engineering checkpoint | archived one-week marker |
| M2 | B4 summary + LLM and B5 structured-prompt LLM | complete engineering baseline floor | retained frozen first generation |
| M3 | structured memory model | complete engineering mechanism | retained frozen ablation result |
| M4 | timestamped person-independent `HumanState` | complete engineering snapshot contract | retained frozen replay result |
| M5 | T0–T3 state transition | complete synthetic engineering mechanism | retained frozen first generation; T3 perception bottleneck preserved |
| M6 | calibrated hybrid `Ours` behavior predictor | complete bounded synthetic hypothesis | retained first-generation lift and high-confidence failure |
| M7 | ablation and intervention | complete synthetic diagnostic instrument | frozen negative findings plus 10/10 component-identifiability coverage |
| M8 | rolling cutoffs and data scaling | complete predominantly-negative synthetic robustness test | frozen B5 win, nonmonotonic history curve, rolling collapse, and sign reversals |
| M9 | second-person transfer | complete engineering transfer, negative predictive transfer result | frozen 1/7-hypothesis result; unchanged-core hashes retained |
| M10 | language, Uruha surface, human ratings, voice/VRM runtime | M10.3 frozen human-rating instrument complete; automated surface passes but authority/human result remains pending | three independent complete blind raters; embodiment remains downstream |
| M11 | final claim table and graphical evidence closure | complete hash-bound synthesis; no new scientific result | retain as teacher-facing first page and update only through a new version when bound evidence changes |
| M12 | literature-grounded paired statistical evaluation of frozen evidence | complete retrospective audit; Ours 1/3 directions, B5 2/3, formal real-person tracks 0 | retain frozen negative/mixed result; future confirmation requires a new protocol and unseen formal data |

## Parallel human-data gate

Formal Uruha model execution remains blocked until:

1. two distinct consenting humans independently code the frozen 18-slot V7 pilot;
2. preregistered inter-rater reliability passes;
3. V9 target calibration coding is separately authorized and completed;
4. temporal target records separately contain observable-input start, prediction cutoff, and observable-future behavior start/end; whole-event boundaries may not substitute;
5. the final holdout remains sealed until its preregistered use.

Codex may continue M2–M7 interfaces and synthetic/mechanism tests while this gate is pending, but none of those runs may be presented as Uruha predictive evidence.

## Resource order

Follow the master specification priority:

1. dataset quality;
2. temporal correctness;
3. annotation quality;
4. provenance;
5. reproducibility;
6. baseline strength;
7. compute scale.

Foundation-model training is not required. The main risk is invalid ground truth or temporal leakage, not insufficient GPU size.

## Current maturity axes after M10.2

| Axis | Current evidence | Bounded maturity |
|---|---|---:|
| Research definition / governance | M0 complete | 100% |
| Temporal instrument / B0–B5 | M1–M2 complete on synthetic fixture | 100% engineering, 0% formal Uruha result |
| Structured memory | M3 schema, cutoff, activation, ablation complete on synthetic fixture | 100% mechanism, 0% real-person parameter validity |
| HumanState representation | M4 snapshot and replay complete on synthetic fixture | 100% schema, synthetic learned dynamics now exercised by M5 |
| Transition | T0–T3 common interface and frozen synthetic comparison complete | 100% engineering mechanism, 0% real-person dynamic validity |
| Hybrid behavior predictor | M6 logits/probability/calibration/selection and B0–B5 comparison complete | 100% engineering mechanism, bounded nonfresh synthetic lift only |
| Causal intervention | M7 first diagnostic plus M7.1 10/10 coverage complete on synthetic fixture | 100% engineering, 0% real-person causal validity |
| Rolling/scaling | M8 complete on fresh synthetic semantic timeline | 100% engineering, negative stability/scaling evidence |
| Second-person transfer | M9/M9.1 same-core Synthetic Mira transfer complete | 100% engineering; predictive transfer hypothesis failed |
| Language / voice / avatar runtime | M10.1 behavior authority, M10.2 register remediation, M10.3 frozen blind-rating instrument, and historical chat/TTS/VRM subsystems | automated surface 18/18; one proxy authority regression; rating instrument ready but 0 human raters; embodiment downstream only |
| Evidence closure / claim governance | M11 binds 13 sources into a 12-stage research map and final claim matrix | 100% engineering synthesis; creates no additional scientific evidence |

If one coarse full-project number is unavoidable, the dependency-weighted project remains approximately **70–75% complete**. The behavior-research engineering architecture is approximately **95–100%**, while central scientific evidence remains approximately **15–20%**: M9 establishes same-core second-person engineering transfer but fails predictive transfer; M10.1 localizes downstream authority/register failures; M10.2 fixes all automatic polite-register failures on a source-disjoint remediation fixture but introduces one proxy authority regression and still has no human ratings. Real longitudinal ground truth, real-person transition validity, and human evaluation remain absent. Formal Uruha evidence remains zero while the human-data gate is blocked.

## M5 frozen result

M5 compared T0 static, T1 hand-weighted, T2 ridge-linear, and T3 constrained-Qwen-feature-plus-learned transition on 40 author-designed events (24 train, 8 dev, 8 holdout). The first-generation result is immutable:

- T0 RMSE 0.1264;
- T1 RMSE 0.0420;
- T2 RMSE 0.0042 with 100% direction accuracy;
- T3 RMSE 0.0576 with 70.8% direction accuracy;
- T3 holdout event-feature MAE 0.2294.

T3 is intentionally retained as weaker than T1/T2. This shows that the current language-to-feature perception layer, especially repetition/support/technical-failure estimates, is the active bottleneck. The result only validates a synthetic state-transition instrument; it is not human private-state ground truth or a behavior-prediction gain.

The next active dependency is M6: predict a calibrated probability distribution over observable behavior labels from transitioned state, event, and memory evidence before any language realization. M6 must use a frozen temporal fixture, preserve B0–B5 comparison and resource accounting, and retain a negative result if `Ours` does not improve the preregistered metrics.

## M6 frozen result

M6 overlays six observable behavior labels on the frozen M5 scenarios, materializes 32 pre-cutoff history rows and 8 future holdouts, and compares B0–B5 against `Ours` before any language realization. The first-generation result is immutable:

- Ours Top-1 87.5%, Top-3 100%, Brier 0.1509, NLL 0.1939, ECE 0.1042;
- best B0–B5 Top-1 87.5%, Brier 0.3469, NLL 0.6949;
- the preregistered narrow synthetic lift gate passes because Top-1 ties while Brier and NLL are strictly lower;
- `quiet_success::holdout` remains a high-confidence Ours failure: `direct_rejection` 0.775 vs correct `acknowledge_then_continue` 0.225;
- B2, B3, B4, and B5 classify that row correctly.

The temperature selected on eight dev rows is 0.5, which sharpens probabilities and may overfit. This is retained as a calibration-mechanism result, not general calibration evidence.

M6 used 41 fresh B0–B5 calls (45,512 tokens, 426.77 seconds). Ours inclusive accounting retains the 40 inherited M5 Qwen feature calls (8,614 tokens, 178.76 seconds) plus 4.55 seconds numeric work. The information paths are different and not perfectly token-parity.

## M7 frozen diagnostic and component-coverage remediation

M7 exactly replays the frozen M6 Ours probabilities, evaluates eight identifiable components, preserves preference and habit as `not_identifiable`, executes 80 named interventions, and verifies that all 40 direct explanation-feature interventions alter the actual selected-label probability. The frozen first diagnostic retains both positive and negative findings: memory, personality, explicit state, and semantic interpretation help on the fixture, while relationship and temporal dynamics improve when removed.

The required `quiet_success` failure remains part of the result. Its correct-label probability changes from 0.225 to 0.99995 under the preregistered `event.support=1.0` intervention and the selection flips, demonstrating an inspectable computation path without authorizing a post-hoc M6 score correction.

M7.1 is a separate post-exposure engineering remediation. It adds five explicit preference-alignment features and six train-only behavior-centroid habit-similarity features, expanding the diagnostic vector from 17 to 28 dimensions. All 10 master components are now independently ablatable and all 10 alter at least one probability metric. This closes component identifiability, not predictive evidence. Temporal, relationship, and preference still improve NLL when removed, so those negative findings remain active hypotheses.

## M8 frozen rolling and scaling result

M8 uses 24 new multilingual fictional events, four strict rolling cutoffs, 16 previously unused test texts, eight history-volume conditions, five bootstrap seeds, and the same B0–B5/Ours contract. The first run stopped at H08 after seven calls because the model emitted an out-of-range support value. M8.1's separately locked amendment clips finite numeric boundary overflow only; all research conditions remain unchanged.

The complete 108-call result supports only one of eight hypotheses. B5 beats Ours on Top-1 (81.25% vs 62.5%), Brier (0.428 vs 0.741), and NLL (0.879 vs 2.916). Rolling Ours Top-1 varies from 100% at E3 to 25% at E4. Full history D7 is worse than profile-only D0 in NLL, and D2 is the best NLL condition, so additional history is nonmonotonic. M7's negative temporal, relationship, and preference removal effects all reverse sign on M8, demonstrating dataset/context dependence.

This negative result completes the M8 hypothesis test; it does not authorize tuning on the 16 exposed rows. The next active dependency is M9 second-person transfer. The exact core logic must remain unchanged; only person data, history, person parameters, and fitted artifacts may change.

## M9 frozen second-person transfer result

M9 changes the fictional target from livestream collaborator Synthetic Ren to research coordinator Synthetic Mira while retaining the same memory, state, transition, predictor, rolling, schema, and label-taxonomy core. The first run stopped after 46 calls because B4 returned the equivalent key `behavior_prediction_summary`; that raw failure is immutable. M9.1 is a separately locked one-change parser amendment that accepts this documented summary alias while retaining the raw output.

The complete 108-call M9.1 result passes every engineering-transfer gate and contains zero person-specific branches in the eight SHA-bound core files, but supports only one of seven predictive-transfer hypotheses. Ren zero-shot, Mira parameter swap, and Mira full adaptation achieve Top-1 50.00%, 56.25%, and 43.75% respectively. Full adaptation is worse than both parameter-only transfer and the B4/B5 floor of 75.00%; its Brier is 1.0498 and NLL is 2.9452. Rolling full-adaptation Top-1 varies from 0% at E1 to 100% at E3, so the aggregate cannot be treated as stable transfer.

This result completes M9 as an engineering-generalization test and a negative predictive-transfer hypothesis. It demonstrates that the core can accept a second person's data without target-specific rewrites; it does not show that the current adaptation learns a better person model. The next active dependency is M10 language realization and human-facing evaluation. Per the master specification, the frozen behavior distribution must be supplied before language generation, and voice/VRM embodiment remains gated behind predictive stability rather than being used to hide it.

## M10/M10.1 frozen behavior-authoritative language result

M10 evaluates all 16 exposed Synthetic Mira behavior cases under three same-model language conditions: direct generation, the frozen M9.1 predicted behavior distribution, and a future-leaking actual-label oracle used only as a diagnostic ceiling. Every case shares event/state, development-only Uruha surface evidence, generation settings, output budget, and hardware. One equal preflight call per condition produces exact scored prompt-token parity in all 16 cases.

The first run stopped after five calls when the classifier emitted the equivalent key `classification`. M10.1 separately locks a one-key alias parser; the complete 144-call run records six normalizations and preserves the original failure. Predicted-language authority alignment is 87.5%, but observed-outcome alignment is 56.25%, below direct generation at 62.5%. Oracle authority and outcome alignment are both 100%, showing a usable behavior-realization ceiling when the upstream decision is correct.

The decomposition is explicit: seven cases are prediction-correct and faithful, seven are prediction-wrong and faithfully realized, and two wrong predictions are bypassed by the language model and accidentally repaired. The language stage therefore does not hide M9 errors. The automatic surface gate also fails: direct/predicted/oracle pass rates are 75.0%/43.75%/25.0%, driven mainly by polite-register drift. Six of nine hypotheses pass, so the overall M10.1 scientific gate remains failed.

The same-model classifier is a proxy only. A blinded 16-item three-way human packet exists, but zero independent M10 ratings have been collected; no human preference, felt-understanding, or Uruha fidelity claim is available. M10 remains active. The next necessary engineering experiment is a source-disjoint behavior-preserving casual-register realizer that must improve surface compliance without reducing authority alignment, followed by independent blind ratings. Voice/VRM remains optional downstream demonstration work.

## M10.2 frozen register-remediation result

M10.2 adds 18 multilingual, source-disjoint synthetic events after the M10.1 polite-register failure was known. It is therefore a transparent remediation fixture, not an untouched global holdout. Each case generates one shared S0 utterance, then applies a constrained S1 rewrite that may change casual Japanese surface form but must preserve the authorized observable behavior.

The 72-call result improves automatic surface compliance from 13/18 (72.22%) to 18/18 (100%), fixes all five polite-register failures, changes 12 utterances, and creates zero surface pass-to-fail regressions. However, authority alignment changes from 18/18 (100%) to 17/18 (94.44%). The single `R-JA-06` proxy regression remains frozen: a sentence that still appears to contain an explicit pause/recheck is classified as `defer_commitment` after repair instead of `pause_and_reassess`. This unresolved disagreement must be judged by independent blinded humans, not erased by post-result classifier changes.

Five of seven hypotheses pass, so the overall gate remains failed. The paired blind packet and hidden key are frozen, but there are currently zero independent raters. Consequently M10.2 supports an automated register-compliance improvement claim only; it does not establish human naturalness preference, felt understanding, semantic preservation, or Uruha fidelity. The next dependency is a reproducible human-rating instrument and independent ratings before any embodiment work is promoted into the research claim.

## M10.3 frozen blind-rating instrument

M10.3 completes the reproducible human collection and analysis instrument without fabricating any ratings. The browser surface loads the blind packet only and never loads the hidden A/B key. It stores one-way rater pseudonyms plus required independence/key-unseen attestations in an isolated research directory, rejects incomplete submissions, and never writes production memory or persona facts.

The preregistered gates require at least three complete distinct raters, average pairwise quadratic-weighted kappa of at least 0.40, a natural-casual-Japanese S1−S0 delta of at least +0.50 with a positive item-cluster bootstrap lower bound, noninferiority tolerances for semantics/behavior/non-overclaiming, and greater than 0.60 S1 preference among changed decisive pairs. `R-JA-06` remains a mandatory separate report. The zero-rating analyzer result has `claim_authorized=false`; the instrument is complete but the human evidence gate is still blocked.

## M11 final evidence closure

M11 creates no new scientific observation. It SHA-binds the master specification and 13 frozen result/gate artifacts into a teacher-facing first page that shows the full computational chain, 12 switchable milestones, four separate maturity axes, the final supported/unsupported/blocked claim table, and both human gates. It explicitly displays the M8, M9, M10.1, and M10.2 negative or mixed outcomes and the zero-human counts.

This completes the final claim-table and graphical evidence-synthesis engineering requirement. It does not change the overall 70–75% dependency-weighted estimate, the 15–20% central scientific evidence estimate, or formal Uruha evidence at zero. Remaining progress now requires actual independent human coding/rating and subsequent real temporal reruns; Codex must not simulate those inputs.

## M12 literature-grounded frozen-evidence audit

M12 does not create new predictions. It SHA-binds and re-evaluates the frozen
M6, M8.1, and M9.1 per-event probability distributions against the
master-spec `B5_STRUCTURED_HISTORY` baseline. It uses multiclass Brier and NLL
as primary proper scores, 20,000 paired bootstrap intervals, exact paired
sign-flip tests, exact McNemar correctness tests, and retains ECE only as a
small-sample descriptive diagnostic.

The result does not support replicated hybrid superiority. M6 directionally
favors Ours but both proper-score intervals cross zero; M8 directionally favors
B5; M9 statistically favors B5 on both Brier and NLL. Across the three tracks,
Ours is favorable on one and B5 on two, with zero formal real-person tracks.
The frozen verdict is therefore `central_same_model_superiority_supported=false`.

M12 also keeps mechanism, memory, and human-facing evidence separate. M7's
40/40 direct feature interventions show computational responsiveness, while
the three component-removal directions replicate 0/3 on M8. V2.22 supports
bounded persistence over an eight-turn baseline but not a strict-task advantage
over full transcript, and costs 1.81x tokens / 23.24x latency. Automatic
language metrics remain proxies and do not become human felt-understanding
evidence. The audit improves evaluation credibility without increasing the
real-person sample size or the central-science maturity estimate.

## Active product continuation after M33

M16–M29 established bounded runtime adaptation, desired-response selection,
causal outcome accounting, correction-aware surface commit, Japanese-visible
guards, and a progressive Safari node graph. M30 then supplied the first frozen
cross-lingual literal-semantic diagnostic and failed at 4/15 faithful authority
with five false authorities. M31 replaced untrusted pre-authorization
generation with source-first normalization and a bidirectional anchor contract.

M31 improved the exposed M30 development replay to 10/15 faithful and one false
authority, but its first sealed reserve still failed: 4/9 faithful, zero false
authority, five false rejects, and zero Chinese faithful cases. M32 then fixed
fresh-session candidate routing, the `um` substring collision, and incomplete
M31 surface commitment. Its live Safari graph now exposes the M31 completeness
failure and M32 deterministic canonical commit.

M32's first sealed reserve also failed: 7/12 faithful, four false authorities,
one false reject, and 3/3 safe incomplete abstentions. English and Japanese met
the 75% per-language boundary, Chinese reached only 25%. The failure is now
localized upstream of surface realization: source time, fine object type,
weekday, and change-operator atoms can be lost or altered inside the model's
canonical self-report.

M33 added an exact-source semantic atom ledger independent of model canonical
self-report. Its first sealed reserve passed all frozen gates: 12/12 faithful
authorities, zero false authority, zero false reject, 3/3 safe incomplete
abstentions, 100% per-language and required atom-trace coverage, five repaired
source conflicts, and no unresolved conflict authority. This remains bounded
to five author-constructed literal construction families; it is not
open-domain semantics or evidence of human pragmatic understanding.

M34 now completes that bounded intervention mechanism. Its first sealed reserve
passed all frozen gates: 8/8 policy and mode selections, 4/4 same-current
counterfactual pair divergences, 8/8 next-turn outcome verifications, 3/3
contradiction replacements, 16/16 visible Japanese replies, and zero unverified
mental-fact or raw adaptive-ledger writes. This is controlled context
sensitivity and correction evidence, not private-intent truth or human
preference evidence.

M35 completed that same-model comparison and remains a frozen failed milestone.
At exact scored prompt-token parity, the current-turn-only baseline selected the
expected current policy on 25% of cases and the longitudinal system on 75%, a
+50 percentage-point controlled observation. However, system mechanism coverage,
pair divergence, surface realization, feedback linkage, and contradiction
revision missed seven frozen gates. A post-result audit also found inconsistent
feedback-policy targets in the frozen dataset, so the 60% feedback-policy score
is invalid evidence and is not corrected after exposure.

M36 added a fail-closed annotation-integrity validator and bounded multilingual
cue composition. Its new frozen reserve passed annotation integrity but failed
seven gates: the exact-token same-model current-policy observation was 16.67%
versus 83.33%, while trigger morphology, one Chinese feedback link, full revision,
and surface-act execution remained incomplete. The failed score is immutable.

The active dependency is M37 Pragmatic Trigger-Relation Normalization. A verified
future response preference must be represented as a typed observable-trigger →
response-policy relation rather than as a lexical echo of the seed utterance or
the seed turn's immediate request act. New source-disjoint pairs must test
morphology and bounded paraphrase while holding current literal state fixed where
applicable. M37 must not absorb the separate M38 feedback-linkage or M39 semantic
surface-act variables. Even a successful M37 remains controlled proxy evidence
unless independent blind human ratings establish felt-understanding preference.

## 2026-08-27 current development override: M43 → M44

M37–M43 bounded runtime work is recorded in handoff §7.50–7.57; do not treat the
historical M37 paragraph above as the next unimplemented milestone. M43 makes
linked decisive support control the current acknowledgement act, avoiding a
new generic clarification while preserving unresolved mental hypotheses. Its
24-case author-written mechanism reserve passed, but actual Web feedback closure
is incomplete: one confirmed M37 action lost its next-turn pending record when
the literal-surface M32 path suppressed it. Mixed practical requests and some
new trigger wording also still fail outside this mechanism.

M44 is the necessary executed-action receipt dependency, specified in
`research/m44_executed_action_feedback_plan_2026-08-27.md`. It must preserve a
prospective, source-linked feedback opportunity for a policy actually expressed
and verified at the final visible boundary; it must never infer a past prediction
from a later yes. No reserve, implementation or acceptance is yet claimed for M44.
The product is not complete; frozen mechanism passes are not universal language
coverage, human preference evidence or completion of a biological brain equation.

## 2026-08-27 latest development override: M44 → M45

M44 is now implemented as an opt-in runtime/Web overlay. It prospectively records
an M37-grounded policy that M39 verified at final emission when a literal layer
had removed its pending prediction. It preserves unrelated pending and earlier
outcomes. A bounded typed store survives normal save/load; M27/M38 still determine
support, contradiction or uncertainty from the following real user turn.

233 selected regression/contract tests pass. The single frozen 24-case typed
reserve passes (24/24 registration decisions vs unchanged-state control 19/24),
but is author-written, not independent holdout or a same-model LLM comparison.
Nine real isolated Safari turns produced three receipts with three different
outcomes: supported, contradicted, uncertain. Their 56 available node payloads
match the runtime and same-cycle history; production DB hashes are unchanged.

M44 does NOT complete conversation quality. Safari turn 6 selected practical
help after correctly acknowledging a misread, but only proposed deciding on a
step, without supplying one. The next necessary dependency is M45 Actionable
Help Delivery, specified in `research/m45_actionable_help_delivery_plan_2026-08-27.md`.
No M45 implementation or acceptance is claimed. Preserve the failure and frozen
M43/M44 results. More trace or a token mentioning a step is not task fulfillment.
