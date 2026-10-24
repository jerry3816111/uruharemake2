# P4-G 多語偏好寫入／更正角色回覆驗收

日期：2026-09-21
結論：`fail`（負結果保留；同案例不重跑）

## 為什麼做這一步

P4-F 的記憶更正機制通過，但兩個寫入輪只回 `了解しました`，不像既有 casual Uruha surface。P4-G 沒有改通用 persona prompt，
而是先凍結一個窄假設：如果輸入是明示第一人稱偏好寫入／更正，而且 final language guard 後只剩 allowlist 中的制式敬語，才換成
簡短 casual 日文。自然的非制式回覆必須原樣保留。

離線六個中／英／日正例、六個負例與相鄰 160 項回歸通過後，implementation commit `b257437` 與新的兩輪案例先 commit，才啟動
全新隔離 root；沒有沿用 P4-F 記憶，也沒有在看結果後改 prompt、allowlist 或期望輸出。

## 真實第一輪：有辨識，但窄 authority 沒啟動

Safari 在 session `20260921_043146_f87fdff2` 收到：

> 我喜歡茉莉花茶，請記住這是我現在的飲料偏好。

P4-G classifier 正確標成 `zh/write`，graph 也顯示 `explicit_preference_acknowledgement_p4`；但模型實際回覆：

> 了解。茉莉花茶が今の飲み物だ

因為這不是 frozen allowlist 的 `了解しました／わかりました／分かりました／承知しました` 純字串，adapter 依規格給
`eligible_surface_already_non_generic`、surface authority=`false`，沒有覆蓋。episode
`a69816fe-6c02-4724-b5e4-48d0deebbcae` 已寫入。這輪 full planner 1 call，使用者等待 `25.2079s`，也超過 20 秒目標。

## 真實第二輪：辨識正確，但舊路由語意錯誤

接著只送出事前固定的日文：

> 訂正。もうジャスミンティーは好みじゃない。今はアイスコーヒーが好き。

P4-G classifier 正確標成 `ja/correction`，但既有 rule router 先誤判為 `ask_like_me`，最後顯示：

> はいはい、全くじゃないとは言わない。そこ聞いて安心したいだけだろ。

這句與偏好更正無關，也不是 generic formal allowlist，因此窄 post-guard adapter 仍不得覆蓋。第二筆 episode
`6e6c32ce-1242-487e-8c51-0361fc700c63` 原樣保存，沒有重寫第一筆。這輪沒有模型呼叫，等待 `11.7563s`。

## 正式 gate 與診斷

frozen gate 重新計算為 `fail`，共 10 項：兩輪各自的 visible output、P4-G status、surface authority、surface changed 與
language-guard repair action 都不符預期。語言、act／language classifier、graph node、兩筆不同 episode、每輪一次 durable write、
模型呼叫上限、0 retry 與 0 fallback 則符合。

這個結果否定了 P4-G 的核心假設：只修「純制式敬語」不足以保證明示記憶行為得到正確 visible surface。第一輪證明模型可能生成
allowlist 外但仍不理想的短句；第二輪更證明錯誤可以發生在 plan/intent route，post-guard 只看語氣已經太晚。另有一個 trace 命名問題：
沒有啟動 authority 時，`final_visible_surface_matches_contract=true` 其實只表示「保持原輸出」，不能當 acceptance pass。

## 成本與邊界

總計 1 個新 process、2 個真實 Safari turns、1 次本機 planner call、0 retry／fallback／paid API／external deployment／production
memory／Function tool／VRM action；兩輪等待合計 `36.9642s`。Safari 沿用既有 Uruha tab，沒有關閉 49 個使用者分頁；server 留在
`127.0.0.1:7860` 顯示第二輪與 graph。

P4-G 不是 persona 或理解成功。它提供了有價值的最小反例：問題不只在敬語字串，還在「明示記憶 act 是否能在通用 planner 前取得
正確 route 與 bounded surface authority」。若繼續，必須另立新規格處理 plan-level act，而不是擴大 allowlist 後重跑本案例。
