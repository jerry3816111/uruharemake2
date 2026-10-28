# P4 B2 受限動作編譯器：模型前契約結果

狀態：**離線結構契約通過，但獨立只讀審查找到仍開放的語義反例；B2 維持 `REVIEW_REQUIRED`，未 freeze、未送新模型、未接產品**。這不是新 action 成績或 Safari 驗收。舊 B1 正式 valid `0/9`、invalid safe abstain `9/9`、來源綁定理由 `0/9` 不變。

## Before → 這次唯一介面修正

Before：原 B2 proposal 讓候選同時自填安全用的 `operation_keys` 與另一份真正會給人的日文 transaction。合成反例把 key 寫成「加標題」，日文卻寫成「在卡片畫圖」；來源明禁畫圖，B2 與 B1 兩個機械守門仍同時綠燈。虛填 `prerequisites` 也可在來源材料齊全時取得原守門綠燈。這些是**可重現的契約缺陷**，不是模型對照分數，詳見前一份 pre-model review。

新增 `p4_action_task_alignment_v2_compiler.py` 把候選可提交的形狀收窄為一個 typed decision：五種有限動作（移動一物、照抄來源值、圈一物、立起一物、加空標題）或來源綁定 abstain。模型不能提交日文 instruction、object、verb、effect、stop；它們由同一操作的固定模板產生，再交給**未改動的 B1 guard**。未知操作、額外日文欄位、未綁定所選可用素材的 target、無來源支持的 blocker 均擋下。每條 frame 中的禁令皆在 sidecar 核對；因 B1 只能錨一條，transaction 只放確定性選出的第一條，且 sidecar 明標 B1 不是全量禁令證明。`deliverable` 固定 `false`。

這是 source-frame→typed-decision→deterministic surface 的**整體介面變因**，不能把 compiler 與 blocker 個別宣稱因果優勢；也沒有解決模型 frame 誤解請求、漏看禁令、把可用素材錯標缺席的語義問題。

## 觀測與界線

- 合成寫標題 action：編譯後舊 B1 `would_deliver=true` 且 M39 surface `accept`；畫圖指令不能作為 decision 欄位注入，未知 `draw` 操作被拒，來源禁畫的 `circle` 衝突被拒。
- 合成假 `prerequisites`：可用卡片時被拒；frame 明示缺席且 blocker 引用同一素材時，結構上可形成 abstain。後者只證明欄位相符，不證明來源真的缺材料。
- 六件**已曝光、開發者撰寫**的 valid dev 題，以人工建立的 source-exact frame 覆蓋五種模板並通過 B1/M39；沒有讓模型產生 frame，也沒有獨立判讀最終指示是否符合 gold，不是 `6/6` 研究品質結果。
- `C-4` 保持在內部逐字來源欄位，不偷換全形字元；舊 B1 日文 guard 排斥 ASCII，模板只指向「原文的值」。這避免無聲改值，但如果來源有多個值，對使用者的指示可能不夠明確，**尚待解決／驗收**。
- 多條禁令在 sidecar 全量核對，卻仍依賴模型提供正確禁令與 scope；B1 的單一錨點不能被冒充成全量驗證。沒有產品接線，無使用者可見 action。

獨立只讀複核找出三個必須保留的**紅色語義 gate**，現已用測試忠實記錄，不把測試通過誤報成問題解決：

1. 來源要求「在空白卡片加一個標題」，typed decision 卻選已知的 `move_one_item`，並把同一句請求誤當移動目的地證據；compiler 得 `compiled_action`、B1 `would_deliver=true`，生成的日文宣稱移到原文指定的列，但原文沒有任何列。
2. 來源同時有開場 cue `C-4`、結束 cue `D-5`，要求抄開場 cue；typed value 選 `C-4` 或 `D-5` 均得 `compiled_action`、B1 綠燈，且兩者日文 instruction 完全相同。值只留 sidecar，尚未保證 visible action 表達正確選擇。
3. 來源只禁畫圖、允許寫標題，typed abstain 卻用該禁令作 `forbidden_action` blocker，得 `compiled_abstain`；exact 引文不等於禁令真的阻擋請求。這是 false-abstain，不可用全拒假裝安全。

另外 `reason_code=[]` 曾造成 `TypeError`；現已加型別提前拒絕與四個非字串回歸。前三項是**研究／介面設計未閉合**，第四項是已修的程式穩定性缺陷。`deliverable=false` 讓上述綠燈沒有直接進產品。

聚焦＋相鄰回歸命令：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_action_task_alignment_v2_compiler.py test_p4_action_task_alignment_v2.py test_p4_action_task_alignment_v2_dev_data.py test_p4_action_transaction_scoring.py test_p4_action_transaction_b_observation.py test_p4_action_transaction_freeze.py
63 passed in 1.02s
```

0 新模型呼叫、0 新 scored case、0 Safari/Web、0 正式 DB 寫入。**此時不可直接實作 runner、寫 sealed 題或送 18 題。**下一步先設計審查這三個紅 gate：如何把 known operation 與 requested change、值／目的地與可見指示、禁令與實際請求作可反駁的一致性驗證；保留獨立 source-only 評分，不能用模型自己填的 frame 當真值。若不能在有界語法和既有 B1 安全邊界內閉合，維持 `REVIEW_REQUIRED` 並改做另一個已有 before 的必要產品 gate，不得靠放寬 B1 或改弱 baseline 取得綠燈。只有這些模型前反例關閉，才重啟 B2 prompt/schema/runner、fake transport、新 sealed source-only gold、事前 hash freeze 及一次性同模型比較。
