# 目前任務卡

更新：2026-10-01。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 當前唯一工作：source-bound action transaction 的預熱相容性 amendment

**2026-10-01 首次啟動 0-scored-call 停止，負結果已保存：**
raw=`analysis/p4_action_transaction_v1_raw_2026-09-30.json`、commit=
`216f16b535bac5fbcfb73532facf61951a756b67`。Ollama 的預熱
`done_reason=load` 回覆沒有 duration pair，嚴格預熱核帳因此
`prewarm_failed_no_scored_calls`，案例 `0/18`、A/B `0/54`，沒有品質／
比較結果。不得覆寫或續跑舊 raw。研究計畫的 2026-10-01 amendment
只對此一實測回覆形式允許預熱 load-only 完成，正式 scored `/api/chat`
的 duration／token／wall 守門不變；新 raw 路徑另訂。
**下一必要交付：先提交 amended plan/config/freeze test，記新的 full SHA；
再修改 runner/evidence 的預熱契約與新路徑、fake tests，另提交／推送，
重新只讀前檢後才可送唯一新 scored 比較。** 18 題、gold、prompt、模型、
token、gate 完全不改。這算一個有根據的修正批次；若再失敗，依
`DEVELOPMENT_WORKFLOW.md` 審查而非無限重試。無關報告目錄不碰。

**2026-10-01 runner／evidence gate 已提交、推送並前檢通過：**
runner commit=`f25874a2f52a20fedc9a21b0aaf7f6ccd0b88c90`，PR #435 open
且 head 對應此 SHA；新工具離線 `123 passed`、既有相鄰隔離回歸
`93 passed`，0 新 scored calls。只讀正式前檢確認 18 題固定順序、本機
`qwen3.5:9b` digest、M2 Pro 32GB、凍結檔 hash、後凍結 runner commit
與結果檔不存在。獨立反例檢查抓出的祖先 commit 先曝光揭盲資料，以及
Ollama server duration 大於實測 wall 的假陽性，已加 fail-closed 與回歸。
下一必要交付是依 `research/p4_action_transaction_v1_plan_2026-09-30.md`
進行**唯一一次**新 18 題／最多 54 scored calls；0 retry、不可續跑。
完成後先獨立提交 raw artifact，才建匿名封包、鎖定開發者代理標註、
後揭盲與核 Git 時序／正式評分。若有 partial、品質或 20 秒成本失敗，
照原門檻保存負結果，不改 freeze/gold/runner 追分。元件結果不外推成
產品、Safari、真人、時間 holdout 或完整人類反應方程式證明。

**2026-10-01 模型前 freeze 紀錄（已履行，不是目前命令）：**
`8b5e7a8972b27402342596d5fe18064795b7a452`，PR #435 仍 open 且 head
對應此 full SHA。新契約 39/39、相鄰隔離回歸 93/93，0 新 scored calls；
無關 `output/graduate_application_report/` 未納入提交。此 commit 只是
前瞻設計／資料／評分契約凍結，不是模型或產品效果。當時下一必要交付是
一次性 runner、raw Git 證據 verifier 與 arm-masked annotation harness 的
模型前假傳輸驗證；此 gate 已由本卡頂部所列 commit 與前檢履行。
舊 M46 20-call FAIL 不重跑。

**2026-09-30 freeze 前設計紀錄（已履行，不是目前命令）：** 新的 18 題 source-only
中／英／日（各 3 action／3 abstain）與獨立 developer-authored gold、
A=M51→M52→M46 原始兩階段觀測重建、B=單次 typed transaction 的 raw-stage
觀測重建、共同守門與 scorer 已準備。B 的拒絕理由要求事前 source/target/
forbidden 錨點；A 舊布林 reason 覆蓋另報，不把它無法表達的類別當 B 優勢。
18×2 的 action/abstain 都須綁同一 raw commit；token、wall、request 與
response 身份也在 digest 內。固定 `solve_regulation` 非 protected 是**隔離元件
fixture**，不能當正式 Web route 證據。M45.1 原版 source filter 的獨立測試
與會安裝 M49 overlay 的相鄰產品回歸分兩個 Python 程序，防片段 ID 漂移。

本 freeze 的模型前離線測試：新四檔 `39 passed`、相鄰舊測試 `93 passed`，
均 0 模型呼叫；命令與 gate 見
`research/p4_action_transaction_v1_plan_2026-09-30.md`。原 M46 正式 20 calls
的 FAIL 不重跑；產品 M51/M52/M46/M45/M39、正式 DB、原始 dirty checkout 與
無關 `output/graduate_application_report/` 不碰。當時的下一動作是先提交
prospective freeze 並記 full SHA；此步已完成，後續以本卡頂部的 runner／evidence
gate 為準。
新 dataset／prompt／gold／scorer 一經 freeze 不改；若出現凍結缺陷且尚未送模型，
須保留 amendment 與新的 full SHA。元件分數不外推到 Safari、真人或產品。

**非獨立架構設計審查已完成，尚未實作或送新模型。** 見
`analysis/p4_m46_two_stage_architecture_design_review_2026-09-30.md`。在前兩次
reviewer 契約均 FAIL、M51 兩候選於 360 token 截斷、Safari 第二次審核 timeout、
P4-BE raw→typed packet 僅 1/6 完整通過的 before 下，選定下一個**整體架構變因**：
用一次來源綁定、單候選、含 task／禁令／actor／前提／effect／stop 證據的 typed
action transaction，加上只核可機驗證欄位的 deterministic guard，與現行兩階段
M51→M52→M46 同題比較。此設計不是第三次 reviewer prompt 小修、不是直接
移除 guard，也不把模型自附證據當語義真理。若缺真工具 receipt，不得聲稱助手
替使用者操作；產品路徑與正式記憶維持不變。

**下一必要交付：先事前凍結新 source-only 中／英／日案例與事前獨立於輸出的
task／禁令／actor／內容／日文／abstain gold、完整 A/B 拓撲契約、同模型／硬體／
總 token 上限、0 retry／單次呼叫、品質＋完整 `≤20s` 成本 gate、精確離線測試及
失敗分支。** 原 M46／P4-BE 題都已曝光，只作回歸。先做設計資料／scorer／
0-call tests 並 commit freeze，記 full SHA；再寫一次性 runner／fake transport tests
另 commit，前檢後才可送新的 scored calls。若 new B 沒有 valid 全保留、invalid
零錯放與 wrong-task／actor 原因辨別，或以全拒換安全、超時，即保留 FAIL；
即使元件通過仍需全新自然生成、private runtime／Safari 多輪與真人／holdout
分層驗收，不能先接產品。允許新研究計畫、config、dataset、離線 scorer/tests、
本卡及後續 runner／結果；不許改已凍結結果／gold、現有產品 M51/M52/M46/M45/M39、
正式 DB、原始 dirty checkout 或無關 `output/graduate_application_report/`。

### 本次 M46 失敗結果（保存歷史，不是目前的執行命令）

**2026-09-30 正式一次性結果為 `review_required_component_fail`，不得重跑、改題、改 gold 或追認 PASS。**
模型前 freeze=`7abf74579e7793c22d3111b149037d9d7bdc5393`，
runner=`0b1dcfcaa63f9ea5af51f5c95cfca94482925848`。本機 9B、同一選定方案、
兩審核介面各 10 題，20/20 呼叫完成且 JSON／tokens／source exact、0 retry；
另 1 guard control 兩臂 0 call 阻擋。A 原版 valid=`2/3`、invalid false action=`2/7`、
舊欄位映射理由=`5/7`、reviewer-only 中位／最大=`13.60179/14.72437s`；
B 新版 valid=`0/3`、false action=`0/7`、明確預定錯誤軸＋primary 理由=`0/7`、
中位／最大=`8.64255/10.78069s`。B 將全部 10 個方案判 `actor_capability=fail`，
9/10 以此為 primary；加速只是全部拒絕，沒有品質改善資格。兩臂都未通過絕對
品質 gate；B 不可接產品，既有 M51/M46/M45/M39 不改、不旁通。原始結果與反例
見 `analysis/p4_m46_decision_interface_result_2026-09-30.json`、
`analysis/p4_m46_decision_interface_failure_2026-09-30.md`。此證據只限 developer-authored
固定封包元件，不是自然生成、完整 20 秒 runtime、Safari、真人／正式 holdout、
強 LLM 優勢或人類方程式。

當時的下一交付是兩階段架構設計審查，而非第三次 reviewer prompt／gold／timeout
小修；現已完成並列於本卡頂部。正式 M55/M56 真人與 temporal holdout 依賴
仍未解除。無關 `output/graduate_application_report/` 保留不碰。

### 前瞻 freeze 與模型前狀態（保存歷史，不是目前命令）

**2026-09-30 freeze 準備已完成，尚未送新模型。** 研究計畫
`research/p4_m46_decision_interface_plan_2026-09-30.md`、
`configs/p4_m46_decision_interface_v1.json`、
`datasets/p4_m46_decision_interface_v1.json`、
`p4_m46_decision_interface_scoring.py` 與兩份 0-call tests 已齊。
新字串但已曝光類型的 developer proxy：10 個可交審封包（3 valid／7 invalid，
中英日）＋1 個共同 guard control；10/10 selector/source/M39 exact 可交審、
control 的原 guard violation=`nonprogress_or_unknown_mechanism`，0 scored calls。
新舊同一 selected plan，唯一變因是單次 review prompt＋schema 的判斷介面；
同一 9B／320 completion token cap、最多 20 review calls、0 retry。
`uncertain` 必須 fail closed 且不計為明確辨出錯誤；`evidence_jp` 的 quote
只是逐字來源錨點，axis-label hit 不等於引文語義充分或真人理由品質。
離線命令
`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_m46_decision_interface_freeze.py test_p4_m46_decision_interface_scoring.py test_p4_m46_fixed_challenge_discrimination_result.py test_p4_m46_fixed_challenge_discrimination_freeze.py test_goal_progress_delivery_m46.py test_state_changing_candidates_m51.py test_candidate_realization_m52.py test_source_neutral_scaffold_m53.py test_p4_av_neutral_operational_role_authorization.py`
=`77 passed`（模型前 amendment 後）。**當時先提交 freeze amendment 並記 full SHA，再新增一次性 runner／fake
transport tests、提交第二個 commit，才送唯一 scored calls；這些步驟已完成。** 未達元件絕對
品質／成本 gate 即保留 FAIL、停止 reviewer 小修；即便通過仍須新自然生成與
full runtime／Safari，不能接產品。產品 M46/M45/M39 不改、不旁通。無關
`output/graduate_application_report/` 保留不碰。

**模型前 freeze amendment：** 首次 freeze commit=`fa298078a47900c1963c252cf62875dc036cb711`，
其後獨立只讀稽核發現 B 允許引用英文 source、parser 卻拒 ASCII 引文，以及
3 個 valid 的 `〜てみよ` 口語 gold 歧義。新 scored calls 仍為 `0`，已在
`research/p4_m46_decision_interface_plan_2026-09-30.md` 記錄並只修 exact
source／instruction quote 的原語豁免（外圍仍需日文）、selected instruction 的
`〜てみて` 口語表面、相應 fake tests／hash；source、機制、gold label／預定錯誤軸、
模型及 gate 不變。修後相鄰離線測試=`77 passed`。當時已提交 amendment，並用其 full SHA
取代 runner 所綁的舊 freeze SHA；沒有用原 SHA 混過前檢。

### 此前設計審查與 before（保存歷史）

2026-09-30 的**非獨立設計審查已完成**：
`analysis/p4_m46_reviewer_decision_interface_design_review_2026-09-30.md`。
它沒有新的模型、產品或真人結果。舊固定封包 FAIL 不變；中文有效案的 `止めよ`
可能是 gold／口語標準歧義，英文有效案疑似把使用者手邊可查的材料誤當未知前提，
actor/surface 負例則漏判助理代操作。選定唯一下一架構變因為**同一 9B、同候選、
同前後 guard 與 320-token cap 下的 M46 單次 review decision interface**；原產品 M46
不動。這不是逐字 prompt 追分，prompt+schema 是一個可歸因契約整體；若品質／成本仍
失敗，即審整個兩階段架構，不再對 reviewer 做第三次小修。

**下一必要交付：先事前凍結全新中／英／日完整封包、內容與日文表面分開的盲於 reviewer
gold、原／新契約、分類映射、score、模型與成本 gate；0 scored calls。** 新舊介面
對同一封包各唯一一次；明確 valid 全保留、invalid／uncertain 零錯放、每類命中原因、
JSON/source/tokens 完整、0 retry、逐案 wall/tokens；reviewer-only `≤20s` 仍不足以授權
完整產品，之後須全新自然生成與 private runtime／Safari 的完整 `≤20s`。不能用舊九題
作新分數、不能修改任何舊 gold／凍結結果或直接改產品。下一步允許新增 prospective
研究契約／dataset／scorer／離線 tests 並更新本卡；先 freeze commit，再新增一次性 runner
與 fake tests，runner commit 前不送模型。精確離線命令及最大 scored-call 數須寫入 freeze。

### 前一工作：固定辨別力 FAIL 與設計審查的 before（保存歷史）

**固定 challenge-only 正式結果為 `fixed_discrimination_fail`，不得重跑或追認 PASS。** 事前 freeze=`41bb4f02edf1bab392a001e0043eda4368d57144`、runner=`668be4b`，8/8 個本機 9B 審核完成、JSON／tokens／source identity 全部完整、0 retry、0 M51 generation、1 個 guard control 未送模型。A 保留有效行動僅 `1/3`（要求 `3/3`），無效行動錯放 `0/5`，但類別對應理由只辨出 `4/5`；B 是隔離的無審核反事實，錯放預構造負例 `5/5`，絕不授權旁通。reviewer-only wall 中位／最大=`13.210155/14.4233s`，prompt／completion=`6,568/2,304` tokens；不是完整產品 20 秒證據。結果與 runner/freeze 相關回歸=`41 passed`。逐案反例、原始結果、事前邊界見 `analysis/p4_m46_fixed_challenge_discrimination_failure_2026-09-30.md` 與同名 `.json`。原 M51 第一題 360-token 截斷的 A/B 消融仍是 `INCONCLUSIVE / NOT RUN`，不能合併兩實驗成成功鏈路。

**下一個必要交付是非獨立設計審查，而非再送模型或直接改產品。** 有效中文封包因 `casual_japanese=false` 被拒，該「止めよ」措辭也可能與 gold 的自然日文要求不一致；有效英文封包因 `no_unknown_prerequisites=false` 被拒；actor/surface 負例聲稱助手替使用者關面板，`no_identity_or_role_error` 卻仍為 true，靠無關旗標阻擋。先分清 gold／表面標準不一致、過度保守、行動者漏辨三種原因，選一個有成本與反例支持的架構變因；若再做 scored 實驗，必須用新 source／新 freeze、明確品質與成本 gate。產品 M46/M45/M39 維持 fail-closed，不旁通、不提高 timeout、不改已曝光封包／gold／門檻。正式 M55／M56 真人依賴仍未解除。

### 前一階段記錄（已完成或失敗，不是現在的執行命令）

**2026-09-30 正式生成於第一個 M51 call 即停，整個 A/B 消融為 `INCONCLUSIVE / NOT RUN`。** runner commit=`e3c1c11c2180d6c7f617e5ec72c7162f26744ee8`；前檢通過後唯一執行，prewarm成功，第一個 call 17.63697s、prompt/completion=`462/360`，輸出在第二候選字串中斷，`JSONDecodeError`；360 tokens 正好碰凍結上限。已產生0/6完整 batch、1/6 generation call、0 review、0 gold、0 retry，結果檔不可續跑／覆寫。詳細原始證據與設計分支見 `analysis/p4_m46_reviewer_necessity_generation_failure_2026-09-30.md`。**下一步是先保存此 FAIL／結果回歸，再做非獨立設計審查**：優先考慮新凍結的固定 challenge-only M46 辨別力測試（只證元件辨別、非自然生成），若有價值再以新 source 對 M51 表示／token 資源做單變因修正；不可改本次 num_predict、重跑剩餘五題、把手工封包冒充生成、直接旁通 reviewer 或接產品。P4-AZ／BA／BC／BD／BE 的既有 FAIL 不變；正式 M55／M56 仍待真人資料。

P4-BE `REVIEW_REQUIRED` 設計審查已作出**非獨立**處置：目前 raw dialogue→typed-spec 自動路徑不接產品，P4-BB 的條件式 compiler 與 BC／BD／BE 失敗證據保留，不再用第三個小 prompt／gold 修正追分。理由、互斥替代方案與限制見 `analysis/p4_be_review_required_disposition_2026-09-29.md`。這不是上游能力 PASS 或產品交付，亦不撤銷 P4-BA/BC/BD/BE 的 FAIL。

下一個對使用者可見交付的最早瓶頸是：P4-AZ Safari 真實兩輪已把 source 與 M51 候選接好，M46 第二次 model review timeout，M45/M39 fail closed、沒有交付動作；P4-BA 同資料模型大小 2×2 的完整 action 全部 `0/2`，小 reviewer 又退化 always-reject。現在先定案**review stage 是否值得其品質／成本**的單一變因，不能直接旁通 reviewer 或拉長 timeout。依前述設計處置，下一卡要凍結全新隔離中／英／日 action cases、valid 與 wrong-task／unsupported specificity／private-inference／non-action／surface controls、相同 M51 frozen generator packet、A=既有 M46 review、B=相同 deterministic guards 但無 model review、事前獨立品質標註、嚴格 false-action／valid-retention／token／latency gate 及失敗分支。兩 arm 重放相同一次 generator 輸出，僅比較 reviewer 貢獻；B 若放錯行動不能因快而接產品。此設計不是完整強 LLM baseline，也不是人評。

**事前歷史快照，不是現在的執行命令：** freeze=`2d522885b939cdb9a3dfd6d8bf4a2786527b6f31`、runner=`e3c1c11c2180d6c7f617e5ec72c7162f26744ee8`。before、單一變因、同候選兩臂、來源與品質標註次序、模型 digest／硬體／tokens／20 秒產品 gate、0 retry、最多 20 scored calls 與所有 FAIL 分支已寫入 `research/p4_m46_reviewer_necessity_plan_2026-09-30.md` 和 `configs/p4_m46_reviewer_necessity_v1.json`。`datasets/p4_m46_reviewer_necessity_v1.json` 封存 6 個全新中英日 source-only generation cases + 9 個 hand-authored challenge packets；後者是辨別力控制，不是假裝 M51 自然生成。離線 scorer 只重放同一候選到 A=既有 review／B=共用 deterministic guards，B 不接產品；M39 是隔離的 final-surface 近似而非完整 M45。3 個 valid 與 5 個 reviewer challenge 均可進入共同 guard，1 個 guard control 兩臂先擋，沒有事後挑題。runner 增加兩階段固定路徑、freeze/model/硬體前檢、唯一生成與 review、生成 packet 與 blind gold 分開提交後才能 review、逐 call checkpoint／0 retry／partial no resume，評分後出錯亦保存已完成 call。相鄰離線命令 `PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_m46_reviewer_necessity_runner.py test_p4_m46_reviewer_necessity_scoring.py test_p4_m46_reviewer_necessity_freeze.py test_goal_progress_delivery_m46.py test_state_changing_candidates_m51.py test_candidate_realization_m52.py test_source_neutral_scaffold_m53.py test_p4_av_neutral_operational_role_authorization.py` = `66 passed`；當時尚0 model calls／0 product changes。事前流程要求先唯一生成、commit packet、blind-to-review 標註且 commit，再送 eligible A reviews；本次於第一步即失敗，因此後續階段未執行。若離線合格原仍需全新 private runtime／Safari 檢查自然日文、實際圖、source、durability、latency；本次沒有取得該資格。不改正式 BC–BE 凍結檔／結果、M51/M46/M45/M39 產品 runtime、記憶、人格或原始 dirty checkout，不架外部 server、不碰無關 `output/graduate_application_report/`。

