# P3：額外的記憶與狀態機制，是否改善真實回覆？

2026-09-09 設計定案。數值與固定 prompt 以 `configs/p3_product_comparison_v1.json` 為準。
本規格是 GPT6 對 GPT5 的設計交接。當前只放行 P3-A 離線實作；沒有放行比較生成。

## 1. 研究位置與可反駁問題

長期方向仍是從過去可觀察資料，建立能預測、修正個人反應的候選計算模型；產品需讓使用者感到被接住。
P3 回答其中一個必要問題：在相同可見歷史、同一基礎模型與共同資源上限下，现產品的記憶、狀態、預測與
修正機制，能否改善最終日文回覆，或者維持品質並減少已量測的生成 token／延遲？
完整 LLM 也能推測言外之意。不能把只看當輪、刻意不推理或缺少人格條件的弱 baseline 當主要對照。

本批 positive／negative 都是有用的交付。自動代理評分通過僅允許稱「這批建構案例中的條件式 proxy 優勢」。
要談真實被理解感需人評；要談個體未來行為方程式需既有 M55–M62 的真實縱向證據。本規格不改其 gates。

## 2. 三個條件與資訊流

| 條件 | 得到什麼 | 做什麼 | 留下什麼 |
|---|---|---|---|
| full_history_direct | 完整共同歷史、當輪輸入、共同人格契約 | 直接生成，可自行考慮語用與記憶 | 日文回覆、實際成本 |
| full_history_deliberate | 同一完整歷史、輸入、人格契約 | draft → 對照歷史檢查 → revise | 最終日文回覆、三步成本 |
| product_system | 同一歷史來源、輸入、人格契約；由既有流程形成的持久狀態 | 現產品檢索、推測、驗證、規劃、表達與寫回 | 真正 final、graph、state 變化與全部已記錄成本 |

deliberate 是本實驗明定的強比較策略，不是某篇論文的官方「一般深思」定義，也不限制模型思考只能如此。
兩個 baseline 都保留，主張品質優勢必須同時對兩個成立；不能看結果後只挑較弱的一個。

逐輪先固定 `prefix_t`（當輪以前所有可見 user／assistant 訊息，包括之前 session）、`input_t` 和 hash，
再建立三個 view。baseline 不可讀 system 的當輪 output、graph、state、未來輸入或 scorer annotations。
system 不能讀 baseline outputs／評分。三者的 source-history hash 與 input hash 必須相同；檢索得到較少資料
是 system 的選擇，但 source 的可用資訊不能比 baseline 多。

### 共同歷史的明確限制

選用可由現產品直接運行的 **system-anchored prefix paired** 設計：完成這一輪三個條件後，只把 system 的
真實 reply 追加至下一輪共同可見歷史；兩個 baseline 回覆不寫回 system。system 持久狀態一路延續，baseline
每次得到完整同一 prefix，所以不是 recent-only 或 current-only baseline。每個 case 有獨立 DB，case 內跨
session 重開需保留該 case 的 DB／adaptive model，baseline 的可見歷史也不能遺失。

這估計的是「在 system 實際走出的共同對話歷史上，誰的下一個回覆更好」。歷史由 system 產生，可能偏向 system；
不能把它稱為兩個獨立對話者的整場人類偏好實驗或不受歷史分布影響的全面優勢。要外推到獨立對話，需另立
共同外部觀察歷史的載入驗證或人類隨機分派；本批不新增觀察歷史重建器。

事先生成固定 order schedule：以 seed 打散三条件順序，必須跨 case 平衡；從同一 before snapshot 建 view，
即使 system 先執行，也不能把這輪結果漏給後執行的 baseline。wall time 比較同機序列執行，禁止並行 inference。

## 3. 模型、人格與資源控制

- 固定 product source commit `34bef3d01d236873b4aa384b76aba2893ff9949d`（P2＋記錄修正）。不得重用舊 V2.14/M35
  的結果、弱 baseline 或旧模型設定冒充 P3。舊模組只可參考 raw-free ledger／blind packet／bootstrap 介面。
