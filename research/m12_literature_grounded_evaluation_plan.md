# M12 Literature-Grounded Evaluation Plan

Date: 2026-08-17  
Status: retrospective evaluation protocol over frozen artifacts; **not a preregistration**

## Why this exists

The project already records Top-1, F1, Brier, NLL, ECE, rolling cutoffs,
ablations, interventions, memory checkpoints, resources, and negative results.
What was missing was a single research evaluation that:

1. maps each metric to a published method;
2. compares `Ours` and a fixed strong baseline on the same events;
3. quantifies uncertainty instead of comparing averages only;
4. tests whether a favorable result replicates across a new semantic timeline
   and a second person;
5. refuses to turn automatic language proxies into human preference evidence.

## Literature-to-project mapping

| Literature method | What M12 uses it for | What it does not prove |
|---|---|---|
| Gneiting & Raftery (2007), strictly proper scoring rules | Brier and NLL are primary because they score the complete behavior distribution | A low score does not prove the latent state equals a private mind |
| Guo et al. (2017), calibration | Reliability bins and ECE remain visible | With only 8/16 rows, ECE is descriptive and bin-sensitive |
| Peyrard et al. (2021), paired NLP evaluation | Candidate and B5 are compared per identical event; win/loss and paired deltas are retained | An unpaired average is not enough for a winner claim |
| Berg-Kirkpatrick et al. (2012), bootstrap/significance in NLP | 20,000 paired bootstrap samples and exact sign-flip tests quantify uncertainty | Retrospective p-values do not become a new preregistered confirmatory test |
| Maharana et al. (2024), LoCoMo | Long memory is decomposed into delayed recall, update, false-memory control, grounding, and cost | The five V2.22 checkpoints are not equivalent to LoCoMo's very-long-dialog benchmark |
| Liu et al. (2016), dialogue-metric limitation | BLEU/string overlap is not used as the primary quality claim | Automatic surface scores do not replace felt-understanding or naturalness raters |

## Fixed comparison

The primary baseline is `B5_STRUCTURED_HISTORY`, fixed by the master research
specification as the strongest structured history-conditioned LLM baseline. It
must not be replaced after seeing test performance.

Three frozen tracks are re-evaluated:

- M6: eight author-designed synthetic holdouts;
- M8: sixteen source-disjoint fictional events over four rolling cutoffs;
- M9: sixteen second-person fictional events with unchanged core logic.

For each track, negative `candidate - B5` Brier/NLL is favorable. M12 reports:

- mean paired delta;
- 95% paired bootstrap interval;
- exact two-sided sign-flip p-value;
- Top-1 discordance and exact McNemar p-value;
- per-case win/tie/loss;
- directional and inferential verdicts.

## Claim rule

The central claim "the hybrid system is better than a strong history-conditioned
LLM" is not supported unless the direction replicates across M6, M8, M9 and a
formal real-person temporal dataset. A synthetic pass can validate engineering
and a mechanism; it cannot establish the public Uruha model.

Language naturalness and felt understanding stay outside the automatic central
score. An LLM judge could be added later as a proxy, but would not be presented
as independent human evidence.
