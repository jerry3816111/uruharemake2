# P4 來源事件 surface：完整輸入一次性授權的零模型結果

狀態：**bounded research diagnostic 的零模型契約通過；一般產品安全與可見品質仍 FAIL／pending。**
本項沿用事前凍結的 `research/p4_source_event_surface_exact_input_capability_amendment_2026-10-24.md`、
題本和 approved SHA manifest，不改 f7/f8 生成、gold、對照資源或正式資料。source-only 凍結已以
`cb0f6f2561204b67a1472d45fb287af86ac48cbf` 推到 PR #435；以下產品實作結果不能倒稱為獨立 holdout。

## Before：安全反例與同起點

舊 opt-in surface 有固定 benign 題的局部保真，但有限動詞 veto 對 `万引きした`、`くすねた`、
所有權未明錢包可組出稱讚，而且 final audit 可能錯標 `matched`。兩個歷史 strict xfail 保留：
**這是一般聊天安全失敗，不因新的白名單研究入口而消失。**

改產品前，`p4_source_event_surface_exact_input_preimplementation_snapshot.py` 依五個舊 WIP SHA
只跑一次 fake M21，保存新 A 題的完整 post-M21 `logic+route_info`、初始狀態和實際 transient handoff
於 checkout 外的 0700 私有 root、0600 檔，不進 repo／正式 DB。私有原件
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-p4-exact-input-before-gd34s10c/raw-before.json`
SHA-256 `5864fc500118aad3073216ab9a5c7be12400858e01db1c18932246c76b6b8eda`；
初始狀態 `c0264726ab6adf52c31149bf5fdadd9ad80bb3ed7c0746899f80319f2a210842`、
normalized boundary 重建兩次同為 `0786953954e7b54bcf0b4e6535aaa922d963542427efa9a3c78d7911d332891a`、
實際 handoff `05032b9884d773291ac4f6a4acfe20327b9526f2532b419a40fbf7b8bfda8278`。
原始兩次 SHA 因時間欄不同，不能假說 raw byte-identical；同一份 raw 的 off/on 深拷貝 byte-identical。
此 before 捕捉器要求舊碼 SHA，改碼後預期拒絕重跑；它不是可於新 HEAD 重現的產品測試。

## 單一變因與可觀察改善

新的能力不是「會判斷善惡」，而是**只允許事先審過的兩個完整輸入**。發行端讀 frozen
`case ID→UTF-8 SHA`，每個隔離 prepared/current run 在私有 `.cache` 子目錄僅有一份 0600 permit；
Web queue-free 入口核全文、run、arm 與 owner/mode，`O_EXCL` 寫 spent marker 並 fsync，
之後同一 handler 的同步 Brain call 使用不可複製的私有 claim。缺 permit、改一個字、重用、重啟重用、
音訊及直接 Brain／Web 繞道，在認知／provider／記憶／第一個 `...` 前拒絕。
拒絕只顯示非角色狀態；可能在認知開始後才發現的異常，另標「可能已有內部讀寫」，不虛稱 no-send。
Gradio queue-free claim 以 browser session 分隔；同 session 重複事件在未保留前取消第一筆 admission，
已保留則不讓第二筆關掉第一筆。缺 session 身分拒絕。預設無診斷 flag 的聊天行為不變。

固定 P1 的 fake-provider 同起點比較：兩臂從相同 deep-copied post-M21 boundary 出發，
其本批測試夾具 canonical SHA 為 `40b9ff6b0eb84c14cbcd185e13a747e922cc5bac8c2b9f5b84e2c21b484c1ebe`。
default／off／on 在回覆前也逐臂核對同一 seed 的 memory、psyche、persona、model-blend、
history、LeftBrain、runtime/config／時鐘和 event queue canonical SHA；這是合成夾具的同起點證據。
**這個夾具與上述改碼前快照是不同合成起點，不能把兩個 SHA 說成相同。**
default/off 回覆相等；on 回覆通過來源／首次／本人／和紙封筒／完成動作、≤28 字、
final/episode/history/graph 對齊的純契約，例示 deterministic surface 為
`和紙の封筒を初めて自分で折ったんだ。やるじゃん。`；此句自然度／人格仍需真人核，
也不證明新的真 M21 候選或 Safari 會得到相同結果。兩臂共用一次 fake M21 回傳；
surface 處理 **0 新 provider calls**。未授權的萬引／侵占／錢包／明示不要鼓勵四例
在 Web contract 均 0 cognition、0 角色泡泡；不主張正式 DB no-send，尚未啟動真 DB。

## 驗證與界線

- 最新擴大受影響相鄰回歸（capability、Web、admission、完整 fake route、f7/f8/M29/personhood/graph）
  `330 passed, 2 xfailed, 1 skipped`，耗時 103.23 秒；`xfail` 是歷史未解安全失敗，
  `skip` 是改碼後不可重建的舊產品碼快照。compile 和 `git diff --check` 通過。
- 獨立只讀複核確認同初始狀態與 receipt 白名單已符合凍結契約，僅同意本 bounded 零模型範圍提交；
  不是安全或產品品質放行。
- 原生 Web Server／Safari Send **0**、真 provider **0**、正式 DB **0**、真人自然度評分 **0**。
  Gradio Blocks binding 有契約測試，但 browser session 的實際排隊時序尚未經原生 Safari 證明。
- 目前只證明前瞻限定輸入研究入口可在零模型路徑 fail-closed；不能宣稱通用善惡判定、
  錯誤回覆 no-send transaction、跨題優於強 LLM、完整「人類反應方程式」或 P4 完成。

## 下一個必要 gate

admission 部分註冊例外的零模型回滾核驗、off/on 同初始狀態斷言、圖上 receipt 的 reason/SHA 白名單、
擴大受影響回歸與獨立只讀複核已完成；只 stage 本批範圍 commit/push、核 PR exact head。
其後依凍結計畫才可在新的隔離 root，
用真 M21 對 A 做一次 off/on 條件式配對：每臂最多 1 generation、0 retry、
≤2000 provider tokens、≤20s，off FAIL／on final visible gold PASS 才能進新的 B 單次 Safari。
任一 gate 失敗即保留原件與 REVIEW_REQUIRED，不換題追分。B 仍須核泡泡／raw／guard／UTTERANCE／episode／
graph、成本、持久化、原生畫面；圖像 PNG/AX 不能保存則該層 pending。正式同模型比較、人評、temporal holdout、
VRM／Function Calling 統一驗收另保留 pending。
