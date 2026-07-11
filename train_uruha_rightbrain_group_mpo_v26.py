#!/usr/bin/env python3
"""Train V10 with a memory-efficient group MPO objective and positive NLL."""

import argparse
import json
import math
import os
import random
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import torch
from transformers import AutoTokenizer

from probe_rightbrain_group_preference_v26 import (
    load_groups,
    tokenize_group,
)
from project_paths import (
    RIGHTBRAIN_GROUP_MPO_V26_TRAINING_RUN_REPORT_PATH,
    RIGHTBRAIN_GROUP_PREFERENCE_V26_DATASET_PATH,
    RIGHTBRAIN_GROUP_PREFERENCE_V26_PROBE_JSON_PATH,
)
from train_uruha_rightbrain_contract_v1 import (
    DEFAULT_BASE_MODEL,
    _sha256,
    build_model,
    init_adapter_report,
    resolve_model_dtype,
)
from train_uruha_rightbrain_dpo_v18 import split_by_source
from train_uruha_rightbrain_simpo_v19 import (
    completion_average_log_prob,
    disable_dropout,
)


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_INIT_ADAPTER = "./uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
DEFAULT_OUTPUT_DIR = "./uruha_rightbrain_plan_sft_lora_v26_group_mpo_v1"


def mpo_loss(scores, positive_mask):
    if scores.ndim != 1 or positive_mask.shape != scores.shape:
        raise ValueError("MPO scores and positive mask must be aligned one-dimensional tensors")
    if not bool(positive_mask.any()) or bool(positive_mask.all()):
        raise ValueError("MPO requires at least one positive and one negative response")
    return torch.logsumexp(scores, dim=0) - torch.logsumexp(
        scores[positive_mask],
        dim=0,
    )


def mpo_coefficients(scores, positive_mask):
    detached = scores.detach()
    probabilities = torch.softmax(detached, dim=0)
    positive_mass = probabilities[positive_mask].sum()
    coefficients = probabilities.clone()
    coefficients[positive_mask] -= probabilities[positive_mask] / positive_mass
    return coefficients


def _probe_reference_map(probe_report):
    output = {}
    for metric_key in (
        "initial_train_absolute_group_metrics",
        "initial_eval_absolute_group_metrics",
    ):
        for group in probe_report[metric_key]["groups"]:
            output[group["id"]] = {
                response["id"]: response["average_log_prob"]
                for response in group["responses"]
            }
    return output


def validate_probe(dataset_path, probe_path, init_adapter=DEFAULT_INIT_ADAPTER):
    probe = json.loads(Path(probe_path).read_text(encoding="utf-8"))
    if not probe.get("decision", {}).get("authorize_group_training"):
        raise ValueError("V26 group pre-training probe did not authorize training")
    if probe.get("dataset_sha256") != _sha256(dataset_path):
        raise ValueError("V26 group dataset changed after the frozen-reference probe")
    actual_adapter = os.path.basename(os.path.abspath(init_adapter))
    if probe.get("init_adapter_ref") != actual_adapter:
        raise ValueError(
            f"Training adapter does not match frozen reference: {actual_adapter} != {probe.get('init_adapter_ref')}"
        )
    actual_model_sha256 = _sha256(Path(init_adapter) / "adapter_model.safetensors")
    if probe.get("init_adapter_model_sha256") != actual_model_sha256:
        raise ValueError("V10 adapter weights changed after the frozen-reference probe")
    return probe


def validate_probe_split(
    probe,
    *,
    base_model,
    max_length,
    seed,
    train_sources,
    eval_sources,
):
    expected = {
        "base_model": probe.get("base_model"),
        "max_length": probe.get("max_length"),
        "seed": probe.get("seed"),
        "train_sources": probe.get("train_source_ids"),
        "eval_sources": probe.get("eval_source_ids"),
    }
    actual = {
        "base_model": base_model,
        "max_length": max_length,
        "seed": seed,
        "train_sources": train_sources,
        "eval_sources": eval_sources,
    }
    if actual != expected:
        raise ValueError(
            "Training configuration or source split differs from frozen-reference probe: "
            f"actual={actual}, expected={expected}"
        )


def attach_reference_scores(groups, probe_report):
    references = _probe_reference_map(probe_report)
    attached = 0
    for group in groups:
        group_reference = references.get(group["id"])
        if group_reference is None:
            raise ValueError(f"Probe lacks reference group: {group['id']}")
        for response in group["responses"]:
            if response["id"] not in group_reference:
                raise ValueError(f"Probe lacks response reference: {response['id']}")
            response["reference_average_log_prob"] = float(
                group_reference[response["id"]]
            )
            attached += 1
    if attached != sum(len(group["responses"]) for group in groups):
        raise ValueError("Not every group response received a frozen reference score")
    return attached


