# 右腦 V29 同策略人類盲測封裝

## 結論

可以進行 11 次一鍵人類比較。

## 為什麼需要人類

程式先排除中文、亂碼、內部計畫外洩、禁用記憶與其他可確定的硬失敗。語意 marker 只是近似規則，不會替人類決定答案；留下的左右回答都來自同一個正式 V10，人類只判斷自然度、語意完整度與人格感。

## 數量

- 真實生成候選：129
- 題內文字去重後：129
- 現行嚴格契約通過：12
- 硬性表面安全通過：38
- 排除舊盲測與 promotion 重疊後可用：38
- 可配成兩個不同硬性表面安全候選的題目：9
- 獨立比較：9
- 隱藏一致性重測：2
- 類別覆蓋：8
- package build seed：20260712
- 候選報告：reports/rightbrain_on_policy_v29_candidates.json, reports/rightbrain_on_policy_v29_candidates_seed20260713.json, reports/rightbrain_on_policy_v29_candidates_seed20260714.json, reports/rightbrain_on_policy_v29_candidates_seed20260715_focused.json, reports/rightbrain_on_policy_v29_candidates_seed20260716_focused.json

## Gate

| Gate | 結果 |
|---|---:|
| exactly_requested_independent_comparisons | PASS |
| exactly_requested_consistency_repeats | PASS |
| all_candidates_same_formal_policy | PASS |
| all_candidates_hard_surface_pass | PASS |
| all_pairs_are_distinct | PASS |
| exact_prior_human_output_overlap_zero | PASS |
| exact_promotion_output_overlap_zero | PASS |
| blind_package_has_no_key_fields | PASS |
| consistency_repeats_are_spaced | PASS |
| package_hash_is_bound | PASS |

## 證據邊界

本封裝只能取得單一評分者的同策略偏好；不能單獨授權訓練、主張評分者間信度，或升級正式 runtime adapter。
