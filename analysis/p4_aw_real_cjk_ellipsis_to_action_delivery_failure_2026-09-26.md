# P4-AW real CJK ellipsis-to-action delivery: formal FAIL

事前凍結的兩輪 private runtime／Safari gate 正式為 **FAIL**。兩輪都只執行一次，使用同一個隔離 session、port `7887`；題目、gate 與結果不重跑、不改寫。

## 可見結果

Turn 1：

> 腦袋裡的想法一直轉個不停，怎麼都安靜不下來。

> しんどくて止まらないのと、楽しみで止まらないの、今はどっち寄り？

Turn 2：

> 你剛才先確認我需要什麼是對的；現在給我一個能立刻做、做完就停的動作。

> 今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。

兩輪都是自然日文、都寫入隔離 episodic memory，Chroma 恰有 2 筆 embedding；Safari 真實顯示兩輪 graph，未關閉任何分頁。

## 新能力真正通過的部分

Turn 1 的 P4-AW 在真實產品中得到 `authorized_current_user_ellipsis`。它沒有把來源改寫成明示第一人稱：M39 的 source role 仍是 `unspecified`；但在 current-user、CJK、typed `cognitive_overactivity`、direct frame、無第三人、M39 可見行為已驗證、P1／plan／pending identity 全部精確時，允許這一輪建立 executed-action authority。

因此同一輪得到：

- P4-AS `executed_and_committed`；
- M44 exact receipt `p1-1-6c5f453019d919e9`；
- P4-AR `authorized_executed_product_event`；
- P4-AG 六個候選、選中 `calibrate_need`；
- temporal future `committed_outcome_locked`。

P4-AW 沒有修改 source frame、trigger detector、候選排序、feedback classifier、P1/P4-AR guard 或 visible reply；新增 model call、factual memory write、raw dialogue trace、private-state truth 都是 0。Safari 已展開 P4-AW 節點。這只把先前 P4-AV 真實 T1 的特定 upstream 缺口從 offline 推進到一條新的 real-product path。

## 兩個獨立的 Turn 2 失敗

第一個失敗在語用閉環，而不是生成末端。Turn 2 的前半句「先確認我需要什麼是對的」本應支持上一輪 `calibrate_need`，後半句則是新的 `solve_regulation` 要求；實際 P4-AT 卻把整句當成本輪 request，得到 `closed_unknown`、`two_independent_acts=false`。exact previous-event identity 仍正確，且 performed action strictly earlier／prior future consumed 都正確，但 previous outcome 不是 supported。

所以 P4-AU 正確 fail closed 為 `blocked_no_decisive_action_feedback`，沒有把 Turn 1 來源正式加入本輪。它仍記錄了相符的 Turn 1 digest `90fdfa7059f3e5db`，但 `prior_source_added=false`；不能把「看得到 digest」寫成 source handoff 已通過。

第二個失敗獨立存在於動作交付：M51 真的生成 2 個不同候選，結構檢查也是 `2/2`；M52 也實現 `2/2`。但 M45 的兩次 model operation 只有一次完成，第二次 `TimeoutError`，使 M46=`counterfactual_review_unavailable`。因此 M45=`withheld_model_unavailable`，M39 對 `practical_action_not_delivered_m45` fail closed，最後可見回覆再次澄清，沒有交付「立刻做、做完就停」的動作。

這次不是 M53 的標籤阻擋：M53 是 `no_named_labels`，P4-AV 是 `predecessor_preserved`，沒有任何 operational role 可被授權。也因此凍結的 P4-AV authorized gate 並未通過。

## 圖與成本

Turn 1 graph index：P4-AW `65`、P4-AS `66`、P4-AR `67`、temporal `68`、utterance `70`。凍結 gate 還要求 P4-AG graph node；該輪 logic 有 exact binding，但 blackboard 沒有獨立 P4-AG node，所以這個 ordering gate 必須記為失敗，不能用 logic 代替圖。

Turn 2 graph index：P4-AU `49`、P4-AV `54`、M53 `55`、M46 `56`、M45 `57`、P4-AT `66`、P4-AG `67`、temporal `68`、utterance `69`。Safari 已實際展開 P4-AT、P4-AU、P4-AV 與 M45 failure node。

Turn 1 end-to-end=`3.8869s`，達到 20 秒目標。Turn 2=`38.1546s`，未達標。總 model calls attempted/completed=`2/1`，可記錄 tokens=`546+272`，但 timeout 使 token accounting 不完整。

## 能主張與不能主張

現在可主張：在一個全新真實 Safari 輪次，受限的 CJK 省略第一人稱語法可在不偽造明示 source role 的前提下建立 exact executed-action event。

不能主張：完整兩輪 action delivery、P4-AT 複合語用支持、P4-AU prior-source handoff、P4-AV real authorization、建議有用、被理解感、人類方程式、自然分布泛化，或優於 matched strong LLM。

## 下一個單一變因

這組正式題永久封存。下一個 milestone 只修「同一當輪同時含有對上一行動的明示支持，以及新的 practical-help request」的 bounded compositional split。需先凍結全新的中／英／日正例與 false-link controls，保持 exact receipt identity、current request routing、M46/M45 fail-closed 與 timeout 結果不變。完成 offline 後仍要另一組全新 Safari pair；不能用本題修後重跑包裝成正式通過。
