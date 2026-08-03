# Qwen3 compiled surface-signal probe

- Only variable: abstract provider labels versus their deterministic concrete surface-only compilation.
- Both signals occupy the first top-level JSON field.
- Eight prompts from four new synthetic sources; two references per provider and source.
- Base Qwen3-4B, greedy decoding, three isolated repeats, no training or save.
- References are loaded only after both conditions finish generation.
