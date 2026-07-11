#!/usr/bin/env python3
"""Train V10 with length-normalized, reference-free SimPO preference loss."""

import argparse
import json
import math
import random
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer

from project_paths import (
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DATASET_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_TRAINING_RUN_REPORT_PATH,
)
from train_uruha_rightbrain_contract_v1 import (
    DEFAULT_BASE_MODEL,
    _sha256,
    build_model,
    init_adapter_report,
    resolve_model_dtype,
)
from train_uruha_rightbrain_dpo_v18 import (
    load_preference_rows,
    split_by_source,
    tokenize_pair,
)


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_INIT_ADAPTER = "./uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
DEFAULT_OUTPUT_DIR = "./uruha_rightbrain_plan_sft_lora_v19_semantic_simpo_v1"


def _move_sequence(sequence, device):
    return {
        key: value.to(device)
        for key, value in sequence.items()
        if key in {"input_ids", "attention_mask", "completion_mask"}
    }


def completion_average_log_prob(model, sequence, device):
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
    token_count = shift_mask.sum(dim=-1).clamp_min(1)
    return (token_log_probs * shift_mask).sum(dim=-1) / token_count


def simpo_loss(chosen_average, rejected_average, beta, gamma):
    raw_margin = chosen_average - rejected_average
    target_margin = beta * raw_margin - gamma
    return -F.logsigmoid(target_margin).mean(), raw_margin, target_margin


def add_chosen_nll(preference_loss, chosen_average, chosen_nll_weight):
    chosen_nll = -chosen_average.mean()
    return preference_loss + chosen_nll_weight * chosen_nll, chosen_nll


def evaluate_simpo(model, rows, device, beta, gamma):
    model.eval()
    output_rows = []
    with torch.no_grad():
        for row in rows:
            chosen = completion_average_log_prob(model, row["chosen"], device)
            rejected = completion_average_log_prob(model, row["rejected"], device)
            loss, raw_margin, target_margin = simpo_loss(
                chosen,
                rejected,
                beta,
                gamma,
            )
            output_rows.append(
                {
                    "id": row["id"],
                    "source_case_id": row["source_case_id"],
                    "source_prompt_id": row.get("source_prompt_id") or row["source_case_id"],
                    "chosen_average_log_prob": float(chosen.detach().cpu().item()),
                    "rejected_average_log_prob": float(rejected.detach().cpu().item()),
                    "raw_preference_margin": float(raw_margin.detach().cpu().item()),
                    "target_reward_margin": float(target_margin.detach().cpu().item()),
                    "loss": float(loss.detach().cpu().item()),
                }
            )
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
    model.train()
    return {
        "pair_count": len(output_rows),
        "chosen_preference_rate": round(
            sum(row["raw_preference_margin"] > 0 for row in output_rows) / len(output_rows),
            6,
        ),
        "target_margin_rate": round(
            sum(row["target_reward_margin"] > 0 for row in output_rows) / len(output_rows),
            6,
        ),
        "mean_raw_preference_margin": sum(
            row["raw_preference_margin"] for row in output_rows
        )
        / len(output_rows),
        "mean_target_reward_margin": sum(
            row["target_reward_margin"] for row in output_rows
        )
        / len(output_rows),
        "mean_loss": sum(row["loss"] for row in output_rows) / len(output_rows),
        "rows": output_rows,
    }


def disable_dropout(model):
    count = 0
    for module in model.modules():
        if isinstance(module, torch.nn.Dropout) and module.p != 0:
            module.p = 0.0
            count += 1
    return count


