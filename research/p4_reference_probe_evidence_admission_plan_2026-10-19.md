# P4 參照探查誤路由：單一證據准入修正計畫

狀態：2026-10-19，**下一批實作／新 Safari 首輪前定案**。前一批 deterministic plan-leak 八輪 raw SHA `ccf6e137a102f6cc1e672b066e9abcfb1fa57a7d343fe0790eadf86b4408aae5`、strict FAIL／0 eligible 不改判，八句不可重送追分。本項是正常對話行為的獨立變因；不假稱已驗到舊 T4 的 `short_confusion` 修正。

## Before、可反駁原因與唯一變因

舊批 B1 `今、プラネタリウムの説明文を短くしてる。` 長 20，`プラネタリウム` 內嵌 `ネタ`；B3 `次の投影の開始時刻、何時か分かる？` 長 17，`投影` 內嵌 `影`。`uruha_brain_mac.py` 的 `early_reference_markers` 在 ≤22 字時只做 substring，兩句都出 `reference_probe` seed，M21 `deterministic_rule_plan`，對外錯問「元ネタ」。兩輪 M22 均為 `general_conversation`；B1 M31 canonical 有「縮短說明文」但沒有可見答案權限，不能用它宣稱最終理解。`_critique_plan` 亦在看見 `ネタ` 等字串時可能注入 `missed_reference_behavior`，所以只擋第一個 if 不足。A1 長 28 且 A3/A4 屬不同斷點，不能合包。

唯一新能力變因：opt-in **reference_probe source／speech-act evidence admission**。從**當輪原文**分辨明問歌詞／曲名／來源、缺作品主體的 ED/OP 或真正短片段，與完整自述／一般資訊問句／第三者陳述；同一 source certificate 約束舊 seed `reference_probe`、critique 復注入及最終 selected `reference_probe`。`ネタ` 不能因藏在片假名單詞內成為來源證據，`影` 不能因藏在漢字複合詞內成為詩意片段證據；問號要依問的是作品來源還是時間／地點，不可一律打掉或一律放行。不能把證據缺失解讀為使用者心理事實。被拒的參照候選應交回既有一般路徑，**不以另一句固定澄清模板頂替**，不新增模型呼叫作「修正器」。保留真正歌詞／ED/OP 路由、引述外層行為、受保護辱罵／危機路由、既有記憶與來源答案權限。這是准入，不同時修日文措辭、性能、A3/A4 或舊 plan-leak。

允許檔案：新 opt-in adapter、專用聚焦測試、薄 Web entry/controller、此計畫與新資料／SHA、結果報告、`CURRENT_TASK.md`。舊 typed-source／plan-leak code、凍結資料與結果、核心共用 scorer、正式 DB、原始 dirty checkout 和無關 `output/graduate_application_report/` 不改。若獨立證書無法安全貫穿 seed／critique／selected，就先留下失敗證據與 `REVIEW_REQUIRED`，不能偷偷修改凍結 core 或把 literal 規則補成測試句黑名單。

## 新題、條件 gold 與產品硬門檻

前瞻資料 `datasets/p4_reference_probe_evidence_fresh_probe_2026-10-19.json`：兩個新的隔離 session、同 DB planned restart、八輪各一次／0 retry。實作前**零模型**舊 `_rule_based_plan` 靜態 before：A1/A3/B1/B3 四個完整自述或資訊問句均錯選 `reference_probe`；A4、B2 真參照仍選 `reference_probe`；A2 無 rule；B4 受保護 `abuse_pushback`。新 code 須讓四個錯准入在同一來源證書下退回一般路徑，兩個真參照保留（若最終模型／產品因其他下游行為未保留，產品照判 FAIL），B4 保護路由不被改。B3 第三者引述不能升為使用者已確認事實。A3/B1 問時間／位置，沒有可信場次或儲位資料就明說不知道／請查來源，不能編值。A1/A2 普通自述不被責備「丟殘句」；A4/B2 真參照用自然日文承接且不編曲名。不能只有 trace 變綠而可見句仍離題。

八輪最終需 **8/8** 真 Safari 泡泡＝raw `assistant_reply`＝graph UTTERANCE＝language guard，自然日文、無內部分析外洩、來源／行動忠實、八個不同持久 turn episode、T0–T8 profile 0 rows／同 digest、每輪 user wait ≤20.0 秒，並記錄可得模型呼叫／token／延遲和真 PID/port。至少 A1/A3/B1/B3 中 **4/4** 前瞻 false admission 有 source certificate 阻擋、A4/B2 **2/2** 正 admission、B4 受保護；不足或任一硬門檻失敗即整批 strict FAIL，不補題、不重送、不改 gold。若 general fallback 引入 M21 超時，按實測 FAIL，另卡歸因。所有數值是產品驗收門檻，不是同模型因果 A/B 或正式 holdout。

先零模型聚焦與受影響路由／引用／日文／graph 回歸，product SHA/diff/commit/push/PR head 再新 0700 root 的 0-turn readiness、官方 SHA ONNX 私有預熱、顯式空 profile；按凍結順序真 Safari，一輪後核泡泡與圖。只有新批結果可作新修正的產品證據，不把同源開發題當作普遍「人類語用理解」或正式同模型優勢。失敗保留；至多兩個有根據的修正批，仍失敗 `REVIEW_REQUIRED`。
