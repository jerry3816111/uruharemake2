# V40 domain-separated action-contract conclusion

## Result

V40 changed only the model-facing output contract. It kept the same Qwen3.5 4B model, 36 retired development cases, deterministic generation settings, V39 action ontology, and V39 grounded compiler.

| condition | exact calls | no-action | required recall | false action | execution parse | trace wellformed | median | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V39 replay control | **100.0%** | **100.0%** | **100.0%** | **0.0%** | **100.0%** | 88.9% | 3.53s | n/a |
| V40 four-array candidate | 55.6% | **100.0%** | 0.0% | **0.0%** | 41.7% | 8.3% | 3.48s | 5.41s |

The candidate failed four preregistered gates: exact calls, required-action recall, execution parse, and trace well-formedness. It does not advance to fresh holdout or runtime integration.

## What failed

- 13 of 36 replies wrapped the object in Markdown fences despite JSON-only instructions.
- 21 of 36 replies had missing or extra root fields.
- 18 individual frames renamed or omitted required fields, especially `commitment`.
- Only three replies were fully well-formed; all three contained empty action arrays.
- The unchanged compiler continued to fail closed, so false actions and unsupported execution remained zero. Safety recovery did not make the representation successful.

## Interpretation

Splitting one frame list into four arrays increased the contract burden for this local 4B model. Basic JSON parseability and an Ollama `format` schema did not guarantee that required nested fields were obeyed. This is evidence against the V40 representation, not evidence that a larger model is required for the whole project.

## Next hypothesis

Return to the better V39 single-array primary representation. When its validator reports a malformed trace, provide the original input, raw frame list, and general validation errors to a separate selective repair step. Compare the locally available 0.8B, 2B, and 4B models on the four retired malformed cases, selecting the smallest model that improves trace quality without changing valid primary outputs or weakening the unchanged grounded compiler.

This tests a human-like self-monitoring pattern: produce a first interpretation, inspect a concrete error signal, and spend extra computation only when correction is needed.
