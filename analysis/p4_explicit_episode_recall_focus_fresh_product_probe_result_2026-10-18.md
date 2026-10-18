# P4 顯性 episode 回憶焦點：九輪 Safari 首發結果

結論：**整批 strict FAIL**，不重播、改題或放寬門檻。狹義能力證據成立：T7 的正確原話在 retrieved candidate rank 8、未進一般 top-5，經專用 handoff 進入 selected core 與最終回覆；T5 正確但原已在 top-5，不計作 handoff 救回。這是同團隊預先凍結的產品開發題，不是獨立 holdout、同模型強 LLM 對照、人評或正式研究結論。前置計畫與題目見 `research/p4_explicit_episode_recall_focus_plan_2026-10-18.md`、`datasets/p4_explicit_episode_recall_focus_fresh_probe_2026-10-18.json`；資料 SHA `958dc9a748ba209522c49cd4e1bc0cda1c0b47bf7a26fd80d503d65b11b9cb37`。首輪前 code／依賴／資料已在 `a82d4de28f2d72db8bec799d8e7e12106d7e6ef0` 推 PR #435；產品 manifest 12/12、前實作 manifest 2/2 重驗 OK。

## 當輪可見結果

| 輪 | 使用者輸入 | Safari 最終泡泡 | 判定 |
|---|---|---|---|
| T1 | `集合する場所は市民ホールの南入口だよ。` | `了解した。南入口で待ち合わせだね。` | 來源建立；user wait **23.4546 秒 > 20 秒**，strict FAIL。 |
| T2 | `集合する時間は七時半だよ。` | `七時半に集合する時間だよ` | 時間來源建立；日文生硬。 |
| T3 | `友達が「集合場所を確認してね」と言った。` | `「友達が集合場所を確認した」っていう記載なんだね。` | 未觸發 focus，但把「請確認」錯述成「已確認」；語義忠實度失敗。 |
| T4 | `先輩は「集合時間も確認して」と言ってた。` | `先輩は集合時間も確認してと言っていたんだね。` | 引述干擾源；此後按計畫停機、同 DB 重啟。 |
| T5 | `さっき言った集合場所、覚えてる？` | `「集合する場所は市民ホールの南入口だよ」って言ってた。` | 正確引用 T1；focus `selected_unique_user_episode`，來源 rank 3／原已在 top-5，不能證明新增 handoff 的邊際作用。 |
| T6 | `私のこと、まだ覚えてる？` | `ん、その話もう少し聞かせて。` | focus 未接管、不捏造；回覆保守，但未正面回答關係問題。 |
| T7 | `前に言った集合時間、覚えてる？` | `「集合する時間は七時半だよ」って言ってた。` | 正確引用 T2；來源 rank 8／`selected=false`，一般工作記憶上限 5，該源 `passed_to_leftbrain` 僅見 `explicit_recall_focus_handoff`；新增有界 handoff 的產品層正例。 |
| T8 | `さっき言った駐輪場の色、覚えてる？` | `そこは今、確かには言えない。もう一度教えて。` | focus `unavailable`，候選 0，未虛構不存在的顏色。 |
| T9 | `「集合場所、覚えてる？」って台詞、変かな？` | `:さっき言った駐輪場の色、覚えてる？ -って話は拾ってる。そこ前提で返す。` | 新 focus 因引號未接管；**整體回覆仍離題且不自然**，拿上一輪駐輪場當本輪答案，產品 FAIL。 |

T5/T7 的 focus receipt、選中 core 和最終泡泡各自同源；T7 的 episode ID 為 `ba5e182b-d97a-45c2-9f78-3c7696b4aee4`，T5 為 `7661211f-cf37-4a6c-9e18-465ab7246688`。`prior_passed_channels` 在最後 receipt 重建時會包含已注入的 handoff，**不可按字面解成注入前的反事實**；T7 未經普通 top-5 的判定同時依 rank 8、`selected=false`、該源僅 handoff 的 provenance。兩輪的舊 `selected_plan.memory_anchor/post_check` 仍引用別的短期／episode 記憶並標 `did_reply_cover_focus=false`，是 pre-focus legacy 快照，和新 final 不一致；只能主張新 focus 憑證與最終輸出一致，不能說整張圖所有記憶節點一致。

## 證據層與隔離

- 零模型聚焦 **10/10**、相鄰 **45/45** 通過；這只證契約／回歸，不替代 Web 真輪。九輪各送一次、0 retry；真 Safari 泡泡、raw `assistant_reply`、node graph `utterance` payload **9/9 逐字一致**。T5/T7/T8 的 focus 節點與 UTTERANCE 已在 Safari 展開核對；T9 的錯誤也在 graph UTTERANCE 如實呈現，沒有把圖節點存在當內容正確。
- launcher-owned 0700 隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-d7ak5ika`。先做 0-turn same-PID HTTP ready／planned stop，官方 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 的私有 ONNX 副本在離線封網狀態預熱成功，並顯式建立空 profile；T0 profile 0 rows。第一 session `20261018_145630_66859b34` 跑 T1–T4，planned stop、原 PID 退出、port 7894 vacant；第二 session `20261018_150023_4ff20e57` 用同一 DB 跑 T5–T9，最後 planned stop、PID 28992 退出、port vacant。非外部部署。
- `evidence/profile-full-t0.json` 到 `profile-full-t9.json` 十份均 present、0 rows、全內容 SHA 同為 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；T9 snapshot 為九個不同 episode ID／0 profile rows。正式 DB、原始 dirty checkout、無關輸出未碰。
- user wait 逐輪 **23.4546／9.5996／9.8782／9.8801／2.9061／2.8332／2.9553／3.0872／3.6495 秒**；8/9 ≤20 秒，平均 7.5826 秒。T1 prewarm ready、cold init 0.3533 秒、cognition 20.7584 秒；本次不能把逾時歸因於 ONNX 下載，亦不能由這些分解確認 cognition 內部哪一步是根因。focus 契約新增模型呼叫 **0**；全管線可信 token 總量 unavailable，不是 0 token。
- raw 原件 `web_logs/conversation.jsonl` SHA-256：`3f646cf2618309099a35ad1926cdc4cdddbbe79c364a2090a13fe41ddc86965f`。兩個 Safari 測試分頁保留供查看，服務已停止，分頁可關閉。

## 失敗歸因與下一個必要交付

T9 的新 focus 為 null；只讀 trace 顯示舊 `_detect_relationship_intent` 將引號內 `覚えてる？` 當成當前 `ask_miss_me`，generic `_extract_actionable_memory_anchor` 取上一輪駐輪場 short-term，`_memory_grounded_reply` 產生可見離題句；當輪 `selected_source=deterministic`、無模型候選。這是舊引述範圍／記憶錨點問題，不是新 handoff 誤接管。T1 是另一個性能變因；T3 是第三者指令語義忠實度問題。它們不能在本卡私自合併成詞彙補丁或單一修正批。

下一步先就 T9 做**只讀設計審查與新工作卡**：把「引號內台詞是被討論的內容，不是當前回憶或關係請求」定成單一 act-scope 變因，前瞻新題／負控／成本與可改檔案先凍結，再實作；T1 冷啟動 cognition 成本、T3 引述指令忠實度分開處理。本批 strict FAIL 永久保留，不重送 T1–T9 改判。此批不證明任意長對話或跨語言回憶、felt-understanding、人類方程式、同模型 LLM 優勢；正式人評／temporal holdout／VRM 與 Function Calling 整合仍 pending，Goal 未完成。
