# P3-B6 single-turn real product canary 驗收

日期：2026-09-14（Asia/Taipei）

結論：**PASS（只限一輪真實產品整合）／QUALITY NOT YET PASSED**。

## 真實執行

- input：`最近下班後我總是很煩，什麼都不想做。`
- visible reply：`最近退社後は常に不機嫌で何もしたくないんだね。`
- route：native M31，1 provider call
- actual prompt／completion tokens：441／151
- allocated completion cap：280；aggregate cap：768
- provider wall：9.212799 秒；turn wall：10.752605 秒；cold init：0.262654 秒
- model：`qwen2.5:7b` frozen digest；normalizer 只插入 seed／top_p／num_ctx
- rejections／terminal failure／fallback：0／none／none
- network：1 個 localhost provider call；paid calls：0
- future turns／annotations／confirmation／production DB access：0／0／0／false
- ephemeral workspace removed：true

result：`analysis/p3_b6_product_canary_result_2026-09-14.json`，SHA-256 `9a412e765c9f29c0d3dc71643ae88e4376dc3df3a2f59739cc1ae86555a75cc4`。checkpoint 保存整輪 intent＋complete，未重試。

## 工程判定與品質觀察分開

工程 gate 13/13 通過：真實產品完成一輪、每個 call 都有 exact options/usage、prompt count 和 tokenizer reservation 相等、預算內、只有 localhost、資料隔離完整。

但這一步沒有讀 annotations 或跑 scorer，因此不能宣稱回覆更好。開發者可見觀察是：句子為日文且忠於「下班後、什麼都不想做」的大意，但 `退社後` 偏書面，`常に不機嫌` 把中文的「總是很煩」收斂成「總處於不機嫌」，可能顯得過度定性，也沒有明顯接住使用者想被陪伴、求方法或只想吐槽中的哪一種。這正是下一步同模型對照需要判斷的差異，不在看到結果後修改 canary。

## 證據邊界

這只證明一個 developer-smoke product turn 能在 frozen fair-comparison gate 下真實執行。它不是 baseline 比較、評分、holdout、人評、Safari、長對話或系統優勢證據；單輪工程通過也不表示「人類反應方程式」成立。
