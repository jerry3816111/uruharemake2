# M18 Hierarchical Context + Adaptive Policy Coverage

Date: 2026-08-24  
Status: bounded product-development milestone complete  
Scope: local runtime, isolated persistence, and Safari acceptance; not production readiness, mind reading, or human-equivalent understanding

## 1. Product problem

M17 could reuse an explicitly corrected response preference only when the categorical context matched exactly. That prevented broad contamination, but it also meant that nearby wording, another interaction inside the same domain, or the same relationship style could not be reused safely. Its visible policy surface was also anchored to six fixed behaviors.

M18 is complete only if the real runtime can:

1. reuse experience through an auditable `exact -> domain -> relationship` hierarchy;
2. reject nearby experience when current evidence conflicts or safety should take priority;
3. compose the visible response from care, directness, humor, listening, actionability, and distance;
4. preserve the selected semantics while varying natural Japanese;
5. retain feedback, decay, privacy, restart, visible graph, and warm-turn latency behavior.

## 2. What changed

### 2.1 Hierarchical experience reuse

The adaptive store now evaluates three source levels with bounded weights:

```text
exact context       1.00
same domain         0.62
same relationship   0.36
```

Every used or rejected atom/dimension records its source scope, match level, effective confidence, age, and gate reason. Relationship fallback may transfer only interaction style; it cannot transfer content needs such as “the user wants a solution.”

### 2.2 Negative-transfer gates

Current visible evidence always outranks prior interaction style. The guarded cases include:

- an explicit solution request blocks a prior no-advice/teasing preference;
- headache, sleep debt, or physical strain blocks humor transfer;
- non-exact humor requires a current familiarity cue;
- positive arousal cannot be copied into unrelated domains;
- relationship fallback is limited to directness, humor, and distance;
- emotional/listening bids suppress high actionability;
- expired or low-confidence scopes are rejected rather than silently revived.

### 2.3 Composable response dimensions

The selected semantic policy is now realized through six inspectable values:

```text
care · directness · humor · listening · actionability · distance
```

Learned dimensions are blended only after hierarchy and negative-transfer checks. Current physical, solution, listening, humor, uncertainty, and relationship evidence can then clamp the result. The persistent store contains structured values and evidence digests, not raw dialogue.

Each semantic anchor has multiple casual-Japanese realizations. Variant selection is deterministic from the input digest and turn index, so repeated nearby turns can vary without changing the selected action or bypassing the final Japanese guard.

### 2.4 Feedback segmentation

M18 recognizes that one utterance may both evaluate the previous reply and begin a new topic. For example:

```text
Exactly, that's right. Like usual, I'm excited that the result is about to come out.
```

The first clause supports the previous response. The new positive topic is evaluated as the current request and is not written back as an atom of the previous context. This prevents a common cross-turn attribution error.

### 2.5 Live graph and fast path

The runtime graph now exposes:

```text
signal -> feedback -> context -> hierarchy/gates -> state -> candidates
-> dimensions -> prediction -> action -> Japanese surface -> persistence
```

The comparison card contrasts direct generation with the M18 path. A verified domain reuse with a small but decisive margin may take the guarded fast path; safety, factual-memory, protected-intent, Japanese-surface, and downstream monitoring guards remain active.

## 3. Isolated Safari acceptance

Runtime isolation:

```text
memory DB:     /tmp/uruha-m18-final.BtTKyF/db
adaptive:      /tmp/uruha-m18-final.BtTKyF/adaptive.json
conversation:  /tmp/uruha-m18-final.BtTKyF/web.jsonl
```

The formal database and external deployment were not used.

### 3.1 Correction and relationship transfer

The first English arousal disclosure selected a bounded clarification. The next turn explicitly rejected advice and requested familiar teasing, producing:

```text
朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。
```

After a full Web-process restart, a mixed support/new-topic turn produced:

```text
あー、それ楽しみで回り続けてるやつじゃん。うちまで気になってきた。
```

The graph showed `feedback=supported`, `scope_match=relationship`, `used=3`, `blocked=3`, and selected `share_arousal`. It reused only bounded familiar style and did not copy the old teasing behavior into positive anticipation.

### 3.2 Domain reuse and varied surface

Input:

```text
Like usual, my mind won't stop again.
```

Result:

```text
てか、お前の脳みそ、朝から勝手に延長戦入ってんじゃん。
```

