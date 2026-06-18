# UruhaBrain 方向審查與未來路線圖

產生日期：2026-04-28  
分支：`codex/vnext-research-90plus`  
目的：給後續 Codex / Gemini / 其他模型接手時使用，避免把專案帶回單純角色 prompt、單純 benchmark chasing、或只修表面台詞的路線。

## 1. 結論

目前方向是對的，但需要更精準地定義「對」是什麼。

這個專案真正有價值的地方不是「更像某個 VTuber」，而是把「人聽到一句話後到說出一句話前，中間發生了什麼」拆成可執行、可觀察、可評測的工程系統。Ichinose Uruha 風格只是輸出層的人格外殼，用來避免系統變成中性助理。它不是研究主體。

目前已經完成的主軸：

- 工程版完成度已過 90：`reports/whole_project_closing_diagnostic_report.json`
- 研究認知成熟度已被重新計算為 `93.32 / 100`：`reports/research_vnext_90plus_diagnostic_report.json`
- 左腦高頻 routing 已達成熟：`run_leftbrain_90_readiness_audit.py` 為 `36/36`
- ToM / 社會推理從早期弱點被拉到 `formal_tombench_accuracy = 0.975`
- 工作記憶與 delayed recall 已有穩定證據：`working_memory_relevance_rate = 0.9474`，`delayed_recall_rate = 0.9167`

但目前仍不能宣稱「整個系統在所有人類感面向都 90+」。原因很明確：

- `DailyDialog` act 對齊只有 `0.3`
- `surface_dialogue_alignment_score` 只有 `59.63`
- 10k 壓測的 `unique_reply_ratio = 0.0431`，代表大規模表面回覆仍偏集中
- human feedback regression 目前缺有效人工真值案例
- ToMBench 分數中包含 symbolic selector，必須誠實標註它是「認知判別器」能力，不是純生成模型能力

所以正確表述是：

> UruhaBrain 已達「研究認知架構 90+」，但尚未達「表面自然聊天 90+」。

## 2. 專案歷史判讀

### 2.1 第一階段：右腦 LoRA 與角色語氣

最早的方向集中在右腦模型，目標是讓模型學 Uruha 說話口調。這一步必要，但不是最後的研究核心。

早期錯誤很典型：

- LoRA 過擬合導致語義邏輯壞掉
- 模型會輸出不相干句子
- 遇到不懂的話只會固定拒答或固定安慰
- 回覆看似有角色，但沒有真正回應使用者語義

這說明單靠 fine-tune 無法解決「人類式思考」。右腦只能負責表達風格，不能承擔理解、記憶、情緒路由與邊界判斷。

### 2.2 第二階段：雙腦架構與工程穩定

專案接著把系統拆成左腦、記憶、右腦。這個方向符合 CoALA 對 language agent 的基本要求：模組化記憶、結構化內外部動作空間、決策流程。

本專案對應如下：

- 左腦：路由、意圖、ToM、候選 plan、貝氏重排序
- 記憶：短期、episodic、semantic、procedural
- Runtime：drives、prediction error、high/low road、event loop
- 右腦：日文口語表面化
- Quality gate：回歸與可重現性基建

這一階段方向正確，因為它把角色扮演從 prompt 變成 architecture。

### 2.3 第三階段：研究版 90+

最近的研究版 90+ 主要補上 ToM 與 social reasoning。ToMBench 從早期 `0.55` 拉到 `0.975`，這代表系統已經能處理多種心智推理題型。

但這裡有一個重要警告：

ToMBench 提升部分來自 deterministic symbolic selector。這是合理的，因為本專案研究目標是「外掛認知架構能否改善推理」，不是證明 base LLM 自發擁有 ToM。但報告與論文裡必須明講：這是 system-level social reasoning，不是純模型 zero-shot ToM。

## 3. 方向是否正確

判定：正確，但下一階段必須換主攻點。

正確的原因：

- CoALA 強調 cognitive architecture，而不是單一 prompt；本專案已符合這個方向。
- Generative Agents 強調 memory、reflection、planning 對 believable behavior 的必要性；本專案已實作類似的三循環記憶與背景整理。
- MemGPT / Letta 類系統證明 long-term agent memory 需要 tiered memory 與 context management；本專案已有 working memory budget 與 memory layers。
- RoleLLM / RoleBench 顯示角色能力需要 profile、style、context-based instruction 與 role-conditioned tuning；本專案已經把 personality 放到右腦，不再讓左腦混入人格幻想。
- ToMBench 與 DailyDialog 讓本專案可以同時測 social cognition 與一般對話 act/emotion，但目前只有 ToM 軸真正過 90。

