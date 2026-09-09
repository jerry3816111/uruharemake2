# GPT5 開發交接：P3-A，先把公平比較入口做對

2026-09-09。狀態：規格已定案；第一項工作是離線 harness 實作。由使用者切換開發模型後執行，
這份文件不會替他切換模型。規格不涉及在 UruhaBrain 內把 qwen 換成 GPT5。

## 接手先做

工作目錄必須是 `/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`。
先讀 AGENTS、CURRENT_TASK、本檔、`research/p3_product_comparison_spec_v1.md`、
`configs/p3_product_comparison_v1.json`。長期方向見 `LONG_TERM_GOAL.md`；歷史只追所需依賴。

```sh
git status --short --branch
python3 scripts/verify_p3_handoff.py
```

ready 代表可以開始 P3-A，**不代表可生成比較結果**。若 source/config/spec digest 不符，先報是哪個實際檔案
改了；不得重寫 lock 來綠燈。若已有自己的 WIP，保留並續作；不能還原、刪除或重做已完成階段。

## 你要交付的唯一成果

可以把「同一份完整對話歷史＋同一輸入」送入三個條件，並用 fake transport 證明資料與資源規則不會被繞過。
三個條件為 `full_history_direct`、`full_history_deliberate`、`product_system`。詳見規格第2節；不能改成
當輪-only baseline，也不能從舊 V2.14/M35 直接複製 runner 當新的完整產品入口。

當前已有什麼：

- 產品入口 `uruha_web_ui_product.py` 安裝 P1/P2 overlays，實際 brain 在 `uruha_brain_mac.py`。
- `run_product_restart_probe.py` 是環境隔離、真實 `run_turn_debug`、已有 graph 的參考，不是 P3 dataset 或 scorer。
- `uruha_compute_ledger.py` 已記錄 chat、native Ollama、Chroma。收尾 commit `34bef3d`；121項相關回歸通過，
  P2九輪與新記錄版逐字相同。報告見 `analysis/p3_complete_product_compute_accounting_acceptance_2026-09-09.md`。
- native M31 預設另用9b；P3 worker 必須在 import 前將它設為7b，並用 transport assertions 證明沒漏路徑。
- 既有來源／策略已定，不要為了讓未來題目通過修改它。P2五組只是已曝光 developer controls。

## 允許範圍與執行順序

只新增 `p3_product_comparison.py`、`run_p3_product_comparison.py`、`test_p3_product_comparison.py`，必要的
P3 worker helper 限一個、先在 task card 說明原因。可更新 CURRENT_TASK 與一份 P3-A acceptance；
`analysis/` 僅輸出具名 contract result／JUnit。禁止修改現有 brain、P1/P2、正式 M、人格、資料、規格／lock。

1. 在純標準庫 module 實作 config loader、generation view allowlist、budget state 與 manifest validation。
   不要在 module import 載入 Gradio／Torch／Ollama 或開 DB。預期 API 名稱已列在規格第6節。
2. 建立可注入 transport 與 worker factory 的三個 condition runners。fake callbacks 提供可識別的輸出與 usage，
   不能預設 system 勝出。baseline draft/critique/revise 的私有 scratch 不進共同可見歷史。
3. system worker 設定臨時 memory/adaptive/web-log 路徑、關 idle/prewarm，才 import product。每 case 獨立，
   case 內 restart 保留 DB；生成只有該時點已可見訊息。common prefix 先 freeze，再依 order 執行，之後追加 S reply。
4. 給所有 transport 加 shared budget／model assertions；timeout／unknown usage／超額均保存失敗，不自動retry。
   以 ledger 核對每一次呼叫，不能只在 CLI 外面記一筆「總計」。先以 fake 覆蓋兩種 transport；不在本階段打真模型。
5. 完成 `--mode contract` 和 `--mode preflight`；`--mode run` 缺 freeze/review release 時必須 0-call 拒絕。
   以不可覆寫的新 output path 留存結果。按規格處理 intent-only 中斷與完成 checkpoint；不建新 capability 平台。
