# V39 grounded frame-isolation conclusion

## Result

V39 replayed the same frozen 4B outputs used by V37 and V38. It added a general colloquial gesture anchor and isolated malformed individual frames from executable grounded frames.

| condition | exact calls | no-action | required recall | false action | execution parse | trace wellformed |
|---|---:|---:|---:|---:|---:|---:|
| V38 full control | 97.2% | 100.0% | 95.5% | 0.0% | 91.7% | 88.9% |
| colloquial anchor only | 100.0% | 100.0% | 100.0% | 0.0% | 91.7% | 88.9% |
| frame isolation only | 97.2% | 100.0% | 95.5% | 0.0% | 100.0% | 88.9% |
| full V39 | **100.0%** | **100.0%** | **100.0%** | **0.0%** | **100.0%** | 88.9% |

The colloquial anchor fixed the only V38 action regression without breaking an ordinary verbal acknowledgement test. Frame isolation made malformed neighboring frames non-executable while preserving valid grounded requests.

## Remaining boundary

Four of 36 raw model traces still contained at least one malformed frame:

- a commitment label was emitted as an action value;
- the textual prompt placeholder was copied as a domain;
- a requested unsupported action used an evidence string not present verbatim in the input;
- two frames repeated the same raw target under different commitments.

The compiler handled all four safely, but compiler recovery is not evidence that the model's observable internal representation is correct.

## Decision

- All action, safety, grounding, execution-parse, and latency gates pass.
- Trace well-formedness is 88.9%, below the preregistered 90.0% development gate.
- V39 therefore does not advance, and no fresh holdout is created or consumed.
- No runtime or physical VRM execution change is authorized.

## Next hypothesis

V40 should leave the successful V39 compiler unchanged and improve only the model-output contract:

- use a conditional JSON Schema so each domain exposes only its own legal values;
- remove union-like placeholder text that a small model can copy literally;
- explicitly return an empty frame list for generic discussion without a concrete action value;
- continue requiring exact evidence copying.

This tests whether trace errors come from the output contract rather than model capacity.
