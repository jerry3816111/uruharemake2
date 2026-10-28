# P4 admission token × Function Calling wrapper：前瞻單變因契約

狀態：**實作前 source-only 設計**。f2 原生 Safari 的一次送出已 strict FAIL，精確錯誤與原件見 `analysis/p4_turn_admission_stateful_f2_fresh_product_failure_2026-10-24.md`；f2 不重送、不改 gold。f0 pre-Send 與 f1 原始 route FAIL 亦維持原判。此項只修產品 Web 函式邊界；不宣稱已使真模型回覆改善。

## Before 與唯一變因

Web 的 `_submit_text_impl`／audio 在 opt-in admission 下把非空 `admission_token` 傳給 `_run_turn`。產品入口先裝 P4-C Function Calling wrapper，再裝失敗結果 truth overlay；truth overlay 透傳 `**kwargs`，P4-C wrapper 卻只接受舊六參數，所以普通聊天在未進 cognition 前 TypeError。唯一變因：**讓 P4-C wrapper 明確識別此 Web admission token，並只在非工具選中路由把它原樣交給既有原始 `_run_turn`**。不得吞任意 `**kwargs`、更動模型／prompt／生成參數、Brain、repair-cue、M29、Web journal/schema、背景、圖、DB 或 f2 題本。

允許修改 `uruha_product_function_calling_p4.py`，新增 `test_p4_admission_token_function_wrapper_contract.py`，以及本項計畫／SHA／結果／任務卡。現有 truth overlay 與 Web 只讀。P4-C status tool **被選中且有非空 token** 時，現在沒有經原始 Web `_run_turn` 的 cognition/admission lifecycle；不能默默忽略 token 並讓 terminal 看似 delivered。此項在工具 provider 呼叫前明確 fail-closed `tool_route_admission_unavailable`，不執行工具，不回覆假成功；無 token 的既有 P4-C tool route 保持原樣。完整工具輪 admission 是後續獨立交付，不併入此補丁。

## 順序、判準與資源

1. 本計畫與 preimplementation SHA 先 commit/push 並核 PR #435 exact head。新增測試先證修改前：經 P4-C＋truth overlay 雙層 product wrapper，普通聊天帶非空 token 應同值、僅一次傳到原 Web `_run_turn`，tool provider 0 次；修改前應精確紅燈 TypeError。另用現有隔離 fake Brain＋**真正 `uruha_web_ui` browser-bound text/audio submit**，經相同雙層 wrapper 核 token 到原 `_run_turn`，journal `arrival→admission_snapshot→cognition_start→cognition_end→terminal delivered`、fake Brain 每輪一次、0 tool provider。這不是 Safari 或真模型。另測不帶 token 的舊 kwargs byte-compatible；tool-selected＋token 應在 `RUNTIME.mark_activity()`、provider factory/invoke、status reader及原 turn 之前 fail-closed，Web journal 應為 `terminal error` 而非 delivered；tool-selected 無 token 繼續既有 read-only 限權／失敗圖契約。
2. 只做上述簽名、非工具路由條件式透傳與工具路由明確拒絕；再跑聚焦及 P4-C、Web admission、repair-cue／M29 相鄰零模型回歸、compile、diff review。成功為契約與現行 wrapper 組合零模型 PASS；任何 source SHA drift、selected path 能執行 provider、非 selected token 被改寫／重複、無 token regression 或 f2 gold 被改，即 FAIL。最多兩個有根據修正批次，仍失敗則 REVIEW_REQUIRED。
3. 此項真 provider calls=0、Safari Send=0、正式 DB writes=0、外部部署=0。修後 f2 **只作回歸，不再送真產品**。未來如要驗可見品質，須新 source-disjoint f3 題、事前 gold、T0/Tpre 私有不可變 snapshot、journal/成本／Safari gate，另凍結後一次送出／零重試。**已知產品限制：opt-in admission journal 下的 P4-C read-only status tool 暫時不可用，會在 tool/provider 前明確拒絕；未開 admission 的既有工具 route 保持可用。** 即使本項 PASS，也不代表 Function Calling status 工具在 opt-in journal 下可交付、完整 runtime 成本、人評、同模型優勢或長期 Goal 完成。
