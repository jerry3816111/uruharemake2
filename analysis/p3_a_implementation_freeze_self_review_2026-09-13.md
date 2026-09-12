# P3-A implementation freeze 自審

日期：2026-09-13

結論：**P3-A offline harness PASS；P3-B1 adapter implementation 放行；real generation 仍 DENIED。**

本次依使用者新指示取消 GPT6／GPT5 型號綁定，改由證據判斷是否能向下一 gate 收斂。本次是原開發 task 的
同模型自審，不是獨立 reviewer，因此 release 明確保留 `self_review_not_independent`，不擴大 claim。

## Review 找到並修正的實際缺口

| 缺口 | before 反例 | 修正後 |
|---|---|---|
| condition runner 信任外層 caller 驗 view | tampered/rehashed-extra view 能進 runner | 每個 runner 自行驗 schema、exact allowlist、source hash、input hash、view hash；0 transport 拒絕 |
| manifest 只有 aggregate token | 無法從 artifact 逐 call 對帳 | 每 call 留 request hash、exact provider usage、completion allocation；validator 重算並對 aggregate |
| wall 只加 transport usage | worker retrieval/writeback 時間可能未入帳 | 從 condition 接收 view 到 final 完成使用可注入 monotonic clock；超過 60 秒 fail closed |

新增反例先觀察到 4 failures，修正後 4/4 通過。整套 P3-A 由 30 增至 34 passed；受影響既有資源記錄回歸
32 passed，保留 8 個既有 dependency warnings。

## 凍結證據

- 新 contract：`analysis/p3_a_self_review_contract_2026-09-13.json`
- manifest SHA-256：`9517e8d4f7aee25360c31d8ec760077bea44e80c91d1781cc20d07cd99a922fd`
- design SHA-256：`7273e2a70945e9d4f71ea5058869ec156d0badc14b649371b1fa9ea5811107d6`
- fake transport attempts：5；real model/network/paid calls：0/0/0
- deterministic rebuild：相同
- JUnit：`analysis/p3_a_self_review_tests_2026-09-13.xml`
- preflight：`analysis/p3_a_self_review_preflight_2026-09-13.json`
- run refusal：`analysis/p3_a_self_review_run_refusal_2026-09-13.json`，exit 2、attempts 0
- release：`research/p3_a_implementation_release_2026-09-13.json`

舊的 2026-09-09 contract 未覆寫，仍能核對原始 P3-A 交付。

## 尚未通過

- 沒有真實 isolated product worker，因此兩種 transport 目前只有 mock route gate。
- provider-equivalent tokenizer/template binding 尚未完成。
- 沒有 P3-B smoke data/review release，不能進行任何真實生成。
- 未碰 confirmation、正式 DB、Safari、人評或 runtime graph。

下一個唯一工作是 P3-B1：新增一個隔離 worker helper，先完成 0-generation import/env/transport interception
驗證。這是讓真實 product 能安全進 comparison 的必要 adapter，不是新增能力平台。
