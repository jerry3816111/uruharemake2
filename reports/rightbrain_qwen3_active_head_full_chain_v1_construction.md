# Qwen3 active-token 完整反向鏈零更新實驗

- 唯一變因：tied LM head 接收 511 個或 16 個 hidden positions。
- 兩組共享完整 36 層 Transformer、全層 LoRA、batch、seed 與 loss。
- 每組 18 個隔離程序；AB 與 BA 執行順序各 9 次。
- 不建立 optimizer、不更新參數、不儲存、不生成、不修改 production。
