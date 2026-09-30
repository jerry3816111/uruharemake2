# P4 行動交付：M46 負結果後的架構設計審查

狀態：**非獨立設計決定；尚未實作、凍結下一批資料或呼叫新模型。** 本文只決定下一個可反駁的架構變因，不改原產品、不撤銷任何正式 FAIL，也不把開發者自審稱為獨立評審。

## 目標與 before 證據

目標不是讓模型「看起來更會說」，而是在已授權的低風險實際任務中，從確切使用者來源選出**使用者可執行、確實推進原任務、自然日文且有停止點**的一步；不能偷偷改任務、替使用者聲稱已操作、編造私事或讓推測進入事實記憶。完整使用者輪次須符合既有 `≤20s` 預算，失敗則保留可理解的 fail-closed 回覆。

1. 現有 M51→M52→M46 流程先要求一次產生兩個完整候選，再以第二次模型呼叫審核選定方案。M51 的一次性自然生成首題耗 `17.63697s`、`360/360` completion tokens，JSON 於第二候選中途截斷，0/6 完整 batch；這不證明加 token 就能通過時間限制。見 `analysis/p4_m46_reviewer_necessity_generation_failure_2026-09-30.md`。
2. 最新一次同方案、同 9B 的 M46 固定元件比較：舊 A 保留有效 `2/3`、錯放無效 `2/7`、理由映射 `5/7`；新 B 保留 `0/3`、錯放 `0/7`、明確理由 `0/7`。B 10/10 把 `actor_capability` 標 `fail`，包括對使用者說「足してみて」的有效案。引文格式 7/10 不合格，但通過格式的有效日文案仍被誤判。B 只更快，未更準。結果和原始輸出見 `analysis/p4_m46_decision_interface_failure_2026-09-30.md` 與同名 JSON。
3. 真實 P4-AZ Safari 第二輪有 M46 review timeout，完整輪次 `38.1682s` 且未交付；P4-BA 四種模型大小配置完整接受都 `0/2`，最快 `16.78266s` 的 4B＋0.8B 亦失品質 gate。單純換小模型或再修 reviewer 文句沒有取得產品資格。見 `analysis/p4_az_real_previous_turn_ellipsis_to_action_delivery_failure_2026-09-26.md`、`analysis/p4_ba_stage_model_allocation_failure_2026-09-26.md`。
4. 已有 P4-BB deterministic compiler 對**正確 typed spec** 6/6 可編譯且快；但 P4-BE raw dialogue→完整 typed spec 只有 `1/6`。因此不能把「先有正確 spec」假裝是上游已解。見 `analysis/p4_bb_typed_action_compiler_acceptance_2026-09-27.md`、`analysis/p4_be_role_value_prompt_failure_2026-09-29.md`。

最小反例分別是：`valid_ja` 的使用者操作被誤認為助手代操作；`wrong_task_zh` 的摘要修改違反使用者「摘要稿不要改」，舊審核放行、新審核雖擋但 `task_alignment=pass`；`actor_surface_ja` 真正聲稱「うちが閉じておく」，新審核雖見 actor 錯卻未提供符合契約的理由。它們是已曝光開發反例，**不能作下一正式新分數**。

## 互斥選項與代價

| 架構選項 | 可能收益 | 已見障礙／新風險 | 本次處置 |
|---|---|---|---|
| 保留兩個模型階段，先加 typed 來源／任務／actor 表示供獨立 reviewer | 仍可做交叉審核、保守阻擋 | M51 首呼叫已 17.64 秒且截斷，M46 審核另需約 8–15 秒；加表示可能更慢。正確性仍未證明 | 暫不選；若單次路徑在 fresh 負例失守，可在新審查回來評估 |
| **單次 source-bound typed action transaction**：一個模型呼叫產生一個行動與可檢查的證據包，後接 deterministic guard | 去掉第二次自由模型審核與兩候選輸出量；把來源、任務、禁止事項、行動者、前提、狀態變化、停止點放在同一可追溯單位 | 模型自附證據**不能自證語義**；逐字來源檢查不能保證它沒有選錯任務或把禁令解反。可能出現全拒或錯放，必須被 fresh 反例否定 | **選為下一個整體架構變因；先隔離研究，不直接替換產品** |
| 僅交付明示且能由 P4-BB 模板編譯的窄域，其餘 abstain | 延遲與可機驗證性較可控 | 覆蓋率降低；raw→typed P4-BE 仍只有 1/6，若從此直接上線就是把錯誤移到上游 | 作保守產品 fallback 候選，不能冒充開放任務理解 |

「直接刪掉 M46 reviewer」不是第四個放行選項：先前隔離無審核反事實曾錯放 5/5 人工負例。也不提高舊 timeout、改舊題／gold／門檻、或為了速度弱化 baseline。

