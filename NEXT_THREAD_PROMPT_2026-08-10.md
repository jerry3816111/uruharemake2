# 新任務啟動提示

> **2026-09-01 最高優先續接：** 舊文所有 M32–M53「下一步」只保留為歷史。使用者已把
> 長期目標改為候選人類反應方程式的前瞻驗證：M54 Equation V1 契約 → M55 真實人物縱向
> pilot → M56 B0–B5/Ours 未見未來比較 → M57 Oracle 錯誤定位 → M58 單一變因與新 holdout
> → M59 因果消融／反事實 → M60 desired-response 前瞻驗證 → M61 第二人物 transfer → M62
> 第二模型重現。允許誠實重試到 M75，之後無論正負停止並總結。先讀
> `research/m54_human_response_equation_v1_plan_2026-09-01.md`，不得再等待逐 M 確認。
>
> **M54已於2026-09-01通過契約gate。** 先讀
> `analysis/m54_human_response_equation_v1_acceptance_2026-09-01.md`；下一個單一里程碑是M55，
> 不要重跑或結果後修改M54。M55只建立timestamped real-person longitudinal pilot、codebook與
> reliability／missingness證據，不能先做M56模型勝負，也不能用sealed future調Equation V1。
>
> **M55最新狀態：pre-content PASS，real-person pilot BLOCKED。** 先讀
> `analysis/m55_real_person_longitudinal_readiness_2026-09-01.md`。3個Uruha來源、30個凍結slots與
> future排除已有效；但V7兩份ledger仍0/18、無reliability lock，故V9 target event/coder仍為0，
> M56不得啟動。除非兩位不同真人完成V7並通過凍結可靠度，不能用Codex、模型或synthetic labels
> 替代。可持續做不消耗holdout且不假造真人證據的工程，但不得把它改稱M55真人結果。
>
> **M55 temporal-row工程gate已通過，但不是M55真人結果。** 先讀
> `analysis/m55_temporal_row_contract_acceptance_2026-09-01.md`。稽核發現V9 whole-event start/end
> 不能安全替代prediction cutoff；新契約另要求input start／cutoff／behavior start／behavior end，
> 並把九個Equation變數的unknown/missingness明列。2-row synthetic compiler證據為0 leakage，
> 但真人rows仍0/30且M56不授權。下一個安全工程單元是private two-coder boundary-extension
> collection instrument；V7通過前只能用synthetic fixtures測工具，不能看或編Uruha target內容。
>
> **M55 two-coder boundary tool工程gate也已通過，真人證據仍為0。** 先讀
> `analysis/m55_boundary_extension_tool_acceptance_2026-09-01.md`。工具把每位coder自己的V9 entry
> 與獨立boundary ledger以digest綁定；真實init/serve仍需V7 reliability pass，stale source、非finite
> 時間、synthetic/real混用全部fail closed。兩份完整ledger只輸出hash與時間差，不顯示文字、不自動
> 合併，每列必須明確真人裁決。Safari合成圖通過，但V7仍0/18＋0/18、V9與真人temporal rows仍0/30、
> M56禁止。下一個不可替代依賴是兩位不同真人完成V7；通過後才可開兩人的V9＋boundary實際站。

> **M55 explicit adjudication／record assembly工程gate也已通過，真人列仍為0。** 先讀
> `analysis/m55_boundary_adjudication_tool_acceptance_2026-09-01.md`。新private工具對每個完整pair
> 強制explicit accept-A／accept-B／manual resolution，即使完全一致也不能auto-pass；保存四個source
> entry hash，不平均時間、不挑標籤、不合併文字。每次page/save/export重驗四份ledger；stale立即
> HTTP 409。synthetic完整匯出可過22-field temporal validator，但固定0真人、M55 false、M56 false。
> Safari的outsider與private圖已通過，未送出表單。現在V7仍0/18＋0/18、V9與real rows仍0/30；
> 不可用Codex/LLM/synthetic補過。所有pre-target M55工具已齊，下一個真依賴就是兩位不同真人V7。

