# P3-A 離線公平比較入口驗收

日期：2026-09-10（Asia/Taipei）
狀態：**PASS（僅 P3-A offline contract）／REVIEW_REQUIRED**

## 實際交付

- `p3_product_comparison.py`：純標準庫的 design loader、generation-view allowlist、共同來源 hash、三條件
  shared budget、case state path 隔離、invocation intent／immutable complete checkpoint、manifest validation。
- `run_p3_product_comparison.py`：`contract`、`preflight`、`run` 三模式。contract 只接 deterministic fake；
  preflight 只讀本機檔案與 Ollama metadata；run 在缺 implementation／data／review release 時 0-call 拒絕。
- `test_p3_product_comparison.py`：必要負案例與兩條 transport/model route、order schedule、artifact integrity 測試。
- 未修改 brain、P1/P2、正式 M、persona data、design、lock、門檻或原始 dirty checkout。

三個條件現在可以從同一 frozen prefix/input 建 view：

1. `full_history_direct`：1 個 logical call，上限 768 completion tokens。
2. `full_history_deliberate`：draft／critique／revise 各 256；scratch 不回寫共同歷史。
3. `product_system`：由可注入 worker 使用同一 view 與 shared budget；P3-A 僅 fake worker，沒有 import 產品或 DB。

## 必要負案例

| # | 契約風險 | 實際結果 |
|---:|---|---|
| 1 | baseline 漏前一個 session／混入當輪 system reply | common-source／turn-id gate 拒絕；0 transport |
| 2 | future／family／expected answer／scorer 注入 | prefix/input allowlist 拒絕；generation view 無 annotation path |
| 3 | 第二 case 重用第一 case state path | `cross_case_state_reuse` |
| 4 | native M31 使用 `qwen3.5:9b` | `model_gate_rejected`；正向 fake 亦核對 native 與 OpenAI-compatible 均為 `qwen2.5:7b` |
| 5 | 第二／第三 call 重置 768 output budget | shared aggregate cap 在第三個 320-token reservation 前拒絕；deliberate 合計固定 768 |
| 6 | context／共同歷史超額，或 actual usage 缺失／超額 | fail closed；不截斷、不以字數補 token，usage 缺失後 budget terminal |
| 7 | transport timeout／intent-only 中斷後重跑 | 第一次保留 intent＋failure；第二次 0-call `intent_without_complete_no_retry` |
| 8 | complete checkpoint、source、output 或最終 manifest 被改 | request／record／content／manifest digest gate 拒絕；output path 不覆寫 |
| 9 | implementation／data／review release 缺少 | run mode exit 2；transport/model/network/paid attempts 全為 0 |
| 10 | 匿名 AB／BA 交換 | condition mapping 還原一致；原始左右數值差正負反轉；未新增自然語言 scorer |

另驗證 6-case schedule 的三條件在每個位置各出現 2 次；相同 seed 產生相同 schedule。

## 可重現證據

```text
.venv/product_checks/bin/python -m pytest -q test_p3_product_comparison.py
30 passed in 0.14s

.venv/product_checks/bin/python -m pytest -q \
  test_p3_complete_product_compute_accounting.py \
  test_persona_policy_compute_seam_v1.py \
  test_persona_policy_token_parity_v1.py
32 passed, 8 dependency warnings in 6.56s
```

Contract artifact：`analysis/p3_a_offline_contract_result_2026-09-09.json`。

- fake transport attempts：5（direct 1、deliberate 3、product fake worker 1）
- real model calls：0
- network calls：0
- paid calls：0
- deterministic manifest SHA-256：`fb235ec214866ccb3bd2a47e6e73bf595a07cd564002ef903c7cb5be8152dece`
- 同一 source-history SHA-256：`4c1707723ba0afd1495235ee98a2806add0c14549530d0006cc31d1d4814a8da`
- 同一 input SHA-256：`d958c4ce343d05caee42c6ff1b56810542f8c16ae7e29791f7d3b588e3d39aa9`

Contract 另綁定三個 implementation artifact SHA-256：core
`5cbd6be4949befe43bf7c63d71c7814a81c7810e5555354eadfdcee8b7952e62`、runner
`0e9b4206e5fd9eaef6fea2a8033591ac42486a6b0933ff4de9f5c502a013acff`、tests
`a57d5bf68976803eb467ff31b35b48e876ffcb4ec98ea5aec39996005276a6b2`。

JUnit：`analysis/p3_a_contract_tests_2026-09-09.xml`。

Preflight：`analysis/p3_a_preflight_2026-09-09.json`。

- 本機 `qwen2.5:7b` metadata 可讀；blob digest
  `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`。
- Ollama template 可讀並留 hash；provider-equivalent tokenizer/template 綁定仍為 false。
- implementation release、data freeze、review release 均為 false。

Run refusal：`analysis/p3_a_run_refusal_2026-09-09.json`，exit 2、transport attempts 0。

## 證據邊界與保留失敗

這次只證明：比較入口在 fake 層能守住完整共同歷史、資訊 allowlist、case 隔離、模型設定、逐條件共享預算、
不可重試與不可覆寫規則。fake 日文句子不是模型品質成果，也沒有測 product、fresh generation、Safari、runtime graph、
人評、confirmation、50輪或「比 LLM 好」。因此目前不能生成優勢結論。

保留未通過項：

- 真實 tokenizer/template 與 provider usage 的等價綁定未完成。
- 真實 isolated product worker 尚未經 GPT6 implementation freeze 審查。
- P3-B smoke corpus、P3-C confirmation data/review release 尚不存在。
- Safari 與真人證據仍 pending；正式 DB 未讀、未寫。

## GPT5 交接執行情況

- 執行角色：GPT5（Codex task；更細模型識別字不可得）。
- 時間範圍：2026-09-09 至 2026-09-10 Asia/Taipei。
- 範圍外修改：0；真模型／付費呼叫：0。
- 有證據的範圍內修正批次：2（補 common-history cap；補 route/order/metadata 與 artifact integrity）。
- 使用者救援：0；使用者只發出一次正常「請繼續」。
- Codex token／usage 數字：工具不可得；app Goal 仍是 usageLimited，不以產品 qwen tokens 代替。

## 下一個必要 gate

P3-A 在這裡停止。下一步由 GPT6 審查 implementation freeze：確認三路 transport、共同歷史、budget、checkpoint、
worker isolation 與 claim boundary；審查通過後才可另行放行 P3-B developer smoke。沒有讀 confirmation，沒有碰正式 DB。
