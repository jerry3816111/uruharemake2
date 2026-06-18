import inspect
import os
import re
from collections import Counter

import torch
from datasets import Dataset, load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
)

# ==========================================
# V10 all-linear LoRA
# Goal: make the right brain more human-like,
# more in-character, and less assistant-like.
# ==========================================
BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
BASE_DATASET_PATH = "uruha_perfect_train.json"
PATCH_DATASET_PATH = "uruha_v10_patch_train.json"
OUTPUT_DIR = "./uruha_v10_all_linear_lora"

SEED = 42
MAX_LENGTH = 384
EVAL_SPLIT = 0.12

LORA_R = 32
LORA_ALPHA = 20
LORA_DROPOUT = 0.10

LEARNING_RATE = 6e-6
NUM_EPOCHS = 4
WEIGHT_DECAY = 0.02
WARMUP_RATIO = 0.15
PATCH_REPEAT = 3

POLITE_PATTERN = re.compile(r"(です|ます|でした|ません|ましょう|ください)")
CODE_PATTERN = re.compile(r"(```|`|def |class |import |print\(|\.sort\(|for |while |\{|\}|\(|\)|=)")
ENGLISH_TAG_PATTERN = re.compile(r"[A-Za-z]{4,}")
WEIRD_SYMBOL_PATTERN = re.compile(r"[\u2600-\u27BF\U0001F300-\U0001FAFF]")
JAPANESE_PATTERN = re.compile(r"[ぁ-んァ-ヶー一-龠]")

FORBIDDEN_OUTPUT_FRAGMENTS = [
    "sleepy face",
    "何十倍も歳上",
    "何十倍も年上",
    "了解。行くなよ",
    "大規模言語モデル",
    "Qwen",
    "LLM",
    "language model",
]

ASSISTANTY_PHRASES = [
    "わかりました",
    "承知しました",
    "かしこまりました",
    "お手伝いします",
]


def normalize_user_text(text: str) -> str:
    text = text.strip()
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def sanitize_output(text: str) -> str:
    text = text.strip()
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^(Thought:|Output:|Assistant:|Uruha:)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("「", "").replace("」", "")
    text = text.replace("『", "").replace("』", "")
    text = text.replace("`", "")
    text = WEIRD_SYMBOL_PATTERN.sub("", text)

    # Keep first person stable for the character.
    text = re.sub(r"\b私\b", "うち", text)
    text = text.replace("わたし", "うち")
    text = text.replace("私は", "うちは")
    text = text.replace("私に", "うちに")
    text = text.replace("私が", "うちが")
    text = text.replace("私の", "うちの")

    # Remove strongly assistant-like phrasing.
    for phrase in ASSISTANTY_PHRASES:
        text = text.replace(phrase, "うん")

    # Remove self-referential drift that does not match the character.
    text = text.replace("うるはん", "うち")
    text = text.replace("ウルハは", "うちは")
    text = text.replace("一ノ瀬は", "うちは")

    # Keep responses short and speech-like.
    match = re.search(r"^(.{1,48}?[。！？!?])", text)
    if match:
        text = match.group(1)
    elif len(text) > 48:
        text = text[:48].rstrip(" 、,") + "。"

    text = re.sub(r"\s+", " ", text).strip()
    return text


def should_skip_output(text: str) -> bool:
    if not text:
        return True
    if len(text) < 4 or len(text) > 64:
        return True
    if not JAPANESE_PATTERN.search(text):
        return True
    if CODE_PATTERN.search(text):
        return True
    if any(fragment in text for fragment in FORBIDDEN_OUTPUT_FRAGMENTS):
        return True
    return False


def preprocess_dataset(paths: list[str]) -> Dataset:
    clean_rows = []
    stats = Counter()

    for path in paths:
        if not os.path.exists(path):
            print(f"Dataset not found, skipping: {path}")
            continue

        raw_dataset = load_dataset("json", data_files=path, split="train")
        repeat_count = PATCH_REPEAT if os.path.basename(path) == PATCH_DATASET_PATH else 1

        for row in raw_dataset:
            user_msg = normalize_user_text(row["input"])
            raw_output = row["output"].strip()
            cleaned_output = sanitize_output(raw_output)

            stats["raw_total"] += 1
            stats[f"raw_total::{os.path.basename(path)}"] += 1
            if "私" in raw_output or "わたし" in raw_output:
                stats["rewrote_first_person"] += 1
            if POLITE_PATTERN.search(raw_output):
                stats["polite_samples_seen"] += 1
            if ENGLISH_TAG_PATTERN.search(raw_output):
                stats["english_samples_seen"] += 1
            if WEIRD_SYMBOL_PATTERN.search(raw_output):
                stats["weird_symbol_samples_seen"] += 1

            if should_skip_output(cleaned_output):
                stats["skipped"] += 1
                stats[f"skipped::{os.path.basename(path)}"] += 1
                continue

            for _ in range(repeat_count):
                clean_rows.append({"input": user_msg, "output": cleaned_output})
            stats["kept"] += 1
            stats[f"kept::{os.path.basename(path)}"] += 1

    if len(clean_rows) < 20:
        raise RuntimeError(
            f"Too few usable samples after sanitation: {len(clean_rows)}. "
            "Expand or clean the dataset before training."
        )

    print("Dataset sanitation report:")
    for key in sorted(stats):
        print(f"  - {key}: {stats[key]}")

    return Dataset.from_list(clean_rows).shuffle(seed=SEED)


