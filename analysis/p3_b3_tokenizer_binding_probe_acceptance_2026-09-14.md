# P3-B3 tokenizer/provider binding probe 驗收

日期：2026-09-14（Asia/Taipei）

結論：**PASS（只限 frozen `qwen2.5:7b` token accounting binding）**。

## 真實結果

- evidence kind：`local_ollama_provider_usage`
- provider evidence calls：8；本次 real/network/paid calls：8／8／0
- completion tokens：8；總 wall time：6.052747 秒
- OpenAI-compatible transport：fit offset 0，verification exact
- native Ollama transport：fit offset 0，verification exact
- 同一 fixture 的兩條 provider prompt counts：4/4 相同
- HF／provider prompt counts：26、46、63、83，兩條 transport 全部逐列相等
- raw output text：未保留；只留 output SHA-256
- result：`analysis/p3_b3_tokenizer_binding_probe_result_2026-09-14.json`
- result SHA-256：`48eb67d56f3fa6d293eebd2bcd3e81766fbb464c935288c9e850ef0df1edf844`

8 次呼叫都在事前 commit `dd47ec0` 的 release 後執行；4 fixtures、tolerance 0、計算式、模型 digest、設定、call 上限與停止規則均未在看到結果後修改。16 個 intent／complete checkpoint 保留，沒有 retry、failure 或 intent-only 狀態。

## 測試證據

- P3 contract：66 passed
- 相鄰 compute／persona／token-parity regressions：32 passed；8 個既有 dependency warnings
- fake contract 另驗證非固定 offset 會保留 failed、0-call 結果不能冒充 provider evidence、完整 checkpoint 可在 0 新 call 下保留原證據、失敗與無效 payload 不可重試。

## 這一步真正排除的問題

在目前 frozen model／chat template／message shape 下，離線 `Qwen2TokenizerFast.apply_chat_template(..., add_generation_prompt=True)` 的 token count 可直接對應兩條本機 Ollama provider usage，不需要估計 offset。P3 後續可用它在 call 前檢查 context／prompt budget，並在 call 後用 provider usage 對帳。

## 仍不能宣稱

這不是回覆品質、產品 full-turn、長期記憶、Safari、人評、正式 holdout 或「比一般 LLM 好」的證據。4 個 synthetic fixtures 不能證明所有未來 Ollama／transformers 版本或任意 request shape 永久相等；模型 digest、template 或 adapter 變更時必須重新綁定。review 仍是同一 task 自審，不是獨立 reviewer。
