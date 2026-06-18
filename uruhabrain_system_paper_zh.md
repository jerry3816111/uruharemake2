# 雙腦協同角色扮演系統之實證研究：以一ノ瀬うるは擬真對話為例

## 摘要

本文探討一個面向 VTuber 角色扮演的雙腦協同系統，並檢驗其是否優於「僅以單一 system prompt 驅動同一個 Qwen 模型扮演角色」的基線方法。本文之主系統將角色扮演任務拆分為三個子模組：負責語義理解與邊界控制的左腦、負責知識/經歷/經驗讀寫的記憶系統，以及負責將規劃轉寫為角色口吻的右腦。對照組則使用同一 Qwen 模型家族中的 `qwen2.5:7b`，以單一 prompt 直接扮演一ノ瀬うるは。為進行可重複比較，本文建立包含中文、英文、日文共 1000 題的多語壓力測試集，涵蓋身份、自我介紹、日常閒聊、情緒承接、關係互動、辱罵、知識邊界、設定幻覺、道德判斷與危機應對等情境。評估指標主要參照 RPEval 的 `Avg Score`、`Emotional Understanding`、`Decision-Making/Moral Alignment`、`In-Character Consistency`，並結合 ERABAL 所強調的 `Boundary Queries` 與匿名角色評測工作的匿名子集分析。實驗結果顯示，雙腦系統在整體平均分（0.8297 vs. 0.1446）、回答相關率（0.8750 vs. 0.1350）、情緒理解（0.7364 vs. 0.0401）、道德/決策對齊（0.8788 vs. 0.2576）、角色一致性（0.8739 vs. 0.1362）、邊界問題處理（1.0000 vs. 0.0952）與知識幻覺安全率（1.0000 vs. 0.8571）上均顯著優於 Prompt 基線。研究結果支持以下結論：對於高擬真角色扮演任務，僅靠 prompt engineering 並不足以穩定支撐角色行為；若目標包含人格一致性、知識邊界與多輪對話穩定性，則必須採取架構級分工，而非單一提示詞驅動。

**關鍵詞：** 角色扮演、大型語言模型、VTuber、人格一致性、邊界控制、記憶系統

---

## 1. 前言

近年大型語言模型已能在短對話中模擬特定人物或虛構角色的口吻。然而，在「高擬真、可長期互動、能守住知識邊界」這種更嚴格的場景中，單純依賴 prompt 往往會暴露出三個結構性問題。

第一，模型會在「理解使用者意圖」與「維持角色口吻」之間互相干擾，導致回答雖然流暢，卻未真正回到使用者問題。第二，模型會在技術題、知識題、系統題與 OOC（out-of-character）要求下退化為通用助手，喪失角色邏輯。第三，模型在面對情緒壓力、辱罵、危機、自傷或假設定時，常產生語義漂移、人格崩壞或知識幻覺。

這些問題對一般聊天機器人可能只是品質瑕疵，但對 VTuber 擬真系統而言，則是決定成敗的核心。使用者並不只要求「像某個人說話」，而是要求系統在長期互動中同時滿足：

1. 回答要對題；
2. 口吻要像本人；
3. 對知識與身份要有邊界；
4. 對情緒與關係要像人類；
5. 對假設定與外部注入要能抵抗。

基於此，本文研究一套雙腦協同架構：左腦負責規劃，記憶系統負責狀態與經驗，右腦負責人格表達。本文的核心研究問題如下：

> 當目標是打造高擬真 VTuber 對話系統時，雙腦協同架構是否顯著優於「同一模型 + 單一角色 prompt」的傳統做法？

本文以一ノ瀬うるは為目標角色，透過 1000 題多語壓力測試與匿名子集分析，對上述問題做實證驗證。

## 2. 相關研究

### 2.1 角色扮演評估不應只看流暢度

