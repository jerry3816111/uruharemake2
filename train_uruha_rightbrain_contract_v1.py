#!/usr/bin/env python3
"""Train a LoRA on the exact canonical RightBrain runtime-v1 message contract."""

import argparse
import hashlib
import json
import math
import os
import random
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import torch
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq,
)

from project_paths import (
    RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH,
    RIGHTBRAIN_CONTRACT_V1_TRAINING_RUN_REPORT_PATH,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_OUTPUT_DIR = "./uruha_rightbrain_plan_sft_lora_v8_contract_v1_from_v5"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rows(path, min_rows=500):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    for item in raw:
        messages = item.get("messages") if isinstance(item, dict) else None
        if not messages or len(messages) != 3 or messages[-1].get("role") != "assistant":
            continue
        try:
            payload = json.loads(str(messages[1].get("content") or "{}"))
        except json.JSONDecodeError:
            continue
        if payload.get("contract_version") != RIGHT_BRAIN_MODEL_CONTRACT_VERSION:
            continue
        rows.append(item)
    if len(rows) < min_rows:
        raise RuntimeError(f"Too few canonical training rows: {len(rows)}")
    return rows


def load_training_rows(dataset_path, supplemental_paths=None):
    rows = load_rows(dataset_path, min_rows=500)
    sources = [
        {
            "role": "primary",
            "path": str(dataset_path),
            "rows": len(rows),
            "sha256": _sha256(dataset_path),
        }
    ]
    for supplemental_path in supplemental_paths or []:
        supplemental_rows = load_rows(supplemental_path, min_rows=1)
        rows.extend(supplemental_rows)
        sources.append(
            {
                "role": "supplemental",
                "path": str(supplemental_path),
                "rows": len(supplemental_rows),
                "sha256": _sha256(supplemental_path),
            }
        )
    return rows, sources


def tokenize_row(row, tokenizer, max_length):
    prompt = tokenizer.apply_chat_template(row["messages"][:-1], tokenize=False, add_generation_prompt=True)
    answer = f"{str(row['messages'][-1]['content']).strip()}<|im_end|>"
    prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
    answer_ids = tokenizer(answer, add_special_tokens=False).input_ids
    input_ids = (prompt_ids + answer_ids)[:max_length]
    labels = ([-100] * len(prompt_ids) + answer_ids)[:max_length]
    if all(label == -100 for label in labels):
        raise ValueError(f"Answer was truncated from row {row.get('id')}")
    return {
        "input_ids": input_ids,
        "attention_mask": [1] * len(input_ids),
        "labels": labels,
    }


class CanonicalContractDataset(Dataset):
    def __init__(self, rows, tokenizer, max_length):
        self.items = [tokenize_row(row, tokenizer, max_length) for row in rows]

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]


def resolve_model_dtype(dtype_name, use_cuda, use_mps):
    if dtype_name == "float32":
        return torch.float32
    if dtype_name == "float16":
        return torch.float16
    if dtype_name == "bfloat16":
        return torch.bfloat16
    if use_cuda:
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    if use_mps:
        return torch.bfloat16
    return torch.float32


def build_model(base_model, init_adapter, lora_r, lora_alpha, lora_dropout, dtype_name="auto"):
    use_cuda = torch.cuda.is_available()
    use_mps = torch.backends.mps.is_available()
    dtype = resolve_model_dtype(dtype_name, use_cuda, use_mps)
    kwargs = {"trust_remote_code": True, "low_cpu_mem_usage": True}
    if use_cuda:
        kwargs["device_map"] = "auto"
        kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
    else:
        kwargs["torch_dtype"] = dtype
    model = AutoModelForCausalLM.from_pretrained(base_model, **kwargs)
    if use_cuda:
        model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    if not use_cuda and use_mps:
        model.to("mps")
    if init_adapter:
        model = PeftModel.from_pretrained(model, init_adapter, is_trainable=True)
    else:
        model = get_peft_model(
            model,
            LoraConfig(
                r=lora_r,
                lora_alpha=lora_alpha,
                target_modules="all-linear",
                lora_dropout=lora_dropout,
                bias="none",
                task_type="CAUSAL_LM",
            ),
        )
    for parameter in model.parameters():
        if parameter.requires_grad:
            parameter.data = parameter.data.float()
    return model