def _policy_group_scores(model, group, device):
    values = []
    with torch.no_grad():
        for response in group["responses"]:
            value = float(
                completion_average_log_prob(
                    model,
                    response["sequence"],
                    device,
                )
                .detach()
                .cpu()
                .item()
            )
            values.append(value)
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
    return values


def evaluate_group_mpo(model, groups, device, beta):
    model.eval()
    output_groups = []
    all_positive_policy = []
    all_negative_policy = []
    pair_count = correct_pairs = tie_pairs = 0
    positive_mass_total = mean_margin_total = 0.0
    strict_count = top_count = 0
    max_reference_delta = 0.0
    for group in groups:
        policy_values = _policy_group_scores(model, group, device)
        reference_values = [
            response["reference_average_log_prob"] for response in group["responses"]
        ]
        implicit = torch.tensor(
            [
                beta * (policy - reference)
                for policy, reference in zip(policy_values, reference_values)
            ],
            dtype=torch.float64,
        )
        positive_mask = torch.tensor(
            [response["label"] == "positive" for response in group["responses"]],
            dtype=torch.bool,
        )
        probability = torch.softmax(implicit, dim=0)
        positive_mass = float(probability[positive_mask].sum())
        positive_scores = implicit[positive_mask].tolist()
        negative_scores = implicit[~positive_mask].tolist()
        positive_policy = [
            value
            for value, is_positive in zip(policy_values, positive_mask.tolist())
            if is_positive
        ]
        negative_policy = [
            value
            for value, is_positive in zip(policy_values, positive_mask.tolist())
            if not is_positive
        ]
        group_pair_count = len(positive_scores) * len(negative_scores)
        group_correct = sum(p > n for p in positive_scores for n in negative_scores)
        group_ties = sum(p == n for p in positive_scores for n in negative_scores)
        strict = min(positive_scores) > max(negative_scores)
        top = max(positive_scores) > max(negative_scores)
        mean_margin = (
            sum(positive_scores) / len(positive_scores)
            - sum(negative_scores) / len(negative_scores)
        )
        pair_count += group_pair_count
        correct_pairs += group_correct
        tie_pairs += group_ties
        strict_count += int(strict)
        top_count += int(top)
        positive_mass_total += positive_mass
        mean_margin_total += mean_margin
        all_positive_policy.extend(positive_policy)
        all_negative_policy.extend(negative_policy)
        max_reference_delta = max(
            max_reference_delta,
            max(
                abs(policy - reference)
                for policy, reference in zip(policy_values, reference_values)
            ),
        )
        output_groups.append(
            {
                "id": group["id"],
                "source_case_id": group["source_case_id"],
                "source_prompt_id": group["source_prompt_id"],
                "positive_count": int(positive_mask.sum()),
                "negative_count": int((~positive_mask).sum()),
                "mpo_loss": float(mpo_loss(implicit, positive_mask)),
                "positive_probability_mass": positive_mass,
                "pair_count": group_pair_count,
                "pairwise_positive_preference_rate": group_correct / group_pair_count,
                "strict_positive_separation": strict,
                "positive_top1": top,
                "mean_positive_negative_margin": mean_margin,
                "responses": [
                    {
                        "id": response["id"],
                        "label": response["label"],
                        "policy_average_log_prob": policy,
                        "reference_average_log_prob": reference,
                        "implicit_preference_score": score,
                    }
                    for response, policy, reference, score in zip(
                        group["responses"],
                        policy_values,
                        reference_values,
                        implicit.tolist(),
                    )
                ],
            }
        )
    group_count = len(groups)
    return {
        "group_count": group_count,
        "candidate_count": len(all_positive_policy) + len(all_negative_policy),
        "positive_candidate_count": len(all_positive_policy),
        "negative_candidate_count": len(all_negative_policy),
        "pair_count": pair_count,
        "pairwise_positive_preference_rate": correct_pairs / pair_count,
        "pairwise_tie_rate": tie_pairs / pair_count,
        "strict_positive_separation_rate": strict_count / group_count,
        "positive_top1_rate": top_count / group_count,
        "mean_positive_probability_mass": positive_mass_total / group_count,
        "mean_positive_negative_margin": mean_margin_total / group_count,
        "mean_positive_policy_average_log_prob": sum(all_positive_policy)
        / len(all_positive_policy),
        "mean_negative_policy_average_log_prob": sum(all_negative_policy)
        / len(all_negative_policy),
        "max_abs_policy_reference_log_prob_delta": max_reference_delta,
        "groups": output_groups,
    }


