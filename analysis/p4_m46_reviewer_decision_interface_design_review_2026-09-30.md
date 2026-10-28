# M46 固定辨別力 FAIL 後：審核判斷介面設計審查

狀態：**非獨立、事後設計審查；0 新模型呼叫，0 產品程式變更。** 本文不修改或重新評分
`41bb4f02edf1bab392a001e0043eda4368d57144` 凍結的 gold、封包、門檻與
`analysis/p4_m46_fixed_challenge_discrimination_2026-09-30.json` 正式 FAIL。

## 可歸因的 before 與不能推出的事

固定 challenge-only 實測有 8/8 完整、可解析的 9B 審核。A 保留有效方案 `1/3`（門檻 `3/3`）、
無效錯放 `0/5`，但五類負例只有 `4/5` 由對應理由辨出；B 無審核反事實錯放預構造負例
`5/5`，不能接產品。具體反例如下：

| 封包 | 觀察 | 歸因邊界 |
|---|---|---|
| 中文有效 | 內容全 true，`casual_japanese=false`；句尾 `止めよ`。 | `PLAN_SYSTEM` 容許 `止めよ`，但這不證明它符合自然口語；原 gold 未把內容與日文表面分開裁定，不能事後改成審核器純錯。M39 的逐字接受也非真人自然度。 |
| 英文有效 | 僅 `no_unknown_prerequisites=false`。 | 來源要求使用者從**自己已有**的筆記抽一題；具體題文對系統未知，不等於使用者無法執行。這是過度保守的可疑反例，非單題已證通則。 |
| 行動者錯置 | 可見句稱 `うちが…案内パネルを一つ閉じておく`，`no_identity_or_role_error=true`；靠 `no_unknown_prerequisites=false` 擋下。 | 產品未錯放，但審核理由漏掉「系統未經工具授權替使用者操作畫面」。M39 的隔離表面檢查也接受，不能用 deterministic-only 旁通。 |

原 M51 自然生成實驗於首個 call `17.63697s`、completion `360/360` 截斷 JSON，故其 A/B
仍是 `INCONCLUSIVE / NOT RUN`；本次固定封包不估計自然生成錯誤率。M46 reviewer-only
中位／最大 `13.210155/14.4233s`，並非產品兩階段延遲。P4-AZ 真實第二輪 `38.1682s`
且審核 timeout，P4-BA 9B/9B 最大 `35.71618s`、完整接受 `0/2`；因此即使新審核品質
改善，也不能單靠元件結果宣稱滿足產品 `≤20s`。

## 設計決定：只比較審核「判斷介面」

下一個、至多一次的前瞻修正批次選 **M46 單次 review decision interface**，而非調低放行門檻。
新介面仍用同一 9B、相同來源與 selected plan、原 M51/M52/M53/P4-AV 前置 guard、
同樣溫度／seed／`num_ctx=4096`／`num_predict=320`、同樣 fail-closed 原則；只把現有
「10 個 content + 4 個 surface 布林值全 true」的 reviewer prompt／schema 作為**一個契約邊界**
換成短的、證據錨定的分類。這是實驗原型，不在產品中替換 `REVIEW_SYSTEM` 或
`inspect_goal_progress`。新舊 A/B 對完全相同的選定封包各呼叫一次，0 retry；不得拿舊已曝光
九題作新分數。若新格式因 320-token 限制截斷或超時，算新介面失敗，不同時加 token／timeout。

新契約在凍結時須具體規定並測試：exact source id/span；進度前後狀態與 observed mechanism；
至少將任務對齊、實際狀態改變、來源／私人事實、執行前提、行動者能力、日文口語與停止點分成
可獨立檢查的 `pass/fail/uncertain` 軸；`uncertain` 必須 fail closed。執行前提要明確區分
「使用者可查閱手邊資料後自行做」和「建議本身依賴來源未給的確定事實、工具或操作權限」。
行動者要檢查**最終可見句**是否聲稱系統已／將替使用者做物理或 UI 操作，不能只看計畫目標。
每個 reject 要給一個對應的原因類別及短的來源／句子證據；證據不能代替獨立 gold。
詳細欄位、解析與 scoring 在任何新呼叫前另作 freeze commit；不能看輸出後改分類映射。

