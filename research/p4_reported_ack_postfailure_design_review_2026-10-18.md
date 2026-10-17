# P4 reported-ack 兩批失敗後的設計審查

狀態：2026-10-18，同團隊、非獨立、**只讀審查／`REVIEW_REQUIRED` 保留**。
本文件不修改產品、不重跑已曝光題、不宣稱新方案已通過。前兩批的 gold、
raw、凍結 SHA 和 strict FAIL 均不改。依 `CURRENT_TASK.md`，任何新產品變更
須先另立單變因 task card、新開發 fixture 與未曝光的前瞻資料；本審查不是
第三次以同句追分的許可。

## 可反駁的 before：三個不同失敗位置

前批 raw SHA `5402089aeec6902ce62d99908bdd8fa250086bd9f8db2857746804abac38f0cb`：
T3 已辨識第三者來源，M31 卻覆蓋 selected action，最終只是字面重述；
T7 unknown 的串行 planner＋M31 等待 23.4192 秒。第二批 raw SHA
`ab52412deaf05e1e5fa9dce08e4d94beb9b4b88ccfbbe5c86061500d044c553d`：
兩個新第三者引述 T2/T6 都有 source/hash/action certificate 且 M31 deferred，
但最後可見 reported-ack 仍是 0/2。逐輪資料與證據邊界見
`analysis/p4_reported_ack_m31_priority_fresh_product_probe_result_2026-10-18.md`。

1. **准入錯位（T6）**：`uruha_reported_ack_m31_priority_p4.py` 的 M31 wrapper
   只見 `user_input`、M29 projection 和 M25／P4-AT 來源證明，無 seed／route。
   `uruha_brain_mac.py` 的 `actual_signal.seed_plan`、`route_info`、M22
   `semantic_route_m22` 卻在 M31 呼叫前已存在。T6 是
   `safety_sensitive`／`protected_low_road`；M31 仍被 deferred。這違反原
   設計對 protected route 的 fail-closed 邊界。它**不**證明該路由本身
   判得對，也不能依「母親」一詞推斷私人風險。
2. **selected→visible 失真（T2）**：selected plan 已是
   `ack_reported_check_instruction_p4`，core 是
   `そう言ってたんだ。何を先に確認する話？`；`direct_chat_answer` 表面變體
   又串接 `。そのくらいでいいだろ。`，產生 `？。`。現有語言 guard 合理
   拒絕畸形標點，但通用 fallback 變成 `ん、その話もう少し聞かせて。`，
   抹掉 source-qualified 行動。M39 接受的是 fallback 後句子；graph
   selected 正確不等於最終回覆正確。
3. **未知對象與成本（T8）**：actor=unknown、新 overlay 無 certificate，
   M21 選 `core_message_jp=確認ありがとう`，M31 完成後未取得表面權限，
   最終仍把未完成的「確認してね」說成已確認。這不是前兩個位置的
   直接結果；18.8440 秒雖在本批 20 秒內，前批 unknown 曾超時。

## 候選單一變因及順序

**A. 先修准入的安全邊界，不把它算作可見承接成功。** 在 orchestrator
的 M31 呼叫點顯式傳入已計算的 seed／route／M22 限定上下文，或在該點
檢查後才調用 deferred wrapper；仍綁原有 source/action/M29 digest proof。
若 route、seed 缺失、protected、factual/memory 或相互矛盾，fail closed
走原 M31 路。普通完整第三者報告保留零額外 M31 model call；protected
原路可能有 M31 的額外延遲／token 成本，需如實測量，不得以速度為由
跨過保護。不得用 ambient/global state 偷渡上下文。**A 的驗收只看
「不在 protected route 假 defer，正常有證據報告仍 defer」；T6 的
`plain_reply` 不會因 A 自動變成正確承接。** 若 protected route 在新良性
「驚訝」控制上誤判，另作 route-policy 研究，不在 A 放寬安全限制。

**B. 另立 selected action 到最終日文的忠實度契約。** 只在當輪來源／
digest proof 與 selected `ack_reported_check_instruction_p4` 均成立，
且不是 protected／unknown／direct／mixed route 時，若表面變體畸形或
行動不符，可選已存在且可通過 guard 的 selected Japanese core；之後仍
執行原語言 guard 及 post-guard final actor audit。這不是在輸出末端任意
補一句固定話，也不准跳過 guard 或把心理推測寫入記憶。預期不增加
模型呼叫、增加少量 deterministic 檢查；風險是 core 太模板化、guard
互動與自然度，必須在新資料另驗。單純修 `？。` 接合雖更便宜，但只
修標點，不足以保證 selected speech act 在其他 fallback 後存活。

**C. unknown 確認對象與串行延遲各自獨立**：先檢查 plan/action 選擇
對「誰確認、是否已確認」的型別缺口，不能用 A/B 一般化修它；延遲需
另量 M21／M31 實際呼叫、等待及可信 token，不能從不同輸入的前後
秒數推因果加速。不能為改善 T8 改弱直接請求負控制或追改已曝光題。

## 下一個可執行 gate（先 A，後 B）

先用 **A** 開新單變因卡，因目前錯誤略過 protected 路由是保護邊界問題。
在任何新生成前，記錄 exact before counterexample、允許檔案、呼叫點和
最小上下文 schema、成功／失敗與回退、≤20 秒成本門檻、新正負控制和
資源上限。開發 fixture 與未曝光 Safari 題分離；正例需不同第三者稱謂／
報告動詞，負例需 protected seed、良性 surprise、factual/memory、
無效／篡改 proof、直接／混合請求、unknown。不能把本批 T2/T6 作新
pass 題。聚焦＋相鄰回歸後，先凍結新題/gold/SHA、commit/push／核 PR，
再用新隔離 root 做真 Safari、graph selected/final 與 profile／成本驗收。
若 A 只通過准入子門檻，仍不可稱 reported-ack 產品 PASS；待 A 的安全
邊界穩定後再單獨設計、測 **B**。B 的 gate 必須核 final bubble／graph
UTTERANCE、自然日文與獨立語感審查，不得只看 selected plan 或 guard
布林值。任一新批失敗須保存反例，不能改同批 gold／重播追分。

本審查不提供同模型強 LLM 優勢、人類被理解感或正式 temporal holdout
證據；它只把目前的錯誤拆成可歸因且可驗收的工程問題。
