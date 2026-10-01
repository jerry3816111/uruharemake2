# Temporal leakage policy

For prediction time `t`, no component may access evidence created or reviewed after `t`, including:

- future transcripts, event labels, outcomes, or extracted memories;
- summaries or embeddings built from future material;
- prompts, examples, rules, or thresholds tuned after seeing test outcomes;
- later sources that retrospectively describe the event;
- holdout content before candidate, scorer, config, and code freeze.

Every temporal dataset build must validate source time, event time, extraction time, dataset partition, index membership, and config binding. Formal runs must record dataset version, cutoff, model/version, prompt, retriever, seed, hardware, commit, and artifact hashes.

Foundation-model pretraining may contain target-period knowledge. Formal reports must document this contamination risk and include evidence-only or outcome-stripped modes where possible. A leakage violation invalidates the affected result; it may not be repaired by relabeling the run after outputs are seen.
