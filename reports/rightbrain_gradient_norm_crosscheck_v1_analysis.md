# RightBrain 梯度 norm 交叉驗證：分析

## 結論

交叉驗證通過。新 backward 的 total gradient norm 為
`2.878972291946411`，與前一輪三個隔離 process 的控制值完全相同。

五次 PyTorch MPS 官方 norm、CPU float64 全元素平方加總、逐參數 norm
合成、projection × LoRA-side 合成與 layer 合成都得到同一尺度。各種算法
的最大相對差約為 `2.6×10⁻⁸`，遠低於事前門檻。

因此，舊 `403.728180` 雖然在自己的 layer/group 資料內部一致，卻無法被
目前跨 process、跨裝置、跨算法的量測重現。它從現在起正式被排除於訓練
參數決策，不得再用來支持 `1345.76x` severe clipping 的結論。

## 實際數據

| 方法 | norm |
|---|---:|
| MPS 官方函式，五次平均 | 2.8789722919 |
| CPU float64 全元素合成 | 2.8789722173 |
| MPS 逐參數合成 | 2.8789722210 |
| projection / LoRA-side 合成 | 2.8789722210 |
| layer 合成 | 2.8789722210 |
| 三 process 控制值 | 2.8789722919 |
| 舊異常值 | 403.7281799316 |

## 事前判準

| 指標 | 門檻 | 實際結果 | 判定 |
|---|---:|---:|---:|
| 五次 MPS 相對 spread | <= 1e-7 | 0 | 通過 |
| MPS vs CPU float64 誤差 | <= 1e-5 | 2.59e-8 | 通過 |
| MPS vs group 合成誤差 | <= 1e-5 | 2.47e-8 | 通過 |
| MPS vs layer 合成誤差 | <= 1e-5 | 2.47e-8 | 通過 |
| 新值 vs 三 process 控制 | <= 0.1% | 0% | 通過 |
| 權重前後一致 | true | true | 通過 |

## 證據邊界

可以主張：

- `2.878972` 是目前同批 gradient 的可重現控制值。
- `403.728180` 不應再進入 max_norm、learning rate 或 AdamW 決策。
- 現在可以重新事前登記一次 AdamW clipped/unclipped 首步效果診斷。

不能主張：

- 已找到舊 `403.728180` 產生的底層原因。
- max_norm 應調高、調低或關閉。
- 右腦模型、人格相似度或正式聊天品質已改善。

下一步只允許使用 `2.878972` 作為完整性控制值，重新比較同一 raw
gradient 在 `max_norm=0.3` 與不裁切時的 AdamW 首步理論更新；仍不得執行
optimizer step 或儲存新模型。