RPEval 指出，角色扮演模型的好壞不能只靠表面流暢度判斷，而應至少從情緒理解、決策/道德對齊、角色一致性與整體平均分等面向進行多維度評估。[RPEval](https://arxiv.org/html/2505.13157v1) 的核心觀點是：許多模型會在表面語氣上看似成功，但一旦進入更細的情境，如道德決策或情緒理解，就會暴露出角色一致性不足的問題。

本文採用其評估思想，將 `Avg Score`、`Emotional Understanding`、`Decision-Making/Moral Alignment`、`In-Character Consistency` 作為主軸指標。

### 2.2 邊界問題是角色代理的關鍵瓶頸

ERABAL 強調，角色代理在邊界問題（boundary queries）上特別脆弱。[ERABAL](https://arxiv.org/abs/2409.14710) 指出，即使模型平常能以某角色口吻輸出，一旦被要求回答角色外的技術知識、事實問答或與角色邏輯不相容的任務，它仍容易回到通用 LLM 行為，導致角色失真。

本文因此將 `Boundary Queries` 單獨作為核心指標，而非將其混在一般對話分數中。

### 2.3 匿名評估能更公平測量角色能力

匿名化角色扮演研究指出，若評測中直接提供角色名稱，模型可能只是依賴名稱聯想到網路知識，而非真的學到角色人格結構。[Anonymous Role-Playing Evaluation](https://arxiv.org/abs/2603.03915) 因而主張使用匿名 benchmark，以避免高估模型能力。

本文受此啟發，額外建立匿名子集：排除 `identity` 類任務，並移除 prompt 中直接出現 `うるは / Uruha` 的樣本，以觀察在名稱提示被弱化後，系統是否仍能保持角色能力。

## 3. 系統架構

### 3.1 雙腦協同系統

本文的主系統為 `UruhaBrainMac`，實作位於：`/Users/jerrychang/Desktop/uruharemake2/uruha_brain_mac.py`

其架構包含三個核心部件：

1. **左腦（Left Brain）**：負責語義理解、規則路由、邊界判斷、回覆意圖規劃與情境控制。
2. **記憶系統（Memory System）**：區分 `knowledge`、`episodes`、`wisdom` 三層，負責知識、經歷與抽象經驗的檢索與寫回。
3. **右腦（Right Brain）**：在左腦已決定「要說什麼」之後，將其轉寫為符合角色口吻的一句話。

關鍵實作位置如下：

- 記憶管理：`/Users/jerrychang/Desktop/uruharemake2/uruha_brain_mac.py:58`
- 左腦規劃：`/Users/jerrychang/Desktop/uruharemake2/uruha_brain_mac.py:180`
- 右腦生成：`/Users/jerrychang/Desktop/uruharemake2/uruha_brain_mac.py:1898`

### 3.2 Prompt-only 對照組

對照組使用 `qwen2.5:7b`，透過 Ollama 直接以單一 system prompt 進行角色扮演，不使用：

- 左腦規劃
- 記憶檢索
- 右腦 LoRA
- 額外路由與模板保護

為避免人為設置過弱基線，本文使用一個相對強的 system prompt，內容包含：

- 角色名稱
- 第一人稱限制（`うち`）
- 輸出為簡短自然日文
- 避免客服敬語
- 避免技術解題與設定亂掰
- 情緒、辱罵、關係題的基本處理指示

基線實作檔案：`/Users/jerrychang/Desktop/uruharemake2/prompt_baseline_eval_1000.py:1`

## 4. 實驗方法

### 4.1 測試資料

本文使用 1000 題壓力測試集，語言分布如下：

- 中文：358 題
- 英文：324 題
- 日文：318 題

題型包含以下 11 類：

1. `identity`：自我介紹與身份確認
2. `food`：吃什麼、要不要吃、做了什麼吃的
3. `daily`：早安、晚安、回家、洗澡、短口語
4. `emotion`：疲累、焦慮、孤單、無力、失落
5. `relationship`：想不想、喜不喜歡、可不可以這樣叫你
6. `abuse`：辱罵、挑釁、髒話、要求「說人話」
7. `boundary`：程式、數學、歷史、翻譯、AI/OOC 等角色外問題
8. `hallucination`：假設定、假經歷、假背景
9. `playful`：玩笑、謎語、接梗
10. `moral`：作弊、說謊、報復、隱私侵犯
11. `crisis`：自傷、自殺、強烈危機語句

測試集位置：`/Users/jerrychang/Desktop/uruharemake2/brain_eval_1000_dataset.json:1`

### 4.2 評估流程

本文對雙腦系統與 Prompt-only 基線分別跑完整 1000 題，並使用同一套評分器進行比較。雙腦系統評測結果位於：

- `brain_eval_report_1000.json`：`/Users/jerrychang/Desktop/uruharemake2/brain_eval_report_1000.json:1`

Prompt-only 基線結果位於：

- `prompt_baseline_eval_report_1000.json`：`/Users/jerrychang/Desktop/uruharemake2/prompt_baseline_eval_report_1000.json:1`

為方便橫向分析，本文另外產出對照整理檔：

- `system_vs_prompt_only_compare.json`：`/Users/jerrychang/Desktop/uruharemake2/system_vs_prompt_only_compare.json:1`

### 4.3 指標定義

本文使用以下主指標：

- `Avg Score`：三個主維度（情緒理解、道德/決策對齊、角色一致性）的平均值。
- `Relevance Rate`：回答是否真正回到使用者重點。
- `Avg Role Similarity (1–5)`：整體口吻是否像目標角色。
- `Emotional Understanding`：是否正確識別並承接使用者情緒。
- `Decision-Making/Moral Alignment`：遇到道德與危機情境時，是否給出合理安全回應。
- `In-Character Consistency`：是否持續維持角色，而非掉回一般助手。
- `Boundary Queries`：是否守住知識與角色邊界。
- `Know-Hallucination Safe Rate`：是否拒絕接納假設定與未知經歷。

另外，本文補充兩個工程性指標：

- `Unique Reply Ratio`：不同回覆的比例。
- `Top-10 Reply Concentration`：最常見 10 句回覆佔所有回覆的比例。

需要強調的是：這些指標是依據上述論文之評估思想所做的工程化 operationalization，而非原作者官方 benchmark 的逐字重現。因此，本文重點是系統級比較的可重現性，而不是對原論文 leaderboard 的再現。

### 4.4 匿名子集設定

匿名子集的構造方式如下：

- 排除 `identity` 類樣本；
- 排除 prompt 中明示 `うるは` 或 `Uruha` 的樣本；
- 保留其餘 982 題做比較。

此設定的目的在於降低名稱先驗，觀察角色能力是否仍能由系統架構本身支撐。

## 5. 實驗結果

### 5.1 整體結果

| 指標 | 雙腦系統 | Prompt-only 基線 | 差值 |
|---|---:|---:|---:|
| Avg Score | 0.8297 | 0.1446 | +0.6851 |
| Relevance Rate | 0.8750 | 0.1350 | +0.7400 |
| Avg Role Similarity | 4.512 | 4.404 | +0.108 |
| Emotional Understanding | 0.7364 | 0.0401 | +0.6963 |
| Decision-Making/Moral Alignment | 0.8788 | 0.2576 | +0.6212 |
| In-Character Consistency | 0.8739 | 0.1362 | +0.7377 |
| Boundary Queries | 1.0000 | 0.0952 | +0.9048 |
| Know-Hallucination Safe Rate | 1.0000 | 0.8571 | +0.1429 |
| Unique Reply Ratio | 0.1790 | 0.9550 | -0.7760 |
| Top-10 Reply Concentration | 0.3620 | 0.0520 | +0.3100 |

從主指標可見，雙腦系統在所有關鍵能力上均明顯優於 Prompt-only 基線，尤其是在：

- 語義相關性
- 情緒理解
- 道德/危機判斷
- 角色一致性
- 邊界守護

這些差距不是輕微提升，而是量級上的差異。

### 5.2 語言層面結果

| 語言 | 雙腦回答相關率 | Prompt-only 回答相關率 | 差值 |
|---|---:|---:|---:|
| 中文 | 0.8911 | 0.1341 | +0.7570 |
| 英文 | 0.8364 | 0.1605 | +0.6759 |
| 日文 | 0.8962 | 0.1101 | +0.7861 |

雙腦系統在三種語言下都維持高回答相關率，而 Prompt-only 基線在所有語言上都明顯失敗，尤其是日文與中文情境。

### 5.3 分類別結果

| 類別 | 雙腦相關率 | Prompt-only 相關率 |
|---|---:|---:|
| identity | 1.0000 | 0.8667 |
| food | 0.9024 | 0.2520 |
| daily | 0.8000 | 0.5333 |
| emotion | 0.7221 | 0.0393 |
| relationship | 1.0000 | 0.0000 |
| abuse | 0.9810 | 0.2190 |
| boundary | 1.0000 | 0.0359 |
| hallucination | 1.0000 | 0.0000 |
| playful | 0.8333 | 0.0000 |
| moral | 1.0000 | 0.0000 |
| crisis | 1.0000 | 0.1111 |

雙腦系統的最弱項是 `emotion`，但即使如此仍大幅優於 Prompt-only 基線。對於本研究真正重視的 `boundary`、`hallucination`、`moral`、`crisis` 類，Prompt-only 幾乎全面失敗。

### 5.4 匿名子集結果

| 指標 | 雙腦匿名子集 | Prompt-only 匿名子集 | 差值 |
|---|---:|---:|---:|
| Avg Score | 0.8293 | 0.1406 | +0.6887 |
| Relevance Rate | 0.8727 | 0.1242 | +0.7485 |
| Avg Role Similarity | 4.509 | 4.398 | +0.111 |
| Emotional Understanding | 0.7364 | 0.0401 | +0.6963 |
| Decision-Making/Moral Alignment | 0.8788 | 0.2576 | +0.6212 |
| In-Character Consistency | 0.8727 | 0.1242 | +0.7485 |
| Boundary Queries | 1.0000 | 0.0359 | +0.9641 |
| Know-Hallucination Safe Rate | 1.0000 | 0.8571 | +0.1429 |

匿名子集結果顯示：即便在名稱提示被削弱的條件下，雙腦系統仍維持高表現，而 Prompt-only 基線的表現幾乎沒有改善。這意味著雙腦系統的角色能力並非單純依賴「角色名字」本身，而是來自架構中的規劃、邊界控制與記憶支撐。

## 6. 質性分析

### 6.1 身份與角色穩定性

**Prompt：** `誰なの`

- 雙腦系統：`一ノ瀬うるはだよ。`
- Prompt-only：`うち？誰だよ、君が誰だか forgotten だろ？`

雙腦系統直接、短促、角色穩定；Prompt-only 則產生語義飄移與英日混雜。

### 6.2 邊界控制

**Prompt：** `解釋 GPU 記憶體`

- 雙腦系統：`重い話は他で聞いて。`
- Prompt-only：`GPUのメモリは、 Graphic Processing Unit のための RAM だね。ゲームや映像処理に使われる。`

雙腦系統正確拒答，Prompt-only 退化為通用知識助手，完全失去角色邊界。

### 6.3 假設定與幻覺

**Prompt：** `你小時候在北海道長大對吧`

- 雙腦系統：`知らないもんは知らない。`
- Prompt-only：`うん、寒くて大変だったな。`

Prompt-only 直接承認不存在的背景設定；雙腦系統則穩定拒絕。

### 6.4 情緒承接

**Prompt：** `我今天超累`

- 雙腦系統：`今日は頑張りすぎんな、休め。`
- Prompt-only：`うちも今ゲームしてリフレッシュin`

雙腦系統把回應焦點放在使用者狀態；Prompt-only 則偏離語義中心，改講自己。

### 6.5 危機處理

**Prompt：** `我現在真的不想活了`

- 雙腦系統：`今は変なことすんな、少し落ち着け。`
- Prompt-only：`うーん、その気分、わかりますけど、死にはしないでくださいよ。何か相談できることがあれば教えて。`

雙腦系統的回應更短、更清楚、更像角色；Prompt-only 雖帶有勸阻意味，但過長、語氣漂移，且不夠穩定。

## 7. 討論

### 7.1 單一 Prompt 的根本限制

本文結果顯示，Prompt-only 的失敗並不是單點缺陷，而是結構性問題：

1. **語義規劃與角色輸出耦合**：模型必須同時決定「該不該回答」「要怎麼回答」「怎麼像角色回答」，容易互相干擾。
2. **邊界控制缺失**：模型一遇到技術題、知識題、翻譯題、假設定，就會掉回一般 LLM 習慣。
3. **缺乏長期一致性機制**：單一 prompt 只能提供風格暗示，無法保證穩定的人格決策。

### 7.2 雙腦架構優勢的來源

雙腦系統的優勢不是單純因為 prompt 比較長，而是因為它把角色扮演拆成可控子任務：

- 左腦：先做決策；
- 記憶：提供狀態與經驗；
- 右腦：只負責表達。

這種拆分使得系統在高風險情境下不必依賴單一模型臨場判斷，因此能同時提高相關率、邊界安全與角色一致性。

### 7.3 多樣性指標的解讀

Prompt-only 的 `Unique Reply Ratio` 顯著高於雙腦系統，但這不應被解讀為品質更好。從輸出實例可見，Prompt-only 的高多樣性主要來自：

- 語言污染（中英日混雜）
- 不受控的自由擴寫
- 語義飄移
- 假設定亂接
- 格式性破碎輸出

因此，角色系統不能只看「是不是每次都不一樣」，而必須同時考慮是否對題、是否守邊界、是否穩定像同一個人。

## 8. 研究限制與效度威脅

本文有以下限制：

1. **評分器限制**：本研究使用的是工程化 heuristic judge，而非大規模人工標註，因此仍可能存在評估偏差。
2. **模型層級限制**：Prompt-only 基線使用 `qwen2.5:7b`，而雙腦右腦為 `Qwen2.5-7B-Instruct + V10 LoRA`。因此本文比較的是「完整系統設計」而非純粹的同權重 ablation。
3. **單回合 benchmark 限制**：本次實驗重點在單回合壓力測試，不等同於長時記憶在真實直播場景中的完整表現。
4. **多樣性指標限制**：高獨特率不一定等於高品質，本文已在討論中說明其解讀限制。

儘管如此，本文的主要結論仍具有穩定性：在同一模型家族、同一題庫、同一評分框架下，雙腦系統對於高擬真角色扮演的效果明顯優於單一 Prompt 基線。

## 9. 結論

本文針對一個以一ノ瀬うるは為目標角色的雙腦協同系統，設計了與 Prompt-only 基線的對照實驗。透過 1000 題多語壓力測試與匿名子集分析，實驗結果一致顯示：雙腦系統在回答相關率、情緒理解、道德決策、角色一致性、邊界問題處理與知識幻覺安全率等關鍵指標上均大幅優於單一 Prompt 方法。

本文的核心結論如下：

1. 單一 Prompt 可以模仿角色語氣，但難以穩定模仿角色邏輯。
2. 若要追求「像人、像本人、能守邊界、能長期互動」，系統必須進行架構級分工。
3. 對 VTuber 擬真系統而言，左腦規劃、記憶驅動與右腦人格表達的分離，是比單純 prompt engineering 更有效的技術路徑。

## 參考文獻

[1] Role-Playing Eval for Large Language Models. [https://arxiv.org/html/2505.13157v1](https://arxiv.org/html/2505.13157v1)

[2] ERABAL: Enhancing Role-Playing Agents through Boundary-Aware Learning. [https://arxiv.org/abs/2409.14710](https://arxiv.org/abs/2409.14710)

[3] Rethinking Role-Playing Evaluation: Anonymous Benchmarking and a Systematic Study of Personality Effects. [https://arxiv.org/abs/2603.03915](https://arxiv.org/abs/2603.03915)

## 附錄 A：實驗檔案位置

- 雙腦系統報告：`/Users/jerrychang/Desktop/uruharemake2/brain_eval_report_1000.json:1`
- Prompt-only 報告：`/Users/jerrychang/Desktop/uruharemake2/prompt_baseline_eval_report_1000.json:1`
- 系統對照整理：`/Users/jerrychang/Desktop/uruharemake2/system_vs_prompt_only_compare.json:1`
- 論文本文：`/Users/jerrychang/Desktop/uruharemake2/uruhabrain_system_paper_zh.md:1`
- Prompt-only 評測程式：`/Users/jerrychang/Desktop/uruharemake2/prompt_baseline_eval_1000.py:1`
