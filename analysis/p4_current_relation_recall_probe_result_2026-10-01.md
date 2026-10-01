# P4 現行產品來源歸屬探針：before 結果（2026-10-01）

## 證據身分與結論

這是事前凍結的**開發者自製診斷**，不是 sealed holdout、同模型強 LLM
比較或正式研究分數。來源／判準見
`research/p4_current_relation_recall_probe_plan_2026-10-01.md`、
`datasets/p4_current_relation_recall_probe_2026-10-01.json`、
`research/p4_current_relation_recall_probe_freeze_2026-10-01.json`；凍結 commit
`0be0d9e`。執行後沒有改題、改 rubric、重送任何一輪。隔離 JSONL 的 SHA-256
為 `f0db3982c06ef92ff61f737881369ab63ea09acccc069fa6fddd92e73acdfe37`。

**主判準 T10 strict FAIL。** T1 的持久 episode 寫了「紗枝は桑の葉茶が好きだ」，T10
確實重新檢索到且送入左腦，但最後只顯示「今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？」。
它既未明確否認「使用者自己最喜歡」，也沒有指出紗枝或先前來源；不能把這種泛用澄清當作
安全的完整回憶。系統有跨重啟儲存與檢索能力，**沒有在本案完成來源約束的答案選擇**。

## 真實輪次與資源

現行 `uruha_web_ui_product_p4_status_truth.py`、本機 Safari、launcher 建立的
`0700` 系統 temp 隔離 root：
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-c1_1cbls`。
原始 JSONL、Chroma DB 只留在該 root，**不提交正式記憶或原始對話**。第一段 session
`20261001_084417_84c4248d` 跑 T1–T5；舊 server PID `18067` 退出且 port 關閉後，
第二段用同 root／DB、不同 server PID `19005`、session
`20261001_085012_fdc7e34a` 跑 T6–T10。精確輸入與凍結資料逐筆相同，無 retry。

| 全局輪 | 可見回覆（原樣） | 使用者等候秒 | 觀察 |
| --- | --- | ---: | --- |
| T1 | 今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？ | 18.5698 | 朋友來源有入 episode，回覆未接住「記住說話者」 |
| T2 | 今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？ | 12.2115 | 無需求閒聊也被迫二選一 |
| T3 | 「麦芽茶は好きじゃない」っていう記載なんだね。 | 11.5045 | 「不是我的偏好」被改成「不喜歡」 |
| T4 | うちは今日、とてもリラックスできるゆっくりした曲を聴いたんだね。 | 12.8625 | 把使用者聽歌說成角色自己聽歌 |
| T5 | 散歩したいんだ。今家だよ | 12.4109 | 日文及主語含糊 |
| T6 | うちは今日は温かい麦茶が好きだね。 | 11.9124 | 再次把使用者偏好說成角色的第一人稱 |
| T7 | 先生は昨日ウーロン茶を飲んだね。 | 12.0674 | 一次性的老師事件未錯置成使用者 |
| T8 | ノートのことか。 | 11.6253 | 過度簡略 |
| T9 | 例句は引用だから) | 23.7394 | 混字／殘括號；唯一 `>20s` |
| T10 | 今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？ | 4.0368 | 未作來源歸屬回答，strict FAIL |

10/10 輪有最終可見文字、瀏覽器 runtime node graph 容器及 `delivery_complete=true`；
瀏覽器逐輪只核對圖存在，T10 才較細看圖節點，不能說已逐節點視覺審核十輪。
Chroma `episodic_memory` 有 10 筆 turn episode + 2 筆濃縮 summary；
十個 log 的 `last_saved_episode_id` 皆可在隔離 DB 對上。`user_profile` collection
為 0 筆：本案未見第三人稱／引用污染成 user profile，但 T6 正例偏好也未形成
typed profile，故不能宣稱偏好生命週期通過。十句都有日文文字，T9 明顯不自然，
T4／T6 角色歸屬錯；「自然日文 10/10」不成立。

總等候 `130.9405s`、平均 `13.0941s`、最大 `23.7394s`，9/10 輪符合
事前每輪 `≤20s` 成本目標。JSONL 沒有**全產品**逐輪 model call/token/成本完整欄位；
局部模組的 `model_call_count=0` 或 `prompt_tokens=0` 不等於全產品 0，故這三項
記為 `unavailable`，不得當成公平比較成本數據。先前規格寫「全 fresh」指每輪
從真實產品入口送新輸入、非 replay；此紀錄不證明每輪都呼叫了基礎模型。

## T10 最早可見失真

1. **持久性／檢索存在：** T1 `stored:episode:d2e89d5e-adea-4a9b-b6db-3b627be961b5`
   有原始 user 來源與日文 summary。T10 的 18 個 retrieved candidates 有它，
   score `0.3651`、rank `15/18`；五格 working memory 未選它，但
   `passed_to_leftbrain_trace_ids` 仍有它（direct episode channel）。所以不能簡化為
   「資料遺失」或「完全沒給左腦」。
2. **路由是第一個決定性錯位：** T10 `semantic_route_m22.selected_type=
   general_conversation`，唯一 evidence 是 `no_decisive_specialized_cue`；
   `typed_factual_grounding.reason=task_shape_not_factual_or_memory`。明確詢問
   「以前誰說最喜歡」沒有取得 factual/memory 任務約束，進入
   `adaptive_fast_path_m18` 的 `calibrate_need`。
3. **答案證據與表面再次錯位：** `memory_anchor` 只給
   `favorite_claim_unknown`、`source=profile`、`trace_id=null`，未綁 T1 紗枝。
   早期 deterministic candidate 只是「桑の葉茶が本命って記録はない。そこは勝手に足さない。」；
   它仍缺朋友來源，最後又被 M39 `selected_policy_not_realized` 改成固定澄清語，
   trace 標 `repaired_and_verified` 只表示符合該 policy regex，**不是語義正確**。

這些層級同時存在，**單加「以前」路由 cue 或只禁 M39 改字都不足以閉合**。
下一個必要介入應以「來源約束的過去陳述問答」為**單一整體介面變因**：明確判斷
是在問先前來源，僅使用當輪已取得且可追溯的持久 episode，綁定人物／值／引用
與原句，無唯一證據時誠實 abstain，並保證 final surface 不被一般 `calibrate_need`
模板覆蓋。先離線契約＋負反例，再用全新非本案的隔離多輪資料凍結後真實 Safari
驗收；本案已曝光，不可拿來當新 holdout 或改過再聲稱成功。

## 邊界

這裡沒有同模型強 LLM 對照、人評、正式 temporal holdout、VRM 人物實測或
Function Calling 一般動作驗收。原始 dirty checkout／正式私有 DB／無關
`output/graduate_application_report/` 未被本案修改。初始 import preflight
繼承既有不完全 sandbox 限制，不能宣稱整條 preflight 已寫入隔離。
