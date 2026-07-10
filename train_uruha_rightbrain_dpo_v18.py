#!/usr/bin/env python3
"""Train a continued RightBrain LoRA with offline semantic-completeness DPO."""

import argparse
import json
import math
import random
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer

from project_paths import (
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DATASET_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_TRAINING_RUN_REPORT_PATH,
)
from train_uruha_rightbrain_contract_v1 import (
    DEFAULT_BASE_MODEL,
    _sha256,
    build_model,
    init_adapter_report,
    resolve_model_dtype,
)


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_INIT_ADAPTER = "./uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
DEFAULT_OUTPUT_DIR = "./uruha_rightbrain_plan_sft_lora_v18_semantic_dpo_v1"


def load_preference_rows(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Preference dataset must be a non-empty JSON list")
    seen_ids = set()
    output = []
    for row in rows:
        row_id = str(row.get("id") or "")
        source_case_id = str(row.get("source_case_id") or "")
        prompt_messages = row.get("prompt_messages")
        chosen = str(row.get("chosen") or "").strip()
        rejected = str(row.get("rejected") or "").strip()
        diagnostics = row.get("pair_diagnostics") or {}
        if not row_id or row_id in seen_ids:
            raise ValueError(f"Missing or duplicate preference row id: {row_id!r}")
        if not source_case_id or not isinstance(prompt_messages, list) or len(prompt_messages) != 2:
            raise ValueError(f"Invalid prompt/source for {row_id}")
        if not chosen or not rejected or chosen == rejected:
            raise ValueError(f"Invalid chosen/rejected pair for {row_id}")
        required_count = int(diagnostics.get("required_group_count", 0))
        rejected_hit_count = int(diagnostics.get("rejected_hit_count", 0))
        semantic_preference = required_count > 0 and rejected_hit_count < required_count
        failure_reasons = (
            diagnostics.get("rejected_surface_failure_reasons")
            or row.get("preference_failure_reasons")
            or []
        )
        strict_surface_preference = bool(failure_reasons) and all(
            [
                diagnostics.get("chosen_strict_quality_pass") is True,
                diagnostics.get("rejected_strict_quality_pass") is False,
            ]
        )
        if not semantic_preference and not strict_surface_preference:
            raise ValueError(
                f"Rejected completion is neither semantically weaker nor a validated surface failure for {row_id}"
            )
        seen_ids.add(row_id)
        output.append(row)
    return output


def split_by_source(rows, seed, eval_source_count=2):
    source_ids = sorted({row["source_case_id"] for row in rows})
    if len(source_ids) <= eval_source_count:
        raise ValueError("Not enough source families for a source-separated train/eval split")
    shuffled = list(source_ids)
    random.Random(seed).shuffle(shuffled)
    eval_sources = set(shuffled[:eval_source_count])
    train_rows = [row for row in rows if row["source_case_id"] not in eval_sources]
    eval_rows = [row for row in rows if row["source_case_id"] in eval_sources]
    return train_rows, eval_rows, sorted(set(source_ids) - eval_sources), sorted(eval_sources)


def _tokenize_completion(prompt_messages, completion, tokenizer, max_length):
    prompt = tokenizer.apply_chat_template(
        prompt_messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    answer = f"{completion}<|im_end|>"
    prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
    answer_ids = tokenizer(answer, add_special_tokens=False).input_ids
    input_ids = (prompt_ids + answer_ids)[:max_length]
    completion_mask = ([0] * len(prompt_ids) + [1] * len(answer_ids))[:max_length]
    if not any(completion_mask):
        raise ValueError("Completion was fully truncated")
    return {
        "input_ids": torch.tensor([input_ids], dtype=torch.long),
        "attention_mask": torch.ones((1, len(input_ids)), dtype=torch.long),
        "completion_mask": torch.tensor([completion_mask], dtype=torch.bool),
        "token_count": len(input_ids),
        "completion_token_count": sum(completion_mask),
    }


def tokenize_pair(row, tokenizer, max_length):
    return {
        "id": row["id"],
        "source_case_id": row["source_case_id"],
        "chosen": _tokenize_completion(
            row["prompt_messages"],
            row["chosen"],
            tokenizer,
            max_length,
        ),
        "rejected": _tokenize_completion(
            row["prompt_messages"],
            row["rejected"],
            tokenizer,
            max_length,
        ),
    }


def _move_sequence(sequence, device):
    return {
        key: value.to(device)
        for key, value in sequence.items()
        if key in {"input_ids", "attention_mask", "completion_mask"}
    }


def completion_log_prob(model, sequence, device):
    batch = _move_sequence(sequence, device)
    output = model(
        input_ids=batch["input_ids"],
        attention_mask=batch["attention_mask"],
    )
    shift_logits = output.logits[:, :-1, :]
    shift_labels = batch["input_ids"][:, 1:]
    shift_mask = batch["completion_mask"][:, 1:]
    token_log_probs = F.log_softmax(shift_logits.float(), dim=-1).gather(
        -1,
        shift_labels.unsqueeze(-1),
    ).squeeze(-1)
    return (token_log_probs * shift_mask).sum(dim=-1)


def dpo_loss(policy_chosen, policy_rejected, reference_chosen, reference_rejected, beta):
    policy_log_ratio = policy_chosen - policy_rejected
    reference_log_ratio = reference_chosen - reference_rejected
    reward_margin = beta * (policy_log_ratio - reference_log_ratio)
    return -F.logsigmoid(reward_margin).mean(), reward_margin


def precompute_reference(model, tokenized_rows, device):
    model.eval()
    reference = {}
    with torch.no_grad():
        for row in tokenized_rows:
            chosen = completion_log_prob(model, row["chosen"], device)
            rejected = completion_log_prob(model, row["rejected"], device)
            reference[row["id"]] = {
                "chosen": float(chosen.detach().cpu().item()),
                "rejected": float(rejected.detach().cpu().item()),
            }
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
    model.train()
    return reference


def evaluate_preferences(model, tokenized_rows, reference, device, beta):
    model.eval()
    rows = []
    with torch.no_grad():
        for row in tokenized_rows:
            chosen = completion_log_prob(model, row["chosen"], device)
            rejected = completion_log_prob(model, row["rejected"], device)
            ref = reference[row["id"]]
            _, reward_margin = dpo_loss(
                chosen,
                rejected,
                torch.tensor([ref["chosen"]], device=device),
                torch.tensor([ref["rejected"]], device=device),
                beta,
            )
            rows.append(
                {
                    "id": row["id"],
                    "source_case_id": row["source_case_id"],
                    "policy_log_ratio": float((chosen - rejected).detach().cpu().item()),
                    "reference_log_ratio": ref["chosen"] - ref["rejected"],
                    "reward_margin": float(reward_margin.detach().cpu().item()),
                }
            )
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
    model.train()
    return {
        "pair_count": len(rows),
        "policy_chosen_preference_rate": round(
            sum(row["policy_log_ratio"] > 0 for row in rows) / len(rows),
            6,
        ),
        "positive_reward_margin_rate": round(
            sum(row["reward_margin"] > 0 for row in rows) / len(rows),
            6,
        ),
        "mean_reward_margin": sum(row["reward_margin"] for row in rows) / len(rows),
        "rows": rows,
    }


def reference_preference_summary(tokenized_rows, reference):
    rows = []
    for row in tokenized_rows:
        ref = reference[row["id"]]
        ratio = ref["chosen"] - ref["rejected"]
        rows.append(
            {
                "id": row["id"],
                "source_case_id": row["source_case_id"],
                "policy_log_ratio": ratio,
                "reference_log_ratio": ratio,
                "reward_margin": 0.0,
            }
        )
    return {
        "pair_count": len(rows),
        "policy_chosen_preference_rate": round(
            sum(row["policy_log_ratio"] > 0 for row in rows) / len(rows),
            6,
        ),
        "positive_reward_margin_rate": 0.0,
        "mean_reward_margin": 0.0,
        "rows": rows,
    }


def train_dpo(model, train_rows, eval_rows, train_reference, eval_reference, args):
    device = next(model.parameters()).device
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
        eps=args.optimizer_eps,
    )
    # Before the first update the policy is exactly the reference adapter, so
    # another full forward pass would reproduce the cached values byte-for-byte.
    initial_train = reference_preference_summary(train_rows, train_reference)
    initial_eval = reference_preference_summary(eval_rows, eval_reference)
    target_steps = max(1, math.ceil(len(train_rows) * args.epochs))
    generator = random.Random(args.seed)
    order = list(range(len(train_rows)))
    consumed = updates = 0
    total_loss = 0.0
    nonfinite_skips = 0
    max_gradient_norm = 0.0
    optimizer.zero_grad(set_to_none=True)
    model.train()
    while consumed < target_steps:
        generator.shuffle(order)
        for index in order:
            if consumed >= target_steps:
                break
            row = train_rows[index]
            consumed += 1
            chosen = completion_log_prob(model, row["chosen"], device)
            rejected = completion_log_prob(model, row["rejected"], device)
            ref = train_reference[row["id"]]
            loss, _ = dpo_loss(
                chosen,
                rejected,
                torch.tensor([ref["chosen"]], device=device),
                torch.tensor([ref["rejected"]], device=device),
                args.beta,
            )
            if not torch.isfinite(loss):
                nonfinite_skips += 1
                optimizer.zero_grad(set_to_none=True)
                if nonfinite_skips > args.max_nonfinite_skips:
                    raise RuntimeError("Too many non-finite DPO losses")
                continue
            (loss / args.grad_accum).backward()
            total_loss += float(loss.detach().cpu())
            if consumed % args.grad_accum == 0 or consumed == target_steps:
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    [parameter for parameter in model.parameters() if parameter.requires_grad],
                    max_norm=0.3,
                )
                gradient_norm_value = float(gradient_norm.detach().float().cpu())
                if not math.isfinite(gradient_norm_value):
                    nonfinite_skips += 1
                    optimizer.zero_grad(set_to_none=True)
                    if nonfinite_skips > args.max_nonfinite_skips:
                        raise RuntimeError("Too many non-finite DPO gradients")
                    continue
                max_gradient_norm = max(max_gradient_norm, gradient_norm_value)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                updates += 1
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
                print(
                    f"update={updates} pair_step={consumed}/{target_steps} "
                    f"avg_dpo_loss={total_loss / consumed:.4f}"
                )
    final_train = evaluate_preferences(model, train_rows, train_reference, device, args.beta)
    final_eval = evaluate_preferences(model, eval_rows, eval_reference, device, args.beta)
    return {
        "target_pair_steps": target_steps,
        "consumed_pair_steps": consumed,
        "optimizer_updates": updates,
        "nonfinite_skips": nonfinite_skips,
        "max_observed_gradient_norm": max_gradient_norm,
        "mean_train_dpo_loss": total_loss / max(consumed, 1),
        "initial_train_preference": initial_train,
        "initial_eval_preference": initial_eval,
        "final_train_preference": final_train,
        "final_eval_preference": final_eval,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DATASET_PATH)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--init-adapter", default=DEFAULT_INIT_ADAPTER)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-report", default=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--max-length", type=int, default=720)
    parser.add_argument("--eval-source-count", type=int, default=2)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=1e-7)
    parser.add_argument("--beta", type=float, default=0.1)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--weight-decay", type=float, default=0.02)
    parser.add_argument("--optimizer-eps", type=float, default=1e-6)
    parser.add_argument("--max-nonfinite-skips", type=int, default=4)
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16", "float32"], default="auto")
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(args.seed)
    rows = load_preference_rows(args.dataset)
    train_rows, eval_rows, train_sources, eval_sources = split_by_source(
        rows,
        args.seed,
        args.eval_source_count,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    tokenized_train = [tokenize_pair(row, tokenizer, args.max_length) for row in train_rows]
    tokenized_eval = [tokenize_pair(row, tokenizer, args.max_length) for row in eval_rows]
    token_counts = [
        sequence["token_count"]
        for row in tokenized_train + tokenized_eval
        for sequence in (row["chosen"], row["rejected"])
    ]
    chosen_completion_counts = [row["chosen"]["completion_token_count"] for row in tokenized_train + tokenized_eval]
    rejected_completion_counts = [
        row["rejected"]["completion_token_count"] for row in tokenized_train + tokenized_eval
    ]
    dry_summary = {
        "pair_count": len(rows),
        "train_pair_count": len(train_rows),
        "eval_pair_count": len(eval_rows),
        "train_source_ids": train_sources,
        "eval_source_ids": eval_sources,
        "source_overlap_count": len(set(train_sources) & set(eval_sources)),
        "token_length_min": min(token_counts),
        "token_length_max": max(token_counts),
        "token_length_mean": round(sum(token_counts) / len(token_counts), 2),
        "chosen_completion_token_mean": round(
            sum(chosen_completion_counts) / len(chosen_completion_counts),
            3,
        ),
        "rejected_completion_token_mean": round(
            sum(rejected_completion_counts) / len(rejected_completion_counts),
            3,
        ),
    }
    if args.dry_run:
        print(json.dumps(dry_summary, ensure_ascii=False, indent=2))
        return 0

    started = time.time()
    model = build_model(
        args.base_model,
        args.init_adapter,
        lora_r=32,
        lora_alpha=24,
        lora_dropout=0.08,
        dtype_name=args.dtype,
    )
    model.print_trainable_parameters()
    device = next(model.parameters()).device
    print("precomputing V10 reference log probabilities")
    train_reference = precompute_reference(model, tokenized_train, device)
    eval_reference = precompute_reference(model, tokenized_eval, device)
    metrics = train_dpo(
        model,
        tokenized_train,
        tokenized_eval,
        train_reference,
        eval_reference,
        args,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    adapter_report = init_adapter_report(args.init_adapter)
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "method": "offline_direct_preference_optimization",
        "method_reference": "https://arxiv.org/abs/2305.18290",
        "base_model": args.base_model,
        "dataset_ref": Path(args.dataset).name,
        "dataset_sha256": _sha256(args.dataset),
        **adapter_report,
        "output_adapter_ref": output_dir.name,
        "output_adapter_config_sha256": _sha256(output_dir / "adapter_config.json"),
        "output_adapter_model_sha256": _sha256(output_dir / "adapter_model.safetensors"),
        **dry_summary,
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "beta": args.beta,
        "grad_accum": args.grad_accum,
        "seed": args.seed,
        "dtype": str(
            resolve_model_dtype(
                args.dtype,
                torch.cuda.is_available(),
                torch.backends.mps.is_available(),
            )
        ),
        "duration_seconds": round(time.time() - started, 3),
        **metrics,
        "research_boundary": (
            "The preference pairs are synthetic and source-family separated. Promotion requires unseen actual-model "
            "multi-seed holdout evidence; DPO training metrics alone cannot promote this adapter."
        ),
    }
    (output_dir / "rightbrain_dpo_v18_training_run.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.run_report).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