此變因同時改 prompt 與 schema，因為二者是同一個輸入／輸出契約；不能把效果歸因於
「哪一句 prompt」或某個單獨欄位。保持候選、模型、資源、前後 guard、資料與決策門檻不變，
才能歸因到**契約整體**。同模型 reviewer 是非獨立 proxy，不是人類審核。

## 為什麼不是其他路徑

- 只加 deterministic actor 字串 guard：可能堵這一例，但不能修有效英文誤拒或自然度歧義；
  亦會誤擋有工具 receipt 的合法助理操作、引述或「我幫你想」。不可用單題 regex 當泛化能力。
- 縮窄 action 類型或移除 reviewer：會犧牲 scaffold／extract 類有效方案；B 已對五個刻意構造
  負例全部錯放。速度不能抵銷錯誤行動。
- 先提高 M51 token 或產品 timeout：可能只修 JSON 可解析性，沒有修 M46 的已觀察辨別錯誤，
  且兩階段成本仍沒有 `≤20s` 證據。
- 直接接 P4-BB typed compiler：其 `6/6` 只是**已正確授權 typed spec** 的條件結果；
  P4-BE raw dialogue→typed spec full accept 僅 `1/6`，不能越過來源解析瓶頸。

## 新實驗先決條件、硬門檻與失敗分支

1. 在模型呼叫前封存全新繁中／英文／日文來源與完整候選封包、順序、原／新 review
   contract、scorer、模型 digest、硬體、token／時間上限和 SHA。新封包須成對覆蓋
   使用者已有材料 vs 虛構前提、使用者自己執行 vs 助理無 receipt 代操作、自然 vs
   生硬停止語，以及 wrong-task／unsupported specificity／private inference／non-action／
   actor-surface 五類負例；每類至少一題。這仍是 developer-authored proxy，非 temporal holdout。
2. 對每個完整封包，先於 reviewer 輸出分別標註**內容效用**與**日文表面／行動者**，
   再合成 `valid/invalid/uncertain` gold 與原因。原 `止めよ` 歧義不可被改舊 gold
   解決；新題若自然度有分歧，預先標 `uncertain`、記錄分歧，不能看模型結果後剔除。
   正例分母與不確定風險規則必須事前固定。
3. 原版與新介面逐案配對、各只呼叫一次；同一 plan、來源與 deterministic eligibility。
   各自的絕對 gate：完整 JSON／source identity／token accounting、所有明確 valid 保留、
   所有 invalid／uncertain 零錯放、每類負例命中預定對應原因、非全拒絕。
   同時計 prompt/completion tokens、逐案 wall、median/max；reviewer-only `≤20s`
   只是必要診斷而非產品放行。原版失敗不能自動讓新版 PASS。
4. 若新版任何品質或成本硬門檻失敗，保留 `REVIEW_REQUIRED`、最小反例，停止在此 reviewer
   小修路徑；改審整個兩階段架構，不再用第三個 prompt 或放寬 gold 追分。若元件通過，
   才另凍結全新自然 M51 generation、同候選比較，最後仍須全新 private runtime／Safari
   核對實際日文、來源、node graph、durability 與完整 `≤20s`。任何下層 PASS 不授權產品。

允許的下一工作僅為新研究契約／dataset／scorer／離線 tests／本卡；先 commit freeze，再寫
一次性 runner 與 fake transport tests、另 commit，之後才可送 scored model calls。正式
M55／M56 真人與 holdout 依賴不變。原 dirty checkout、正式私有 DB、已凍結檔、產品
M51/M46/M45/M39、公開 persona 與外部部署均不碰。