不應該繼續走的方向：

- 不要再把主要精力放在 LoRA 語氣微調。
- 不要為了 ToMBench 繼續硬寫 benchmark-specific symbolic rule，除非同步加 contamination / holdout 檢查。
- 不要再單純增加左腦 if/else 規則。高頻 routing 已成熟，邊際收益低。
- 不要把「角色像不像 Uruha」放在研究核心。它是 demo 與輸出層問題，不是大腦研究問題。

## 4. 目前最重要的問題

### 4.1 指標自我欺騙風險

目前最大的風險不是功能壞，而是分數看起來太好。

具體風險：

- `research_cognitive_readiness_score = 93.32` 可能讓接手者以為所有研究問題都解決了。
- `formal_tombench_accuracy = 0.975` 來自架構化 selector，不能當成右腦生成能力。
- `leftbrain_dialogue_control = 100.0` 是 targeted audit，不等於所有自然語料都穩。
- `surface_dialogue_alignment = 59.63` 明確說明表面聊天還不夠自然。
- `unique_reply_ratio = 0.0431` 說明大規模輸出仍有模板集中。

後續所有報告必須同時列出：

- 認知架構分數
- 表面對話分數
- 人工回饋真值數量
- 大規模多樣性分數
- prompt-only baseline 差距

只報最高分是不合格的。

### 4.2 記憶仍像「參考資料」，還不完全像「重力」

目前記憶檢索與 delayed recall 指標不錯，但還不夠證明記憶真的改變回答形狀。

下一階段要加入：

- `memory_relevance`：這段記憶是否相關
- `memory_speakability`：這段記憶是否適合說出口
- `memory_gravity`：這段記憶應該改變 plan 的方向、語氣、距離感或信任恢復速度多少
- `memory_causality_trace`：最後回答到底是因為哪段記憶而改變

驗收方式不是「有沒有檢索到記憶」，而是：

> 同一句使用者輸入，在不同記憶狀態下，plan 與回覆是否出現可解釋差異。

### 4.3 左腦與右腦之間的帶寬還不夠

目前很多 plan 欄位已經存在，但右腦常常只吃到粗粒度 intent。

下一階段要強化這些欄位：

- `focus_anchor`：這句話真正要接的具體詞、事件、梗、情緒或前文
- `reply_obligation`：這次回覆必須完成什麼義務，例如回答、吐槽、安慰、拒絕、澄清
- `information_payload`：這句話需要帶多少新資訊
- `tone_driver`：語氣由哪個原因驅動，不是泛泛的 warmth/blunt
- `avoid_repetition_key`：避免重複的句型或語義
- `post_check`：生成後是否真的覆蓋 focus

這件事比繼續新增模組更重要。

### 4.4 Human feedback loop 還沒有成為主資料來源

目前自動 benchmark 很完整，但真實人工失敗案例仍弱。

下一階段的核心應該是：

- Web UI 每一句都能標記失敗原因
- failure taxonomy 固定化
- 標記進 JSONL
- regression dataset 自動產生
- 每次修復都跑 before/after diff
- 修復是否有效由 human-labeled cases 驗證

沒有這條線，系統會越來越會考試，但不一定越來越像人。

## 5. 未來詳細路線圖

### Phase 1：建立真實人工回饋閉環

目標：把使用者不滿意的回覆變成第一級研究資料。

步驟：

1. 在 Web UI 增加每回合標記欄位。
2. 標記 taxonomy 固定為：
   - `MISREAD_INTENT`
   - `MISREAD_EMOTION`
   - `MISSED_JOKE_OR_CULTURE`
   - `TOO_ROBOTIC_LOGIC`
   - `GENERIC_REPLY`
   - `REPEATED_REPLY`
   - `WRONG_BOUNDARY`
   - `WRONG_MEMORY_USE`
   - `GHOST_MEMORY`
   - `LOW_INFORMATION_DENSITY`
   - `RIGHTBRAIN_SURFACE_ERROR`
3. 每筆標記至少包含：
   - user input
   - previous turns
   - selected plan
   - final reply
   - expected behavior in Chinese
   - expected behavior in Japanese, optional
   - failure labels
   - severity
4. 產生 `datasets/human_feedback_regression_cases.jsonl`
5. 每次修復後跑 `eval_human_feedback_regression.py`

