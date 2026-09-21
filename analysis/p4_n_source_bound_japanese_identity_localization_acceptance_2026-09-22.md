# P4-N source-bound Japanese identity localization acceptance

## 結論

P4-N offline gate=`pass`。P4-M 暴露的問題不是記憶遺失，而是 P4-J 只會把有限 lookup table 內的 value 轉成日文表面。這次沒有把 `柚子茶` 加進表，也沒有重跑 P4-M；新增的是一個獨立 adapter：只有 active typed record 來自明示日文自述、provenance 完整，而且 value 是 1–24 個 codepoints 的安全日文字串時，才允許原樣出現在日文回答。

## 前後差異

修改前，完整 provenance 的 development value `玄米茶` 仍得到 `unsupported_active_value_localization`，且安全 abstention 不洩漏值。修改後，三個不同構形 `玄米茶`、`ジャスミンティー`、`レモン・ティー` 都得到 `value_surface_strategy=bounded_japanese_identity`；既有 `麦茶` 仍先走 `finite_localization_map`。

以下情況全部保持 abstain，且 contract 不回傳原值：

- 同一日文字值卻標成 English 或 Chinese source；
- ASCII 或日英混合字串；
- 句號後夾帶第二句；
- newline／控制邊界；
- 超過 24 codepoints；
- source kind、epistemic status、typed schema 或 preference semantics 任一不符。

## 為什麼使用 additive adapter

最初設計打算直接改 P4-J，但受影響回歸立刻證明那會破壞 P4-K release 對 P4-J 實作 hash 的歷史綁定。產品修改尚未 commit，也沒有真實回合，因此先恢復 P4-J 到原 hash，再以事前 amendment 把實作移到 `uruha_source_bound_japanese_value_surface_p4.py`。P4-J hash 前後皆為 `dbec8a2cd9a6b4bbc1faeb13add35f1b491e038c0cccb377bcc137bda7750aff`，舊 release 測試重新通過。

## 驗證

- positive development fixtures：`3/3`。
- source／script／length／injection negative fixtures：`7/7`。
- provenance negative fixtures：`4/4`。
- P4-I 到 P4-N、歷史 freeze/result/release 受影響 suite：`166 passed`、`0 failed`；2 個既有 Chroma SWIG deprecation warnings。
- 隔離 product preflight=`ready`，sandboxed import probe=`ok`，server 未啟動，Safari turn=`0`，model／network／production memory／deployment=`0`。
- 第一次 preflight 指令因使用不允許的 `/private/tmp` root，在 product import 前被 launcher fail-closed；已記錄而不算產品失敗。第二次使用 launcher 允許的系統 temporary parent 通過。

## 還沒證明

這只是 offline mechanism pass，尚未證明新 value 真的經過 Web、持久 DB、process restart、英文 query、日文 surface 與 P4-J graph。下一步必須使用未參與上述 development fixtures的新日文 value，先 freeze 再執行一次 no-retry product acceptance。它仍不等於任意 echo、安全翻譯、一般記憶、長對話可靠、felt understanding、強 LLM 優勢或人類方程式。
