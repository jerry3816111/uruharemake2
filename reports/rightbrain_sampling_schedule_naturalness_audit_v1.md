# RightBrain Sampling Schedule Naturalness Audit v1

## 結論

保守採樣把自動 gate 通過率提高到 46.7%，但自然度審查只有 **6/11（54.5%）** 通過，因此 **不修改 runtime 預設**。

## 為什麼自動分數不夠

| case | 自動 gate | 實際問題 |
|---|---|---|
| background_family_pressure | PASS | `〜てはどうですか` 變成不符合角色的敬語／接客服務語域 |
| private_do_not_mention | PASS | `お体調`、`選抎` 是不自然或錯誤日文，且帶入不該主動提及的身體背景 |
| no_memory_plain_question | PASS | 出現非日文常用字形 `后`，回答也偏離「如何安排今天」 |
| support_read_receipt_self_blame | PASS | `自分勝手に悪いとは言わない` 扭曲了左腦原本「不要先怪自己」的意思 |
| reference_fragment_probe | PASS | `説明清聴する` 是錯誤搭配詞 |

## 決策

- 保守 schedule 只能算「自動指標候選」，不能上線。
- 現行 runtime 採樣參數保持不變。
- 下一個工程瓶頸是建立一般化日文流暢度／搭配詞檢查，不能只擴充錯字黑名單。

## 邊界

這是非盲的 agent 語言審查，不是假裝成人類盲測。它足以否決部署，但不能用來主張人類偏好勝出。
