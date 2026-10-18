# P4 位置建議言語行為交接：前瞻工作卡

日期：2026-10-19。狀態：**只讀因果審查後、實作與本批模型生成前的開發者前瞻計畫**。題句和條件式 gold 在 `datasets/p4_location_advice_act_fresh_probe_2026-10-19.json`；此刻尚無本批 code、真模型、Safari 或產品 PASS。這不是正式 temporal holdout、同模型強 LLM 對照或真人評價。前批 11 輪 raw SHA `5b6543bad332c8a28abb82ad2f0d00732a7d7d1beec4bd5ab853c90b893c0b5d`、整批 strict FAIL 和 B5 原句均不改判、不重送追分。

## Before、斷點與單一變因

前批 B5 問「予備マイクはどこに置くのがいい？」；Safari／raw／graph 最終同為「予備マイクは適当な場所に。」、user wait 11.2060 秒。當輪 raw 顯示 M22=`general_conversation`，M21 `full_planner` completed、耗 7.7666 秒，選定 `intent=chat`、`surface_act=plain_reply`，`core_message_jp` 在表面化前已是該空泛句；M18/M34 無 selected `solve_regulation` policy，M45=`not_applicable`、新增模型呼叫 0、reason=`non_help_or_protected_current_act`。`planner_debug` 曾引用先前「予備マイクの置き場、どこ？」未知現有位置問答。原 raw 不留三個模型候選原文，故只能定位選定計畫已錯，**不能斷言**錯在候選生成、排序或單一提示詞。證據與其他獨立失敗見 `analysis/p4_local_time_place_answer_authority_fresh_product_probe_result_2026-10-19.md`。

唯一擬議產品變因：在 opt-in 入口形成**當輪 User 來源限定的「建議放置」言語行為證書**，區分「現在實際放在哪」的事實問句、真正徵求可行放置建議、第三者／引號內問句、與明示不要建議。把同一證書交給既有 M21 規劃與選定計畫核對，再核最後可見句及 graph；正例須將使用者明說的物件／目標連到一個低風險、可採用的放置原則或建議，資訊真的不足才精確短問，不能靠「適当な場所」「好きな所」「一緒に決めよう」等空句冒充交付。證書不是固定地點、固定回覆、物件字表、私心推斷或開放領域建議器；未知的現有位置仍須保留未知，過去 User 儲位／第三者猜測不自動成為最佳建議。

這是同一 advice-act handoff 變因在規劃、選定與可見邊界的檢查，不把互不相關的 prompt、rerank、renderer 各記一項增益。不得為了本批改選 M18=`solve_regulation` 或接入 M45/M46：B5 的 M45 根本未嘗試；歷史 M45 類型契約曾區分具體動作與空承諾，但任意換書等失敗及額外生成／review 成本不能當位置建議已可用。保留舊 M22、M18、M45/M46、事實來源閘、受保護路由、模型與參數、記憶寫入及語言守門。新 opt-in 變因新增模型呼叫須為 **0**。若無法在此範圍內把證書交給 M21 與可見句，先停在設計審查，不暗改共用路由或放寬 20 秒門檻。

## 允許檔案與先後順序

本次凍結步驟**只新增本計畫與上述 dataset**，不改 `CURRENT_TASK.md`、既有 freeze/gold、程式或結果。後續實作若審查同意，允許新的 opt-in `uruha_location_advice_act_handoff_p4.py`、其聚焦 `test_p4_location_advice_act_handoff.py`、薄產品入口 `uruha_web_ui_product_p4_location_advice_act.py`、隔離 controller `p4_location_advice_act_detached_control.py`，以及僅為把證書傳給原 M21 所需的 `uruha_brain_mac.py` 最小 opt-in hook；後續 preimplementation／product SHA、結果報告與 `CURRENT_TASK.md` 只記錄本項。不得改舊 M21 候選 scorer、M22/M18/M45/M46/M39 共用契約、歷史產品探針與報告、正式 DB、原始 dirty checkout或無關 `output/graduate_application_report/`。若 hook 必須改共用行為，須先重審設計，不能偷擴允許範圍。

先驗證 dataset JSON、九句對既有 `datasets/*.json` 的逐字碰撞和新物件來源分離；凍結計畫／dataset SHA 與 git commit **先於實作和任何新模型生成**。再做最小 opt-in 程式、聚焦及受影響相鄰零模型回歸、語法與入口檢查、產品 SHA、diff review、精確 commit/push 與 PR head 核對。最後才啟全新 0700 隔離 root、0-turn same-PID ready/planned stop、官方 SHA ONNX 私有離線預熱、顯式空 profile、兩個真 Safari session／同 DB planned restart，一句一次、0 retry。這批作者自編題已由開發者讀過，只能稱 fresh 產品探針，不能改名正式 holdout。

## 九輪條件式 gold 與硬門檻

Session A 的 A1 是有足夠低風險目標的建議正例；A2 問**現有**儲位而無直接 User 答案，不能把 A1 建議當現實；A3 是直接 User 儲位陳述，A4 必須只從該直接 User 來源答出。A4 後 planned stop，新 PID/session B 使用同 DB。B1 是同物件的新建議目標，不可把 A3 的已知儲位直接包成最佳建議；B2 的係員「かも」只屬第三者推測；B3 是另一物件與目標的建議正例，不可把 B2 推測升格為確定位置或預設最佳；B4 的引號屬措辭修改任務，B5 明示先別提案而要求傾聽。完整逐輪欄位和 gold 在 dataset；沒有任何題的固定日文答案。

**整批 strict gate**：A1/B1/B3 **3/3** 最終自然日文確實提供 goal-tied、物件對齊、低風險的具體放置建議／原則，不能只是空泛詞、未執行承諾或無理由轉問；即使 runtime fail-closed 改問，正例仍判 FAIL。A2/A4 事實分支 **2/2** 保持未知不編／直接 User 來源答值與真 trace ID，A3 User 斷言語義保留；B1/B3 不把既有儲位或第三者猜測當建議來源；B2/B4/B5 **3/3** 不被新 advice gate 錯接管，且可見行為忠實。每輪核 current-act 證書、選定 plan、最後 guard、graph node 的權限與 shadow；**9/9** Safari 泡泡＝raw assistant reply＝最後 guard＝graph `UTTERANCE`，無內部分析與來源捏造，九個不同持久 episode。每送下一句前立即保存該輪 full-profile 與 episode snapshot：T0–T9 **10/10** 收據存在、profile 0 rows／同 digest，不能用晚輪倒補漏輪。每輪完整 user wait **≤20.0 秒**，九句各一次／0 retry；新增 advice gate 模型呼叫 0，列出既有 M21/M31/M45 attempted/completed、可得 token／latency、PID／port，缺總 ledger 明標 incomplete 而不報節省。任何內容、來源、圖／泡泡、記憶收據、延遲或程序硬門檻失敗即整批 strict FAIL；局部控制成功只作局部證據。

B6 的無證據責備、A4 雙 `が` 及前批 T1 漏收據的**歷史判定**不由本 advice 修正重算；本批只把逐輪收據流程設成硬 gate。若兩次有根據修正仍失敗，保留 `REVIEW_REQUIRED` 並展示反例，不換題／降 gate 追分。正式同模型強 LLM、真人、temporal holdout、VRM／Function Calling 仍 pending。
