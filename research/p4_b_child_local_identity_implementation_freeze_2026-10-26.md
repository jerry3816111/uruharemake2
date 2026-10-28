# P4 B child-local identity：改碼前任務卡（待審）

狀態：**跨代理只讀審查 GO scoped 產品改碼與 fake-only 驗收；未授權立即實跑 one-use harness、第四次真 Ollama／B Send。** 這不是獨立真人或跨機器審查。設計基準 `research/p4_b_child_local_identity_adapter_design_2026-10-26.md` 與唯讀 before `analysis/p4_b_source_closure_inventory_2026-10-26.md` 不改。目標只修第三次真私有 zero-turn 在 Web import 前遇到的 sandbox `/bin/ps` 身份阻擋，同時保留舊的證據欄位及安全邊界；不把合成 probe PASS 推論成真 Ollama PASS。

## 唯一可歸因變因與 before

變因：B-only 身份觀察從 child sandbox 裡的 `ps` 依賴換成 raw OS process observation，並以 operator→descriptor→controller→receipt→child 的同代次見證鏈連結。為讓新 observer 有可信來源，descriptor/receipt schema 與 safety-critical source SHA 同步遷移；不變的是 model/runner binary SHA、model-store 雙掃、同 ledger／M21 admission、zero fallback、資源與產品回覆路徑。

Before：第三次真零輪 child 已通過雙 argv `_child_context`，卻在 `_inspect_live_identity → _process_start` 的 sandbox `/bin/ps lstart` EPERM，0 Web ready／0 B Send、總 262.7400 秒。綁定函式還直接 `/bin/ps -wwE` 並間接 `/bin/ps -ww`。合成 one-use probe 在同類 profile 有九欄正測＋真負控 PASS（active 0.332843 秒），但不是 Ollama。現 `B_COMMITTED_SOURCES` 6 檔、child receipt 5 檔；至少 7 個現有零輪安全關鍵檔未綁。每 create 四次約 4.683GB SHA＝至少 18.73GB 邏輯讀，cached 四次 9.301121 秒只是非 Web。

## 凍結實作範圍

- 允許產品檔：`p4_b_private_zero_turn_operator.py`（首次 raw/argv 捕獲、descriptor v2）、`p4_preference_fallback_detached_control.py`（descriptor v2 解析/逐字比對、source snapshot、receipt 發行）、`uruha_p4_b_private_endpoint_binding.py`（binding/receipt v4、B-only observer 與舊身份/模型 SHA 保持）、`uruha_p4_b_private_child_bootstrap.py`（新欄重建）、新 `uruha_p4_b_child_local_identity.py`（純 B 用 raw libproc/procargs/lsof；不匯入一次性合成 probe）。
- 允許測試與非產品驗收檔：`test_p4_b_private_zero_turn_operator.py`、`test_p4_b_private_controller_seam.py`、`test_p4_b_private_endpoint_binding.py`、`test_p4_b_private_child_bootstrap.py`、`test_p4_b_private_child_chain_zero_provider.py`、新 `test_p4_b_child_local_identity.py`、獨立 one-use `p4_b_child_local_identity_sandbox_preflight.py` 與其 fake-only `test_p4_b_child_local_identity_sandbox_preflight.py`、事前 source-input-oracle SHA freeze；再改本卡/結果與完成後產品 source SHA。preflight 只能呼叫新 adapter 的 raw OS 觀察 primitive 對自建 Python 程序，不得宣稱它通過 real Ollama 的全部 semantic flags/model SHA。既有 `p4_b_isolated_ollama_identity_probe.py`、`uruha_p4_b_resource_gate.py`、四個 controller helper 不改行為，只納入完整 source lock。
- 不碰原第三次 run/root、已凍結 source/題、共享 11434、正式 DB、VRM、認知模組、prompt、模型參數、ledger gate/限額、baseline、gold；不修改 synthetic probe source/結果，不另造新的 M 編號。

## 必須先失敗閉鎖的契約

