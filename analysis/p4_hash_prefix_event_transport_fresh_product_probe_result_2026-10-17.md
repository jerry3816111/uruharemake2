# P4 hash-prefix 事件傳遞：五輪真 Safari 前瞻產品驗收

**結論：有限事件傳遞與移除子門檻通過；整批產品 strict FAIL／REVIEW_REQUIRED。** 首輪前已凍結的五句，當輪 Safari 目視各送一次、0 retry；兩個 session、同 DB planned restart、五個 episode 與來源／行動路由均符合事前有限檢查。T1/T4 的最終回覆確實各撤回一個無來源 hash 開頭，事件 SHA 可與實際交付句重算對齊；這修補了前批 `RightBrain.speak` logic 副本使收據遺失的觀察缺口。但 T3 雖未捏造後輩偏好，末句「そのくらいでいいだろ。」在這個未知問題後顯得敷衍，不能按事前「自然日文」必要 gate 宣稱整批 PASS。這是同團隊非獨立的質性判斷，沒有真人評分；不把局部機制證據外推為人格自然度、P4 完成或較強 LLM 優勢。原七輪 strict FAIL 不改、不重播。

## 凍結、執行與原件

- 單變因／事前判準／逐字題：`research/p4_hash_prefix_event_transport_design_2026-10-17.md`、`research/p4_hash_prefix_event_transport_fresh_probe_plan_2026-10-17.md`、`datasets/p4_hash_prefix_event_transport_fresh_probe_2026-10-17.json`；opt-in 入口 `uruha_web_ui_product_p4_hash_prefix_transport.py`。首輪前 commit `ca2621b76edcc42b732576656bc15553b8b8c9fc` 已推 PR #435；10/10 新 freeze SHA 在結果後仍 `OK`。這五句是 developer-authored、非獨立 holdout。首輪前聚焦＋相鄰 46/46（2 upstream warnings）、六個新 Python 檔 compile、CLI help 通過，屬契約／工程證據，不能取代 Safari 結果。
- 新 launcher-owned 私有隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-1w28v6i7`；未用正式 DB、原始 dirty checkout 或外部部署。0-turn ready/stop run `e5ddf26f2d0b7203`、PID 93757；兩段對話 runs `0b498b2705ec28ce`／`f35973d2e9a83507`，PIDs 94291／94773。三次 start-to-ready 約 21.643／8.097／9.606 秒，ready 均同 PID、唯一 localhost listener、HTTP 200；三次 planned stop 的原 PID exited、port vacant。T3 stop 後同 root/DB 換 PID 重啟，UI 換 session；不是把兩段混成同一對話 session。
- 0-turn 停機後，已有 Chroma ONNX archive 用獨立 inode、link count 1 的私有副本預熱；83,178,821 bytes，官方 SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`，封鎖下載仍得到 1×384 finite embedding，約 0.443 秒。只在新 root 的解壓目錄／檔案限制為 0700/0600；這是設施準備，不是對話模型生成。顯式空 profile setup 的 receipt 與新入口路徑一致：before `absent/unavailable/0/null`，after `present/present/0/4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`，1.931 秒，DB 0→167,936 bytes，僅建立 0-row `user_profile`；它是揭露的測量 setup，**不是**產品修正。既有 sandbox 並非全系統 deny-by-default，不主張不可突破的檔案隔離。
- 私有原始 `web_logs/conversation.jsonl` SHA-256 `f83fcd56307ddc2c7a35e6b9442c5fdbfec0654490d7d4086e515bb9a22358e5`（五行）；profile setup receipt SHA-256 `3d4857d78d2942c582e2a52f734c276d62088c27b771098c05ef3cf9f4e309ee`；三個 stop receipt SHA-256 依次 `aac079b67dd57fcdeafdca6e9be28f6959c65d0bedc118aebf6b9c1195b6d66f`、`f9c702626d93c50e1ceef22fe57d2539792e8b8faafa9a058023b988ecb5f5b5`、`a3e80baafeade97789e2556ad3d59bcb52efdb2153d8c9cdc3a8be20c6a0ceec`。原件及逐輪 profile/episode 快照留在隔離 root，沒有把私人 raw 複製進 repo。

## 逐輪真實結果