- 所有生成路徑固定同一個 Ollama `qwen2.5:7b` digest。M31 預設 `qwen3.5:9b`，必須在 isolated worker import
  以前套用 config override；其他未知模型、網路端點或未記錄 call 令 run invalid。RightBrain transformer 關閉，
  與當前 P2 本機 probe 一致；必須在報告揭露，不能聲稱完整雙模型產品比較。
- 全部生成 temperature=0、seed=20260909、top_p=1、num_ctx=8192、think=false、0 transport retries。
  這是受控 P3 設定，不是 P2 run2 的完全複製；P2 本身曾使用 temperature=0.1。只在 harness 的 transport adapter
  中正規化，不能改正式研究入口或永久預設。必須攔截 OpenAI-compatible 與 native Ollama 兩條 path。
- 所有條件使用 JSON 的同一人格契約，保留系統原有安全／語言 guard。不要把「final reply only」指令錯套到
  需要 JSON 的內部 planner。共同可見輸出規則與 persona block 要進入 baseline 與 system 的相關 request；記錄
  block hash。內部 planner 的 schema／任務指令是架構差異的一部分，不能要求它們和 baseline prompt 完全相同。
- 人格引用 `public_persona_evidence_v1` 中 002／003 的開發假設；率直、對陌生人保留距離，不代表公開人格全面還原。
  未公開經歷與未觀察心理保持未知；不得下載額外 persona corpus 或打開正式人物 outcome 來補表現。
  smoke 前盤點 system 讀取的其他靜態 persona/fact assets：若會影響題目，必須同樣提供給 baseline，或將該
  case 判資訊不對稱。只共享一段風格文字不能證明所有人物知識相同；人格瑣事／真人生平不在本批題目範圍。
- 每條件／每輪共享上限：累計 input 32,768 tokens、output 768 tokens、wall 60 秒。direct 最多 1 call／768
  output；deliberate 3 calls、每次最多 256；system 最多 4 calls，單次最多 320 且受剩餘總額限制。
  extra calls 不能各自重新獲得整輪預算。凡有 retry、失敗、驗證、修正或額外生成均須入帳。
  三者 wall 邊界均為收到該輪 view 到 final／guard／必要寫回結束，含各自檢索與處理；排除共同資料讀取、
  初始化與離線展示渲染（這些另外計）。timeout 後 provider 是否仍在生成不確定時，停止整批新呼叫並留
  measurement failure，不能用客戶端返回時間冒充已完成模型運算或讓下一條件和它競爭硬體。
- 每個 request 的 input＋允許 output 必須裝進 8,192 context；共同歷史本身限 6,000 tokenizer tokens。
  完整 prompt 超標時 fail closed，不默默截斷、摘要或用字數當 token。
- preflight 使用與本機 model digest 可核對的 tokenizer／template；實跑另外以 provider 的
  `prompt_eval_count`／`eval_count` 或已驗證 equivalent usage 核帳。若事前估算與實際不一致越界，保留 run 並
  判 fairness invalid，不事後調大上限。找不到可核對 tokenizer/template 時保持 not_ready。
- 「共同上限」不等於 actual token 相同。報告列 actual input/output、call 數、Chroma 操作、wall median/p95、
  setup/warmup、DB bytes；既有 ledger 沒有的 CPU/RSS/energy 寫 unavailable。不得用 Python worker RSS 冒充
  Ollama daemon/GPU 的 RAM。無需為了填表新增能源平台；只能主張已量測資源的成本差異。

## 4. Corpus 與評分資料隔離

資料尚未製作。先完成並凍結 harness、prompt、config，再依以下已定案的配額建資料。不得在生成後重標目的。