6. 跑小測與相關回歸，做 diff review，更新 CURRENT_TASK 至 `REVIEW_REQUIRED`，提交／push既有分支並核對 PR435。
   然後通知使用者：「P3-A 完成，請切回 GPT6 做生成前審查。」不自行製作 confirmation、改閾值或開模型比較。

下面是要實作後才存在的 CLI／測試命令；目前不能說它們已經通過：

```sh
.venv/product_checks/bin/python -m pytest -q test_p3_product_comparison.py
.venv/product_checks/bin/python run_p3_product_comparison.py --mode contract --design configs/p3_product_comparison_v1.json --output /tmp/p3-a-new-contract.json
.venv/product_checks/bin/python -m pytest -q test_p3_complete_product_compute_accounting.py test_persona_policy_compute_seam_v1.py test_persona_policy_token_parity_v1.py
git diff --check
```

不要覆蓋 `/tmp/p3-a-new-contract.json`；若已存在，使用另一個尚未存在的具名 output。
產品 interpreter 是 `.venv/product_checks/bin/python`。系統 python3只用於純標準庫 preflight；不用全域 pip 補依賴。
若只改新 harness，121項既有完整回歸不必又跑；若碰現有入口或全域狀態則已超本項範圍，先留下原因進審查。

## 你必須證明的負案例

| 注入的錯誤 | 必須觀察到的結果 |
|---|---|
| baseline 漏前一個 session／混入 S 當輪回覆 | hash/view gate 拒絕，0 transport |
| case 附 future、family、expected answer 或 scorer 欄位 | generation view 不包含；無法驗證 allowlist 時拒絕 |
| 第二 case 拿到第一 case 的 memory/adaptive 檔 | worker isolation 拒絕 |
| native M31 偷用 qwen3.5:9b | model gate 拒絕，不能算同模型 |
| 第二／第三 call 重新獲得768 output上限 | shared remaining budget 拒絕 |
| context 超標／actual usage缺失／超額 | 明確 invalid；不以字數補 token，不截斷 |
| request timeout或intent-only中斷 | 保留 failure，重跑不再呼叫該 item |
| complete checkpoint、source或output被改 | digest mismatch；不覆寫原結果 |
| missing implementation/data/review release | `--mode run` 非零退出，attempts=0 |
| 匿名左右位置交換 | condition mapping正確、已給定數值差反號；不在本階段另寫自然語言評分器 |

## 工時與退出規則

本項 real generation budget = 0、付費呼叫 = 0，不下載模型。先做最小 view/budget 負測試，再接 worker。
每個 failure 最多兩次有因果證據的修正；仍無法解則輸出 `REVIEW_REQUIRED`，寫出實際反例、檔案、原因與最小提案。
純等待 Safari／真人不是本項工作，也不能藉機加報告網站。沒有新的問題時不要反覆重跑。

第一次 GPT5 接手結果需記：实际開發模型（可得才填）、起止時間、改動範圍、測試、重試／返工、使用者救援次數、
Codex token/usage（工具可得才填，不用產品 qwen tokens 代替）。這能評估交接可執行性；單次結果不能證明兩模型等效。

## 交回 GPT6 時用這個格式

「P3-A [通過／partial]；actual generation attempts [0]；負案例 [通過數／總數]；
source與共同歷史／budget的證據 [path]；剩餘問題 [精確項目]；commit／PR [實值]。
下一步是 GPT6 審查 implementation freeze，之後才可放行 developer smoke。未讀 confirmation、未碰正式 DB。」

GPT6 審查重點：所有生成路徑是否被限制；信息是否對稱；共同歷史定義是否真的實作；同預算是否逐輪累計；
原生 verifier/mock/真模型證據有無混淆；是否仍是現產品的對話機制；是否擅自多造工具。
