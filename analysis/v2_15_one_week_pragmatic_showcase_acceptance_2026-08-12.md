# V2.15 一週研究展示里程碑驗收

日期：2026-08-12  
狀態：本機展示里程碑完成；研究優越性尚未完成人類盲評  
里程碑名稱：Human Pragmatic Understanding Observatory

## 1. 一週小目標

讓第一次看到 UruhaBrain 的老師在三分鐘內看懂一個可反駁的研究差異：

- 一般 baseline：同一個基礎模型根據目前對話直接生成回答。
- UruhaBrain：把「字面訊號 → 暫定語用理解 → 證據與替代假設 → 下一輪預測 → 後續支持／否定 → 撤回與校正 → 人格化日文回覆」做成可追溯的跨輪機制。
- 研究主體是人類語用理解與預測；Uruha 是公開證據約束的實驗人格，不是真人、意識或讀心宣稱。

這個里程碑不是再做一張架構圖，而是把 frozen fresh-generation 結果、可重播的認知狀態與研究邊界放進同一個可操作網站。

## 2. 已完成的展示

入口：Web UI 第一個頁籤 `Research Demo`。

三個可逐輪切換的故事：

1. 猜錯後修正：曖昧的高喚起訊號先保留正負兩種可能；使用者否定焦慮後，系統明說「読み違えた」，撤回舊理解；第三輪使用更新後的目標互動。
2. 字面與真正需求不同：從「改天」形成可否定的婉拒假設，後續得到確認，再把回覆目標改成協助低摩擦拒絕。
3. 跨語言偏好撤回：英文輸入先形成穩定偏好，使用者撤回後 active 由 1 變 0、withdrawn 由 0 變 1，原紀錄保留但不再當成目前喜好。

每一步同時顯示：

- 同模型 baseline 與 UruhaBrain 的實際 frozen 回覆。
- Observation、Literal、Pragmatic Hypothesis、Prediction、Later Outcome 節點。
- Evidence、Alternatives/Unknown、Relationship/Need 分支。
- persistent other-model 的 stable、situational、provisional、withdrawn、expired 狀態。
- correction → public-persona appraisal → action/surface。
- 54 組完整比較結果、token fairness gate 與證據邊界。

展示器只讀 frozen 證據，沒有模型呼叫、沒有正式記憶寫入，也不會把示範對話混進正式 DB。

## 3. 三分鐘老師展示腳本

### 0:00–0:25：一句話說研究問題

「我不是只讓模型回得像 Uruha。我在研究的是，人講話時字面和真正需求不同，系統能不能提出可驗證的暫定理解，並在猜錯後真的改掉，而不是把錯藏起來。」

### 0:25–1:25：跑案例 A 的三步

- 第一步：使用者只說坐不住，系統不把它直接判成焦慮，而是短問「楽しみな方か不安な方か」。
- 第二步：使用者說不是緊張。按下一步後指出 Outcome 為否定、withdrawn 增加，以及日文回覆「そっちだな、読み違えた」。
- 第三步：展示修正後的互動目標已改成一起分享興奮，而不是繼續安撫。

### 1:25–2:10：切到案例 C

先看英文偏好進入 stable，再切第二步；指出 stable active 變 0、withdrawn 變 1。重點不是「有記憶」，而是「舊記憶遇到矛盾後會被撤銷且留下歷史」。

### 2:10–3:00：看完整比較與限制

- 可見日文／人格自動契約：baseline 9/54，system 42/54。
- 語義 anchor proxy：baseline 6/54，system 30/54。
- token parity：54/54 通過，所有配對 prompt-eval token 差值為 1，gate 上限為 2。
- 主動指出：這是機制與 proxy 證據，不是人類偏好勝出的證明；至少三位獨立盲評仍待完成。

## 4. Safari 真實驗收

在使用者外部 Safari 實際完成以下操作：