def _device(model):
    return next(model.parameters()).device


def _move(batch, device):
    return {key: value.to(device) for key, value in batch.items()}


def evaluate_loss(model, loader, device, limit):
    model.eval()
    losses = []
    with torch.no_grad():
        for index, batch in enumerate(loader):
            if index >= limit:
                break
            loss = model(**_move(batch, device)).loss
            if torch.isfinite(loss):
                losses.append(float(loss.detach().cpu()))
    model.train()
    return sum(losses) / len(losses) if losses else None


def train(model, tokenizer, train_set, eval_set, args):
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True)
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        train_set,
        batch_size=args.batch_size,
        shuffle=True,
        generator=generator,
        collate_fn=collator,
    )
    eval_loader = DataLoader(eval_set, batch_size=1, shuffle=False, collate_fn=collator)
    device = _device(model)
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
        eps=args.optimizer_eps,
    )
    initial_eval_loss = evaluate_loss(model, eval_loader, device, min(4, args.eval_limit))
    if initial_eval_loss is None or not math.isfinite(initial_eval_loss):
        raise RuntimeError(f"Initial forward-loss probe is non-finite: {initial_eval_loss}")
    print(f"initial_eval_loss_probe={initial_eval_loss:.4f}")
    target_micro_steps = max(1, math.ceil(len(train_loader) * args.epochs))
    model.train()
    optimizer.zero_grad(set_to_none=True)
    consumed = 0
    updates = 0
    nonfinite_loss_skips = 0
    nonfinite_gradient_skips = 0
    total_loss = 0.0
    max_observed_gradient_norm = 0.0
    epoch_pass = 0
    print(
        f"training rows={len(train_set)} eval_rows={len(eval_set)} micro_steps={target_micro_steps} "
        f"grad_accum={args.grad_accum} device={device}"
    )
    while consumed < target_micro_steps:
        epoch_pass += 1
        for batch in train_loader:
            if consumed >= target_micro_steps:
                break
            consumed += 1
            loss = model(**_move(batch, device)).loss
            if not torch.isfinite(loss):
                nonfinite_loss_skips += 1
                optimizer.zero_grad(set_to_none=True)
                print(f"WARNING non-finite loss at micro_step={consumed}: {float(loss.detach().cpu())}")
                if nonfinite_loss_skips + nonfinite_gradient_skips > args.max_nonfinite_skips:
                    raise RuntimeError(
                        "Too many non-finite training events: "
                        f"loss={nonfinite_loss_skips}, gradient={nonfinite_gradient_skips}"
                    )
                continue
            (loss / args.grad_accum).backward()
            total_loss += float(loss.detach().cpu())
            if consumed % args.grad_accum == 0 or consumed == target_micro_steps:
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    [parameter for parameter in model.parameters() if parameter.requires_grad],
                    max_norm=0.3,
                )
                gradient_norm_value = float(gradient_norm.detach().float().cpu())
                if not math.isfinite(gradient_norm_value):
                    nonfinite_gradient_skips += 1
                    optimizer.zero_grad(set_to_none=True)
                    print(
                        "WARNING non-finite gradient at "
                        f"micro_step={consumed}; optimizer update skipped"
                    )
                    if nonfinite_loss_skips + nonfinite_gradient_skips > args.max_nonfinite_skips:
                        raise RuntimeError(
                            "Too many non-finite training events: "
                            f"loss={nonfinite_loss_skips}, gradient={nonfinite_gradient_skips}"
                        )
                    continue
                max_observed_gradient_norm = max(
                    max_observed_gradient_norm,
                    gradient_norm_value,
                )
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                updates += 1
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
                if updates % args.log_steps == 0 or consumed == target_micro_steps:
                    print(
                        f"update={updates} micro_step={consumed}/{target_micro_steps} "
                        f"avg_loss={total_loss / max(1, consumed):.4f}"
                    )
    eval_loss = evaluate_loss(model, eval_loader, device, args.eval_limit)
    return {
        "target_micro_steps": target_micro_steps,
        "consumed_micro_steps": consumed,
        "optimizer_updates": updates,
        "nonfinite_skips": nonfinite_loss_skips + nonfinite_gradient_skips,
        "nonfinite_loss_skips": nonfinite_loss_skips,
        "nonfinite_gradient_skips": nonfinite_gradient_skips,
        "max_observed_gradient_norm": max_observed_gradient_norm,
        "final_train_loss": total_loss / max(1, consumed),
        "sampled_eval_loss": eval_loss,
        "initial_eval_loss_probe": initial_eval_loss,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH)
    parser.add_argument("--supplemental-dataset", action="append", default=[])
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--init-adapter", required=True)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-report", default=RIGHTBRAIN_CONTRACT_V1_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--max-length", type=int, default=720)
    parser.add_argument("--eval-split", type=float, default=0.08)
    parser.add_argument("--eval-limit", type=int, default=24)
    parser.add_argument("--epochs", type=float, default=0.12)
    parser.add_argument("--learning-rate", type=float, default=6e-7)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--weight-decay", type=float, default=0.02)
    parser.add_argument("--optimizer-eps", type=float, default=1e-6)
    parser.add_argument("--lora-r", type=int, default=32)
    parser.add_argument("--lora-alpha", type=int, default=24)
    parser.add_argument("--lora-dropout", type=float, default=0.08)
    parser.add_argument("--max-nonfinite-skips", type=int, default=8)
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16", "float32"], default="auto")
    parser.add_argument("--log-steps", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260622)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(args.seed)
    rows, dataset_sources = load_training_rows(args.dataset, args.supplemental_dataset)
    random.Random(args.seed).shuffle(rows)
    eval_count = max(1, int(len(rows) * args.eval_split))
    eval_rows = rows[:eval_count]
    train_rows = rows[eval_count:]
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    train_set = CanonicalContractDataset(train_rows, tokenizer, args.max_length)
    eval_set = CanonicalContractDataset(eval_rows, tokenizer, args.max_length)
    lengths = [len(item["input_ids"]) for item in train_set.items + eval_set.items]
    if args.dry_run:
        print(
            json.dumps(
                {
                    "rows": len(rows),
                    "primary_rows": dataset_sources[0]["rows"],
                    "supplemental_rows": sum(source["rows"] for source in dataset_sources[1:]),
                    "train_rows": len(train_rows),
                    "eval_rows": len(eval_rows),
                    "token_length_min": min(lengths),
                    "token_length_max": max(lengths),
                    "token_length_mean": round(sum(lengths) / len(lengths), 2),
                    "max_length": args.max_length,
                },
                indent=2,
            )
        )
        return

    started = time.time()
    model = build_model(
        args.base_model,
        args.init_adapter,
        args.lora_r,
        args.lora_alpha,
        args.lora_dropout,
        args.dtype,
    )
    model.print_trainable_parameters()
    metrics = train(model, tokenizer, train_set, eval_set, args)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    adapter_model_path = output_dir / "adapter_model.safetensors"
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
        "base_model": args.base_model,
        "dataset_ref": Path(args.dataset).name,
        "dataset_sha256": _sha256(args.dataset),
        "dataset_sources": dataset_sources,
        "supplemental_rows": sum(source["rows"] for source in dataset_sources[1:]),
        "init_adapter_ref": Path(args.init_adapter).name,
        "init_adapter_config_sha256": _sha256(Path(args.init_adapter) / "adapter_config.json"),
        "output_adapter_ref": output_dir.name,
        "output_adapter_config_sha256": _sha256(output_dir / "adapter_config.json"),
        "output_adapter_model_sha256": _sha256(adapter_model_path),
        "rows": len(rows),
        "train_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "max_length": args.max_length,
        "token_length_min": min(lengths),
        "token_length_max": max(lengths),
        "token_length_mean": round(sum(lengths) / len(lengths), 2),
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "optimizer_eps": args.optimizer_eps,
        "batch_size": args.batch_size,
        "grad_accum": args.grad_accum,
        "seed": args.seed,
        "dtype": str(resolve_model_dtype(args.dtype, torch.cuda.is_available(), torch.backends.mps.is_available())),
        "duration_seconds": round(time.time() - started, 3),
        **metrics,
    }
    (output_dir / "rightbrain_contract_v1_training_run.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.run_report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
