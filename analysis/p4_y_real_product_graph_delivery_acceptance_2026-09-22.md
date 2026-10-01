# P4-Y 隔離真實產品／Safari runtime graph delivery 驗收

日期：2026-09-22  
狀態：**PASS（prospectively frozen real-product + Safari）**，failed gates=`0`。

## 為什麼做這一步

P4-X 的四輪真實執行中，P4-T／P4-V／P4-W logic 都存在，但 Safari graph 三種 node 都是 0/4。P4-Y 先以合成 full-Web
integration 證明最後 refresh 後交付可行，再另凍結兩個從未使用、也不重用 P4-X 的日／英輸入，用新的 private runtime root、port
`7871` 與新的 Safari tab 做唯一一次真實驗收。

## 真實畫面結果

| 輪次 | 輸入 | 可見日文 | graph surface chain |
|---|---|---|---|
| 1 | `今日は机の左側に青いノートを置いた。` | `今日は机の左側に青いノートを置いたんだね。` | P4-T → P4-V → P4-W → utterance |
| 2 | `The calendar reminder is set for Friday afternoon.` | `カレンダーの予定は金曜日の午後にあるんだね。` | P4-T → P4-V → P4-W → utterance |

Safari accessibility tree 在兩輪後都直接列出：

1. `utterance_frame_shadow_p4`
2. `utterance_frame_coverage_extension_p4`
3. `frame_preserving_visible_repair_p4`
4. `utterance`

## 量化證據

- successful／Japanese／durable episode／graph visible=`2/2, 2/2, 2/2, 2/2`。
- P4-T／P4-V／P4-W graph trace=`2/2, 2/2, 2/2`。
- logic trace 與 graph node payload 精確相同=`6/6`；duplicate node=`0`；delivery complete=`2/2`。
- typed preference write=`0`；隔離 `user_profile` collection=`0`。
- end-to-end=`16.1522s, 11.8162s`；總和=`27.9684s`，皆在事前上限內。
- 本次 P4-Y 機制新增 model call=`0`；原產品 semantic authorization 實際完成本機模型 call=`2`，provider elapsed
  合計=`23.0926s`，token accounting unavailable，不能寫成整體零模型。
- retry／fallback／付費 API／外部部署／正式記憶存取／function tool／VRM action／關閉使用者 tab 均=`0`。
- conversation JSONL 兩列 SHA-256：`74d7454d4c9978b0b2699ba32b44b76a6cd9fcff014e2dcdc53116e0f65d39e8`。

## 可主張與不可主張

現在可以主張：在一個事前凍結、隔離的真實產品＋Safari 兩輪中，已存在的三層語境判定／修復 trace 能以 exact payload、固定順序
送到圖像化 runtime graph。這修正了 P4-X 的 0/4 graph delivery failure。

不能主張：節點內的理解一定正確、命題一定保留、repair accuracy、felt understanding、人類偏好、強 LLM 優勢或人類方程式。
P4-X 的 T1／T3／T4 語意反例仍有效，不能被這個 PASS 掩蓋。下一步 P4-Z 必須另用全新 holdout，單獨處理 source-bound
proposition preservation 與 hypothetical ownership。

伺服器與新 Safari result tab 保留，未關閉任何舊 tab，供使用者直接查看。
