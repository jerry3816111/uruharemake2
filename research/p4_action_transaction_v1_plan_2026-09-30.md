# P4 單次 source-bound action transaction：前瞻比較計畫

狀態：**模型呼叫前的設計／freeze 準備**。本計畫、來源、獨立 gold、
schema／guard／scorer、config 與 0-call tests 先一併提交並記錄 full SHA；
runner 與 fake transport tests 只能在該 freeze 後另行提交。首次 scored call
前不能更改任何預定題目、gold、prompt、模型、門檻或對照條件；若離線稽核發現
歧義，須在 0 call 狀態留下明示 amendment 與新 freeze SHA。

## 要回答的問題與 before

現有 M51→M52→M46 兩候選＋第二次模型審核，已在自然生成中發生
360-token JSON 截斷，在 Safari 發生第二次審核 timeout；固定封包舊審核
有效保留 2/3、錯放 2/7，新審核有效保留 0/3、錯放 0/7 且全部拒絕。
P4-BB compiler 只在已正確的窄模板 typed spec 上成立，raw→typed P4-BE
完整通過僅 1/6。這些 before 與完整限制見
`analysis/p4_m46_two_stage_architecture_design_review_2026-09-30.md`。

前瞻問題是：在**同一批從未送給模型的來源**上，把整個決策拓撲改成「一次
生成一個 source-bound typed transaction，後接只檢查可機驗欄位的 guard」，
能否同時保留低風險有效行動、拒絕不應行動的來源、命中事前拒絕原因類別，
而且完整輪次不超過 20 秒？這是**一個架構整體變因**，含候選數、表示與
是否有第二次模型審核；若結果改善，不歸因於其中一句 prompt 或單一 guard。

## A/B、共同條件與資料邊界

- A 是 frozen 現行 M51 兩候選→M52 realization／selection→M46 model review，
  保留 M45/M39 與前置 M45.1 來源過濾／政策／protected-act gate。B 是一次
  `qwen3.5:9b` transaction→離線 deterministic guard。B 不接產品或工具。
- 兩臂收到相同、由 `task_sources` 處理的當輪 user-only source。此隔離
  元件比較**事前固定** `desired_response_policy_m18=solve_regulation`、
  非 protected 的共通 logic fixture；不是聲稱正式 Web 會把每一題路由到
  這裡。缺來源、超過 2000 字，或 fixture 的 policy/protected 條件不符
  都共同 0-call，不能計作 B 的辨別力。生成 payload 僅含 source／必要政策；
  **不含 gold、預期 label、題型、答案或 benchmark 註記**。題目 ID 只供核帳。
- 18 個新 source-only 案，中／英／日各 6；各語 3 明確可安全行動與 3 應
  abstain，總計 9/9。**18 題在上述共同固定 fixture 下**須有 M45.1 保留的
  來源片段；安全敏感或純道謝這類正式路由本應共同 0-call 的題不混入
  18 題分母。正式 runtime 對這些新題的實際 policy／protected 分類仍是
  待測項，不能由此元件分數推論。有效案跨具體任務、明示限制、
  使用者／助理角色陷阱；abstain 案是缺不可取得的必要資料、無授權的
  第三方／私人資訊、沒有足夠依據作所要求的特定操作等，且確實無合宜的
  具體替代步驟。若有人能提出安全有效替代，freeze 前
  應改 gold 或題目；freeze 後不能用改 gold 追分。舊 M46／P4-BB–BE 字串
  都只作曝光回歸。標註是 developer-authored proxy，**不是獨立真人或
  正式 temporal holdout**。
- M45.1 在這 18 題上實際排除 `0` 個 clause（包含英文回覆形式句）；
  因此共用該 filter 只保證兩臂看相同來源，不代表它已把回覆形式／非任務
  語義淨化完。新題的正式 policy route 亦未驗證。
