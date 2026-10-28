# V2.14 盲評操作說明

目的：比較同模型 Baseline 與 V2.13 System，但評分者只看到隨機 A/B，不知道條件名稱。自動 proxy 不能代替本步驟。

## 評分者規則

- 至少 3 位彼此獨立、沒有看 blind key 的評分者。
- 每人完成全部 54 pairs；不可只挑好例子。
- 依 packet 提供的 `context_A/context_B` 與當輪回覆評分；允許兩者都差。
- 核心維度：隱含需求是否被接住但不過度斷言、過度解讀／捏造（反向）、felt understanding。
- turn > 1 才評 cross-turn consistency；只有 `rating_focus` 指定 correction 的項目才評 revision quality。
- Uruha 公開人格自然度是次要指標，不能取代 pragmatic understanding。
- 發現私人內容捏造、讀心式斷言、拒絕採納使用者更正、中文／英文表面洩漏時，填入 error tags 與 note。

## Artifacts

- 評分內容：`analysis/v2_14_human_pragmatic_blind_packet.json`
- 評分者 1：`analysis/v2_14_rater-01_ratings.jsonl`
- 評分者 2：`analysis/v2_14_rater-02_ratings.jsonl`
- 評分者 3：`analysis/v2_14_rater-03_ratings.jsonl`
- `analysis/v2_14_human_pragmatic_blind_key.json` 只能由分析者在三份評分完成後使用。

三份完成的 JSONL 需合併為一個檔案，保留每列的不同 `rater_id`，再執行：

```bash
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python human_pragmatic_human_eval_v2_14.py \
  --packet analysis/v2_14_human_pragmatic_blind_packet.json \
  --key analysis/v2_14_human_pragmatic_blind_key.json \
  --ratings analysis/v2_14_all_raters_ratings.jsonl \
  --output analysis/v2_14_human_pragmatic_human_eval_result.json
```

Analyzer 會拒絕不完整、重複或少於三位評分者的資料；少於三位只能稱 pilot。只有輸出 `claim_authorized=true` 才能作 frozen-condition superiority claim。