def assign_prompt_balance_weights(rows, enabled=False):
    if not rows:
        raise ValueError("Prompt balancing requires at least one training pair")
    pair_counts = Counter(
        row.get("source_prompt_id") or row["source_case_id"] for row in rows
    )
    prompt_count = len(pair_counts)
    pair_count = len(rows)
    target_prompt_weight = pair_count / prompt_count
    for row in rows:
        prompt_id = row.get("source_prompt_id") or row["source_case_id"]
        row["sample_weight"] = (
            target_prompt_weight / pair_counts[prompt_id] if enabled else 1.0
        )
    prompt_weight_totals = {
        prompt_id: sum(
            row["sample_weight"]
            for row in rows
            if (row.get("source_prompt_id") or row["source_case_id"]) == prompt_id
        )
        for prompt_id in pair_counts
    }
    weights = [row["sample_weight"] for row in rows]
    return {
        "enabled": bool(enabled),
        "pair_count": pair_count,
        "prompt_count": prompt_count,
        "pair_counts_by_prompt": dict(sorted(pair_counts.items())),
        "pre_balance_prompt_contribution_ratio": (
            max(pair_counts.values()) / min(pair_counts.values())
        ),
        "target_total_weight_per_prompt": target_prompt_weight,
        "sample_weight_min": min(weights),
        "sample_weight_max": max(weights),
        "sample_weight_mean": sum(weights) / pair_count,
        "prompt_weight_totals": dict(sorted(prompt_weight_totals.items())),
        "post_balance_prompt_weight_spread": (
            max(prompt_weight_totals.values()) - min(prompt_weight_totals.values())
        ),
    }


def research_boundary(prompt_balance, chosen_nll_weight):
    qualifications = []
    if prompt_balance:
        qualifications.append(
            "Prompt balancing is a local inverse-multiplicity weighting ablation motivated by "
            "multi-preference research; it is not a reproduction of AMPO or GroupDPO."
        )
    if chosen_nll_weight > 0:
        qualifications.append(
            "Chosen NLL follows the optional SFT regularization form in the official SimPO "
            "implementation and the stability motivation reported by GroupDPO; it is not a full "
            "GroupDPO reproduction."
        )
    if not qualifications:
        qualifications.append(
            "SimPO metrics use two unseen source families but automatic contract preference labels."
        )
    qualifications.append(
        "Promotion still requires source-separated preference gates and matched-seed actual-model "
        "holdouts against V10."
    )
    return " ".join(qualifications)


def train_simpo(model, train_rows, eval_rows, args):
    device = next(model.parameters()).device
    gamma = args.beta * args.gamma_beta_ratio
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
        eps=args.optimizer_eps,
    )
    initial_eval = evaluate_simpo(model, eval_rows, device, args.beta, gamma)
    target_steps = max(1, math.ceil(len(train_rows) * args.epochs))
    generator = random.Random(args.seed)
    order = list(range(len(train_rows)))
    consumed = updates = nonfinite_skips = 0
    total_loss = total_chosen_nll = total_composite_loss = 0.0
    total_weighted_preference_loss = total_weighted_objective_loss = 0.0
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
            chosen = completion_average_log_prob(model, row["chosen"], device)
            rejected = completion_average_log_prob(model, row["rejected"], device)
            loss, _, _ = simpo_loss(chosen, rejected, args.beta, gamma)
            composite_loss, chosen_nll = add_chosen_nll(
                loss,
                chosen,
                args.chosen_nll_weight,
            )
            sample_weight = float(row.get("sample_weight", 1.0))
            weighted_loss = composite_loss * sample_weight
            if not torch.isfinite(weighted_loss):
                nonfinite_skips += 1
                optimizer.zero_grad(set_to_none=True)
                if nonfinite_skips > args.max_nonfinite_skips:
                    raise RuntimeError("Too many non-finite SimPO losses")
                continue
            (weighted_loss / args.grad_accum).backward()
            total_loss += float(loss.detach().cpu())
            total_chosen_nll += float(chosen_nll.detach().cpu())
            total_composite_loss += float(composite_loss.detach().cpu())
            total_weighted_preference_loss += float((loss * sample_weight).detach().cpu())
            total_weighted_objective_loss += float(weighted_loss.detach().cpu())
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
                        raise RuntimeError("Too many non-finite SimPO gradients")
                    continue
                max_gradient_norm = max(max_gradient_norm, gradient_norm_value)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                updates += 1
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
                print(
                    f"update={updates} pair_step={consumed}/{target_steps} "
                    f"avg_simpo_loss={total_loss / consumed:.4f} "
                    f"avg_chosen_nll={total_chosen_nll / consumed:.4f} "
                    f"avg_weighted_objective={total_weighted_objective_loss / consumed:.4f}"
                )
    final_train = evaluate_simpo(model, train_rows, device, args.beta, gamma)
    final_eval = evaluate_simpo(model, eval_rows, device, args.beta, gamma)
    return {
        "target_pair_steps": target_steps,
        "consumed_pair_steps": consumed,
        "optimizer_updates": updates,
        "nonfinite_skips": nonfinite_skips,
        "max_observed_gradient_norm": max_gradient_norm,
        "mean_train_simpo_loss": total_loss / max(consumed, 1),
        "mean_train_chosen_nll": total_chosen_nll / max(consumed, 1),
        "mean_train_composite_loss": total_composite_loss / max(consumed, 1),
        "mean_train_weighted_simpo_loss": total_weighted_preference_loss / max(consumed, 1),
        "mean_train_weighted_objective_loss": total_weighted_objective_loss / max(consumed, 1),
        "initial_eval_preference": initial_eval,
        "final_train_preference": final_train,
        "final_eval_preference": final_eval,
    }