驗收條件：

- 至少 100 筆人工標記案例
- 每個 high-priority label 至少 10 筆
- regression resolved rate 大於 80%
- 不得只靠自動 judge

### Phase 2：記憶重力與因果 trace

目標：讓記憶不只是被檢索，而是能改變決策。

步驟：

1. 在 memory retrieval 後計算：
   - `memory_relevance`
   - `memory_recency`
   - `memory_emotional_charge`
   - `memory_speakability`
   - `memory_gravity`
2. 左腦候選 plan 必須標註：
   - `used_memory_ids`
   - `memory_effect_on_plan`
   - `memory_should_be_spoken`
3. 右腦 prompt 要收到：
   - 可明說的記憶
   - 只影響語氣的記憶
4. trace 要可視化記憶如何改變 plan 分數。

驗收條件：

- 同一句輸入在有/無特定記憶時，plan 分數有可解釋差異。
- `GHOST_MEMORY` rate 下降。
- `memory_causal_effect_rate` 大於 0.75。

### Phase 3：右腦資訊密度與多樣性

目標：解決「有回答但像棒讀」與模板集中。

步驟：

1. 每個 plan 增加 `minimum_content_units`。
2. 右腦生成後計算：
   - `focus_coverage`
   - `new_information_units`
   - `reply_specificity`
   - `semantic_repetition`
3. 若 post-check 失敗，觸發一次 constrained rewrite。
4. 建立 small human-rated set，專測「像人聊天」。

驗收條件：

- 10k `unique_reply_ratio` 至少提升到 0.10。
- `top_20_reply_concentration` 小於 0.25。
- `LOW_INFORMATION_DENSITY` 人工標記下降 50%。
- 不犧牲 `forbidden_leak_rate = 0.0`。

### Phase 4：DailyDialog / 對話行為對齊

目標：補足目前最弱的 surface dialogue alignment。

注意：DailyDialog 是英文 daily dialogue benchmark，不能完全代表 Uruha 日文輸出。但它能測 planner 是否能對一般對話 act / emotion 做合理標籤。

步驟：

1. 分析 `reports/formal_brain_benchmarks_report.json` 中 DailyDialog 錯誤分群。
2. 針對 compressed proxy 覆蓋不足的 prompt 做 planner classifier，而不是用右腦生成。
3. 明確分開：
   - user utterance act
   - expected assistant reply act
   - emotion of user
   - emotion of response
4. DailyDialog 評測報告要保留 confusion matrix。

驗收條件：

- `dialog_act_accuracy` 從 0.3 提升到 0.55 以上。
- `emotion_accuracy` 從 0.6167 提升到 0.75 以上。
- 報告中要明確標註它是 planner proxy，不是角色輸出自然度。

### Phase 5：學術報告與可重現性

目標：讓老師或外部 reviewer 能理解這不是玩具，而是可重現研究系統。

步驟：

1. 更新 `uruhabrain_system_paper_zh.md`，把研究主體改成「人類式認知中介過程」。
2. 降低 VTuber 角色模仿的篇幅，把它定位成 persona shell。
3. 加入方法章：
   - perception
   - working memory
   - prediction error
   - high/low road
   - BDI/ToM
   - Bayesian reranking
   - Levelt-style formulation
   - memory consolidation
4. 加入 limitation 章：
   - 分數可能被 symbolic scorer 拉高
   - 自動 benchmark 不等於真實人類感
   - 沒有神經資料，只是 computational analogy
5. 加入 reproducibility 章：
   - branch / commit
   - eval commands
   - report artifacts
   - dataset generation scripts

驗收條件：

- 一個老師不懂 LLM，也能看懂研究問題、方法、限制與數據。
- 報告不能宣稱「真正複製人腦」，只能說「工程上重現部分認知功能分解」。

## 6. 可參考資源

### Cognitive agent 架構

- CoALA: Cognitive Architectures for Language Agents  
  https://arxiv.org/abs/2309.02427  
  對應本專案：模組化記憶、動作空間、決策流程。

- Generative Agents: Interactive Simulacra of Human Behavior  
  https://arxiv.org/abs/2304.03442  
  對應本專案：記憶、反思、規劃對 believable behavior 的作用。

- MemGPT: Towards LLMs as Operating Systems  
  https://arxiv.org/abs/2310.08560  
  對應本專案：tiered memory、context management、interrupt/control flow。

- Letta / MemGPT framework  
  https://www.letta.com/blog/memgpt-and-letta  
  可作為未來替換或對照本地 memory manager 的參考。

