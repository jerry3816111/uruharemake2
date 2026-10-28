# P3-B3 tokenizer/provider binding probe 預註冊

日期：2026-09-14（Asia/Taipei）

## 問題與單一變因

P3 需要用相同 token 預算比較三個條件，但目前只有離線 Hugging Face chat template 的候選計數，尚未證明它等於產品兩條本機 Ollama transport 回報的 prompt usage。這一步只改變一件事：把同一 `qwen2.5:7b` 模型的 provider usage 與離線計數綁定。它不測回答內容，也不讀 P3 developer-smoke 題目、annotations 或正式資料庫。

## 凍結設計

- config：`configs/p3_tokenizer_binding_probe_v1.json`
- config SHA-256：`47974ee1558d0a53dd2e9a401c570901f17b3ccea842f12a18ae47215f072be3`
- 模型：`qwen2.5:7b`
- Ollama blob digest：`2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`
- transport：OpenAI-compatible localhost 與 native Ollama localhost
- fixtures：3 個 fit、1 個未參與 fit 的 verification；兩 transport 各 4 次
- generation：temperature 0、seed 20260909、top_p 1、num_ctx 8192、think false、每次最多 1 completion token
- 成本上限：恰好 8 個 provider evidence calls、最多 8 completion tokens、0 paid calls、0 retry
- 資料保留：只留 usage、時間與 output hash，不留生成文字

估計式事前固定為：`provider_prompt_tokens = hf_chat_template_tokens + integer_transport_offset`。每條 transport 的 3 個 fit offset 必須完全相同；第 4 個 fixture 必須在 tolerance 0 下被精確預測；同一 fixture 的兩條 provider count 也必須相同。

## 成功、失敗與停止規則

只有兩條 transport 同時符合上述全部條件才是 `provider_binding_pass`。任何 offset 不一致、verification 不精確、兩條 transport 不一致、usage 缺失、模型／設定漂移、額外 call、timeout 或 intent-only 中斷，都保留為 `binding_failed_retained` 或終止錯誤；不可改 fixture、tolerance 或重試追分。

成功只表示這個 frozen model／template／probe shape 的 token 計數可綁定，不表示回覆品質、UruhaBrain 優勢或人類反應方程式成立。失敗則阻止後續 P3 developer smoke 的公平 token 比較，需回到設計審查。

## 執行前證據

- preflight：`analysis/p3_b3_tokenizer_binding_probe_preflight_2026-09-14.json`，`ready_for_execution_review`，0 generation／network／paid calls
- fake contract：`analysis/p3_b3_tokenizer_binding_probe_contract_2026-09-14.json`，`offline_tokenizer_contract_pass`，只驗狀態機與計算規則
- P3 contract：66 passed
- 相鄰 compute／persona／token-parity regressions：32 passed，保留 8 個既有 dependency warnings
- review：同一 Codex task 自審，不是獨立 reviewer