> **M56 blinded same-model fair-comparison preflight已凍結，但正式執行仍禁止。** 先讀
> `analysis/m56_fair_comparison_preflight_acceptance_2026-09-01.md`。七組B0–B5/Ours、固定B5 vs
> Ours primary contrast、prediction packet/outcome key隔離、SHA commitment順序、同模型／硬體／
> decoding／token規則與Brier＋NLL gate都已在看結果前凍結。focused 17/17，選定相容116/116，
> Safari圖像頁通過；但model calls與target outcome access都是0，formal result不存在。V7仍0/18＋
> 0/18、V9與real rows仍0/30，故不可啟動M56 generation。下一個合法動作仍是兩位不同真人完成V7，
> 通過後依V9→boundary→adjudication→temporal compile順序產生M55 real rows，再重驗preflight後執行。

> **M56 capability-separated execution capsule與separate scorer也已凍結，正式執行仍禁止。** 先讀
> `analysis/m56_blinded_execution_capsule_acceptance_2026-09-01.md`。七組不再共用含完整history的packet：
> 每次model request只得到該condition的authorized view；B1/B2沒有history，B4 summary與cost分離，
> B5/Ours source object/hash相同。完整七組submission需先SHA-256 commitment，獨立scorer才可驗證並
> 讀outcome key；事後改動、漏列、重排、作弊evidence、retry/fallback或resource drift均fail closed。
> focused 28/28、選定相容161/161、Safari圖通過，但formal model calls／target outcome access仍為0，
> 不是M56結果。V7仍0/18＋0/18；不可用synthetic fixture或同一人替代。真人gate通過並完成30列後，
> 還必須materialize真正pre-outcome Equation V1 fit/state/transition artifact，不能用fixture hash冒充Ours。

> **M56.1 pre-outcome Equation artifact overlay已凍結，正式執行仍禁止。** 先讀
> `analysis/m56_pre_outcome_equation_artifacts_acceptance_2026-09-02.md`。新overlay不改M54–M56凍結檔，
> 而是把B5/Ours同一source object真正轉成content-addressed fit、九變數state與跨cutoff transition；
> `S/R/N`無來源時保持null。只有Ours request可取得完整產物，submission、wrapper receipt與wrapper
> scorer會重驗內容hash；placeholder、late/non-monotonic history、B5 artifact exposure與事後竄改均
> fail closed。focused 14/14、M54–M56 direct 110/110、選定相容170/170，Safari沿用原tab且28 tabs
> 不變。這仍只是在synthetic outcome-free packet上的工程證據：V7 0/18＋0/18、V9/real rows 0/30、
> formal calls 0、formal result不存在。真人gate通過後還需另凍結real-data execution authorization，
> 重驗全部dependency hash並記錄actual CPU/prompt token cost；不能把這次bundle說成真人預測結果。

> **M56.2 formal real-data activation envelope已凍結，但目前live activation明確DENIED。** 先讀
> `analysis/m56_2_real_data_activation_envelope_acceptance_2026-09-02.md`。新入口沒有caller-supplied
> readiness：它只讀標準V7/V9/M55 live evidence，並綁定十個凍結依賴、本機`qwen3.5:9b` manifest、
> Ollama、CPU/RAM與run rules。未來真人gate通過後才可在gitignored四個private compartments建立
> 30-row packet、獨立outcome key、210 tasks與90個Equation artifacts，並以30分鐘single-use receipt
> 換取一次no-retry generation lease。synthetic rehearsal與偽造real-shaped packet都不能取得receipt；
> focused 13/13、M54–M56.2 direct 123/123、選定相容188/188，Safari圖像頁通過。現在仍是V7
> 0/18＋0/18、V9 0/30、real rows 0/30、formal calls 0、formal result absent；下一個不可替代依賴仍是
> 兩位不同真人完成V7，不能用Codex、LLM、synthetic labels或同一人重複作答替代。