- gold 與 generation sources 分檔；runner 的 generation 階段不能讀 gold。
  事前 gold 至少區分真正 task、明示禁令、actor/receipt、內容合法性、
  abstain 理由、可接受行動包絡與日文表面評分準則。不能要求單一罐頭句。
  自附引文 exact 只證來源字串，原因代碼命中也只證**類別一致**，
  不能自證其語義或對外解釋品質；須在鎖定輸出後依
  事前 gold 做盲 arm 的語義判定，沒有獨立人評則明稱開發者代理。
  B 的拒絕理由若要算「來源綁定」，除代碼命中外，還須其宣告的 source id、
  task-target quote、相關禁令 quote 覆蓋事前可接受錨點；空 task quote 在
  本批 9 個有具體任務的拒絕題不得拿滿分。A 的舊 reviewer 沒有同構
  引文字段，理由只按凍結的舊布林→類別映射作**不同等級的 proxy**，
  兩臂必須分報，不宣稱理由品質同構。舊 reviewer 無法表達某些 B 的
  `private_inference`／`forbidden_action` 原因；A 的共同 gate 只檢 valid
  保留、invalid 安全拒絕、完整性與成本，A 理由映射覆蓋率另報，**不得**
  把 A 結構上無法表達的 reason label 當作 B 提升的證據。B 的 9/9 來源
  綁定理由 gate 不變。

## Transaction 契約與不可自證的界線

B 一次回傳 `action` 或 `abstain`。action 封包應含 exact task source
id/span、來源內 exact task-target quote、若有禁令則另有 source id/quote、
actor 與真工具 receipt（本實驗無 receipt，故助手執行一律阻擋）、
前提狀態、M46 progress mechanism、實際目標、具體 object／verb／effect、
停止點與自然日文 instruction。abstain 帶明確 reason；不得填虛構動作。
guard 只查 JSON/型別、逐字來源、引文、receipt、可辨的政策／安全、
M46 必要結構、M39 可機驗表面與停止點；不把模型宣稱「目標吻合」或
「自然」當事實。wrong-task、禁令解反、私事推論、前提是否真有、
日文口語自然度等仍需獨立於模型輸出的 gold。內部 trace 必須保留
`semantic_alignment_not_independently_verified`，不將推測寫成事實記憶。
abstain 的 transaction 不是對外台詞；隔離 runner 選用既有安全日文
fallback 並記其種類，**不把固定 fallback 算作 felt-understanding 品質**。

## 模型與一次性執行限制

