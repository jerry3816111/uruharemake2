# P4 reported-ack A：seed provenance 唯一修正批的 Safari 結果

2026-10-18；**A 的有限路由准入子門檻 PASS，但 reported-ack 產品整體 FAIL**。這是開發者自編、首輪前凍結的八題產品探針，不是獨立 holdout、同模型對照、人評或正式研究放行。首發 A 的 strict FAIL／原件 SHA `1e59785995586f5ea9247a577433d1436fbf6fdd3603eb74dfbaf0b5806d56d7` 不改算。

## 首輪前凍結、隔離與可追溯原件

- code／題目／條件式 gold／計畫／SHA manifest 在首輪前 commit `618c628fef40ac01eac2b272ec48e11e1c3b2f04` 並推 PR #435；最後核 `research/p4_reported_ack_route_admission_seed_provenance_fresh_probe_freeze_2026-10-18.sha256` 為 8/8 OK。零模型聚焦最後版 36/36，較廣相鄰回歸 177/177（9 個既有 warnings）；這些不是 Safari 成績。
- 原件：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-9mchgu11/web_logs/conversation.jsonl`，SHA-256 `9580fd65f4fd4094ae733e9bdcd12fbefba1190e7723c5b009f956cadcd74236`，恰 8 行／八句各一次／0 retry。0700 私有 root，專用 opt-in 本機入口 `uruha_web_ui_product_p4_reported_ack_route_admission.py`。同一入口 0-turn readiness run `6163f3ca13e6b0d8` 同 PID HTTP 200 後 planned stop；隔離 ONNX 副本 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 離線預熱成功，沒有在測試時下載。
- session `20261018_054051_9d2fe36a`／run `264f34fa67e68f77`／PID 55563 完成 T1–T4；planned stop 後原 PID 退出、port 7894 vacant。用**同 root／同 DB** 的 run `745cb2467f5f789a`／PID 57217 重啟，同 PID listener／HTTP 200；Safari 新空 session `20261018_054723_fa841fa8` 完成 T5–T8。最後 planned stop，PID 57217 退出、port vacant；無第三次發送或並行 listener。
- 隔離 profile 的 T0–T8 九份完整內容收據皆 `present`、0 rows、相同 digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；T8 快照有 8 個 distinct episode、0 profile rows。這只驗證隔離 DB 的收據時點，不是 OS 層對正式 DB 的不可觸及證明。

## 八輪真 Safari：條件式 gold 與最後可見句

`cert` 是當輪同 digest 的 M25/P4-AT/M29 source certificate；「原 M31」表示未被 A 略過的既有 semantic call。T1/T5 的早期真無規則命中標記 `no_rule_match` 且 serialized seed 恰 `{}`；T2/T7 有 `matched_rule` 的 protected seed。其餘不適用欄位不可當成功的證明。

| 題 | 當輪來源／route／M22；A→M31 | selected core → Safari 泡泡／graph UTTERANCE | 等待 | 判定 |
|---|---|---|---:|---|
| T1 朋友轉述 | cert true；`no_rule_match + {}`；high/deliberative、general；**admitted → deferred、原 M31 0** | `そう言ってたんだ。何を先に確認する話？` → `ん、その話もう少し聞かせて。` | 10.0361s | A 正例通過；B 可見承接失真 |
| T2 妹的轉述 | cert true；protected seed、low/prediction-error、safety；**rejected → 原 M31 1** | `妹の確認ってことか` → 同句 | 13.5381s | A 保護側通過；沒有捏造私人事實 |
| T3 引述＋當前直接要求 | 單句 cert 不成立；high/general；M31 不適用、無 defer | 當前要求先問回覆形式 → `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | 3.5659s | 直接要求未被引文吃掉 |
| T4 集合時間變動 | cert false；high/general；not source candidate → 原 M31 1、無 defer | `集合時間が急に変わったんだね。` → 同句 | 10.2126s | 沒有把非引述當 reported-ack |
| T5 老師轉述（重啟後） | cert true；`no_rule_match + {}`；high/deliberative、general；**admitted → deferred、原 M31 0** | `そう言ってたんだ。何を先に確認する話？` → `「ん、その話もう少し聞かせて」っていう記載なんだね。` | 12.2960s | A 正例通過；B 嚴重失真，錯引舊回覆 |
| T6 沒提供過的號碼 | cert 不適用；high/factual_or_memory；M31 不適用、無 defer | `少しくらいは思ってる` → `前に:先生は「まず先に確認して」と言った。って言ってたろ。` | 2.8185s | 沒捏造號碼／沒錯 defer，但記憶問答焦點失敗，日文冒號不自然 |
| T7 同事轉述 | cert true；protected seed、low/prediction-error、safety；**rejected → 原 M31 1** | `一回止まって聞き返す` → `今ちょい力抜けてるけど、そこは普通に返せる。` | 13.7662s | A 保護側通過；可見回覆與事件不相稱 |
| T8 未定確認對象 | cert false；high/general；not source candidate → 原 M31 1、無 defer | `まだ決めてないんだね。` → 同句 | 19.8950s | 沒錯 defer／沒編對象；距 20 秒門檻很近 |

每輪當下實際查看 Safari 泡泡與 runtime node graph 的來源、M22、selected、M31 與 UTTERANCE；8/8 目視泡泡等於 graph UTTERANCE，且 8/8 raw `assistant_reply` 等於 blackboard `utterance.payload.reply`。沒有錄影或逐輪截圖，Safari 目視本身不能從 JSONL 獨立重算。所有回覆以日文為主，但 T5／T6 等不符合自然且忠實的產品要求。

## 嚴格判定與下一個單一變因

- A 的預註冊子門檻：來源完整、普通 high-road 真空 seed **2/2 admitted 且原 M31 0**；來源完整 protected／low-road **2/2 rejected 且原 M31 1**；四個負控制 **4/4 無錯 defer**。8/8 user wait ≤20 秒，平均 **10.7661 秒**、最大 **19.8950 秒**；八 episode、兩 Safari session、同 DB restart、profile 0 rows／digest 不變、服務完整啟停皆符合。故只稱 **A 有限准入 PASS**，不是所有報告句或所有安全情境的普遍保證。
- M21 一般模型完成 3 次，原 M31 semantic call 完成 4 次，A deferred 2 次；本原件沒有可核實的**整輪實際 token 數**。M45 某些 0 token 欄位及 `max_output_tokens=256` 不代表整輪用量；實際 token 記 `unavailable`。
- **reported-ack 產品整體 FAIL**：T1/T5 即使 selected action/core 對，最後兩句都沒有按選中的第三者指令承接；T5 還把先前 generic 回覆當新引文。T6 的記憶問答也未回答問題，T7 的最後句不相稱。A 的路由修正不能代替 B 的 selected→visible fidelity，也不能解決 T6 記憶或 C 的近門檻延遲。
- 下一個必要且獨立的設計項是 **B：selected reported-ack action/core 如何在所有後段 guard 後忠實、自然地成為最終日文**。先以本批 T1/T5 作只讀 before 定位，確定一個最小因果點、保護負控制、全新未曝光題與單一變因；凍結／審查後才實作，舊題不回放追分。T6 記憶與 C 性能另卡，不能塞進 B。兩次 A 批次的結果（一敗一有限通過）都保留。

本批不能證明相對強 LLM 優勢、人類被理解感、正式 temporal holdout、完整 VRM／Function Calling、公開真人人格忠實度或人腦方程式；Goal 仍未完成。
