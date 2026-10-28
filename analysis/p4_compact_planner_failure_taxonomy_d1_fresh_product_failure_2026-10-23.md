# P4 compact planner taxonomy：d1 真 Safari 路由到達，但隔離與可見品質失敗

日期 2026-10-23。事前 source-only d1／計畫／5 SHA 及零模型路由 test 先於本次模型生成，以 `dcc6cd7` 推既有 PR #435；作者題非 formal holdout，與 c0/d0 不比較格式失敗率。零模型首次 test 因期待不存在的 M18 key 而失敗，僅修 test 斷言後聚焦＋compact **16/16** 通過；真 Web 所有 overlay 的路由仍以這輪另驗。d0 tick1/fast path 與 c0 compact `unexpected fields` 舊判均不改、不重播。

## 唯一新輪及 hard gate

新 0700 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-fag62_ba`，固定 7925／control／run `2277522b1dd68630`／PID 55437；官方 Chroma ONNX archive SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`，與來源獨立 inode、私有 cache，離線預熱 384 維 finite／0 Python socket attempts。same-final-PID HTTP ready，模型 `/api/tags` 前後 digest 均 `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。新 Safari tab 52→53、session `20261023_215813_ee481478`、未按 Reset；事前 `memory_db` embeddings/queue 0/0、`session_db` 無檔、JSONL 空。只有這個私有 root 接收該作者題，正式 DB 未接觸。

21:58:59 CST 保存不可覆寫 Tpre 複本，並在按 Send 前對**同一複本**執行 `jq -e`，確實通過同 PID/session、`memory_db`、reset0/tick0/finish0、ready；這改善了 d0「未讀收據就送」的執行錯誤。Safari click 呼叫的時間括號是 epoch ms `1792763952287`→`1792763952426`（21:59:12 CST 附近），由 Tpre 檔 mtime 到 click-call 約 **13–14 秒**，超過 d1 事前 ≤10 秒目標；檔案 mtime 只到秒，不能宣稱精確的 Tpre→實際 click 間隔。click 呼叫後 Safari UI 顯示 autonomous tick1；回覆完成後保存的 Tpost 為同 PID/session/DB、reset0、finish1，**tick1 而非凍結的 tick0**。tick 發生在 click 之前或之後，既有證據不能判定。故 d1 產品診斷 **strict FAIL**；不能因 Tpre 過、背景 `writes=0` 或模型已執行而追認為合格隔離。外部 event-published receipt 本就不是 click-time 原子取樣，這輪更有明確 Tpost 反證。沒有重送 d1 或替換 root。

## Off-gate 觀察：有到 planner，但沒有證明格式子類

Safari User：「表の列名を三つ整理した。今は一言だけ励まして。」；泡泡與私有 JSONL 最終同為「しんどいなら、今日は無理すんな。」短日文，但沒有承接明說的鼓勵與可觀察的列名整理，反而轉向使用者未提供的辛苦／休息情境；事前 visible contract **FAIL**，不能把這稱為被理解。原生 graph 現場展開 `compact_general_plan_p2`，顯示 attempted/completed true、3 candidates；同輪 `direct_reply_act_planner_handoff_p4` 是 `control_no_handoff`、`actual_route=full_planner`、`planner_prompt_injected=false`，M29 阻止字面投影接管／M33 不接管，M21 full planner 8.0444 秒。這與 d0 的 0 generation fast path 不同，但因 tick hard gate 失敗，只能報 off-gate 路由觀察。

本次 qwen2.5:7b 呼叫成功，compact strict parser `completed=true`／3 candidates，**沒有格式錯誤**，所以新 taxonomy 沒有在真模型失敗路徑受測，屬 `non_reproduction`；不能反推 c0 是缺欄或多欄。當輪 scoped ledger 1 generation、1039 prompt＋72 completion＝**1111 provider tokens**、11 vector operations、0 failed calls，M19 user wait 10.5286 秒≤20；startup/background 不在此 token 帳本。私有 DB 最後 1 embedding／1 queue record，對應此輪 episode，profile 寫入未作為本報告正面主張。

進一步的同輪 trace 讓下一個失敗位置可歸因：選中核心 `core_message_jp=頑張って！`；表面原句成了「頑張って！。そのくらいでいいだろ。」；`visible_language_guard.initial_rejection_reasons=[malformed_japanese_punctuation]`，`repair_action=safe_japanese_persona_fallback`，於是最終變成「しんどいなら、今日は無理すんな。」。M39 接受的是換句後的表面；它沒有驗出相對源句的鼓勵行動遺失。這說明**在這個 off-gate 輪次**，有效候選並未因 compact 格式拒絕，反而是表面標點與 fallback 改壞可見行動；不推論 tick 造成表面錯誤，也不宣稱它是所有類似輸入的普遍原因。

事後唯讀 source 核對：`uruha_brain_mac.py` 的 `_speech_plan_variants` 在 `direct_chat_answer` 預設分支直接拼接 `f"{core}。そのくらいでいいだろ。"`，沒有處理核心已含句末 `！`；語言 guard 明確拒絕 `！。`，`support` 場景的安全 fallback 固定為上述休息句。當輪 `contextual_expression_commit_p2` 為 null，M39 也沒有選定 policy ID 可核對原 reply act。這些是對已保存 trace 的程式路徑定位，不升格為合格產品輪次或普遍因果效果。

私有原件 SHA-256：Tpre `64180b90be26c5c47d7cac9e333cc70100a82c6e1b55f5da351078b791fd982c`；Tpost `6387cb26ebcf60ce9acac55a94c9221743a96a8832bd0e1ee052f0acc3a67710`；單行 JSONL `d02d8da3fc3da72c20b1e25a4d1579f723fba1a04e422fe2b1820b758ea41868`；ready `18d679885b833e16c0bd120decdc9d4956c388972983124a9138be29b3fd4083`；planned stop `b28b08abe1fd54dc05a52be5e94146d5d2c2bdc0d8c1335ee76c519eddee4c88`。原生 Safari AX／圖現場核對但沒有可重核落盤 PNG/AX，saved-native-visual 仍 FAIL。僅新 tab 53→52 已關，exact PID planned stop 顯示退出／7925 vacant；無部署。

## 下一個必要設計審查

把兩個問題分開，不合修：一是 event-published Tpre 與 Safari click 之間的背景 tick race／過長時窗，若要強產品驗收需新前瞻、只讀的同鎖 live-state barrier 或等價可驗證 admission 收據，不能停 scheduler、降低 c/d1 舊 gate 或重播曝光題；二是日文標點畸形後 fallback 丟失已選鼓勵行動，需新的 source-disjoint 反例、保護負控和單一「語意保留的表面修復／拒絕」設計，而非把任意鼓勵詞硬碼到回覆。兩者都要先 zero-model、再隔離真輪；若無法做到，保留 `REVIEW_REQUIRED`。這些負結果不能支持同模型 certificate 優勢、人評被理解感、正式 temporal holdout 或完整人類反應方程式。
