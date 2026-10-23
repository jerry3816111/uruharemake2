# P4 admission token × Function Calling wrapper：零模型結果

狀態：**局部 Web／wrapper contract PASS；真產品及 f2 均未通過**。事前單變因計畫 `research/p4_admission_token_function_wrapper_contract_plan_2026-10-24.md` 先以 `48390dd` 推 PR #435；11 檔回歸暴露歷史 SHA 時間點混淆後，額外驗證器範圍先以 `research/p4_admission_token_function_wrapper_contract_amendment1_2026-10-24.md`／`92d3d02` 凍結、推送並核 exact head。f2 原生 Safari **一次 Send、strict FAIL** 的原因仍是 `admission_token` TypeError；本批沒有重送 f2，也沒有改 f2 題／gold／判定。

## 改了什麼、如何知道

產品的 P4-C wrapper 現明確接受 Web 的非空 `admission_token`。普通非工具路由只將 token 原樣傳給原 `_run_turn`，不增加 Function Calling provider 動作；無 token 的舊 keyword 形狀不變。read-only status 工具若被選中且有 admission token，因它目前繞過原 Web cognition lifecycle，會在工具、活動標記、status reader 與 provider 前以 `tool_route_admission_unavailable` 明確拒絕；無 token 的既有工具路由維持。未修改 Web、truth overlay、Brain、模型、prompt、DB、背景、graph 或正式資料。

新增的零模型測試先在改產品碼前得 **4 failed／1 passed**，四個失敗精確重現 f2 的 unexpected `admission_token`。修改後，真 `uruha_web_ui` 的 browser-bound **文字、音訊**送出均穿過實際雙層產品 wrapper，隔離 fake Brain 各一輪；每輪 journal 為 `arrival→admission_snapshot→cognition_start→cognition_end→terminal delivered`，token 全程同值、fake Brain 一次、tool provider/factory 0。工具選中＋token 的負控則 journal `arrival→admission_snapshot→terminal error`、沒有 cognition 或 provider/status/tool 額外活動；舊無 token 路由由既有 P4-C suite 驗證。

受影響 11 檔合併回歸起初 **166 passed／1 failed**；唯一失敗是舊 P4-C freeze verifier 把凍結時 adapter SHA 與現行故意修正的檔案比對。保留原 freeze JSON SHA `d52a8ae3...` 與舊 adapter 值 `7173e8c5...`，驗證器改從固定提交 `48390dd43c75a59358c2e52087aa95ee0771e9c3` 讀**當年的 Git blob**，並明確核原檔名；若 blob 缺失或 SHA 不同就失敗。現用 adapter 由新契約及本批 product SHA 獨立綁定。修後 11 檔 **167 passed、9 既有 warnings**（54.12 秒）；最後增補檔名綁定後，聚焦 2 檔 **7 passed、9 既有 warnings**（5.36 秒），Python compile 與 `git diff --check` 通過。所用 interpreter 是 `.venv/product_checks/bin/python`，真 provider calls=0、Safari Send=0、正式 DB writes=0。本批五檔 SHA 在 `research/p4_admission_token_function_wrapper_product_2026-10-24.sha256`。

## 邊界與下一步

- 本批只消除了 f2 已觀察到的 Web product wrapper TypeError，**沒有**新自然日文回覆、native graph、episode/記憶、真模型成本或 Safari 通過證據；f0 pre-Send、f1 原始 route、f2 product 既有 FAIL 均保留。
- 目前 opt-in admission 下的 selected read-only status tool 明確 fail-closed，屬已知產品限制；完整工具輪 admission lifecycle 需獨立設計／驗證。Web 選中工具的錯誤路徑對音訊暫存檔清理未在本次單變因內檢查，不能聲稱完善。
- 下一個真產品題必須是**新、source-disjoint f3**，先凍結題與 gold、T0/Tpre 私有不可變檔案樹證據、同 PID/session/DB、journal、Safari 可見日文／graph／episode、成本及嚴格失敗門檻，再在新 0700 隔離 root 單次送出／零重試。這是必要驗收，不是修後自動 PASS。正式比較、holdout、人評、完整 Function Calling/VRM 與長期 Goal 均 pending。

只在安全 worktree 工作；原始 dirty checkout、正式資料、無關 `output/graduate_application_report/` 不碰。
