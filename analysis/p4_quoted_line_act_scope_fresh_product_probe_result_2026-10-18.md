# P4 引述台詞 act-scope：前瞻 Safari 產品驗收

日期：2026-10-18。**整批 strict FAIL，原件保留，不重播八句改判。** 這是同團隊事前自編的開發探針，不是正式 temporal holdout、真人偏好或同模型強 LLM 對照。

## 凍結與執行界線

- 原九輪 T9 的錯答、T1 超時及其他失敗保持原判；本批用未曝光的八句，計畫和資料先以 `524e873` 凍結，opt-in 實作、相鄰測試與 13/13 product SHA 再以 `09ed473` 推既有 PR #435。首輪前重新核 SHA 13/13 OK；新聚焦＋相鄰零模型測試 35/35。這些不是 Safari 證據。
- 專用 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-1v5sxw95`。零輪 run `b84c220c8607b385`（PID 35972）同 PID HTTP 200 後 planned stop，然後明示建立唯一空 `user_profile` 並存 T0 完整內容快照。官方 Chroma ONNX archive 83,178,821 bytes，SHA256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`；獨立 inode、0600 私有副本，封鎖下載仍得 1×384 finite embedding，私有樹再次掃描 0 unsafe nodes。這是環境預檢，不計產品成功。
- 真 Safari session A：run `137c0067ca256250`、PID 37165、session `20261018_153439_ab62ff67`，T1–T4。T4 後 planned stop，PID 退出、7894 vacant；同一 DB restart。session B：run `bae85169d2cdf748`、PID 37814、session `20261018_153835_6b975430`，T5–T8。終局 planned stop、PID 退出、7894 vacant。兩個 session 的 `turn_index` 各從 1 開始；下表 T 是 raw JSONL 行序。
- 八句逐字各送一次、0 retry；Safari 當輪實際目視 user/bot 泡泡及下方 graph。8/8 Safari 泡泡＝raw `assistant_reply`＝runtime graph `UTTERANCE`。raw 原件 `web_logs/conversation.jsonl` SHA256 `5908bccccbfeeea5ee4aeb6be094ff174b5ab161c451ec4830b11b6575dbab1e`。T0–T8 九份 full profile 均 present、0 rows、同 digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；末次快照有 8 個不同 episode ID。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 未碰。

## 實際可見結果與圖／來源核對

| T | 當輪輸入 | Safari 實際回覆 | 等待 s | 事前 gate 核對 |
|---|---|---|---:|---|
| 1 | `展示会の受付場所は東側のロビーだよ。` | `了解しました` | 21.7664 | 建來源 episode；**>20.0s，性能 FAIL**。雖是日文，敬體也不合既有 casual／forbid-polite 人格目標。 |
| 2 | `さっき言った展示会の受付場所、覚えてる？` | `「展示会の受付場所は東側のロビーだよ」って言ってた。` | 2.8874 | 直接回憶 PASS：`explicit_episode_recall_focus_p4` 為 `selected_unique_user_episode`，source ID `01c70c2e-70ce-4af1-b34e-55940d015939`＝T1 episode、retrieved rank 3、原話與可見值一致。 |
| 3 | `「展示会の受付場所、覚えてる？」という台詞、口語として自然？` | `変ではないけど、前後の流れによっては少し唐突に聞こえるかも。` | 3.3927 | 引號內回憶未執行，回答外層自然度；scope/selected/final/graph 一致。 |
| 4 | `帰りのバスは最終便だよ。` | `帰りのバス、最終便か` | 10.5794 | 不同短期 episode 已建立；後按計畫重啟。 |
| 5 | `「私のこと、今も覚えてる？」って台詞、重すぎる？` | `少し重く聞こえるかも。相手との距離感次第だな。` | 2.9733 | 重啟後 scope 把引號當評價對象、外層為語氣問題；未用 T4 巴士記憶回答。 |
| 6 | `私のこと、今も覚えてる？` | `前に:「うちのこと、今も覚えてる？」って台詞、って言ってたろ。` | 3.1023 | **可見語義／自然度 FAIL**：selected `ask_miss_me`，最後卻把 T5 的引述諮詢當記憶答案，且 `前に:` 不自然。 |
| 7 | `「覚えてる？」は引用ね。で、私のことは今も覚えてる？` | `「ん、その話もう少し聞かせて」っていう記載なんだね。` | 3.1746 | **可見外層問句 FAIL**：未被新 scope 遮斷，selected `ask_miss_me`、core `少しくらいは思ってる`，但最終回覆沒有回答外層關係問句。 |
| 8 | `『展示会の受付場所、覚えてる？』という一文、短くできる？` | `短くするなら、分かりきった部分を省く。どこまで削れるかは前後次第だな。` | 3.5331 | scope/selected/final/graph 對上外層 `shorten`，沒有回答引號內回憶；但只給抽象建議，**沒有針對該句提出可用的精簡版本**，事前「至少有界建議」若按可執行改寫解讀則 FAIL，不能報成改寫品質 PASS。 |