The graph showed `scope_match=domain`, `used=9`, `blocked=0`, `playful_tease`, humor `0.98`, directness `0.94`, and a different Japanese realization from the earlier tease. Backend user-wait trace was `1.1630s`, cognition `0.0205s`, target met, with one redundant general-planner call avoided.

### 3.3 Explicit goal conflict

Input:

```text
Like usual, my mind won't stop again. How do I stop it now?
```

Result:

```text
最初の一個だけ決めよ。いま頭に浮かんでることをメモして、五分だけそこから離れればいい。
```

The graph retained the same-domain source but blocked three conflicting transfers, selected `solve_regulation`, and composed actionability `0.96` / directness `0.92`. It did not reuse the teasing surface. Backend user-wait trace was `1.1645s`, cognition `0.0165s`.

### 3.4 Physical evidence overrides relationship style

Input:

```text
I have a headache and didn't sleep all night. Like usual, my mind won't stop.
```

Result:

```text
体がしんどい方なら、無理に頭止めようとしないで一回水飲も。
```

The context changed to `physical_wellbeing`. Relationship reuse was limited to two safe style dimensions while four transfers were blocked. The selected policy was `care_physiology`; care became `0.92`, humor `0.02`. Backend user-wait trace was `1.2412s`, cognition `0.0133s`.

### 3.5 Restart and privacy

The adaptive store survived two complete Web-process restarts. It ended with schema `uruha_adaptive_person_model_m18`, store version `3`, two learned scopes, and structured pending state. Exact scans for all acceptance dialogue fragments returned no matches in the adaptive JSON.

Safari used the existing local UruhaBrain tab. The other 15 tabs were not closed or modified.

## 4. Visual evidence

- `analysis/m18_safari_hierarchical_transfer_2026-08-24.jpeg`: relationship-level reuse without copying the old content behavior.
- `analysis/m18_safari_domain_reuse_latency_2026-08-24.jpeg`: domain reuse with a different natural-Japanese tease.
- `analysis/m18_safari_negative_transfer_dimensions_2026-08-24.jpeg`: explicit solution and physical-safety overrides in the visible chat.
- `analysis/m18_safari_graph_comparison_card_2026-08-24.jpeg`: direct-generation comparison card plus the live M18 graph entrance.
- `analysis/m18_safari_runtime_node_graph_2026-08-24.jpeg`: actual connected runtime nodes for the physical-safety turn.

## 5. Automated evidence

M18-specific tests:

```text
Ran 11 tests in 0.496s
OK
```

Focused compatibility suite covering M18/M17/M16, functional/pragmatic/personhood loops, Japanese visible output, idle suppression, proactive behavior, and graph contracts:

```text
Ran 100 tests in 1.076s
OK
```

Python compile and `git diff --check` passed for the changed runtime files.

A separate historical 57-test group was intentionally not folded into the M18 pass count: six pre-existing lock/fixed-string checks fail because they expect the old `gr.Tab("Chat")` literal or immutable historical artifact hashes in this already-dirty worktree. The other 51 tests in that group passed. M18 did not rewrite historical locks to manufacture a green result.

## 6. Honest completion boundary

M18 is complete as a bounded product milestone. It proves that hierarchical experience and composable response dimensions change real local replies while safety and visible trace remain connected.

It does not prove that the seven manual domains cover ordinary conversation, that the six semantic anchors are a complete human response space, that marker-based evidence captures culture or indirect speech generally, or that the system understands private mental states. The Japanese variants remain a finite realization bank. No broad independent human evaluation was performed.

Safari also exposed the next product defect: the brain trace reports roughly 1.2 seconds for decisive M18 turns, but the Gradio page can still wait tens of seconds when the queued autonomous polling cycle occupies the single frontend concurrency slot. One physical-safety turn displayed `43.7s` at the page layer even though its brain trace was `1.2412s`. This must not be hidden by quoting only cognition time.

## 7. Next product milestone

M19 is **Human-Priority Cognitive Scheduling**:

1. prevent latent rehearsal/autonomous polling from occupying the human-message queue;
2. make direct human input preempt or bypass background cognition safely;
3. retain non-idle proactive features without restoring silence-triggered visible speech;
4. expose queue wait, brain work, and surface streaming as separate graph timings;
5. verify in Safari that repeated background ticks cannot push a decisive human turn beyond the warm interaction budget.

This is a product correctness issue: a system cannot feel attentive if its private background process makes a human wait, even when its internal response decision is fast.
