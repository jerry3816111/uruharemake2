# P4-K cross-restart surface delivery acceptance

## 結論

P4-K 的事前凍結 product gate=`pass`，failed gates=`0`。這次沒有重跑已失敗的 P4-J rooibos 案例；另用新隔離 root、兩個不同 process 和兩個只執行一次的 Safari 輪次，驗證 propagation 修正確實把已授權的 typed current-preference contract 送到最後可見日文與 runtime node graph。

這是 bounded delivery pass。`紅茶` 與更早 P4-F 的 black-tea 語意有重疊，freeze 已在執行前揭露；因此不得把結果說成 unseen semantic generalization，也不代表 open-domain memory、長對話可靠、人類被理解感、優於強 LLM 或人類方程式。

## 真實執行

第一個 product process 在 `127.0.0.1:7863` 使用全新 mode-0700 isolated root。Safari 實際輸入：

> I prefer 紅茶. Please remember that as my current drink preference.

可見回覆：

> ん、その好みは覚えとく。

P4-H act=`write`，P4-I 寫入 `scope=drink`、`value=紅茶`，active memory id=`15d6830f-10cf-4b08-9935-3f69624d3a9d`。profile 恰有一筆 typed positive，episode 恰新增一筆；等待 `2.1570s`，planner model call=`0`。

PID `86488` 退出且 listener 關閉後，第二個 product process 以同一 runtime root／memory DB 啟動，PID=`86555`、新 session=`20260921_133845_920e0a0d`。在任何 recall turn 或外部注入前，它已看到第一程序的同一 active id。Safari 再輸入一次凍結問題：

> 私の今の飲み物の好みは何？

可見回覆：

> 今の飲み物の好みは紅茶。前のじゃなくて、今の方ね。

P4-J status=`resolved_unique_active_typed_current_preference`，回答綁定同一 active id；final surface 與事前契約逐字相同。Safari 下方 graph 也實際出現 `typed_current_preference_recall_p4` 的 `select` node。等待 `2.1684s`，planner model call=`0`。

## 持久化與非變更證據

- profile count：recall 前 `1`，後 `1`。
- active typed current count：前 `1`，後 `1`；historical count=`0`。
- typed record content hash：前後皆 `61beba378c2a8efad67cd2772a8e75f04457b83c6d5b97afb35a55969bb70741`。
- episode count：`1 -> 2`，兩輪各一筆、episode id 不同。
- recall 的 profile writes=`0`、historical/negative/episode answer use 均=`0`。
- 兩程序、一次真正重啟、兩輪、retry=`0`、fallback=`0`、planner model calls=`0`。
- production memory、paid API、external deployment、Function tool、VRM action 都是 `0`。
- 沿用同一個現存 Uruha Safari tab；關閉使用者 tab=`0`。

## 與 P4-J 失敗的差異

P4-J 舊結果已正確把 typed state 解成 plan，但 normalization 後 contract 沒到 final logic，最後被 episode timestamp surface 取代，且 graph 無 P4-J node。P4-K 只修這條 propagation seam：若 final logic 遺失欄位，就從同一輪 `memory_data` 恢復已選中且已授權的 contract，先放回 final logic，再讓既有 visible guard 與 graph materializer 使用。這次真實 pass 表示修正已穿過完整 Web runtime；舊 P4-J failure 仍保留，沒有重寫或重跑。

## 下一個必要缺口

目前成功案例的寫入句用 English scope phrase，P4-I 因而儲存 canonical `drink`。現有 multilingual parser 對部分中文／日文 scope surface 仍可能儲存 `飲料` 或退成 `general`，而 P4-J query 已 canonicalize 成 `drink`；這會造成同一概念跨語言 exact-scope join 失敗。下一步 P4-L 應只處理「明示 preference write 的 scope alias canonicalization」，保留原 source language／hash，不碰 value localization、surface wording、baseline 或研究 claim。先做 before regression、凍結 single-variable contract，再實作；在新的 product acceptance freeze 前不送真實輪次。
