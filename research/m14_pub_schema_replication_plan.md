# M14 Schema-enforced PUB Replication

M13 showed two separable facts: reasoning beat immediate answering, but Ours did
not beat generic deliberation; moreover, Ours instantiated its complete schema
in only 15/64 rows.  M14 changes exactly one mechanism: Ollama receives a strict,
condition-specific JSON Schema.  Prompt text, model, decoding, tasks, sample
size, metrics, and gates stay fixed.

The formal sample is the next 16 hash-ranked IDs per task, not any of M13's 64
consumed cases.  A three-call probe uses public item 0, which was already viewed
and is excluded from every formal sample.  The formal run cannot begin unless
all probe payloads match their full schemas.

M14 succeeds only if all outputs satisfy full schemas and Ours beats Generic by
at least five accuracy points with exact paired McNemar p <= .05, without a task
regression greater than 12.5 points.  A schema pass alone is engineering
evidence, not a cognitive superiority result.
