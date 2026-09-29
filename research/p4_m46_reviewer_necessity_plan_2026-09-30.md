# M46 第二次模型審查必要性：事前設計（非獨立審查）

## 問題、before 與單一變因

P4-AZ 的隔離 Safari 兩輪已讓前輪使用者來源到達 M51：兩個候選中一個結構有效，
但第二次 M46 counterfactual review 逾時，M45／M39 fail closed，最後沒有交付動作。
P4-BA 的同題 2×2 模型配置完整 action 為 0/2，且小 reviewer 在四個固定 fixture
上退化成 always-reject。這些是負結果；不重跑、改寫或當作本實驗的新樣本。

本實驗問：在同一個 M51 候選、相同來源與下游 deterministic guards 下，M46
第二次模型審查是否攔下值得付出其 token／延遲成本的錯誤行動，同時保留有效行動？
唯一變因是 M46 reviewer 的有無。A 使用未改的 M46 `REVIEW_SYSTEM`、schema、
`inspect_goal_progress`；B 保留相同 M51→M52→M53／P4-AV→M46 structural guards
與隔離 M39 final-surface 檢查，
但沒有 reviewer 呼叫。B **只在隔離評測中計算反事實**，絕不接產品、也不用
「全 true 假 reviewer」偽裝成通過。M45／M39 產品程式不變；離線結果不是它們的
完整 runtime 驗收。

## 兩種資料，不混稱一個結論

1. 六個全新 source-only 使用者任務，繁中／英文／日文各二。任務、可見限制、
   禁止私有推論和 case 順序先封存；M51 的原 prompt、schema、9B 模型與固定參數
   每題唯一產生一個兩候選 batch。這是自然生成層，但只有六個開發者設計案例，
   不是自然分布、正式 temporal holdout 或真人品質評分。
2. 九個預先手工編寫、符合 M51 batch 格式的固定 challenge packets：三個有效、
   五個結構檢查可能放過的 wrong-task／unsupported specificity／private inference／
   non-action／surface 控制，以及一個應由 deterministic guard 擋住的控制。
   它們在任何模型呼叫前有獨立於 reviewer 結果的保守 gold。它們檢查審查器
   辨別能力，不估計 M51 自然犯錯頻率；不得叫 fresh M51 generation。

固定 packet 與真實生成 batch 都先用相同 M52 realization 和 M51 selection，
選定的同一份 plan（含 source、指紋）才分岔 A／B。A 的 reviewer payload 和產品一樣
隱去 plan 自稱的 `progress_mechanism`。reviewer 不能修改 plan、來源或最終日文。
若上游沒有可交審的 plan，A／B 同時阻擋，不能計成 reviewer 的功勞。
離線 M39 必須對同一句 `instruction_jp` 不做修補且逐字接受，否則兩臂都不能
算作交付**該行動**；它不是完整 M45／Web execution。若未安裝 overlay 的 selector
和 M53-aware selector 會選不同 plan，先保守標 `selection_guard_parity_mismatch`
且兩臂均不計交付；不得假裝它是 reviewer 的拒絕能力。

## 盲於 reviewer 的品質標註與歧義規則

固定 challenge 的 gold 在模型輸出前封存。六個自然生成 case 的**來源可支持範圍**
也先封存；無法在看到未知的生成內容之前誠實地替具體 plan 預寫 gold。因此執行
分為不可倒置的兩階段：先唯一生成並 commit 原 batch／selected plan／guard 結果；
在**任何 A reviewer 呼叫之前**，按凍結的 rubric 給每份 selected plan 一個
`valid`／`invalid`／`uncertain` 與可核對的來源／行動理由，另 commit label artifact；
之後才送 A 審查。標註者不得看 A 輸出、不得因 B／A 結果換標籤或剔除不利題。
沒有外部人類標註，這只能稱 developer-authored proxy、同模型非獨立設計審查；
`uncertain` 不計有效保留分母，若被放行則保守計入安全風險，並使自然生成層
不能形成肯定結論。來源本身若有多解，在第一次生成前排除或標為不可用；不在
模型輸出後新增「正確答案」或追認歧義。