> **M56.3 lease-gated formal generation runner已凍結，但目前仍不允許呼叫模型。** 先讀
> `analysis/m56_3_lease_gated_generation_runner_acceptance_2026-09-02.md`。M56.3只接受`run_id`，
> 先重驗M56.2 consumed lease，再依固定順序建立B4 summaries與30×7 prediction schedule；B0為0-call，
> B1–B5/Ours每sample一次call，0 retry/fallback。每次正式call必須留下actual token、latency、CPU、
> process/Ollama memory、provider duration、model identity及content hashes；完整210列通過後才可寫
> submission→SHA commitment→separate-scorer release，generation全程不得讀scoring outcome。
> focused 14/14、M54–M56.3 direct 137/137、選定相容202/202，Safari圖像頁通過；但現在live audit
> 仍是V7 0/18＋0/18、V9/real rows 0/30、lease/calls/commitment/release/result皆0或不存在。這只證明
> future authorized runner mechanics，不是actual resource/performance或人類方程式證據。下一個不可
> 替代依賴仍是兩位不同真人完成V7。

> 最新入口是上方的「M56.3 lease-gated formal generation runner」覆蓋段；前文各 M 的
> 下一步均為歷史，不要重跑或回寫既有封存結果。真人gate未通過時繼續做不消耗target的必要工程，
> 但不得把工程fixture改稱正式結果。

在以下工作目錄繼續：

`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`

先讀 `CHAT_CONTEXT_COMPACTION_2026-08-10.md`，不要要求我貼舊聊天室。開始前執行 `git status --short --branch`，避開原始工作樹的 unrelated dirty files。

長期目標是開發／研發優先：把記憶、語用推測、狀態、回覆策略、後續誤差與人格整合成能在真實多輪中持續學習與修正的產品。研究只用來驗證實作是否有效、安全、可追溯及有何限制；不再以論文包裝取代工程。一ノ瀬うるは是有公開證據邊界的主要 reference-person 參數，不宣稱等同真人。

M16–M29 bounded 產品里程碑、M30 negative diagnostic 與 M31 source-first semantic authorization 已完成。先讀 `analysis/m31_semantic_authorization_reserve_acceptance_2026-08-25.md`。M31 first sealed reserve 明確失敗：9 個 valid 中只有 4 faithful、0 false authority、5 false reject；3/3 incomplete 正確 abstain；zh/en/ja 是 0/66.7/66.7%；median 9.043s、p95 9.692s。M31 安全但過度保守，不能稱 reliable cross-lingual semantics。M31 code/result freeze 與 reserve hashes 不可回寫或重解釋。

下一個單一產品里程碑是 `M32 Deterministic Semantic Commit Repair and Ordinary-Negation Routing`。M31 reserve 現在只能當 exposed development evidence。先封存全新 source-disjoint reserve，再做兩個可歸因修正：

1. ordinary literal negation（例如 `museum is not open`）不得被 correction classifier 攔走；明確 `No, not that...` correction 行為不得退化；
2. M31 已有 faithful canonical normalization、但只因 polite register 或可修 surface anchor 失敗時，M32 可用 deterministic casual commit 修復；semantic fields missing/conflicting 時仍 fail closed，不得為提高 coverage 放行。

驗收必須分開 M31 exposed replay 與 M32 sealed reserve，要求 false authority／unsafe incomplete／unsupported addition 不退化，並記錄 zh/en/ja coverage、negation、latency、raw-free trace。完成後用隔離 Safari 顯示 candidate→normalization→commit/reject 的實際 node path與新 reserve 結果；不要外部部署、不要污染正式 DB。

以中文簡短說明正在做的 M 內容後直接繼續，不需等待使用者確認。

## Latest continuation override — after M32 sealed failure

M32 已完成並封存；先讀
`analysis/m32_semantic_commit_routing_reserve_acceptance_2026-08-25.md`。
M32 first sealed reserve 明確失敗：12 valid 中 7 faithful、4 false
authority、1 false reject；3/3 incomplete 正確 abstain；zh/en/ja 是
25%／75%／75%；fresh-session 66.7%；polarity 與 ordinary negation 100%；
median 7.6775s、p95 8.9144s。不得回寫或重新解釋 M32 freeze/result。

下一個單一產品里程碑是 `M33 Source-Anchored Semantic Atom Ledger`。
M32 reserve 現在只能當 exposed development evidence。先建立並封存新的
source-disjoint M33 reserve 與 protocol，再實作獨立於 model self-report 的
source atom extraction／verification：至少分開 time、object、quantity、
negation、change operator，逐項保留 provenance。canonical 與 source atoms
不一致時只能 bounded deterministic repair 或 revoke authority；不得為了
coverage 放行。direct Japanese source 應走可追溯 identity/normalization path，
不必無條件交給翻譯模型。

