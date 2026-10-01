# P4-Z source-bound proposition preservation 驗收

## 真正修正的問題

P4-X 證明 P4-W 可以把「引用／傳聞／假設」的外框修回來，但也留下三個反例：引用內文被別的句子取代、傳聞遺失了「弄丟」這個動作、使用者的假設行動被改成角色自己的行動。P4-Z 因此不再只檢查句型標記，而是先從當輪來源的受限文法抽取 `subject / predicate / object / time / location / embedding stance / speaker owner`，再核對最終回覆。

候選回覆不能提供或補完來源欄位；來源不符合受限規則時保持原回覆並明確 abstain。這個層不增加模型呼叫、不寫入事實、profile 或 episode，也不把未支援的複雜語句硬翻成命題。

## 凍結後的結果

- 已曝光 development 反例：exact contract `3/3`、exact repair `3/3`、repair 後零違規 `3/3`。
- 未用於 P4-X／P4-Y 的合成 holdout：中／英／日共 `9/9` exact contract、`9/9` exact reply、`9/9` repair 後零違規。
- 原本就正確的 supported controls：`6/6` byte-preserving no-op。
- 超出規則的 unsupported controls：`3/3` abstain、`3/3` 不改回覆。
- 合成 full-Web graph integration：`3/3` exact logic payload、`3/3` exact graph payload，surface chain 均為 P4-T → P4-V → P4-W → P4-Z → utterance。
- trace 原始 source/reply 洩漏=`0`；新增 model call=`0`；新增 fact/profile/episode write=`0/0/0`。
- frozen gate：`PASS`，failed gates=`0`。
- P4-M～P4-Z 受影響完整回歸：`247 passed`（另有 3 個既有 dependency deprecation warnings）。

## 可見差異

| 類型 | P4-W 後仍錯的輸出 | P4-Z 輸出 |
|---|---|---|
| 引用 | `「今ほしいの…」っていう記載なんだね。` | `「冬季入口は八時に閉まる」っていう引用なんだね。` |
| 傳聞 | `後輩が紫のマグカップらしいって話ね。` | `後輩が紫のマグカップをなくしたらしいって話ね。` |
| 假設 | `うちは朝の電車を取り消すと仮定するんだね。` | `「そっちが朝の電車をキャンセルする」っていう仮定の話ね。` |

## 證據邊界

這次 PASS 只證明三種受限文法與凍結合成資料中的 deterministic proposition preservation，以及 graph delivery。它不是 open-domain 語義理解、自然分布準確率、翻譯品質、人類偏好、felt understanding、強 LLM 優勢或「人類方程式」證據。下一個獨立 gate 必須使用未曝光的真實產品輸入，確認本機模型候選經 P4-Z 後仍能保持來源命題與圖表一致；不能把本次固定合成案例當成真實產品成功。