- 新增一個本機頁籤並開啟 `http://127.0.0.1:7863`；其餘既有頁籤未修改或關閉。
- 確認 `Research Demo` 是第一個且預設選取的頁籤。
- 點擊「下一個證據步驟」，確認案例 A 由 TURN 1 更新為 TURN 2。
- 確認 TURN 2 的可見 system 回覆含「読み違えた」，圖上 Outcome 顯示否定並保留 revision。
- 實際捲動檢查認知節點、persistent other-model、比較長條與 evidence boundary。
- 切換案例 C，確認英文輸入仍得到日文回覆，第二輪 stable active=0、withdrawn=1。

截圖證據：

- `analysis/v2_15_teacher_demo_correction_turn2_2026-08-12.png`
- `analysis/v2_15_teacher_demo_cognitive_loop_turn2_2026-08-12.png`
- `analysis/v2_15_teacher_demo_evidence_boundary_2026-08-12.png`
- `analysis/v2_15_teacher_demo_preference_withdrawal_2026-08-12.png`

Safari 驗收中發現 frozen 中文偏好案例的原始輸出保留了「抹茶拿鐵」，不符合自然日文展示品質。沒有竄改 frozen 輸出，而是把第三個展示故事換成原本就存在的英文 ginger-ale 偏好撤回案例；該案例的失敗契約仍誠實顯示為 failure。

## 5. 自動驗收證據

- 新增 V2.15 展示契約：7/7 通過。
- V2.11–V2.15 相鄰回歸：143/143 通過。
- frozen holdout：18 個三輪案例，中文／英文／日文各 6，驗證通過。
- frozen binding：6/6 SHA-256 一致。
- fresh result：108 outputs、54 paired turns、0 transport errors。
- raw result SHA-256：`9005d3495d90e4500409bb1304cc5b68ab62edc134e6b200ecb0fb91a7ed3c22`。
- `git diff --check`：通過。
- Python compile：通過。
- 正式記憶 DB aggregate hash 驗收前後相同：`c56a8201731a004c8c031d01908e8c6ebd7c7b3aafdd295dc6d898873d859da6`。
- 隔離展示目錄沒有產生任何 DB 或對話 log 檔案；production memory writes = 0。

## 6. 資源量

本展示層重用 frozen V2.14 證據，播放時的增量成本很低：

- 模型推論：0 次；Ollama 不需要為 Research Demo 啟動。
- GPU：0（展示頁本身）。
- 正式 DB 寫入：0。
- 本機 Web Python process：驗收時約 430 MiB RSS。
- 外部服務與部署：0；只綁定 `127.0.0.1:7863`。

若重跑完整 fresh comparison，才需要本機 `qwen3.5:9b`、Ollama 與 108 次生成；這不屬於每次老師展示的成本。

## 7. 完成度與仍缺什麼

### 這個一週里程碑

完成度：100%。網站、三個故事、圖像化流程、同模型對照、研究邊界、Safari 驗收與回歸證據都已具備。

### 功能性語用理解研究原型

目前約 75–80%。已具備可觀察、可反駁、可撤銷的跨輪理解機制與 fresh paired outputs；尚缺可信的人類被理解感證據、更多 unseen holdout、較好的跨語言人格表面品質與完整 Web edge-case 收斂。

### 使用者最終理念

目前約 35–45%。距離長期、穩定、多模態、關係連續且能在真實互動中泛化的類人理解系統，仍缺：

- 至少三位獨立盲評者完成同模型 A/B 評分。
- 更大的未見語用案例與失敗分類，而非只靠 18 個 frozen case。
- 可靠語音聲學特徵；目前文字輸入只能標記 acoustic unavailable。
- 長期校準在數天／數週真實互動中的漂移、遺忘與矛盾處理。
- 即時語音、VRM 行動與認知回路的整體延遲與安全驗收。

因此目前能證明「有一個不同於直接生成、而且可檢查與修正的研究機制」；不能先說「已證明普遍比 LLM 更懂人」。