## P4-BE 正式 FAIL 與 REVIEW_REQUIRED（保存歷史）

### 已封存的 P4-BE 正式結果（不得重跑、改題、改 gold 或追認 PASS）

P4-BE freeze=`90b4c4af2583f37a43997f9662485e81584fae04`、runner=`93938c6ed8d27393a24274cc62d5b5ff12d49751`。本機 `qwen3.5:9b` 對同一批 6 positive＋8 controls，以 P4-BC 原 prompt／P4-BE 新 prompt 各唯一執行一次：`28/28` scored calls 完成且 JSON 可解析、`0` retry、tokens 完整、controls `8/8`／`8/8`、false spec/source `0`。同題 paired BE-only full pass=`1`、BC-only=`0`、source identity 合法的 BE-only raw role/value uplift=`1`，但候選的**絕對門檻失敗**：typed=`5/6`、non-span=`3/6`、role/value evidence=`2/6`、完整 packet=`1/6`、normalized atoms=`11/18`、slots=`3/6`、compile／mechanism／自然日文各=`3/6`、full accept=`1/6`（均須 `6/6`，atoms須`18/18`）。原 prompt full accept=`0/6`、compile=`6/6`；局部一案改善不抵銷退步。新／原 prompt tokens=`16,843/12,811`、median call=`10.47381/10.11207s`，max=`16.079/15.32578s`。候選沒有選用，產品 runtime 未改。正式證據與逐案限制見 `analysis/p4_be_role_value_prompt_evidence_2026-09-29.json`、`analysis/p4_be_role_value_prompt_failure_2026-09-29.md`，結果回歸見 `test_p4_be_role_value_result.py`。

P4-BD 與 P4-BE 已是這條上游路徑的兩個有根據修正批次。**下一個必要交付是設計審查，不是第三個 prompt／gold 微調，也不是直接接產品**：用中文 request 漏「只給一個／現在」而新 prompt 修好，以及新 prompt 中文混入日文 slot、英文漏 `unknown_constraint_jp`／編造 literal `...`、日文把回答形式誤當任務完成限制這些最小反例，先選定一個可歸因的能力變因及成本。選項是 source-bound 結構化角色／條件表示與獨立驗證、只修 canonical 日文 slot materializer（不解 evidence）、或縮小六模板路徑並保留 fail-closed。若變更研究問題、baseline、資料、門檻或重大架構，需明確設計審查／凍結後才可實作；已曝光 P4-BD／BE 題只能作回歸，不能充當新 holdout。成功與失敗都須有實際前後例、成本、單元→fresh model→runtime/Safari 分層證據。P4-BE 收尾只允許本次正式 evidence／失敗報告／immutable 結果回歸與本卡；收尾後只可新增獨立設計審查與更新本卡，未取得設計結論前不送新的 scored model calls。原始 dirty checkout、正式私有資料、無關 `output/graduate_application_report/`、已凍結檔及外部部署均不碰。Codex Goal 不因本卡 `REVIEW_REQUIRED` 而標為 complete／blocked。

### P4-BE 事前設計與凍結（保存歷史；下述「下一步」均已執行，不是當前命令）

### Before：P4-BD 正式 FAIL，禁止重跑或回填金標

P4-BD freeze=`26fb89821d7d1b846ff3d83aa4209f8ecd8384e8`、runner=`b6362cd`；9B／4B 對各14個全新開發案例唯一執行，28/28完成、JSON／tokens完整、0 retry。兩模型 role-aware evidence／packet 都=`0/6`，normalized accepted atoms=`5/18`、`2/18`；strict single-gold仍各=`0/6`。9B positive normalized/non-span/downstream=`5/6`，4B=`5/6,4/6,4/6`；controls unavailable＋reason均=`8/8`、false spec/source violation=`0`、max=`15.05412/9.38962s`，但任何一個 failed positive gate 都不能被成本／control 通過抵銷。產品 runtime 未改、無 selected model。正式證據和限制見 `analysis/p4_bd_role_aware_evidence_failure_2026-09-29.md`；結果回歸是 `test_p4_bd_role_aware_result.py`。P4-BD 與 P4-BC 原題、契約、gold、prompt、runner及結果不得修補或重跑；P4-BD 題也成為 exposed development，非 holdout。

P4-BD 兩種不同原因必須保留：一部分是事前列舉 span 過窄的可能假陰性（例如 `我那疊收據`），另一部分是真正錯目標／錯條件／漏完成限制／source 翻譯（例如4B日文分頁 role 錯、英文 evidence=`会議メモ`）；兩個 invalid packet 還漏 `unknown_constraint_jp`。不能把全部失敗解釋成標註，也不能靠任何 source substring 放行。P4-BD 的 `18/18` hard-negative scorer 單測只是 evaluator 契約證據，不是產品能力。

### 事前選定的單一變因與設計 gate

P4-BE 是此上游問題**第二個、最後一個有根據修正批次**，只改 raw dialogue→typed spec producer 的「source-bound evidence 角色／值擷取」系統 prompt；不得同時移動 `unknown_constraint_jp`／canonical Japanese slots 到 deterministic materializer、改 P4-BB compiler、M51/M46/M45/M39、產品模型、公開 persona、回覆或記憶。只讀審查已比較 prompt-only、source offset／ID、template regex parser，選 prompt-only：依六模板既有語義保留 owner／predicate／肯否／quantity／completion，不加入新題字面例子。source offset 只能防非來源片段，不能防錯角色；regex 會把六題變硬編碼。審查見 `analysis/p4_be_source_bound_role_prompt_design_review_2026-09-29.md`，屬非獨立開發審查，不是人評。這只是最後一次有界修正，不宣稱 prompt 是最終認知架構。

下一步事前凍結**未曝光**的新 cases、source／role 語意 gold、hard negatives、比較 arm、prompt/schema、模型與硬體／token／latency 上限及成功／失敗門檻；新評測在同一批新 cases 用相同 evaluator 比較 frozen P4-BC producer prompt 與 P4-BE prompt，不得以不同題目分數當改進。只測 `qwen3.5:9b`，`2 prompts × 14 cases=28` 次 scored calls、0 retry；這不授權 4B 選型。若仍由開發者標註，標 `developer-authored proxy`；多解歧義必須在模型輸出前處理。先離線 scorer／negative mutations、fake transport，再 commit freeze 與 runner，才可唯一一次正式生成。未凍結前=0 scored calls。結果若仍不達事前完整 gate，保留 FAIL，提出最小反例與 `REVIEW_REQUIRED` 架構取捨，不再換下一個小編號追分。產品 Safari／圖像與正式研究層仍 pending，不因離線 runner 成功升格。

### 2026-09-29 P4-BE 事前凍結準備（歷史時點為 0 scored model calls）

已準備 `configs/p4_be_role_value_prompt_v1.json`／`.txt`、`datasets/p4_be_role_value_prompt_v1.json`、`p4_be_role_value_scoring.py`、`test_p4_be_role_value_freeze.py`、`test_p4_be_role_value_scoring.py` 及設計審查。新 source 與 BB/BC/BD 全文逐字無交集，六個 positive 逐模板且中／英／日各2，八 controls 理由各1；仍是固定 ontology 下的開發 proxy。對每個 role 凍結一個原文 window 和完整 target／predicate／quantity／completion anchors，18 個 source-exact hard-negative mutants 及6個 window 內漏關鍵 anchor 反例必須被擋；quote 邊界只作診斷而不作 gate，避免重犯 BD 的有限 alias 問題，但語法不自然的 anchor-complete 片段可能通過。兩 arm 同一 scorer 與資料，唯一 producer 變因是 P4-BC prompt evidence 指示變得 role/value 完整。`unknown_constraint_jp` 等完整 slots 仍由模型負責，漏填即 FAIL。

候選 9B 必須 positive typed／non-span／template／role-value evidence／full packet／slots／downstream compile／mechanism／自然日文各6/6、accepted atoms18/18，controls unavailable＋reason各8/8、false spec/source violation0、JSON14/14、tokens完整、max call≤20s；要說 prompt 帶來額外價值還須 paired BE-only full pass≥1、BC-only full pass=0，且至少一案 BC raw role/value FAIL→BE raw role/value PASS、兩 arm source identity 均合法，避免把 slot 修好誤稱 evidence 進步。兩 arm 均須 completed／parseable 才可解釋成對比較；baseline 其他 gate 與成本照報、不作 BE eligibility。strict single-gold與實際tokens／latency逐案照報。前置合格不接產品；正式結果若仍 FAIL，停止小修小補而輸出 `REVIEW_REQUIRED`。

先跑凍結與相鄰離線測試，成功後 commit freeze、記 full SHA；**不能先寫／執行正式 runner**。凍結後不可改 dataset、anchors、prompt、schema、scorer、gates、模型或成本上限。之後只能新增一次性 runner／fake tests（先 commit）與 evidence/result test/report/本卡。正式 preflight 應核 freeze SHA、hash、9B digest、M2 Pro 32GB、既有本機 Ollama、固定輸出不存在；prewarm 失敗不送 scored calls，每 arm/case唯一一次、0 retry，partial 不可續跑。精確離線命令：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_be_role_value_freeze.py test_p4_be_role_value_scoring.py test_p4_bd_role_aware_freeze.py test_p4_bd_role_aware_scoring.py test_p4_bd_role_aware_runner.py test_p4_bd_role_aware_result.py test_p4_bb_typed_action_compiler_freeze.py test_p4_bb_typed_action_compiler.py test_p4_bc_raw_dialogue_typed_spec_freeze.py test_p4_bc_raw_dialogue_typed_spec_harness.py test_p4_bc_raw_dialogue_typed_spec_result.py
```

目前允許修改：本卡、P4-BE 設計審查與 prospective dataset／contract／scorer／tests／一次性 runner，均須按 freeze→runner→結果分階段；不得改動 P4-BB／BC／BD frozen 路徑與原始 dirty checkout。只讀設計審查及 freeze 離線測試已完成；下一步先 commit freeze、再寫 runner，不得在 runner commit 前跑模型。P4-BD 收尾驗證命令：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_bd_role_aware_freeze.py test_p4_bd_role_aware_scoring.py test_p4_bd_role_aware_runner.py test_p4_bd_role_aware_result.py test_p4_bb_typed_action_compiler_freeze.py test_p4_bb_typed_action_compiler.py test_p4_bc_raw_dialogue_typed_spec_freeze.py test_p4_bc_raw_dialogue_typed_spec_harness.py test_p4_bc_raw_dialogue_typed_spec_result.py
```

## P4-BD role-aware evidence span evaluation：已凍結與失敗（保存歷史）

### 2026-09-29 模型呼叫前的設計／凍結紀錄（歷史時點）

Before 仍是下述 P4-BC 正式 FAIL；本卡唯一變因是**evidence span 的評分契約**。P4-BD 新增 6 個 developer-authored positive（繁中／英／日各 2、六 template 各 1）及 8 個不同 unavailable reason controls；與 BB/BC 完整 source 逐字無交集，但固定 ontology 語義重疊，**不是獨立 holdout**。每個 positive 的 3 個 role 有事前 exact-source candidate、hard negative 與 conservative `accepted_exact_spans`。兩次分開的 LLM-proxy 判斷在 54 個二元 label 中同意 `48/54`、完整 role-set `12/18`；六個分歧候選在模型輸出前全部從可接受集合排除。這不是兩位真人的 inter-rater reliability。原始判斷與非獨立設計審查見 `analysis/p4_bd_annotation_proxy_pre_freeze_2026-09-29.json`、`analysis/p4_bd_role_aware_design_review_2026-09-29.md`。