def build_prompt(user_msg: str) -> str:
    return (
        "<|im_start|>system\n"
        'You are "Ichinose Uruha" (一ノ瀬ウルは).\n'
        "[Identity]\n"
        "- VTuber from VSPO!.\n"
        "- Lazy, slightly bratty, gamer, but still human and emotionally natural.\n"
        '- First person is always "うち". Never use "私".\n'
        "[Style Rules]\n"
        "- Casual Japanese only.\n"
        "- Reply in one short spoken sentence.\n"
        "- Sound like a person talking, not an assistant serving.\n"
        "- Avoid polite customer-service language.\n"
        "- No English tags, no stage directions, no emoji, no metadata.\n"
        "- No fabricated lore, age-gap setting, fantasy setting, or hidden backstory.\n"
        "- Do not call yourself by weird variants or nicknames.\n"
        "- If the topic is outside your persona, dodge briefly with disinterest.\n"
        "- Do not explain code, math, history, or technical facts.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        f"[心の声]: リスナーがこう言っている。『{user_msg}』。一ノ瀬ウルハとして短く自然に返事して。<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def tokenize_function(example, tokenizer):
    prompt = build_prompt(example["input"])
    response = f'{example["output"]}<|im_end|>'

    prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
    response_ids = tokenizer(response, add_special_tokens=False).input_ids

    input_ids = prompt_ids + response_ids
    attention_mask = [1] * len(input_ids)
    labels = [-100] * len(prompt_ids) + response_ids

    input_ids = input_ids[:MAX_LENGTH]
    attention_mask = attention_mask[:MAX_LENGTH]
    labels = labels[:MAX_LENGTH]

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


print("Loading tokenizer and base model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

quantization_config = BitsAndBytesConfig(load_in_8bit=True)

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=quantization_config,
    device_map="auto",
    trust_remote_code=True,
)
model.config.use_cache = False
model = prepare_model_for_kbit_training(model)
model.gradient_checkpointing_enable()

lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    target_modules="all-linear",
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

print("Loading and sanitizing dataset...")
dataset = preprocess_dataset([BASE_DATASET_PATH, PATCH_DATASET_PATH])
dataset_split = dataset.train_test_split(test_size=EVAL_SPLIT, seed=SEED)

print("Tokenizing dataset with completion-only labels...")
tokenized_train = dataset_split["train"].map(
    lambda ex: tokenize_function(ex, tokenizer),
    remove_columns=dataset.column_names,
)
tokenized_eval = dataset_split["test"].map(
    lambda ex: tokenize_function(ex, tokenizer),
    remove_columns=dataset.column_names,
)

data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True)

training_args_kwargs = {
    "output_dir": OUTPUT_DIR,
    "per_device_train_batch_size": 2,
    "per_device_eval_batch_size": 2,
    "gradient_accumulation_steps": 4,
    "learning_rate": LEARNING_RATE,
    "num_train_epochs": NUM_EPOCHS,
    "logging_steps": 2,
    "save_strategy": "epoch",
    "save_total_limit": 1,
    "load_best_model_at_end": True,
    "metric_for_best_model": "eval_loss",
    "greater_is_better": False,
    "lr_scheduler_type": "cosine",
    "warmup_ratio": WARMUP_RATIO,
    "weight_decay": WEIGHT_DECAY,
    "optim": "paged_adamw_8bit",
    "fp16": torch.cuda.is_available(),
    "bf16": False,
    "max_grad_norm": 0.3,
    "gradient_checkpointing": True,
    "group_by_length": True,
    "remove_unused_columns": False,
    "report_to": "none",
    "seed": SEED,
    "data_seed": SEED,
}

training_args_signature = inspect.signature(TrainingArguments.__init__)
if "evaluation_strategy" in training_args_signature.parameters:
    training_args_kwargs["evaluation_strategy"] = "epoch"
elif "eval_strategy" in training_args_signature.parameters:
    training_args_kwargs["eval_strategy"] = "epoch"
else:
    raise RuntimeError(
        "This transformers version exposes neither `evaluation_strategy` nor "
        "`eval_strategy` on TrainingArguments."
    )

supported_training_args = set(training_args_signature.parameters)
filtered_training_args_kwargs = {
    key: value
    for key, value in training_args_kwargs.items()
    if key in supported_training_args
}
skipped_training_args = sorted(set(training_args_kwargs) - set(filtered_training_args_kwargs))
if skipped_training_args:
    print(
        "Skipping unsupported TrainingArguments for this transformers version:",
        ", ".join(skipped_training_args),
    )

training_args = TrainingArguments(**filtered_training_args_kwargs)

trainer = Trainer(
    model=model,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_eval,
    args=training_args,
    data_collator=data_collator,
)

print("Starting V10 all-linear fine-tuning...")
train_result = trainer.train()
trainer.save_state()

print("Saving LoRA adapter and tokenizer...")
trainer.model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("Training finished.")
print(f"Output saved to: {OUTPUT_DIR}")
print(f"Final train loss: {train_result.training_loss:.4f}")
