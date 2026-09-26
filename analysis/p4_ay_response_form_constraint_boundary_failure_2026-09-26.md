# P4-AY response-form constraint boundary: offline FAIL with bounded partial pass

P4-AY 依 `5735fc9` 事前凍結的 19 個新案例與 6 個 predecessor positives 實作。完整 frozen gate 為 **FAIL**；資料、門檻與失敗結果不改寫。

## 它真正修好的部分

P4-AY 只在 exact P4-AX/P4-AT 已證明「支持上一輪澄清 + 本輪 practical request」之後，重新判斷 M47 current-task refs。它只排除：

1. 已被 P4-AX 授權的 exact feedback clause；
2. 沒有新問題內容的受限 response-form／action-shape constraint，例如「一個動作、立即開始、有明確終點」。

全新中／英／日正例 `6/6` 均由原本 `blocked_current_task_replacement` 變成 exact prior source linked，source identity=`6/6`，並通過既有 deterministic fake-M45 structural contract=`6/6`。這個 fake downstream 只證明結構接線，不是 live model 品質。

12 個 controls 全部沒有加入 prior source，其中 genuine new topic（報告、面試筆記、履歷）`3/3` 得到 `blocked_genuine_task_replacement`。第三人稱、引用／測試句、receipt mismatch、非 practical policy、沒有上一輪回饋也都保持 fail closed。既有 P4-AU positive links=`6/6` 保留。

P4-AX authority=`7/7` 保留；P4-AT outcome mutation、P4-AU non-task guard bypass、候選排序、visible reply、新增 model call、factual memory、assistant/private source、raw dialogue trace、完整 frozen 字串 patch 全為 0。

聚焦與相鄰回歸=`33 passed`。port `7890` 隔離 sandbox product preflight=`ready`，server 未啟動，model call／Safari operation／VRM-tool execution=`0/0/0`。

## 為什麼完整 gate 仍失敗

exposed development 使用 P4-AX 正式 Turn 1：

> 腦中的念頭一波接一波冒出來，怎樣都停不下來。

P4-AY 已成功證明 Turn 2 的 current refs 都只是 feedback／response form，沒有新主題；但接著碰到 P4-AU 下一個既有 guard：這句中文省略第一人稱，M39 source role=`unspecified`，P4-AU 只內建日文 subject ellipsis，因此得到 `blocked_prior_source_role`。P4-AY 誠實停在 `blocked_non_task_p4_au_guard`，沒有把它升成 direct first-person。

這不是 P4-AY 應順便放寬的條件。P4-AY 的單一變因是 current-task replacement discrimination；若同時改 prior-source role authority，就無法知道 source link 是哪一項改動造成。因此 frozen development 的 `development_authorized_count=0/1`、`development_prior_source_linked_count=0/1`，完整 gate 必須為 FAIL。

## 第一次失敗與唯一 correction

第一次實作是 fresh positives=`5/6`、controls=`12/12`、development=`0/1`。日文 frozen positive 的 ordinary copula suffix `だった` 沒被 feedback-only grammar 接受；證據統計也把 predecessor 的「exact source 已存在」錯算成「P4-AY 本輪新加入」。

唯一 informed correction 只補 frozen 日文肯定語尾，並修 evidence harness 對 already-present exact source 的計數。修後 fresh positives=`6/6`、predecessor=`6/6`；沒有碰中文 prior-role guard、資料、gate、P4-AX/P4-AT、model、prompt、memory 或 visible reply。第一次結果保存在 `analysis/p4_ay_first_implementation_failure_2026-09-26.json`。

## 能主張與不能主張

可以主張：在 frozen 三語句型與 controls 中，系統能把「我仍在問同一個問題，只是限制你怎麼回答」和「我換了另一個要處理的問題」分開，而不放寬其他 source authority。

不能主張：P4-AY 完整 offline 通過、正式 P4-AX pair 修復、中文省略主詞 prior source 已授權、live model 能交付動作、建議有效、被理解感、人類方程式，或優於 matched strong LLM。

## 下一個單一變因

下一個 P4-AZ 只處理 exact previous-turn CJK subject ellipsis 的 prior-source authority。必須要求既有 typed cognitive-overactivity、direct current-user frame、無第三人／引用／report、exact earlier executed receipt 與 P4-AT support chain；來源角色仍誠實保留 `unspecified`，不能泛化成明示第一人稱。需先凍結新的中／日正例與 third-party、meta、news/report、physical-object、resolved、ambiguous controls。

P4-AZ 不得改 P4-AY task discrimination，也不得順便修正式輪次獨立存在的 M45 `JSONDecodeError`。offline 若通過，仍需全新 Safari pair。