### Role-playing / persona evaluation

- RoleLLM / RoleBench  
  https://arxiv.org/abs/2310.00746  
  對應本專案：角色 profile、風格模仿、role-conditioned tuning。

- RPEval  
  https://huggingface.co/papers/2505.13157  
  對應本專案：emotional understanding、decision-making、moral alignment、in-character consistency。

### Social cognition / ToM

- ToMBench  
  https://arxiv.org/abs/2402.15052  
  對應本專案：社會推理與心智理論測試。注意 symbolic selector 的分數需分開報告。

### General dialogue evaluation

- DailyDialog  
  https://aclanthology.org/I17-1099/  
  對應本專案：dialog act / emotion proxy。目前是弱點，不應忽略。

### Psycholinguistics / memory / language acquisition

- Levelt, Speaking: From Intention to Articulation  
  https://direct.mit.edu/books/monograph/4300/SpeakingFrom-Intention-to-Articulation  
  對應本專案：概念化、形式化、發音/表面化、self-monitoring。

- Baddeley working memory / episodic buffer  
  https://www.sciencedirect.com/science/article/pii/S1364661300015382  
  對應本專案：working memory buffer、episodic integration。

- Usage-based theory of language  
  https://www.frontiersin.org/articles/10.3389/fpsyg.2013.00255/full  
  對應本專案：不要把語言能力理解成硬編碼語法；應重視使用、chunking、analogy、rich memory。

## 7. 對 Chomsky / Universal Grammar 的工程判斷

不要把 Chomsky 的 Universal Grammar 當成這個專案的主工程依據。

比較穩的做法是：

- 承認人類有語言學習偏向與生物基礎。
- 但工程上採用 usage-based / construction / interaction-driven 的路線。
- 也就是讓系統從使用樣本、對話回饋、記憶、chunking、類比與錯誤修正中形成語言行為。

這和本專案方向一致：UruhaBrain 不應該追求內建一套完美語法，而應該追求「在使用中形成可修正的說話模式」。

## 8. Codex / Gemini 分工建議

Codex 作為 project manager：

- 決定方向與驗收標準
- 控制 scope
- 寫 task packet
- 審查 Gemini patch
- 跑全套驗證
- 最後決定是否 commit

Gemini 作為 implementation worker：

- 根據 packet 做局部施工
- 不自行擴 scope
- 回報修改檔案與驗證命令
- 不改未被指定的核心架構

每輪標準流程：

1. Codex 寫明確 packet。
2. Gemini 施工。
3. Codex diff review。
4. Codex 必要時補修。
5. Codex 跑 tests / audits。
6. Codex 更新 report 或 evolution log。
7. Codex commit。

## 9. 未來施工十條原則

1. 每個新機制都必須有輸入、輸出、trace、測試與 before/after 證據。
2. 不要再用「新增一個聽起來很像認知科學的模組」當進度。
3. 優先提高左腦到右腦的訊號帶寬，而不是新增更多分類標籤。
4. 記憶必須能改變 plan，不只是被塞進 prompt。
5. 自動 benchmark 只能當底線，不能取代人工失敗案例。
6. 每次報分數都要同時報弱項，尤其 DailyDialog、多樣性、human feedback。
7. ToMBench symbolic score 必須標註為 system-level scorer，不可說成 base model 能力。
8. 回覆自然度不能用字數衡量，要用 focus coverage 與 information density。
9. 右腦生成後必須做 post-check，確認是否完成 reply obligation。
10. 任何改動如果不能讓真實對話更好，就不應該進主分支。

## 10. 下一個最值得做的任務

如果下一位 Codex 只能做一件事，做 Phase 1：人工回饋閉環。

原因：

- 目前 ToM 已高，繼續刷 ToMBench 收益低。
- 工程 gate 已成熟，繼續磨基建收益低。
- 真正阻礙「像人」的是體感問題，而體感問題需要人類標記。
- 有了人工標記資料後，後續 memory gravity、right-brain density、DailyDialog 對齊都能變成資料驅動，而不是主觀猜測。

建議第一個具體 PR：

- 在 Web UI 加入每回合 failure annotation 控制。
- 寫入 `analysis/human_feedback_annotations.jsonl`。
- 產生 `reports/human_feedback_annotation_report.md`。
- 把這些案例接到 `eval_human_feedback_regression.py`。

這一步完成後，專案會從「能被自動測試證明」進入「能被真實互動修正」。
