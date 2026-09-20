# P3-B74 isolated two-coder collection site acceptance

日期：2026-09-20

## 結論

`SYNTHETIC SITE READY / SAFARI VISIBLE / HUMAN RELIABILITY NOT STARTED`。B74已把B73契約做成可操作的localhost網站，
但目前18題全是synthetic fixtures，不能算真人標註或真實Uruha資料。

## 實際證據

- 20/20 affected tests passed：HTTP GET/POST、錯誤表單fail-closed、unknown token 404、重啟保存、cross-coder isolation、完整分析。
- Safari新增1個分頁並實際看到頁名`UruhaBrain B74 coder`、synthetic警告、stimulus、response與所有標註欄位。
- Safari實際提交一題後進度由`0/18`變`1/18`。
- private root mode=`0700`，兩份ledger=`0600`；提交後entry counts=`[1,0]`，證明沒有自動複製到另一coder。
- 另一個完整18×2 synthetic run的四個primary alpha均為`1.0`，但結果仍明確設定
  `synthetic_fixture_authorizes_human_reliability=false`與`real_source_prediction_authorized=false`。

## 使用者現在不需要做的事

目前頁面只是在驗證工具，不需要使用者填滿18題。真正需要真人時，必須先前瞻凍結18個real stimulus→response packets；之後只需
使用者與另一位不同真人各做同一組18題，不是找大量受試者。兩人可靠度仍只驗證codebook能否一致使用，felt-understanding preference
是之後另一個實驗，不能混在這個gate。

## 限制與下一步

B74沒有讀新來源內容、沒有模型呼叫、沒有真實human label、沒有production memory write。下一步先凍結real packet sampling frame與
來源選擇規則，確認每個episode真的有可辨認的stimulus→Uruha response boundary；不能再用任意固定秒窗代替對話事件。
