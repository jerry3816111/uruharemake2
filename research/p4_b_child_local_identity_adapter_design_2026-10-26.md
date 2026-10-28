# P4 B child-local 真 Ollama 身份契約：設計審查草案

狀態：**跨代理只讀複審 GO 作為 B-only 設計基準；尚未放行產品改碼、第四次真私有 zero-turn、B／Safari Send。** 此審查同屬 Codex 協作，不是獨立真人或跨機器驗證。上游唯一零模型替身輪次及其限制見 `analysis/p4_b_ps_free_identity_feasibility_result_2026-10-25.md`。第三次真 Ollama zero-turn 仍為 `REVIEW_REQUIRED`；此文件不追改三次舊結果或已曝光題目。

## 為什麼需要這一步

先前真 child 在 Web import 前的 live-identity `_process_start` 因 sandbox 內 `/bin/ps` EPERM 停止。這不是替換一個函式即可修好的問題：`uruha_p4_b_private_endpoint_binding.py` 的 `_inspect_live_identity` 在兩端使用 `/bin/ps lstart`，中間用 `/bin/ps -wwE` 看 daemon 環境，並間接呼叫 `p4_b_isolated_ollama_identity_probe._process_identity` 的兩次 `/bin/ps -ww`；後者還做 daemon／runner binary、model path、parent、flags、port owner 與 SHA 的驗證。零模型替身在同類真 sandbox 中以 libproc／`KERN_PROCARGS2`／`lsof` 看見九欄、完成同 observer 真終止負控，**只移除了「這些 API 對受控 Python 程序完全不可用」的不確定性**。它沒有測真 Ollama 的 argv、env、啟動代次或每次 create 成本。

此單元的唯一可歸因變因為 **B child 的 live process observation provider**：從 sandbox 內被拒的 `ps` 改為 child-local OS 觀察，但維持或加強所有原身份欄位、原兩次 pre-create revalidation、模型檔與 binary SHA、receipt 與資源 gate；不更改模型、生成、token 估計、B 題、prompt、分數、資料或 20 秒標準。若為保持來源綁定而新增 receipt/source-digest 欄，屬同一 observer 可信鏈的必要 schema 遷移，不藉此放寬安全。

## 設計候選與資料流

1. **operator 初次見證、descriptor v2、controller 與 receipt v4 連續綁定。** `p4_b_private_zero_turn_operator.py` 在 daemon 初次識別及 runner callback 初次識別時，各以 `raw-before → 既有 ps lstart/argv/env/listener 與 binary/model 檢查 → raw-after` 夾住精確 PID；raw `(pid, ppid, start_tvsec, start_tvusec)` 須不變，並於 descriptor v2 寫入 daemon／runner raw generation 與當時 OS 完整 argv/exec-path digest。動態 root/port 的**字串不用事前固定**，但解析、必要 flags、canonical digest 演算法與負控須在執行前凍結；operator 在捕獲當下計算 digest。Controller 不得自行挑一個新 raw 作為替代：它用外部 `ps lstart`／`ps -ww/-wwE`／`lsof` 和 raw API 重驗，且 raw、argv digest 必須與 operator descriptor v2 完全一致，才簽發一次性 0600 receipt v4。receipt 同時保留舊 `lstart` 字串作外部稽核，新增兩個 raw start tuple 與兩組 exact argv／exec-path digest；child 必須核對同一組。**不把秒級字串轉成微秒值，也不宣稱二者數值等價；只證它們在 operator→controller→child 的同一 raw generation 上連續觀察到。** 發生 PID 更換、讀取競態、缺欄或 root/descriptor/receipt 漂移就送前拒絕。
2. **B-only child observer。** 在已 source-bound 的 B 身份模組內建立窄觀察介面，或另建模組並把它加入 committed-source snapshot 與 receipt SHA；不得修改供其他路線使用的 generic `ps` helper 來偷換證據。對 real Ollama 分開讀 `libproc` raw start/PPID、`KERN_PROCARGS2` executable/argc/完整 argv 與**argv 後的環境區**、`lsof -t` 唯一 PID＋detail 127.0.0.1 listener。parser 必須支援真 runner 的長 flags，而非複製合成 probe 的 `argc<=8`、`exec_path==argv[0]` 假設；固定 byte/argc 上界、UTF-8／NUL／重複 key／截斷失敗閉鎖。argv/env 不進一般 trace 或回覆。
3. **逐欄保持舊語意。** daemon binary 路徑與 SHA、`serve`；runner binary 路徑與 SHA、daemon parent、`--model` 精確私有 GGUF、`--host 127.0.0.1`、`--port` 私有 runner port、`--offline`、`--no-jinja`、`--chat-template chatml`；daemon `OLLAMA_MODELS` 恰一個為私有 models、`OLLAMA_NO_CLOUD` 恰一個為 `1`；兩個 listener 都必須由各自 exact PID 唯一持有。synthetic probe 同時看 runner env 是探針的較強控制，**不能推論真 runner 有相同 env，也不以新增 runner env 要求偷改本單元原契約**。真正 Ollama 的完整 argv digest 在 operator 初次捕獲時形成，controller/child 逐字重驗；執行前須凍結語法、旗標唯一性與 parser，不靠既有報告中的某個動態字串作當輪真值。若觀察到不同組合，只能設計審查，不能在真 B 結果後放寬追綠。
4. **雙向 generation 夾取。** 每次 `_inspect_live_identity` 在任何檔案讀、argv/env 與 `lsof` 前後，都核兩個 `(pid,start sec,usec,ppid)`；中途變代、父子關係、listener 或模型檔 fingerprint 變動即拒。現有 `_model_store` before/after 兩次 SHA 與 binary SHA 暫不變。這是合作式檢查，不是 OS 原子快照；不能向同 uid 惡意換檔者承諾零 TOCTOU。每次 provider create 前後仍由同一 ledger 兩次重新驗證，任何失敗不可嘗試 fallback 到共用 11434。
5. **補齊本路徑 safety-critical source 可信鏈。** 現在 `p4_preference_fallback_detached_control.py` 的 `B_COMMITTED_SOURCES` 與 `private_child_source_digests()` 未包含 binding 實際執行的 `p4_b_isolated_ollama_identity_probe.py`，也未包含 child/bootstrap 與 ledger 實際使用的 `uruha_p4_b_resource_gate.py`；若新增 adapter，又會多一個被執行的模組。開始改碼前先做一次可查核的 B child/controller safety-critical import/call inventory：至少對上述兩個既有 helper、新 adapter、operator 自身及所有會決定 receipt、身份、M21 admission、pre/post-create 的實際程式列檔案、函式、用途、是否已受 committed snapshot＋receipt 雙重 SHA 綁定。缺的關鍵檔要進兩份 source lock；operator source 另在首次啟動前凍結 SHA，descriptor v2 帶其 SHA 供 controller 核對。若仍有 unbound 安全關鍵執行檔，preflight FAIL，不可聲稱「完整 source closure」或進真模型。receipt 版本、exact field set、controller snapshot、bootstrap reconstruction、錯誤負控同步更新；不只加欄、也不把 unrelated 全 repo 檔案納入本單元。

