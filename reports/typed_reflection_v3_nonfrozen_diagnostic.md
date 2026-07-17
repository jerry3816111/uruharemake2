# Typed Reflection V3 non-frozen diagnosis

## Scope

This diagnosis used three new utterances that do not appear in the frozen V3 pilot. It is root-cause evidence, not a benchmark result.

## Reproduction

With the V3 free-form prompt, `qwen2.5:7b` returned valid five-field JSON for semantic, procedural, and interpretive inputs, but copied the schema placeholder `confidence: 0.0` in all three cases. The runtime correctly rejected each result because the frozen safety minimum was `0.65`.

One interpretive output also translated the English phrase `maybe later` into the non-source Chinese text `也许以后`. Raising or deleting the confidence threshold would therefore hide a real grounding and language-quality risk.

## Structured-output probe

The same three new utterances were then sent through Ollama JSON Schema structured output at temperature 0. Type, exact evidence quote, confidence range, and required fields were constrained successfully in 3/3 probes. The interpretive Japanese surface still contained source-external Chinese in 1/3 probes.

## Engineering decision

V4 should not ask the model to decide provenance fields. The program should supply reflection type, exact source utterance, source episode, source hash, and grounding confidence. The model should generate only `content_jp` and `trigger_jp` under JSON Schema. Source-external language contamination gets at most one bounded repair; if it remains, no memory is written.

Official references:

- https://docs.ollama.com/capabilities/structured-outputs
- https://qwen.readthedocs.io/en/v2.5/index.html
