# P4 第三方引述／M31 優先序：凍結八輪 Safari 產品結果

## 判定

**整批 strict FAIL／`REVIEW_REQUIRED`，不是 P4 產品完成。** 首輪前
`1ad129c` 已把新 opt-in 程式、新八句/gold、程序和 SHA manifest 推到
PR #435；事後 8/8 manifest 仍相符。兩個 Safari session、同 DB planned
restart，八句各送一次、0 retry，8 個相異 episode；8/8 raw reply＝graph
UTTERANCE，當輪目視泡泡也相同；8/8 等待 ≤20 秒；12 份完整 profile
收據皆 `present/0 rows` 且內容 digest 相同。這些程序與追蹤性門檻通過，
**不能抵銷 T2/T6 的核心可見失敗與 T8 的負控制失敗。**

前批已曝 T3：第三者來源辨識正確，M31 仍獲表面權限並輸出
`先輩が先に確認してと言った`，等待 13.8276 秒，其中 M31 10.8876 秒。
本批的新 opt-in seam 使兩個全新報告句 T2/T6 均有 source/hash/action proof，
M31 `model_call_attempted=false`、`completed=false`；但 **final reported-ack
visible 0/2**。這只證明 M31 奪權點被避免，不證可見行動已修好。

## 逐輪實際結果

| 輪 | 事前測的分支 | 真 Safari 泡泡＝graph UTTERANCE | 最終判定 | user wait 秒 |
|---|---|---|---|---:|
| T1 | 直接要求先問回覆形式 | `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | 路由與可見行動合格 | 3.0233 |
| T2 | 友人完整引述，應承接 | `ん、その話もう少し聞かせて。` | **FAIL**：M31 deferred、selected ack 與 core 正確，最終 guard 改成失去引述內容的泛答 | 12.0191 |
| T3 | 引述後另有直接請求 | `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | 混合來源未錯略過直接請求 | 3.5418 |
| T4 | 使用者自己先查再回覆 | `うん、先に確認してからでいいよ。返事はそのあとで。` | self-defer 合格；其後 planned restart | 10.4998 |
| T5 | 重啟後英文直接請求 | `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | 跨語直接請求合格 | 3.4056 |
| T6 | 母親完整引述，應承接 | `一回止まって聞き返す。そのくらいでいいだろ。` | **FAIL**：M31 deferred 但 protected low-road 的 selected plan 是 `plain_reply`，最終與引述無關且語氣不自然 | 2.8911 |
| T7 | 普通非引文第三人稱敘述 | `先生は来週に戻るんだね。` | 不受新 overlay 侵入，M31/M32 舊路完成 | 14.0916 |
| T8 | 不明確認對象 | `確認ありがとう` | **FAIL**：沒有新 overlay proof，但把要求確認誤讀成「謝謝你確認」；不可稱已釐清或已確認 | 18.8440 |

逐字輸入與事前 gold 見
`datasets/p4_reported_ack_m31_priority_fresh_probe_2026-10-18.json`。
8/8 actor/action/source 及 M25 與事前靜態路由一致；T2/T6 的 M29
當輪 digest、M31 defer 都正確，其他 6/6 沒有新 priority certificate。
T2/T6 actor final audit 均誠實標 `reported_instruction_ack_missing`，
沒有把 graph 的 selected 或 M31 defer 冒充可見成功。T8 是 overlay 未介入
的獨立可見錯誤；無同題 baseline，不歸咎或洗白為新 overlay 的因果效果。

## 失敗定位與成本

- T2 runtime `selected_plan.surface_act=ack_reported_check_instruction_p4`，
  `core_message_jp=そう言ってたんだ。何を先に確認する話？`。在可見語言 guard
  之前卻成為 `そう言ってたんだ。何を先に確認する話？。そのくらいでいいだろ。`；
  guard 因 `malformed_japanese_punctuation` 採通用安全 fallback，最後失去
  source-qualified 對話行動。M39 接到的是 fallback 後的泛答並報 accept；
  這證明「selected 正確」仍不足以保證使用者看見正確回覆。
- T6 `semantic_route=safety_sensitive`、`M21=protected_low_road`、selected
  `intent=short_confusion/scene=casual/surface_act=plain_reply`。原 actor wrapper
  在非 `chat` seed 不選承接；新早期 M31 certificate 尚看不到此 protected
  seed，卻仍 deferred。這違反設計中「protected 路由不略過」的保護意圖；
  不能只補最後一句或聲稱它是正確安全回覆。未從路由證據推斷母親的
  私人心理，也未證明此 protected route 本身是否合理。
- T8 actor=`unknown`、M25/M18 null、新 priority null；M21 full planner
  9.4357 秒、M31 model completed 後 authority rejected，最後
  `確認ありがとう`。這是另一個 unknown-context 語義／延遲風險，與本次
  第三方引述優先序變因分開。
- 八輪 user wait 總 68.3163、平均 8.5395、中位 7.0208、最大 18.8440 秒；
  8/8 在預註冊 20 秒內。raw 明示 M21 完成 3 次一般 planner call，M31
  完成 2 次語意 call，報告句 M31 跳過 2 次；這**不是**所有 runtime 模型呼叫
  的全面核帳。raw 的 `prompt_tokens/completion_tokens=0` 僅屬不適用的
  M45 子模組，沒有本批 M21/M31 可信實際 token 數，不得報零 token。
  前批 T3 13.8276 秒與新 T2/T6 12.0191／2.8911 秒是不同句、不同
  路由和 session，不能拿來估計同題的因果加速；本批 T8 18.844 秒也
  沒有解決前批未知句 23.4192 秒的獨立串行風險。

## 隔離、圖與原件

- 私有 launcher root：
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-1622haaw`；
  raw：`web_logs/conversation.jsonl`，停機後 SHA-256
  `ab52412deaf05e1e5fa9dce08e4d94beb9b4b88ccfbbe5c86061500d044c553d`。
  原件含對話 trace，留在隔離 root，不複製入 Git。
