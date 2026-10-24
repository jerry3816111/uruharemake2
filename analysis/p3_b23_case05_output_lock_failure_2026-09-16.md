# P3-B23 case05 output-lock failure

Date: 2026-09-16

## Outcome

**FAIL retained; no retry and no annotation access.**

The fresh `p3-smoke-speaker-memory-en` case completed all four product turns and all four
same-model direct-v2 turns. The locked result is
`analysis/p3_b23_case05_output_lock_result_2026-09-16.json`, SHA-256
`cfdd42a4c50665cb2714b9430442f40d221e558933ec395311d382b61fcca7b9`.

The B23 accounting correction worked as designed:

- eight invocation intents and eight completion records were retained;
- two actual product calls and four direct calls produced six provider/network calls total;
- all six calls were accounted exactly, with zero failure/retry/paid calls;
- 2,285 prompt tokens, 381 completion tokens and 51.232715 seconds total runner wall time were recorded;
- the restart reused only the isolated case memory path, then removed the ephemeral workspace;
- annotation, confirmation and production DB access remained zero.

This disproves B20's old assumption that a valid four-turn product run must make at least four
provider calls. Product u3 and u4 completed with zero provider calls and still produced signed turn
records. Zero-call-aware accounting is therefore a valid harness repair, not a quality result.

## Locked visible outputs and failed gate

Product:

1. `は青いマグカップを集めている。うちにはの方が好ましい。`
2. `彼女は来月夜市を訪れるんだね。`
3. `ん、その話もう少し聞かせて。`
4. `ん、その話もう少し聞かせて。`

Direct-v2:

1. `そうですね、それぞれの嗜好は違いますね。`
2. `彼女は来月夜市に行きたいと言っていた。`
3. `あなたは Plain glass cups ( Plainなガラスコップ)が好ましいと言いました。`
4. `夜市に行く計画はミナさんのものだったよ。その点は間違えちゃだめだね。`

The sole contract failure was `all_eight_shared_surface_pass=false`: direct u3 contained Latin
script. Outputs are therefore not eligible for native judge grading, and no product/direct quality
preference is claimed.

## Product failure localization without answer access

The product's selected working memory on u3 contained the u1 speaker-qualified episode, and its
planner core was `Plain glass cupの方が好ましいって言ったよね`. The memory was nevertheless
classified as `background_only / relevant_but_not_requested`, so no memory surface authority was
created. Self-monitor repair then emitted an internal instruction-like sentence; the Japanese
language guard correctly rejected it and used the generic casual fallback. u4 repeated the same
path despite retrieving the night-market episode.

The existing P2 speaker-qualified adapter is intentionally limited to explicit quoted-source
questions such as “who said this phrase”. It does not cover an explicit first-person preference
recall question or a current other-versus-self ownership correction. B24 may repair only that bounded
contract using already-selected evidence. It must not rerun/regrade B23, scan unselected memory,
guess a speaker, or change the baseline, model, annotations or locked outputs.

This is an exposed developer failure and a causal implementation lead, not holdout or human evidence.
