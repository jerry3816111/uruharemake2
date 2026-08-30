# M47：先判斷「要方法／不要方法」，再決定是否啟動行動生成

日期：2026-08-29。安全 worktree、opt-in Web 入口；M46 與更早證據均保留。結論是
**M47 route gate PASS；完整實用回覆管線仍 FAIL**。

## 為什麼需要這一個 M

M46 已能要求「目標 → 可觀察進展 → 一步動作 → 預期變化」，但正式 Safari 暴露兩個更早的
錯誤：`手順を一つだけ教えて` 沒被當成日文求助；`不要給我方法` 裡面的 `給我方法` 反而
被當成中文正向授權。若連使用者要不要方法都判錯，後面的行動生成再嚴格也沒有意義。

M47 的單一變因因此只有 **current-turn desired-response scope**：把任務內容與使用者期待的
回覆形式分開，判斷這輪是否明確授權或禁止 practical help。它不生成答案、不放寬 M46、
不修改 34 秒預算，也不把 M46 的成功與否反推成路由標籤。

## 真正實作

- 新增 `uruha_crosslingual_help_routing_m47.py` 與 `uruha_web_ui_m47.py`。中文、英文、日文
  的正向求助與否定範圍用有界 request pattern 表示；單獨出現「方法／method／アドバイス」
  不再等於求解請求。
- `不要給我方法` 同時含有表面正向子字串 `給我方法`。M47 先移除完全落在否定 span 內的
  假正向 cue；若後面有不重疊的新請求（例如「不要泛泛的方法，給我一個具體步驟」），
  仍以後面的 replacement 為準。
- 日文補足舊 M36 沒涵蓋的 `手順を一つ` 反向詞序，但仍要求 `教えて／決めて` 等請求頭，
  不因普通提到「手順」就觸發。
- trace 保留 current input 的 `start/end/length/digest`，可以在當輪還原 task clause 與
  desired-response clause 的來源位置；不把原文複製成心理事實，`long_term_memory_write=false`。
- runtime 新增獨立、唯一、相連的 M47 node。圖卡顯示：語言訊號 → 回覆形式範圍 →
  任務證據位置 → 實際策略 → M46 是否應／實際介入 → 路由驗收。卡片明說只證明路由。

## 開發失敗沒有抹除

修正前的實測基線是：日文要一步 `selected=null`；中文不要方法卻
`selected=solve_regulation`；普通說「我看過這個方法」雖沒有 explicit route，底層仍產生
`solution_request=0.98`。第一版 M47 又因正向子字串起點較晚，仍讓 `給我方法` 蓋過整段
`不要給我方法`；之後才加入「正向 cue 完全落在否定範圍內就無效」。

第一次擴大回歸命令也因 zsh 不自動拆分變數，把 38 個檔名當成一個參數而跑了 0 個測試；
該結果未被當成通過。改為明確命令替換後才得到最終 275/275。

## 契約與回歸證據

- M47 新契約加既有 M25/M36：**17/17**。涵蓋三語正向、三語禁止、否定後 replacement、
  一般名詞提及、source geometry、runtime policy、graph/card 與 protected-risk 不被覆蓋。
- M16–M46 選定 38 檔加 M47：**275/275，42.81 秒**；3 個警告仍為 SwigPyPacked、
  SwigPyObject 與 `aifc` deprecated。這不是全歷史 repository suite。
- `git diff --check` 通過。原 checkout 與安全 worktree 正式 Chroma DB SHA256 仍分別為
  `9bd050...895f`、`eb3483...cf4`。

## 正式隔離 Safari 六輪

session `20260829_215140_740eebe1`，同一個既有 Safari 測試分頁從 7887 導向隔離的 7888；
沒有新增或關閉其他分頁。六個輸入均以貼上方式核對 CJK 原文。

| 案例 | M47 路由 | M46 | 可見結果 |
|---|---|---|---|
| 日文書架，要一步 | authorize → solve | 進入 | reviewer timeout；未交付 |
| 中文信件／收據，要一步 | authorize → solve | 進入 | plan rejected；未交付 |
| 日文不要方法、只聽 | forbid → listen | 避開 | 自然日文傾聽 |
| 中文不要方法、抱怨 | forbid → calibrate | 避開 | 不再誤 solve，但重複問方法或傾聽 |
| 英文空白報告，要一步 | authorize → solve | 進入 | 本輪 plan rejected；未用過去成功覆寫 |
| 中文只提到方法 | no explicit help | 避開 | 不誤 solve，但表面仍過度追問回覆形式 |

後端稽核結果：路由 **6/6**、日文 **6/6**、三個正向案例進 M46 **3/3**、三個非正向案例
避開 M46 **3/3**。但是實際 action delivery **0/3**；禁止方法的表面遵守只有 **1/2**。
所以 `route PASS` 不等於 `practical help PASS`，更不等於被理解感。

## 圖像與證據邊界

- `m47_safari_route_card_2026-08-29.jpeg`：真 Safari 的六節點路由卡；目前顯示一般提到方法
  沒有啟動 M46。
- `m47_safari_six_turn_chat_2026-08-29.jpeg`：正式六輪後半段可見對話，保留被拒絕的 M46
  回覆與兩個仍不自然的澄清。
- `m47_isolated_safari_result_2026-08-29.json`：逐輪 route、policy、span geometry、M46
  intervention、action delivery 與日文輸出稽核。

這是 scripted development evidence，不是獨立 holdout。沒有盲評、沒有真人被理解感、沒有
跨模型或長對話優勢，也沒有證明人腦方程式。

## 完成與下一個 M

M47 真正完成的是：**跨語言「要一步／不要方法／只是提到方法」能先在當輪被分範圍，並
可靠決定 M46 應介入或避開；錯誤不再被藏在最後一句裡。**

Web 首次結果同時指出兩個後續缺口：三個正向路由全到達、卻 0/3 交付；中文禁止方法雖
避開 solve，仍出現多餘的二選一澄清。下一個 M 必須一次只動一項。由於正向 practical-help
是 M46–M47 的主因果鏈，而目前交付率為零，M48 優先處理 **跨語言 action realization**：
在不改 M47 route 與 M46 usefulness gate 的前提下，讓中／日／英任務內容能穩定生成含
實際物件、操作與可見停止點的自然日文候選。中文 no-method 澄清連續性保留為下一個獨立 M。

