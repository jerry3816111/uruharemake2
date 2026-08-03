# Qwen3 有效 token LM head VJP 實驗

- 唯一變因：completion mask 放在 tied LM head 前或後。
- 511 個位置中只有 16 個需要計分。
- 其餘 495 個位置不改答案，只增加無效投影。
- 三組共享 hidden、embedding 權重、targets、loss、seed 與裝置。
- 每組 18 個隔離程序；不訓練、不儲存、不修改 production。
