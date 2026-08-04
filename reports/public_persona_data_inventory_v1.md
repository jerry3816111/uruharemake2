# Uruha 公開人格與本機資料總覽 V1

> 這份總覽整理目前已存在或已登錄的資料，不搬動原始語音、模型、對話紀錄，也不把專案生成資料當成本人資料。

## 一句話現況

目前有 **874 段（約 87.7 分鐘）已確認為 Uruha 的本機語音**、5 筆公開行為開發觀察、3 個校準來源、4 個封存來源與 3 位對照人物；但正式行為事件、人工評分和人格相似度分數仍是 0。

## 哪些資料真的存在

| 資料層 | 數量 | 現在怎麼使用 | 能否當正式本人證據 |
|---|---:|---|---:|
| 本機 Uruha 語音 | 874 段 / 87.7 分鐘 | 已用於 TTS 訓練 | 暫時不能；缺原始 URL 與時間戳 |
| 公開行為開發觀察 | 5 筆 | 研究設計與契約診斷 | 僅開發證據，不是最終分數 |
| Uruha 校準來源 | 3 個 YouTube archive | 等待人工事件編碼 | 還不能；目前只有來源 metadata |
| Uruha 最終封存來源 | 4 個 YouTube archive | 保持封存 | 尚未使用，防止測試洩漏 |
| 對照人物來源 | 3 人 / 9 個 archive | 等待相同規則人工編碼 | 還不能；目前沒有行為標籤 |
| 人工／模型生成資料 | 多批 | 右腦訓練、回歸與測試 | 否 |

## 目前使用狀態

### 已在系統或歷史訓練中使用

- 874 段確認語音已形成 Style-Bert-VITS2 的 Uruha TTS 模型；聊天時使用的是訓練後模型，不是把原始錄音送進右腦。
- 這台機器目前缺少優先候選 adapter，因此右腦回退到 `Qwen2.5-7B-Instruct + uruha_v10_all_linear_lora`。
- `uruha_v10_patch_train.json` 的 36 筆是人工修補句，只能算工程訓練資料。

### 只用於研究設計，尚未進入正式人格評分

- 5 筆公開行為觀察是研究者改寫摘要，不保存原貼文全文，也沒有寫進 production memory。
- 3 個 Uruha 校準來源與 9 個對照來源已驗證 URL、官方頻道與日期，但尚未產生行為事件標籤。

### 封存且尚未使用

- 4 個 Uruha final holdout 只登錄 metadata；目前不開內容、不產生答案、不訓練模型。

## Uruha 來源分組

### 開發觀察

- `persona_obs_v2_dev_001` <- [uruha_x_profile_dev_20260801](https://x.com/uruha_ichinose)（verified_target_profile，信心：medium）
- `persona_obs_v2_dev_002` <- [uruha_x_delayed_song_notice_dev_20260801](https://x.com/uruha_ichinose/status/1982395052333863365)（verified_target_public_post，信心：medium）
- `persona_obs_v2_dev_003` <- [uruha_x_fatigue_plan_dev_20260801](https://x.com/uruha_ichinose/status/2083131719323205667)（verified_target_public_post，信心：medium）
- `persona_obs_v2_dev_004` <- [uruha_x_health_uncertainty_dev_20260801](https://x.com/uruha_ichinose/status/2082761153659429283)（verified_target_public_post，信心：medium）
- `persona_obs_v2_dev_005` <- [uruha_x_stream_start_dev_20260801](https://x.com/uruha_ichinose/status/2083142143657623982)（verified_target_public_post，信心：medium）

### 校準來源：開發期間可人工編碼

- [uruha_calibration_youtube_valorant_20260318](https://www.youtube.com/watch?v=cssf0abPOPw)，發布日 `2026-03-18`。
- [uruha_calibration_youtube_street_fighter_20250317](https://www.youtube.com/watch?v=M37jBhQWK_0)，發布日 `2025-03-17`。
- [uruha_calibration_youtube_farming_20250308](https://www.youtube.com/watch?v=6mpZwCihM0Q)，發布日 `2025-03-08`。

### Final holdout：只保留，不讀內容

- `uruha_youtube_forza_holdout_v2`，發布日 `2026-07-24`，sealed=`true`。
- `uruha_youtube_apex_team_holdout_v2`，發布日 `2026-07-29`，sealed=`true`。
- `uruha_final_holdout_youtube_apex_collab_20250206`，發布日 `2025-02-06`，sealed=`true`。
- `uruha_final_holdout_youtube_social_deduction_20210404`，發布日 `2021-04-04`，sealed=`true`。

## 語音資料已確認什麼

- 已確認：`Style-Bert-VITS2/Data/uruha/` 的說話者是一ノ瀬うるは。
- 已確認：逐字稿索引、raw WAV、processed WAV 都是 874 筆，總長約 87.7 分鐘。
- 尚未確認：原始影片 URL、影片 ID、錄音日期、每段時間戳與再利用權利。
- 因此：可以保留現有 TTS 使用，但暫時不能把這批語音放進正式人格相似度分數。

## 目前正式評價還缺什麼

目前狀態：`official_source_manifest_and_rater_protocol_only_no_formal_persona_dataset`。

- target calibration 行為事件：0。
- contrast 行為事件：0。
- 人類盲評：0。
- 系統正式回答與人格分數：0。

所以現在完成的是 **來源與邊界整理**，不是已經測出『像本人多少％』。

## 重建與本機驗證

```bash
python3 build_public_persona_data_inventory_v1.py --write
python3 build_public_persona_data_inventory_v1.py --check
python3 build_public_persona_data_inventory_v1.py --verify-local --asset-root /path/to/uruharemake2
```