- 0-turn PID 42140 的唯一 loopback／HTTP 200 readiness、planned stop／
  PID exited／port vacant 成立；離線 ONNX 獨立私有副本 83,178,821 bytes，
  SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`
  與套件宣告一致，封鎖下載後得到 1×384 finite embedding，呼叫 0.4309
  秒。首次空 profile setup 因 ONNX 解壓六檔 0644 被安全檢查拒絕，
  僅把此 root 六檔改 0600 後同一未產生 intent 的 setup 成功；receipt
  before DB absent、after 僅 `user_profile` 0 rows、digest
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`，
  setup 1.8503 秒、DB 0→167,936 bytes。這些是明列的設施成本，不是
  對話模型品質。
- T1–T4 Safari session `20261018_044930_f7e2ce3c`，PID 42736；
  T4 後 planned stop，episodes 0→1→2→3→4→4。同 root/DB PID 43365
  readiness 後，新 Safari session `20261018_045309_cbc5c661` 跑 T5–T8；
  episodes 4→5→6→7→8→8。兩 PID 的 stop receipt 均 planned，最終
  controller `stage=exited`、port 7894 無 listener。12 份 full-profile
  收據皆 present、0 rows、同 digest；所有 snapshot 的 user_profile_rows
  皆空，最後 8 個 episode ID 互異。這是隔離 DB 邏輯讀／程序證據，
  不是 OS 級不可寫保證或長期記憶能力的正面驗證。
- 真 Safari 當輪目視每個泡泡與 graph UTTERANCE；raw 可獨立重算 8/8
  logged reply＝runtime blackboard utterance、8/8 exact frozen inputs、2 session。
  沒有操作錄影，raw 不能單獨證明瀏覽器泡泡或 0 retry。T2 的圖顯示
  third-party actor、M31 deferred、selected ack、generic UTTERANCE 並存，
  是可視化差異的失敗例；actor 節點的展開預覽被截斷，完整 final audit
  需看 raw，不能說 UI 已充分呈現所有原因。新開的兩個 Safari 測試分頁
  保留以供檢視；服務已停，分頁不是必要常駐程序，可由使用者關閉。

## 結論與下一步邊界

87/87 零模型聚焦／相鄰回歸、8/8 首輪前 SHA、程式語法、controller CLI
是工程契約證據；本報才是隔離本機真 Safari 輪次。此次是對同一可見
第三方引述失敗的第二個有根據前瞻批次，**仍 FAIL，因此同卡
`REVIEW_REQUIRED`；不重播曝露句、不補第三批詞彙例外追分。**
後續設計審查需分開評估：(a) 在保護路由／初始 seed 已知時才允許
M31 defer 的真正 admission seam；(b) 有來源 selected action 到最終
日文的表面忠實度（含標點與 fallback），不能以通用 fallback 洗掉
可見承接；(c) unknown 確認句與串行延遲是不同工作項。每項都要有
新的正／負控制、成本及新未曝光資料，重大架構選擇先審查。

本批不證明同模型強 LLM 優勢、真人被理解感、正式 temporal holdout、
公開 Uruha 人格的人評、完整 VRM／Function Calling 或人腦方程式。
