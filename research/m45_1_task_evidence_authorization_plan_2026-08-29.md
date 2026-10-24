# M45.1：先分開「我要什麼回答」與「我在做什麼」

M45 首次真實 Safari 第 1 輪失敗：沒有任務內容的 advice request 被同模型審核
當成 task evidence。下一輪 scripted confirmation 又繼承錯誤 delivered flag。
M45 frozen core、24-case 結果、11 輪原始 Web 全部保留，不覆寫成修好後成績。

最小修正只動來源授權，不新增報告答案或主題白名單：

1. 使用既有 M25/M36 的 explicit-response classifier 與既有 correction cue，
   按標點切開原文；被辨識為要求回覆形式／糾正的整個子句不能單獨充當任務。
2. 只有其餘的獨立內容子句，以及原本有合法跨輪 linkage 的上一輪使用者內容，
   才交給 M45 的生成／審核。保留原始來源 ID、offset、digest；不採助理文字。
3. 沒有剩餘內容時零模型呼叫，短問任務並明示未交付；沿用 M45 的不計成功與
   下一輪不可冒算方法有效機制。protected／non-help 路徑不動。
4. 保守限制：若任務只嵌在要求回覆的同一子句，可能被整句排除，不能宣稱
   通用 task extraction。此版先堵住形式要求被當成任務內容的來源漏洞；其餘
   語意審核、自然性、過度拒答仍需獨立驗證，不能增加成功總分來掩蓋。

驗收：新契約涵蓋三語純要求、明確內容＋要求、linked correction、助理不入源、
只有 request 內嵌任務的保守拒絕、protected/non-help；獨立新 Safari session
驗證缺任務→確認不學錯、內容明确→實際一步、正常傾聽與圖表來源。這些是
修復回歸與功能驗收，不冒稱未見 holdout。完成 M45 原始 11 輪後才開始實作。
