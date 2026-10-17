# P4 reported-ack A：無規則 seed 的來源證明修正（唯一前瞻修正批）

狀態：2026-10-18，設計先定案；尚未對新題做模型／Safari 生成。這只更正 A 的 seed 表示，不是 B 的最終可見承接、T6 記憶或 C 的延遲改良。首發 A 原件 SHA `1e59785995586f5ea9247a577433d1436fbf6fdd3603eb74dfbaf0b5806d56d7` 與 strict FAIL 永久保留。

## before、可反駁機制、單一變因

首發 T1/T5 在來源證明、`actual chat/casual`、`high_road/deliberative`、M22 exclusive `general_conversation` 均齊時，A 仍 0/2 准入；`_rule_based_plan` 沒命中回 `None`，`classify_user_signal` 預設 actual chat/casual 並把 seed 壓成 `{}`，准入只接受 seed 明寫 chat/casual。T2/T7 有真正 protected seed、low road、安全 M22，2/2 正確拒絕。失敗詳見 `analysis/p4_reported_ack_route_admission_fresh_product_probe_result_2026-10-18.md`。

修正只新增同輪 seed provenance：在 `None` 被壓成 `{}` **之前**標 `no_rule_match`；非空 dict 標 `matched_rule`；其他回傳標 `invalid`。顯式傳入主要 M31 context。A 對 `no_rule_match` 只承認**存在且恰為 `{}`** 的 seed，並仍要求 actual chat/casual、high-road deliberative、M22 單一普通分類、無 profile grounding、完整 M25/P4-AT/M29 同 digest source certificate；`matched_rule` 只承認原本精確的 seed chat/casual。缺 marker、未知 marker、缺／`None` seed、marker 與 seed 矛盾、部分非空 seed、protected／low-road／factual／mixed 仍回原 M31。不得把一般對話 M22 單獨當安全證明，也不得用後段 selected plan 回填早期 seed。無 ambient state、不新增模型呼叫、不保存原文或心理事實。

允許改：`uruha_brain_mac.py` 的 seed provenance 與既有 M31 context 一欄、`uruha_reported_ack_route_admission_p4.py` 一個准入條件及 raw-free audit、聚焦測試、新前瞻題／plan／SHA／結果與 `CURRENT_TASK.md`。不改既有首發 code 凍結宣稱（Git 歷史保留）、舊題/gold、原始 dirty checkout、正式 DB、非 opt-in 行為或後段 surface。若 default classifier 多一個 inert metadata 欄，它不得改 default 決策結果。

## gate、資源與退出

1. 零模型：真無規則命中、空 seed＋正確 marker 才有普通正例；無 marker／seed、`None`、部分 seed、矛盾 marker、錯 digest、protected seed／low route／M22 safety 或 factual 均恰一次原 M31；正例 0 次。contextless late repair 仍原 M31。既有 A 105 測試與相鄰測試不退化，必要時新增專注測試。
2. 新八題必須與三批已曝凍結題及新測試 fixture 逐字不同。首輪真生成前凍結順序、條件式 gold、code、計畫、SHA，commit／push、核 PR #435 head。0 retry、0 事後改題／標註／code。這仍是開發者自編產品題，不是正式 holdout。
3. 新 0700 隔離 root，同 opt-in 本機入口，0-turn readiness/planned stop，私有 ONNX 離線預熱與顯式 0-row profile setup；兩 Safari session、T4 後同 DB planned restart。逐輪核 source、seed marker、route、M22、M31 與模型呼叫、selected、最終泡泡／graph UTTERANCE／raw、≤20 秒、完整 profile digest、八個 episode、自然日文；記可核實的實際 token，沒有數字就 `unavailable`。
4. A 嚴格子門檻：至少一個真正 `no_rule_match + {}` 的 high-road 完整報告 **准入並 0 M31 semantic call**；至少一個 source-qualified protected/low-road 完整報告 **拒絕並原 M31**；新八輪逐題符合事前條件式 gold；8/8 user wait ≤20 秒；0 profile facts、圖／泡泡一致、隔離啟停正確。B 若可見回覆仍失真，照實列產品 FAIL，不把 A 子門檻外推。若 A 本修正批仍失敗，維持 `REVIEW_REQUIRED` 並停止此方向追分，等待新的設計審查；不得第三次換字句／追加例外。

實際證據層級：static contract ≠ fresh generation ≠ Safari full runtime ≠ 同模型 baseline ≠ 真人感受／正式 temporal holdout。即使 A 達標，也不能宣稱已解人類反應方程式或 P4 整體完成。

## 首輪前、零模型題目選擇檢查

候選句中含「順番／手順／表記／一覧」的引述雖符合表面語法，既有 M25 沒選出 `calibrate_need`，因此 P4-AT 不產生完整 reported-check certificate。這是在任何新模型／Safari 生成前的靜態檢查，已改成 `datasets/p4_reported_ack_route_admission_seed_provenance_fresh_probe_2026-10-18.json` 的八句，沒有看答案追分。最終八句逐字 `rg -F` 查整個 repository 均無既有匹配；以現有 M25/P4-AT classifier 與**人工構造的有效同 digest M29 projection** 做靜態 certificate 預覽，T1/T2/T5/T7 true、其餘 false；真 `_rule_based_plan` 預覽 T1/T5 `no_rule_match`，T2/T7 `matched_rule` 且 protected seed。實際 M29、runtime M22、route、M31 與最終可見仍必須 Safari 核對，靜態預覽不作產品 PASS。
