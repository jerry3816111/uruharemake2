# P4-BE：來源綁定的 role/value prompt 成對比較，正式 FAIL

P4-BE 的題目、契約、評分器與唯一 producer prompt 變因先固定於 `90b4c4af2583f37a43997f9662485e81584fae04`；一次性 runner 與 fake transport 測試先固定於 `93938c6ed8d27393a24274cc62d5b5ff12d49751`。正式呼叫前 preflight 核對 freeze、檔案 hash、模型 digest、硬體、既有本機 Ollama 與尚不存在的結果路徑。2026-09-29 對同一批全新 developer-authored 6 個 positive、8 個 unavailable controls，使用同一個本機 `qwen3.5:9b` 各比較 P4-BC 原 prompt 與 P4-BE 新 prompt。**28/28 scored calls 完成、28/28 JSON 可解析、0 retry、每 arm/case 唯一一次**。逐案原始輸出與評分在 [`p4_be_role_value_prompt_evidence_2026-09-29.json`](p4_be_role_value_prompt_evidence_2026-09-29.json)。正式判定 **FAIL，`selected_prompt=null`，產品 runtime 未改，下一狀態 `REVIEW_REQUIRED`**。結果不得重跑、改題、補 gold 或把局部改善追認為通過。

## 問題、單一變因與事前判準

P4-BD 發現來源文字雖可逐字擷取，仍可能取錯 task object、忽略數量／停止條件，或與必填日文 slots 不一致。P4-BE 只問：在六種既有 bounded-action template 下，讓 raw dialogue→typed spec producer 明確保留每個 evidence role 的 owner、predicate、肯否、數量及完成條件，能否在**同題成對對照**中改善整包正確性？P4-BE 只改 producer 的系統 prompt 證據指示；dynamic schema、normalizer、P4-BB compiler、六個 template、模型、M2 Pro 32GB、temperature `0`、seed `20260927`、`num_ctx=4096`、`num_predict=480`、20 秒單呼叫上限與零重試都沒改。兩 arm 同題、同 evaluator、交錯順序；候選 prompt 更長，實際 token 另列成本。未使用影片、真人資料或正式記憶。

事前凍結的**絕對 gate**要求候選 JSON `14/14`；positive normalized typed、非 span 欄位、template、role/value evidence、完整 packet、日文 slots、下游 compile、mechanism、自然日文、整包 full accept 各 `6/6`，接受的 atoms `18/18`；controls unavailable＋reason `8/8`、false spec/source violation `0`、完整 token accounting、最大呼叫 `≤20s`。另要有 paired BE-only full pass 至少1、BC-only full pass為0、至少1個兩邊 source identity 均有效的 raw role/value BE-only 改善。**絕對與 paired 兩組 gate 都須通過**才可選新 prompt；strict single-gold exact 只照報，不作新的 gate。

## 正式數據：一個真改善不足以選用

| 同一批14題的指標 | P4-BC 原 prompt | P4-BE 新 prompt | 事前候選門檻 |
|---|---:|---:|---:|
| 完成且 JSON 可解析 | 14/14 | 14/14 | 14/14 |
| positive normalized typed／非 span exact／template | 6/6、4/6、6/6 | **5/6、3/6、5/6** | 各6/6 |
| role/value evidence／完整 packet | 1/6、0/6 | **2/6、1/6** | 各6/6 |
| 接受的 role atoms（normalized） | 12/18 | 11/18 | 18/18 |
| canonical 日文 slots／下游 compile | 4/6、6/6 | **3/6、3/6** | 各6/6 |
| mechanism／自然日文／full accept | 6/6、6/6、0/6 | **3/6、3/6、1/6** | 各6/6 |
| controls unavailable＋reason | 8/8 | 8/8 | 8/8 |
| false spec／assistant 或 private source | 0、0 | 0、0 | 0 |
| strict evidence／spec exact（僅診斷） | 0/6、0/6 | 0/6、0/6 | 非 gate |
| max／median scored call | 15.32578／10.11207 秒 | 16.079／10.47381 秒 | max≤20 秒 |
| prompt／completion tokens | 12,811／3,732 | 16,843／3,749 | 完整記帳 |

同題配對為 BE-only full pass=`1`、BC-only=`0`、雙方 pass=`0`、雙方 fail=`5`；兩邊 source identity 合法的 BE-only **raw role/value** 改善=`1`。因此 paired advantage gate 通過，但 P4-BE 自身的多項 absolute gate 失敗，正式結論仍是 FAIL；不能拿 `0/6→1/6` 宣稱「新系統較好」。候選相較原 prompt 多 `4,032` prompt tokens（約 `31.5%`）、`17` completion tokens；median／max 單呼叫分別多 `0.36174`／`0.75322` 秒。28 次 scored calls 共 `29,654` prompt、`7,481` completion tokens，call wall-time 加總 `328.1185s`（不是實驗端到端時長）；prewarm `4.08504s` 另列。六題太少，沒有顯著性或母體優勢主張。

