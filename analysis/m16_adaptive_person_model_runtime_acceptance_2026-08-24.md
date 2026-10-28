# M16 Adaptive Person Model Runtime 驗收報告

日期：2026-08-24  
定位：開發／研發里程碑；研究只用來驗證機制是否真的改變產品行為。這不是論文結論，也不是意識、讀心或真人等價證據。

## 1. 要解決的產品問題

舊系統能在 trace 中分析「使用者可能需要什麼」，但分析不一定能改變最後說出口的話，也不會把使用者之後的否定轉成可跨重啟使用的互動經驗。

M16 的完成定義是：

1. 真實對話形成具名的 desired-response 狀態與候選策略；
2. 下一輪能把使用者反應判為支持、否定或未知；
3. 被否定時更新可撤銷的狀態原子與策略可靠度；
4. 更新後的模型必須真的改變使用者可見的日文回覆；
5. 結構化修正能跨控制式重啟保留；
6. runtime node graph 顯示狀態、候選、選擇、回饋、持久化與可見輸出承諾；
7. 不把原始私密對話存進 adaptive model，也不覆蓋危機、安全、事實回憶與日文輸出 guard。

以上七項均已在本次 bounded milestone 內完成。

## 2. 實際接入的資料流

```text
當輪文字與可用證據
  → named state atoms（需求、睡眠、身體負荷、玩笑邀請、關係熟悉度、不確定性…）
  → 六種可干預 response policies
  → desired-response utility + Uruha public-persona fit + evidence − risk
  → 選出的 plan 寫回真實回覆規劃
  → 使用者可見日文
  → 下一輪 support / contradict / uncertain
  → atoms + policy reliability 更新
  → 只持久化摘要化參數與 evidence digest
  → 後續相似情境重新使用
```

六種策略是 `care_physiology`、`solve_regulation`、`listen_presence`、`share_arousal`、`playful_tease`、`calibrate_need`。它們是目前可測試的有限策略集合，不代表所有人類期待已被窮舉。

## 3. Safari 隔離三輪實測

隔離條件：新的暫存 session、暫存 episodic DB、暫存 adaptive model；沒有寫入正式長期資料。外部瀏覽器為 Safari，本機頁面為 `http://127.0.0.1:7866`。

### 第 1 輪：未知時先確認

- 輸入：`我坐不住，腦子停不下來。`
- 選擇：`calibrate_need`
- 可見回覆：`てか、寝てないのか、考え事で止まんないのか、まずそこだけどっち？`
- 意義：系統沒有把「坐不住」直接固定成焦慮、求解法或求吐槽。

### 第 2 輪：使用者否定原接法

- 輸入：`不是要方法，是等你吐槽。`
- feedback：前一策略 `contradicted`
- 新選擇：`playful_tease`
- 可見回覆：`あ、そっちか。さっきは読みすぎた。今の言い方で直す。 朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。`
- 寫入的結構化修正：提高 `humor_invitation` 與 `relationship_familiarity`，降低 `solution_request`；不保存原句。

### 控制式重新啟動後，第 3 輪：修正被真正重用

- 再次輸入：`我坐不住，腦子停不下來。`
- 選擇：`playful_tease`
- 可見回覆：`てか、朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。`
- graph：顯示三個 learned atoms 被使用、`calibrate_need` 的 contradiction 歷史、`playful_tease` 成為當輪選擇、persistence revision=1、surface commitment 可見。

這個結果證明的不是「系統讀到內心」，而是：相同表面輸入在使用者明確修正前後，會因可追溯的個人化狀態改變而產生不同的真實輸出，而且修正跨重啟存在。

## 4. 實測時發現並修掉的兩個真問題

1. **trace 選對、嘴巴沒說出來**：早期實測已選 `playful_tease`，但可見回覆只剩「我理解錯了」。新增 final surface commitment guard，確保選定行為至少一次出現在可見回答。
2. **否定句被當正向證據**：`不是要吐槽，是真的想要方法` 曾錯被判為 humor support。現在否定玩笑的 pattern 優先，並寫入低 `humor_invitation`；已加入回歸測試。

## 5. 驗證證據

### 單元／契約與整合回歸

最終 scoped regression：`141/141` 通過，包含 adaptive model 8 個專屬測試、三輪 real-runtime integration、日文可見輸出、人格／self identity、記憶、主動閒置 guard、route 與 node graph 契約。Python compile 與 `git diff --check` 同時通過。

### 持久化與隱私邊界

- schema：`uruha_adaptive_person_model_m16`
- `revision_count=1`
- `raw_dialogue_persisted=false`
- 持久化資料只含具名 atoms、confidence、來源類型、digest、策略計數與 pending prediction；對四段實測原文的檔案掃描為 0 命中。

### 真實 Web／Safari 證據

- [持久修正後的實際日文回覆](m16_safari_persistent_reuse_2026-08-24.png)
- [當輪 runtime node graph 與比較卡](m16_safari_runtime_graph_2026-08-24.png)

## 6. 已完成與尚未完成

已完成的是一個真正在產品 runtime 中運作的「猜測—被修正—保存—重用」最小閉環；它不再只是 replay、分數或靜態圖表。

仍未完成：

- atoms 與策略集合目前偏窄，主要針對這類語用接法；尚未證明可泛化到所有自由對話。
- 學到的互動偏好目前偏全域，尚缺「情境／主題／關係範圍」隔離，可能把某次邀請玩笑過度套到別的情境。
- 第一次本機模型回覆約需 65–85 秒，互動延遲仍不適合流暢產品體驗。
- 尚未有大量真實使用者盲評，所以不能宣稱比一般 LLM 更有被理解感。
- 這不是生物人腦方程式、主觀意識、真正讀心或一ノ瀬うるは本人。

## 7. 下一個開發里程碑

**M17 Context-Scoped Adaptation + Latency Budget**：先讓每個 learned atom 有適用情境、關係與衰減範圍，避免一次修正污染不相干場景；再量測並合併不必要的模型呼叫，把一般文字回合的目標延遲降到可對話範圍。研究驗證只保留跨情境污染回歸、重啟重用、日文／安全 guard 與延遲數據。
