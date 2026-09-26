# P4-AZ real previous-turn ellipsis to action delivery: formal FAIL

事前凍結的兩輪 private runtime／Safari gate 正式為 **FAIL**。兩輪在同一隔離 session、port `7892` 各執行一次；題目、gate 與結果永久封存，不重跑，也不在結果後改門檻。

## 可見結果

Turn 1：

> 腦子裡的思緒一陣一陣湧上來，今晚一直靜不下來。

> 今ほしいの、止め方と、ただ聞いてほしいのと、どっちに近い？

Turn 2：

> 你先釐清我想要哪種回覆很好；現在給我一個立刻能做的具體步驟，做完就結束。

> 今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。

兩輪皆為自然日文，各有一筆隔離 durable episode；Chroma 恰有 2 筆 embedding。Safari 真實顯示兩輪 node graph，並展開核對 P4-AZ 與 M45；沒有關閉任何既有分頁。

## P4-AZ 真正通過的部分

Turn 1 產生 `calibrate_need` 的可見澄清，P4-AS=`executed_and_committed`，M44 把 exact receipt `p1-1-edcea049e7c9ba65` 留到下一輪，六個 P4-AG 候選的結果仍被鎖定，沒有先偷看未來回饋。

Turn 2 先完成以下既有鏈：

- P4-AX=`bounded_support_composed`，把「剛才先釐清很好」與新的 practical-help request 分開；
- P4-AT=`closed_supported`，prediction identity 與 Turn 1 精確相同；
- P4-AY 找到 1 個可排除的 feedback／response-form reference、0 個 genuine replacement task，並只停在 `blocked_prior_source_role`。

新 P4-AZ 在真實產品得到 `authorized_previous_turn_cjk_ellipsis`：八個 exact-chain checks 與七個 source checks 全通過。它沒有把 `speaker_role=unspecified` 改成第一人稱，也沒有把「思緒湧上來」升格成已知心理真相。P4-AU 隨後得到 `prior_source_linked`，新增來源恰為 `prior:1`，digest=`e74410df5013679a`，與 Turn 1 原句完全相同；assistant／private-inference source 都是 0。

圖表順序是 P4-AY `47` → P4-AZ `48` → P4-AU `49` → M50 `50` → M53 `55` → M46 `56` → M45 `57` → utterance `70`。因此，P4-AX formal Safari pair 暴露的「前一輪中文省略主語來源無法交給下一輪行動生成」缺口，這次已在一條全新真實產品路徑收斂。

## 最早剩餘失敗已移到 M46 model review

來源交接後，M51 確實產生 2 個不同候選，其中 1 個通過結構檢查並被選中；P4-AV 沒有繞過 M46/M45/M39，M53 也記錄 0 個 unsupported named label。這表示失敗已不是「沒有來源」或「沒有候選」。

真正最早的剩餘失敗是第二個 model-dependent gate：

- 第一個 model call 完成候選生成，記錄 `876` prompt tokens、`300` completion tokens；
- 第二個 M46 counterfactual review 發生 `TimeoutError`；
- M46=`counterfactual_review_unavailable`，所以不能把結構正確的候選直接當成內容正確；
- M45=`withheld_model_unavailable`，沒有交付動作；
- M39 正確 fail closed，留下 `practical_action_not_delivered_m45`；
- 最終可見句仍是再次澄清，而不是「立即可做且做完停止」的一步。

這是一個有價值的因果分離：P4-AZ 修好來源授權與交接，但並未假裝同時修好 model review 或可見建議品質。

## 成本與正式失敗

Turn 1 end-to-end=`3.507s`，Turn 2=`38.1682s`；僅 1/2 達到 20 秒目標。總 model calls attempted/completed=`2/1`，已完成 call 的 token=`876+300`；timeout call 沒有完整 token，因此 accounting 標為 incomplete。

正式失敗 gate 共七個：M45 delivery、M46 verification/content/surface、M39 practical act、禁止再次澄清，以及 2/2 latency target。來源、完整性、graph ordering、日文、durability 與 no-private-source gates 都通過，但不能替代這七個產品交付失敗。

## 能主張與不能主張

現在可以主張：在一個全新兩輪 Safari session，系統能把上一輪中文省略主語的可觀察問題來源，在不改寫說話者角色、不新增私密推論的前提下，精確接到下一輪 practical-help planner；這個轉移在 graph 中可逐節點核對。

不能主張：具體步驟已交付、建議對真人有用、使用者感到被理解、open-domain 語用泛化、人類方程式，或優於 matched strong LLM。

## 下一個單一變因

本正式 pair 只保留為 exposed negative evidence，不再執行。下一個工作只隔離「已經有 source-bounded、structurally-valid candidate 後，M46 review 為何仍不可用且超時」。不能把 M51 結構通過當作內容通過，也不能單純拉長 timeout 後用同一題重跑。

下一階段應先凍結新的 review-availability task card，檢查是否能在相同內容／表面標準下，減少重複 model work或建立可審計的 deterministic pre-review，使正式路徑在 20 秒內完成；任何修改仍需用新的 fresh Safari pair 驗收。
