# P3-B1 isolated product worker 驗收

日期：2026-09-13

結論：**P3-B1 在「零生成產品隔離與 transport seam」範圍 PASS；真實生成仍 DENIED。**

這一階段把 `uruha_web_ui_product.py` 放入每個 case 專屬的 subprocess 環境，並在產品 import 前隔離
Chroma memory、adaptive person model、Web logs、M31 model、idle visible、prewarm 與 right-brain model load。
它也把同一個 budget/model/options/usage gate 綁到產品實際使用的兩個全域入口：OpenAI-compatible
`OpenAI` 與 M31 native `urllib.request.urlopen`。未列帳的其他 network route fail closed。

## 可重現結果

- preflight：`analysis/p3_b1_product_worker_preflight_2026-09-13.json`
- preflight SHA-256：`040503a8d09d1885b9bd5a62ad7c00d164f97acdcf8ed65df71e3d359630f624`
- product comparison tests：42 passed in 11.21s
- 相鄰 compute/persona regressions：32 passed，保留 8 個既有 dependency warnings
- JUnit：`analysis/p3_b1_product_worker_tests_2026-09-13.xml`
- real model / network / paid calls：0 / 0 / 0
- formal／confirmation cases accessed：0

## 真正證明的內容

1. 產品入口兩次實際 import 都保持 lazy，brain instance 是 0；因此沒有 Ollama probe、Chroma 開庫或模型生成。
2. 同一 case + state slot 的第二個 subprocess 被辨識為 restart，state path hash 相同；不同 case 重用該 slot
   在產品 import 前以 `cross_case_state_reuse` 拒絕。
3. import 後 `DB_PATH` 指向 ephemeral case memory，而不是 repository 的 production DB；Web logs 與 adaptive
   model 也指向 case workspace。workspace 在 probe 後被移除。
4. OpenAI-compatible 與 native Ollama 兩條 gate 以 contract fake 各攔截一次，逐 call 記錄 exact usage；錯誤
   options、未 release 的 real transport、transport failure/retry 都有 fail-closed 回歸。
5. 本機已有 `Qwen2TokenizerFast` 與 chat template，offline fixture 為 25 tokens；但它只被記錄成 candidate，
   `provider_usage_equivalence_validated=false`。

## 仍不能宣稱

- 兩條 adapter 的成功呼叫是 contract fake，不是 Ollama response；不能說 product 已產生可比較回覆。
- gate 已綁到產品真正的全域 transport seam，但尚未實例化 brain，因此仍未觀察現有各 planner call 是否都能
  在 frozen options/token allocation 下完成。若現有 call 帶 temperature drift 或沒有 cap，下一階段會拒絕，
  不能暗中放寬比較條件。
- HF tokenizer/template 尚未和 Ollama 回傳的 `prompt_eval_count` 做 controlled provider equivalence；在此之前
  real transport 必須拒絕。
- 沒有 6-case developer smoke、品質評分、human preference、Safari、正式 holdout 或系統優勢證據。
- 此為同一開發 task 的自審，不是獨立 reviewer。

## 下一 gate

下一步只設計並凍結 6-case developer smoke 的 source/annotation manifest 與一次性的 tokenizer-binding +
product-smoke release。資料凍結與 release 完成前，仍是 0 generation；confirmation 資料與正式 DB 不可讀。