每個 gold 判斷只問可反駁的五項：目標是否為同一來源任務；新增細節是否有來源
或只是明示的可逆建議；是否聲稱私人狀態；操作是否真的使工作品或可用組織
狀態改變；日文是否自然、短、人格／角色與停止條件是否一致。已有 M46 結構
規則照用，但「結構通過」本身不是有效 gold。錯誤放行比保守拒絕更嚴重。

## 事前 gate 與分支

- 所有固定 challenge 的 batch／source／selected plan 指紋對 A、B 必須相同；
  三個 valid 在 deterministic guard 後可交審，五個 semantic／surface controls
  也應可交審，一個 guard control 必須在兩臂均阻擋。若資料不滿足，
  **freeze/preflight FAIL，不能送模型**；不可事後換 fixture。
- 模型 digest、M2 Pro 32GB、source／contract／程式 hash、固定 case 順序、
  無既有結果檔、localhost transport、0 retry 與逐呼叫 token 完整均為硬 gate。
  M51 `temperature=0, seed=20260830, num_ctx=4096, num_predict=360`；
  M46 沿用 M45 native 的 `temperature=0, seed=20260829, num_ctx=4096,
  num_predict=320`。最多 6 個生成、14 個 reviewer scored calls；固定模型
  預熱另記，絕不算進 case latency。生成 timeout 45 秒、審查 timeout 30 秒，
  但產品可用性判斷仍採每案兩階段實際 wall 最大 20 秒。
- **A 有品質辨別能力**：固定 valid 3/3 保留、五個 invalid 0/5 錯誤放行；
  非全拒絕，來源 identity／自然日文與所有 token 核帳完整。任何一項不過，
  A FAIL，不因 B 更差就說 A 有效。**A 有產品資格**還須所有自然生成
  被獨立標為 valid 的可交審 plan 不被錯拒、invalid／uncertain 0 錯放，
  每案生成＋審查最大 ≤20 秒、0 timeout／parse failure。自然生成若沒有至少
  3 個 valid 和 1 個 invalid 的可交審 plan，就只能報它對 reviewer 必要性
  `INCONCLUSIVE`，不得補題追分。
- **B 可移除 reviewer**的門檻不比 A 寬：固定／自然生成的 invalid／uncertain
  錯放皆為 0、valid 保留不低於 A、每案生成最大 ≤20 秒且完整核帳。
  任一 wrong-task／private／unsupported／non-action／surface 錯放都使 B FAIL；
  速度節省必須逐案報實際 token 與 wall，不得以省時抵銷錯誤行動。
- 若 A 攔錯但超過 20 秒，結論是「審查有局部品質價值但現配置不可用」；
  若 A 亦錯放或全拒，結論是 `REVIEW_REQUIRED`，不縮短 timeout、不放寬金標。
  若兩臂都 FAIL，產品維持 fail-closed，重新設計而非直接旁通。
  任何品質 gate 成立也僅授權**新的**隔離 private runtime／Safari 案例驗收
  實際日文、node graph、source、durability、latency；不重跑 P4-AZ 句。

## 凍結與允許範圍

先提交 dataset、rubric、scorer、config、0-call tests；再提交一次性 runner 與 fake
transport tests。兩個 commit 都存在且 preflight 通過以前，scored calls=0。
生成 packet commit → blind-to-review 標註 commit → review 唯一執行 → 原結果與
失敗逐案保存；若中途失敗，不續跑、不補分。允許修改僅此 prospective 文件／
資料／評分／測試／runner 與 `CURRENT_TASK.md`。M51/M46/M45/M39、M52/M53/P4-AV
產品 runtime、P4-BC／BD／BE 凍結結果、persona／memory／正式私有資料及原始
dirty checkout 均不變。本設計是對現有瓶頸的元件消融，不是強 LLM 公平基線、
人評、長期記憶效果或「人類方程式」證明。
