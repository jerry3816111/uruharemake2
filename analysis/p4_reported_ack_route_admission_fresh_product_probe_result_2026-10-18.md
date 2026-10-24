# P4 reported-ack M31 路由准入 A：首發八輪 Safari 結果

2026-10-18；**整批 strict FAIL / REVIEW_REQUIRED**。這是開發者自編、首輪前凍結的產品探針，不是獨立 holdout、同模型對照或人評。前兩批失敗仍有效；本批不重算它們的 pass。

## 凍結與隔離

- 首輪前 commit `c1ee0ec` 已推到 PR #435；`datasets/p4_reported_ack_route_admission_fresh_probe_2026-10-18.json`、code、plan 與 `research/p4_reported_ack_route_admission_fresh_probe_freeze_2026-10-18.sha256` 事先凍結。八題各送一次，0 retry，未事後改題或 gold。
- 原件：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-usl08bw8/web_logs/conversation.jsonl`；SHA-256 `1e59785995586f5ea9247a577433d1436fbf6fdd3603eb74dfbaf0b5806d56d7`。root 是本次新建的私有 0700 目錄，不是正式 DB。
- 0-turn 同入口 readiness 後 planned stop；私有 ONNX archive 離線預熱與顯式 0-row profile setup 成功。正式生成在 session `20261018_052041_62c77edc` 跑 T1–T4；T4 後同 root／同 DB planned stop，第二個 session `20261018_052455_1e224b9b` 跑 T5–T8。第二次 start 曾因第一個 start 尚在預檢而被重複發出；後者明確拒絕 `localhost_port_not_vacant:7894`，沒有第二個 listener 或新增對話。有效重啟是 run `a9a0639b5d34e8fb`、PID 51820，same-PID HTTP 200 核對通過。結束時 planned stop、PID exited、7894 port vacant。
- T0 及 T1–T8 共九份完整 profile 收據皆為 0 rows、相同 digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；八個 distinct episode ID。這只能證明本隔離 DB 在收據時點未新增 profile fact；非 OS 層正式 DB 不可觸及證明。

## 真 Safari 逐輪核對

| 題 | 實際路由／M31 准入 | 最終可見回覆 | 等待 | 判定 |
|---|---|---|---:|---|
| T1 姉的轉述 | high／general；來源證明有；seed 空，A 拒絕，原 M31 | `ん、その話もう少し聞かせて。` | 22.3399s | A 正例未覆蓋；可見承接不足；超時 |
| T2 父的轉述 | protected low／safety；來源證明有；A 拒絕，原 M31 | `一回止まって聞き返す。そのくらいでいいだろ。` | 13.5739s | A 負例通過；回覆品質另列 |
| T3 引述＋直接要求 | high／general；無單句來源證明；M31 不適用 | `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | 3.4803s | 沒有錯 defer，直接要求保留 |
| T4 非引述 | high／general；無證明，原 M31 | `先輩の予定は来週に変ったらしいんだね。` | 10.3587s | 沒有錯 defer |
| T5 後輩的轉述 | high／general；來源證明有；seed 空，A 拒絕，原 M31 | `後輩がまず先に確認してと言っていたんだね。` | 10.0431s | A 正例仍未覆蓋；後段 M32 修復不算 A |
| T6 記憶題 | high／factual_or_memory；M31 不適用 | `:後輩が「まず先に確認して」と言っていたって話は拾ってる。そこ前提で返す。` | 3.1118s | 沒錯 defer，但記憶焦點錯且前導冒號不自然 |
| T7 兄的轉述 | protected low／safety；來源證明有；A 拒絕，原 M31 | `一回止まって聞き返す。そのくらいでいいだろ。` | 9.7661s | A 負例通過；回覆品質另列 |
| T8 對象未知 | high／general；無證明，原 M31 | `確認するんだね。` | 19.0083s | 沒有錯 defer，未捏造確認對象 |

每輪實際看了 Safari 泡泡、當輪 runtime node graph 的 source／M22／selected／M31／UTTERANCE，並與 JSONL 原件交叉核對；8/8 `assistant_reply` = blackboard `UTTERANCE.reply` = 當輪目視泡泡。Safari 目視未保存影片或截圖，不能由 JSONL 獨立重算。八輪皆有日文主體，但 T6 的冒號及內容錯位不符合自然日文／正確記憶的可見品質要求。

## 可量化門檻與因果定位

- A 要求至少一個完整普通 high-road 轉述准入：**0/2**（T1/T5 都拒絕）；至少一個來源完整 protected／low-road 轉述拒絕：**2/2**（T2/T7）；負控制沒有 reported-ack 錯 defer：4/4。故不可稱 8/8 A pass。
- 每輪 user wait ≤20 秒：**7/8**；平均 11.4603 秒，最大 22.3399 秒。M21 completed 2 次，M31 model completed 6 次、deferred 0 次。本原件沒有可信數值 token 消耗欄；底層 ledger 的 `actual_usage_recorded_by_underlying_ledger=true` 不等於本批可核對 token 數，記 `unavailable`。
- 根因不是第三者來源辨識缺失：T1/T5 的 actor/source/action certificate、actual `chat/casual`、high-road deliberative、M22 exclusive general 都存在。`_rule_based_plan` 沒有命中時回 `None`，`classify_user_signal` 把 seed 序列化為 `{}`、同時把 actual intent/scene 預設為 `chat/casual`；A 契約卻要求 seed 內明寫這兩個值，故拒絕。T1 final generic 與 T6 記憶失真是不同後段問題，不能用修 A 宣稱一併解決。
- 失敗保留。若進行計畫允許的唯一有根據修正批，應在 seed 被轉成 `{}` 前顯式標記「確實沒有規則命中」；A 只在 marker、空 seed、actual、high route、M22、source certificate 全部一致時准入。缺 marker、缺 seed、矛盾或保護路由仍回原 M31；另用**新未曝光**題及事前凍結驗證，不重播本八句追分。B（selected→visible）與 T6 記憶、C（未知／延遲）各自另卡，不能算在 A 成果。

## 證據界線

零模型聚焦＋相鄰 105/105 證明靜態契約；本次真 Safari 證明在所列八個實際輪次，A 保護側有效、正例沒有進入預期路徑且超時一輪。這不支持 reported-ack 產品 PASS、對強 LLM 的優勢、人類被理解感、正式 temporal holdout、VRM／Function Calling 的整體交付，更不是人類反應方程式已解。
