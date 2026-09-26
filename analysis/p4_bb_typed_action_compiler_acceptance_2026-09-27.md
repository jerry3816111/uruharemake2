# P4-BB typed action compiler boundary: formal PASS

事前凍結於 commit `a4dd116` 的 P4-BB deterministic compiler 完整通過。它只處理一個明確邊界：**上游已經產生且授權一份 source-bound typed task spec 之後，能否不再讓自由文字模型猜 progress mechanism，而直接編譯成既有 M46 可驗證的自然日文 action plan。**

這不是 raw-dialogue understanding 測試，也沒有接進產品 runtime。

## 實際輸入與輸出

| 原始輸入語言 | typed mechanism | 實際日文動作 |
|---|---|---|
| 繁中：簡報仍空白 | `structure_scaffold` | まずメモに見出しを三つだけ書いて、そこで止めよ。 |
| 繁中：收據按公司抬頭分堆 | `group_by_rule` | 机の領収書を、会社名ありは左、会社名なしは右に置いて、全部置いたら止めよ。 |
| 英文：會議筆記抽出一項決定 | `extract_relevant_subset` | 会議メモから決定事項を一つだけ抜き出して、そこで止めよ。 |
| 英文：寄信前檢查專案名 | `verify_named_condition` | まずメールの件名だけ見て、プロジェクト名が入っているか一回確認したら、そこで止めよ。 |
| 日文：關掉一個不用的分頁 | `remove_named_obstacle` | 使っていないタブを一つだけ閉じて、そこで止めよ。 |
| 日文：在空欄填今日日期 | `direct_atomic_completion` | まず空欄に今日の日付だけ書いて、そこで止めよ。 |

六案都保留 exact user source ID／span、逐字得到凍結的 expected plan，並通過既有 `M46.structural_plan_violations`。同案重編譯的 plan 與 digest 全部一致；不是從多個輸出中挑最好看的結果。

## 正式數字

- positive compiled／exact expected／M46 structural／source exact／mechanism exact／自然日文／repeat exact：全為 `6/6`；
- 六個 allowed progress mechanisms：`6/6` 覆蓋；繁中／英文／日文：`3/3` 語言覆蓋；
- source ID/span 錯誤、assistant source、假 evidence atom、缺欄位、額外 private-motive 欄位、未知 template、destructive safety、非日文 slot、缺 rule role、超大 count、缺 task spec：`12/12` 以事前指定原因 blocked；
- control false plan=`0`；model call=`0`；raw dialogue trace=`0`；factual memory write=`0`；
- formal run 最慢 compile=`0.00090479s`，低於 frozen `0.01s` gate。

33 個 freeze＋implementation tests 全部通過。產品 M51/M46/M45/M39 與 runtime model 都沒有修改。

## 相對 P4-BA 真正增加了什麼證據

P4-BA 證明單純把 generator/reviewer 換小無法同時保住品質與 20 秒：最快的 `4B+0.8B` 雖為 `16.78266s`，品質 gate 全失敗。P4-BB 則證明另一種架構切法在凍結範圍成立：把 mechanism、required evidence roles、slot schema 與停止條件變成 typed contract 後，下游 plan compilation 不需要模型，也不會再出現 `group_by_rule` 自由誤標或 always-reject reviewer。

但兩者**不是公平速度對照**：P4-BA 從 raw source 生成，P4-BB 收到的是資訊更完整的 typed spec。因此不能說 P4-BB 比 P4-BA 快幾萬倍，也不能用本結果刪掉 upstream 理解成本。P4-BB 的價值是把不確定性移到一個可以單獨驗證的上游介面，而不是藏在兩次自由生成裡。

## 能主張與不能主張

現在可以主張：對六個事前凍結、低風險、可逆 action ontology，正確的 source-bound typed spec 可以被 deterministic、exact-source、natural-Japanese、fail-closed 地轉成 M46 結構有效 plan；unknown／malformed／private／unsafe spec 不會回退到自由猜測。

不能主張：系統已能從一般對話形成正確 spec、模板涵蓋開放世界、建議對真人有用、使用者感到被理解、優於 matched strong LLM，或已得出人類方程式。六個模板是 bounded ontology，不是人的完整行動空間。

## 下一個必要證明

下一步 P4-BC 必須使用**完全新的 raw-dialogue cases**，事前凍結上游 typed-task-spec producer：同一來源要選對 template、擷取 exact evidence atoms、產生不含私密捏造的日文 slots；unsupported／ambiguous／risky cases 必須輸出 unavailable。4B 與 9B 可在相同 schema／資料／硬體下比較，但不能使用 P4-BB 已曝光句子追分。

只有 P4-BC 通過，才有資格測「raw dialogue → typed spec → P4-BB compiler」的一階段模型產品路徑與 fresh Safari；目前仍不改產品。
