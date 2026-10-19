# P4 位置建議：敬體修復時保留選定命題的前瞻工作卡

日期：2026-10-19。狀態：**實作和本批任何模型生成之前凍結的開發者計畫**。條件式 gold 在 `datasets/p4_location_advice_formal_surface_fresh_probe_2026-10-19.json`。本項不是正式 holdout、同模型強 LLM 比較或真人語感判定。

## 問題證明與唯一變因

前批九輪 strict FAIL 不重算，原件 SHA `8e05c0252d01590a8419e1bf86605948cc426932d1f3631c6e85d77a5d354468`。A1/B1 的 M21 full planner 各選出具位置建議命題的 `…見つけやすいです` 句；P4 handoff 已是當輪 User 來源、`matched_full_planner`，M39 唯一檢出 `formal_register`，卻因 selected policy 為空，呼叫固定 fallback 把完整句改成 `ん、そこもう少しだけ聞かせて。`。這證明了**末端修復會遺失已選命題**，不證明原候選都足夠好：B1 原候選還未明確回答「易發放」。B3 是 M18 跨領域失眠模板早捷徑；B2 是 M31 核准殘片，兩者分因保留。

唯一變因是**僅在 opt-in 位置建議入口，對證書確實綁定的 selected candidate 做 formal-only、可逆核對的常體轉換，讓既有日文／M39 guard 仍照常執行**。不是通用語義重寫或新建議產生器，不改原 M39、M18、M21、M22、M31、M45 及舊事實來源／記憶。只有當輪 User SHA 與證書一致、`eligible=true`、`matched_full_planner`、候選 SHA 等於 tick 時選定 core、M22 為一般對話、未受保護、M39 前稽核唯一違規為 `formal_register`、policy act 已滿足、候選是一句且沒有引號，才試單句終止的 i-adjective `…やすいです[。]`／`…にくいです[。]` → 保留整段逐字前綴並將句尾改自然常體 `…やすいよ。`／`…にくいよ。`。僅此兩種有界形態，不泛刪 `です`、不改引用台詞、`ます／ください`、多句或不確定活用。轉後再跑原 M39 inspect；如仍有 role／unsupported／policy／formal 違規，或 guard 最後再改掉，記失敗收據並保留原有 fail-closed／strict 產品失敗。trace 只存前後 SHA、方法 enum、檢查結果，不寫原文或私人心理。

此轉換只保護可觀察的**已選命題字串前綴**；不證明選定命題本來就貼合 User 目標，不把未授權具體地點洗成記憶事實。若沒有此精確候選形態，本批產品不能以 0 hit 宣稱修正有效。

## 允許範圍與程序

本步只新增本計畫、新九題、preimplementation SHA 並先 commit/push PR #435；在凍結提交前不改程式、不送新題模型。後續允許修改 opt-in `uruha_location_advice_act_handoff_p4.py` 的最外層 visible guard、新聚焦測試 `test_p4_location_advice_formal_surface_p4.py`、新薄 Web 入口 `uruha_web_ui_product_p4_location_advice_formal_surface.py`、新隔離 controller `p4_location_advice_formal_surface_detached_control.py`、首輪前 product SHA、結果報告與 `CURRENT_TASK.md`。不可動前批 dataset/gold/result、原始 dirty checkout、正式 DB 或無關 `output/graduate_application_report/`；不為本批把 M18/B3、M31/B2 一起修掉。

先零模型 fixture 驗證：兩種支援詞尾及標點、前綴同一性、有效證書與 SHA、唯一 formal 違規、轉後再稽核；反例涵蓋 protected、敏感、引號內敬體、多句、`ます／ください`、混合 role/unsupported/policy 違規、錯誤／過期／不匹配證書、事實來源、未知與 no-advice，均不被新轉換接管。跑受影響相鄰測試、語法、入口與 controller 檢查；產品 SHA、diff review、commit/push/PR head **先於** fresh 生成。

全新 launcher-owned 0700 隔離 root，0-turn same-PID ready/planned stop；官方 SHA ONNX 私有離線預熱、顯式空 profile 後，真 Safari A1–A3，各句一次，A3 後 planned stop；同 DB 新 PID/session 跑 B1–B6，各句一次、0 retry。每輪存即時 episode/full-profile T0–T9 再送下句，核泡泡＝raw＝guard＝graph UTTERANCE、handoff 與 formal repair node、source 及選定／可見、每輪 user wait ≤20 秒、自然日文、九個不同 episode、profile 0 rows 同 digest、額外模型呼叫 0，列舊 M21/M31 與可得 token／延遲。無完整 token ledger 就標 incomplete，不報節省。

## 先凍結的判準與失敗分支

- A1/A2 建議正例須 **2/2** 提供與防滾失／抗風吹散目標相連的一個具體、低風險可採行位置原則；不能只說「適當地方」、反問或答別的題。至少 **1 輪** selected candidate 真命中安全 formal-only 轉換且可見句保留同一命題前綴；若 0 hit，即使回覆好看也沒有本變因的產品因果證據。命中但原候選本身無目標關聯，仍判建議 FAIL。
- A3/B1/B3 的直接 User 時間事實不得被建議或第三者「かも」覆蓋；B1 是真重啟後的直接 episode 檢索。B2 第三者猜測須保留歸屬與不確定性，不因只沒編值就算完整通過。B4 的引用台詞不得被當作當輪敬體錯誤擅改；B5 明說先聽不給建議，B6 敏感保管不提供位置建議。以上控制若上游既有缺陷失敗，整批仍 strict FAIL，且不得私下合修本變因以追分。
- 9/9 可見自然日文、行動／來源忠實、graph／raw／guard／泡泡一致；T0–T9 十個即時雙快照、九個獨立 episode、profile digest 不變；每輪 ≤20 秒、0 retry、新轉換 0 model calls、same DB planned restart。任一硬門檻失敗＝**整批 strict FAIL**；局部 safe-transform 命中只作局部證據。Safari 無截圖則明標目視，不能把 raw 重建當獨立視覺證據。

如果本修正仍未讓 full pipeline 對建議交付達標，保留反例、只讀分辨 M18 早路徑／M21 候選品質／M31 語義碎片；依同項最多兩個有根據修正批和 `REVIEW_REQUIRED` 規則收斂，不能無限加模板。正式同模型比較、真人、temporal holdout、VRM／Function Calling 統一入口另按其原 gate，Goal 不因本項完成而完成。
