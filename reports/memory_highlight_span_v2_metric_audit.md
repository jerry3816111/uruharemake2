# Memory Highlight + Span V2: Interrupted Metric Audit

The first full run was deliberately interrupted after 10 completed cases because the frozen
`polarity_hit` concept was implemented with an incorrect punctuation boundary.

## Observed error

- Six A/B responses began with `Yes.` and contained the correct supporting entity.
- The implementation accepted `Yes ` and `Yes -` but rejected `Yes.`.
- This was a scorer false negative, not a model, memory, highlight, or span-contract failure.

## Correction boundary

- Replace the delimiter list with a start-of-response whole-word check for `Yes` and `No`.
- Apply the same correction to every condition.
- Add tests for period, comma, hyphen, and prefix words such as `yesterday` and `nobody`.
- Do not change the dataset, gold labels, selector, model, seed, prompts, architecture, or gates.

## Preserved audit evidence

- Completed cases: `10/36`.
- Interrupted JSON SHA-256: `0148b447701565fda37c49627d06c77f12bec79e83739afc7407da7a43f7c229`.
- Interrupted results SHA-256: `56c2048ef6435b44bf5babb008c5c4e850b404cd8133165ba6a9cb9f1c54d779`.
- Model digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
- Original implementation commit: `8729e1e`.

The interrupted raw checkpoint remains outside the repository and is not reused. The corrected
run starts from case 1 and writes a new implementation-bound report.