1. Operator 在啟 daemon 前先核自身來源檔與 committed HEAD／事前 frozen SHA 一致，descriptor 前再核未漂移；不可僅在 descriptor 時讀新檔 SHA 冒充已載入程式來源（這仍是 cooperative provenance，非 code signing）。它在 daemon 與 runner**首次識別時**各以 raw-before/舊 `ps`+唯一 listener+argv/env/raw-after 夾住 PID，原始兩端 raw `(pid,ppid,start_sec,usec)` 完全一致。當下按事前固定 canonical JSON 演算法算 executable／完整 argv digest；descriptor v2 保存 raw、digest、operator source SHA、原 `lstart` 字串及既有端點。不能用看到新結果才改 parser/expected flags。
2. Controller 讀 descriptor v2，自己外部重讀 raw/ps/lsof，逐字比對 operator raw/digest/PPID/ports；不接受僅同秒 `lstart` 相等或自捕新 raw。receipt v4 將同一 raw/digest/source SHA 固定；child bootstrap 核 receipt exact fields/0600/digest/source/time，再用同一值建 binding。
3. Child 每次 live identity 都用 raw-before→完整 argv/daemon env/唯一 loopback owner/binary+model SHA→raw-after；先後 raw 與 receipt 完全一致，runner PPID=daemon PID，真 Ollama flags/model path/full argv digest 不可少。`exec_path` 與 `argv[0]` 分開比，不能沿用合成 `argc<=8` 或強制兩者字串相等。argv/env 不落一般 trace，查不到任何欄即送前拒；**只要求 B pre-Web live-identity／pre-create revalidation 可達路徑無 `/bin/ps`**，不冒稱整個 Web child 其他功能均無 ps。原 `_model_store` before/after 與每 create 前後雙 revalidation 保留。
4. B zero-turn safety-critical allowlist 需對 operator、controller 四 helper、identity/model SHA helper、resource gate、新 adapter、已有六檔逐函式確認 `bound／not applicable+reason`，缺關鍵來源=0；controller committed snapshot 與 child receipt 的適用來源 SHA 均要有改檔/未提交/中途漂移負控。zero-turn 關閉不等於 B Send：compact planner schema、Brain native/RightBrain 和 product overlays 尚另需全入口 source closure。

## 驗收順序、停損與成本

1. 先在 fake OS/process 下紅綠：同秒 PID reuse、raw sec/usec/PPID/argv/exec/env duplicate or wrong、runner flags/model、listener owner 非唯一、binary/model SHA drift、descriptor/receipt/source drift、child 中途換代、M21/ledger 前後 gate、無 `ps` fallback；每例都要證明 provider 0 call。聚焦命令固定為 `.venv/product_checks/bin/python -m pytest -q test_p4_b_private_zero_turn_operator.py test_p4_b_private_controller_seam.py test_p4_b_private_endpoint_binding.py test_p4_b_private_child_bootstrap.py test_p4_b_private_child_chain_zero_provider.py test_p4_b_child_local_identity.py test_p4_b_child_local_identity_sandbox_preflight.py`；再跑受影響 controller/bootstrap/ledger 相鄰回歸、compile、`git diff --check`，不因聚焦通過把其他層當 PASS。
2. 只在獨立 source-only review 後固定新 adapter、**獨立 one-use harness/fixture**、同類 profile、input/oracle 與成功/失敗欄位 SHA，提交推 PR #435 exact head；才准執行一次 `.venv/product_checks/bin/python p4_b_child_local_identity_sandbox_preflight.py --execute`。harness 自建與上次 probe **不同且獨立**的兩個合成 Python listener，讓新 adapter 的 raw OS 觀察 primitive 在 actual-script、同 sandbox／同 observer PID 上讀前後變化；每欄固定布林、原始 shell exit、active/total wall、cleanup 與正負矩陣保存於新 `analysis/` 結果，不存完整 argv/env。限制 0 模型 clone/HTTP、0 Web/B Send、30 秒 active＋最多 10 秒清理、精確 own-PID/PGID cleanup，失敗保留不換條件重跑。這**只驗新 primitive 的真沙盒可見性**，不算真 Ollama semantic flags、model SHA 或完整產品 adapter PASS。
3. 即使上述全部過，也**不能直接第四次模型 run**。另由重大設計審查核：真 Ollama argv/env/runner 行為的可驗預期、同代次 source/receipt、至少 18.73GB/輪 SHA 與完整啟動成本、20GiB/1GiB 私有資源門檻、20 秒 Safari 尚未成立、exact cleanup。若無可信路徑，B 繼續 `REVIEW_REQUIRED`。任何真零輪的新失敗都保留原件，不同 root 或弱化 gate 不能當 retry。

成功僅稱 B child-local 身份替代在指定層有證據；不稱人類反應方程式已證、Uruha 品質改善、B token upper bound、A/B 公平比較、≤20 秒或產品/VRM/Function Calling 完成。測試數量、文件與 PR 不算認知能力提升。
