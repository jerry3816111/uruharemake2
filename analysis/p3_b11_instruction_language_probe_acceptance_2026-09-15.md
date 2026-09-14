# P3-B11 instruction-language isolation probe acceptance

Date: 2026-09-15

## Outcome

**PASS only for the preregistered obvious-surface hypothesis; NOT READY as a usable baseline.**

On one synthetic English input, Japanese stage instructions increased final shared-surface passes
from 1/2 to 2/2 under the same `qwen2.5:7b`, persona, input, empty history, decoding options and
completion caps. All eight calls completed once with exact provider prompt accounting.

## Locked example

Synthetic input:

> A neighbor asked whether I can join a crowded weekend cleanup. I said I have not decided yet.

| arm | direct final | deliberate final | obvious surface passes |
| --- | --- | --- | --- |
| English instructions | `うちはまだ決めかねているので、その件についてはそう伝えたよ。` | `（英語翻訳） I haven't decided yet, so I'll consider it further.` | 1/2 |
| Japanese instructions | `うちはまだ決めかねているみたいだね。行けるかどうかまた教えてほしいな。` | `何か他に質問があれば教えてください。` | 2/2 |

The Japanese deliberate final is still not acceptable as a conversational answer: it is generic,
polite, and disconnected from the source. Therefore the observed 2/2 is only an obvious language-
surface result, not naturalness, grounding, pragmatic quality, or system advantage.

## Root-cause evidence for the next gate

Both deliberate critique stages returned empty text with one completion token. The current pipeline
appends the draft as a final `assistant` message; Ollama then renders that shape without a new
assistant generation prompt. The revise stage likewise receives consecutive assistant scratch
messages. This makes the draft/check/revise baseline structurally unable to provide a reliable check,
even though token accounting is exact.

## Resources and boundary

- Release commit: `a224c61`.
- 8 real/local network calls; 2,107 prompt + 115 completion = 2,222 tokens;
  10.198241 summed condition seconds; 0 paid calls.
- English arm: 982 prompt + 60 completion tokens; Japanese arm: 1,125 + 55.
- 0 developer cases, 0 annotations, 0 confirmation, 0 production DB access.
- 113 focused tests passed before release.

The result supports testing a new private-scratch carrier shape. It does not authorize changing the
frozen v1 comparison, running another developer case, or claiming better understanding.
