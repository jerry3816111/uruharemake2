# P2 Contextual Expression Commit：前瞻工作卡

日期：2026-09-08
狀態：實作前凍結的產品修正計畫；不是正式研究 preregistration。

## 已重現問題

在 P2 compact planner 已完成、`dialogue_act=direct_chat_answer` 的路徑中，模型選出的日文核心會再經過兩個
與當輪語境無關的 deterministic decorator：

1. `_speech_plan_variants` 無條件補 `そのくらいでいいだろ。`。
2. `_finalize_surface_reply` 依 `intent|surface_act|user_input` 的字元 hash 選一個口頭前綴。

修改前同一路徑的實際函式證據：

| 當輪輸入 | compact selected core | 固定 variant | final |
|---|---|---|---|
| `そう、それでいい。` | `うん、そのとおりだ。` | `うん、そのとおりだ。。そのくらいでいいだろ。` | `先に、うん、そのとおりだ。そのくらいでいいだろ。` |
| `うん、聞いてくれてありがとう。` | `ありがとう。そのくらいでいいよ。` | `ありがとう。そのくらいでいいよ。。そのくらいでいいだろ。` | `いや、ありがとう。そのくらいでいいよ。そのくらいでいいだろ。` |

這兩段新增內容沒有來自 compact planner、記憶、使用者回饋、persona evidence 或 safety contract。

## 本次唯一核心變因

只在產品入口、且當輪確有完整 P2 compact planner call 的一般 `direct_chat_answer` 路徑，將表達層從
「無條件固定裝飾」改成「保留既有 refine/sanitize/language guard，但固定前綴與固定尾句沒有證據就不加入」。

用新的 opt-in adapter 實作；不修改凍結的 `uruha_brain_mac.py`。研究入口與未安裝 adapter 的行為保持不變。

## 不可改邊界

- 不改 compact planner prompt、候選數、模型、輸入、Memory／Hard rules、20 秒／256 token 預算或 0 retry。
- 不改 P1 identity、P2 grounded-validation、M27 outcome ledger、adaptive learning 或任何 frozen M1–M57 檔案。
- 不以測試句、謝詞、確認句或固定答案作路由條件。
- 不接管 memory、support、safety/boundary/refusal、explicit clarification 或非 compact turn。
- 不繞過 final visible-Japanese firewall；非法語言仍須被既有 guard 修復或 fail closed。
- 不把產品實測寫成同模型正式 superiority、人評或完整理解證據。

## 預先成功條件

1. 上述兩個重現案例的 final 不再包含 hash prefix 或額外固定尾句，且保留 selected core 的意思。
2. compact `direct_chat_answer` 的 trace 清楚顯示 core、被抑制的 decorator 類型、實際 final surface 與既有語言 guard 結果。
3. 非 compact、memory、support、安全／邊界與真正 clarification 在安裝前後 byte-identical。
4. core 自帶兩句時保留兩句，不以切句或 phrase blacklist 假修正；超長／非日文仍經既有 sanitize/language guard。
5. 0 新增模型呼叫、0 新增長期記憶寫入、M27 ledger 不變。
6. focused 與相鄰產品測試通過；再跑新的隔離本機六輪。Safari 若工具仍拒絕，維持 pending，不改稱通過。

## 失敗條件與分支

- 若 selected core 本身不自然，保留為 planner/surface-realizer 的下一個可歸因問題，不用恢復固定 suffix 掩蓋。
- 若保護路徑有任何 byte drift，收窄 activation gate；不能降低既有 guard。
- 若隔離完整 runtime 找不到 trace 或 final 不等於表達層 audit，先修接線，不進 P3。
- 若本批仍不能讓普通控制輪自然，不宣稱 P2 完成；保留 negative result 並依 stage 重新排下一個產品工作項。
