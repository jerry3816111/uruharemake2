# P4-F 明示偏好更正跨 process 重啟驗收

日期：2026-09-21
結論：`pass`（只限事前凍結的一個 bounded product case）

## 這一步修掉什麼實際缺口

P4-E 證明一筆偏好能跨重啟回溯，但沒有回答「之後明確改口」時該怎麼辦。P4-F 先以 fixture 重現：舊偏好與新偏好都被檢索時，
既有 adapter 只能得到 ambiguous，無法分清 current 與 historical。接著只新增一個窄機制：同一位使用者、同一物件、同一個被選入的
episode 內明確出現「不再偏好舊值；現在偏好新值」時，才建立 typed supersession；其他型態維持 fail-closed。

事前 contract、三句原文、預期 current／revoked 值、restart 證據、0-retry 與失敗條件先在 commit `86b365d` 凍結，之後才跑真實產品。

## 三個真實產品輪次

同一個全新隔離 root 的第一個 process（PID `70799`、session `20260921_041025_abc55fae`）收到：

> I prefer herbal tea. Please remember that as my current tea preference.

Safari 回覆 `了解しました`，寫入 episode `aa6fff5f-ebb6-4d73-b661-5c38fdbd3338`。接著收到：

> Correction: I do not prefer herbal tea anymore. I prefer black tea now.

Safari 回覆 `了解しました。`，另寫入 episode `a2baf17f-c271-4d95-b56b-a49a5990cfdc`。兩輪各只寫一筆 episode，沒有覆寫舊資料。

舊 process 真正停止後，使用完全相同的 runtime root、memory DB 與 launcher manifest 啟動新 PID `70923`、新 session
`20260921_041239_0f54a1e3`。重啟之間沒有注入、seed、改 prompt、重試或改答案。新 session 只問：

> What kind of tea did I say I prefer?

題目不含 `black tea` 或 `herbal tea`。Safari 實際顯示：

> 今の好みは紅茶。前のハーブティーから更新してる。

## 為什麼不是碰巧挑到一筆記憶

runtime graph 顯示 `speaker_qualified_fact_p3`，狀態為 `resolved_explicit_preference_supersession`；current=`紅茶`、
revoked=`ハーブティー`，兩個 value digest 不同，且 correction／historical trace 分別綁回上述兩個 immutable episode。
兩筆來源都早於新 process，也都出現在 selected working memory。

更重要的是，舊 episode 的 retrieval score=`1.4813`，更正 episode=`1.4801`。若只依最高分任選，反而會選舊值；本次結果是先從
明示更正關係判斷 current／revoked，再生成固定日文 recall。recall 輪 general planner model call=`0`、DB rewrite=`0`，frozen gate
重新計算為 `pass`、failed gates=`[]`。

## 成本與仍保留的失敗

總計 3 個真實 product turns、2 次 process start、1 次 restart、2 次本機 planner calls（只有兩個寫入輪）、0 retry、0 fallback、
0 paid API、0 external deployment、0 production memory、0 Function tool、0 VRM action。三輪等待合計 `32.1162s`；conversation log
共 3 rows、`3,453,699` bytes。Safari 沿用既有 Uruha tab，沒有關閉使用者分頁；graph 可見兩個歷史 episode 與 supersession 節點。

P4-F 不隱藏一個可見缺口：兩個寫入輪雖是日文，但 `了解しました`／`了解しました。` 過度禮貌、制式，不符合既有較自然的うるは
口吻。這不影響本步「跨重啟更正因果」gate，卻代表 persona surface 尚未通過；下一步只能針對這條寫入／更正 surface authority 做
窄修正，不可藉此重跑同一 P4-F 案例追分。

本結果只證明一個 developer-authored 英文茶類偏好更正案例。它不證明一般信念修正、任意語言／類別的更正、連鎖撤銷、50輪可靠、
人類式記憶、被理解感、相對強 LLM 優勢或人腦方程式。
