# P3 GPT5 交接準備結果

2026-09-09：READY_FOR_GPT5_OFFLINE_IMPLEMENTATION。

已完成既有成本記錄收尾（commit `34bef3d`，121 tests）；定案 P3 三條件、共同歷史、所有 model paths、
共享資源上限、來源／annotation 分離、proxy rubric、成功／失敗分支、圖像展示與階段順序。
`GPT5_HANDOFF.md` 已限制第一項為 P3-A offline harness，附入口、允許檔案、命令與十類負案例。
`CURRENT_TASK.md` 已壓縮為當前工作，舊結果仍在 Git 與交接；長期完整方向在 `LONG_TERM_GOAL.md`。

準備檢查：

- `python3 scripts/verify_p3_handoff.py`：8 個靜態檔案 digest 及 accounting source 綁定通過。
- 純記憶體 12 種錯誤設計變體均被 `design_errors` 拒絕：少 baseline、開生成／取消審查、漏歷史、
  current-reply leak、跨 case state、換模型、retry、改budget、挑弱baseline、proxy冒充人評、假裝資料已放行。
  這驗證交接檢查器，不代表尚未實作的 P3 runner 已能擋這些錯誤。
- 沒有製作或讀取新的 confirmation；沒有 P3 model call／比較分數／human preference 結果。
- 已自審共同歷史的 system anchor 分布限制、9b native verifier 缺口、不可把 call 數當相同成本、
  格式檢查不等於日文自然度、抽樣單位必須 case、AB/BA 不是兩個獨立人評。

目前尚未交付：P3-A runner／tests／transport controls、corpus freeze、真實比較、50輪新壓力測試、Safari、真人偏好。
P3-A 做完必須回到 GPT6 review，才可按規格繼續 smoke。這是具體審查點，不要求每個一般步驟詢問使用者。

App 狀態與檔案分開：Goal 工具回報 usageLimited；工具沒有改 objective 介面。嘗試透過 Computer Use
編輯 Codex App 被拒絕，理由是該 App 不允許受控的安全限制。因此新 Goal 文字已備妥但 App 欄位未改、
未恢復自動續作，也沒有切換模型。使用者可在當前任務自行選 GPT5 再續作，不需要另貼舊聊天室。

官方 Goal 指南建議固定可驗收終點、驗證命令與 checkpoint：
[Follow a goal](https://learn.chatgpt.com/use-cases/follow-goals)。本次採取該方式整理目標；
它不提供本回合工具缺少的 objective 更新權限，也不能消除使用限制。