M33 必須保留 M32 的 fresh routing、standalone `uh/um` boundary、incomplete
abstention、final Japanese guard、persona/memory/protected routes、raw-free
persistence 與 Safari graph。完成 implementation freeze 後只執行一次新的
sealed reserve；無論 pass/fail 都保留並直接決定 M34，不需等待使用者確認。

## Latest continuation override — after M33 sealed pass

M33 已完成且封存；先讀
`analysis/m33_source_anchored_semantic_atom_acceptance_2026-08-25.md`。
M33 first sealed reserve 通過全部 frozen gates：12/12 faithful authority、
0 false authority、0 false reject、3/3 incomplete safe abstain；zh/en/ja、
fresh session、direct Japanese、change、negated/limited quantity、polarity 與
atom trace coverage 全為 100%；5 次 source conflict repair、0 unresolved
conflict authority；median 9.2464s、p95 13.2376s。不得回寫或重新解釋 M33
freeze/result；presentation-only result strip 已另有 manifest。

下一個單一產品里程碑是 `M34 Counterfactual Pragmatic Branch Ledger`。
M33 literal atoms 只能當可觀察輸入，不能直接當成使用者真正想要的回覆。
M34 必須把 literal state、candidate communicative goals、desired-response
modes、current/context/relationship evidence、observable next-turn prediction、
uncertainty 與 bounded alternative 分開。以同一 current utterance、只改 valid
prior context 的 counterfactual pair 做可歸因 intervention；下一輪明確 feedback
必須能 support／contradict／leave unknown 並更新 branch，不改寫原證據，也不把
unverified mental state 存成 factual long-term memory。

先封存新的 M34 intervention reserve 與 protocol，再實作 ledger、runtime
integration、graph 和 evaluator；development 可用既有 M18–M27 cases，但新的
sealed reserve 必須 source-disjoint。保留 natural Japanese visible output、
Uruha persona、protected routes、raw-free trace、M27 causal outcome discipline
與 M33 source-atom boundary。完成後自行做 tests、一次 sealed reserve、隔離
Safari 真實多輪與圖像驗收，無論 pass/fail 都直接決定 M35，不需等待使用者確認。

## 2026-08-25 latest override after M34

M34 已完成並凍結。8-case／4-pair zh-en-ja sealed reserve 僅執行一次且
PASS ALL：policy/mode、same-current pair divergence、literal invariance、evidence／
alternative／observable prediction trace、next-turn verification、contradiction
replacement、surface match 與 visible Japanese 全為 100%；unsafe mental-fact／raw
adaptive persistence 為 0；median 0.3503s、p95 0.3590s。不得依 reserve outcome
修改 M34 core；結果後變更只限 presentation strip/report 並有 manifest。

下一個單一產品里程碑是 `M35 Same-Model Longitudinal Pragmatic Advantage`。
研究問題不是「LLM 能不能猜語用」，而是控制同一 base model、相同當輪輸入、
相同 Uruha persona/surface 約束後，M34 verified longitudinal context +
prediction/verification/revision 是否比 current-turn-only direct baseline 更能選中後續
被實際回饋支持的 desired-response branch，且在被否定時修正得更好。先封存新的
source-disjoint pair reserve、generation contract、token/latency audit 與 proxy rubric，
再實作 evaluator；baseline 不得讀 hidden history/system trace。若尚無獨立盲人評，
只能報 controlled proxy advantage，不得宣稱 felt-understanding preference 或全面勝過 LLM。

## 2026-08-25 latest override after M35 frozen failure

M35 已完成並凍結，正式結果不可回寫或重跑。相同 `qwen3.5:9b`、相同當輪
輸入、persona/surface contract 與 exact scored prompt-token parity 下，baseline
當輪 policy accuracy 25%，M34 longitudinal system 75%，形成 +50pp 的受控當輪
觀察；但 mechanism、pair divergence、surface、feedback linkage 與 contradiction
revision 共七個 frozen gates 失敗，因此 M35 overall decision 是 FAIL。另在結果後
稽核發現 frozen feedback-policy targets 有兩個 contradiction 標註錯誤及數個
non-comparable label 不一致，故 formal feedback policy 60% 不得作為證據，也不得
用結果後修正分數取代原始失敗。