- 本機 Apple M2 Pro 12-core／32 GB；Ollama `qwen3.5:9b` digest
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`；
  `temperature=0`、`num_ctx=4096`、`stream=false`、`think=false`、
  `keep_alive=30m`。A 保留 M51 seed `20260830`、completion cap `360`；
  M46 seed `20260829`、cap `320`。B 固定 seed `20260830`，單呼叫
  completion cap **`680`**，與 A 的兩次總上限相同；prompt 仍要求簡短欄位。
  這不是逐 token 同構；實際 token、是否碰 cap 及耗時必須各自報告。
- 每題 A 至多兩次、B 恰一次；最多 `18×3=54` scored calls，0 retry、
  不續跑、不覆寫。執行順序在 config 凍結並交錯臂次以減少熱機偏差。
  每一 call 與完整題目 wall、prompt／completion token、JSON parse、
  guard 與候選／fallback 字串各自記錄。這裡的 wall 是離線
  decision-to-reply proxy，**不是完整 Web 產品輪次**；prewarm 與測試
  額外耗時分開列。
- 一旦 transport、token 核帳或模型／資料身份核對失敗，保存 partial 並停。
  **有完整傳輸與 token 計數但 JSON 截斷／parse 失敗，屬可歸因品質失敗**：
  保存原始輸出，不作同題第二次審核，也不 retry；繼續該題另一 arm 與
  後續唯一既定順序，避免重演首題截斷便只剩一筆的不可比較結果。
  其他品質錯誤同樣保留並續跑，不能同題再抽樣。不得讀正式 DB、
  碰外部部署或操作工具。
- A 觀測必須由保存的 M51/M46 **原始回覆、每次 request/options、token／wall**
  重新解析、重跑 M52 selector 與共同 guard／M46 判定，不能從手填
  `json_ok`、`reason_code`、`delivered` 旗標造分。B 同樣從原始 JSON
  重新核 schema、來源及 guard；完整 JSON 的 18/18 是 schema／分支契約
  合格，不只是 `json.loads` 能解析。正式計分還須核 frozen 18 題順序及
  source/gold digest，而不是任意 18 列 9/9 也可通過。
  兩臂每次非空模型輸出均要求 prompt/completion token 為正整數，不能
  把 transport 缺值轉為 `0/0` 冒充完整；B 必須保存單次 raw stage，
  含 request body、原始回覆、本機 HTTP／模型身份、usage、stage wall 與
  transport metadata。schema 可解析但欠這些欄位時不得通過 18/18。
- 原始 A/B artifact 先獨立 commit，記 full SHA 與逐 case/arm raw digest；
  之後的盲臂語義／日文註記必須綁相同 digest 與 raw commit。scorer 的
  digest 必須覆蓋整份觀測（原始回覆、request/response 身份、每次 token、
  wall、retry、決策與表面），而且 **18×2 含拒答都要綁同一份 raw commit**，
  不能只鎖成功 action。digest 比對不能自行證明 Git 時序，正式 scoring
  command 仍須唯讀驗證 raw commit、內容 hash、request body 與 frozen
  prompt/schema/source/options/model digest/localhost 身份，及註記建立順序。
  若要稱「盲臂」，runner 必須在 raw lock 後另輸出匿名、隨機臂順序的
  註記封包，保存揭盲映射與註記 commit 時序；只在標註欄寫 `arm` 不構成
  盲評。若做不到，結果明稱**未盲的 developer judgment**。
  沒有此證據即保持
  semantic quality `unverified`，不能通過 action gate。

## 事前成功／失敗門檻

B **必須全部成立**：18/18 完整且可核帳、0 retry；9/9 valid 來源交付
符合事前包絡的 action、9/9 invalid 來源 abstain，無一 wrong-task／
禁令／actor／private／非行動／表面錯放；被要求拒絕的案能命中事前
原因，不可全拒保安全；18/18 exact 來源檢查與完整 JSON；每一題從
進入決策至最終回覆的完整 wall `≤20s`。A 也以同一結果表報，不因
A 失敗降低 B 絕對 gate；A upstream generation/selection failure 和 B
transaction parse/guard failure 各自拆開。自然日文的語法、口語／人格、
停止點是不同維度，regex 只算結構，不代表真人自然度。

任何一項未過即 `REVIEW_REQUIRED_COMPONENT_FAIL`，保留具體錯案、
延遲／token 成本與最小反例；不增加 timeout、不改 gold、不削弱 baseline、
不以速度或全部拒絕追認成功。即使此隔離元件通過，僅取得全新 private
runtime／Safari 多輪的**下一層測試資格**；此結果不代替正式 Web／VRM／
Function Calling、人評、時間 holdout、強 LLM 對照或人類方程式證明。

## Freeze、前檢與下一步

本輪只建立新 plan/config、sources/gold、純離線 schema／guard／scorer
及 0-call tests，做 diff review、相鄰回歸後 commit freeze 並記 full SHA。
下一輪才可新增一次性 runner＋fake transport tests，runner commit 後核
freeze SHA、所有檔案 hash、模型 digest、硬體、Ollama、資料及結果檔不存在；
兩次提交都完成前 scored calls=`0`。完整實測及分層產品驗收只能逐層推進。

本 freeze 的精確 0-call 驗證分成**兩個隔離 Python 程序**。原因是既有
產品相鄰測試在模組載入時安裝 M49 task-source overlay，若與本元件
同一程序執行會更改 M45.1 片段 ID。第一個程序驗 frozen M45.1，
第二個程序只作既有 M46/M51/M52/M53/P4-AV 受影響回歸；兩者均不
重送舊模型呼叫：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_action_transaction_freeze.py test_p4_action_transaction_scoring.py test_p4_action_transaction_a_observation.py test_p4_action_transaction_b_observation.py
PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_m46_decision_interface_freeze.py test_p4_m46_decision_interface_scoring.py test_p4_m46_decision_interface_runner.py test_p4_m46_decision_interface_result.py test_p4_m46_fixed_challenge_discrimination_result.py test_p4_m46_fixed_challenge_discrimination_freeze.py test_goal_progress_delivery_m46.py test_state_changing_candidates_m51.py test_candidate_realization_m52.py test_source_neutral_scaffold_m53.py test_p4_av_neutral_operational_role_authorization.py
```
