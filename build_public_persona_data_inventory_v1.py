#!/usr/bin/env python3
"""Build one deterministic inventory across public-persona and local assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FILES = {
    "source_registry": ROOT / "datasets/public_persona_source_registry_v1.json",
    "observation_registry": ROOT / "datasets/public_persona_observation_source_registry_v2.json",
    "observations": ROOT / "datasets/public_persona_observations_v2.json",
    "reference_manifest": ROOT / "datasets/public_persona_reference_source_manifest_v2.json",
    "contrast_manifest": ROOT / "datasets/public_persona_contrast_source_manifest_v4.json",
    "readiness": ROOT / "datasets/public_persona_fidelity_eval_v2_readiness_inventory.json",
    "source_availability": ROOT / "reports/public_persona_source_availability_v8_result.json",
    "local_assets": ROOT / "datasets/public_persona_local_asset_registry_v1.json",
}
JSON_OUTPUT = ROOT / "reports/public_persona_data_inventory_v1.json"
MD_OUTPUT = ROOT / "reports/public_persona_data_inventory_v1.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path):
    return Path(path).relative_to(ROOT).as_posix()


def _target_sources(reference_manifest, role):
    return [
        source
        for source in reference_manifest["sources"]
        if source.get("actor_id") == reference_manifest["target_id"]
        and source.get("source_type") == "official_public_stream_archive"
        and source.get("dataset_role") == role
    ]


def build_inventory():
    payloads = {name: load(path) for name, path in FILES.items()}
    references = payloads["reference_manifest"]
    contrasts = payloads["contrast_manifest"]
    observations = payloads["observations"]
    readiness = payloads["readiness"]
    availability = payloads["source_availability"]
    local_assets = payloads["local_assets"]
    observation_source_by_id = {
        source["source_id"]: source for source in payloads["observation_registry"]["sources"]
    }

    calibration_sources = _target_sources(references, "calibration")
    holdout_sources = _target_sources(references, "final_holdout")
    contrast_sources = [
        source
        for source in contrasts["sources"]
        if source.get("source_type") == "official_public_stream_archive"
        and source.get("dataset_role") == "contrast_calibration"
    ]
    contrast_actor_ids = sorted({source["actor_id"] for source in contrast_sources})
    voice = next(asset for asset in local_assets["assets"] if asset["asset_id"] == "uruha_local_voice_corpus_v1")

    if len(calibration_sources) != 3:
        raise ValueError("expected exactly three target calibration sources")
    if len(holdout_sources) != 4:
        raise ValueError("expected exactly four target final holdout sources")
    if len(contrast_sources) != 9 or len(contrast_actor_ids) != 3:
        raise ValueError("expected nine contrast sources across three actors")
    if len(observations["observations"]) != 5:
        raise ValueError("expected five development observations")

    return {
        "schema": "uruha_public_persona_data_inventory_v1",
        "target_id": references["target_id"],
        "reviewed_at": local_assets["reviewed_at"],
        "artifact_bindings": {
            name: {"path": relative(path), "sha256": sha256(path)}
            for name, path in FILES.items()
        },
        "available_data": {
            "official_identity_and_policy_sources": len(payloads["source_registry"]["sources"]),
            "observation_registry_entries": len(payloads["observation_registry"]["sources"]),
            "development_observations": len(observations["observations"]),
            "target_calibration_source_reservations": len(calibration_sources),
            "target_final_holdout_source_reservations": len(holdout_sources),
            "matched_contrast_actors": len(contrast_actor_ids),
            "matched_contrast_source_reservations": len(contrast_sources),
            "local_confirmed_voice_clips": voice["registered_fingerprint"]["raw_audio_count"],
            "local_confirmed_voice_minutes": voice["registered_fingerprint"]["duration_minutes"],
        },
        "target_sources": {
            "development": [
                {
                    "observation_id": observation["observation_id"],
                    "source_id": observation["source_id"],
                    "source_type": observation_source_by_id[observation["source_id"]]["source_type"],
                    "url": observation_source_by_id[observation["source_id"]]["url"],
                    "confidence": observation["confidence"],
                }
                for observation in observations["observations"]
            ],
            "calibration": [
                {key: source.get(key) for key in ("source_id", "url", "published_at", "sealed")}
                for source in calibration_sources
            ],
            "final_holdout": [
                {key: source.get(key) for key in ("source_id", "url", "published_at", "sealed")}
                for source in holdout_sources
            ],
            "local_voice": {
                "asset_id": voice["asset_id"],
                "identity_status": local_assets["owner_attestations"][0]["identity_status"],
                "source_traceability": voice["source_traceability"],
                "fingerprint": voice["registered_fingerprint"],
            },
        },
        "contrast_sources": {
            "actor_ids": contrast_actor_ids,
            "sources": [
                {key: source.get(key) for key in ("source_id", "actor_id", "url", "published_at")}
                for source in contrast_sources
            ],
        },
        "usage_status": {
            "active_or_historical_runtime": [
                "The confirmed local voice corpus was used to train local Style-Bert-VITS2 assets.",
                "The raw voice clips are not loaded into the rightbrain during chat.",
                "The local rightbrain currently falls back to Qwen2.5-7B plus uruha_v10_all_linear_lora.",
            ],
            "research_development_only": [
                "Five paraphrased target observations support development diagnostics only.",
                "Three target calibration streams and nine matched-contrast streams are source reservations for human coding.",
            ],
            "sealed_not_used": [
                "Four target final-holdout streams are reserved and their content remains unopened for scoring.",
            ],
            "not_target_evidence": [
                "Manual patch text, generated rightbrain corpora, benchmark data, human-feedback logs, and model outputs.",
            ],
        },
        "formal_readiness": {
            "status": readiness["status"],
            "counts": readiness["counts"],
            "flags": readiness["flags"],
        },
        "verified_source_availability": {
            "decision": availability["decision"],
            "summary": availability["summary"],
            "evidence_boundary": availability["evidence_boundary"],
        },
        "boundaries": local_assets["boundaries"],
    }


def render_markdown(inventory):
    counts = inventory["available_data"]
    sources = inventory["target_sources"]
    readiness = inventory["formal_readiness"]
    lines = [
        "# Uruha 公開人格與本機資料總覽 V1",
        "",
        "> 這份總覽整理目前已存在或已登錄的資料，不搬動原始語音、模型、對話紀錄，也不把專案生成資料當成本人資料。",
        "",
        "## 一句話現況",
        "",
        f"目前有 **{counts['local_confirmed_voice_clips']} 段（約 {counts['local_confirmed_voice_minutes']:.1f} 分鐘）已確認為 Uruha 的本機語音**、5 筆公開行為開發觀察、3 個校準來源、4 個封存來源與 3 位對照人物；但正式行為事件、人工評分和人格相似度分數仍是 0。",
        "",
        "## 哪些資料真的存在",
        "",
        "| 資料層 | 數量 | 現在怎麼使用 | 能否當正式本人證據 |",
        "|---|---:|---|---:|",
        f"| 本機 Uruha 語音 | {counts['local_confirmed_voice_clips']} 段 / {counts['local_confirmed_voice_minutes']:.1f} 分鐘 | 已用於 TTS 訓練 | 暫時不能；缺原始 URL 與時間戳 |",
        f"| 公開行為開發觀察 | {counts['development_observations']} 筆 | 研究設計與契約診斷 | 僅開發證據，不是最終分數 |",
        f"| Uruha 校準來源 | {counts['target_calibration_source_reservations']} 個 YouTube archive | 等待人工事件編碼 | 還不能；目前只有來源 metadata |",
        f"| Uruha 最終封存來源 | {counts['target_final_holdout_source_reservations']} 個 YouTube archive | 保持封存 | 尚未使用，防止測試洩漏 |",
        f"| 對照人物來源 | {counts['matched_contrast_actors']} 人 / {counts['matched_contrast_source_reservations']} 個 archive | 等待相同規則人工編碼 | 還不能；目前沒有行為標籤 |",
        "| 人工／模型生成資料 | 多批 | 右腦訓練、回歸與測試 | 否 |",
        "",
        "## 目前使用狀態",
        "",
        "### 已在系統或歷史訓練中使用",
        "",
        "- 874 段確認語音已形成 Style-Bert-VITS2 的 Uruha TTS 模型；聊天時使用的是訓練後模型，不是把原始錄音送進右腦。",
        "- 這台機器目前缺少優先候選 adapter，因此右腦回退到 `Qwen2.5-7B-Instruct + uruha_v10_all_linear_lora`。",
        "- `uruha_v10_patch_train.json` 的 36 筆是人工修補句，只能算工程訓練資料。",
        "",
        "### 只用於研究設計，尚未進入正式人格評分",
        "",
        "- 5 筆公開行為觀察是研究者改寫摘要，不保存原貼文全文，也沒有寫進 production memory。",
        "- 3 個 Uruha 校準來源與 9 個對照來源已驗證 URL、官方頻道與日期，但尚未產生行為事件標籤。",
        "",
        "### 封存且尚未使用",
        "",
        "- 4 個 Uruha final holdout 只登錄 metadata；目前不開內容、不產生答案、不訓練模型。",
        "",
        "## Uruha 來源分組",
        "",
        "### 開發觀察",
        "",
    ]
    for item in sources["development"]:
        lines.append(
            f"- `{item['observation_id']}` <- [{item['source_id']}]({item['url']})"
            f"（{item['source_type']}，信心：{item['confidence']}）"
        )
    lines.extend(["", "### 校準來源：開發期間可人工編碼", ""])
    for item in sources["calibration"]:
        lines.append(f"- [{item['source_id']}]({item['url']})，發布日 `{item['published_at']}`。")
    lines.extend(["", "### Final holdout：只保留，不讀內容", ""])
    for item in sources["final_holdout"]:
        lines.append(f"- `{item['source_id']}`，發布日 `{item['published_at']}`，sealed=`{str(item['sealed']).lower()}`。")
    lines.extend(
        [
            "",
            "## 語音資料已確認什麼",
            "",
            "- 已確認：`Style-Bert-VITS2/Data/uruha/` 的說話者是一ノ瀬うるは。",
            "- 已確認：逐字稿索引、raw WAV、processed WAV 都是 874 筆，總長約 87.7 分鐘。",
            "- 尚未確認：原始影片 URL、影片 ID、錄音日期、每段時間戳與再利用權利。",
            "- 因此：可以保留現有 TTS 使用，但暫時不能把這批語音放進正式人格相似度分數。",
            "",
            "## 目前正式評價還缺什麼",
            "",
            f"目前狀態：`{readiness['status']}`。",
            "",
            "- target calibration 行為事件：0。",
            "- contrast 行為事件：0。",
            "- 人類盲評：0。",
            "- 系統正式回答與人格分數：0。",
            "",
            "所以現在完成的是 **來源與邊界整理**，不是已經測出『像本人多少％』。",
            "",
            "## 重建與本機驗證",
            "",
            "```bash",
            "python3 build_public_persona_data_inventory_v1.py --write",
            "python3 build_public_persona_data_inventory_v1.py --check",
            "python3 build_public_persona_data_inventory_v1.py --verify-local --asset-root /path/to/uruharemake2",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def serialized_outputs():
    inventory = build_inventory()
    return (
        json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        render_markdown(inventory),
    )


def write_outputs():
    json_text, md_text = serialized_outputs()
    JSON_OUTPUT.write_text(json_text, encoding="utf-8")
    MD_OUTPUT.write_text(md_text, encoding="utf-8")


def check_outputs():
    json_text, md_text = serialized_outputs()
    expected = {JSON_OUTPUT: json_text, MD_OUTPUT: md_text}
    stale = [path for path, text in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
    for path in stale:
        print(f"STALE: {relative(path)}", file=sys.stderr)
    if not stale:
        print("Public persona data inventory is current.")
    return not stale


def _wav_stats(directory):
    files = sorted(Path(directory).glob("*.wav"))
    seconds = 0.0
    for path in files:
        with wave.open(str(path), "rb") as handle:
            seconds += handle.getnframes() / handle.getframerate()
    return len(files), round(seconds, 3)


def verify_local_assets(asset_root):
    registry = load(FILES["local_assets"])
    assets = {asset["asset_id"]: asset for asset in registry["assets"]}
    voice = assets["uruha_local_voice_corpus_v1"]
    root = Path(asset_root).resolve()
    transcript = root / voice["paths"]["transcript_index"]
    raw_dir = root / voice["paths"]["raw_audio_directory"]
    processed_dir = root / voice["paths"]["processed_audio_directory"]
    fingerprint = voice["registered_fingerprint"]
    errors = []

    if not transcript.is_file():
        errors.append(f"missing transcript index: {transcript}")
    else:
        lines = sum(1 for line in transcript.read_text(encoding="utf-8").splitlines() if line.strip())
        if lines != fingerprint["transcript_count"]:
            errors.append(f"transcript count {lines} != {fingerprint['transcript_count']}")
        observed_sha = sha256(transcript)
        if observed_sha != fingerprint["transcript_index_sha256"]:
            errors.append("transcript index sha256 mismatch")

    raw_count, raw_seconds = _wav_stats(raw_dir) if raw_dir.is_dir() else (0, 0.0)
    processed_count, processed_seconds = _wav_stats(processed_dir) if processed_dir.is_dir() else (0, 0.0)
    if raw_count != fingerprint["raw_audio_count"]:
        errors.append(f"raw audio count {raw_count} != {fingerprint['raw_audio_count']}")
    if processed_count != fingerprint["processed_audio_count"]:
        errors.append(f"processed audio count {processed_count} != {fingerprint['processed_audio_count']}")
    if raw_seconds != fingerprint["duration_seconds"]:
        errors.append(f"raw duration {raw_seconds} != {fingerprint['duration_seconds']}")
    if processed_seconds != fingerprint["duration_seconds"]:
        errors.append(f"processed duration {processed_seconds} != {fingerprint['duration_seconds']}")

    patch = assets["uruha_v10_manual_patch_v1"]
    patch_path = root / patch["path"]
    if not patch_path.is_file():
        errors.append(f"missing manual patch: {patch_path}")
    else:
        rows = load(patch_path)
        if len(rows) != patch["registered_fingerprint"]["row_count"]:
            errors.append("manual patch row count mismatch")
        if sha256(patch_path) != patch["registered_fingerprint"]["sha256"]:
            errors.append("manual patch sha256 mismatch")

    missing_main = root / assets["uruha_legacy_main_text_dataset"]["path"]
    if missing_main.exists():
        errors.append("legacy main text dataset unexpectedly exists; registry must be updated")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return False
    print(f"Local assets verified: 874 clips, {raw_seconds / 60:.2f} minutes, identity attested by project owner.")
    return True


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--verify-local", action="store_true")
    parser.add_argument("--asset-root", default=str(ROOT))
    args = parser.parse_args()
    if args.write:
        write_outputs()
        print(f"Wrote {relative(JSON_OUTPUT)} and {relative(MD_OUTPUT)}")
        return 0
    if args.check:
        return 0 if check_outputs() else 1
    return 0 if verify_local_assets(args.asset_root) else 1


if __name__ == "__main__":
    raise SystemExit(main())