def train_group_mpo(model, train_groups, eval_groups, args):
    device = next(model.parameters()).device
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
        eps=args.optimizer_eps,
    )
    initial_train = evaluate_group_mpo(model, train_groups, device, args.beta)
    initial_eval = evaluate_group_mpo(model, eval_groups, device, args.beta)
    target_steps = max(1, math.ceil(len(train_groups) * args.epochs))
    order = list(range(len(train_groups)))
    generator = random.Random(args.seed)
    consumed = updates = nonfinite_skips = 0
    max_gradient_norm = total_mpo_loss = total_positive_nll = 0.0
    model.train()
    while consumed < target_steps:
        generator.shuffle(order)
        for index in order:
            if consumed >= target_steps:
                break
            group = train_groups[index]
            consumed += 1
            policy_values = _policy_group_scores(model, group, device)
            references = [
                response["reference_average_log_prob"]
                for response in group["responses"]
            ]
            implicit = torch.tensor(
                [
                    args.beta * (policy - reference)
                    for policy, reference in zip(policy_values, references)
                ],
                dtype=torch.float64,
            )
            positive_mask = torch.tensor(
                [response["label"] == "positive" for response in group["responses"]],
                dtype=torch.bool,
            )
            coefficients = mpo_coefficients(implicit, positive_mask)
            direct_mpo = float(mpo_loss(implicit, positive_mask))
            positive_count = int(positive_mask.sum())
            direct_positive_nll = -sum(
                value
                for value, is_positive in zip(policy_values, positive_mask.tolist())
                if is_positive
            ) / positive_count
            optimizer.zero_grad(set_to_none=True)
            group_finite = True
            for response, reference, coefficient in zip(
                group["responses"],
                references,
                coefficients.tolist(),
            ):
                policy = completion_average_log_prob(
                    model,
                    response["sequence"],
                    device,
                )
                sample_loss = coefficient * args.beta * (policy - reference)
                if response["label"] == "positive":
                    sample_loss = sample_loss - (
                        args.positive_nll_weight / positive_count
                    ) * policy
                if not torch.isfinite(sample_loss):
                    group_finite = False
                    break
                sample_loss.backward()
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
            if not group_finite:
                nonfinite_skips += 1
                optimizer.zero_grad(set_to_none=True)
                if nonfinite_skips > args.max_nonfinite_skips:
                    raise RuntimeError("Too many non-finite group MPO losses")
                continue
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                [parameter for parameter in model.parameters() if parameter.requires_grad],
                max_norm=args.max_gradient_norm,
            )
            gradient_norm_value = float(gradient_norm.detach().float().cpu())
            if not math.isfinite(gradient_norm_value):
                nonfinite_skips += 1
                optimizer.zero_grad(set_to_none=True)
                if nonfinite_skips > args.max_nonfinite_skips:
                    raise RuntimeError("Too many non-finite group MPO gradients")
                continue
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            updates += 1
            total_mpo_loss += direct_mpo
            total_positive_nll += direct_positive_nll
            max_gradient_norm = max(max_gradient_norm, gradient_norm_value)
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            print(
                f"update={updates} group_step={consumed}/{target_steps} "
                f"mpo_loss={direct_mpo:.4f} positive_nll={direct_positive_nll:.4f}"
            )
    final_train = evaluate_group_mpo(model, train_groups, device, args.beta)
    final_eval = evaluate_group_mpo(model, eval_groups, device, args.beta)
    return {
        "target_group_steps": target_steps,
        "consumed_group_steps": consumed,
        "optimizer_updates": updates,
        "nonfinite_skips": nonfinite_skips,
        "max_observed_gradient_norm": max_gradient_norm,
        "mean_train_mpo_loss": total_mpo_loss / max(updates, 1),
        "mean_train_positive_nll": total_positive_nll / max(updates, 1),
        "initial_train_group_metrics": initial_train,
        "initial_eval_group_metrics": initial_eval,
        "final_train_group_metrics": final_train,
        "final_eval_group_metrics": final_eval,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_GROUP_PREFERENCE_V26_DATASET_PATH)
    parser.add_argument("--probe", default=RIGHTBRAIN_GROUP_PREFERENCE_V26_PROBE_JSON_PATH)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--init-adapter", default=DEFAULT_INIT_ADAPTER)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-report", default=RIGHTBRAIN_GROUP_MPO_V26_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--max-length", type=int, default=720)
    parser.add_argument("--eval-source-count", type=int, default=2)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=1e-7)
    parser.add_argument("--beta", type=float, default=2.0)
    parser.add_argument("--positive-nll-weight", type=float, default=1.0)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--optimizer-eps", type=float, default=1e-6)
    parser.add_argument("--max-gradient-norm", type=float, default=0.3)
    parser.add_argument("--max-nonfinite-skips", type=int, default=4)
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16", "float32"], default="auto")
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.epochs <= 0 or args.positive_nll_weight < 0:
        raise ValueError("epochs must be positive and positive_nll_weight non-negative")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(args.seed)
    probe = validate_probe(args.dataset, args.probe, args.init_adapter)
    groups = load_groups(args.dataset)
    train_groups, eval_groups, train_sources, eval_sources = split_by_source(
        groups,
        args.seed,
        args.eval_source_count,
    )
    validate_probe_split(
        probe,
        base_model=args.base_model,
        max_length=args.max_length,
        seed=args.seed,
        train_sources=train_sources,
        eval_sources=eval_sources,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    tokenized_train = [tokenize_group(group, tokenizer, args.max_length) for group in train_groups]
    tokenized_eval = [tokenize_group(group, tokenizer, args.max_length) for group in eval_groups]
    attached_count = attach_reference_scores(
        [*tokenized_train, *tokenized_eval],
        probe,
    )
    dry_summary = {
        "group_count": len(groups),
        "train_group_count": len(train_groups),
        "eval_group_count": len(eval_groups),
        "candidate_count": attached_count,
        "train_source_ids": train_sources,
        "eval_source_ids": eval_sources,
        "source_overlap_count": len(set(train_sources) & set(eval_sources)),
        "positive_nll_weight": args.positive_nll_weight,
        "frozen_v10_absolute_eval_pairwise_preference_rate": probe[
            "initial_eval_absolute_group_metrics"
        ]["pairwise_positive_preference_rate"],
        "frozen_v10_absolute_eval_misranked_pair_count": probe["decision"][
            "eval_misranked_pair_count"
        ],
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
    metrics = train_group_mpo(model, tokenized_train, tokenized_eval, args)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_group_mpo_v26_training",
        "method": "reference_based_group_mpo_first_order_surrogate_with_positive_nll",
        "method_references": [
            "https://arxiv.org/abs/2604.15602",
            "https://proceedings.mlr.press/v267/gupta25c.html",
        ],
        "base_model": args.base_model,
        "dataset_ref": Path(args.dataset).name,
        "dataset_sha256": _sha256(args.dataset),
        "probe_ref": Path(args.probe).name,
        "probe_sha256": _sha256(args.probe),
        **init_adapter_report(args.init_adapter),
        "init_adapter_model_sha256": _sha256(
            Path(args.init_adapter) / "adapter_model.safetensors"
        ),
        "output_adapter_ref": output_dir.name,
        "output_adapter_config_sha256": _sha256(output_dir / "adapter_config.json"),
        "output_adapter_model_sha256": _sha256(output_dir / "adapter_model.safetensors"),
        **dry_summary,
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "beta": args.beta,
        "positive_nll_weight": args.positive_nll_weight,
        "weight_decay": args.weight_decay,
        "optimizer_eps": args.optimizer_eps,
        "max_gradient_norm": args.max_gradient_norm,
        "seed": args.seed,
        "max_length": args.max_length,
        "dtype": str(
            resolve_model_dtype(
                args.dtype,
                torch.cuda.is_available(),
                torch.backends.mps.is_available(),
            )
        ),
        "disabled_dropout_module_count": disabled_dropout_count,
        "duration_seconds": round(time.time() - started, 3),
        **metrics,
        "research_boundary": (
            "This implements the reference-based MPO group loss and first-order surrogate described by GroupDPO, "
            "using local groups of 4-6 V10 responses and automatic strict-contract labels. It is not a full-paper "
            "reproduction and cannot establish broad human preference without actual-generation holdout evidence."
        ),
    }
    (output_dir / "rightbrain_group_mpo_v26_training_run.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.run_report).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "optimizer_updates": metrics["optimizer_updates"],
                "nonfinite_skips": metrics["nonfinite_skips"],
                "initial_eval_pairwise_preference": metrics[
                    "initial_eval_group_metrics"
                ]["pairwise_positive_preference_rate"],
                "final_eval_pairwise_preference": metrics["final_eval_group_metrics"][
                    "pairwise_positive_preference_rate"
                ],
                "final_eval_strict_separation": metrics["final_eval_group_metrics"][
                    "strict_positive_separation_rate"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
