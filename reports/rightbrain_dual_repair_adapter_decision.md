# RightBrain Dual Repair Adapter Decision

## 結論

雙 adapter 路由值得保留，但目前的 v12 repair adapter 不值得上線。

## 這次驗證了什麼

- runtime 現在可以同時載入 surface adapter 與 repair adapter。
- 初次候選生成使用 surface adapter。
- 只有在初次候選全數失敗且 repair enabled 時，才切到 repair adapter。
- repair 生成後會立刻切回 surface adapter，避免污染後續回答。
- trace 會記錄 `adapter_name` 與 `used_repair_adapter`，可以驗證 repair 是否真的走第二 adapter。

## 行為結果

| 條件 | surface adapter | repair adapter | raw acceptance | repair success | effective acceptance | final pass |
|---|---|---|---:|---:|---:|---:|
| baseline | v8 | 無 | 40% | 0/6 | 40% | 100% |
| dual adapter | v8 | v12 | 40% | 0/6 | 40% | 100% |

## 解讀

雙 adapter 架構成功隔離了風險：v12 不再拉低初次候選，raw acceptance 從 PR #39 的 30% 回到 v8 的 40%。但是 v12 在 repair 階段仍然 0/6，代表它沒有學到可用的修復能力。

## 上線決策

- 保留雙 adapter 機制。
- `URUHA_RIGHT_BRAIN_REPAIR_ADAPTER_PATH` 預設不設定。
- `URUHA_RIGHT_BRAIN_MODEL_REPAIR_ENABLED` 預設仍關閉。
- v12 不作為正式 repair adapter。

## 下一步

下一輪應訓練真正獨立的 repair adapter，而不是把 v12 這種同一 LoRA continuation 拿來上線。新的 repair adapter 必須同時滿足：

- repair success 高於 baseline 0/6。
- raw acceptance 不低於 v8 baseline 40%。
- final pass 維持 100%。
- trace 顯示每次 repair 都使用第二 adapter。
