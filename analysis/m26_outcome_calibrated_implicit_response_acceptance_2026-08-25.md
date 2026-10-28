# M26 Outcome-Calibrated Implicit Desired-Response Distribution and Abstention

Status date: 2026-08-25  
Scope: bounded product milestone; isolated local runtime and Safari validation  
Claim boundary: operational action belief, not a probability of a private mental state and not externally human-calibrated mind reading

## 1. Problem closed

M25 made an explicit Chinese, English, or Japanese request for listening, companionship, practical help, teasing, or clarification authoritative. It did not decide what to do when the user did not name a desired reply form. Before M26, M18 exposed useful candidate utilities, but a utility score was still being treated too much like a decision.

M26 adds a final implicit-response boundary before the visible Japanese reply:

```text
M18 candidate utilities
→ normalized operational distribution
→ scoped outcome reliability
→ probability / margin / evidence / outcome gates
→ execute the implicit mode OR abstain into low-pressure clarification
→ next-turn supported / contradicted / uncertain update
```

The current-turn M25 explicit request and M20 explicit correction still outrank the implicit distribution.

## 2. What changed in the real runtime

- `uruha_adaptive_person_model.py`
  - converts the six M18 policy utilities into a temperature-normalized distribution;
  - keeps raw utility, base probability, outcome-weighted probability, evidence quality, learned reliability, and alternatives separate;
  - applies explicit probability, probability-margin, evidence, and outcome gates;
  - changes the selected policy to `calibrate_need` only when an implicit guess does not pass;
  - permits strong current physical-wellbeing evidence to select physiological care even when older interaction preference points elsewhere;
  - stores no raw dialogue in the adaptive M26 state.
- `uruha_brain_mac.py`
  - executes the M26 gate before runtime memory records the final decision;
  - emits distribution and outcome events into the real cognition trace and turn logic.
- `uruha_memory_observatory.py`
  - displays the M26 distribution and next-turn outcome as connected runtime nodes;
  - shows top mode, probability, margin, evidence, gate result, and prior outcome;
  - explicitly labels the number as an operational belief, not an externally calibrated human-state probability.
- `uruha_web_ui.py`
  - keeps the M26 trace inside the M24 progressive browser payload budget.

## 3. Isolated Safari multi-turn acceptance

Runtime isolation:

- page: `http://127.0.0.1:7867/?m26final=1`
- session: `20260825_120542_03f37fc8`
- log: `/tmp/uruha-m26-safari.jvPBLE/web.jsonl`
- adaptive state: `/tmp/uruha-m26-safari.jvPBLE/adaptive.json`
- production memory DB was not used or modified.

| Turn | User input | Visible Japanese reply | M26 action | Top operational belief | Previous outcome |
|---|---|---|---|---|---|
| 1 | `我從早上就一直坐不住，腦子停不下來。` | `まあ、寝てないのか、考え事で止まんないのか、まずそこだけどっち？` | abstain to low-pressure clarification | clarification, p=0.6467, margin=0.5544, evidence=0.0000 | not available |
| 2 | `不是要吐槽，我是真的想要一個現在能做的方法。` | `あー、そこ読み違えた。今すぐできる一個だけ一緒に決めよ。` | M20/M25 explicit-authority bypass | practical help, p=0.5531, margin=0.4333, evidence=0.9801 | contradicted; scoped reliability 0.5000→0.3333 |
| 3 | `我今天又從早上就一直坐不住，腦子停不下來。` | `最初の一個だけ決めよ。いま頭に浮かんでることをメモして、五分だけそこから離れればいい。` | execute learned implicit mode | practical help, p=0.4441, margin=0.3016, evidence=0.5752 | uncertain; no false credit |
| 4 | `我頭痛而且整晚沒睡，像平常一樣腦子又停不下來。` | `寝不足とか体のしんどさがあるなら、まず水飲んでちょっと休も。` | execute strong current physiological-care evidence | physiological care, p=0.6558, margin=0.5514, evidence=0.9702 | uncertain; new request not misread as feedback |

This sequence verifies four different behaviors in one real Web session: initial restraint, explicit correction authority, reversible experience reuse, and current physical evidence overriding older practical-help preference. All four user-visible replies remained natural Japanese.

Visual evidence:

- `analysis/m26_safari_initial_abstention_2026-08-25.png`
- `analysis/m26_safari_explicit_correction_outcome_2026-08-25.png`
- `analysis/m26_safari_verified_implicit_execution_2026-08-25.png`
- `analysis/m26_safari_physiological_care_execution_2026-08-25.png`
- `analysis/m26_safari_distribution_graph_2026-08-25.png`
- `analysis/m26_safari_distribution_node_detail_2026-08-25.png`

## 4. Automated evidence

- M26-specific contract/runtime/graph suite: **6 passed**.
- Focused compatibility from V2.12 plus Japanese, identity/proactive, routing, observatory, and M16–M26: **198 passed, 3 warnings** in 6.13 seconds.
- The compatibility suite includes retained learned-transfer, explicit-correction, final-Japanese, no-idle-visible-speech, graph, and payload-budget behavior.

## 5. Retained failures found while implementing M26

These were not deleted from the engineering record:

1. A single strict probability/margin threshold blocked an already verified reversible teasing preference. M26 now uses a narrower learned-evidence gate, while still requiring matching scope and negative-transfer checks. The values are engineering thresholds, not externally calibrated constants.
2. High uncertainty originally blocked an explicit headache/no-sleep care case. Strong current physical-wellbeing evidence now outranks the general uncertainty gate for the physiological-care policy.
3. Safari automation `type_text` corrupted Chinese input into punctuation. Acceptance switched to the system paste path; this was a test-control issue, not a UruhaBrain reply defect.

## 6. What is and is not complete

M26 completes a bounded operational mechanism: the system no longer has to treat the highest implicit utility as permission to act. It can expose alternatives, abstain, obey correction, reuse reversible experience, and distinguish an unrelated next request from decisive feedback.

M26 does **not** establish:

- that `p=0.65` means a human user wants that response 65% of the time;
- population-level calibration, human preference superiority, universal paraphrase understanding, or private-state inference;
- a biological human equation, consciousness, or equivalence to 一ノ瀬うるは.

The next necessary milestone is **M27 Causal Outcome Calibration Ledger and Evidence-Count Guard**: retain privacy-safe M26 predictions and only causally linked outcomes, compute empirical reliability/coverage when enough evidence exists, exclude unknown outcomes from successes, and prevent automatic confidence claims or threshold tuning before a minimum evidence gate is met.
