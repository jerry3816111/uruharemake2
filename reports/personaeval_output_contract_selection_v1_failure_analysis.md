# PersonaEval output-contract selection failure analysis

This is a post-hoc diagnostic. The preregistered scores, gates, and parsers remain unchanged.

## Formal result

| Condition | Parsed | Correct | Repeat prediction agreement |
| --- | ---: | ---: | ---: |
| Strict probability | 28/30 (93.33%) | 12/30 (40.00%) | 9/9 (100.00%) |
| Candidate name | 19/30 (63.33%) | 5/30 (16.67%) | 6/9 (66.67%) |

- Candidate-minus-strict accuracy: `-23.33` percentage points.
- Exact paired McNemar p-value: `0.09228515625`.
- The point difference is not statistically significant at `0.05`; the pilot is small and does not establish a population-level degradation.
- The candidate contract nevertheless failed every preregistered acceptance gate, so it is rejected without a larger run.

## Failure localization

| Track | Strict parsed / correct | Candidate parsed / correct | Observed candidate-contract failure |
| --- | ---: | ---: | --- |
| Drama | 9/10 / 2/10 | 8/10 / 2/10 | One related but non-option phrase and one long analysis instead of one exact option. |
| Expertise | 10/10 / 4/10 | 1/10 / 0/10 | Nine outputs were expert names, while the official options were audience expertise levels. |
| Literary | 9/10 / 6/10 | 10/10 / 3/10 | Parsing was solved, but role-identification accuracy fell; this is not a format-only failure. |

The phrase `candidate name` was semantically ambiguous across official tracks. In the Expertise track, the model deterministically answered names associated with the subject rather than copying one official level option such as `Expert` or `Graduate Student`. This explains most parse loss, but it does not explain the Literary accuracy loss.

## Reliability and cost

- Candidate exact output agreement was `9/9`, but valid prediction agreement was only `6/9`. Three repeated rows produced the same invalid output every time; this is a deterministic contract failure, not sampling noise.
- Primary completion tokens fell from `1,832` to `615` (`-66.43%`).
- Primary generation time fell from `292.128` to `204.265` seconds (`-30.08%`).
- Lower latency does not compensate for the failed reliability and ability gates.

## Decision boundary

- Do not rescore non-option outputs with a lenient parser.
- Do not enlarge this exact `candidate name` contract.
- Do not use this pilot to judge the target person, replace human raters, train a judge, or authorize production.
- The next evaluator experiment, if pursued, must be a new preregistered local-judge redesign on another disjoint holdout. It cannot be presented as a continuation that retroactively repairs this result.