| 輪／session | Safari 輸入 → 最終可見回覆 | 有界稽核與風險 | M19 等待 |
|---|---|---|---:|
| T1／1 | `先輩に「胡椒焼きポテト、一口いる？」と言われた。` → `先輩にポテトを一口勧められたのか。で、なんて返した？` | `chat/plain_reply`；reported `visible_report_preserved`、prefix `visible_core_exact`，最終＝selected core；實際移除 `まあ、` 1 件。沒有直接接受先輩的邀請。 | 2.8027s |
| T2／1 | `焼きバーガー、一口いる？` → `バーガー出してくるのずるいな。普通に少しもらう。` | `food_offer_generic/named_offer_accept`；action `visible_action_preserved`，不是 T1 轉述來源；無 reported/prefix **audit node**。 | 2.6243s |
| T3／1 | `後輩は柚子羊羹が好き？` → `後輩が柚子羊羹を好きかどうかは、今の話だけじゃ分からないな。そのくらいでいいだろ。` | `third_party_question_evidence_p4=visible_unknown_preserved`，未知未寫成偏好；但尾句的語境自然度／接住感不足，整批自然日文 gate 不予通過。 | 3.0800s |
| T4／2 | `祖母に「昆布チーズおにぎり、一口いる？」って言われた。` → `祖母におにぎりを一口勧められたのか。で、なんて返した？` | 重啟後 `chat/plain_reply`；reported `visible_report_preserved`、prefix `visible_core_exact`；實際移除 `いや、` 1 件，沒有混用 T1 先輩／ポテト。 | 2.6467s |
| T5／2 | `塩チーズポテト、一口いる？` → `ポテト出してくるのずるいな。普通に少しもらう。` | `food_offer_generic/named_offer_accept`；action `visible_action_preserved`，未誤用祖母的邀請；無 reported/prefix **audit node**。未保留塩チーズ細節，不能稱高保真個體反應。 | 2.6322s |

T1/T4 各一筆 final-related 事件的 `selected_candidate_sha256`＝`returned_candidate_sha256`＝最終回覆 SHA；`legacy_candidate_sha256`＝SHA(`prefix + 最終回覆`)；舊 reported source admission proof 亦相符。兩輪移除數合計 2，達「至少一輪可核實移除」正控制。負控制 T2/T3/T5 的原始 logic **各有一個**中途 `_hash_prefix_provenance_events_p4`：T2/T5 事件 SHA 與最終回覆不同，T3 相同；三輪均沒有 reported/prefix audit node，不能寫成「全無事件」或「所有可能前綴都不存在」。所計的是符合 reported 來源與最終交付的去重事件，不是人類認知操作數。

五輪當場 Safari 目視泡泡逐字等於當輪 graph UTTERANCE；raw 可獨立重算 5/5 `assistant_reply`＝blackboard `utterance`。圖的 raw payload 含 T1/T4 來源及 prefix 稽核、T2/T5 直接邀約行動、T3 第三者未知稽核；從 raw 可重建圖的 verify node。T2/T5 行動節點圖標籤會縮為 `selected_offer_action_surface_fidelit…` 且可能在水平捲動區，當輪未留下逐一點開的持久畫面／操作錄影。**持久原件不能獨立重算 Safari 泡泡、0 retry 或點開狀態**；這些限於當輪 UI 目視。圖的 selected row 摘要也省略 `surface_act`，完整行動核對還依賴 selected plan／logic／final 的有限稽核，不能只憑圖摘要證明開放域語義。

## 記憶、成本與嚴格判定

顯式 setup receipt after，加上 T0、逐輪、T3 stop/restart、T5 stop 的九份完整 profile snapshot，全為 `present/present/0`，全內容 digest 同為 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；沒有觀察到 profile 內容污染。`turn_episode_ids` 依序 0→1→2→3→3（stop）→3（restart）→4→5→5（stop），五個不同 ID；這證明持久寫入/數量，不證明跨 session 真正取用記憶。最終 SQLite 檔 221,184 bytes，較 setup 後增 53,248 bytes；Chroma 快照可能改 metadata，不能把全部增量直接歸因於五段內容。

五輪 user wait 總和 13.7859 秒、平均 2.75718 秒、最大 3.0800 秒，全部 ≤20 秒。五輪 M21 都是 `deterministic_rule_plan/completed_without_general_model`，`model_call_attempted=false`、`model_call_completed=false`；本 M21 路徑記錄到的一般模型嘗試為 0，但 raw 沒有可用的生成 token 計量欄位，不能報實測 token 數。等待數字不含 ONNX 準備、profile setup、啟停與人操作時間；未量電力、總硬體成本。這批**不是 fresh model generation、同模型公平比較、正式 temporal holdout 或人評**。

| 事前必要 gate | 結果 |
|---|---|
| 五輪、0 retry、兩 session、same-DB restart、五個 episode、泡泡＝graph、每輪 ≤20 秒 | 當輪目視與 raw/receipt 符合；UI 項不具獨立重放收據。 |
| T1/T4 reported exact core、source proof、final-related 可核實 hash 移除；T2/T5 direct action；T3 未知不編 | 有界 raw/graph 核對符合；T1/T4 各移除 1。 |
| setup after→T0→逐輪→停重啟→最終 stop 的 full profile status/count/digest 全相同 | 九份 snapshot 符合。 |
| 自然日文且來源正確 | 來源有限核對符合；T3 尾句未過同團隊質性自然度審核，**整批 strict FAIL／REVIEW_REQUIRED**。 |

不能為通過而改本批題目／gold、重播五句、加第三批同卡例外或抹去[前七輪失敗](p4_hash_prefix_provenance_fresh_product_probe_result_2026-10-17.md)。下一個**獨立**單變因需先審查前批 T3「使用者自行先查行程」被當成「請助手先提問」的 actor/scope 誤讀，另把未知問句尾句自然度記為獨立表達風險，不能塞回已曝光的 prefix card。正式同模型比較、人評、temporal holdout、VRM／Function Calling 完整交付與人類反應方程式主張仍未完成。