Freeze 檔限 `configs/p4_bd_role_aware_evidence_v1.json`、`datasets/p4_bd_role_aware_evidence_v1.json`、`datasets/p4_bd_span_annotation_candidates_v1.json`、上述兩份 analysis、`p4_bd_role_aware_scoring.py`、`test_p4_bd_role_aware_freeze.py`、`test_p4_bd_role_aware_scoring.py` 與本卡。先執行精確離線命令：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_bd_role_aware_freeze.py test_p4_bd_role_aware_scoring.py test_p4_bb_typed_action_compiler_freeze.py test_p4_bb_typed_action_compiler.py test_p4_bc_raw_dialogue_typed_spec_freeze.py test_p4_bc_raw_dialogue_typed_spec_harness.py test_p4_bc_raw_dialogue_typed_spec_result.py
```

已在 2026-09-29 的 freeze 準備版得到 `66 passed`、0 模型呼叫，之後完成 freeze commit `26fb898`。凍結後任何新題、gold、accepted span、prompt/schema、門檻及模型條件均不可改。runner 與其 tests 在正式呼叫前另 commit `b6362cd`，正式後沒有改 runner。

P4-BD eligibility 的事前數值：每模型 14 案，JSON `14/14`，6 positive 的 normalized typed／非 span exact／template／role-aware evidence／role-aware 完整 packet／canonical slots／P4-BB compile／mechanism／自然日文均 `6/6`；8 controls 的 unavailable＋reason `8/8`，false spec／source violation `0`，token accounting 完整，max scored call `≤20s`。原 strict single-gold exact evidence/spec **仍逐案和總數報告，但不作新的放行 gate**；這是本卡唯一評分邊界變更，否則 role-aware 即使正確也會被整包 equality 強制判 FAIL。仍保留 9B／4B、原 BC prompt/schema／full slots／compiler、M2 Pro 32GB、temperature `0`、seed `20260927`、`num_ctx=4096`、`num_predict=480`、固定順序各一次 prewarm、0 retry。最多 `28` scored calls；任一必要 gate 不過即該模型 FAIL，不接產品。若兩者過才按 median latency 再 completion tokens 選。

正式 runner 的 preflight 要核對 freeze SHA、所有 hash、模型 digest、硬體、Ollama 服務與新 evidence path 不存在；prewarm 失敗不送 scored calls，逐案 checkpoint，但 partial result 一律 FAIL 且不可續跑。P4-BC 舊正式題與 runner 不重跑／不覆寫。模型輸出之前不進 Safari 或正式 DB；P4-BD 結果只能是 bounded offline evidence，真實 Web、建議效果、強 LLM 優勢及人類方程式仍 pending。

P4-BC已依freeze=`1424f24`、runner=`4045947`唯一執行28 calls，正式 **FAIL**，不得重跑或改原gate。28/28 completed、JSON parse成功、token完整。9B的template／slots／downstream compile／mechanism／自然日文=`6/6`，controls unavailable=`8/8`，但gold-boundary exact evidence=`0/6`、control reason=`7/8`、max=`21.71181s`；4B controls reason=`8/8`且max／median=`14.39932/9.32895s`，但positive normalized／compile=`5/6`，日文atomic raw output雖選對template，漏掉required `unknown_constraint_jp`而fail closed。兩者false control spec=`0`，產品runtime未改。完整證據：`analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md`。

重要診斷：兩模型12組positive evidence atoms的required role set都正確，atom也全是原source exact substring，但與唯一gold邊界逐字不同，所以formal exact=`0/6`。部分是明顯合理的短／長span（`空白` vs `還是空白`、`收據` vs `桌上的收據`），部分仍可能角色不精確（`email` vs `subject`）。因此不能把P4-BC洗成PASS，也不能只要substring就算對。

P4-BD唯一變因是**evidence span評價**。P4-BC只作exposed development；用完全新raw-dialogue cases，在模型執行前為每個role凍結一組acceptable exact spans、允許的containment關係與語意改變的hard negatives。template、full slots、controls、9B/4B、prompt/schema、硬體、0 retry與20秒gate保持；不得同時把canonical slots移進deterministic compiler。正式判定同時報strict single-gold exact與role-aware score，前者不刪除。

先設計annotation contract與inter-annotation consistency proxy（至少兩組獨立規則標註或可重現雙標註；若沒有獨立人類只能稱developer-authored），commit freeze後才可新跑。若role-aware仍失敗，保留semantic grounding缺口；若通過，只能說span evaluator不再懲罰預先承認的等價邊界，不能直接接產品。canonical slot responsibility另留下一卡。

## P4-BC raw dialogue typed spec freeze 與結果（保存歷史，不是當前下一步）

P4-BB 已在 freeze commit=`a4dd116` 後 0 correction 一次完整 **PASS**：繁中／英文／日文 6 positive 覆蓋 M46 六種 allowed progress mechanism；compiled／exact expected plan／M46 structural／source exact／mechanism exact／自然日文／deterministic repeat 全為`6/6`。12 個 identity／provenance／schema／language／safety／unsupported controls 依預定原因 blocked=`12/12`，false plan=`0`。model call／raw dialogue trace／factual memory write=`0/0/0`，最大 compile=`0.00090479s`。產品 runtime 未改。完整證據：`analysis/p4_bb_typed_action_compiler_acceptance_2026-09-27.md`。

P4-BB 真正證明的是：**若**已有正確且授權的 source-bound typed task spec，下游 action plan 可以不用模型自由猜 mechanism，並可 deterministic、source-exact、自然日文、fail-closed 地形成。它沒有證明 raw dialogue 能正確產生 spec，也不能和 P4-BA 的 raw-source 兩階段時間直接相除；模板 coverage 只有六種 bounded action ontology。

下一個單一未證明邊界是 P4-BC：`new raw dialogue → source-bound typed task spec`。先事前凍結完全新的繁中／英文／日文 positive 與 ambiguous／unsupported／risky／third-party／private-inference controls；P4-BB cases只能作 exposed development，不得當formal。比較`qwen3.5:9b`與`qwen3.5:4b`在相同 schema、資料、硬體、temperature、seed、token上限與0 retry下，能否選對 template、複製exact source identity/span、擷取exact evidence atoms、產生合法日文slots，且unsupported輸出`unavailable`。

P4-BC gate 必須同時含 typed-spec exactness、P4-BB downstream exact compile、positive coverage、negative rejection、private/assistant source=`0`、完整tokens與單一model-call latency `<=20s`。任一模型只有全部通過才可作後續 integration候選；都失敗就保留負結果，不改產品。先commit P4-BB結果，再freeze P4-BC dataset／contract／tests；不得先改M51/M46/M45/M39或接Safari。

P4-BC freeze 已準備：6 個完全新positive（繁中／英文／日文各2，逐一覆蓋六個P4-BB template）與8個ambiguous／third-party／medical／financial／unsupported／no-action／quoted-meta／private-state controls；P4-BB來源逐字交集=`0`。9B與4B各對14案只呼叫一次，共28個scored calls，模型固定順序各prewarm一次且不計case latency；prompt、dynamic schema、case order、硬體、temperature=`0`、seed=`20260927`、num_ctx／num_predict與0 retry完全相同。

每個模型只有JSON=`14/14`、positive typed／exact spec／template／evidence／slots／downstream compile／mechanism／日文=`6/6`、controls unavailable＋reason=`8/8`、false spec與assistant/private source=`0`、tokens完整、max call `<=20s`才eligible。先commit本freeze後才實作一次性runner；任一近似答案、compiler僥倖可編譯或另一模型較好都不能洗掉該模型的failed gates。

## P4-BB typed action compiler freeze 與結果（保存歷史，不是當前下一步）

P4-BA 已依事前凍結的 2×2 配置各唯一執行一次，正式 **FAIL**，不得重跑或在結果後改 gate。20 個 scored model calls 全部 completed、JSON 可解析、token accounting 完整，所以這次不是 transport failure。四個 arm 都不具產品資格：`g9_r9` 的 generation structural／allowed mechanism=`1/2,0/2`、review fixture=`3/4`、full accept=`0/2`、max=`35.71618s`；`g9_r08`=`1/2,0/2,2/4,0/2,22.22539s`；`g4_r9`=`0/2,0/2,3/4,0/2,29.86752s`；`g4_r08` 雖唯一通過 latency（max=`16.78266s`），但品質為`0/2,0/2,2/4,0/2`。

兩個 generator 在兩案都選 `group_by_rule`，allowed mechanism=`0/2`；0.8B reviewer 接受=`0/4`，退化成 always-reject；9B reviewer 的 report relabel content checks 全通過，只因 surface flag 拒絕，不能證明真正辨別 task progress。exact source、自然日文、0 raw dialogue trace、0 factual-memory write仍保持。產品 runtime 未改。完整證據：`analysis/p4_ba_stage_model_allocation_failure_2026-09-26.md`。

這否定的只有「單靠較小的 stage model allocation 可同時保住既有品質與 20 秒成本」；不是人評、自然分布、強 LLM 比較、人類方程式或所有小模型的結論。

下一個單一架構變因是 P4-BB **typed action compiler boundary**。先事前凍結新 dataset／contract：deterministic 層只根據已授權 source、task kind 與明列 allowed mechanisms 產生可審計 slots；模型不能自行發明 mechanism，只能填寫或實現允許欄位。semantic progress 與 persona-surface 分開記分，但任一失敗仍 fail closed；unknown task 必須保持 uncovered，不得硬套模板。P4-BA cases只能作 exposed development，正式需全新中／英／日 action cases與 false-source／unsupported-task controls。

P4-BB freeze 已準備為 6 個全新 positive（繁中／英文／日文各 2，覆蓋 M46 六種 allowed mechanism）與 12 個 identity／provenance／schema／language／safety／unsupported controls。正式 gate 是 exact expected plan、M46 structural、source／mechanism exact、自然日文、deterministic repeat=`6/6`；controls blocked＋reason=`12/12`、false plan=`0`；model call／raw dialogue trace／factual memory write=`0`；max compile `<=0.01s`。

本卡只證明「already-authorized typed task spec → bounded action plan」；raw dialogue 如何形成正確 task spec 明確不在本卡。先 commit 這份 freeze，再只新增 `uruha_typed_action_compiler_p4.py` 與結果測試／證據；不得先改產品M51/M46/M45/M39或runtime model。即使offline全通過，也只授權另凍結 upstream typed-spec producer 測試，不直接授權 Safari 或產品接線。

## P4-BA stage allocation freeze 與結果（保存歷史，不是當前下一步）

P4-AZ real pair 已唯一執行並正式 **FAIL**，但把最早因果缺口往後推進：P4-AY 找到 1 個response-form／feedback ref、0 個genuine replacement task並只停在prior role；P4-AZ=`authorized_previous_turn_cjk_ellipsis`，source role仍為`unspecified`且0 rewrite；P4-AU=`prior_source_linked`，新增`prior:1` digest與T1 exact相同，assistant/private source=`0/0`。P4-AV/M53 integrity、graph ordering、2/2自然日文、2/2 durable、isolated Chroma=`2`均通過。

完整pair仍FAIL：M51生成2個候選、1個structurally valid；第一個model call完成`876+300` tokens，第二個M46 counterfactual review `TimeoutError`，M46=`counterfactual_review_unavailable`、M45 withheld、M39 fail closed，再次澄清而沒有交付動作。T1/T2=`3.507/38.1682s`，僅1/2達20秒門檻。正式pair不得重跑。完整證據：`analysis/p4_az_real_previous_turn_ellipsis_to_action_delivery_failure_2026-09-26.md`，result commit=`7a280c8`。

這個review timeout亦已在P4-AT、P4-AW、P4-AZ三個fresh Safari pair重現；不再把它當偶發錯誤，也不直接拉長產品timeout。P4-BA只回答一個資源配置問題：相同frozen M51 prompt/schema、M46 checks/schema、資料、硬體、temperature、seed與token上限下，generator=`qwen3.5:9b/4b`、reviewer=`qwen3.5:9b/0.8b`的2×2配置，是否有任一組同時保持generation structural validity、review positive/negative discrimination、full-pipeline acceptance與每案two-stage `<=20s`。

允許新增：P4-BA frozen dataset/config、freeze test、一次性offline benchmark harness、result evidence/test/report，以及本節更新。不得先改產品runtime、M51/M46/M45/M39、prompt、schema、gate、資料或既有正式結果；每個unique model/case只執行一次，0 retry。generation output可在不同reviewer arm重用以維持factorial歸因；所有arm正負結果都保留。模型依`9b→4b→0.8b`各做一次不計分prewarm並維持`30m`，prewarm耗時另記，避免把不同cold-load順序混入stage latency。

正式gate：generation JSON、selected structurally-valid及case-specific allowed progress mechanism=`2/2`；四個fixed reviewer fixture=`4/4`，不可always-true；full pipeline source exact、自然日文、M46 content/surface accept=`2/2`；raw dialogue trace／factual memory write=`0/0`；token accounting完整；各案two-stage最大`<=20s`。任何arm只有全部gate通過才可作後續產品整合候選；多組通過取median latency最低，其次completion tokens最少。全部失敗就產出負結果，不改runtime，下一步依失敗分支重設架構而非追分。

先完成freeze commit，再實作harness並跑唯一一次四arm評測；這只是development-only本機模型配置證據，不是人評、建議有效、自然分布、強LLM優勢或人類方程式。

## P4-AZ offline 與 real freeze 保存歷史（不是當前下一步）

P4-AZ於`ad2ca9b`事前凍結，只修exact previous-turn中文省略第一人稱的prior-source authority，0 correction一次通過完整offline gate：development=`1/1`；全新繁中／簡中positive authorized與exact source linked=`6/6`，deterministic fake-M45 downstream structural contract=`6/6`；third-party／quoted-meta／news-report／physical-object／resolved／hypothetical controls=`12/12` blocked且false source=`0`；P4-AY predecessor source=`6/6` preserved。target source role仍為`unspecified`=`7/7`，沒有改寫成明示第一人稱；exact feedback chain與typed trigger=`7/7`。

P4-AY task mutation、P4-AU non-role bypass、candidate/order、visible reply、新增model、factual memory、assistant/private source、raw trace、完整fresh字串patch=`0`。聚焦與相鄰回歸=`42 passed`；port `7891` sandbox preflight=`ready`且0 model／Safari／VRM-tool operation。這只證明frozen deterministic source-authority接線，fake downstream不是live建議品質。完整證據：`analysis/p4_az_previous_turn_cjk_ellipsis_authority_acceptance_2026-09-26.md`。

下一步先commit本offline結果，再事前凍結**完全新的**兩輪private runtime／Safari pair，不得重用P4-AX正式句。T1需建立subjectless Chinese exact executed `calibrate_need`；T2需為全新compound support＋response-form request，並分別通過P4-AX、P4-AY、P4-AZ、P4-AU exact source、P4-AV/M53、M46/M45/M39 visible immediate action。timeout、JSON parse failure、再澄清、generic promise、只有internal plan、缺席node都FAIL；須記錄日文、durability、graph、tokens、latency與0 assistant/private source。正式pair PASS也只是一條fresh product path，不是建議有效、人評、人類方程式或強LLM優勢。

## P4-AY offline 結果與 P4-AZ 來源（保存歷史，不是當前下一步）

P4-AY 於`5735fc9`事前凍結，只區分「同一問題的feedback／response-form constraint」與「真的換了問題」。完整 frozen gate 為 **FAIL**：development=`0/1`，全新中／英／日positive=`6/6`、controls=`12/12`、genuine topic replacement=`3/3` blocked、既有P4-AU positive links=`6/6` preserved。第一次實作 fresh=`5/6` 且predecessor統計錯算，唯一 correction 只補日文肯定語尾`だった`與already-present source計數；沒有改資料／gate／中文來源角色。

失敗原因已收斂到下一個既有guard：P4-AX正式T1的中文句省略第一人稱，M39 source role=`unspecified`；P4-AY證明T2沒有新task後，P4-AU仍以`prior_source_not_direct_user_first_person`阻擋。P4-AY保持`blocked_non_task_p4_au_guard`，沒有繞過它。P4-AX authority=`7/7` preserved；P4-AT mutation、P4-AU non-task bypass、candidate/order、visible reply、model、factual memory、assistant/private source、raw trace、完整fresh字串patch=`0`。聚焦與相鄰回歸=`33 passed`；port `7890` sandbox preflight=`ready`且0 model／Safari／VRM-tool operation。完整證據：`analysis/p4_ay_response_form_constraint_boundary_failure_2026-09-26.md`。

P4-AZ唯一能力變因是exact previous-turn CJK省略第一人稱的prior-source authority。只在typed cognitive-overactivity、direct current-user frame、無第三人／引用／report、exact earlier executed M44/P4-AT chain、P4-AX supported、P4-AY所有current refs已授權時，允許上一輪source role仍誠實保持`unspecified`但作為exact prior problem來源。先事前凍結新的中／日正例與third-party、meta、news/report、physical-object、resolved、ambiguous controls；不得改P4-AY task boundary、P4-AU其他guard、M45/M46/M39、prompt、model、memory、visible reply或本次獨立`JSONDecodeError`。offline通過後仍需全新Safari pair。

## P4-AX real 結果與 P4-AY 來源（保存歷史，不是當前下一步）

P4-AX implementation=`33fd460`、real pair freeze=`7d2bf25`。全新的兩輪 private runtime／Safari pair 已在 port `7889` 各唯一執行一次，完整正式結果為 **FAIL**，不得重跑、改題或改 gate。

新能力的真實產品邊界確實通過：T2 的 P4-AX=`bounded_support_composed`，把對 exact 上一輪澄清的支持與本輪 `solve_regulation/practical_help` request 分開；P4-AT=`closed_supported`、P4-AG previous resolution=`supported`，prediction id 精確相同。P4-AX node `66` 位於 P4-AT/P4-AG/temporal/utterance `67/68/69/70` 前；P4-AX predecessor mutation、P4-AU bypass、新增 model／factual memory／raw trace 都是 0。

完整 pair 的最早失敗是 P4-AU 把「給我一個步驟、能馬上開始、完成就停止」誤判成新的 independent task source，得到 `blocked_current_task_replacement`；雖核對到 T1 digest=`4ebe80e6d582690d`，但沒有加入 prior source。P4-AV/M53 因未到達不能計為 pass。另有獨立 downstream failure：M45 一次完整 model call 回傳非契約資料而 `JSONDecodeError`，M51 未執行、M46=`plan_unavailable`、M39 對 `practical_action_not_delivered_m45` fail closed。T1/T2 latency=`3.776/31.0372s`，calls=`1/1`，tokens=`1001+360`但 accounting incomplete。2/2 自然日文、2/2 durable、isolated Chroma=`2`、2/2 graph；Safari 展開 P4-AX/P4-AU/M45，0 tab 關閉。完整證據：`analysis/p4_ax_real_compound_feedback_to_action_delivery_failure_2026-09-26.md`。

P4-AY 唯一能力變因是：在 P4-AU 裡區分**本輪真正換了問題／主題**，與**只約束回答形式或動作形狀**。後者例如「一個步驟／立即開始／完成即停」，不應遮掉 exact 上一輪 problem source；前者仍必須 fail closed。先事前凍結全新中／英／日 positive response-form constraints，以及 genuine topic replacement、third-party、quoted/meta、receipt mismatch、非 practical policy 等 controls。不得改 P4-AT outcome、receipt identity、direct-user authority、M45/M46/M39、prompt、model call、memory、visible reply，亦不得同時修本次 `JSONDecodeError`。offline 通過後仍需全新的 Safari pair；本次正式 FAIL 永久保留。

## P4-AX offline 與 real freeze 保存歷史（不是當前下一步）

P4-AX於`4bd1664`事前凍結，只修同一當輪同時含有「明示支持exact上一輪澄清」與「本輪新的practical-help request」的bounded
compositional split。第一次實作為development=`0/1`、fresh positive=`9/9`、controls=`10/12`、predecessor=`6/6`，已保存；唯一informed
correction只讓offline harness傳入真實產品已有的M25 base-request trace，並修日文第三人稱報告與CJK hypothetical guard，不改資料／gate／
positive grammar／P4-AT結果／request routing／P4-AU／M46-M45／prompt／model／memory／visible reply。

修後development=`1/1`；全新中／英／日response-kind confirmation、need-direction clarification、pre-answer need-clarity=`9/9`；third-party／
quoted-meta／generic-confirmation／hypothetical controls=`12/12` unknown；既有P4-AT question support=`6/6` core exact保留。16個支持案例均為
exact receipt且current policy=`solve_regulation`；false support、predecessor mutation、P4-AU bypass、candidate rerank、visible change、model、
factual memory、raw trace、private truth、完整fresh字串patch=`0`。focused=`13 passed`、P4-AT～AX affected=`74 passed`；port `7888`
sandbox preflight=`ready`、0 model／Safari／VRM-tool operation。完整證據：
`analysis/p4_ax_compound_feedback_request_split_acceptance_2026-09-26.md`。

該階段後續要求是先commit本offline結果，再事前凍結**完全新的**兩輪private runtime／Safari pair；此要求已由上節的正式結果完成並封存。原 gate 要求為：T1需建立exact executed `calibrate_need`；T2使用未曝光
三語任一compound support＋request，必須P4-AX node在P4-AT/P4-AG/temporal前、P4-AT=`closed_supported`、P4-AU加入exact T1 source，並由既有
M51/M52/M53/P4-AV/M46/M45/M39真正交付可立即開始且有停止條件的日文action。timeout、再澄清、generic promise、只有internal plan均FAIL；
不能用P4-AW正式pair重跑。本offline PASS不改寫P4-AW real FAIL，也不保證後段model review會成功。

## P4-AW real 結果與 P4-AX 來源（保存歷史，不是當前下一步）

P4-AW offline結果、實作與事前凍結pair分別固定於`a0e8c4a`、`8487644`、`acb562e`。新的private runtime／Safari兩輪已在
port `7887`各唯一執行一次，完整正式結果為 **FAIL**，不得重跑或改gate。

T1新能力確實進入真實產品：中文省略第一人稱時，P4-AW=`authorized_current_user_ellipsis`且source role誠實保留`unspecified`；
P4-AS=`executed_and_committed`、M44 exact receipt=`p1-1-6c5f453019d919e9`、P4-AR authorized、P4-AG六候選與future lock均通過。
P4-AW沒有改source frame／trigger detector／候選排序／feedback／P1-P4-AR guard／visible reply，新增model／factual memory／raw trace／
private truth=`0/0/0/0`。這是P4-AW的real-product bounded PASS，不是完整pair PASS。

T2同時暴露兩個獨立失敗。最早是複合句`你剛才先確認我需要什麼是對的；現在給我…`沒有被拆成「支持前輪action」與「本輪新request」：
P4-AT=`closed_unknown`、`two_independent_acts=false`，P4-AU因`earlier_action_not_explicitly_supported`沒有加入T1 prior source。後段仍辨識
`solve_regulation/practical_help`並由M51產生2個不同且structurally valid=`2/2`候選、M52 realized=`2/2`；但兩次model operation只有一次完成，
第二次`TimeoutError`，M46=`counterfactual_review_unavailable`、M45=`withheld_model_unavailable`，M39對
`practical_action_not_delivered_m45` fail closed，最後又澄清而未交付動作。T1/T2 latency=`3.8869/38.1546s`；model attempted/completed=
`2/1`，已記錄tokens=`546+272`但accounting不完整。2/2自然日文、2/2 durable、isolated Chroma=`2`、2/2 graph；Safari展開AW、AT、AU、
AV、M45節點，0 tab關閉。另T1 logic有P4-AG exact binding，但blackboard沒有獨立P4-AG node，所以凍結ordering gate也誠實FAIL。

下一個單一能力變因只修**同一當輪同時含有對上一行動的明示支持，以及新的practical-help request**的bounded compositional split。
先把本次句子降為exposed development，另凍結全新的中／英／日正例與false-link controls；不得改receipt identity、current request routing、
候選排序、M46/M45 review與fail-closed、visible reply、prompt或記憶。修後本題只能作regression，仍需全新Safari pair。完整證據：
`analysis/p4_aw_real_cjk_ellipsis_to_action_delivery_failure_2026-09-26.md`。

## P4-AW offline 與 freeze 保存歷史（不是當前下一步）

P4-AW 只修 CJK 省略第一人稱時的 executed-action authority。契約於 `a0e8c4a` 先凍結；第一次實作只達 development=`0/1`、
fresh positive=`4/6`，但 controls=`12/12`、明示第一人稱 predecessor=`2/2`，失敗已保存。唯一 informed correction 只把 upstream 已有的
typed `cognitive_overactivity` compose 到 copied shadow state，不改 detector／資料／gate。修後 development=`1/1`、全新中／日文
subjectless positive=`6/6`、third-party／quoted-meta／news-report／physical-object／resolved／ambiguous-role control=`12/12` blocked、
explicit predecessor=`2/2` preserved；typed trigger與完整 P4-AS→P4-AR exact chain=`7/7`，false authority=`0`。source frame／detector／
P1-P4-AR guard／candidate order／feedback／visible reply／model／memory／raw trace／private truth／完整fresh字串patch變更皆=`0`。
focused=`15 passed`，affected total=`74 passed`（P4-AW 15＋predecessor/adjacent 59）；port `7886` sandbox preflight=`ready`，
0 model／Safari／VRM-tool operation。完整證據：
`analysis/p4_aw_cjk_subject_ellipsis_action_authority_acceptance_2026-09-26.md`。

這只證明 frozen CJK grammar 的 deterministic authority bridge；P4-AV 舊 Safari FAIL 不改寫。下一步須先 commit 本 offline 結果，再凍結
**完全新的**兩輪 private runtime／Safari pair，T1 是未曝光 subjectless direct-user cognitive-overactivity，必須 P4-AW final、P4-AS executed、
M44/P1/P4-AR/P4-AG exact、future locked；T2 才能驗 P4-AT support、P4-AU exact prior-source handoff、P4-AV neutral role、M53/M46/M45/M39
真正 visible practical action。題目、gate、port與no-retry先commit；generic promise、再澄清、timeout、只有internal plan都算FAIL。

## P4-AU 正式結果已凍結；P4-AV／P4-AW 的來源（保存歷史，不是當前下一步）

P4-AU offline freeze與修正後固定結果通過：development=`1/1`、全新中／英／日positive source handoff=`6/6`、9個false-link control正確阻擋=`9/9`，
deterministic fake M45 downstream structural contract=`6/6`，predecessor mutation／candidate order／新增model／factual memory／assistant或private來源／raw trace=`0`；
相鄰回歸=`85 passed`。它只把exact previous-user problem接到本輪action delivery，沒有放寬M45/M46/M53/M39。

`9c33ccc`事前凍結的全新中文private runtime／Safari兩輪已於port `7884`唯一執行，正式 **FAIL**，不得重跑、改題或改gate。前半整鏈通過：
T1 executed `calibrate_need`、exact M44 receipt=`p1-1-c47bcaefa644b5b4`、P4-AG六候選與future lock；T2 P4-AT=`closed_supported`，並把當輪
新要求分開判定為`solve_regulation/practical_help`。P4-AU=`prior_source_linked`，`prior:1` digest=`e0fcdf502c58532a`與T1 exact user source相同，
assistant/private fallback=`0/0`、raw trace／新增model／factual memory=`0/0/0`。P4-AU node index=`50`，在M50/M53/M46/M45/utterance
`51/55/56/57/69`前；Safari已展開核對。2/2自然日文、2/2 durable episode、isolated Chroma=`2`。

正式交付仍失敗：M45一次model call產生2個不同候選，但structurally valid=`0/2`；選中候選含2個quoted scaffold labels，M53判定
exact source=`0`、neutral role=`0`、unsupported=`2`，觸發`unsupported_concrete_scaffold_label_m53`。因此M46=`plan_rejected`、
M45=`withheld_goal_plan_failed`、M39對`practical_action_not_delivered_m45` fail closed，最後再次詢問而沒有交付立即步驟。凍結failed gates為
M45 delivery、M46 verified/content/surface、M39 practical act與generic clarification prohibition；T2=`711+288` tokens、`20.7275s`。
這證明exact跨輪來源接通與真正source-safe action delivery是不同gate；前者通過、後者失敗，不能宣稱felt understanding、人類方程式或強LLM優勢。
完整證據：`analysis/p4_au_real_source_bound_current_action_delivery_failure_2026-09-26.md`。

P4-AV唯一能力變因是**區分中性操作角色標籤與自行發明的具體主題分類**。P4-AU正式題只能作exposed development，不得重跑。先事前凍結
M53 development反例、新的中／英／日source-neutral operational-role positives，以及invented topical categories、hidden-priority／emotion／diagnosis labels、
source-quoted labels與unquoted controls。只允許對來源無關且不聲稱內容真值的操作角色做typed authorization；任意`「環境」「經濟」「社會」`或
`「重要」「不重要」`等具體分類仍須阻擋。不得改plan文字、M46 review、M45/M39 gate、候選分數／排序、prompt、model call、記憶或visible reply。
offline通過並commit後，才能凍結完全新的real Safari兩輪；PASS仍只證明一條source-safe action delivery產品路徑，不證明建議對真人有用。

P4-AV已於`3c5437d`事前freeze後0 correction一次通過offline：development=`1/1`；新的中／英／日source-neutral workflow-role
positive=`6/6`且predecessor M53原本全阻擋；invented topic／priority／emotion／diagnosis／preference／feasibility／attribute controls=`7/7`
仍阻擋；exact-source／existing-neutral／unquoted predecessor controls=`3/3`保持。plan mutation、candidate rerank、新增model、factual memory、
raw label trace、M46 bypass、M45/M39 weakening、visible reply及完整題字串patch=`0`。聚焦與相鄰回歸=`56 passed`；port `7885` sandbox
product preflight=`ready`、0 model／Safari operation。完整證據：
`analysis/p4_av_neutral_operational_role_authorization_acceptance_2026-09-26.md`。

P4-AV實作commit=`83ea808`。另於`2fdfbdd`事前凍結**完全新的**兩輪private runtime／Safari case，port `7885`正式執行在T1即 **FAIL**
並停止，T2未送、同題不得重跑。T1可見日文`ん、寝てないのか、考え事で止まんないのか、まずそこだけどっち？`確實執行澄清，M39=
`accepted_verified_surface`且policy act=`true→true`；但中文省略第一人稱使source frame=`unspecified`，P4-AS因`early_authority_exact`與
`direct_user_first_person`失敗為`not_applicable`，M44=`not_registered`，P4-AR=`blocked_unexecuted_shadow_action`。雖P4-AG仍有六個shadow
候選，temporal正確顯示current candidates=`0`、future=`not_available`。P4-AS／P4-AR／P4-AG／temporal／utterance index=
`64/65/66/68/69`，Safari已展開P4-AS節點；1輪自然日文／durable／graph=`1/1/1`、latency=`3.0913s`、0 model call。
P4-AV／M53未到達，所以不能把本次寫成P4-AV產品效果。完整證據：
`analysis/p4_av_real_neutral_operational_role_delivery_failure_2026-09-26.md`。

P4-AW唯一能力變因是**CJK省略第一人稱時的executed-action authority**。P4-AV正式T1只能作exposed development，不得重跑。先凍結新的中／日
主詞省略direct-user cognitive-overactivity正例，以及third-party、quoted／metalinguistic、news/report、physical-object motion、resolved-state與
ambiguous-role controls；只能在existing typed trigger、direct source、third_party=false、M39已驗證可見`calibrate_need`、exact P1 pending與plan identity
均成立時，將`unspecified`視為本輪direct-user ellipsis，不得把一般無主詞句都升成user-first-person。不得改trigger detector、candidate ranking、P1/P4-AR
guard、feedback、visible reply、prompt、model call、記憶或private truth。offline通過並commit後，P4-AV仍需另一組全新Safari pair。

原P4-AV real gate要求如下，保存作為失敗邊界：正式gate仍須
同時通過P4-AS→AT→AU exact來源鏈、P4-AV node在M53/M46/M45/utterance前、M53不阻擋中性workflow role、M46 content/surface verified、
M45 delivered、M39 practical act與自然日文／durable graph；generic promise、再澄清、model unavailable或只有internal plan都算FAIL。即使PASS也
只證明一條產品action-delivery path，不是建議有用的人評、自然分布、強LLM優勢或人類方程式。

## P4-AT 正式結果已凍結；P4-AU 的來源依據（保存歷史，不是當前下一步）

P4-AT offline在事前freeze後通過：17案的上一個action outcome與本輪request policy=`17/17`、development=`1/1`、全新中／英／日
positive=`9/9`、false-prior-link controls=`0/7`、unrelated unknown=`3/3`、exact receipt identity=`17/17`，候選分數／排序、model call、
factual memory與raw dialogue leakage變更=`0`。P4-AT只把上一輪observable action feedback與本輪response request分開，不改P4-AG classifier、
P1 identity、M44 truth、候選排名或visible reply；實作commit=`a1600e2`，相鄰回歸=`51 passed`。

另於`f2d1ecd`事前凍結完全新的中文兩輪private runtime／Safari case，port `7883`唯一一次正式執行為 **FAIL**，不得重跑、改題或改gate。
真正的因果閉環通過：T1以`calibrate_need`建立exact M44 receipt、P4-AG六候選與future commitment；T2把使用者支持精確綁回同一
`p1-1-54b3425d01de0b33`事件，P4-AT=`closed_supported`、M44/P4-AG=`supported`，並把當輪新要求另外辨識為
`solve_regulation/practical_help`。performed action strictly-earlier、prior future consumed、same-turn backdating=`true/true/false`；P4-AT／P4-AG／
temporal／utterance graph index=`66/67/68/69`，Safari可見；2/2自然日文、2/2 durable episode、P4-AT新增model/factual memory=`0/0`。

凍結的T2 action-act gate失敗：候選表面原為`今すぐできる一個だけ、一緒に決めよ。`，沒有真正交付步驟；M45嘗試兩次、完成一次model call後
`TimeoutError`，成為`withheld_model_unavailable`，M46=`counterfactual_review_unavailable`。M39因此對
`practical_action_not_delivered_m45` fail closed，最後可見為`今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。`；
T2 latency=`37.9706s`，高於20秒。唯一failed gate=`turn_2_m39_practical_act_count`。這證明「理解前一個行動的回饋」、「辨識現在要什麼」與
「真的做出現在要的行動」是三個不同gate；前兩個通過、第三個失敗，不能宣稱felt understanding、人類方程式或強LLM優勢。完整證據：
`analysis/p4_at_real_executed_action_outcome_closure_failure_2026-09-26.md`。

P4-AU唯一能力變因是**把剛才問題的source-bound context接給本輪明示action request**，不是放寬M39/M45或把timeout當成功。P4-AT正式兩輪已曝光，
只能作before/development，不能重跑。先事前凍結新的中／英／日兩輪：T1需有direct first-person problem context與真正executed receipt；T2需同時
包含exact action feedback與明示`practical_help` request。只有exact receipt identity、strict next-turn window、direct first-person ownership且本輪沒有
observable topic correction時，才可把T1的最小source atoms交給既有M45/M46；不得把persona推測、內部candidate、第三人稱、引用、過期或跨題內容當source。
fresh positive必須實際產生一個source-consistent、自然日文、可立即執行的步驟；controls需涵蓋topic correction、unrelated feedback、third-party、
receipt mismatch與timeout，全部fail closed。不得改P4-AT outcome、P4-AG/M44、候選分數、M39 action-act gate、語言guard、prompt、記憶真值或把 generic
promise-to-help算實際action。先freeze／commit，再offline implementation與回歸；只有另凍結全新real Safari兩輪後才能主張一條產品action delivery閉環。

P4-AU已完成offline freeze與實作。第一批凍結測試失敗保留：fresh positive=`4/6`、control正確阻擋=`6/9`；根因是日文省略主詞、M47 ref未切細、
metalinguistic predecessor guard未compose，以及expired fixture改了會被M44重算的衍生欄位。唯一一次informed correction不改題／gate／prompt／M39／M45，
只compose既有P4-AT direct-source guard、細分ref、為無third-party/meta的日文direct user turn處理主詞省略，並讓fixture真正改authoritative created turn。
修後development=`1/1`、全新中／英／日source linked與exact identity=`6/6`，九個third-party／meta／unrelated／new-task／identity／window／no-feedback／
wrong-policy／oversize controls誤加=`0/9`且block reason=`9/9`；六個positive以fake generation/review通過既有M45 structural contract=`6/6`，但這不是
live model品質或人評。候選score/order、predecessor source、model call、factual memory、assistant/private-inference source、raw trace變更=`0`；相鄰回歸
=`84 passed`，sandbox product preflight=`ready`。完整證據：`analysis/p4_au_source_bound_current_action_delivery_acceptance_2026-09-26.md`。

P4-AU唯一下一步是另commit本offline結果後，事前凍結**完全新的**private runtime／Safari兩輪，不得使用P4-AT或P4-AU任何已曝光句子。正式gate需同時看：
T1真正executed `calibrate_need`與exact receipt；T2 P4-AT支持閉環、P4-AU exact prior source handoff、M45/M46實際交付一個source-consistent且可立即開始的日文步驟、
M39 action-act match、P4-AU node在M50/M45/utterance前、2/2 durable與日文、實際model call/token/latency。timeout、generic promise、再問一次或只有內部policy正確都算FAIL；
即使PASS也只是一條fresh產品閉環，不等於人評、自然泛化、人類方程式或強LLM優勢。

## P4-AS／P4-AT 保存歷史（不是當前下一步）

P4-AS已完成offline、產品接線、開發Safari及正式one-shot驗收。offline prospective gate=`13/13`：development=`1/1`、
全新中／英／日positive=`6/6`、third-party／metalinguistic／resolved／ordinary-motion controls=`6/6`，M39 surface、M44 receipt、
product pending及P4-AR authority=`7/7`，false execution／role violation／新增model／factual memory=`0`。第一次開發Safari保留一個真實
FAIL：產品已先建立exact P1 pending，但P4-AS誤要求pending必須為空，所以receipt缺失、P4-AR阻擋。唯一一次informed correction只允許
pending absent或prediction/policy/turn/input全部exact；exact pending與ledger逐字保留，只補missing receipt，mismatch仍fail closed。
修正後全新開發Safari通過，完整正負證據保存在`analysis/p4_as_product_development_*_2026-09-25.*`。

實作commit=`81e6ba6`後另於`83bcb2c`事前凍結全新中文private runtime／Safari題，port `7882`唯一一次正式執行為 **FAIL**，不得重跑或改gate。
真正機制鏈通過：P4-AS=`executed_and_committed`、M39=`accepted_verified_surface`、M44 exact receipt、P4-AR=
`authorized_executed_product_event`、六候選pending、P1 sequence=`1`、temporal=`過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`；
Safari展開P4-AS／P4-AR／temporal，graph index=`65/66/67`均在utterance `69`前，logic→runtime exact，日文／durable embedding=`1/1`，
latency=`3.216s`，P4-AS新增model/factual memory=`0/0`。但凍結要求逐字
`今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？`，實際為
`しんどくて止まらないのと、楽しみで止まらないの、今はどっち寄り？`；兩句都實現`calibrate_need`，但exact surface=`0/1`，所以正式
failed gates=`turn:visible_reply`,`metric_mismatch:exact_visible_reply_count`。這證明action-level因果正確與逐字可重現是不同主張，不能用前者
洗掉後者FAIL。完整結果：`analysis/p4_as_real_selected_action_surface_execution_failure_2026-09-25.md`。

P4-AT唯一能力目標是**已執行行動的下一輪因果閉環**，不是追逐P4-AS逐字答案。先以P4-AS正式題作已曝光development，只讀驗證其M44 receipt
可被下一輪observable feedback精確連結；不得重跑該正式輸入。再事前凍結全新的兩輪中／英／日序列，至少包含：使用者確認要方法、確認只想被聽、
否定兩個選項／轉向其他需求，以及無關訊息保持unknown。T1必須有released visible `calibrate_need`、exact M44/P1/binding；T2必須把支持／否定／
未知綁回同一performed action，將T1 commitment從future移入strictly-earlier past，並在需要時撤銷或換policy，unknown不得算成功。表面驗收以事前固定的
action-act rubric與M39 observable surface contract為準，另記exact string但不把單一措辭混同理解；不得改P4-AG classifier、P1 identity、M44 outcome、
候選分數、語言guard、prompt或記憶真值。offline通過並commit後，才能另凍結完全新的private runtime／Safari兩輪；即使PASS也只證明一條
action→feedback→calibration產品閉環，不等於使用者偏好、人評、自然分布、人類方程式或強LLM優勢。

## P4-AS／P4-AR 保存歷史（不是當前下一步）

P4-AR在重新檢查產品因果語意後，沒有把P4-AQ的fallback硬升成P1 identity：P4-AQ所選`calibrate_need`只存在於late shadow，
released M18 decision仍是`not_applied`，M44 action receipt是`not_registered`，可見回覆也沒有執行澄清。若直接簽P1事件，下一輪會把
使用者反應錯誤歸因給未曾顯示的行動。P4-AR因此改為**executed-action authority gate**：只有existing desired decision、applied
decision／plan、exact product pending及registered receipt全部綁同一真正P1事件與policy時才允許outcome verification；fallback不能升P1，
P1 guard不降低。

offline freeze／implementation與相鄰P4-AD～AR回歸=`144 passed`。事前另凍結一個全新English one-turn private runtime／Safari case，
唯一一次正式執行為 **PASS**：P4-AQ先`0→6`候選並選`calibrate_need`；P4-AR正確得到
`blocked_unexecuted_shadow_action`，保留6個候選供查看，但current binding=`not_available/0`、temporal=`過去 0｜現在 0候選/選択 なし｜
本輪未來 無承諾`，fallback→P1=`0`。graph index為guard/order/binding/temporal/utterance=`64/65/66/67/68`，四個logic→graph
payload exact且Safari可展開guard；日文／durable episode／graph=`1/1`，等待`17.6066s`，P4-AR新增model／factual memory=`0/0`。
完整證據：`analysis/p4_ar_real_executed_action_identity_gate_acceptance_2026-09-25.md`。

這個PASS只證明**不替未執行的內部候選造假後續驗證**。可見回覆
`うちの頭は考えで埋まって今夜落ち着かないんだね。`雖為日文，卻把使用者第一人稱誤成角色的`うちの頭`，也沒有真的執行
`calibrate_need`；因此不是felt understanding、語意忠實、使用者偏好、預測正確、人類方程式或強LLM優勢證據。

P4-AS下一個唯一能力變因是**selected-action surface execution**。先把P4-AR已曝光case當development反例，不重跑正式題；再事前凍結
新的中／英／日cognitive-overactivity正例與speaker-ownership／resolved／literal controls。只有當P4-AF/AD已授權且選出一個bounded action，
才允許在M39之後以source-bound proposition與persona約束把該action實現為自然日文；`calibrate_need`必須是短、低壓、可否定的澄清，
不得把候選心理狀態說成事實。visible surface真的表達該policy後，M44才可登記exact executed receipt並由既有P1簽發下一輪事件；若surface
未表達、ownership錯、M39拒絕或receipt不一致，一律fail closed且不得建立future commitment。不得改AH detector、AF authority、AD候選
分數／排序、AG feedback classifier、P1 guard、記憶內容、persona facts或新增模型call。離線通過並commit後，才能另凍結全新real
Safari case；即使通過也只證明選擇→表達→receipt→可驗證事件的單一路徑，不等於使用者喜歡、預測正確或研究全面優勢。

P4-AM與P4-AN各保存一個不同的真實產品FAIL：P4-AM的temporal payload存在於logic但被最後一次blackboard refresh覆蓋；P4-AN已修好
post-turn delivery，Safari也能在utterance前看到節點，但全新P4-AH trigger在P4-AD／AF／AG之後才建立，因此當輪仍是0候選、無future
commitment。不得把「圖有顯示」改寫成認知整鏈通過。完整負結果：
`analysis/p4_am_real_runtime_temporal_graph_failure_2026-09-25.md`、
`analysis/p4_an_post_turn_temporal_graph_failure_2026-09-25.md`。

P4-AO改用舊M37已可達的全新三輪case，不改產品程式。第一輪真實Safari成功顯示`過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`，
但第二輪在P4-AG把真實`p1-2`事件放進每輪重建的sequence floor=0空白shadow時，被P1正確拒絕為跳號，正式 **FAIL** 並停止；不得重跑。
完整負結果：`analysis/p4_ao_reachable_temporal_graph_failure_2026-09-25.md`。

P4-AP只修classifier-only shadow的prediction identity continuity，不降低P1 guard、不複製product ledger。事前freeze後離線／相鄰回歸=`75 passed`；
唯一一次全新隔離Safari三輪正式 **PASS**：prediction sequence=`1→2→3`、shadow floor=`0→1→2`、identity-bound supported=`2/2`；三輪
past=`0→0→1`、present六候選=`3/3`、future locked=`3/3`、identity／temporal node均在utterance前=`3/3`、日文／durable episode／graph
=`3/3`，最大單輪`3.7837s`、總和`10.4651s`，新增model／factual memory／raw graph leakage=`0/0/0`。這只證明一條真實產品路徑能以
精確事件identity完成commit→next-turn verification→later-past promotion；不證明心理預測正確、人評、自然分布泛化、人類方程式或強LLM優勢。
另保留gate外觀察：T2/T3表面回覆相同，不能用mechanism PASS宣稱felt understanding。完整證據：
`analysis/p4_ap_shadow_identity_continuity_acceptance_2026-09-25.md`。

P4-AQ完成上述單一ordering修正：development=`1/1`、全新中／英／日base-M37-miss正例=`3/3`均由固定P4-AH命中並在同輪形成
六候選／typed authority／pending binding／locked future；六個literal／resolved／ordinary-motion controls=`6/6` abstain，候選排序、detector、
classifier、visible reply、model call、factual memory、source state與既有temporal/identity規則變更=`0`。P4-AD→AQ相鄰回歸=`104 passed`。

事前另凍結全新三輪private runtime／Safari case後執行唯一一次，正式 **FAIL** 並於第一輪停止。ordering本身在真實產品成功：0→6候選、
`calibrate_need`、typed `cognitive_overactivity`、pending binding、future locked；Safari可見P4-AQ節點與
`過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`，日文／durable episode／graph=`1/1`、latency=`17.2761s`、新增model／
factual memory／raw leakage=`0/0/0`。但released M18 decision仍為`not_applied`且無product prediction ID，P4-AG只可建立
`additive_shadow_identity` fallback；P4-AP正確拒絕把fallback冒充`p1-N`事件，因此identity node、sequence與floor均不存在。凍結三輪
identity gate已不可能通過，T2/T3未送出、同題不得重跑。可見日文`考えが湧き続けるのは無理だよ`也只過語言guard，語氣生硬，不能宣稱
felt understanding。完整負結果：`analysis/p4_aq_real_live_extended_trigger_ordering_failure_2026-09-25.md`。

P4-AR下一個唯一能力變因是**late-trigger product prediction identity bridge**。先用P4-AQ已曝光T1作before/development，不修改或重跑正式case；
再凍結新的中／英／日late-only離線正例與inactive／literal controls。修正必須讓「P4-AH後才成立的同一個corrected shadow decision」取得由既有
P1規則簽發、且與product model sequence floor一致的真正`p1-N-*`事件，再交給既有P4-AG/P4-AP；不得把fallback字串解析成sequence、手寫
`p1-*`、跳過P1 guard、複製已驗證ledger、改AH detector、AF authority、AD候選分數／排序、AG feedback classifier、temporal promotion、
visible reply、prompt、模型call或factual memory。離線須證明P4-AQ before為fallback／無identity，after為exact product P1 identity且control no-op；
通過後另凍結完全新的三輪private runtime／Safari case，P4-AQ輸入永不再用。即使P4-AR通過，也只證明一條late-trigger產品事件能跨輪保持
identity，不等於預測準確、被理解感、人類方程式或強LLM優勢。

P4-Z deterministic contract 已完成：development=`3/3`、全新 synthetic holdout=`9/9`、faithful no-op=`6/6`、
unsupported abstain=`3/3`，P4-M..Z=`247 passed`。它只支援 quote／hearsay／hypothetical 三種受限文法，不能寫成
open-domain semantics、felt understanding 或強 LLM 優勢。

P4-AA 依 freeze 在private root／port `7872`完成唯一一次四輪真實產品與 Safari 執行：4/4自然日文、4/4 durable
episode、supported exact=`3/3`、unsupported no-op=`1/1`、P4-T/V/W/Z logic→graph payload=`16/16`，最大單輪
`17.5013s`；P4-Z新增model call=`0`，既有semantic authorization實際本機model call=`4`。但是正式凍結 gate 必須保留
**FAIL**：合約把實際P4-V node `utterance_frame_coverage_extension_p4`誤寫為
`utterance_frame_shadow_extension_p4`，所以逐字 frozen surface chain=`0/4`。不得事後改 gate 或重跑同題；工程觀察不能
取代正式 PASS。完整負結果：`analysis/p4_aa_real_product_source_proposition_acceptance_2026-09-23.md`。

P4-AB已以additive entry完成：四種事前凍結trace摘要exact=`4/4`，payload mutation／raw token／reply／logic／detail／model／
memory change=`0`；P4-M→AB與M24 graph=`266 passed`。圖上訊號從`18 fields`變為「來源框架｜說話者歸屬｜已知命題欄位｜
動作｜違規數 before→after」，且能顯示repair failed-closed。核心renderer hash保持不變。第一次直接改核心時完整P4掃描的舊
immutable gate失敗已保存並改為additive entry；另發現branch既存P4-D product-entry hash mismatch，本次不修改也不宣稱repo全綠。
完整證據：`analysis/p4_ab_source_proposition_graph_summary_acceptance_2026-09-23.md`。

P4-AC已依freeze完成唯一一次private root／port `7873`真實產品與Safari兩輪：2/2自然日文、2/2 durable episode、2/2 graph與
P4-Z node；可讀摘要與同輪logic exact=`2/2`、canonical surface chain=`2/2`、generic `N fields`摘要=`0/2`。supported引用
exact=`1/1`，unsupported control誠實顯示「來源／歸屬未知、欄位無、保留原文」=`1/1`。最大單輪`16.5364s`、總和
`27.7068s`；P4-AB新增model/memory/tool call=`0/0/0`，既有semantic authorization實際本機model call=`2`、elapsed
`22.8006s`、token unavailable。P4-M→AC與M24 graph回歸=`273 passed`。完整證據：
`analysis/p4_ac_real_readable_graph_acceptance_2026-09-23.md`。Safari與server保留，0 tab關閉。

P4-AD已完成additive shadow ledger：它把observable evidence、六種response action candidates、選出的operational action、下一輪
support/contradict/unknown驗證與private reason unknown分開；action score明定不是心理真值機率，選擇也不是private truth commitment。
第一次事前凍結9題中／英／日validation只有`5/9`啟動，四個失敗雖都已有舊M37 `cognitive_overactivity` typed trigger，較舊語用層卻
未啟動。負結果完整保存。唯一一次informed correction不加關鍵詞、不改題／gate／舊M18/M54，只在additive shadow內接通既有typed
trigger；同組修復回歸=`9/9`、6個literal controls false positive=`0`、12/12 candidate contract，0 reply/model/memory change；
P4-M→AD與M24=`286 passed`。因為這9題答案已被用來決定修正，修後`9/9`只算exposed development regression，不能再稱獨立
holdout泛化。完整證據：`analysis/p4_ad_desired_response_ambiguity_acceptance_2026-09-23.md`。

P4-AE已在P4-AD修正固定後另建並commit六個全新中／英／日paraphrase與六個near-miss controls，再執行唯一一次。真ambiguity的
status／selected clarification／required candidates／private unknown均=`6/6`，但near-miss只有`5/6`，正式gate **FAIL**，0 retry／fallback。
反例`風扇一直轉，但我已經把報告寫完了。`被錯誤建立六個候選。靜態根因是舊`_explicit_atom_assignments`只要看到`報告`就建立
`task_pressure`，而`build_current_state`把任何explicit atom當成desired-response activation；它也沒有理解`已經…寫完`的completion。
這代表topic cue被誤當need signal，不是P4-AD cognitive-overactivity bridge的主體判定。完整負結果：
`analysis/p4_ae_fresh_ambiguity_generalization_failure_2026-09-23.md`。P4-AE關閉，不改同組追分。

P4-AF已把P4-AE反例降為development，並以additive guard只修**是否應建立desired-response ledger**的因果邊界；M18/P4-AD、
候選分數／排序、可見回覆、prompt、模型與記憶均不改。current-turn authority限於typed cognitive-overactivity、明示response-form、
bounded emotional/support signal或當輪matched verified trigger relation；task topic／task_pressure／domain不能單獨授權。結果為4個development
status/authority/action=`4/4`；6個fresh positive=`6/6`，6個fresh negative=`6/6`；8個eligible case候選policy/order/score保持
`8/8`，topic-only authorization=`0`，0 reply/model/memory change。P4-M→AF與M24=`304 passed`。完整證據：
`analysis/p4_af_desired_response_eligibility_acceptance_2026-09-23.md`。

P4-AG已凍結9條兩輪序列後執行；正式結果 **FAIL**。在7個有第一輪authorized ledger的序列中，prediction/ledger identity
binding=`7/7`，support selected=`3/3`，contradiction舊候選撤銷且明示replacement取得可撤銷權威=`2/2`，unknown誤算成功=`0`，
0 visible/model/factual-memory change。但兩個fresh first turn（日文`頭の中が回り続けて…`與英文`thoughts will not slow down…`）
在舊M37均為`no_bounded_observable_trigger`，所以整體first-turn eligible=`7/9`、正式gate不可寫PASS。完整負結果：
`analysis/p4_ag_multiturn_outcome_binding_failure_2026-09-24.md`。這兩題已曝光，只能作development regression。

P4-AH下一個單一能力變因是**multilingual observable-trigger coverage**，不得改P4-AG binding／feedback classifier／P4-AF authority或
可見回覆。先把兩個P4-AG upstream failure降為development，再凍結未看過的中／英／日compositional cognitive-overactivity正例與
literal／completed-task／ordinary-motion近鄰反例；修正必須是typed head+predicate composition或等價結構，不可只加兩句完整字串。
先證明trigger predicate與private-state boundary，0 candidate rerank／model／memory／visible change；通過後另開全新多輪集，才能驗證
P4-AH→AF→AG完整鏈，不能把P4-AG原fresh題修後重跑包裝成獨立泛化。

P4-AH已依freeze一次通過：兩個P4-AG曝光development=`2/2`、全新中／英／日compositional positive=`9/9`、ordinary object motion／
metalinguistic／resolved-state／physical-head control abstention=`12/12`；完整case字串寫入source=`0`，base M37 mutation=`0`，
private-truth claim=`0`，0 candidate／visible／model／memory change。它只證明有限developer-authored多語組合感知覆蓋，不回溯改寫
P4-AG FAIL；P4-M→AH與M24回歸=`317 passed`。完整證據：
`analysis/p4_ah_multilingual_trigger_coverage_acceptance_2026-09-24.md`。

P4-AI下一個單一驗收目標是**固定後的整鏈可達性**，不再改任何規則：事前凍結完全未出現在P4-AG／AH的全新中／英／日兩輪序列，
至少support、explicit contradiction+replacement、unrelated unknown各3條。每條必須依序有P4-AH typed trigger→P4-AF authority→P4-AD
六候選→P4-AG exact prediction/ledger binding→candidate outcome與reversible next-use；unknown不得算成功，contradiction不得保留舊候選
priority。只允許compose既有固定模組，不改detector／classifier／threshold／prompt／reply／memory。PASS仍只算synthetic chain contract，
之後才決定是否授權real product/Safari與visible reply planner接線。

P4-AI已依freeze做唯一一次、0 correction／retry，正式結果 **FAIL**：typed P4-AH path=`8/9`，但P4-AF authority／六候選／exact identity
binding／exact outcome均=`9/9`；support=`3/3`、contradiction+replacement=`3/3`、unknown=`3/3`、unknown誤算成功=`0`。失敗案日文
`止められなくて`沒有命中P4-AH固定的`止められない`終止形，雖被舊bounded-emotional路徑授權而得到正確outcome，仍不能冒充指定
因果路徑PASS。完整負結果：`analysis/p4_ai_fresh_ambiguity_learning_chain_failure_2026-09-24.md`。

P4-AJ下一個單一變因是**日文形態覆蓋**：把P4-AI漏判降為development，事前凍結新的否定／接續／口語活用正例與已平息、引用字詞、
身體動作近鄰反例；只能擴充typed predicate morphology，不得改P4-AI chain、P4-AF authority、feedback、候選或可見回覆。通過後仍需
再用完全新的P4-AK兩輪集確認整鏈；不可重跑P4-AI後宣稱獨立PASS。

P4-AJ已依freeze一次通過：P4-AI曝光miss=`1/1`、全新日文活用正例=`6/6`、已平息／引用／身體／物體controls abstain=`8/8`；
predecessor mutation／完整句patch／private truth claim=`0/0/0`，0 visible/model/memory change。它不回溯改寫P4-AI FAIL。完整證據：
`analysis/p4_aj_japanese_morphology_acceptance_2026-09-24.md`。

P4-AK下一步必須在P4-AJ固定後另凍結完全新的中／英／日兩輪序列，compose AH→AJ→AF→AD→AG，至少support／contradiction／unknown
各3條；不得再改任何detector、classifier或門檻。只有指定typed path、六候選、identity binding與outcome全通過，才可稱synthetic
end-to-end chain PASS；仍不等於Safari可見品質、自然分布、人評或強LLM優勢。

## 已完成的 P4 前置歷史

P4-S 已依事前 freeze 完成唯一一次真實 Safari 12 輪、兩 process lifecycle，failed gates=`0`。12/12 日文、12/12 durable
episode、12/12 graph；七個非寫入干擾誤寫=`0`，兩次答案不在 query 的 recall exact=`2/2`。真 restart 為 PID
`30321→30585`、session `20260922_183428_41a5a0e9→20260922_184133_5916e29d`，最終 profile 恰有 active drink/game、
historical drink、negative drink 各一筆。最慢一輪=`16.3151s`、總等待=`121.1807s`。product planner追加model call=`0`，但
一般語意授權另有9次本機模型call、provider elapsed=`86.457s`且token accounting unavailable；不得把它寫成零模型系統。
完整證據：`analysis/p4_s_real_product_multiturn_acceptance_2026-09-22.md`。

P4-S同時暴露4個凍結gate外的可見失敗：T4丟掉引用框架、T7把使用者第一人稱行為改成角色行為、T9把第三人稱傳聞陳述改成向對方
提問、T10完全誤解「將內嵌句視為假設」的指令；現有M39 verifier四次都接受。P4-T已把speaker ownership、embedding mode、
evidential stance、speech act分開，shadow gate在4個曝光development failure=`4/4`、12個事前凍結中／英／日failure=`12/12`、
8個faithful control false positive=`0`；24/24 visible candidate逐字不變，0 model/fact/profile/episode write，trace node位於utterance前。
第一次integration修改released product entry，正確觸發5個immutable-hash failure；最後修正改用`uruha_web_ui_product_p4_t.py` additive
entry，舊hash恢復，P4-M..T=`181/181 passed`。完整證據：
`analysis/p4_t_utterance_frame_shadow_acceptance_2026-09-22.md`。

P4-U先凍結「只有P4-T已報出frame violation才修表面」的單一變因；development前置條件=`4/4`，但12個新holdout只有`5/12`
得到凍結標註的P4-T violations，第一個repair prototype因此只有exact reply=`6/12`。差異是三個新user→agent動詞、一個英文
`The memo says`報告標記與三個hypothetical／frame-instruction缺口。若在P4-U再寫第二套分類器，會同時改detector與repair並破壞
凍結契約，所以在product integration前判FAIL：0 model／memory／product／Safari。12案已曝光，只能降為development；不得修完再稱
holdout。完整負結果：`analysis/p4_u_preimplementation_compatibility_failure_2026-09-22.md`。

P4-V以additive entry擴充P4-T，不改可見回覆、模型／prompt／memory或released hashes。結果為7個曝光development反例的
base/evidence/effective exact=`7/7`、9個新中／英／日holdout=`9/9`、9個faithful control false positive=`0`；25/25 candidate逐字
不變，0 raw source/reply trace、0 model/fact/profile/episode write。英文`Suppose I said ...`的舊quote false positive仍留在base trace，
但新effective frame正確撤銷，能看出判定被校正而非掩蓋。P4-M..V回歸=`200 passed`；第一次回歸命令因測試環境把不相容的
system transformers置於product peft前而collection error，改用system pytest＋product site-packages優先後完整通過，未安裝或修改
環境。完整證據：`analysis/p4_v_utterance_frame_coverage_extension_acceptance_2026-09-22.md`。

P4-W只在P4-V effective trace已有violation時修正可見日文，沒有violation嚴格no-op；不重做before分類、不改detector、模型／prompt／
memory或released hashes。4個曝光development與12個新中／英／日holdout的before／exact reply／after-zero全部通過，8個faithful control
逐字不變；24/24 Japanese、0 raw trace、0 model/fact/profile/episode write。graph順序固定為P4-T→P4-V→P4-W→utterance，P4-M..W
完整回歸=`212 passed`。這已證明有限developer-authored frame family的deterministic visible repair，但尚未證明真模型或Safari會走到它。
完整證據：`analysis/p4_w_frame_preserving_visible_repair_acceptance_2026-09-22.md`。

P4-X已依事前freeze在新private runtime／port `7870`完成唯一一次4輪Safari執行，原案例不得重跑。4/4日文、4/4 durable
episode、4/4 generic graph可見；三輪自然觸發P4-W，logic內P4-T／P4-V／P4-W均為4/4，branch consistency與visible digest均4/4，
但Safari graph的三種P4 node皆為`0/4`，凍結gate為FAIL。另有三個gate外語意反例：T1修復引用框架卻包住無關命題、T3恢復傳聞
卻漏掉`なくした`事件、T4保留假設卻把使用者的I改成角色`うちは`且未被偵測。完整負結果：
`analysis/p4_x_real_product_frame_repair_failure_2026-09-22.md`。

P4-Y只處理trace delivery：把已存在於同輪`logic`的P4-T／P4-V／P4-W資料送入最後一次blackboard refresh之後，不改可見回覆、
detector／repair、模型、prompt或memory。合成complete／stale duplicate／missing trace三案通過，visible與logic逐位元不變、exact payload
`8/8`、missing synthesized=`0`；P4-M..Y回歸=`227 passed`。另以兩個全新日／英prompt在private runtime、port `7871`與新Safari tab
完成唯一一次實機驗收：2/2日文、2/2 durable episode、2/2 graph，P4-T/V/W各2/2，logic→graph exact payload=`6/6`，固定順序
2/2，failed gates=`0`；單輪=`16.1522/11.8162s`。P4-Y新增model call=`0`，但產品semantic authorization實際本機call=`2`，
token accounting unavailable。完整證據：`analysis/p4_y_real_product_graph_delivery_acceptance_2026-09-22.md`。

P4-Z不得重用P4-X或P4-Y輸入追分。先從P4-X已曝光反例抽象出source-bound proposition contract：輸入中的核心subject／predicate／object／
embedding stance／speaker ownership必須在visible reply有可追溯對應，不能只看quote／hearsay／hypothetical外框是否存在。先建立已曝光development
fixture與全新中／英／日holdout、faithful controls和no-op邊界；單一變因必須放在P4-W之後、可見回覆前，或證明現有M33/M39足以提供權威
source atoms後再修復。不得由關鍵詞自行造出來源沒有的命題，也不得把P4-X frame after-zero重新包裝成語意成功。先freeze／commit，才實作與驗收。

狀態：**P3-B54完成；P3-B55 REVIEW_REQUIRED。** capability-separated extractor在事前freeze後，以5秒合成raw驗證generation只取得
`1..3`秒artifact；3秒後2000 Hz sentinel／可見440 Hz能量比`6.781521697810383e-31`，低於凍結門檻
`0.0001`。raw在2個fresh reader process前刪除、private root mode `000`、兩次SHA-256一致、0 forbidden field／
private canary hit／private import。超長artifact、hash、禁止欄位、symlink、hardlink與permission均fail-closed；
B52全版本至B54共58項回歸通過。仍為0 reserved-source media、0 hidden future、0 prediction、0 model call。
完整release：`research/p3_b54_unidirectional_context_extraction_release_2026-09-18.json`。

B55 V1因ffmpeg version flag錯誤在0 network時fail；保存後V2只把`--version`改為`-version`，offline 24項通過後
消耗唯一transport invocation。V2在1.978149秒以yt-dlp exit 1結束：1 request、0 local/public artifact、0 future、
0 playback／semantic inspection／prediction／model。依事前規則不再重試或追加修正。完整反例與選項：
`analysis/p3_b55_reserved_source_context_transport_review_required_2026-09-18.md`。

### B56 執行結果與新設計審查

使用者以「請繼續」授權review建議1，覆蓋B55 `next_execution_authorized=false`，但不改其他邊界。B56另凍結
一次diagnostic transport，使用相同source、`*3000-3180`、工具、0 retry／fallback與B54 public gate；private worker
只把stderr映射成allowlisted error class，不保存／顯示原文、hash或token。允許類別為availability、provider challenge／
authentication、TLS／network、extractor／format、ffmpeg／postprocessing、command／option、unknown；分類必須先以fixture
凍結並涵蓋redaction canary。

若同一請求成功，只可輸出B54 exact 180秒artifact／manifest，private transport刪除後以fresh reader核對duration與hash；
若失敗，保存category、return code、stderr byte count與elapsed，0 public artifact後停止。不得再次修正／重跑，不得登入、
cookies、換來源、改cutoff、存stderr文字、人工播放／語意檢查、取得hidden future、執行prediction／model、寫正式M56或
production memory。

B56事前41項通過後消耗唯一請求：yt-dlp在2.944204秒exit 1，診斷類別`ffmpeg_or_postprocessing`，stderr
35 bytes只計數後丟棄；private runtime已刪除，0 public artifact、0 future／prediction／model。離線確認yt-dlp可找到
ffmpeg/ffprobe 8.0.1，direct ffmpeg synthetic pipeline exit 0，因此不是缺少ffmpeg，但現有redacted evidence不足以判定
postprocessing子原因。完整驗收：`analysis/p3_b56_allowlisted_diagnostic_transport_acceptance_2026-09-19.md`。

2026-09-19使用者再次以「請繼續」明確授權B57，並確認YouTube公開影片作為未來prediction資料來源方向。B57單一架構
變因：private yt-dlp resolver只把一個`bestaudio` signed URL留在記憶，direct ffmpeg再裁`3000..3180`並走B54 gate。
URL／resolver stdout／stderr／metadata不得落盤、hash或進receipt；只記byte count、URL count、allowlisted host category與
failure category。仍為0 retry／fallback、無cookies／登入、同source/cutoff；成功前不得人工播放／語意檢查，成功後也只
能把context artifact交給下一個prediction freeze，不得在本步讀`3181..3241`。

B57事前52項通過後執行：resolver exit 0，在1.927396秒取得1個private `googlevideo_cdn` URL；URL text/hash/excerpt
均未保存。direct ffmpeg在0.081831秒exit 8，分類`tls_or_network`；private runtime刪除，0 public artifact、0 future／
prediction／model。這排除source resolver失敗，但不能把原因斷言為特定HTTP status或header。完整驗收：
`analysis/p3_b57_split_resolver_direct_ffmpeg_acceptance_2026-09-19.md`。

2026-09-19～20使用者明確授權依既定計畫持續執行並使用Codex token，不必逐步停下確認；授權不包含花錢、付費API、
登入、cookies／帳號資料、hidden future洩漏、改弱baseline、降低gate或無限重試。此授權覆蓋B57 review的
`next_execution_authorized=false`，允許B58唯一一次新provider capability。

B58只改resolver同時在private memory提供allowlisted HTTP headers；明確拒絕Cookie／Authorization／Proxy-Authorization／
Set-Cookie，丟棄Range與未列入的非敏感header，URL與header name/value/hash都不落盤。69項affected suite通過後執行：
resolver exit 0、`1.560216s`、1個private URL與3個allowlisted header；direct ffmpeg仍在`0.079168s` exit 8、
`tls_or_network`。0 artifact／future／semantics／prediction／model／paid access。完整驗收：
`analysis/p3_b58_private_allowlisted_header_transport_acceptance_2026-09-20.md`。

B57 headerless與B58 allowlisted-header是兩個前瞻direct-audio修正批次，均失敗；依流程關閉此分支，不再加header、換小參數或
重跑。B59改走metadata-only caption availability probe；87項affected suite後執行成功：resolver exit 0、`1.598962s`，同一來源
沒有日文人工字幕，但有`automatic / ja / json3`，0 caption content／future／semantics／prediction／model。完整驗收：
`analysis/p3_b59_source_semantic_availability_probe_acceptance_2026-09-20.md`。

B60事前104項affected suite通過；resolver成功選出同一track，但唯一urllib caption GET在取得內容前以`tls_or_network`失敗：
0 raw caption／public artifact／prediction-side future access。完整驗收：
`analysis/p3_b60_private_caption_cutoff_extractor_acceptance_2026-09-20.md`。

B61事前114項affected suite通過後成功：yt-dlp native downloader exit 0、`1.888588s`；private full caption
`1,483,058 bytes`投影後刪除，發布65個cue，first/last=`3002.760/3176.079s`；fresh reader exit 0、hash一致、
不回傳text。prediction-side future／prediction／model仍為0。完整驗收：
`analysis/p3_b61_native_subtitle_cutoff_extractor_acceptance_2026-09-20.md`。

B62凍結同一qwen3.5:9b、context、兩call graph、每條512 completion上限、seed／temperature與六label；第一個
`BASELINE_LITERAL` representation call已回傳，但exact schema validation失敗，system未執行、prediction未凍結、future仍0。
raw result因call record只在condition成功後append而誤記0 calls；依控制流程operational actual=`1`，tokens/latency=`unavailable`，
不可填0。完整驗收：`analysis/p3_b62_real_context_prediction_acceptance_2026-09-20.md`。

B63事前22項測試後，以Ollama JSON schema執行；第一個baseline representation call完成並正確記錄：1986 prompt、256
completion（等於num_predict上限）、22.292540秒，回傳後仍parse失敗；system與prediction未執行，future仍0。這支持output
被completion ceiling截斷，但未保存raw，不能斷言確切截斷內容。完整驗收：
`analysis/p3_b63_schema_enforced_prediction_acceptance_2026-09-20.md`。

B64是prediction execution第二個、最後一個修正；保持每個condition總completion ceiling=512與所有研究條件不變，只把兩call
相同分配由256+256改為320 representation +192 prediction。provider-boundary accounting與JSON schemas不變。B64成功才可封存
兩條prediction並進separate future unlock；B64失敗則停止prediction修正，不再放寬schema、增加總token或重跑。任何結果都不得
以單一row宣稱全面優勢或formal M56。

B64事前26項suite通過並凍結提交後執行；第一個baseline representation call完成，`1986/320` prompt/completion tokens、
`25.001742s`，completion再次精確等於ceiling，回傳後仍parse失敗。model call=`1`，system/prediction/future/outcome/retry/
fallback=`0`。因此B62 two-call interface兩個修正批次已用完並關閉；不得把後續工作說成第三次修正。完整驗收：
`analysis/p3_b64_final_equal_budget_prediction_acceptance_2026-09-20.md`。

B65若繼續，必須另立新研究介面：用相同`qwen3.5:9b`、同一real pre-cutoff context、相同condition order、seed、temperature、
`num_ctx`及每condition completion ceiling `512`，把失敗的free-standing representation→prediction兩call改為一次bounded joint
representation-and-prediction。兩condition使用同一個有長度上限的JSON schema與相同一call graph；prompt只允許baseline採literal
state、system採可反駁pragmatic state。先contract/tests/freeze/commit，才可各做一次model call。完成兩條prediction前仍不得讀
3181秒後future；成功也只授權另一步outcome unlock，不是正確率或優勢結論。失敗原樣保留，不以同一介面追參。

B65事前37項affected suite與freeze commit後成功：同一`qwen3.5:9b`完成baseline/system各1 call；實際prompt tokens=
`2224/2217`、completion=`261/233`、latency=`23.262607/18.687710s`，均低於相同512 ceiling。baseline最高label為
`accept_support_and_continue=0.65`，system為`acknowledge_then_continue=0.60`；兩條prediction已封存，state文字只留hash。
future/outcome/retry/fallback仍為0。完整驗收：`analysis/p3_b65_bounded_joint_prediction_acceptance_2026-09-20.md`。

B66先以B65 immutable saved result與canonical result hash綁定prediction，再凍結outcome-only worker：使用同一source的日文automatic
caption，但只公開`3181.0..3241.0`內完整cue；private full caption取得後刪除，禁止回讀3000..3180 context、禁止改prediction、
禁止新model/judge call。評分必須在看future前定案：以可重現的observable behavior mapping取得實際label，再對兩組預測分布計算
selected-label hit、actual-label probability、Brier score與log loss；文字預測只做有證據的token/phrase overlap描述，不假裝是語意人評。
單一row無論正負都只算exploratory counterexample，不得宣稱全面優勢或formal M56。

B66在freeze commit後成功揭盲：first 3 cues=`3182.520..3190.559s`，固定marker `?`令actual proxy label=
`ask_clarification`。baseline/system對actual label機率=`0.05/0.10`、Brier=`1.360/1.235`、log loss=
`2.9957/2.3026`；依凍結rule system勝，但兩組top-1都錯。0 model/judge/retry/prediction mutation；private full caption在fresh
future reader前刪除。完整驗收：`analysis/p3_b66_future_outcome_scoring_acceptance_2026-09-20.md`。

B67不使用B66已曝光row調prompt、marker或門檻；事前固定同一來源四個尚未公開給prediction side的time windows：context/future分別為
`600..780/781..841`、`1200..1380/1381..1441`、`1800..1980/1981..2041`、`2400..2580/2581..2641`。
先一次private caption acquisition只發布四個context artifact，刪除raw與所有future後，原樣重用B65 joint schema、qwen3.5:9b、
condition order、seed、temperature、num_ctx及每condition 512 ceiling，封存8條prediction。任一row/call失敗即保留不完整batch，
不得先讀任何四個future；全部完成才可另立B68一次揭盲aggregate。這是same-source replication development evidence，不是獨立holdout。

B67事前31項affected suite與freeze commit後完成：四列context cue counts=`77/72/66/72`；同一B65介面8/8 calls完成，
prompt/completion tokens total=`18,908/1,697`、model latency=`152.907164s`。top-1有三列condition差異，八條prediction均已
封存；future/outcome/retry/fallback=`0/0/0/0`。完整驗收：
`analysis/p3_b67_same_source_multiwindow_prediction_acceptance_2026-09-20.md`。

B68必須綁定B67 immutable result hash，以一次private acquisition同時投影四個凍結future windows，raw刪除後才由fresh reader
讀取。每列原樣重用B66 frozen first-3-cues/12-second target、marker order、actual-label probability、Brier、log loss與winner rule；
禁止逐列解鎖、改marker/metric、改prediction或呼叫model/human/LLM judge。報告逐列正負與aggregate平均，但四列仍是同一影片的
development replication，不得外推成independent holdout或全面優勢。

B68在freeze commit後一次揭盲四列：row wins system/baseline/tie=`4/0/0`，mean actual-label probability=
`0.2875/0.2625`、mean Brier=`1.0134/1.17095`、top-1 hits兩組皆`1/4`。r0600與r1200的actual-label probability
相同，system只因Brier稍低取勝；baseline mean log loss被r1800的zero-probability放大。0 model/judge/prediction mutation/retry。
完整驗收：`analysis/p3_b68_multiwindow_future_aggregate_acceptance_2026-09-20.md`。

B69不得繼續切同一支影片追分。下一必要交付是事前選定另一支公開一ノ瀬うるは長影片，先只做metadata/caption availability與
duration檢查，不讀字幕內容；選擇規則、source id、context/future windows必須在內容取得前commit。後續原樣重用B65介面與B66 proxy，
但因新source是在看過B68後選定，仍稱source-level prospective replication，不假稱正式independent holdout。若找不到合法可用caption，
保存availability負結果，不用登入/cookies/替換到有利來源。

B69 source selection已完成但尚未查caption metadata：固定query與selection rule選中官方頻道rank 1、duration `12,933s`的
`Mlk5e3hBnb8`，排除原source；四個context/future windows也已固定為600秒間隔的同一組位置。下一步B69A只准一次
metadata-only日文caption availability probe，0 caption content/model/future；若不可用就保存負結果，不換來源。

B69A事前28項affected suite與freeze commit後完成：唯一一次metadata-only resolver在`1.678007s`成功，第二來源無日文人工字幕、
有`automatic / ja / json3`；raw metadata `508,363 bytes`只在記憶解析後丟棄。caption content／future／model／retry／fallback=
`0/0/0/0/0`。完整驗收：`analysis/p3_b69a_source2_caption_availability_acceptance_2026-09-20.md`。

B69B只可使用B69事前固定的第二來源與四個context windows；一次native yt-dlp acquisition後，只發布600..780、1200..1380、
1800..1980、2400..2580的context artifacts，刪除private full caption與四個future內容，再由fresh reader核對。原樣重用B65
bounded joint schema、同一qwen3.5:9b、condition order、seed、temperature、num_ctx與每condition 512 completion ceiling，依序完成
4列×2條prediction。全部8 calls完成前不得讀任何future；任一失敗即保存不完整batch並停止，不重試、不換來源、不調prompt／
門檻。這仍是source-level prospective replication，不是正式independent holdout。

B69B已terminal失敗且未揭盲：唯一caption acquisition與四個context artifacts成功；cue counts=`69/66/77/55`。本機模型前6 calls
完成前三列paired conditions，第7個`s2r2400 / BASELINE_LITERAL` provider call完成但prediction parser以`schema`拒絕，第8 call未執行。
總實際prompt/completion tokens=`15,429/1,650`、model latency=`133.887876s`；future/outcome/retry/fallback=`0/0/0/0`。依事前規則
禁止同來源重跑、補第8 call或B69C揭盲。完整反例：`analysis/p3_b69b_source2_multiwindow_prediction_acceptance_2026-09-20.md`。

B70先在已曝光development fixtures建立與來源無關的介面可靠度gate，不回頭追B69分數。最小單一機制候選是：保留JSON結構、
日文與所有內容gate，只對全部finite且非負、總和大於0的label weights做相同的deterministic normalization，再以凍結精度核對sum=1
且ranking不變；baseline/system完全同規則。同時把未來schema拒絕原因映射為不含raw response的allowlisted類別。先離線contract/tests/
failure fixtures與現有合法outputs；若gate通過，另立B71在任何caption內容前選定第三來源，修正版只能在新來源前瞻測試。B69第二來源
永久保留未完成反例。

B70離線gate已完成：相同adapter把六個finite nonnegative weights以50位decimal／12位輸出精度正規化，residual固定加到label順序中
第一個最大weight，並確認selected behavior不變。例`[2,3,1,1,1,2]→[0.2,0.3,0.1,0.1,0.1,0.2]`；baseline/system
同規則。缺label、負值、nonfinite、全零、非日文與缺state仍拒絕；38項affected suite通過。model/network/future/B69 retry均0。
這不能反推B69 raw失敗原因，也不是效果證據。完整驗收：
`analysis/p3_b70_prediction_interface_reliability_acceptance_2026-09-20.md`。

B71下一步必須在查caption metadata/content前，用固定搜尋與排名規則選第三支官方長影片，排除`4y5GiQpgJgo`與`Mlk5e3hBnb8`，
同時事前固定四個context/future windows。選定後才可另做availability；任何prediction都必須事先綁B70 adapter、同一B65模型／prompt／
token上限與兩condition。因第三來源仍是在先前結果後設計，只算prospective development replication，不假稱正式independent holdout。

B71已依freeze唯一搜尋選中official rank 2的`j6Hlk9cY9LQ`，duration=`12,883s`；四組`s3r0600/1200/1800/2400`
context/future windows已同時固定。搜尋耗時`0.936168s`，raw metadata `15,402 bytes`在記憶解析後丟棄；caption metadata/content、
model、future、retry、fallback=`0/0/0/0/0/0`。完整驗收：`analysis/p3_b71_source3_selection_acceptance_2026-09-20.md`。

B71A只准對已固定source做一次metadata-only日文caption availability probe，0 caption content/model/future；不可改query、來源或windows。
若無支援的Japanese track，保存負結果並停止此來源，不使用登入、cookies、替代來源或人工挑選。

B71A事前39項affected suite與freeze commit後完成：唯一metadata-only resolver在`1.827625s`成功；無日文人工字幕，有
`automatic / ja / json3`。raw metadata `508,363 bytes`只在記憶解析後丟棄；caption content/model/future/retry/fallback=
`0/0/0/0/0`。完整驗收：`analysis/p3_b71a_source3_caption_availability_acceptance_2026-09-20.md`。

B71B只可使用B71固定的第三來源與四個context windows；一次native caption acquisition後只發布context artifacts，刪除private full
caption與future，再由fresh reader核對。模型、prompt、options、condition order與每condition 512 completion ceiling原樣沿用B65；
唯一新增介面機制是事前B70 deterministic probability normalization，baseline/system完全同規則並記錄是否實際套用。8 calls全部完成前
不得讀future；任一call或parser失敗即terminal保存，不重試、不換來源、不放寬內容／日文gate。成功也只授權另一步整批future揭盲，
不能先宣稱修正有效或system有優勢。

B71B已完成8/8 predictions：四列context cue counts=`72/60/58/68`；prompt/completion tokens=`17,312/1,763`，model latency=
`149.1632s`。B70 adapter綁定兩condition，但8個input weight sums全為`1.0`，normalization applied=`0/8`；因此成功不能歸因於
B70，只能證明adapter未破壞合法輸出。兩condition top-1在2/4列不同；future/outcome/retry/fallback=`0/0/0/0`。完整驗收：
`analysis/p3_b71b_source3_b70_prediction_acceptance_2026-09-20.md`。

B71C必須綁定B71B immutable result hash，一次private caption acquisition同時投影四個固定future windows；raw刪除後才由fresh reader
讀取。逐列原樣重用B66/B68的first-three-cues-within-12s、marker order、actual-label probability、Brier、log loss與winner rule；
禁止逐列解鎖、改prediction/marker/metric或呼叫model/human/LLM judge。正負結果都保存；仍是development proxy，不是人類真值或正式holdout。

B71C已一次揭盲第三來源四列：row wins baseline/system/tie=`2/2/0`；平均actual-label probability=
`0.375/0.2375`、平均Brier=`0.81845/0.95215`、top-1 hits=`2/4`與`1/4`，均是baseline較好。
更重要的是四列均無marker命中，全部落到default `acknowledge_then_continue`，actual label diversity=`1`。這沒有重現
B68第一來源的system 4/4 row wins，也暴露目前caption-marker proxy在第三來源缺乏區分力。完整驗收：
`analysis/p3_b71c_source3_future_aggregate_acceptance_2026-09-20.md`。

B72不得新增來源、字幕、future或模型呼叫，也不得用已曝光B68/B71C結果調marker後回報優勢。下一必要交付是綁定兩份immutable
result/release，計算跨來源描述統計、label diversity、marker hit、來源方向反轉及不同metrics是否同向；明確判定現有proxy是否足以支撐
system advantage claim。若量尺失效，保存`proxy_not_adequate`，停止累加同類影片，另立尚未看新prediction/outcome的評價目標重設計；
不得只報對system有利的row wins或Brier而隱藏actual-label probability/top-1反向結果。

B72已完成read-only audit並判定`proxy_not_adequate_for_system_advantage_claim`：跨兩來源8列的row wins雖為system 6、baseline 2，
actual-label probability卻為baseline/system=`0.31875/0.2625`，top-1=`3/8`與`2/8`；Brier/log loss反向偏system。
第三來源actual label diversity=`1`且marker hit=`0/4`，三個metrics發生source direction reversal。0新來源/future/model/judge；
完整驗收：`analysis/p3_b72_cross_source_proxy_validity_audit_acceptance_2026-09-20.md`。

B73下一步不是修改已曝光marker，而是先凍結新的prospective target設計與評價方法：target必須有可辨認的stimulus→response單位，
把直接可觀察行為與需要人類判讀的語用／被理解感分層；automatic proxy只能在與盲化真人標註達到事前可靠度後使用。B73先建立schema、
annotation packet、雙coder reliability gate、missing/ambiguous處理及同模型公平比較欄位，並用synthetic fixtures驗證工具；不得讀第四來源內容、
執行新prediction或用Codex/LLM標註冒充真人。已曝光B68/B71C只作失敗例，不可作新量尺的成功驗證資料。

B73已完成protocol/tooling：prediction view不含outcome，coder view不含condition/prediction；不可辨認boundary的episode fail-closed，
acoustics缺少只能標unavailable。target分成observable moves、goal、stance、literal/pragmatic relation、surface text與另行主觀人評；兩位
不同真人各18 episodes、四個primary alpha均需`>=0.667`且至少兩種observed categories。27項affected suite通過；新來源內容/
prediction/outcome/model/human labels=`0/0/0/0/0`。完整驗收：
`analysis/p3_b73_prospective_response_target_protocol_acceptance_2026-09-20.md`。

B74只建立可實際使用的本機雙coder收集平台：兩個不可互看的private ledgers、同一frozen packet manifest、無condition/prediction欄位的
HTML表單、逐欄validation、完成後才可由獨立analyzer讀兩份ledger。先用synthetic packets驗證啟動、提交、重啟保存、跨coder隔離、
incomplete拒絕與reliability report；不得用synthetic pass解鎖真實來源或宣稱human reliability。Safari若工具仍拒絕則保持UI pending，
不能改稱通過；也不得在B74先取第四來源內容。

B74已完成：20項affected tests通過；Safari實際新增1 tab顯示synthetic標註頁，提交一題後`0/18→1/18`。private root/ledger
permissions=`0700/0600`，兩ledger entries=`[1,0]`；完整18×2 synthetic calculation的四個primary alpha均`1.0`，但
`synthetic_authorizes_human=false`、`real_prediction_authorized=false`。新來源/model/正式human label=`0/0/0`。完整驗收：
`analysis/p3_b74_isolated_two_coder_collection_site_acceptance_2026-09-20.md`。

B75下一步只設計並凍結real 18-episode sampling frame：來源選擇與slot規則必須在內容review前固定，每個slot需可辨認外部stimulus、
Uruha response與時間boundary；無清楚stimulus的直播獨白標unusable且不得用鄰近字幕補成對話。frame需包含controlled same-surface
context pairs與literal/pragmatic context-flip controls，並維持公開來源provenance、acoustic unavailable規則與train/dev/holdout分離。
先做metadata/source availability，不得在sampling freeze前觀看或標註response內容；B75也不得直接執行model prediction。

B75已terminal不足：唯一一次`ytsearch24:一ノ瀬うるは コラボ 雑談` metadata search exit 0、`1.323599s`、raw stdout
`33,182 bytes`丟棄，但符合official channel＋duration＋keyword＋exclusion的來源為`0`。caption/media/model/outcome/retry/fallback=
`0/0/0/0/0/0`，0 selected source／slot。這是provider ranked search discovery失敗，不是官方頻道內容不存在，也不是B73否定。
完整驗收：`analysis/p3_b75_real_episode_sampling_frame_acceptance_2026-09-20.md`。

B76是此source-discovery的第一個前瞻修正：改為一次直接列舉相同official channel公開uploads的metadata inventory，再套用事前固定的
排除、duration、title keywords與provider order；不得使用B75 query、人工選片、caption/content或playback。若仍不足三支，保存負結果並
停止本來源發現分支，不做第二個關鍵字／小參數重試。若足夠，只能建立同一6-relative-region-per-source frame；content review與model仍另 gate。

B76亦terminal不足：official channel `/videos` inventory exit 0、`0.565957s`、raw stdout `8,540 bytes`丟棄，eligible sources=`0`；
caption/media/model/outcome/retry/fallback全為0。因raw未保存，不能事後斷言是哪個metadata field造成0。B75＋B76已耗盡本source-discovery
分支原始嘗試與唯一修正；不得擴limit、換tab／keyword或人工挑選。完整驗收：
`analysis/p3_b76_official_channel_inventory_acceptance_2026-09-20.md`。

P3-C1已完成離線contract/data/metrics freeze：18個surface families、36 variants；train/dev/holdout各6 families，中文／英文／日文
各6 families。每組literal/pragmatic context保持byte-identical surface，family不跨split；prediction packet不含target，聲學固定unavailable。
baseline取得完整context且可正常推理，system唯一介入是顯式可反駁pragmatic state；兩組同模型、同一call、每item同384 completion ceiling，
額外system state token計入同budget。primary為holdout mean multiclass Brier至少改善0.03，且literal overinterpretation不得更差、paired
context-flip top-1不得更差。11項focused與43項B65/B70/B73/C1 adjacent通過；model/network/Uruha source/future/human label/production/
formal write全為0。完整驗收：`analysis/p3_c1_controlled_context_flip_acceptance_2026-09-20.md`。這只是developer-authored prospective
proxy contract，不是model效果、人評、獨立holdout或reference-person prediction。

P3-C2已完整執行但未通過事前效果量：8個train smoke後24個dev calls，32/32 validated，0 retry/fallback/holdout/Uruha future。
總成本=`22,952` prompt、`6,497` completion、`326.528142s` model latency。baseline/system mean Brier=`0.13305/0.120717`，
system改善`0.012333`，低於SESOI `0.03`；兩組dev top-1與paired flip皆100%，literal overinterpretation皆0，顯示developer題有ceiling。
English/Chinese system Brier較低，但Japanese=`0.1058/0.1583`與deixis=`0.0608/0.1658`反向。system相對baseline耗用
`1.2851×` prompt、`3.112×` completion與`2.3136×` latency；沒有成本優勢替代結論。依freeze判`controlled_lane_success=false`，
C1 holdout保持0 access，不以改門檻、改target或偷跑holdout追分。完整驗收：
`analysis/p3_c2_controlled_context_flip_acceptance_2026-09-20.md`。

P3-C3是唯一下一步：只做官方、外部作者的controlled pragmatic benchmark／stimulus資源discovery，先查DRInQ、PaCE及直接相關官方
artifact的paper supplement、repository、license、資料schema、same-surface context pair與train/dev/test邊界；不得下載／讀取hidden test
answers、執行模型、取得新Uruha來源／future或把C1 developer cases改名獨立holdout。事前列fit criteria：必須能在相同完整context與同模型
條件比較direct baseline和system，必須同時量context sensitivity與literal overinterpretation，必須有可合法重現的split/provenance；若官方
artifact不可得、license不允許或任務只測另一種能力，保存負結果而不自行重建答案。P3-C3輸出只能是候選資源與是否適合的決策，不能先宣稱
外部benchmark優勢；若有合格資源，另立contract/freeze後才可取允許的train/dev部分，test仍鎖定。

P3-C3已完成並保存`no_executable_external_benchmark_now`。DRInQ具同surface context variation且作者repo有單一validated CSV，
但未見dataset license與train/dev/test split，因此只列`conditionally_eligible_blocked`，0 CSV下載／row read。PaCE的方法最符合
literal/pragmatic context-flip，但本次從ACL官方頁與官方來源搜尋未發現可核對的dataset artifact，列
`method_fit_artifact_blocked`；這不斷言資料永不存在。PUB有MIT artifact，但不是same-surface literal/pragmatic pair且專案以前已用過，
不能當新independent holdout。三者合計executable candidate=`0`；benchmark dataset download／row／hidden answer、model、new Uruha
source/future、human label、production write均為0。完整驗收：
`analysis/p3_c3_external_pragmatic_benchmark_discovery_acceptance_2026-09-20.md`。

P4-A是唯一下一步。先只讀盤點既有本機聊天入口、真實runtime node graph、VRM 3D與Function Calling的啟動方式、資料源、port／process
owner、共用session與既有Safari驗收，列出「已經整合／存在但分離／真的缺少」的可重現證據。不得先新增dashboard、複製HTTP handler、
改研究資料／gate、碰原始dirty checkout、外部部署、登入或付費API。盤點完成後，若四項已有同一入口，先以啟動／重啟／長對話／工具成功
與失敗／3D顯示建立最小acceptance contract；若尚未整合，只准選一個阻擋統一入口的最小連線作為P4-B單一變因。P3的負／混合結論、
C1 holdout鎖定與M55/M56正式門檻不因P4產品工作改變。

P4-A已完成可重跑source inventory：Chat與truthful runtime node graph都已接在`uruha_web_ui_product.py`同一產品入口與同一turn output；
但Git tracked 3D asset=`0`，沒有VRM renderer或physical action executor。`vrm_action_policy_v34.py`只存在於research/eval路徑，
product/web/brain均未import，也沒有runtime tool schema或tool-result loop，因此Function Calling狀態為
`research_policy_only_not_product_runtime`，不能說是「既有功能」。safe worktree預期的`Style-Bert-VITS2/venv/bin/python`不存在，
system Python也沒有Gradio，故direct launch尚未ready。4項focused tests與inventory validation通過；runtime/Safari/model/production memory/
tool/physical action均0。完整驗收：`analysis/p4_a_unified_local_entry_inventory_acceptance_2026-09-20.md`。

P4-B是唯一下一步，單一變因只新增safe isolated product launcher，不改brain、prompt、研究資料、VRM或Function Calling。launcher必須
明確解析操作員指定或已知可用Python、檢查Gradio與entry，但不複製／修改原始dirty checkout；每次預設建立獨立temporary memory DB、
session DB與Web logs，只綁`127.0.0.1`，拒絕public host/share、登入與付費API。先以fixtures驗證interpreter缺失、dependency缺失、
public bind、路徑碰撞、child command/env與cleanup／preserve規則；offline contract通過才可真實啟動。真實啟動後核對health、隔離路徑、
聊天＋同輪graph與重啟；Safari是獨立可見驗收。P4-B不得把啟動成功擴張成VRM／Function Calling已整合。

P4-B已完成，保留一次真實失敗與一次sandbox修正。v1雖localhost HTTP 200與Safari可見，但Human Annotation path仍指向repo，故在0聊天、
0 repo write時判fail。v2以macOS sandbox拒絕child寫safe worktree與原始dirty checkout，synthetic deny／isolated allow通過；32項完整相鄰
suite後，以同manifest及明確reuse重開。Safari維持48個tabs且沿用既有tab，真實英文輸入要求只聽、不給建議，最終日文為
`うん。今は方法出さないから、そのまま話して。`；trace選`listening/listen_presence`、否定`solve_regulation`、surface matched，
同輪graph有69節點，user wait=`3.3884s`。1筆`1,353,575 bytes`JSONL、memory DB與adaptive model都只在isolated root；Git clean，
沉默後0可見催促。server仍在`127.0.0.1:7860`供使用者查看。完整驗收：
`analysis/p4_b_safe_isolated_product_launcher_acceptance_2026-09-20.md`。尚未驗post-chat process restart recall、voice、VRM或Function Calling。

P4-C是唯一下一步：新增一個allowlisted、read-only、零副作用的`get_runtime_status` Function Calling seam，作為未來VRM action transport的
前置，但不可接physical VRM。先凍結explicit status-request與ordinary conversation／negation／hypothetical／prompt-injection guards、唯一tool
schema、空argument、single-call、bounded result與日文surface contract；tool只能回傳不含路徑／對話／secret的brain-loaded、turn count、
memory isolation、tool capability狀態。offline fake-provider先驗證valid call、no-call、wrong tool、extra args、duplicate、malformed與executor exception
全部fail-closed，並把request→model decision→validated call→tool result→Japanese surface加入現有node graph。contract/tests/freeze/commit前
不得做real model call；real call通過與negative guards通過後才可整合product。shell、file write、external network、login、paid API與VRM execution
一律不授權。P4產品工作不改P3/M55/M56研究結論。

P4-C已完成產品真實驗收：status輪在全新session、brain仍lazy時以英文詢問，模型1 call選中唯一
`get_runtime_status({})`，tool 1 execution、side effect/memory-content read/brain initialization/retry=`0/0/0/0`；日文回覆正確顯示
brain待機、0 turn、isolated memory及read-only能力。同輪graph有request→model decision→validated call→tool result→surface五個
function nodes，共7 nodes，端到端=`6.2512s`。下一輪普通英文聊天仍回`うん。今は方法出さないから、そのまま話して。`，走原本
69-node path，P4-C新增model/tool/function-node=`0/0/0`，端到端=`2.697s`。後續4次background cycle未新增visible idle prompt。
core gate＋產品Safari真實本機model calls合計2，0 paid/external/retry。完整驗收：
`analysis/p4_c_product_function_calling_acceptance_2026-09-20.md`。這只證明一個read-only status tool，不是一般Function Calling、
state-changing action、VRM或研究優勢。

P4-D是唯一下一步。先做read-only local capability inventory，確認safe worktree與原始checkout是否已有可合法重用的VRM/GLB/GLTF asset、
renderer package、license/provenance、3D canvas入口與既有animation/action transport；原始dirty checkout只讀不改。若有合法asset與renderer，
凍結同一localhost產品入口的最小render contract；若沒有，保存缺口並只設計user-supplied `.vrm` 邊界與離線synthetic fixture，不下載或
重散布來路不明角色模型。P4-D只先做到可視3D renderer與truthful load/error node，不接未通過holdout的personality/action decision，
不執行physical state-changing action，不改P3資料／gate，也不使用登入、付費API或外部部署。

P4-D已完成並 release：同一Safari產品頁新增browser-only Local VRM Stage；初始只顯示`NEUTRAL STAGE · NOT URUHA`中性舞台。
以隔離runtime內自製4,020-byte VRM 1.0 mannequin實測，canvas真正畫出紫色T-pose且「選擇→驗證→解析→呈現」四節點全綠；
9-byte破損檔案則parse節點紅、render未完成、placeholder回復，沒有假稱顯示。valid→invalid→valid只做瀏覽器本機解析，conversation rows
維持`3→3`，server upload／asset persistent write／action／P4-D model/tool call全為0。viewer無remote URL/fetch/XHR且只允許blob/data；
這是application-level no-network evidence，不是假稱量測Safari其他48個既有分頁。status Function Calling與ordinary chat真實回歸仍通過，
端到端=`6.3426s/2.842s`；VRM始終可見。第一次raw http-literal proxy失敗亦保留，沒有改dependency或放寬runtime規則。
完整驗收：`analysis/p4_d_local_vrm_renderer_acceptance_2026-09-20.md`；release：
`research/p4_d_local_vrm_renderer_release_2026-09-20.json`。這不代表有一ノ瀬うるはasset、角色授權、動作智慧、tool-controlled avatar或研究優勢。

P4-E是唯一下一步，單一變因只驗證一個明示、speaker-qualified事實能否跨真正product process restart保存與回溯。必須在第一輪前固定
兩session腳本、唯一事實、可接受日文內容、ownership/relationship錯置反例、retrieval provenance、restart證據與失敗判準；只使用P4-B
既有isolated runtime，不讀production memory。第一session明確告知一個親屬所屬寵物名稱後停止process；以同一isolated root新PID／新session
重啟，第二session問題不得包含答案。成功需同時有正確名稱、正確speaker/owner關係、實際persisted retrieval trace、自然日文與graph可見，
且VRM local asset因browser-only不應被server記住。任何錯名、把親屬寵物說成使用者自己的、只靠prompt含答案、沒有retrieval證據或未真正
換process都算fail。結果一次保存，不因失敗改題、改prompt、手動注入memory或重跑；不把單一成功外推成長對話／open-world memory可靠。

P4-E已依事前freeze一次通過：全新隔離root第一個PID `62778`收到「Rina喜歡black coffee、使用者偏好herbal tea」，日文回覆
`記憶に残すよ`後真正退出；同一root／memory DB以新PID `62949`與新session重啟。答案不在第二題時，Safari回覆
`あんたが好みって言ってたのはハーブティー。`；唯一candidate的persisted episode ID=
`b992ec7e-cea9-4dca-81eb-e0760050b140`，來源時間早於新process，selected speaker=`user`而非Rina，圖上有
`speaker_qualified_fact_p3`，general planner model call=0。VRM stage在新page回到waiting，證明browser-local asset未被server持久化。
兩process／兩turn合計只有第一輪1次本機planner call，0 retry／tool／VRM action／paid API／production memory。完整驗收：
`analysis/p4_e_cross_restart_memory_recall_acceptance_2026-09-20.md`。這是developer-authored bounded product integration，不是open-domain、
長對話、人類記憶或研究優勢證據。

P4-F已依事前freeze一次通過：第一個process保存「偏好herbal tea」與另一筆「不再偏好herbal tea，現在偏好black tea」；舊process
真正退出後以同一isolated root／memory DB、新PID／新session重啟。答案不在recall問題時，Safari回覆
`今の好みは紅茶。前のハーブティーから更新してる。`。graph狀態=`resolved_explicit_preference_supersession`，兩個immutable episode
分別綁定historical／correction trace，current／revoked digest不同，DB rewrite=0。舊episode retrieval score=`1.4813`仍略高於更正
episode=`1.4801`，因此結果不是任選最高分。3 turns／2 processes／1 restart／2 write-turn planner calls，0 retry／fallback／paid API／
production memory；frozen gate failed=`0`。完整驗收：
`analysis/p4_f_cross_restart_preference_supersession_acceptance_2026-09-21.md`。這只證明一個bounded English tea correction case，
不等於一般信念修正、長對話、人類式記憶或研究優勢。

P4-G是唯一下一步，原因來自同一真實P4-F執行暴露的可見產品缺口：兩個寫入輪分別回`了解しました`與`了解しました。`，雖然是日文，
卻過度禮貌且制式，不符合既有casual Uruha surface要求。先把這兩個raw輸出、原planner route與P4-F memory semantics凍結為before；定位
現有full-planner輸出到visible surface之間最窄的authority。唯一允許變因是「使用者明示請系統記住偏好」與「使用者明示更正同一偏好」
兩類 acknowledgement 的自然、簡短、casual日文表達；不得改general persona prompt、模型、memory ranking、episode寫入、supersession／
recall adapter、P3研究資料或baseline。

成功需先用offline fixtures證明中／英／日三語的明示記憶與更正輸入都不再顯示`了解しました`系模板，仍只輸出自然日文、保留うるは公開
人格邊界，且普通聊天、拒絕、求助、身份、回溯與P4-F current／revoked均不退化。必須有negative guards，避免把普通「了解嗎？」、第三人稱
偏好、假設句或非偏好更正誤套成確認。P4-F同一真實案例不得重跑；離線contract、tests、freeze及commit完成後，另用未曝光的isolated新案例
做一次真實runtime／Safari驗收，並核對episode write、graph、語言與0 retry。這一步只改善可見surface，不得宣稱研究優勢或更深理解。

P4-G已完成但正式gate為`fail`，且負結果不可重跑／追分。全新isolated root的中文寫入輪正確辨識`zh/write`，但模型回
`了解。茉莉花茶が今の飲み物だ`，因不在frozen formal-ack allowlist，post-guard authority沒有啟動；等待`25.2079s`亦超過20秒。
日文更正輪的P4-G classifier正確辨識`ja/correction`，但既有rule route誤判`ask_like_me`，顯示與偏好更正無關的
`はいはい、全くじゃないとは言わない。そこ聞いて安心したいだけだろ。`。兩輪graph node與不同episode均存在、模型call=`1/0`、
retry/fallback=`0/0`，但frozen gate共10項surface失敗。完整負結果：
`analysis/p4_g_multilingual_preference_acknowledgement_acceptance_2026-09-21.md`。

P4-H是唯一下一步，單一變因從失敗診斷直接收斂為「明示偏好記憶act在general planner與舊intent碰撞之前取得deterministic plan／surface
authority」。先綁定P4-G immutable result，沿用已通過的中／英／日classifier，不擴allowlist、不改general persona prompt；對write與
correction各建立一個bounded rule plan，明確intent、dialogue act、core Japanese與0新增推測，讓寫入行為不需要任意模型措辭且不會被
`ask_like_me`先攔走。最終surface須由同一typed act contract接管，而不是只在reply剛好等於制式敬語時接管。

P4-H不可改episode/schema、memory ranking、P4-F parser／localization／recall、研究資料或baseline；「記住訂正內容」只代表原episodic
turn確實保存，不宣稱所有語言都已形成typed current preference。需把P4-G trace中未啟動authority卻顯示
`final_visible_surface_matches_contract=true`的誤導欄位修正。先以六個正例及普通聊天／第三人稱／假設／引文／安全路由做offline regression，
commit後另凍結全新案例才可真實執行；P4-G茉莉花茶／冰咖啡案例不得重跑。成功只代表bounded product act與surface，不代表人類理解或研究優勢。

P4-H已完成且 frozen product gate=`pass`。全新 English write／Chinese correction 在同一新隔離 process 各執行一次，實際顯示
`ん、その好みは覚えとく。`與`ん、訂正の内容はそのまま覚えとく。`；兩輪皆為 deterministic rule plan、正確
`explicit_preference_memory_write/correction` intent、graph `select` node、不同 episode、planner model call=`0`、retry/fallback=`0`，
使用者等待`2.1027s／11.2373s`，0 failed gates。P4-G舊案例未重跑。完整證據：
`analysis/p4_h_multilingual_preference_memory_act_acceptance_2026-09-21.md`。

同一結果也直接暴露 P4-I 的唯一問題：第一輪 English `sparkling water` 寫入後 typed profile `likes=[]`；第二輪 Chinese 更正後
profile 為`likes=[]`、`dislikes=[氣泡水]`，新 current preference `熱可可`沒有成為 typed like。兩輪 episode 都正確保留，因此不能再改
P4-H planner／surface，也不能說資料完全沒記住；缺口是 current preference 內容從多語 observable utterance 到 typed active state／superseded
history 的 projection 不完整。

P4-I先只讀定位既有 profile extraction、episode write 與 P4-F typed supersession 路徑，再綁定 P4-H immutable result，凍結 English／Chinese／
Japanese write與correction的 typed contract。current preference 與 superseded history必須分開，來源、時間、語言與更正鏈可查；不得只把舊項目
粗暴加入dislikes、不得抹掉原episode、不得把偏好內容當心理推測。先做offline parser／writeback／negative guard與受影響回歸，commit後才可另立
全新cross-restart real case；P4-H氣泡水／熱可可與P4-G舊案例都不得重跑。這一步仍不碰研究baseline、production memory、外部部署或人類優勢claim。

P4-I已依事前freeze一次通過：第一個process以English寫入scope=`drink`的`oolong tea` active typed positive，真正退出後，第二個process
以相同isolated root／memory DB及新PID／新session啟動，送出Chinese correction為`barley tea`。最終P4-I validity resolver得到一筆
active新positive、一筆historical舊positive及一筆active明示negative；舊record沒有刪除或改寫，兩個positive共用相同scope predicate。
Safari兩輪顯示自然日文與P4-H `select`／P4-I `memory` nodes；2 process／2 turn／0 retry／0 planner model call，等待
`2.3411s／16.2815s`，frozen gate failed=`0`。完整驗收：
`analysis/p4_i_cross_restart_current_preference_acceptance_2026-09-21.md`。

P4-J只處理仍明確未授權的read path：目前P4-I profile shadow仍是`answer_use_authorized=false`、`affects_working_memory=false`，所以typed state
持久化成功不等於產品會用它回答「我現在喜歡什麼？」。先凍結一條read-only adapter：僅對明示第一人稱、current-preference、exact supported
scope的問題讀取active P4-I current record；scope缺失／不支援／多active候選必須fail closed，historical與negative不能當current answer。
非selected問題完全保留P4-F episode recall。回覆仍須自然日文，graph要顯示typed source id與active-only決策；回答本身不得寫profile。
P4-I oolong／barley案例不得重跑。contract／tests／freeze／commit前不得送新real turn，也不得把這一步外推成一般記憶、人評或研究優勢。

P4-J 已依事前 freeze 做完唯一 cross-restart 案例並判定 `fail`，不得重跑。第一個 process 以 English 寫入
`drink=rooibos tea`，active typed memory id=`b1ae941d-5120-47c2-81fb-77194545ce78`；第二個 process 重用同一隔離 DB，
Chinese answer-absent query 成功把同一 id 讀進 `typed_current_preference_recall_authority_p4` plan，且 planned core 正確為
`今の飲み物の好みはルイボスティー。前のじゃなくて、今の方ね。`。但 Safari／JSONL 最終顯示 episode timestamp 回覆
`前に: 2026-09-21 13:15:5って言ってたろ。そこは忘れてない。`，graph 也缺 P4-J node。profile 仍為1筆且 hash 前後一致；
2 process／2 turn／0 retry／0 planner model call，frozen gate 7項失敗。完整負結果：
`analysis/p4_j_cross_restart_typed_recall_acceptance_2026-09-21.md`。

P4-K 只修這個已定位的 propagation seam：planner normalization 會保留 P4-J intent/core，卻丟掉自訂 contract，導致 visible guard 只查
final logic 時無法接管 surface，materializer 也沒有 payload 可畫。允許從當輪 `memory_data` 恢復已選中、已授權的 P4-J contract，先複製到
final logic 再套用 exact surface authority，最後產生 select-stage graph node。必須新增模擬 normalized logic 缺少自訂欄位的回歸；safety route
仍不得被覆寫，非selected query、P4-F、typed storage、active resolver、localization、expected surface與P4-J舊freeze一律不改。

先完成implementation與受影響回歸；在另立新acceptance freeze前真實產品輪次=`0`。之後只可用未執行的新值／新語言案例，P4-J rooibos、
P4-I oolong/barley、P4-H sparkling-water/hot-cocoa及P4-G案例都不得重跑。成功也只代表bounded跨重啟typed recall交付，不是一般記憶、
長對話、人評、強LLM優勢或人類方程式。

P4-K 離線實作已完成：visible guard 先沿用 final logic 內合法 contract，若 planner normalization 已移除自訂欄位，才從同一輪
`memory_data` 恢復並複製到 final logic；safety route 在恢復前就返回。事前紅燈=`2 failed, 3 passed`，修正後 P4-K=`5 passed`，
P4-F～P4-K affected suite=`179 passed`。freeze verifier 的 current-file hash 假失敗已改為讀 freeze commit 的 immutable Git blob；
freeze JSON、contract與產品案例皆未改。完整離線驗收：
`analysis/p4_k_typed_recall_surface_propagation_acceptance_2026-09-21.md`。

唯一下一步是 P4-K-REAL：在任何新real turn前另凍結全新兩程序案例；使用未在P4-J真實案例執行的exact source value與query language form，
第一程序明示寫入，真正退出後第二程序以答案不在題目的exact-scope current query回溯。需同時通過exact自然日文、P4-J select node綁同一
active id、profile count/id/content hash不變、不同PID/session、0 retry／planner model call／production memory／external deployment。
P4-J rooibos失敗仍為fail，不得重跑或改寫。

P4-K-REAL 已依事前 freeze 一次通過，failed gates=`0`。第一個 process 以 English 明示寫入 `drink=紅茶`，Safari 顯示
`ん、その好みは覚えとく。`，active typed id=`15d6830f-10cf-4b08-9935-3f69624d3a9d`；真正退出後，第二個
process 重用同一 mode-0700 isolated root／DB，以新 PID／session 回答 Japanese answer-absent query，Safari 精確顯示
`今の飲み物の好みは紅茶。前のじゃなくて、今の方ね。`，graph 有 `typed_current_preference_recall_p4` select node，
且使用同一 active id。profile count／id／content hash 前後不變，episode `1->2`；2 process／2 turn／0 retry／fallback／planner model call，
等待 `2.1570s／2.1684s`。完整證據：`analysis/p4_k_cross_restart_surface_delivery_acceptance_2026-09-21.md`。

這只證明 P4-K propagation 與跨重啟 delivery；`紅茶` 和舊 P4-F black-tea 語意重疊已事前揭露，不能宣稱 unseen semantic
generalization。下一步 P4-L 只處理目前已知的 cross-language exact-scope gap：Chinese／Japanese 明示 current-preference write 可能保留
surface scope `飲料` 或退成 `general`，但 P4-J query 已 canonicalize 為 `drink`。單一變因是把既有 supported write aliases 映射到
canonical scope，同時保留 source language／hash／provenance；不可同時改 value extraction、value localization、P4-J query／surface、
研究 baseline 或 frozen real cases。先做 before regression、contract與freeze；另立新 product acceptance freeze 前 real turn=`0`。

P4-L offline implementation 已完成。Before 證據顯示繁中 `飲料`、簡中 `饮料`、日文 `飲み物` 與 P4-J canonical
`drink` 形成不同 predicate；新 product-only adapter 只對 P4-I 已選中且 explicit-scope 的三個 frozen exact aliases 投影成
`drink`，不依 value 猜 `general`，不改 `snack`／未選中句。P4-I、P4-J 原檔未改；source language／input hash／value hash保留，
typed metadata另留alias id與source alias hash，graph新增 raw-free P4-L memory node且無 answer authority／model call。

Prospective test由implementation前collection error轉為P4-L=`9 passed`；P4-I～P4-L affected regression=`98 passed`，只有既有
Chroma SWIG warnings 2項。安裝後 temporary-Chroma smoke確認繁中 `桂花茶` 寫成 `scope=drink`、canonical predicate與
`drink:zh-Hant:v1` provenance，而 direct P4-I frozen tests不安裝adapter時仍保留舊結果。完整驗收：
`analysis/p4_l_preference_scope_canonicalization_acceptance_2026-09-21.md`。此層尚未有真實Safari證據；下一步P4-L-REAL必須先
凍結全新 Chinese explicit-scope write → real restart → English answer-absent query，freeze commit前 real turn=`0`。

P4-L-REAL 已依事前 freeze 一次通過，failed gates=`0`。第一個 process 以繁中明示 scope `飲料` 寫入 `麦茶`，P4-L
投影成 canonical `drink` 並保存 `drink:zh-Hant:v1` 與 source alias hash；Safari 顯示 `ん、その好みは覚えとく。`，graph
同時有 P4-I/P4-L memory nodes，active id=`c62640d7-ab6a-4edc-8f42-d44f8fd4fa01`。真正退出並關閉 listener 後，第二個
process 重用同一 mode-0700 root／DB，以新 PID/session 接受英文 answer-absent query，Safari 精確顯示
`今の飲み物の好みは麦茶。前のじゃなくて、今の方ね。`，graph 有 P4-J select node，使用同一 active id。

profile count／id／content hash、canonical scope與alias provenance在recall前後不變，episode `1->2`；2 process／2 turn／
0 retry／fallback／planner model call，等待 `2.2757s／2.2885s`。`麦茶` 與舊 P4-I barley-tea 語意重疊已事前揭露，
所以只證明 bounded跨語scope alignment與delivery，不證明novel value semantics或一般理解。完整驗收：
`analysis/p4_l_cross_language_scope_delivery_acceptance_2026-09-21.md`；下一步是上方 P4-M，不再重跑本案。

## 工作環境

- 安全 worktree：`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`。
- 分支：`codex/v2-15-pragmatic-research-showcase`，PR #435。查實際 HEAD，不碰原始 dirty checkout。
- Python：產品測試用 `.venv/product_checks/bin/python`；純標準庫 verifier 可用系統 python3。
  不全域安裝依賴。Gradio／Torch／brain 的 import 留在 isolated worker，不放純資料 module 的頂層。
- 長期目標檔：`LONG_TERM_GOAL.md`。2026-09-09 Goal 工具讀到 usageLimited；文件更新不等於 app 已恢復。
  不清除／假完成／改內部 DB 來換 Goal。使用者手動回合仍可執行已授權工作。
- 本機 Safari 已完成P4-B、P4-C與P4-D真實驗收；目前沿用1個Uruha頁面、沒有關閉使用者tab。P3-A不依賴瀏覽器。

## 已完成、不要重做

- P1 prediction identity 跨重啟保存；P2 compact planner、表達 core commit、當輪求助、婉拒、
  獨處要求與 speaker-qualified recall 的有限產品 baseline 已凍結：
  `research/p2_integrated_product_baseline_freeze_2026-09-09.json`。4 mechanism＋1 abstention、結構4/4。
- P3成本記錄收尾 commit：`34bef3d01d236873b4aa384b76aba2893ff9949d`。
  `research/p3_compute_accounting_freeze_2026-09-09.json`；121 passed／8 dependency warnings。
  `analysis/p3_complete_product_compute_accounting_acceptance_2026-09-09.md`。
- P3-A fail-closed comparison harness 與自審修正已凍結；P3-B1 isolated product worker 將產品真實 OpenAI／
  native M31 globals 綁到同一 gate，兩次 lazy import、same-case restart、cross-case refusal 均通過。驗收：
  `analysis/p3_b1_product_worker_acceptance_2026-09-13.md`。仍為 0 real model/network/paid calls。
- P3-B2 developer smoke source／annotations 已分離凍結：6 cases、24 user turns、12 sessions、三語各2、
  六 family 各1，建立 72 個 allowlisted views。驗收：
  `analysis/p3_b2_developer_smoke_acceptance_2026-09-13.md`；未執行任何生成。
- P3-B3 provider/tokenizer binding 在既有四種 fixture 通過；P3-B4 找到產品 call shape drift；P3-B5 adapter 已補齊並驗證
  seed/top_p/num_ctx。P3-B6 單一 product canary 工程通過，但品質未定。P3-B7 baseline 執行保留負結果：3 calls、2 complete、
  1 prompt-count failure，沒有三條件比較。詳見 `analysis/p3_b7_canary_baselines_acceptance_2026-09-14.md`。
- 真實本機run2：5 sessions／9輪，與P2可見回覆9/9相同；ledger 2生成＋130記憶操作，
  2,901生成tokens、30.834245秒；四個結構checks通過。兩次run均保存。
- native M31只mocked transport驗證，這九輪未實際觸發；Chroma embedding token／CPU/RSS/energy未量測。
  HTML是runtime graph產物，Safari未驗收。開發控制不是新holdout或全面能力證據。
- 不為新純資料harness重跑未變動的121項或M57.9八分鐘套件。

## 仍需保留的限制

- P2只在已曝光開發案例通過，不等於open-world對話、50輪可靠、人評、強LLM優勢或人腦方程式。
- 原生M31預設qwen3.5:9b，而一般planner是qwen2.5:7b；P3必須按config在isolated worker import前統一，
  transport核對所有路徑。不是改永久產品預設。
- P3共同歷史目前是system-anchored paired；報告必須揭露其條件性，不能當獨立對話偏好實驗。
- 正式研究依據上次封存紀錄仍缺真人／真實temporal資料；此輪未新讀私人ledger。M57.9 partial，
  M58沒有新授權。產品比較不能補造正式結果。
- developer smoke僅逐案推進，case06在B27仍為0 generation；未執行的cases／turns、case06評分、真人與formal confirmation仍不可宣稱。

## 回報方式

使用中文，先回答使用者新問題，再依卡片工作。短報實際成果、必要數據／例子、限制、Git與下一gate。
不要用「測試很多」代表使用者感受到的進步。兩次有證據的修正仍失敗就列反例進review，不亂加功能。