下一個單一產品里程碑是 `M36 Compositional Multilingual Pragmatic Cue &
Annotation Integrity Remediation`。先建立通用 annotation-integrity validator：
contradicted row 必須有可由 current feedback 獨立辨識的 explicit replacement
policy，且 expected target 必須相符；support/uncertain 的 feedback-policy 比較必須
明確標成 not-scored。通過 validator 後才可封存新的 source-disjoint reserve。

M36 再修正組合式多語線索，不加入 M35 exact sentence 模板：英文 practical-help
seed／correction、listen/no-advice target；日文允許 `頭が` 與 `止まらない` 中間有
bounded adverb；句首 `No`／`違う` 只有在 pending previous branch 且當輪含 valid
explicit replacement policy 時才算 contradiction。必須分開 mechanism/correction
與 surface-realization evidence，保留 natural Japanese、persona、protected routes、
raw-free persistence 與 Safari graph。凍結後只跑一次新 reserve，無論 pass/fail
都保留並直接決定 M37，不需等待使用者確認。

## 2026-08-26 latest override after M36 frozen failure

M36 已完成並凍結，正式結果不可回寫或重跑。新的 12-case／6-pair zh-en-ja
reserve 在 annotation-integrity gate 為 12/12 pass、0 errors；同一
`qwen3.5:9b` 與 exact scored prompt-token parity 下，current-turn-only baseline
當輪 policy 16.67%，longitudinal system 83.33%，差 +66.66pp。六個有效
contradiction 的 system feedback policy 100%，outcome linkage 91.67%；但 mechanism、
pair divergence、full revision、current/feedback surface 等七個 frozen gates 失敗，
overall decision 保留 FAIL。Safari 中 `不是` correction 可完成
`solve_regulation → listen_presence`，但這不能取代 sealed `不對` failure 或人評。

下一個單一產品里程碑是 `M37 Pragmatic Trigger-Relation Normalization`。先封存
source-disjoint relation-level reserve 與 protocol，再把明確 seed preference 拆成：
observable trigger predicate、requested response policy、scope、source、verification
status 與 confidence。seed 當輪 request act 不得混成 future trigger；current turn 必須
用 typed trigger normalization 比對 morphology／bounded paraphrase，而不是 M36 exact
sentence／phrase template。需要保留 counterfactual pair、同模型 baseline、token/cost、
Japanese output、persona、protected routes、raw-free persistence 與 graph lineage。

M37 只修 trigger relation；不要順便改 Chinese `不對` feedback linkage 或 surface-act
verifier，以維持單一核心變因。M36 exposed failures可當 development diagnostics，新的
formal reserve 必須 source-disjoint 且 implementation freeze 後只跑一次。完成、失敗
或需要決定時保留證據並直接決定 M38，不需等待使用者確認。

## 2026-08-26 latest override after M37 frozen mechanism pass and Safari surface failure

M37 已完成並凍結，正式結果不可回寫或重跑。12-case／6-pair zh-en-ja
source-disjoint reserve 在同一 `qwen3.5:9b`、byte-identical current、exact scored
prompt-token parity 下，baseline policy 16.67%，M37 typed relation 100%，差
+83.33pp；system pair divergence 100%，baseline pair invariance 100%；latency
ratio 1.0634、completion ratio 1.1075、raw／mental-fact write 0，全部 formal gates
PASS。M37 可以跨已實作 morphology／bounded paraphrase 與英文→中文 trigger reuse，
但不等於 open-domain semantics。

隔離 Safari 四輪實際驗證 candidate → support 後保存 → 英文 paraphrase 命中 → 中文
跨語命中，內部機制成立；visible Japanese format 4/4。產品表面驗收明確 FAIL：一輪
把 report stall 擴寫成未提供的「等待結果」，一輪只重述問題而未實現
`share_arousal`，support turn 又不自然地重問需求。因此 M37 formal surface proxy 不得
當作 semantic grounding、persona 或 felt-understanding 證據。現有 M37 core、dataset、
protocol、freeze、formal raw 均不得依 Safari 結果修改；dashboard/report/evidence 已由
post-reserve manifest 分開保存。

