# P4-L preference scope canonicalization acceptance

## 結論

P4-L offline implementation=`pass`。prospective regression 在實作前因模組不存在而 collection error；實作後 P4-L contract／freeze=`9 passed`，P4-I～P4-L affected regression=`98 passed`，只有既有 Chroma SWIG deprecation warnings 2 項。這一階段沒有送真實產品對話、沒有模型呼叫、沒有接觸 production memory 或外部部署。

## 問題與單一變因

P4-K 已證明：當 typed record 與 query 都是 canonical `drink` 時，跨 process 回溯可送到正確日文 surface 與 graph。但 P4-I 原本忠實保存抽取到的 scope surface，因此繁中 `飲料`、簡中 `饮料`、日文 `飲み物` 分別形成三個 predicate；P4-J 的三語 query 則都 canonicalize 成 `drink`。結果是同一概念無法 exact-scope join。

P4-L 只改一件事：產品安裝後，已被 P4-I 選中、`scope_source=explicit_utterance`，而且 language＋scope 精確命中 freeze table 的三個別名，才投影為 `drink`。`general` 不依 value 猜 scope，`snack` 等不支援 scope 不變，未選中句子也不變。

## 實作邊界

- 新增 product-only `uruha_preference_scope_canonicalization_p4.py`，安裝順序固定為 P4-I → P4-L → P4-J。
- 不修改 P4-I 與 P4-J 原檔；直接呼叫未安裝的 P4-I 仍維持 frozen 行為，舊 P4-I tests 全過。
- value、value hash、source language、source input hash、act 與 epistemic status 原樣保留。
- typed metadata 使用既有 canonical predicate `current_preference_scope:218ae6b44966c8a9`，另存 alias id 與 source alias hash；不保存 raw alias 或 raw dialogue。
- graph 新增 `preference_scope_canonicalization_p4` memory node，綁定 P4-I current memory id；沒有新增 answer authority 或模型呼叫。

## 可重現例子

安裝 adapter 後，繁中句子的隔離 temporary-Chroma smoke test得到：

```json
{
  "scope": "drink",
  "scope_source": "canonical_alias_projection",
  "predicate": "current_preference_scope:218ae6b44966c8a9",
  "alias_id": "drink:zh-Hant:v1",
  "source_language": "zh",
  "value": "桂花茶",
  "answer_use_authorized": false
}
```

原 value 與 input digest 均未改；typed record metadata 同時保留 `preference_scope_alias_id=drink:zh-Hant:v1` 與 source alias SHA-256。安裝函式第一次回傳 true、第二次 false，避免重複 wrapper。

## 尚未建立

這仍是 offline mechanism evidence。尚未用新 frozen Safari case 證明 Chinese write → restart → English query 的完整產品路徑，也沒有證明任意 scope／語言 ontology alignment、長對話、felt understanding、優於強 LLM 或人類方程式。下一步只能先凍結一個未執行的 P4-L-REAL case；在 freeze commit 前真實輪次維持 0。
