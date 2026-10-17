# P4 下一個獨立產品項：第三者引述食物邀請的來源作用域

狀態：2026-10-17，**同團隊、非獨立的只讀設計審查**；先鎖問題／單一變因／驗收，未開始改程式或生成新答案。上個 selected-offer 表面項兩個前瞻批次已用完，第二批 strict FAIL／REVIEW_REQUIRED；本項不能重播或重標它的六題，也不能用新程式回頭洗白。

## Before 與因果界線

舊凍結 Safari T2 `友人に「抹茶ミルクシェイク、一口いる？」って言われた。` 的原始 log／圖顯示 selected `food_offer_sweet/named_offer_light_accept`，泡泡直接答 `ミルクシェイクなら一口ほしい`；事前 gold 要的是把它當「使用者報告朋友的話」，不能由 Uruha 接受。根因在 `uruha_leftbrain_rules._looks_food_offer_query` 對整句 item／`一口`／`？` 子字串匹配，`get_direct_daily_query_plan` 因而選錯 action；後段 `selected_offer_contract_p4` 對引文 abstain 是正確的，**無 audit 節點不是負控制通過**。舊 T3 甜點 core 的 audit 有限文法缺口是另一個儀器變因，這裡不碰。

## 單一變因與選擇的實作邊界

只改 P4 產品的「已選食物邀請之來源作用域授權」。新來源 certificate 只在一個完整、短、有界的日文單句可辨：使用者報告一名第三者向自己說出引號內完整食物邀請，且句外沒有另一個向 Uruha 的直接邀請、求建議、否定、條件或其他請求；舊 plan 已是 casual `food_offer_generic/sweet`。此時把該 selected action 換成 source-faithful `chat/plain_reply`，日文自然承接「朋友／同僚向使用者提了 X；使用者後來怎麼回應」；不得說 Uruha 要吃、不得把被報告的話當事實性本人偏好或寫 profile。certificate 記 source hash、引文 span hash、reported speaker role、item hash、`addressee=reported_user` 的文字證據、未知範圍與不寫長期事實的聲明。這是文字證據的有界推論，不證明朋友在現實中真的說過。

來源辨識只批准「角色＋引號內 food-offer 問句＋`って言われた／と言われた／と聞かれた`」的完整單句；字數、有界 item 詞彙、配對引號、單一問句和明確報告後綴缺一就 abstain。不能用「含引號一律拒絕」：`友人に「ポテト、一口いる？」と言われた。でも、焼きおにぎり、一口いる？` 的第二句是新直接邀請；`「新作」チーズピザ、一口いる？` 的引號是商品名；求建議 `友人に「一口いる？」と聞かれた。どう返す？` 也不是直接邀請。未覆蓋的複句或多語引用保持原路、在報告列 remaining risk，**不得**把 abstain 或缺圖節點報為安全。

執行上新增一個 product-only scope module、**新** Web 入口與只改 ENTRYPOINT 的**新** detached controller；新入口先安裝既有 current-statement→third-party-question→selected-offer 鏈，再裝此 scope gate。舊 `uruha_web_ui_product_p4_offer_action.py` 與 `p4_offer_action_detached_control.py` 都在上一批 8/8 SHA manifest，絕不修改；也不改共用 `_looks_food_offer_query`、M31/M32、writer、語言 guard、正式 DB、舊 dataset/gold/result。理由：全域 detector 由多語／fragment／模型候選等共用，修改會混入多個因果變因；末端 audit 只能觀察，不能糾正已選錯 action。新 product gate 僅在既有 deterministic casual food-offer seed 與來源 certificate 同時成立時授權，其他原路；這不是通用引述理解。

新 graph 節點須位於 selected plan 後、utterance 前，顯示 source scope、舊 selected intent hash/類別、新 selected act、final 是否仍直接接受、selected/logic/utterance/泡泡是否一致；**只有**真正最後日文忠實於 reported-speech core 且沒接受一口才報 `visible_report_preserved`，否則 `selected_or_visible_mismatch`。不得在缺少 final/graph 時自行補成功節點或把內部分析倒入一般聊天泡泡。保留原圖 input、memory、decision、utterance、writeback 連線與 no-new-fact-write。

## 預先成功／失敗條件與順序

1. 開發層先用舊 T2 只作可重現 before，不把它當新前瞻成功。新增 source-disjoint 單元／契約例：純朋友/同僚引述正例；直接食物邀請；引文後另有直接邀請；商品名引號；求建議；否定；條件；轉述要求；引號不配對；危機／邊界；第三者偏好問句／陳述；本人偏好與記憶召回；中文／英文。正例 certificate/selected/final 均一致，負例不可取得新 certificate，不可破壞既有 protected route。用 exact core/graph 檢查，不以「沒有新節點」替代正確回覆。
2. 精確首層命令為 `.venv/product_checks/bin/python -m pytest -q test_p4_reported_offer_source_scope.py`；相鄰 `.venv/product_checks/bin/python -m pytest -q test_leftbrain_rules.py test_p4_current_statement_source_authority.py test_p4_third_party_question_evidence.py test_p4_selected_offer_action_surface_fidelity.py test_p4_source_bound_third_party_statement_act.py`；同 Python `-m py_compile` 新檔，`git diff --check`。先小測、再相鄰，不因通過而稱 Safari PASS。新隔離產品入口 0-turn 啟停只證設施。
3. 首次真輪次前凍結**全新** source-only 六輪、事前逐輪 gold、程式與新入口/controller 的 SHA manifest，commit/push 並核 PR head。六輪至少兩個不同角色／食物／報告動詞的純引述正例、兩個直接 offer 控制、一個非直接來源負控制及 T3 後同 DB restart 的純引述正例。每句逐字一次、0 retry、≤20 秒；逐輪核 Safari 泡泡、selected/core、scope 節點、utterance、episode/profile IDs、模型呼叫/token、M19 等待；一個錯選直接接受、graph/泡泡不符、直接 offer 退步、錯寫 profile、超時或啟動錯即 strict FAIL，保留原 raw 與金標。
4. 不新增通用模型呼叫；新 certificate 的純 CPU 成本、入口啟動／cache readiness、每輪延遲與存儲增量分列。對照僅為 source-scope 產品行為，不是同模型 LLM 優勢、真人被理解感或正式 holdout。產品項至多兩個有理由的前瞻批次；仍失敗轉 REVIEW_REQUIRED，不第三批追分。

這個項目修正的是「誰的話被當成向誰提出行動」的最小必要認知邊界，對長期 human-reaction 目標有真實但很窄的貢獻；若只憑有限日文句型通過，不能宣稱一般人類語用理解或已得人腦方程式。
