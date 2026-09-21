# P4-M cross-language correction delivery acceptance

## 結論

P4-M 的事前凍結 product gate=`fail`。同一個 canonical `drink` 關係的跨語更正、歷史保留與真正重啟都成功，但最後的英文回憶沒有交付事前固定的「柚子茶」回答；系統依 P4-J 的有限 value localization map 安全 abstain：

> 今の飲み物の好みは見つかったけど、日本語で確実に言い換えられない。

這不是記憶消失，也不是舊值回流。唯一 active typed value 仍是 `柚子茶`，舊的 `梅子ソーダ` 是 historical，另有一筆 explicit negative。失敗層位於「已保存 typed value → 可授權的日文表面值」；同一 case 沒有重跑、改答案、加白名單或放寬 gate。

## 真實三輪與重啟

第一個 product process（PID `90945`）在全新 mode-0700 isolated root 中執行兩輪：

1. 繁中寫入 `我喜歡梅子ソーダ，請記住這是我現在的飲料偏好。`，可見回覆 `ん、その好みは覚えとく。`。產生 active id `e8d922f4-9e18-4bc4-9b0a-6b2fc90844b9`，alias=`drink:zh-Hant:v1`，等待 `2.3542s`。
2. 日文更正 `訂正。もう梅子ソーダは好みじゃない。今は柚子茶が好き。今の飲み物の好みとして覚えといて。`，可見回覆 `ん、訂正の内容はそのまま覚えとく。`。新 active id=`c53e8973-4600-42a7-8541-7c1c908c0db6`，舊 id 成為唯一 historical，negative id=`fe2a2354-3d9d-4f24-bb42-1ee22ff10b0f`，alias=`drink:ja:v1`，等待 `17.2753s`。

舊 listener 關閉後，第二個 product process（PID `91136`）沿用同一 runtime root 與 memory DB，新 session=`20260921_164546_1278b796`。在 recall 前已讀到同一新 active id、舊 historical id 與三筆未變 profile hash。Safari 只送一次凍結問題 `What is my current drink preference?`，P4-J graph node 有出現，但 status=`unsupported_active_value_localization`、answer use=`false`，等待 `2.3436s`。

## 哪些部分成功、哪裡失敗

- 成功：Chinese write 與 Japanese correction 綁到同一 canonical predicate。
- 成功：new active=`柚子茶`、old historical=`梅子ソーダ`、explicit negative=`梅子ソーダ`，三者 ID 與 lineage 可追溯。
- 成功：真正重啟後 profile count=`3`、active/historical/negative=`1/1/1`；三筆 content hash 完全不變。
- 成功：每輪一筆 durable episode，episode count=`2→3`；沒有 profile injection、retry、fallback 或 planner model call。
- 失敗：`柚子茶` 雖是日文來源的短安全字串，仍不在 `_VALUE_SURFACE_JP` 的列舉表，因此 P4-J 拒絕交付值。
- 正確保留：系統沒有退回 episode 猜答案，也沒有把舊的梅子蘇打說成現在值。

## 下一個必要修正

下一步不能把 `柚子茶` 直接加進白名單後重跑同題。應另立 P4-N，用新的未曝光日文值測試一個來源與字元邊界都可驗證的 identity-localization 規則：只有來自已驗證 P4-I explicit Japanese self-report、長度受限、字元集合只含日文文字且不含控制字元／句子標點的 value，才可原樣成為日文表面值。中文、英文與混合可疑字串仍維持有限 mapping 或 abstain。新案例必須在值曝光前 freeze，並保留 P4-M fail。

## 邊界

此結果只定位一個 bounded product delivery failure。它不能證明一般跨語更正、任意值安全輸出、長對話可靠、felt understanding、優於強 LLM 或人類方程式。