T3/T5/T8 的 `quoted_line_act_scope_p4` 都是 `outer_edit_question_selected`，`quote_role=object_of_evaluation_not_current_request`，`prior_memory_anchor_answer_authorized=false`，`selected_intent=quoted_line_feedback`，`final_visible_surface_matches_contract=true`；graph 專用 receipt 與 raw 同值。T6/T7 不是 eligible：這是刻意保留外層真正關係問題的邊界，不代表舊回覆路徑已正確交付。

T8 的 `shorten` 回覆來自依 outer-act 類型選取的有界固定 core，沒有讀取引文後生成更短的台詞。故這輪可計「不誤執行引號內回憶、外層類型路由正確」，不可計「已完成針對該句的精簡改寫」。即使將泛泛方向寬判為 suggestion，整批 strict FAIL 與這個能力限制也不變。

## 失敗歸因、成本與下一步

T6 的舊 `memory_anchor` 取自 T5 `short_term` 的 `User:「私のこと、今も覚えてる？」って台詞...`，`memory_use_expected=true`；最後 deterministic surface 從該 anchor 生成 `前にUser:...`，而不是 selected core。日文 guard 只做 `localized_and_removed_nonproper_ascii`，留下 `前に:` 等殘片。T7 又從 T6 的壞回覆形成 `short_term` anchor，deterministic candidate 含 `-> Uru` trace 殘片；日文 guard 退成泛答，舊 frame shadow 把整輪錯視為引述報告而非引號外真問句，`frame_preserving_visible_repair_p4` 的 `quote_embedding_restore` 再包成「っていう記載」。局部 frame violation 清除卻沒有恢復外層問句。這顯示「選對路由／修掉局部 frame」不等於最終對使用者答對。不得將 T6/T7 算作新 scope 的正例，也不得默默擴大新 scope 去覆蓋真正問題。

八輪 user-wait 平均 6.42615 秒，最大 21.7664 秒，7/8 ≤20 秒；T1 比門檻多 1.7664 秒。新 scope 收據的 `model_call_added=false`（T3/T5/T8）；既有 M21 在 T1 有一次 attempted/completed，M31 在 T1/T4 記錄 completed，不能據此聲稱整條管線只有這些呼叫。可靠的整體 token ledger 不存在，總 token 記 `unavailable`，不得寫 0。0-turn 啟動／預熱和兩次約一分鐘的啟動成本與 user-wait 分開；本項不是成本優勢證據。

**結論**：有界引述台詞的當輪 act-scope 在三個新引述題中，內部 certificate 到最終可見文字維持一致；直接 episode 回憶也保留。整批因 T1 延遲／人格語氣、T6/T7 真關係問句最終答非所問，以及 T8 精簡交付不足，strict FAIL。下一個必要設計審查先拆開三個變因：舊 `short_term` anchor 對真正關係問句的答案權限與 selected→final 忠實度；有界精簡請求的可執行改寫；冷啟 T1 >20 秒及敬體語氣。每項需新資料／單變因／前瞻 gate，這八句不可重播追分。不能由此宣稱一般語用理解、被理解感、同模型優勢、真人等價、人類方程式或完整產品就緒。
