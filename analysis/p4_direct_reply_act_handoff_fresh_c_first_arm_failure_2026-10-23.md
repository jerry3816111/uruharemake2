# P4 direct-act handoff fresh c：第一臂真 Safari 失敗，批次停止

日期 2026-10-23。依先前已推 PR #435 的 `research/p4_direct_reply_act_handoff_fresh_c_plan_2026-10-23.md`／c0–c6 題本／11 檔 SHA 執行。**只送 c0 control 一次；1/9 arm-turn 已送，剩餘 8/9 未送；比較機制整批 strict FAIL，不能計算 certificate handoff 效果。** 舊 a0 不同模型和 b 送出前 reset66 失敗不改判、不重播。

## 實際可見結果與因果鏈

User 原文：「昼、試作品の寸法を一つずつ測った。今日はそこまで進めたから、今は一言だけ労って。」 Safari 最終泡泡／私有 JSONL `assistant_reply` 同為「ん、そこもう少しだけ聞かせて。」自然日文，但沒有交付明示的一句労い，c0 事前 visible contract **FAIL**。不能假設 User 真的疲累或需要更深的心理安慰。

同輪 `literal_topic_projection_m29` 准入 `brief_care`，`direct_reply_act_planner_handoff_p4` 是 `control_no_handoff`／`actual_route=full_planner`／`planner_prompt_injected=false`，這符合控制臂設定。Ollama `qwen2.5:7b` provider 呼叫本身回傳，真 ledger `leftbrain_general_plan` 1 generation、1051 prompt＋62 completion＝1113 tokens，無 transport error。然而 compact-plan 驗證 `completed=false`、candidate_count=0、failure_type=`ValueError`，M21 `error_fallback`／model_call_completed=false；stdout 原件第 7 行明確記 `P2 compact candidate has unexpected fields`。`uruha_compact_planner_p2.py` 只允許每個 candidate 恰為 `scene/core_message_jp/response_mode`，超出或缺欄位即拒絕；模型原始 JSON 未持久保存，故**不能指出具體哪個欄位**，也不能把這叫模型無法理解明示請求。fallback 先給「軽く返事する。そのくらいでいいだろ。」；M39 因 `external_reply_or_result` 進一步修成上述低壓追問。真 graph 顯示 handoff/control、M29 准入、full-planner 路由及最終 utterance；路由到 planner 不代表有效候選被採用。

## 隔離與可重核量測

- c0 control 固定埠 7915，送前空閒；新 launcher-owned 私有 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-jccaqeid`，官方 ONNX 獨立 inode archive SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`，本 root 封 socket 預熱 384 維 finite／0 socket attempts。run `7f0acab0b79d8c4a`，final PID `28695`，HTTP ready same PID；Safari 新 tab 52→53，URL `127.0.0.1:7915`、session `20261023_181124_4646b47c`，未按 Reset。
- 真送出前保存兩份獨立 0600 Tpre receipt，最後一份時刻 18:12:00 本地，SHA `d8f21a5a1fb21bed6107b3353e932552267603fc15e6641819172a0b5b421a67`：PID/session 相同、active `memory_db`、reset0/tick0/finish0，記憶 DB embeddings/queue 0/0，session DB／web log 空。Safari Send 隨後執行，但沒有獨立可持久的 click 時戳；故事前 Tpre→Send ≤10 秒只能依執行順序與 log/handler 時間近似，**不能標成精確測得 PASS**。
- 18:12:35 本地的獨立 Tpost SHA `217e84db882a74a72d4772035bfb9c3c6d7d6b03f4199607e4eb95113f3ff0e6`：同 PID/session、`memory_db`、reset0/tick0、finish1。當輪 `episodic_memory` 1 embedding、`user_profile` 0，session DB 無檔；私有 JSONL 一輪 1,063,673 bytes，SHA `8ab9f113bb2eb8f9f918ce023b8dd3fd2b5c94696ce0bfb661c6b3aab43f4f48`。真 ledger 12 scoped calls＝1 generation＋11 向量操作、0 failed calls、provider token 帳本完整；M19 user wait 10.3929 秒≤20。`qwen2.5:7b` 本機 `/api/tags` before/after digest 相同 `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。當輪 Tpre/Tpost tick0，**不是背景 tick 導致這次 fallback**；停止前更晚的 live receipt tick3 是輪次後 idle，不可拿它取代 Tpost。
- 當場 Safari AX／原生 node graph 和 screenshot 工具觀察到一輪、handoff/control 節點及真箭頭；原生 PNG/AX 沒有落到可重核檔案，完整產品 `saved-visual=FAIL`。只關本次新分頁 53→52；exact planned stop 同 PID 退出／7915 vacant。沒有把資料寫到正式 DB、沒有部署。原件 ready SHA `938c0c9f63e6ae05253989b99793191a5f745b56dccc5ce90d258f78db521159`，stop SHA `d462a7b233b5a896573c89d58c118ac147c3eb0aba0e5e915f384db83e956ea7`，stdout SHA `0965d18ddd72d0775e01400385f1f4cbd7dfe33318f8167a50f2427e07a0e17a`。

## 判定／下一個必要工作

這是**已保存的負結果**：輸入准入和產品模型呼叫有發生，但 compact-plan 格式拒絕使最終回覆未達明示行動；沒有 treatment 配對，不能聲稱 handoff 比 control 好／壞，也不能拿 53/53 零模型測試代替真生成。依 frozen「任一硬 gate 失敗即停」，c1 treatment 與其餘七臂一律不送。完整圖像交付另為 FAIL；真人感受與正式 holdout 仍無證據。

下一個單變因先做設計審查：在不保存 raw prompt/reply、不改人物/記憶/安全或壓低 baseline 的前提下，讓 compact planner 的**可診斷失敗類別**與有限結構修復可驗證；先定 source-disjoint 題、格式合法性／超欄位／少欄位／duplicate／truncation 的零模型反例及成本上限，再決定是否容許 deterministic normalization 或一次 fresh generation。不得重送 c0–c6 追分；若修復仍不穩，保留 `REVIEW_REQUIRED` 並評估停用該額外 planner seam，而非無限加規則。整個 UruhaBrain Goal 仍 active。
