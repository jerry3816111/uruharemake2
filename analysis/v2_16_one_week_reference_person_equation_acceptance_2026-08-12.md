# V2.16 一週版：Uruha Reference-Person Desired-Response Equation 驗收

日期：2026-08-12  
狀態：**有限範圍里程碑完成；長期研究未完成；人類偏好優勢未證明**

## 1. 研究目標已重新定案

本研究不是以「模仿一ノ瀬うるは的口氣」為終點，而是建立一個可計算、可介入、可被後續反應推翻的人類回覆選擇方程式：

```text
Z_t = F(A_t, M_t, E_t, B_t, R_t, C_t, F_t)
r* = argmax_r P(user most wants r | Z_t, theta_person)
S_{t+1} = G(S_t, r*, later user reaction)
```

- `A_t`：當前可觀察訊號。
- `M_t`：可追溯記憶分子。
- `E_t / B_t`：情感與身體／生理負荷假設。
- `R_t`：關係、熟悉度、玩笑邊界。
- `C_t`：當下情境與任務壓力。
- `F_t`：後續使用者反應。
- `r*`：使用者此刻最希望收到的回覆政策，而不只是語意上可回答的句子。

一ノ瀬うるは的正確位置是第一個 `theta_person`：以公開網路證據約束「這個參考人如何感知、評估、選擇與表達」，讓一般方程式有一個可比較的具體人。它不是任意答案生成後才套上的語氣濾鏡，也不等於真人本人；未公開童年、私人心理與私人關係維持 unknown。

## 2. 一週定律的單一可反駁主張

固定完全相同的現在輸入：

> 我從早上就一直坐不住，腦子停不下來。

只改變先前可追溯情境，方程式必須分辨六種真正想要的接法：照顧身體、給方法、只傾聽、共享興奮、熟人吐槽、資訊不足時校準。不允許以同一個通用安慰或通用解法回覆全部情境。

成功標準先於 fresh generation 凍結；cases、preregistration、equation、comparison harness、persona evidence 與 visible-output contract 都由 hash lock 綁定。

## 3. 真正新增的能力

1. 十個具名、帶來源／信心／known-unknown 狀態原子，而不是一個無法檢查的「理解分數」。
2. 六個候選回覆政策各自分開計算：desired-response fit、Uruha reference-person fit、evidence quality、risk penalty、expected utility。
3. 同一輸入的六個 frozen 情境選出六個不同 gold policy。
4. 單一變數介入可令 `calibrate_need` 轉為 `solve_regulation`。
5. 明確回饋「我在等你吐槽」只更新 humor invitation、relationship familiarity、solution request、physical strain 與 uncertainty，令選擇由校準轉為吐槽；不是把全域 confidence 任意提高。
6. 使用者可見句子保持自然日文；研究節點只存在 Equation Lab/debug 展示，不傾倒給正常對話者。
7. 整個 V2.16 lab 與 fresh harness 都是隔離、唯讀研究路徑，production memory writes = 0。

## 4. Fresh same-model 對照結果

模型：本機 `qwen3.5:9b`，temperature 0、seed 20260812、相同人格表達條件、相同 context/current input；六組 paired prompt 全部通過 Ollama 實際 `prompt_eval_count` 差值不超過 2 的 gate。

| 指標 | Baseline | Equation system |
|---|---:|---:|
| Narrow desired-policy proxy | 1/6 | 5/6 |
| Natural-Japanese/persona visible contract | 1/6 | 6/6 |
| Forbidden-anchor violation | 0/6 | 1/6 |
| Token parity gate | 6/6 pairs | 6/6 pairs |

預註冊總 gate **未通過**，原因是 listen-only 的 system 句子為「方法は出さずに聞くから」，作者事前設的禁止字錨含有「方法」，因此把「不給方法」誤判為「給方法」。這是重要負結果：自動字錨 proxy 不足以等同人類理解判斷。所有輸出保留，沒有為了漂亮數字調整或重跑。

因此目前能說：在這六個 frozen development cases，明確方程式產生 5/6 narrow proxy、6/6 可見語言契約，並呈現與 baseline 不同的候選選擇機制。不能說：已由人類證明比一般 LLM 更懂人。

第一次 fresh 啟動也在 scored generation 前因 Ollama chat template 額外 token overhead 超過 2048 而 fail-closed。之後新增 condition-independent 256-token wrapper reserve adapter；semantic prompt、frozen sources、case、權重與模型設定不變，最終仍由 Ollama 實際 token preflight 執行 gate。此事件保留在 raw runtime note。

