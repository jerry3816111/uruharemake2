# M39 Semantic + Persona Surface-Act Verifier — Acceptance Report

## Outcome

M39 is complete as a bounded product/research milestone. Its first and only frozen 24-case formal reserve passed every preregistered gate. The retained pre-M39 metadata-only surface audit achieved 25% expected-action accuracy; M39 achieved 100%.

The result demonstrates a specific mechanism: after the system has selected a response policy, the final visible Japanese can be checked and boundedly repaired for source-role inversion, unsupported additions, policy-act non-realization and a narrow persona-register boundary. It does not prove open-domain semantic equivalence or human felt-understanding preference.

## Why M39 was necessary

M34–M38 could correctly show `selected_policy_id=care_physiology` or `share_arousal` and still mark the surface as matched using metadata. Real Safari turns proved that this was insufficient:

- `I didn't sleep last night...` became `私は昨夜寝なかった...`, assigning the user's experience to Uruha.
- a verified `share_arousal` branch could produce a literal restatement without actually staying with the user;
- an earlier M37 turn added an unsupported story about waiting for a result.

These are not failures of branch selection. They are failures between the chosen branch and the final utterance.

## Implemented boundary

M39 runs after the existing Japanese language guard and before episode memory/UI publication. It keeps the already-selected branch fixed and inspects only observable surface integrity:

1. builds a raw-free source frame with user/third-party role and bounded observable concept IDs;
2. checks whether the Japanese reply reassigns a user or third-party state to the wrong speaker;
3. checks a bounded set of unsupported event/time/cause additions;
4. checks whether the actual wording performs `share_arousal`, `listen_presence`, `solve_regulation`, `care_physiology`, `calibrate_need` or `playful_tease`;
5. either accepts, performs a bounded policy-aware Japanese repair, or leaves protected safety/factual/deliberation routes untouched;
6. audits the repaired surface again and adds an M39 node before the final utterance node.

M39 is installed through a new Web wrapper and live launcher hook, so M37/M38 frozen implementation files remain byte-identical.

## Frozen formal result

- Cases: **24** (English 9, Chinese 8, Japanese 7).
- Pre-M39 metadata-only expected-action accuracy: **25%**.
- M39 expected-action accuracy: **100%**.
- Role-inversion repair recall: **100%**.
- Unsupported-addition repair recall: **100%**.
- Selected-policy realization repair recall: **100%**.
- Correct-surface noninterference: **100%**.
- Protected-route noninterference: **100%**.
- Post-repair policy-act match: **100%**.
- Forbidden concept after repair: **0%**.
- Visible Japanese format: **100%**.
- Formal-register residue: **0%**.
- Raw dialogue persistence / unverified mental-fact writes: **0 / 0**.
- Median / p95 verifier latency: **0.000062 / 0.000346 seconds**.
- Model generation calls: **0**.

Formal raw result SHA-256: `28c60f0b46466e655706aa6305fe9f299f75b15ce5979fa83625bf0ff42758d2`.

The baseline is deliberately the retained pre-M39 surface audit, not a same-model LLM generation baseline. Therefore the 25%→100% difference is evidence for this verifier's added detection/repair coverage, not evidence that the full UruhaBrain is broadly better than a strong LLM.

## Isolated Safari evidence

The M39 wrapper was run on port 7876 with a temporary memory DB, session DB, adaptive model and logs. No existing Safari tab was closed; the M38-owned tab was reused.

### Retained role-inversion case

Input: `I didn't sleep last night, but I'm not asking you to fix anything.`

Visible reply: `寝てないのか。そりゃしんどいだろ、無理すんな。`

The graph recorded `agent_first_person_owns_user_state`, repaired the reply and changed the actual care-policy audit from false to true. User wait was 14.8205 seconds, so semantic repair passed but latency remains uneven.

### Cross-turn M37 → M39 linkage

The user established `task_stall → share_arousal`, confirmed it, and later said `The report has stalled again.` M37 matched the verified relation and M34 selected companionship. The pre-M39 candidate only restated the stall; M39 detected `policy_act_match_before=false` and produced `進んでないのか。まあ、今はうちがここにいる。`, after which the act audit was true.

### Noninterference

An already-correct companionship reply was accepted unchanged. `Who are you?` still produced `うちは一ノ瀬うるは。そこは間違えてない。`; identity and Japanese persona output did not regress.

### Retained upstream failure

The benign support turn `Yes, that's exactly right.` was misclassified upstream as `safety_sensitive` and produced `先に、うわ、今の言い方は無理。ちょっと距離取るぞ。` M39 correctly did not override a protected route, but the user-visible result is still wrong. This is not counted as an M39 pass. It defines the next independently attributable milestone: affirmation/safety route disambiguation.

## Verification and integrity

- M39 focused/evaluator tests: **10 passed**.
- M16–M39 plus personhood compatibility: **207 passed**, 3 warnings.
- Six non-reserve development probes: **6/6**.
- Python compile, wrapper import and diff checks: passed.
- Before formal execution: M39 freeze **10/10**, M37 freeze **10/10**, M38 freeze **11/11** hashes matched.
- Formal reserve executed exactly once; result is immutable.
- Accepted Safari raw utterances did not appear in the adaptive JSON; the stored M37 relation contains typed predicate, policy and digests only.

## Claim boundary and next milestone

M39 supports the claim that a bounded, traceable final-surface verifier can prevent several high-impact "thought correctly, spoke incorrectly" failures without changing correct or protected replies. It does not establish unrestricted semantic understanding, human preference, natural Uruha equivalence, consciousness, mind reading or a complete human-brain equation.

The next single-core milestone should be M40 `Affirmation vs Safety Route Disambiguation`: benign support/confirmation language must not enter a protected danger/boundary route, while genuine safety input must retain protection. M39 itself must not be modified to hide that upstream error.