## 選定架構的操作定義與不可自證處

單次 transaction 的模型輸入只含當輪**已授權**的 user source／當前必要政策，不含評測 gold；一次輸出一個候選，至少要有 exact source id/span、原文 task-target evidence、明示禁止事項 evidence（若有）、actor=`user` 或有真實工具 receipt 才能是 `assistant`、使用者可取得的前提或 `unknown`、有界動作、預期 before/after、自然日文 instruction 與可見停止條件。`unknown`、來源不在已授權集合、缺 actor receipt、超出低風險範圍、格式／日文／停止條件不合時 fail closed。沒有工具 receipt 不得說助手已操作。

deterministic guard 只可以核對**可機驗證**的 exact 來源、欄位型別、引文位置／同一來源、actor／receipt、明確禁令的可識別衝突、日文與停止點契約；不得把模型自己填的 `task_aligned=true` 或漂亮的前後描述當作獨立證明。若來源→行動目標的語義對應無法機驗證，trace 要標為「未獨立證實」，評測時由預先獨立於輸出的 gold 核對。正常聊天仍只顯示自然日文，不傾倒證據包；graph 只展示實際 source→transaction→guard→交付／撤回。這是可測的行動架構，不是一般人類語用理解能力已完成。

這個比較的**唯一研究變因是整個決策拓撲／transaction contract**，包含候選數、表示與是否有第二個模型審核；不能把任何改善拆說成「少一個 reviewer」「某句 prompt」或「某個 schema 欄位」單獨造成。現有 M51/M52/M46/M45/M39 安全鏈維持原樣，B 先離線 shadow 執行，沒有正式 DB 寫入或外部 tool 副作用。

## 下一項前瞻 freeze 的必要規格與放行階梯

1. **先凍結新的 source-only 資料與事前 gold**，至少中／英／日各有明確可執行正例，以及 wrong-task／明示禁令、assistant 未授權代操作、虛構前提／來源、私人推測、non-action、日文表面、ambiguous/unsupported 控制；覆蓋率分母包含 abstain，不挑成功題。沿用前述例子只作回歸。gold 須分開標 task target、禁令、actor、內容有效性、日文自然度、可接受回覆或 abstain 理由；歧義在呼叫前裁定，無真人就明列 developer-authored proxy。
2. **同題配對 A 現行兩階段 vs B 單次 transaction**；凍結同一 9B digest、硬體、來源／政策、溫度、context、資料順序與總模型 completion-token 上限（B 不得超過 A 兩次呼叫上限之和），每臂每題唯一執行、交錯順序、0 retry，記載各 stage 與完整輪次實際 tokens／wall。因拓撲不同，stage seed 無法逐一等同；B 使用事前固定 generator seed，A 保留既有兩階段 seed，明列此限制作為整體架構比較，不偽稱逐 token 相同。先 prewarm，另記時間。
3. **絕對品質 gate 不能只看不錯放**：凍結的明確 valid 全保留，invalid 零放行，wrong-task／actor 等預定原因須由可稽核輸出或 guard 精確命中，JSON／source／tokens 完整，不能 always-reject；preflight、單元／mutation、fake transport 各先於真模型。對照 A 也同表計分；B 即使相對 A 好，但絕對 gate 未過仍 FAIL。`evidence` exact 只是一個子指標，不把語義 gold 偷渡成 runtime guard。
4. **成本與產品階梯**：先隔離 fresh generation＋guard 取得品質與完整一輪 `≤20s` 估計，計模型呼叫數、prompt/completion tokens、最大與中位 latency；只有此層全過，才設計全新 private runtime/Safari 多輪，驗日文、persona、安全、source、真實 node graph、持久性、完整 `≤20s` 與 0 未授權工具操作。再之後才談產品替換、真人評價與正式 temporal holdout；低層 PASS 不能代替高層。
5. **失敗分支**：若 B 有任何 wrong-task／actor 錯放或有效案全拒，保留 FAIL，不以快抵安全；若完整輪次超 20 秒，保留成本 FAIL，不延長 timeout；若證據包 parse／角色標註不穩，區分表示失敗和 guard 失敗。至多兩個有根據的修正批次，仍失敗則回到互斥選項審查或收窄範圍。任何新題、門檻、模型、架構實作都須先另存可追溯 freeze commit；本設計審查本身不是 freeze 或 scored-run 放行。

本審查可以支持的主張只有：「兩階段目前同時受內容辨別與完整成本所限，因此值得以前瞻資料檢驗一次性、來源綁定且有 deterministic guard 的整體決策拓撲。」它**不能**證明該拓撲更好、一般 LLM 無法做到、使用者感到被理解，或已求得人類反應方程式。