1. smoke：6 個 cases，每 family 1 個，各 4 輪；三種輸入語言各 2 cases。明列 developer_smoke，可用來修接線。
2. confirmation：24 個 source-disjoint cases，每 family 4 個，各 4 輪；三種語言各 8 cases。family/language
   聯合配额以 family index f=0..5、case variant k=0..3 的 `(f+k)%3` 決定，語言順序 zh/en/ja。
3. 每個 case 至少一個 turn 附明確可觀察的確認／否定／更改需要；correction 不可一律預設 system 前輪猜錯。
   用自包含的使用者補充，驗證狀態必須依實際前輪 prediction 才能判 supported/refuted/unknown。
4. 六類：需要改變、婉拒或暫時同意、字面與情緒需求不同、關係與玩笑界線、記憶說話者來源、未知與換話題。
   其中明確 withdrawal、self identity、跨語言 final reply、無來源心理推測等是橫跨案例的共用 regression 指標。
5. 每個 case 來源含 source_id、作者／工具角色、建立時間、exposure status、language、family、session 邊界、
   turn ID 與文本 hash。generation view 僅含目前已可見對話；family、期望、gold、評分指示、後續 turn 不可傳入模型。
6. scorer annotations 分檔；寫 expected acceptable actions、unacceptable unsupported claims、可見 evidence turn IDs，
   不指定一個唯一漂亮句子。對「只說腦子停不下來」且沒有其他證據的例子，不能把缺眠／想被吐槽任一項
   當成已知答案；有根據的澄清或多種合理回覆皆可接受。
7. source partitions 與歷史 P2/M/其他開發資料分開；不得只是把同句換語言、換標點或改名 holdout。除了 exact hash
   去重，需檢查與 P2 五組的實質語境重複；有衍生關係就標開發，不能算 source-disjoint confirmation。
8. 作者與實作者若讀到內容，label 必須是 `author_exposed_development_disjoint_confirmation`。這不是獨立人類
   holdout，也不排除 base-model pretraining exposure。完整 corpus 與 annotations 在第一個 confirmation call 前
   鎖 hash；若實作者先讀而改過產品/prompt，這批資料降級為 dev，另由設計審查定新 reserve，不能偷偷沿用。
9. 另做 1 組 50 輪 developer stress，包含跨 session 記憶、撤回與 topic change。與主分數分開，不把 50 輪當
   50 個獨立受試者；上下文越界須報失敗，不能縮掉 baseline 歷史。P4 整合前需完成；當前 P3-A 不製作它。

## 5. 評分、成功／失敗與不確定

生成與評分程序分開；固定所有 outputs／errors 的 manifest 後才讀 annotations。先做機器可檢查的來源／角色／
future leak／語言粗篩，再用本機 qwen3.5:9b 做 blinded proxy judge（若本機不可用則 pending，不買 API 或換 judge）。
這個 9b judge 不參與回覆，也不能為 system 提供未來資訊；評分成本獨立於產品成本。

每個 target 比 S/direct 與 S/deliberate，各跑 AB／BA 一次（同一 judge，不能稱兩位獨立評審）。judge 看相同
prefix、input、匿名兩個 replies、該輪 annotations 與下列 rubric；看不到 condition 名称、graph、call 數或架構。
每次輸出 JSON `{scores:[{reply_slot,attunement,grounding,correction,continuity,unsupported_assertion,
japanese_issue,identity_issue,evidence_turn_ids,reply_quote}],preference}`。correction 無適用事件為 null。
所有分數只能 0/1/2；quote 必須是回覆原文 span，evidence IDs 必須指向当時已可見 turn。invalid JSON、future ID、
不符 span 不重試、不填成功，保留 unavailable。可以引用接下來 turn 驗證「前輪預測」，但不能當前輪已知 evidence。

| 維度 | 0 | 1 | 2 |
|---|---|---|---|
| attunement（主要） | 忽略／違背可見需要 | 部分接住，或無必要泛問 | 回應有根據的目的；未知時澄清得當 |
| grounding | 捏造／誤歸因 | 大致有根據但不精確 | 事實／角色／未知界線正確 |
| correction（有適用事件） | 延續被撤回的假設 | 當轮承認但仍混入舊假設 | 自然退讓，後續相關輪也尊重新資料 |
| continuity | 矛盾或硬套無關舊資料 | 部分保持 | 只在相關情境保留並更新經驗 |