## 可核對的前後例子與失敗層

- **有界真改善**，中文簡報案 `p4_be_zh_scaffold_001`：來源是「我的簡報是一片空白……請只給我一個現在能開始的小步驟」。原 prompt 把 request 擷取成 `小步驟`，漏掉「只給一個／現在能開始」；新 prompt 保留 `請只給我一個現在能開始的小步驟`，三個 evidence role、slots、下游 compile 與整包都通過。這一題支持 prompt 可在局部改善角色／值擷取，不支持普遍改善。
- **日文 slot 倒退**，中文收據案 `p4_be_zh_group_001`：兩 arm 都取到正確的 task/rule/completion 三角色，但新 prompt 將中文 `我桌上的報帳收據` 直接填到 `items_jp`，且 `left_label_jp=公司名あり`，使日文 slot 契約／compiler 拒絕；原 prompt 的 evidence 合格、compiler 可編譯，但 `items_jp=機の領収書` 仍不等於凍結 canonical 值。這是 producer 的完整 packet 問題，不能用 evidence role 一項掩蓋。
- **英文完整性倒退**，`p4_be_en_extract_001`：原 prompt 的 completion=`exactly one` 已漏「recorded decision／then stop」；新 prompt 改成 `then stop` 仍漏 one/decision，且必填 `unknown_constraint_jp` 為空，normalizer `typed_spec_contract_mismatch` fail closed。這不是傳輸錯誤。
- **非來源片段與條件漏失**，`p4_be_en_verify_001`：新 prompt 的 limit=`check once ... then stop` 含原文不存在的字面 `...`，source-exact compiler 拒絕；condition=`contains the project's name` 又漏「subject line」，limit 漏 `Before sending`。原 prompt 能 compile，但 task object=`draft email` 範圍過大、limit=`check once` 不完整，也不能判 full pass。
- **回覆形式誤當任務限制**，日文 `p4_be_ja_atomic_001` 兩 arm 都將「最初の一手を教えて」類片段放在 limit，而實際任務完成條件是「今日の日付を書いたら完了」。新 prompt 沒修正這個語用／角色錯置。日文關分頁案也未完整達 role/slots；其中 `そのタブ` anchor 的事前評分可能保守造成個別假陰性，不能事後改 gold，也不能解釋前述明確失敗。

## 可信範圍與必要設計審查

本次證據支持的是：一個 prompt-only、單模型 9B、六模板固定 ontology、開發者標註的本機離線 proxy，出現一案局部角色改善，但**無法穩定交付正確來源綁定的完整 typed packet**。controls `8/8` 與 source identity 正確不代表 positive 成功；source ID/span 受本次 dynamic enum 限定，零違規也不能外推到開放來源安全。window＋語義 anchor scorer 可擋已列反例，但也可能拒絕其他合理片段；這不是兩位真人標註或自然語言全面正確性的證明。P4-BD 與 P4-BE 已是此問題兩個有根據的修正批次；現有題均已曝光，不能在它們上面繼續修 prompt 追分。

`REVIEW_REQUIRED` 的最小反例是：prompt 可修中文 request 的「一個／現在」，卻同時讓 `items_jp` 混入中文、英文 packet 漏必填 unknown、英文字面 evidence 編造 `...`，而日文回覆形式仍錯放任務完成限制。已排除「模型沒回應／JSON 解析／重試／外部 source／control 失守」作為主因。需要先審查**互斥的下一個單一變因**及其代價：

1. 把 source-bound evidence 的角色、原文 span、完成條件做結構化表示／獨立驗證，再讓模型輸出 slots；可針對語義錯置，但會新增階段、標註與 latency，須先定資料邊界和對照。
2. 只對已確認 template 的 canonical 日文 slots 做 deterministic materializer；可處理 `items_jp`、缺 `unknown_constraint_jp` 等 packet 錯，**不會**解決錯角色或捏造 evidence，須另列研究問題。
3. 若六模板的上游路徑成本高於可驗證價值，維持 fail-closed fallback、縮小使用範圍；不把低層離線結果接成一般對話能力。

三者不可在同一次實驗混合，亦不可削弱 baseline 或沿用這批已曝光題當新 holdout。若要學術主張，還需獨立標註有效性、未曝光 temporal holdout、同模型公平全管線對照與真人偏好；本卡沒有完成這些。產品 full runtime、Safari 圖像、VRM／Function Calling、正式記憶與人評都**未因 P4-BE 驗收**。使用者不需自己架 server；此次僅用已存在的本機 Ollama，沒有外部部署。
