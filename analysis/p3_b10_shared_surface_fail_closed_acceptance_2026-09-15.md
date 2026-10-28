# P3-B10 shared-surface fail-closed acceptance

Date: 2026-09-15

## Outcome

PASS for the bounded surface-fairness correction. No model call was authorized or executed.

## Before

P3-B9 accepted both baseline finals when they were merely nonempty, even though the direct final was
mixed English/Japanese and the deliberate final was an English translation wrapper. The product
firewall also allowed the persona first-person `私`, despite the frozen shared contract requiring
`うち`.

## Change

- Added `shared_visible_surface_contract` to the pure P3 contract layer. It checks only obvious,
  machine-observable requirements: nonempty, Japanese present, no Latin-script leakage, no `私` as
  first person, no quote/translation wrapper, and no internal-analysis marker.
- Product and baseline canary result gates now require that contract. It detects failures; it does
  not rewrite baseline answers or claim human-rated naturalness.
- Product final normalization now changes standalone persona first-person `私` to `うち`. Compound
  words such as `私生活` are intentionally unchanged.

## Evidence

- Existing locked P3-B9 finals are now correctly classified as 0/3 surface passes:
  product=`no_watashi_first_person`; direct=`no_latin_script`; deliberate=`no_latin_script` plus
  translation/quote wrapper.
- Offline counterfactual on the immutable product sentence:
  `友人が週末のコンサートに招待し、私は行こうかと言ったんだね。`
  becomes
  `友人が週末のコンサートに招待し、うちは行こうかと言ったんだね。`
  Only the first-person surface changes; the known semantic weakness remains visible.
- 109 focused tests passed across the P3 comparison and V2.11 visible-language guard suites.
- 0 new model/network/paid calls; no new dataset, annotation, confirmation, or production DB access.

## Boundary

This prevents an infrastructure pass from being mistaken for a valid Japanese/persona comparison.
It does not improve pragmatic understanding, repair the old answer, prove naturalness, or establish
system advantage. The next isolated variable is the language of baseline stage instructions, tested
first on a fresh synthetic English probe before any new product comparison.