不能只依關鍵詞或 system 自稱 selected policy 打分；主要評分對象是最終回覆。trace 用來定位，不用來替 final 加分。
同一 rubric 可輸出 blind human sheet；沒有真人填寫時 human preference 為 unavailable，不能填零、proxy 或模型偏好。

統計以 case 為 cluster：先每 case 平均，再比較 24 個 paired case differences；10,000 次有放回 case bootstrap，
固定 seed。AB／BA 映回實際條件後分數取平均，另外報方向一致率（tie 也需一致），不挑有利順序。
缺失生成屬該 case 的 product failure（attunement=0，列 failure）；缺失 judge 不補分，coverage 要包含這些項目。
若生成失敗造成後續依賴缺失，case 後續列 not_run_due_to_prior_failure 並保留在 scheduled denominator。

必須依以下順序判斷，不能只摘綠色指標：

- **invalid_measurement**：模型/digest、來源、共同 prefix、budget、future leak 或 DB 隔離任一不合。保留結果，禁止優勢結論。
- **inconclusive_proxy**：評分可用率 <95%、AB/BA 一致率 <90%，或 CI 太寬；不能稱無效或有效已證明。
- **quality_proxy_pass**：對兩個 baseline 的 attunement 平均各提升至少 0.2/2，paired case CI 下界 >0；
  unsupported assertion rate 增幅各 ≤5 個百分點，correction 平均差各 ≥-0.1；觀察到的日本語／identity 違反率 ≤5%。
- **cost_proxy_pass**：對兩個 baseline 的品質差 CI 都完全位於 [-0.1,+0.1]，相同品質下生成 token 與 median wall
  各至少減少20%，p95 回退不超過10%，且同樣通過上述 grounding/correction/language guards。Chroma 與不可得成本
  另外列出，因此只可稱「這些已量測指標較省」。
- **retained_no_demonstrated_advantage**：測量有效且 judge 足夠穩定，仍不達以上門檻。交付負結果，由 GPT6 決定
  是否以單一消融簡化；不得先改提示／題目再拿同一 confirmation 當新證據。

以上門檻是專案事先選定的工程取捨，不是官方人類理解標準。24 cases 的小型 proxy 不能保證普遍化或可靠人評。

## 6. 實作入口與必要驗收

新檔案建議僅：`p3_product_comparison.py`（純資料與 view／budget／validation）、`run_p3_product_comparison.py`
（isolated workers 與 CLI）、`test_p3_product_comparison.py`。沿用 ledger／graph，不複製 20,000 行 brain 或 HTTP handler。
正式研究檔、P1/P2 策略、persona data、grader 閾值與舊輸出都不在允許變更中。

P3-A 需提供：

- `load_design(path)`、`build_generation_view(prefix,current_input,condition)`、`reserve_call(budget,request)`、
  `record_usage(budget,provider_usage)`、`validate_run_manifest(manifest)` 與可注入 fake transport 的条件 runners。
- generation view 用 allowlist 新建物件，不能先複製整個帶 annotations/future 的 case 再 pop 幾個欄位。
- CLI `--mode contract --design ... --output NEW_PATH` 只能 fake/local deterministic，assert 0 network／0 real model calls。
- CLI `--mode preflight` 只檢查 versions、paths、model metadata／tokenizer 綁定；不得呼叫生成。
- `--mode run` 在缺 design＋implementation＋data freeze＋review release 任一時，以非零退出且 transport attempts=0。
  review release 是含各 artifact hash、允許 split 和 resource 上限的明確 JSON；不能有 `--force` 跳過。
  config 的 `implementation_release` 描述本次 P3-A 交接權限，不能由實作者改成 true。後續 GPT6 審查產生
  額外 release，引用原設計 digest 與 implementation/data hashes 才可授權指定 split；缺少或不匹配就拒絕。
