# P4 B 隔離 Ollama 身份預檢：非 B 零生成結果

判定：**私有同模型 render/tokenize 可行；B token hard-cap 仍 REVIEW_REQUIRED，B 不可 Send。** 此批只處理 `research/p4_b_isolated_ollama_identity_preflight_2026-10-25.md` 的身份隔離可行性，沒有碰 A/B 題、gold、作者評分、真 generation、Safari 或正式 DB。

## 可重核的 before → after

- Before：P2 compact 後的 M21 請求會到 inner ledger gate，但目前 counter 是任意整數 callback；實際產品 LeftBrain URL 仍固定共用 `localhost:11434/v1`。共用 daemon 的 render→tokenize→generate 不是同一身份的原子操作。此前 36-token 非 B fixture 只證共用服務工具通路。
- After：在 `/tmp/uruha-p4-b-ollama.72H90N`（0700）建立**僅供本批**的私有 `OLLAMA_MODELS`。用 `cp -c` 複製一份 858-byte manifest 和其引用的 5 blobs；4,683,073,952-byte GGUF 的來源／副本 inode 分別 5586332／49796930、links 各 1，私有樹無 symlink／多重 hardlink。manifest、GGUF、template、system、license、config 六個檔案 SHA 都與 manifest 指定 digest 相符。`du` 對 clone 的邏輯讀數為 4.4G；前後 `df -h` 可用量均顯示 116GiB，但沒有 byte-exact 的增量測量，不宣稱零磁碟成本。
- 本機 binary `/Applications/Ollama.app/Contents/Resources/ollama` SHA-256 `bba8b79eac84ab092b9568978c1116e6c950eda588961b14d8608ac683a2af0b`，私有 daemon `/api/version` 為 0.34.4；`/api/tags` 唯一模型 `qwen2.5:7b` digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。啟動 env 有 `OLLAMA_HOST=127.0.0.1:11455`、私有 `OLLAMA_MODELS`、`OLLAMA_NO_CLOUD=1`、`OLLAMA_MAX_LOADED_MODELS=1`、`OLLAMA_NUM_PARALLEL=1`、`OLLAMA_MAX_QUEUE=0`。daemon PID 3998；其子 runner PID 4093 在 `127.0.0.1:51234`，從私有 GGUF 路徑載入，使用 Go/template 路（`OLLAMA_GO_TEMPLATE:true`、runner `--no-jinja --chat-template chatml`）。這是本次觀察，不是固定 port contract。
- 非 B 兩訊息固定句 `Tokenizer fixture only.` 帶 P2 的 JSON Schema shape，以 OpenAI 相容 `_debug_render_only=true` 對私有 daemon 做 3 次診斷 POST，另對共用 daemon 做 1 次相同診斷 POST；私有 1 次 runner `/tokenize` 診斷 POST。兩邊 rendered prompt SHA 均為 `6b22ff40dad08610b87219952f758fa0c314026cce14abb6bc8a4adfd62deba4`（200 characters）；私有 runner `add_special=false, parse_special=true` 為 **37 tokens**。debug reply content 空、usage 0，這是 render-only protocol，不是「prompt_tokens=0」或真正生成 parity。此批生成完成數 **0**，HTTP 診斷呼叫不被隱藏。
- [Ollama v0.34.4 原始碼](https://raw.githubusercontent.com/ollama/ollama/v0.34.4/server/routes.go) 的 ChatHandler 對 debug render 在 Completion/Chat 前返回；這支持「本次診斷請求沒有走生成」的路由解讀，仍以實際空 content／0 usage 和本次模型紀錄交叉核對。
- 私有 daemon 與 runner 已正常停止；11455／51234 不再 listening。共用 11434 仍由原 PID 1529 listening，本批未停止／重配共用服務。私有 clone 暫留於上述精確 `/tmp` root 供本批可重核測試，未修改 repository 外其他資料。

## 可重現 probe 與續作核對（同日，仍非 B）

前一段 37 tokens 的 fixture system 句帶有額外 `Private constraints`；新 `p4_b_isolated_ollama_identity_probe.py` 刻意使用較短固定句，**不得把兩者混成相同輸入**。新 probe 只接受私有 0700 clone、六檔 digest／獨立 inode、指定 daemon 與其子 runner 的 PID／loopback port／GGUF 路徑、版本與 binary SHA；只使用固定無敏感句的 render-only 診斷和 runner `/tokenize`。`test_p4_b_isolated_ollama_identity_probe.py` **17/17** 零網路測試通過，涵蓋無效 clone、共享端點、HTTP 回應、執行檔 SHA 與前後身份漂移時的預拒或 fail-closed；加上相鄰 gate／P2 的正確 project Python，**63/63 passed**。這是契約證據，不是真 B token 證據。錯用系統 Python 3.12 曾得 61 passed／1 failed（缺 `colorama`），改回既有 `.venv/product_checks/bin/python` 後全部通過；未因此安裝或改套件。

用同一私有 clone、絕對路徑 daemon binary 再啟動：daemon PID 23695／11455，子 runner PID 23744／55132，Ollama 0.34.4。先用 1 次固定句 render-only 診斷載入 runner（空 content、usage 0；這不是模型生成），再跑 probe 的 5 次診斷 HTTP（version、tags、show、render-only、tokenize）：`request_sha256=029f6ab6361a3955ce0e519fe77144634b4d6e004d20dc61d72c178edf1d8e2b`、rendered 180 chars／SHA `b7daaa86448a80fdbd2c43903f7100749d61bd45aedfd562317575bf896de7e0`、**35 tokens**、0 generated completions。probe 回傳 `mechanical_identity_pass_not_b_authorization`、`b_prompt_upper_bound_proven=false`、`b_safari_send_authorized=false`；結果 JSON 不包含完整 rendered prompt 或回覆，原始固定 fixture 字串仍在程式碼中。兩個執行檔 SHA 分別為 daemon `bba8b79eac84ab092b9568978c1116e6c950eda588961b14d8608ac683a2af0b`、runner `e1cf69803dac46fc5beb750ae77f3824cf4aa42bd8f636fc9d613039baf959e2`；獨立只讀審查後把 runner SHA 也改為 frozen 比對，並用同一存活 PID 的 `_process_identity` 實機核對通過。這個最後的窄核不是重跑整個 probe，不能包裝成一個原子交易。

第二次私有 daemon／runner 已停止，11455／55132 均無 listener；共用 11434 仍為原 PID 1529。此續作額外 **6 個私有 HTTP 診斷呼叫、0 真模型 completion、0 A/B 問題、0 Safari、0 正式 DB**；加上上一段的私有 4、共用 1，整批已知 HTTP 診斷合計私有 10、共用 1。不能把 `debug usage=0` 說成「token 成本 0」，也不能把 model load／disk/CPU 成本抹掉。

**凍結計畫偏差／未測：**原計畫寫「1 個私有 daemon」，本次為手動可行性與自動 probe 先後啟動 **2 次**（從未並行）；若該上限解作整批總啟動數，便已超過，不能事後把凍結文字改成「同時 1 個」。原計畫要求保存耗時，此批沒有可靠 stopwatch／機器可重算的端到端秒數，故不報假的延遲。這兩點使「完全按預定資源／量測驗收」不成立，但不推翻已觀察到的私有 render/tokenize 可行性；後續若要以它放行任何 B gate，必須另訂前瞻契約並補齊。

## 限制與下一個放行條件

這證明新私有 runner 可從私有 model store 渲染與計數同一**無敏感 fixture**，且與共用服務渲染 hash 一致；**不**證明 B 實際 transformed prompt 的上界，亦未核同 shape 真 provider usage parity。產品 child 目前仍使用共用 11434；僅有 private oracle 而真請求發往共享端點仍會 TOCTOU。即使之後綁到同一私有 daemon，跨 HTTP 也只是合作式隔離，不能假稱對同帳號惡意改檔者的原子硬保證。

下一個必要工程是讓已驗證的 private daemon/runner 身份與**真正 target client endpoint** fail-closed 綁定，先以非 B 同 shape、明確預算的真 provider conformance 比較 tokenizer 與 usage；然後才可能在唯一已授權 B 輪的送前 gate 計數其實際 transformed request。獨立仍需 A 作者三項評分與真 A on-only PASS、Web child/terminal gate、非 B Safari 20 秒與晚到抑制演練。這些都未過，故 B 常閉、0 Safari Send、P4/長期 Goal 未完成。