下一個單一產品里程碑是 `M38 Target-Guarded Multiscript Feedback Linkage`。只處理
feedback 是否確實在修正上一輪 prediction／branch：中文 `不對`、`不是這個意思`、
英文與日文對應更正必須在 current feedback 同時包含可辨識 replacement target 時才可
link、contradict 並撤銷／替換；普通句內否定、否定外部事實、沒有 pending prediction、
沒有 replacement target 或 target 不唯一時必須 fail closed，不得把表面 `不／not／ない`
本身當成更正。

先凍結新的 source-disjoint multiscript correction／ordinary-negation reserve 與
annotation-integrity protocol，再實作 linkage、trace、graph、evaluator。保留 M37 frozen
relation、M34 audit history、M27 causal discipline、natural Japanese guard、persona、
protected routes、raw-free persistence 與 token/cost audit。M38 不修 M37 已揭露的日文／
內容 surface 缺陷；那是下一個獨立 `M39 Semantic + Persona Surface-Act Verifier` 的單一
核心變因。完成後 tests、一次 sealed reserve、隔離 Safari、多輪圖像與誠實 pass/fail
報告，然後直接決定 M39，不等待使用者確認。

## 2026-08-27 latest override after M38 frozen failure and Safari linkage pass

M38 已完成並凍結，正式結果不可修改或重跑。18-case zh-en-ja source-disjoint
reserve 中，current heuristic baseline 44.44%，M38 94.44%，差 +50pp；ordinary-negation
false linkage 0/6、targetless rejection false linkage 0/3、raw／mental-fact write 0、
median 0.000667s、p95 0.001715s。但 unique-target correction recall／replacement accuracy
只有 88.89%，M34 revision accuracy 94.44%；一個中文 word-order case 安全 fail closed，
所以 overall decision 與四個 accuracy gates 保留 FAIL。不得結果後加 exact template。

隔離 Safari 真實 Web 已驗證 unique correction 可完成 `solve_regulation → share_arousal`、
ordinary negation 不會誤改 branch、targetless rejection 不會捏造 replacement 並改走低壓
clarification；adaptive store 無 raw test utterance。Safari 同時暴露 M39 的 retained
counterexample：英文 `I didn't sleep last night...` 被日文 surface 成
`私は昨夜寝なかった...`，造成 speaker-role 反轉；另有 report-stall cases 雖選對 policy，
visible reply 仍可能增添未提供情節或只重述內容。

下一個單一產品里程碑是 `M39 Semantic + Persona Surface-Act Verifier`。研究 intervention
只能改 final visible-surface verification／repair，不得改 M34 branch selection、M37 relation、
M38 linkage 或 frozen result。先建立並封存 source-disjoint reserve／protocol，至少分成：
source speaker/entity/polarity preservation、unsupported content addition、selected-policy act
realization、natural Japanese/persona boundary、protected-route noninterference。verifier 必須在
final Japanese guard 後稽核；可以做 bounded deterministic repair、safe regeneration 或 abstain，
但不能僅靠 lexical hit 把語意錯誤判 pass，也不能把 private intent 寫成 fact。

reserve 要包含同一 selected policy 但不同 literal／source roles 的 counterfactual cases、direct
Japanese 與 translated zh/en、M37 trigger-authority cases、M38 correction/ordinary-negation cases。
先 freeze 後只跑一次 formal reserve；分開 mechanism audit、semantic fidelity、persona/naturalness
proxy 與真實 Safari 內容檢查。無人評時不得宣稱 felt-understanding preference。完成 tests、一次
sealed reserve、隔離 Safari、多輪圖像與誠實報告後直接決定 M40，不等待使用者確認。

## 2026-08-27 latest override after M39 bounded pass and retained upstream route failure

M39 已凍結，24-case reserve 全部 gates PASS；這是 metadata-audit baseline 25% →
bounded final-surface action 100% 的 deterministic mechanism evidence，不是同模型生成勝率。
Safari 實際修正 user/agent role inversion，並讓 M37 已選 companionship 真正表現在最後
日文回覆；207 regression tests 通過。M37/M38/M39 frozen implementation/result 均不得改。

