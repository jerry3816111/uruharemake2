# P4-B safe isolated product launcher 驗收

日期：2026-09-20  
結論：`launch_chat_graph_pass_after_one_sandbox_repair`

## 使用者現在真的拿到什麼

本機產品入口現在可以從safe worktree重現啟動，不需要把程式或venv搬回原始dirty checkout。啟動器會：

- 找到既有專案venv並保留venv symlink語意；
- 強制只監聽`127.0.0.1`、不開Gradio public share；
- 把chat memory、session與Web logs導向private temporary runtime root；
- 關閉idle-visible催促式發話；
- 用macOS sandbox拒絕product child寫入safe worktree與原始dirty checkout；
- 先做unsandboxed與sandboxed product import probe，任何一步失敗都不啟動server。

目前網站保留在Safari的`http://127.0.0.1:7860/`，server仍在執行，方便使用者直接查看。沿用原有Safari分頁，
tab數`48 → 48`，沒有關閉任何頁面。

## 真實失敗與修正

第一次frozen v1 launch本身達到HTTP 200、localhost-only與Safari可見，但Safari status同時顯示repository中的Human Annotation path。
chat資料雖然隔離，optional annotation按鈕仍可能寫回repo，所以第一次結果保留為
`failed_product_child_not_fully_write_isolated`；當時沒有送聊天、沒有repository write。

唯一修正是v2 OS sandbox。合成fixture實際證明protected path的`touch`被拒絕、isolated runtime內寫入成功；repair與原v1相鄰
suite為`32 passed`。修正commit後才以相同manifest、明確`--reuse-runtime`重開一次。v2 HTTP 200，page bytes=`1,963,996`，
listener只有`127.0.0.1:7860`，sandbox profile mode=`0600`。

## 一輪 Safari 真實對話

中文輸入的第一次UI automation只打出標點，沒有送出；這是accessibility輸入限制，不冒充產品失敗或成功。清空後使用實際英文：

> I feel tired today. Please just listen; I do not want advice.

Safari最終顯示：

> うん。今は方法出さないから、そのまま話して。

本輪不是「有回答就算成功」。實際trace顯示：

- `selected_mode=listening`
- `selected_policy=listen_presence`
- `explicit_desired_response_detected=true`
- `negated_policy=solve_regulation`
- `surface_status=matched`
- actual runtime graph nodes=`69`
- end-to-end user wait=`3.3884s`，低於既有`20s`目標
- 後續沉默檢查沒有新增可見催促回覆

也就是說，系統沒有只抓「累」然後給休息方法；它把「請聽我說、不要建議」當成當輪明示回覆形式，阻止解法路徑，最後用日文
執行陪聽。這是一個明示語用案例的產品證據，不可外推成系統能普遍猜中未說出口的期待。

## 寫入與證據範圍

- 1筆conversation JSONL=`1,353,575 bytes`、5行text log，全部在isolated root。
- Chroma DB與adaptive person model也只出現在isolated root。
- 真實回合後Git仍clean；production memory access=`0`。
- 這一輪走deterministic fast path；未觀察到provider model call證據，tool execution=`0`、physical VRM action=`0`。
- voice controls可見，但Safari顯示microphone unavailable，TTS未初始化；未驗收voice。
- v1→v2證明manifest root能在停止process後明確reuse；尚未測「已有聊天後再次重啟能否語義回憶」。

P4-B通過的只是可重現安全啟動與一輪chat＋truthful graph。P4-A已證明VRM 3D與Function Calling其實尚未進產品；下一步先建立
零副作用、單一allowlisted read-only tool的Function Calling seam，因為它也是未來VRM action transport的前置能力。不得直接把過去
未通過holdout的VRM action policy接到physical execution。
