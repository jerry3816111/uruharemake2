# M48：內部動作落到最後一句，但上游任務理解仍可能錯

日期：2026-08-29。安全 worktree、opt-in Web 入口；M47 與 M46 凍結證據不改寫。
結論：**surface realization contract PASS；source-aligned practical-help pipeline FAIL**。

## 這一個 M 改什麼

M47 已讓「要方法／不要方法」正確進出 M46，但正式正向案例 0/3 交付。其中一類錯誤不是
沒有內部動作，而是 `action_object_jp/action_step_jp/completion_jp` 已形成，最後一句卻漏掉
exact object 或 visible stop。M48 只修這一層：

`既有 action fields → bounded Japanese realization → 原 M46 content/surface review → delivery`

它不選 task、不選 progress mechanism、不新增排序規則或工具，也不放寬 M46 reviewer。
semantic fields 前後保持不變；完整 repair 狀態只進當輪 trace，不寫 long-term person model。

## 安全邊界與開發失敗

- 只有 pre-violations 全部屬 `missing object／missing stop／invalid visible Japanese／formal surface`
  才有 repair 權限。nonprogress、task relabel、invalid internal fields、缺 object binding 全部拒絕。
- repair 優先保留原 instruction；無法保留時才從 already-formed action step 實現既有動詞，
  再加只指向該既有動作完成的停止句。reviewer 看不到 M48 私有 trace，仍獨立審核。
- 第一版程式有 unmatched parenthesis，首次測試 collection error；修後 fixture 又因測試直接
  傳未經 M45.1 分句的 source ID 造成3 fail。兩者均未冒算能力失敗或通過。
- 首次真 Safari 的 planner 回傳 `action_verb_jp=分けよ`；第一版只接受 dictionary-form
  inflection，因此 repair fail closed。加入「已實現短命令保持原操作」後，28/28 focused 通過；
  但同一中文案例仍因 action step 沒含 declared object 而正確拒絕，沒有硬塞物件。

## 測試

- M48＋M46＋M47 focused：**28/28**。包含 surface-only repair、semantic fields unchanged、
  reviewer 仍可否決、nonprogress 不修、missing binding fail closed、valid surface不改、形態、
  graph/card 與 reviewer payload 不含 M48 private trace。
- M16–M47 選定39檔加 M48：**284/284，41.94秒**；3個既有依賴警告。不是全歷史 suite。
- `git diff --check` 通過；正式兩個 Chroma DB hash 未變。

## Safari 七輪真實結果

正式 session `20260829_221224_2ffcdcb6`；六個 practical-help 加一個 no-method：

| 輪 | M48 | M46 | 誠實判定 |
|---|---|---|---|
| 中文信件／收據 | internal object binding 不一致，fail closed | reject | 上游 plan FAIL |
| 日文依顏色分紙 | nonprogress＋task relabel，禁止修 | reject | 上游 plan FAIL |
| 英文放錯堆的收據 | nonprogress，禁止修 | reject | 上游 plan FAIL |
| 英文空白報告 | surface 原已有效，not needed | delivered | bounded author 看來有小幅進展 |
| 英文下載資料夾 | internal Japanese/Latin fields invalid | reject | 上游 plan FAIL |
| 日文三個見出し | 缺 stop，M48 真實修補1次 | delivered | **source alignment FAIL** |
| 日文不要方法 | M48/M46 不介入 | listen | 非 help 回歸保留 |

M48 真實 repair 的可見句為：
`見出しと導入文を書いてみよ。それができたら、そこで止めよ。`

trace 顯示 object/operation/stop 全部可見、semantic fields unchanged，M46 proxy 內容／日文皆通過。
但使用者原文要求「見出しを三つ」，上游 plan 改成「見出しと導入文」。作者未盲檢查判定
這不是同一目標；因此 M46 的 same-model review 是 false accept。M48 surface repair 自身成功，
卻不能把錯 plan 變成好回答。

七輪 trace 7/7、日文7/7；M48 repair 1且契約1/1，not-needed 1，fail-closed/block 4；M46
交付2/6，作者 bounded source alignment 只1/2。六個 help 路徑共8次完成模型呼叫、6678 prompt
＋1863 completion tokens、M46/M48 path累計99.70422秒；速度仍不合格。

## 圖像證據

- `m48_safari_repaired_delivery_card_2026-08-29.jpeg` 是 Safari 顯示的 frozen real turn-6 trace：
  M48、M47、M46 三張卡同時可見。頁首明說不是重新生成或新成功輪。
- `m48_actual_turn6_observatory_2026-08-29.html` 直接由保存的真 Web JSONL turn6 runtime trace
  渲染；可檢查來源輸入、實際輸出、M48 surface repair 與 M46 false-accept chain。
- 正式七輪及首次 imperative failure raw 均另存 gzip，沒有用重播覆寫首次結果。

## 完成與下一步

M48 真正完成的是：**已形成的同一動作不再因最後一句漏 object/stop 而必然丟失；修補權限
受到明確內容邊界限制，且實際 Web 至少觀察到一次 repair。**

未完成的是 source-qualified task handoff。M47 其實已在 `task_spans` 找到「見出しを三つ」與
「色ごとに分ける」，但 M45.1/M46 只把不含 response-form 的獨立 clause 當 task source，
所以嵌在「請給一步」同句裡的 task constraint 沒交給 planner/reviewer。下一個單一變因 M49
應把 M47 已驗證的不重疊 task spans 安全交給 M46；不改 M48 surface、M46 reviewer 或答案。