def main(
    default_dataset=RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DATASET_PATH,
    default_output_dir=DEFAULT_OUTPUT_DIR,
    default_run_report=RIGHTBRAIN_SEMANTIC_PREFERENCE_V19_TRAINING_RUN_REPORT_PATH,
    force_prompt_balance=False,
    force_chosen_nll_weight=0.0,
):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=default_dataset)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--init-adapter", default=DEFAULT_INIT_ADAPTER)
    parser.add_argument("--output-dir", default=default_output_dir)
    parser.add_argument("--run-report", default=default_run_report)
    parser.add_argument("--max-length", type=int, default=720)
    parser.add_argument("--eval-source-count", type=int, default=2)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=3e-7)
    parser.add_argument("--beta", type=float, default=2.5)
    parser.add_argument("--gamma-beta-ratio", type=float, default=0.1)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--weight-decay", type=float, default=0.02)
    parser.add_argument("--optimizer-eps", type=float, default=1e-6)
    parser.add_argument("--max-nonfinite-skips", type=int, default=4)
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16", "float32"], default="auto")
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--prompt-balance", action="store_true", default=force_prompt_balance)
    parser.add_argument("--chosen-nll-weight", type=float, default=force_chosen_nll_weight)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.chosen_nll_weight < 0:
        raise ValueError("chosen_nll_weight must be non-negative")

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
    prompt_balance = assign_prompt_balance_weights(
        tokenized_train,
        enabled=args.prompt_balance,
    )
    dry_summary = {
        "pair_count": len(rows),
        "train_pair_count": len(train_rows),
        "eval_pair_count": len(eval_rows),
        "train_source_ids": train_sources,
        "eval_source_ids": eval_sources,
        "source_overlap_count": len(set(train_sources) & set(eval_sources)),
        "prompt_balance": prompt_balance,
        "chosen_nll_weight": args.chosen_nll_weight,
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
    disabled_dropout_count = disable_dropout(model)
    model.print_trainable_parameters()
    metrics = train_simpo(model, tokenized_train, tokenized_eval, args)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    adapter_report = init_adapter_report(args.init_adapter)
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "method": (
            "length_normalized_reference_free_simpo"
            + ("_prompt_balanced" if args.prompt_balance else "")
            + ("_chosen_nll" if args.chosen_nll_weight > 0 else "")
        ),
        "method_reference": "https://arxiv.org/abs/2405.14734",
        "grouping_references": [
            "https://proceedings.mlr.press/v267/gupta25c.html",
            "https://arxiv.org/abs/2604.15602",
        ],
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
        "gamma_beta_ratio": args.gamma_beta_ratio,
        "gamma": args.beta * args.gamma_beta_ratio,
        "grad_accum": args.grad_accum,
        "disabled_dropout_module_count": disabled_dropout_count,
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
        "research_boundary": research_boundary(
            args.prompt_balance,
            args.chosen_nll_weight,
        ),
    }
    (output_dir / "rightbrain_simpo_v19_training_run.json").write_text(
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
