# P4-W 語境框架保真的可見日文修復驗收

狀態：**PASS（unit／contract／additive product integration）**。真實模型與 Safari 尚需另立前瞻契約，不能由本結果代替。

## 真正改變的行為

P4-W 不再只在 graph 顯示「這句有問題」。它只讀取已凍結的 P4-V effective violations，依 violation 類型修正最後給使用者看的日文：

- `speaker_owner_shift_user_to_agent`：把角色錯接手的使用者行動還給使用者。
- `quoted_content_promoted_to_assertion`：把被提升成事實的內容重新放回引用框架。
- `hypothetical_*`：把假設內容保留為假設，不寫成當前決定。
- `hearsay_stance_dropped + statement_changed_to_question`：恢復傳聞立場與陳述語氣。

repair 不得重新分類 source；沒有 P4-V violation 時嚴格 no-op。P4-T、P4-V 舊 trace仍保留，P4-W只在後面新增 before／after repair node。

## 凍結後結果

- 已曝光 development：before exact=`4/4`、reply exact=`4/4`、after unresolved=`0/4`。
- 全新中英日 holdout：before exact=`12/12`、reply exact=`12/12`、after unresolved=`0/12`。
- faithful controls unchanged=`8/8`。
- Japanese visible output=`24/24`；trace=`24/24`；raw source/reply trace=`0`。
- 新增 model call=`0`；fact/profile/episode write=`0/0/0`。
- additive product entry、P4-T→P4-V→P4-W→utterance graph order與predecessor hashes均通過。

## 前後例子

| 使用者可觀察內容 | 修復前 | 修復後 |
|---|---|---|
| `I will repair the brass lamp this weekend.` | `うちは今週末、真鍮のランプを直す。` | `そっちは今週末、真鍮のランプを直すんだね。` |
| `The manual states, "the orange switch stays down".` | `オレンジのスイッチは下がったままなんだね。` | `「オレンジのスイッチは下がったまま」っていう記載なんだね。` |
| `Assuming I said "I would leave the club"...` | `クラブを辞めるんだね。` | `「クラブを辞める」っていう仮定の話ね。` |
| `Apparently my teacher ordered a purple bag.` | `先生、紫のバッグを注文した？` | `先生が紫のバッグを注文したらしいって話ね。` |

## 邊界與下一 gate

這是 developer-authored、有限 violation families 的 deterministic Japanese surface transform。它尚未證明真實模型會產生同形錯誤、Safari 路徑會啟動修復、自然分布準確率、被理解感、人類偏好、強 LLM 優勢或人類方程式。下一步需凍結一個隔離 product/Safari 合約，用全新 prompt 驗證：真模型候選、P4-V before trace、P4-W changed／after trace、最終畫面與 graph 四者一致；不得拿本批已曝光字串作真實 holdout。
