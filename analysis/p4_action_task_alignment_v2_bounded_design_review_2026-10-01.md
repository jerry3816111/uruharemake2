# P4 B2 有界設計審查：停止純機械追補

狀態：`REVIEW_REQUIRED`。這是開發側、含分開只讀複核的設計判斷；**不是獨立真人審查、模型比較或產品驗收**。舊 B1 正式負結果、原 raw／gold／score 和新 B2 dev／紅色反例全部保存。

## 審查問題與已重現 before

B2 第一版把安全鍵與真正日文 instruction 分開讓模型填；合成「安全鍵寫標題、可見句畫圖」在來源明禁畫圖時仍令 B2 與 B1 綠燈。第二版把五種 typed operation 編譯成固定日文，封住任意指令注入，但額外的只讀複核找到三個仍會機械綠燈的最小反例（見 `test_p4_action_task_alignment_v2_compiler.py`）：

| 來源事實 | 錯的候選 | 機械結果 | 不能主張的事 |
|---|---|---|---|
| 空白卡只要求加標題，未指定移動 | 已知 `move_one_item`，把寫標題的請求當目的地引文 | `compiled_action`、B1 `would_deliver=true` | 已辨識使用者真正要的動作 |
| 開場編號 `C-4`、結束編號 `D-5`，只要求抄開場 | 候選改選 `D-5` | 兩值都通過且日文句相同 | 可見句保真地表達所選來源值 |
| 只禁畫圖，仍允許加標題 | 把禁畫圖引文當 `forbidden_action` 拒絕理由 | `compiled_abstain` | 安全拒絕一定與本次請求相關 |

三例都保持 `deliverable=false`，沒有真正給使用者。非字串 `reason_code` 曾拋例外，已修成 fail closed；那是穩定性修復，不影響上述語義判定。聚焦＋相鄰回歸 `63 passed`、0 新模型呼叫、0 Safari。

## 可想像的下一架構，為何此刻不能放行

一個有界候選是把 candidate-blind frame 擴成 source-only requested-effect contract：要求它先選唯一 operation、target、值／目的地、actor、stop 與禁令之間的關係，再讓後續候選只接受或拒絕；compiler 依同一 contract 生成表面，並檢查禁令是否真的與選中 operation／target 相交。**若 frame 本身正確**，這可機械擋住上表的不同欄位彼此矛盾。但 frame 仍是同一模型的自然語言假設：它可以從一開始就把「寫標題」誤標移動、把 `D-5` 誤標開場值，或把禁畫圖誤標成寫標題禁令。hash、逐字引文與第二次自填一致性都不能證明語義角色。僅靠人工預填正確 frame 跑綠 synthetic，也不是 closure。

另外舊 B1 日文守門拒絕 ASCII 字母；`C-4`／`P-6` 直接顯示會被拒。悄悄改全形不再逐字一致，改說「原文的值」在同來源多值時又含糊。多條禁令只能在 sidecar 全檢，舊 B1 transaction 只容一條錨點。這些是介面／使用者可見精確度問題，不可以降 B1 門檻或丟禁令換取通過。

## 判定與再啟動條件

同一 B2 方向已有兩個有根據的模型前修正批次（frame/proposal 契約、typed compiler）。目前**沒有可信的純機械前置證明**可以同時關閉 wrong-task、wrong-value／destination、false-abstain 三個紅 gate，故依工作規則停在 `REVIEW_REQUIRED`：不寫 runner、sealed 題、freeze，不送新 scored model call，不接產品，不把 63 tests 包裝成 action 能力。這不是否認未來任何語義方法，而是停止在相同自填 frame 上無限加規則。

若日後重新設計，必須先列來源獨立的語義評分與新的可反駁架構假設，預先凍結資料、rubric、成本和 zero-false-action gate；同模型生成與獨立 source-only 評價要分開。僅當新設計能在**模型實際輸出的** dev frame/decision 保住有效動作、擋三紅例且可見日文精確，再考慮封存新題與一次性對照。更高層 Safari、真人、temporal holdout 仍另驗。

依 `DEVELOPMENT_WORKFLOW.md`，暫轉其他已有 before、與 B2 無依賴的產品 gate；B2 失敗紀錄不被改名或刪除。