Safari 新反例：`Yes, that's exactly right.` 成功支持並保存 trigger relation，卻被上游誤判
`safety_sensitive`，產生疏離回覆。M39 不可覆寫 protected routes，因此這個失敗保留。
下一個單一里程碑 `M40 Affirmation vs Safety Route Disambiguation`：只讀定位 actual signal、
seed intent/scene 與 low-road attribution，預先封存新的多語 reserve/protocol，再用独立
wrapper/module 修正有足夠可觀察依據的 benign support 誤路由。真正危險、邊界、混合訊號、
不確定情況不能因出現 yes/對/そう 就被放行。trace/graph 要保留 original 與 corrected
attribution；M37 support persistence、M38 correction、M39 surface 與 Japanese/persona 不退步。
一次 frozen reserve、回歸、隔離 Safari、多輪圖像與誠實報告後直接決定 M41，不需再確認。

## 2026-08-27 latest override after M40, M41 and M41.1

M40完成並封存：同rule code/cue inventory只改Latin token boundaries，修正
`that's exactly`被compact成含`sex`的誤判。27case formal一次PASS，70.37%→100%，
12個真正/混合/分隔protected cases全保留，p95 audit2.01ms、0模型呼叫。
Safari確認英文正常、M37約定保存/重用、M39陪伴表面保留，但必須保留日文
`大丈夫`中`夫`觸發marriage_boundary，以及支持後V2.13仍不必要地重問。

M41修主圖late nodes遺失；初始Safari的same-cycle history副本仍過時，M41.1再獨立修正，
沒有修改M41 freeze。9 focused/225 selected regression通過。真實Safari中M40與M39
nodes可展開，payload與當輪logic/歷史相符；缺source不造node。全Web JSON並非完全一致，
因Web delivery後補latency/scheduler metadata，不能把這件事藏掉或寫成完整telemetry同步。

最新執行入口是`uruha_web_ui_m41_1.py`／`start_uruha_live_m41_1.py`。
目前測試Safari是127.0.0.1:7879、temp root `/tmp/uruha-m41-1-safari.qxjuet`；
原有27tabs未關，沒有production DB寫入，沒有commit/PR/merge/deploy。
read handoff §7.54/7.55、M40/M41 acceptance與M42 plan，check git status後直接續做M42。

M42單一變因是CJK relationship-request evidence，不是肯定句白名單：區分詞內漢字、
第三者關係敘述與指向角色的婚姻/獨占要求。先封存新的source-disjoint reserve；
務必含真正`丈夫`/`嫁`要求以防移除誤判時同時破壞邊界。M37–M41.1所有freeze/result保留。
支持後不該重問是之後獨立變因；不需要再向使用者確認開始。
## 2026-08-27 最新續接覆蓋：M42 已封存，下一步 M43

先讀 handoff 第7.56節、`analysis/m42_cjk_relationship_evidence_acceptance_2026-08-27.md`
與 `research/m43_supported_feedback_closure_plan_2026-08-27.md`，再檢查 git status。
M42 33case bounded mechanism PASS不代表Web產品品質通過。M42有9個有效Safari輸入，
其中arousal重問、第三者早餐錯問角色、protected reply錯套dirty意象都是保留FAIL。
10個accepted中第2輪是Unicode自動輸入失敗，別拿它當有效日文測試；後續用paste。

下一個M43只修已驗證supported act如何結束確認並取得回覆authority，勿順便改
meal-check或安全surface；新reserve先凍結、舊M37–M42不改不重跑。
新站入口`uruha_web_ui_m42.py`，URL`http://127.0.0.1:7880/?m42safari=1`，
temp`/tmp/uruha-m42-safari.pqqcs9`、session`20260827_150256_5c1f547b`、PTY38814。
7879舊測試站已停止；27個Safari tabs保留、沿用最後測試tab。不要把旧頁打不開
當新站故障。M43目前只有定位與計畫，沒有宣稱實作完成。

## 2026-08-27 夜間最新覆蓋：M43 完成有界修正，下一步 M44

