# P3-B70 prediction-interface reliability acceptance

日期：2026-09-20

## 結論

`PASS / OFFLINE MECHANISM GATE / ZERO MODEL OR FUTURE`。B70在不重跑B69、沒有新網路或模型呼叫的情況下，建立一個
來源無關的deterministic probability normalization adapter，並保留其他內容與安全拒絕。

## 機制與可見例子

模型若輸出六個非負finite相對weights `[2, 3, 1, 1, 1, 2]`，舊parser會因總和為10而拒絕；B70固定以
50位decimal運算、12位輸出精度正規化成`[0.2, 0.3, 0.1, 0.1, 0.1, 0.2]`。總和為1，最高行為仍是
`accept_support_and_continue`。相同adapter同時用於baseline與system，沒有改prompt、schema、model options或token budget。

## 驗收證據

- B70直接測試`12 passed`；與B65、B69B結果／release及B70結果驗證合跑共`38 passed`。
- baseline/system兩個condition的sum-drift fixture都正規化成功，selected behavior不變。
- 缺label、負值、nonfinite、全零、非日文prediction、缺state欄位仍被拒絕，共6種unchanged rejection fixtures。
- schema失敗只可映射到固定allowlist；測了7種分類，不保存raw response或使用者文字。
- model/network/future/B69 retry/training/formal M56/production writes全為0。

## 證據界線

B70只證明介面機制在開發fixture上可重現，不代表B69B當時一定是probability-sum錯誤，因其raw response依事前規則未保存；
也不代表模型已能跨來源穩定預測，更沒有baseline/system勝負。真正驗證必須先凍結第三個未讀來源，再用B70介面一次前瞻執行。