## 先驗驗收與停損（按順序）

| 層 | 必須看到的證據 | FAIL 分支 |
|---|---|---|
| Source/fake | operator descriptor v2→controller receipt v4→child raw/argv digest 同一見證鏈；同秒 PID 換代負控；B safety-critical call/import inventory 的未綁定數為 0；舊身份欄位逐項保持；沒有 sandbox child 可達的 `/bin/ps`；raw start／PPID／daemon env 恰一值／兩 listener owner／binary+model SHA／receipt replay/source drift/TOCTOU 各有反例；pre-create 前後仍同 ledger，0 provider call | `REVIEW_REQUIRED`，不啟真模型 |
| 真 sandbox、非 B | 新 adapter 的 actual-script 能在同 profile 核**受控程序**；若必須另啟替身，題與 oracle 前瞻凍結、不得把上次 one-use 輪次重跑；仍不等於真 Ollama | 缺欄或無法清理即停止 child-local |
| 真私有 Ollama zero-turn | 僅在獨立重大設計／source review、完整 source/模型/profile SHA freeze、exact PR head、private roots/ports/cleanup 與資源上限審核後，才**另行決定**是否授權新的 one-use run；同 PID bootstrap→Web ready→planned exact stop、0 B Send、無 shared 11434 fallback、全程時序及成本可核 | 任一 gate 失敗保留新 FAIL，不能同 root retry 或改弱 oracle |
| B Send 之前 | 真 transformed request 的同版 render/tokenize/usage 上界、首個 M21 only、≤2000 token 與 256 completion、非 B Safari click→terminal DOM 20 秒與 late-surface guard、A 作者真評與 A on-only PASS 全部各自通過 | B 常閉；零輪成功不等於可按 Send |

最小測試位置為現有 `test_p4_b_private_zero_turn_operator.py`／`test_p4_b_private_endpoint_binding.py`／`test_p4_b_private_child_bootstrap.py`／`test_p4_b_private_controller_seam.py`／`test_p4_b_private_child_chain_zero_provider.py` 與新 parser fake-only cases；先測精確負控，再跑相鄰回歸。要核 operator→descriptor→controller→receipt→child→Web/ledger 的全鏈，不能只 mock 第一個 `_process_start`。真輪必須保存退出碼、first-failure stage、exact PID/ports 收尾與事後共同服務不變；任何 cleanup review 不得稱 planned stop。

## 成本與無法宣稱的部分

目前每次 `_inspect_live_identity` 兩次 `_model_store`，每次 create 的 ledger admission 前後各重驗一次，即四次約 4.683 GB 模型 SHA，**至少約 18.73 GB 邏輯讀**；既有 cached 四次 read-only 實測 `9.301121s`，不包含 Web queue、模型生成、stream、TTS 或 Safari DOM。第三次真 zero-turn 總 `262.7400s` 主要包含約 240 秒 ready 等待，不能當 B 回覆 latency。此單元不改 SHA 次數或 cache；若身份 adapter 過了而 click→DOM 仍超 20 秒，應另立單變因的可撤銷成本設計（例如有同等時序與內容完整性證據的受控 attestation），**不能直接省掉 SHA**。本單元不能證明人類反應方程式、日文品質、Uruha 人格、VRM 或 Function Calling；它只避免私有 B 對照在身份未證時污染比較。

只讀複審先指出兩項阻擋：operator descriptor 若未存初次 raw 代次，同秒 PID 換代可能被 controller 誤接；以及 identity probe／resource gate 等實際安全關鍵來源未全在 B source lock。修訂上述 operator→descriptor→controller→receipt→child dual-anchor 與 source-inventory gate 後，複審才給**設計基準 GO**。下一步仍須把這份設計變成逐檔 implementation freeze、完成 source inventory，並另做改碼/驗收審查；設計 GO 本身不是產品能力或第四次模型授權。成本是否能通過 20 秒仍是一項未解硬 gate。