- 每個 item／condition 先存 invocation intent，成功才存 complete。意圖存在但無 complete 的中斷不能自動重打；
  保留 terminal failure，已完成者可按 hash 重用。不照搬整套 M56 capability 平台來實現這個有限產品 runner。

必測負案例：基線漏先前 session、current system reply 偷漏、future/annotation 注入、跨 case state 混用、M31 偷用9b、
第二次 call 超總 budget、tokens unavailable、context 靜默截斷、artifact 被改／覆寫、transport error 觸發重試。
三個條件來源相同仍不代表 prompt 相同；不能用填充符號浪費 token 假造公平。
fake fixture 只驗證接線／隔離，不應指定「Uruha 必勝」。匿名位置對換後条件還原與已給定數值的差值要對稱。
實際 rubric scorer 是後續階段；P3-A 不需再建自然語言裁判。

## 7. 階段、資源與交接出口

| 階段 | 交付物 | 放行條件／下一步 |
|---|---|---|
| P3-A（現在可交 GPT5） | 上述 harness、負測試、0-call contract result、實作 diff／hash | GPT6 審查 view 隔離、所有模型路徑与 budget 接線；未過不能開資料／跑分 |
| P3-B | smoke source／annotation manifest、實作與語言規格 smoke 證據 | 6×4 輪開發 probe；最多兩個有 before 證據的修正批次，再凍結 implementation |
| P3-C | 24-case confirmation manifest、blinded scorer 規格、release | 第一個 call 前核對來源／exposure／同模型與 readiness；之後 outputs 全部保留 |
| P3-D | 一次 confirmation、proxy 統計、真實逐輪 graph 與差異頁 | 不管正負都報告；GPT6 審查因果歸因／claim；Safari 不可用仍明記 pending |
| P3-E／P4 接續 | 50 輪壓力結果；必要時一項消融；本機入口、VRM/tools 整合盤點 | 消融需新前瞻設計；P4 整合不能假稱未過 P3 的能力優勢；正式 M 線 gates 保留 |

P3-A 不需任何付費 API、模型下載或推理。contract suite 目標兩分鐘內；若單元測試要載入完整模型，先修測試隔離。
依目前本機 9 輪約31秒、2次生成的開發控制不能推算一般高模型路由的全部成本。
硬上限（不是費用或預測）：smoke 24 targets×最多8 calls=192 generation calls，judge 96 calls；confirmation
96 targets×最多8 calls=768 generation calls，judge384 calls。confirmation 生成 output 上限221,184 tokens，
judge output 上限147,456；input 預算仍逐條件逐輪核帳。以全部 calls 都逼近 timeout 算，confirmation 可接近8小時；
實際先由 smoke 測得 median/p95 提出估算再放行。0 remote paid API。不以資源不足自動降標或換模型。

每階段只更新同一 task card 與一份簡短 acceptance；不能為統計欄位另加 M／網站。支援工程要指出阻擋上述哪一 gate，
否則不做。完成 A 就標 `REVIEW_REQUIRED`，通知使用者可切回 GPT6；不可假裝平台會自動換模型。

## 8. 圖像展示的完成標準

沿用實際 runtime graph，逐輪選擇 case/session/turn；左側完整同一輸入歷史，中間三條件可見回覆／預測狀態，
右側下一輪實際驗證與改變，下方成本與 evidence level。展示至少一個成功、一個保留失敗／未知、一個撤銷例子。
baseline 沒有顯式狀態節點時標「此方法不輸出該狀態」，不能畫一條假的思考流程。
將圖節點連到該次 trace 的真實 ID／source hash；raw ledger 仍不含對話。一般聊天界面仍只顯示自然日文。
Safari 未驗收就顯示 pending，不能把離線 HTML 當操作截圖；既有拒絕的網址／控制階段不可用別的 UI 技術繞過。
