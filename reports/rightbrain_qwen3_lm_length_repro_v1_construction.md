# Qwen3 完整 LM 64 / 800 token 定位實驗

- 唯一變因：64 或 800 token 計算圖。
- 兩組前 64 token、有效標籤與所有模型元件完全相同。
- 800-token 組只追加 736 個 label=-100 的 padding。
- 固定 36 層、全 LoRA、LM head、交叉熵、Metal 與零更新。
- 不包含人格、benchmark 或 production 修改。
