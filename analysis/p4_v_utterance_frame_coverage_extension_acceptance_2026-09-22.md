# P4-V 語境框架偵測覆蓋擴充驗收

狀態：**PASS（shadow detection only）**。P4-U 的可見修復仍未通過，也尚未重新開始。

## 為什麼需要這一步

P4-U 事前規定只有 released P4-T 已報 violation 才能修表面；新資料卻只有 5/12 符合這個前置條件。若直接在修復器內補判斷，會同時改 detector 與 repair，無法知道成敗來自哪一項。P4-V 因此獨立擴充偵測範圍，而且不改可見回覆。

## 唯一變因與結果

新增三種可追溯、raw-free 的抽象訊號：

1. 跨語言行為概念與時間錨點一致時，檢查 user action 是否被改成 agent action。
2. `memo／notice／公告／説明書` 等來源標記與引用區段分開表示。
3. 「只是假設／不是現在決定」與 candidate 是否保留假設框架分開表示。

凍結後結果：

- 已曝光 development 反例：base／extension evidence／effective violation exact=`7/7`。
- 全新中英日 holdout：base／extension evidence／effective violation exact=`9/9`。
- faithful controls：extension evidence exact=`9/9`，false positive=`0/9`。
- candidate逐字不變=`25/25`；raw source/reply trace=`0`。
- 新增 model call=`0`；fact/profile/episode write=`0/0/0`。
- additive product entry、P4-T→P4-V→utterance graph order與三個 predecessor hash均通過。

## 可見例子

| source | candidate | P4-T | P4-V effective |
|---|---|---|---|
| `I will water the white orchid tonight.` | `うちは今夜白い蘭に水をやる。` | 無 violation | user→agent ownership shift |
| `The memo says, "the blue room is closed".` | `青い部屋は閉まってるんだね。` | 無 violation | quote promoted to assertion |
| `Suppose I said "..."; keep that as an assumption.` | `赤いチケットの話は仮定として扱う。` | quote false positive | effective 0；保留 base trace 並由 hypothetical frame 校正 |

最後一列說明這不是只會加警報：新層也能保留舊判定，並以更明確的框架撤銷錯誤警報。實際使用者畫面仍看到原 candidate，因為本步只驗證偵測能力。

## 邊界

這證明的是 developer-authored、有限 action/time/report/hypothetical 規則上的 deterministic shadow coverage；不是開放域語意等價、自然分布準確率、可見修復、felt understanding、人類偏好、強 LLM 優勢或人類方程式。9 個 holdout 已揭露，未來修復不可重用。下一步若做可見修復，必須另立契約並凍結另一批全新資料。
