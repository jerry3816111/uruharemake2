# P4 時序行為者／作用域：凍結新題真產品結果（2026-10-18）

## 判定

**整批 strict FAIL，不能稱產品驗收通過。** 首輪前在 `e156459` 凍結的 8 題、gold、
產品碼與程序未因結果修改，manifest 9/9 仍相符。八題各由真 Safari 送出一次，
分為兩個 session；T4 後同一隔離 DB planned stop/restart。T3 的第三者引述沒有錯誤
觸發 `calibrate_need`，但 M31 下游覆蓋了預期的承接行動，最後只留下不完整重述；
T7 等待 23.4192 秒，超過事前 20 秒上限。這兩個失敗獨立存在，不用其餘六輪
的成功消除。

此前七輪 T3 把「使用者自己先確認、稍後回覆」錯當成「助手先詢問使用者需要
何種回覆」。本批的單一產品變因是 opt-in 的 actor/source/action/time seam；
它能分開上述兩者，也保留第三者引述與不明歸屬，但尚不能保證最終回覆忠實
執行已選行動，亦沒有解決獨立的慢路徑成本。

## 凍結輸入、可見輸出與判定

| 輪 | 事前角色／動作 | Safari 泡泡＝graph UTTERANCE | 機制／可見判定 | 等待秒 |
|---|---|---|---|---:|
| T1 日 | 使用者自行先查再回覆 | `うん、先に確認してからでいいよ。返事はそのあとで。` | self-defer 正確 | 10.9001 |
| T2 日 | 直接要求助手先問回覆形式 | `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | `calibrate_need` 正確 | 3.3165 |
| T3 日 | 報告先輩的引述，不是當輪命令 | `先輩が先に確認してと言った` | **FAIL**：actor 正確為 third_party，但 selected act 被 M31 換成 literal-topic 重述；不是自然承接 | 13.8276 |
| T4 英 | 使用者自行查車次再回覆 | `うん、先に確認してからでいいよ。返事はそのあとで。` | self-defer 正確 | 13.1613 |
| T5 中 | 直接要求助手先問回覆形式 | `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | `calibrate_need` 正確；跨重啟新 session | 3.3000 |
| T6 中 | 使用者自行查車次再回覆 | `うん、先に確認してからでいいよ。返事はそのあとで。` | self-defer 正確 | 12.5478 |
| T7 日 | `先に一回確認して。`，歸屬不明 | `確認してから話すよ。` | unknown、未假報 `calibrate_need` 或已查；承接較弱，且 **23.4192 秒超時** | 23.4192 |
| T8 英 | 直接要求助手先問回覆形式 | `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | `calibrate_need` 正確 | 3.7491 |

逐字輸入與事前 gold 見
`datasets/p4_temporal_actor_scope_fresh_probe_2026-10-17.json`。T7 的句子不宣稱
已完成確認，可按寬鬆的承接標準接受，但它沒有釐清要查什麼，不是值得宣稱的
「被理解感」成功。八個泡泡與 graph 的逐輪相等及 0 retry 為 Safari 當輪操作
觀察；私有 raw 可獨立重算 raw reply＝runtime blackboard utterance 8/8，不能
單靠 raw 證明瀏覽器實際泡泡或操作次數。

## 可重算機制與失敗定位

- 8/8 `user_text` 逐字等於 frozen inputs；actor/action/source、M25 與 M18
  policy 均符事前 gold；8/8 actor node 在 M25 前。self-defer 3/3、直接助手
  請求 3/3、不明歸屬 1/1 未被誤升級。
- T3 `temporal_actor_scope_p4.status=reported_check_instruction_not_direct`，
  `M25=null`、`M18=null`，但最終
  `selected_plan.surface_act=semantically_authorized_literal_topic_m31`，不是 frozen gold
  `ack_reported_check_instruction_p4`。M31 `plan_applied=true`，模型語意審核
  用 10.8876 秒；新節點最終如實標 `reported_instruction_ack_missing`。
  M31 本身的 `surface_self_checks` 另有 faithful/subject/predicate=false，
  故不能把「有 source-first 審核」等同最終自然回覆正確。
- T7 `actor=unknown/action=unresolved`，M25/M18 均 null；M21 full planner
  9.5932 秒，加上 M31 semantic call 10.7653 秒且最後被拒絕，M19 使用者
  實等 23.4192 秒。這是串行成本及沒有及時回退的產品反例；不能把
  `M21` 單段的 completed 誤報成整輪達標。
- 7/8 輪在 20 秒內；等待總和 84.2216、平均 10.5277、中位 11.72395 秒。
  M21 記錄 4 個完成的一般 planner 呼叫，M31 另記錄 2 個完成的語意呼叫；
  這不是整個 runtime 所有可能 model call 的全面核帳。raw 中實際 token
  欄位不可用，不能以零值推稱零 token，亦不能主張同模型成本優勢。

## 隔離、持久化與來源

- launcher-owned 私有 root：
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-coyug8rh`。
  raw：`web_logs/conversation.jsonl`；停機後 SHA-256
  `5402089aeec6902ce62d99908bdd8fa250086bd9f8db2857746804abac38f0cb`。
  原件留在隔離 root，未把含對話 trace 的 raw 複製入 Git。
- 兩個 Safari session ID 為 `20261017_234917_d530589a`、
  `20261018_031324_70d29f8b`，各四輪。首個 PID 8791 planned stop 後退出、
  7894 port vacant；中途 Codex 額度中斷的啟動請求沒有留下新產品程序或
  新對話 log，確認後以同 root 新 PID 29990 重啟；其同 PID listener／
  HTTP 200 readiness 通過，最後 planned stop 同 PID 退出、port vacant。
  未重送 T1–T4 或重播失敗題。既有 Safari 分頁未關閉。
- `evidence/` 內 12 份 T0／每輪／停機／重啟／終停的 full-profile 收據均
  `collection=present`、0 rows、相同全內容 digest
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。
  episode IDs 為 0→1→2→3→4→4→4→5→6→7→8→8，最終 8 個互異 ID。
  snapshot helper 是隔離 DB 的邏輯讀，不能單獨證明 OS 級不可寫；
  0-row profile 也不是長期記憶能力的正面證據。
- 官方 SHA 的 83,178,821-byte ONNX archive 以私有副本在離線 sandbox
  預熱，一次 1×384 embedding readiness 成立；這是設施準備，不是新題
  的生成品質證據。

## 證據邊界與下一個必要工作

零模型 21/21 聚焦、40/40 相鄰測試及 freeze SHA 是工程／契約證據；
本報八輪是本機真 Safari／opt-in 產品證據，但開發者事前自編新題，並非
獨立 formal holdout、同模型 LLM 對照或真人偏好。不能推論「一般 LLM
做不到」、公開 Uruha 人格已獲人評、過去／現在／未來方程式成立，或完整
VRM／Function Calling 已驗收。

下一個**單一因果變因**應先做只讀設計審查：在已辨識 third-party report
且無其他獨立當輪任務時，讓已選的 reported-ack action 在 M31 語意授權後
仍能被最終 selected/final 保留；需同時保護一般 literal-topic 正例、直接
助手請求、使用者自行延期、引文後另有獨立任務及 unknown。不可編輯或
重播此八題／舊七題追分；後續以全新未曝光題、首輪前凍結後再驗。
T7 的串行 latency 是另一個必修的性能變因，另卡處理，不與 T3 修正合包。
