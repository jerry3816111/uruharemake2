# RightBrain 訓練信號尺度診斷：分析

## 結論

預註冊假設成立：原角色政策處理組的第一個 8 筆梯度累積批次，在任何
optimizer step 前的總梯度 norm 為 `403.7282`，是原裁切門檻 `0.3` 的
`1,345.76` 倍。若呼叫原訓練使用的全域 norm 裁切，理論係數為
`0.0007430742`，即梯度向量會統一縮放到原幅度約 `0.0743%`。

這只證明第一次更新會發生強烈全域裁切，**尚未證明裁切造成前一輪訓練
失敗**。原 optimizer 是 AdamW；依 PyTorch 官方公式，梯度同時進入一階矩
與平方後的二階矩，均勻縮放會在 `m_hat / (sqrt(v_hat) + epsilon)` 中大幅
抵消。下一輪必須直接比較 AdamW 第一步的理論參數更新，不能直接放寬
`max_norm`。

官方依據：

- PyTorch `clip_grad_norm_`：<https://docs.pytorch.org/docs/2.13/generated/torch.nn.utils.clip_grad_norm_.html>
- PyTorch AdamW：<https://docs.pytorch.org/docs/stable/generated/torch.optim.adamw.AdamW_class.html>
- Hugging Face PEFT：<https://huggingface.co/docs/peft/package_reference/peft_model>

## 實驗控制

| 項目 | 實際狀態 |
|---|---:|
| 來源模型 | V10 Qwen2.5-7B LoRA |
| 資料 | 原政策對齊 treatment 的固定首 8 筆 |
| 順序 | 原 seed `20260801` 重建，8/8 ID 相符 |
| 固定配置 | 每筆 800 tokens，8 次梯度累積 |
| backward | 8 次 |
| optimizer 建立／step | 0／0 |
| gradient clipping 呼叫 | 0 |
| 生成／模型儲存 | 0／0 |
| 權重 SHA-256 前後 | 完全相同 |

所有模型、adapter、資料、程式與前輪結果雜湊均在執行前鎖定。80,740,352
個 trainable elements 全部是 FP32，符合 PEFT 對訓練穩定性的建議。

## 實際數據

| 指標 | 結果 |
|---|---:|
| 8 筆平均 loss | 2.746010 |
| loss 範圍 | 1.902031－3.958298 |
| 總梯度 norm | 403.728180 |
| 梯度 RMS | 0.0449308 |
| 相對 0.3 門檻 | 1,345.76 倍 |
| 理論裁切係數 | 0.0007430742 |
| 有限梯度 | 80,740,352 / 80,740,352 |
| 沒有 gradient 的 trainable parameter | 0 |
| 執行時間 | 168.60 秒 |
| 程序 RSS | 0.53 GiB |

註：原始結果欄位沿用 `peak_process_resident_memory_bytes` 名稱，但實作是在
寫出結果前以 `psutil.Process().memory_info().rss` 讀取單一時間點；因此本表
只將它解讀為「結果寫出時的程序 RSS」，不能當作整次執行的記憶體峰值。
此欄位不參與假設判定。

前一輪 treatment 記錄到的最大裁切前 norm 是 `942,987.3125`，約為本次
第一批 `403.7282` 的 2,335 倍。這表示最大異常出現在後續更新路徑，而非
這個固定首批；本次單批診斷不能推論其餘 9 次更新的梯度大小。

## 梯度集中位置

| LoRA 側 | 合併 norm | 梯度平方占比 |
|---|---:|---:|
| LoRA-A | 3.1078 | 0.0059% |
| LoRA-B | 403.7162 | 99.9941% |

最大群組依序為：

| 投影群組 | norm |
|---|---:|
| `up_proj / LoRA-B` | 223.1766 |
| `gate_proj / LoRA-B` | 174.7180 |
| `v_proj / LoRA-B` | 173.8831 |
| `o_proj / LoRA-B` | 144.7581 |
| `down_proj / LoRA-B` | 112.6878 |

V10 權重本身的 LoRA-A L2 為 `45.7248`，LoRA-B L2 只有 `0.2090`。這與
梯度主要落在 B 側一致，但僅是機制線索，不足以把 B 側尺度定為 bug。

## 研究判定

可以主張：

- 第一次累積梯度是有限且非常大於原全域裁切門檻。
- 權重沒有因診斷而改變，結果不是新模型表現。
- 原訓練至少第一次 update 會進入強烈全域裁切區。
- 梯度幾乎全部集中在 LoRA-B，尤其 MLP `up_proj`。

不能主張：

- 全域裁切已被證明是角色政策訓練失敗的原因。
- 提高裁切門檻、學習率或 epoch 一定會改善結果。
- 後續 9 次 update 的梯度都等於第一次。
- 已得到任何人格相似、聊天品質或 production 證據。

## 下一個可推翻假設

在完全相同的第一批 raw gradient 下，分別依原 AdamW 公式計算「0.3 全域
裁切」與「不裁切」的第一步理論參數更新。如果兩者的更新 L2 與逐元素
方向幾乎相同，便排除裁切係數是微小權重更新的主要原因，下一個單一變因
應轉向 learning rate；如果差異很大，才有理由設計 max-norm 修復 pilot。
此診斷仍不需要 optimizer step、模型保存或正式 runtime 修改。
