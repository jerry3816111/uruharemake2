# P4 單句偏好快路：人物／物品邊界設計審查

2026-10-16；新 Safari 題目及產品執行**之前**。保留先前
`p4_source_bound_preference_fallback_plan_2026-10-16.md` 的原文、commit 與
26.5627 秒負結果，不回寫或重跑舊六輪。

## 反例與取捨

未驗收實作的來源准入把 `私は紗夜が好き。` 判為本人 `like/紗夜`；
這只證明說話者／原文值，**不能證明值是物品**。原設計同時要求
「任意物品」及「人物歧義拒絕」，但對不帶敬稱的未知名字，單靠這個
字面 grammar 不可能可靠兼得。另一個事前無模型預檢發現
`私は青じそ梅おにぎりが好き。` 由既有規則選 `food_offer_generic`，
因此不能當新 fallback 的產品正例。這些不是模型或 Safari 得分。

本審查採保守邊界：快路只准**表面帶有一般非人物物品類別詞頭／詞尾**
的值，例如食品／飲品／媒體類別；詞表是類別形態線索，不能存放新
Safari 題目的整個物品值，也不能因「任何名稱都可當物品」而放行裸
人名。人名、未知類別或同形歧義回原 planner；原有明確人物關係問句
與高優先規則仍優先。保留原先「物品名不設白名單」的方向，但承認
這個 bounded fast path **不是任意物品覆蓋**。若類別線索也能是人名，
不主張排除所有真實世界的人物歧義；正式產品結論仍須列此限制。

## 單一核心變因與驗收

核心變因仍是「有來源的單句偏好在一般 planner fallback 省第二次
模型呼叫」。本修正只收緊同一 eligibility，不改 M31、writer、關係
問句 matcher、回覆人格或正式研究資料。事前新增無敬稱人名負例、
不同類別物品正例、舊規則優先、graph selected-node truth；false
positive 需為 0。模型前純 route 預檢要證明每個擬議新正例真的選
`planner_path=source_bound_preference_fallback_p4`，否則換**全新**
未凍結題，不能在 Safari 後換。後續仍依原卡的 20 秒、逐輪 profile
row-ID、自然日文、graph、隔離重啟、0 retry 門檻；不得因本審查
降低門檻。歷史六輪與 T2 失敗保持 developer-exposed。

圖上要如實區分：owner-admission 提供來源 hash；selected fallback
節點只在真 selected plan 上成立；graph 若只顯時間順序，不能宣稱
已有獨立來源因果邊。fallback node 的 `raw_dialogue_persisted=false`
只描述該 audit，不代表整個 graph／episode 不含原句。快路的跨輪
回覆品質可能低於一般 planner，須在新多輪產品案例中觀察，不以
成本改善代替語義驗收。
