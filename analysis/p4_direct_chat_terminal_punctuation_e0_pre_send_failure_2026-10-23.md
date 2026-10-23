# P4 句末標點 e0：零模型修正成立，真 Safari 在 Send 前停止

日期 2026-10-23。source-only 計畫／作者 e0 題／前置 SHA 在 `77434bd`，獨立只讀審查提出的路由 go/no-go 以前瞻 amendment `72d6b0d` 另存，產品 code/test/11 SHA 在 `b3c0927`，皆先於本次 Safari 推 PR #435。原 d1/c0/d0 判定不改、不重播；e0 也是 developer-authored 診斷、非正式 holdout。

## 已取得的下層證據

唯一產品 code 變因是 `uruha_brain_mac.py` 的 legacy `direct_chat_answer` 尾句接合：core 已以 `。！？` 結束時不再重插 `。`。改前同一測試 4/8 FAIL，其中三個 raw variant 多標點；測試 harness 在 code 前已修成完整 `run_turn_debug` 中使用真 RightBrain。改後聚焦 **8/8**、受影響 guard/P2/direct-act/compact 合併 **104/104**，9 個既有警告。隔離 fake LeftBrain client 一次能走 M29→full compact→`support` P2 排除→真 `_speech_plan_variants`；注入 core `よくやった！` 時 raw variant、final、episode 均為「よくやった！そのくらいでいいだろ。」，guard `repair_action=none`／拒絕理由空。這是零真 provider call 的機制及接線證據；注入句沒有提使用者描き直した図，固定尾句也可能顯得敷衍，**不得**稱新題可見品質已過。

## 唯一新產品準備與嚴格失敗

新 0700 私有 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-oc8x6u_9`、7926／control／run `f0d5986b30e5bdf2`／PID61968。產品 SHA **11/11**、本機 `qwen2.5:7b` digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`；官方 ONNX archive SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 的私有副本 inode 獨立，離線預熱 384 維 finite／0 Python socket attempts。服務 same-final-PID HTTP ready。Safari 僅新 tab 52→53，session `20261023_223430_becf86e2`，e0 原句只預填，沒有按 Reset 或 Send。

22:35:40 CST 保存的 Tpre 複本對同 PID/session、`memory_db`、reset0、finish0、ready 均符合，但 `autonomous_tick_index=1`，**不是**凍結的 tick0；ready file mtime 到 Tpre mtime 約 62 秒。Safari 預填／未按 Send 屬現場操作觀察，沒有另存可重核的原生 PNG/AX 或獨立 click timestamp。依 pre-send hard gate 立即停止：**0 user turn、0 真模型 user-turn generation、0 可見回覆**，不改題、不重送或換 root；無 Tpost，沒有取得標點機制的真模型行使或可見品質結果。Tpre SHA-256 `e1c7508860f71d5b3eccc5737ecaf05195591424f2fb7aa5eb01886c12d521da`；ready `d6233bf3c887fccab34207e716294ab272c25ca511662fa1b14b13d24cc8249d`；planned stop `25dbafa7873342f838c62b7e474ed59d83a79d0b8e40a027b17139c61fc0c05b`。私有 Web conversation JSONL/session DB 無檔，memory embeddings/queue 0/0；本次 tab 53→52 已關、exact PID exited／7926 vacant。未送訊，無原生對話 graph/PNG/AX；saved-native-visual、真產品品質及成本比較均未驗收。正式 DB、原始 dirty checkout、無關 output 未碰。

## 不可外推與下一步

本項現狀是 **zero-model mechanism PASS、Safari product strict FAIL（pre-send）**，不是「標點已在真 Web 修好」，也不是同模型優勢、人評被理解感或人類反應方程式的證明。d0/e0 都在 pre-send tick1，d1 則 Tpre tick0/Tpost tick1；這表明原 event-published receipt 的 tick0 時窗對人工 Safari 準備脆弱，但不能推論 tick 導致先前錯誤回覆。下一個必要單變因是**驗收測量／admission**：前瞻設計同鎖的 per-turn 入口狀態與背景事件歸因，區分「Send 前已有無寫入的 idle tick」與「生成期間有競態」，以可驗證的狀態／寫入證據取代過去對 tick0 的代理；舊 c/d/e0 gate 與 FAIL 原樣保留。不能僅停止 scheduler、提高 idle 門檻或事後允許 tick1 追認本題。完成測量工具後須新 source-disjoint 題再驗，仍要驗選中 core、真實 final、source/自然日文/人格、記憶、成本與 Safari 圖。