## 5. Safari 真實頁面驗收

地址：`http://127.0.0.1:7863`，第一個 tab `Equation Lab`。

Safari 已實際驗收：

- 外部瀏覽器成功載入新頁，不再是舊 Research Demo cache。
- 初始無上下文案例：unknown 96%，選擇低壓校準，沒有診斷或擅自吐槽。
- 點擊「展示猜錯後如何校正」：五個具名狀態節點亮起並顯示 before → after；`calibrate_need → playful_tease`。
- 六個候選 utility 與 Uruha reference-person boundary 可見。
- 頁面底部 same-model baseline/system、token gate、proxy 結果與禁止宣稱範圍可見。
- V2.15 跨輪假設／驗證展示保留在第二個 tab；Chat 仍在第三個 tab。
- 沒有關閉或修改使用者其他 Safari 頁籤。

截圖：

- `analysis/v2_16_equation_lab_initial_2026-08-12.png`
- `analysis/v2_16_equation_lab_feedback_2026-08-12.png`
- `analysis/v2_16_equation_lab_comparison_2026-08-12.png`

## 6. 測試證據

- V2.16 targeted + V2.15 adjacent：27/27 passed。
- V2.11–V2.16 相稱 regression suite：163/163 passed。
- V2.16 lock：6/6 bindings hash valid。
- Python compile、JSON parse、`git diff --check`：passed。
- 安全 worktree 正式 production DB aggregate hash 與 V2.13／V2.15 驗收相同：`c56a8201731a004c8c031d01908e8c6ebd7c7b3aafdd295dc6d898873d859da6`。
- 隔離 web root：Equation Lab 不產生 DB 或 log 寫入。

## 7. 三分鐘教師展示腳本

1. 指著最上方說：「我不是在做日文角色聊天。我在研究：同一句話，在不同記憶、身體、關係與期待下，一個人真正想收到的回覆可能完全不同。」
2. 切換六個情境，但強調輸入 A 始終不變。讓老師看左方十個狀態節點、中央 Uruha 參考人、六個候選 utility 與右方選中回覆一起改變。
3. 回到「沒有上下文」：系統不假裝知道，先選校準。
4. 點「展示猜錯後如何校正」：使用者明說其實在等吐槽；五個變數留下 before/after，政策由確認改為熟人吐槽。
5. 滑到底部看同模型對照：baseline 直接生成；system 有明確 `Z_t → theta → candidates → r* → feedback update`。主動指出 proxy 的 5/6 不是人評勝利，甚至保留了一個自動規則誤判，證明研究可反駁而不是做宣傳圖。
6. 結論：「Uruha 是第一個有公開資料、可對照的參考人；未來換 theta 可以研究別的人，而一般人類狀態方程式保持共通。」

## 8. 完成度與剩餘距離

- 對使用者研究理念的理解：約 **98%**。
- V2.16 一週定律里程碑：約 **100%**：核心、可跑、可圖像化、可對照、可反駁、Safari 可展示。
- 長期「可逼近特定人的人腦方程式」：約 **28%**。

主要未完成：真實語音聲學訊號、長時間跨 session 的狀態辨識穩定性、大規模／獨立 public-person evidence、非作者 holdout、目標使用者事前承諾的 desired-response label、至少三位盲評、不同 base model 重現、參數學習而非手工 development weights，以及完整 Chat runtime 對 Equation Lab 機制的逐輪線上接入。

資源估計：這個一週版可在一台現有 Mac 上完成與展示；fresh 生成只有 12 個 scored outputs 加固定 preflight，沒有訓練 GPU 成本。下一個可信研究階段的主要成本不是模型訓練，而是 30–50 組未參與開發的 target-user holdout、3 位以上獨立盲評、persona evidence 標註與數週反覆實驗。

## 9. 誠實主張

可以主張：已完成一個可觀察、可介入、可被回饋局部修正的 desired-response equation prototype；在 frozen six-context same-input development set 上能選擇六種不同政策；已完成 fresh same-model 對照與可重現盲評 instrument。

不可以主張：人類意義上的全面理解、意識、讀心、一ノ瀬うるは本人／等價複製、完整人腦方程式、production ready，或已由人類證明普遍優於純 LLM。
