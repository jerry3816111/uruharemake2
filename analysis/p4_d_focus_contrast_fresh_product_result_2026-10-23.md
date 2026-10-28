# P4-D-F-C：焦點圖對比修正的新隔離 Safari 結果

日期：2026-10-23。設計／新 c0/c1／preimplementation SHA 先以 `84540b7` 推到 PR #435；CSS-only 產品與 11/11 聚焦、208/208 受影響零模型測試以 `02c3e33` 在真題前推到同一 PR 並核 exact head。兩個 developer-authored source-disjoint 題只作 prospective product probe，不是 temporal holdout、人評或公平同模型比較；舊 f0/f1/f2 的 strict FAIL 不重寫、不重送。

## 隔離與逐輪原件

- Controller 建立新的 0700 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-rkaru1p7`。官方 ONNX archive 83,178,821 bytes／SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 複製到私有 0600 inode `48832458`，與主機 inode `4160298` 不同；六個官方檔案解到私有 cache。封鎖 Chroma `_download` 與 `httpx.stream` 的預熱得有限 1×384 向量、download entrypoint 0 次；不外推為 OS 層完全無網路。
- Zero-turn run `d716d6c3725eeb70`／PID 1001：首次 verify-ready 早於 listener，稍後同 PID HTTP 200 ready，沒有重啟；兩個私有 Chroma 的 embeddings／queue 0、web log 尚無內容，planned stop／原 PID 退出／7894 vacant。產品 run `fb27e8687df27aa8`／PID 1479 同樣首次 ready 探測過早，稍後同 PID ready；T0 私有 episode 0、profile 0。最後 exact planned stop、原 PID 退出、7894 vacant；stderr 僅見 librosa `pkg_resources` 警告與 Matplotlib 字體快取訊息，無可見下載或 traceback。
- 原生 Safari 只新開一個 localhost 分頁，明確用「顯示方式→實際大小」設定 100% 後送題。送前 `typeText` 曾把 c0 的 CJK 輸入弄壞，**沒有送出**；改用 paste 凍結原文並在畫面核對。c0/c1 每題各按 Send 一次、0 retry；沒有把錯字草稿計入實驗。測完只關本次分頁，總數 52→53→52，未關使用者其他分頁。
- 真正送出的兩行 raw 同一 session `20261023_023625_595d63d3`、turn 1/2。私有 `web_logs/conversation.jsonl` 2 行／3,609,554 bytes／SHA `2e4ea96b12ba063c11e9e02335c387082674341f3e55bb79a8c853945eb728f4`，未加入 Git。每輪 Safari 泡泡＝raw `assistant_reply`＝`logic.visible_language_guard.final_reply`＝`runtime_trace.blackboard` 的 utterance payload；D trace 狀態是 `source_admitted_current_user_report`、`source_authorized_plan_selected`、`visible_surface_status=matched`、`terminal_status=trace_and_episode_reported_match`。這是當輪一致性，不是全系統或長期記憶完成證明。

| 凍結輪次 | Safari 最終日文 | 圖、重載與私有資料 | user wait |
|---|---|---|---:|
| c0 本人決定銀色の港の北窓 | `そっちが2092年6月23日に翡翠の砂時計を受け取る場所を銀色の港の北窓に決めたんだな。` | 原圖 78 節點／113 邊；六卡 input→本人決定 D→選定 D→utterance→output→trace episode，標題與箭頭亮色可辨，reload 焦點仍是 c0；私有 episode 0→1、profile 0 | 15.7816s |
| c1 明示訂正藍色の天文台の西階段 | `訂正ね。そっちが2092年6月23日に翡翠の砂時計を受け取る場所を藍色の天文台の西階段に決めたって話な。` | 原圖 81／121；焦點改為本人訂正 D／訂正承接，回覆和六卡不用舊地點；reload 焦點仍是 c1；私有 episode 1→2、profile 0 | 11.653s |

Safari 工具畫面直接觀察到深底上的焦點標題與五段箭頭為亮色，六張卡在同一列，不需水平捲動；收起浮動 VRM 面板後，c1 六卡全部可見，重載後仍維持亮色。這是**目視可讀**，沒有 computed-style 或量測過的對比率。重載後側欄 Session 曾顯啟動 ID，焦點圖仍回復 c1；不能把側欄當作重載後同 session 的獨立證明。原生 `getScreenshot`／AX 是工具內觀察，**沒有保存 native PNG 或 AX 檔**；曾試一般 macOS 截圖鍵但桌面未出現檔案，因此 saved-visual gate 仍 FAIL，不偽稱有可重看原生截圖。

私有 SQLite 獨立讀取 `session_db`：兩筆 `episodic_memory` 各 `source=turn_episode`，User 原文與同輪可見回覆逐筆相符；`user_profile` 0。另一個 `memory_db` embeddings／queue 0。圖末端僅是 trace-reported episode，DB 持久化另由本次 SQLite 佐證。c1 `kind=correction_reported`，但 `correction_supersession=unresolved`；不能宣稱舊地點已永久撤銷或以後一定不會被召回。D tracker `model_calls_added=0` 不是整個 runtime 零模型呼叫或完整 token 成本帳。

## 嚴格判定

**本批 CSS 對比及窄義 D 圖像交付 PASS：** 凍結 c0/c1 在原生 Safari 100% 實際大小完成一次實測，兩輪皆在當輪與 reload 顯示來源相符的六卡主鏈，標題／箭頭可讀，原圖 node/edge 未刪；raw、guard、utterance、私有 episode 與回覆一致，2/2 等待 ≤20 秒。只有兩條 CSS 葉節點色規則；舊前後零模型 HTML 逐字不變，不能把本批寫成回覆或記憶能力改善。

**完整教師展示／整體產品仍 strict FAIL：** 無可落盤的原生 Safari PNG/AX，故 saved-visual 明確失敗；舊 f2 命題角色／日文地點歧義、D0–D10 whole-batch FAIL、D2/D5、`correction_supersession=unresolved` 均未解。沒有正式同模型比較、人類被理解感、temporal holdout、VRM 真人模型或 Function Calling 統一產品驗收；長期 Goal 仍 active。下一個產品項須獨立處理持久視覺證據或 f2 語義表面，先凍結單變因新題與判準，不回播已曝光題追分。
