# M57 Outcome-Blind Component Error Localization — Acceptance

Date: 2026-09-04

Decision: **PASS as a bounded engineering-readiness milestone; formal M57 science remains denied**

Single changed variable: add an explicit single-component substitution diagnostic after M56's aggregate comparison,
without changing the model, samples, outcome, generation rules or formal authorization state.

## Why M57 exists

M56 can eventually answer whether Ours or a baseline predicts 30 withheld behaviors better, but a win or loss alone
does not tell us where the recoverable error entered. The retained pre-change probe forged only the already-defined M56
report shape: it had seven condition metrics and 30 B5/Ours paired records, but **0/10** required localization fields,
zero component interventions and zero provenance records. This proves a diagnostic representation gap only. It does
not prove that retrieval—or any other real component—is wrong.

M57 therefore freezes five observable computational boundaries before any real M56 target outcome is available:

| Stage | Plain-language question | Allowed evidence | Can lead the recoverable-stage ranking? |
|---|---|---|---:|
| perception | Did the system encode the current input correctly? | two-coder observable input annotation fixed before outcome | yes |
| retrieval | Did it select the relevant pre-cutoff history? | two-coder history IDs fixed before outcome | yes |
| state | Did its explicit computational state help? | source-bound observable proxy only; never private mental truth | yes |
| decision | What if the correct action label were already known? | post-outcome one-hot diagnostic ceiling | no |
| realization | Did it express the intended action well in Japanese? | independent blind human surface ratings | no; unavailable now |

Every formal substitution plan must be committed before outcomes are opened. It changes one named stage, records all
downstream recomputation, uses the same samples/resources/no-retry rule, and scores only after every prediction exists.
Decision is visibly an upper bound, not a cause. Missing state or realization evidence remains unavailable rather than
being synthesized.

## Attribution rule

For each eligible stage, M57 measures paired improvement from original Ours to the single-stage substitution using
Brier score, negative log likelihood and top-1 accuracy. It uses 20,000 paired bootstrap draws with frozen seed
570904. A recoverable effect requires the lower 95% bound for both proper-score improvements to exceed zero and top-1
not to worsen. A leading stage requires the same unique leader on Brier and NLL with at least 0.05 separation. Ties,
mixed metrics and interactions return no leader.

This is a descriptive computational localization rule. It never establishes a unique biological or psychological
cause.

## Mechanical rehearsal result

Two author-constructed 30-row fixtures test the analyzer, not Uruha:

| Fixture | Perception Brier recovery | Retrieval Brier recovery | State recovery | Result |
|---|---:|---:|---:|---|
| clear retrieval effect | 0.402 | 1.108 | 0.000 | `leading_recoverable_stage = retrieval` |
| perception/retrieval tie | 1.108 | 1.108 | 0.000 | `leading_recoverable_stage = null` |

For the clear fixture, retrieval also led NLL recovery (1.386 versus perception 0.560). For the tied fixture, the
analyzer returned `ambiguous_interacting_or_unresolved` rather than selecting a stage. In both fixtures the decision
one-hot ceiling was excluded, realization was unavailable, model calls were zero and real target-outcome reads were
zero.

## Retained failure and correction

The first Safari rendering exposed a real presentation defect that unit tests did not: long unbroken stage-status
strings pushed the five-card row past the section boundary. The research rule and thresholds were not loosened. The
page was changed to shrink-safe/wrapping cards with plain Chinese stage names and Brier recovery bars, then reloaded
and rechecked in Safari. The final screenshots contain no visible card overflow.

An initial pre-change-probe test also used two guessed field names instead of the probe's retained schema. The probe
was not rewritten; the test was corrected to assert the existing key map and zero-count field.

## Cost

Seven independent clear-plus-ambiguous fixture pairs were retained. Each pair analyzes 60 synthetic rows and performs
20,000 bootstrap draws per available stage:

- median clear fixture: **0.798261 s**;
- median ambiguous fixture: **0.802508 s**;
- median pair: **1.602724 s**;
- observed pair range: **1.593786–1.612762 s**;
- formal model calls / real target-outcome reads / formal results: **0 / 0 / 0**.

These are local analyzer costs on author-constructed fixtures, not formal model latency, production throughput or a
real-person diagnostic cost.

## Verification

- focused M57 including the implementation freeze: **13/13 passed**;
- direct M54–M57 portion inside the final suite: **281/281 passed**;
- final selected M1/M2/M6/V7/V9/M54–M57 compatibility suite: **349/349 passed** in 96.06 seconds;
- mutation coverage rejects missing samples, invalid probability sums, wrong changed component, plan drift, future
  outcome leakage, retry, outcome-before-commit and caller-minted formal authorization;
- Python compile, JSON parsing, dependency hashes, implementation-freeze hashes and diff whitespace checks passed;
- formal entry rejects malformed run IDs and an otherwise valid run before invoking the analyzer while M56 is absent.

These are selected repository suites, not every historical test.

## Safari graphical acceptance

Safari reused the existing M56.13 test tab and loaded `http://127.0.0.1:7922/dashboard`. The tab count remained 33;
no user tab was created or closed. The corrected page visibly showed:

- `M56 AGGREGATE → M57 COMPONENT SUBSTITUTION`;
- five plain-language stage cards and graphical recovery bars;
- clear fixture `leading = retrieval` next to tied fixture `leading = None`;
- `FORMAL M57 DENIED`, V7 `0/18 + 0/18`, real temporal data `0/30` and formal M56 result `0`;
- a Chinese evidence boundary explaining exactly what the fixture does and does not establish.

No form or visible card overflow remained. The local server was stopped. The remaining read-only Safari tab is safe
to close. Evidence:

- `analysis/m57_safari_component_localization_top_2026-09-04.png`
- `analysis/m57_safari_component_localization_boundary_2026-09-04.png`
- `analysis/m57_safari_component_localization_acceptance_2026-09-04.json`

## Evidence boundary and next admissible step

M57 engineering readiness now establishes that the frozen analyzer can measure eligible observable substitutions,
reject malformed/future-leaking inputs, identify a deliberately clear signal and abstain on a deliberate tie. It has
not localized any real Uruha error and supplies no evidence that Equation V1 is correct, that the system understands
private human state, or that it beats a strong LLM.

The current readiness build intentionally contains no formal-artifact bridge. The pure analyzer rejects every bundle
marked `real_formal_m56_diagnostic` even when a caller supplies `formal_authorization = true`; the result validator
also rejects caller-minted formal results. After M56 is genuinely authorized, a new frozen bridge must derive
authority and same-resource hashes from validated M56 artifacts rather than accepting caller booleans.

Formal M57 execution requires the same external evidence already blocking M55/M56: two distinct humans must complete
the V7 ledgers, V9 needs independently reviewed events, 30 leakage-free temporal rows must exist, and M56 must produce
an authorized formal result. Only then may the precommitted stage plans run without outcome peeking. If the formal
result has no recoverable stage, that negative result must be retained. If stages tie or interact, M58 must freeze one
new causal variable on new sealed data instead of retrofitting a winner.