先讀 handoff §7.57、`analysis/m43_supported_feedback_closure_acceptance_2026-08-27.md`
及 `research/m44_executed_action_feedback_plan_2026-08-27.md`，核對 git 與 frozen hashes。
保持 development-first 與安全 worktree；不用再次詢問要不要開始。

M43 對已有 decisive linked support 的純確認做 current-act closure；24case 作者編寫
typed-contract 24/24 vs M28 15/24，223 選定回歸通過，另 1 純 CSS test。主 Safari
10 有效輪中的 4 次純確認為 3 成功、1 缺 pending 失敗；49/49 可用認知 payload
在 logic／主圖／同 cycle history 相同。精確 pending close 沒有 Web 正例，只有契約。

不得隱藏 M43 失敗：presentation trigger 不認、M32 清掉真正 M37 行動的 pending，
導致下一輪日文確認再泛問；新增實用要求雖未被 M43 吞掉，原 planner 仍答非所問。
M44 是修第二項的 post-emission executed-action receipt，不是增加肯定句白名單。
必須先封存新案例，保留純字面／保護路徑、不覆寫其他 pending 或既有 resolved ledger，
而且仍由下一輪真正 feedback 決定支持／反駁／未知，不能建 receipt 就算成功。

M37–M43 frozen core/tests/eval/result 全不改。M43 原 plan 檔被 M42 manifest 封存，
不要更新那個舊檔；最新實作／限制都在 M43 acceptance。
最新 UI `uruha_web_ui_m43_readable.py`（CSS-only overlay）、live `start_uruha_live_m43.py`。
Safari `http://127.0.0.1:7882/?m43readable=1`，temp `/tmp/uruha-m43-readable.AWVJxc`，
PTY67266；27 tabs 保留、沿用最後測試 tab。7880/7881 舊服務已停止但資料未刪。
主驗收完整 log 在 `/tmp/uruha-m43-safari.xZvLgA`，精簡證據已存 analysis。

## 2026-08-27 夜間最新覆蓋：M44 回饋紀錄已接通，下一步 M45

先讀 handoff §7.58、`analysis/m44_executed_action_receipt_acceptance_2026-08-27.md`
與 `research/m45_actionable_help_delivery_plan_2026-08-27.md`，核對 git/freeze 後直接續做。
M43+M44 已本機實作並驗證，不用再問是否開始；M45 目前只有定位與規格。

M44 將已執行、M39通過、M37有來源的策略補成 next-user-turn receipt；不改先前
plan、其他 pending 或 resolved outcome，建立紀錄不算支持。233 選定測試過，
唯一 24-case 作者自編契約 24/24 vs 原 M43 19/24，5/5 補記錄、0/19誤登記。
這不是獨立 holdout 或 LLM 優勢。runtime test 有 fake generation/fault injection。

9輪真實隔離 Safari：turn3/5/7 補紀錄，turn4/6/8 分別支持／否定／未知。
M43失敗的日文確認現能正常承接；56/56 graph source/history payload相同，9/9圖
連線/budget通過。9/9日文不等於自然度滿分；turn8有「明日に」措辭瑕疵。
turn6真正否定並換策略，卻只有「一緒に決めよ」，沒有給實用步驟，必須保留FAIL。
M45修這個「策略被選中≠行動已交付」缺口；不硬編本例答案、不擴寫心理事實。

M37–M44 frozen core/tests/eval/reserve/results 均不可改、正式 reserve 不重跑。
M44舊plan已被M43 manifest鎖住。最新Web `uruha_web_ui_m44.py`，
`http://127.0.0.1:7883/?m44safari=1`；temp `/tmp/uruha-m44-safari.JZBsIK`，
session `20260827_224641_b6aae58e`、PID4142／PTY80022，先查是否存活。
舊7882已停止，舊檔全保留；27tabs未增減，沿用最後測試tab。正式DB前後hash一致。
M44user wait 2.0183–14.2507s，不把毫秒core check當整輪速度；有2個無turn ID timeout。
仍未commit/PR/merge/deploy，勿碰原始dirty checkout。Goal工具目前仍paused且objective
含舊V2.11段落；不要假稱已更新工具目標或完成整個Goal，依最新handoff手動續做。
