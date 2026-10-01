# P3-C1 controlled context-flip lane acceptance

日期：2026-09-20

## 結果

P3-C1 離線契約與資料 freeze 完成。這不是模型效果 pass，而是後續正負結果都不容易被事後修改的前置條件已成立。

- 18 個 surface families、36 個 variants；train/dev/holdout 各 6 families；中文、英文、日文各 6 families。
- 每個 family 的 `literal_control` 與 `pragmatic_flip` 使用完全相同的 surface utterance，完整 family 不跨 split。
- prediction packet 只含可觀察 context、surface、options、evidence anchors；不含 expected distribution 或 top-1 target。
- 所有項目固定 text-only；acoustic status=`unavailable`，禁止用不存在的語速、停頓、音量或韻律作證據。
- baseline 是取得完整 context、可正常推理的同模型 direct baseline，不是先前 B65 的 literal-restricted condition。
- system 唯一介入是顯式可反駁 pragmatic state；同一 item 仍只有一次 call、同 384 completion ceiling，額外 state token 不免費。
- primary、SESOI、overinterpretation guard、paired-flip guard 與所有 secondary metrics 已在 model output 前固定。

## 驗證證據

- C1 focused：`11 passed in 0.14s`。
- B65/B70/B73/C1 adjacent：`43 passed in 0.48s`。
- synthetic metric fixture 可辨認兩種方向：target-aligned system 通過；system 對所有題都選 pragmatic 時，雖能選中 pragmatic side，
  literal-control overinterpretation=`1.0` 並 fail 整體 gate。
- implementation freeze hash：`334b6a9587d228156a3fbc16a083cf5e19ed05adc80380e286dd9b4f98e31703`。
- P3-C1 model/network/Uruha source/future/human label/production/formal write 全部為 0。

## 實際改善

先前 B72 的量尺只看到未對齊字幕與標點 marker，無法回答「同一句話為何在不同脈絡下應該不同理解」。P3-C1 現在把這個問題改成
可操作的 paired intervention，並把系統最容易作弊的方向——看到隱含意圖就到處過度解讀——列為共同成功條件。因此後續若 system
只是在所有題增加推測，它會明確失敗，不會被包裝成理解力提升。

## 尚未證明

目前沒有任何 C1 真實模型輸出或結果；developer-authored target 也不是人類共識或私人心理真值。P3-C1 不證明 system 優於 LLM、
被理解感、真實人物未來預測或人腦方程式。下一階段須先凍結 provider runner 與 balanced order，再只用 train/dev 檢查介面；
holdout 在所有介面變更停止後才允許一次性執行。
