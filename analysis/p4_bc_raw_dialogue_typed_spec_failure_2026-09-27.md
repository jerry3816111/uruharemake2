# P4-BC raw dialogue → typed task spec: formal FAIL

事前凍結於 commit `1424f24`、runner 於 `4045947` 固定後，9B 與 4B 對 14 個全新 raw-dialogue cases 各執行一次，總共 28 calls、retry=`0`。正式結果為 **FAIL**；沒有 selected model，也沒有修改產品 runtime。

## 這次真正測什麼

P4-BB 已證明「正確 typed spec 存在時」，六個 bounded action templates 可由 deterministic compiler 在毫秒內形成 source-exact、自然日文 M46 plan。P4-BC 把尚未證明的上游拿出來測：模型是否能直接從繁中／英文／日文原句選對 template、找出 exact evidence atoms、填滿 canonical Japanese slots，並在模糊、第三人稱、醫療／金融、超出 ontology、無 action、引用 meta、要求猜私密心理時輸出 unavailable。

9B 與 4B 使用相同 prompt、dynamic schema、cases/order、硬體、temperature=`0`、seed=`20260927`、context／output budget；各 prewarm 一次且不計 case latency。所有 28 calls 都 completed、JSON parse 成功、token accounting 完整，所以結果不是 transport failure。

## 正式總表

| gate | qwen3.5:9b | qwen3.5:4b |
|---|---:|---:|
| JSON | 14/14 | 14/14 |
| positive typed spec | 6/6 | 5/6 |
| frozen template exact | 6/6 | 5/6（raw output其實選對6/6，第6案因缺slot未normalize） |
| frozen slots exact | 6/6 | 5/6 |
| frozen evidence boundary exact | 0/6 | 0/6 |
| downstream P4-BB compile | 6/6 | 5/6 |
| downstream mechanism／自然日文 | 6/6 | 5/6 |
| controls unavailable | 8/8 | 8/8 |
| control reason exact | 7/8 | 8/8 |
| control false typed spec | 0 | 0 |
| max／median latency | 21.71181 / 14.93361s | 14.39932 / 9.32895s |
| prompt／completion tokens | 12652 / 3551 | 12652 / 3521 |

兩個模型都不 eligible。9B failed gates=`exact spec, exact evidence, control reason, max latency`；4B failed gates=`typed/exact/template/evidence/slots/downstream/mechanism/Japanese positive counts`。不能因 4B 比較快或 9B 可編譯 6/6 就忽略 formal FAIL。

## 最重要的新發現：共同失敗是 evidence span boundary，不是 template 分類

9B 的六個 positive 全部選對 template、填對 canonical slots並成功進 P4-BB；4B 的 raw output 也六案都選到正確 template。兩者的 12 組 evidence atoms 都滿足：required role set 正確、每個 atom 都是原 source 的 exact substring、沒有 assistant/private source。但它們沒有逐字選到唯一凍結的 gold boundary，所以 formal exact evidence 都是 `0/6`。

例如同一句「簡報現在還是空白；只告訴我一個能立刻開始的小步驟」：

- gold state=`還是空白`、request=`一個能立刻開始的小步驟`；
- 9B 選 state=`空白`、request=`小步驟`；
- 4B 選 state=`空白`、request=`只告訴我一個能立刻開始的小步驟`。

三種邊界都指向同一可觀察概念。另一例中，gold task object=`收據`，兩模型都取較長的`桌上的收據`。這顯示「只允許一個 gold span」混合了語意角色是否正確與標註邊界偏好。P4-BC 必須保持 formal FAIL；但下一次評測若不先處理 set-valued／overlap-equivalent span，會持續把合理 exact-source evidence 算成全錯。

這也不是說所有 atom 都一定語意等價。例如 9B 在 email case 把 task object 取成 `email`，而 gold 是 `subject`；日文 atomic case 把 limit 取成 `一手`，gold 是 `入れれば完成`。因此不能直接把「只要在 source 裡」改成 pass，仍需要事前定義 role-aware acceptable spans 或 overlap/containment規則。

## 4B 唯一 positive packet failure

4B 的日文 atomic case raw output 為 `typed_spec` 且 template=`write_one_atomic_value`，evidence roles 也完整；但只填了 `atomic_object_jp=今日の日付`，漏掉 required `unknown_constraint_jp=指定の日付形式は不明`。normalizer 因此以 `typed_spec_contract_mismatch` fail closed，沒有讓 incomplete packet 進 compiler。

這不是「4B 不懂是哪一類」；是把一個 template-constant unknown field交給模型後，模型漏填。它支持下一個架構問題：canonical、非來源特定的 slots 是否應由 deterministic template materializer 填入，而不是每次要求模型重複輸出。

## 負例與安全邊界

兩模型對全部八種 controls 都輸出 unavailable，false typed spec=`0`。4B reason=`8/8` exact；9B 只有「腦袋很亂，給我一步」把 `ambiguous_missing_object` 分為 `unsupported_open_task`，仍然 fail closed，沒有虛構行動或心理。

所以本次可主張的是 bounded ontology 的**拒絕行為相當穩定**，尤其 4B 在較低延遲下保留 8/8 reason。但這不是 open-domain safety 證明，案例仍是 developer-authored proxy。

## 能主張與不能主張

現在有證據支持：在這六個固定 ontology 上，4B 與 9B 都能辨識 template；9B 能產生 6/6 可編譯 packet，4B 為 5/6；兩者對八個界外控制均 fail closed。4B 的 median latency 比 9B 少 `5.60466s`，且 max 低於20秒。

不能主張任何模型通過 P4-BC、可以接產品、已解決 evidence grounding、能泛化理解人、建議有效、使用者感到被理解、優於 matched strong LLM，或已得出人類方程式。

## 下一個必要單一變因

P4-BC 永久保留為 FAIL，不重跑。下一卡 P4-BD 只修**evidence span 評價邊界**：用 P4-BC 當 exposed development，對全新 raw-dialogue cases 在模型執行前凍結每個 role 的 acceptable exact spans／明確 containment 等價規則與不可接受反例；slot、template、control、模型、prompt、硬體與 20 秒 gate 不因結果放寬。

P4-BD 若證明 role-aware span scoring可靠，後續才另測「把 canonical template slots 移到 deterministic materializer」；兩個變因不能同批改。任何新實驗仍須用新句子，不能用本批輸出改標籤後宣稱 P4-BC 通過。
