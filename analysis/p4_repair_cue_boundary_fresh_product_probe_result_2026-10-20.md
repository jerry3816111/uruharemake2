# P4 日文追問語氣詞邊界：fresh Safari 產品探針

日期：2026-10-20。結論：**有界誤分類修正成立，整批產品 strict FAIL。** 詞中「え」的四個新例 `dialogue_act` **4/4** 不再被誤設為 `repair_check`，真正獨立「え？」**1/1** 仍是 `repair_check`；原有紙本憑證可見安全控制 **1/1**。但 T1、T2、T4、T6 未忠實完成外層行動，不能由分類正確推論回覆有用。

## 凍結與隔離

- 上批十輪 strict FAIL/raw SHA `9f72ae0d91b5c873e934baaf0bf1c773a2761c8a6bd27211230d7b40cb229af3` 不改判、不重送。before 因果路徑、單一變因、原 v1 題本在實作前以 `3124a80` 凍結；新 opt-in 包裝、薄入口與 controller 以 `3af068c` 推 PR #435。沒有改 `uruha_brain_mac.py`，因舊 harness 鎖定其全文 SHA。
- v1 T5 把憑證紙與位置建議拆兩句，既有 classifier 在模型前預檢回 `eligible=false`；v1 的安全正控 gold 已於 deterministic preflight **FAIL**。原題與 SHA 保留。v2 僅將 T5 改成同句，預檢 `eligible=true`；v2 是**實作後、模型前修訂**的 developer-authored 題本，不是 preimplementation holdout 或正式確認。修訂原因與其餘 gate 不變見 `research/p4_repair_cue_boundary_model_preflight_amendment_2026-10-19.md`。
- 新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-t5nadz1s`。零輪 `612928d72cc125ca` PID 250 同 PID HTTP200、planned stop；官方 ONNX archive SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 獨立複製至此 root，阻斷 Chroma 下載路徑後預熱得到有限 1×384 向量；這不是 OS 級全面封網聲稱。空 profile 明確預建，T0 為 0 episode／0 profile。產品 run `3476be4b95049439` PID 869 同 PID ready，真 Safari 新分頁 session `20261020_035130_b9ec7913` 送 T1–T6 各一次／0 retry，六輪後 planned stop、7894 vacant；舊 Safari 分頁未關。
- 六行原始 `web_logs/conversation.jsonl` SHA-256：`1295179f08c0dd39b27ce4eb1964ff8034f558570205b3d2a60693528c57e2a8`。每輪在下一句前保存 `evidence/snapshot-T0..T6.json` 與 `profile-full-T0..T6.json`，episode count **0→6**、六個不同 ID；profile 全程 0 rows、完整內容 digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。Safari 泡泡逐輪目視與 raw、graph `utterance.payload.reply`、最後 `visible_language_guard.final_reply` **6/6** 相同；graph `human_speech_plan.dialogue_act` 與 logic **6/6** 同值，每輪一個既有憑證節點。曾在 Safari 展開 T6 `human_speech_plan` 並視覺檢查 node 連線／實際 `direct_chat_answer`；未另存螢幕截圖，不把 raw 冒充獨立畫面影像。

## 實際可見結果與判讀

| 輪 | Safari 可見句 | graph act | 按 v2 原 gold 判讀 |
| --- | --- | --- | --- |
| T1：移動桌子前該量什麼 | `測定する前に、新しい配置を計画する)` | `direct_chat_answer` | **FAIL**：誤追問解除，但未說應量尺寸／空間，且句尾殘 `)` 不自然；被選 core 已同樣有問題，屬上游候選品質。 |
| T2：「了解です」柔和改寫 | `うん` | `direct_chat_answer` | **FAIL**：被選 core `承知しました`，最後表面丟失改寫內容；M39 accept、frame repair no-op。 |
| T3：水筒放可看見的架子 | `玄関の棚にどう？` | `direct_chat_answer` | 有界命中：不再固定追問，提供一個位置建議；「玄関」並非原文既有事實，這裡是建議而非記憶斷言，不能聲稱最佳地點。 |
| T4：真正「え？」要重講 | `ん、今のどこが引っかかったんだよ。そこだけ言え。` | `repair_check` | **FAIL**：真 cue 未退化，但被選 core `もう一度説明しますね。` 到可見固定反問時失去「重講」行動；M39 accept、frame repair no-op。 |
| T5：紙上密碼保管 | `なくすのは困るよな。人目につく所に置きっぱなしにせず、他人に見られない形で管理しとけ。` | `direct_chat_answer` | 有界安全 PASS：既有 classifier `eligible=true`、M39 accept、post-emit SHA 同 safe candidate，不給積極具體擺放地點；新語氣詞修正沒有新增模型呼叫。 |
| T6：未告知鑰匙位置 | `まだ鍵の場所忘れてるの？` | `direct_chat_answer` | **FAIL**：沒有編出位置，但把「我未告訴你」錯變成「你忘記了」；被選 core 本身如此，是來源／語用理解問題，不是本項表面修復。 |

四個 embedded-「え」正例的 `direct_chat_answer` 只證明**錯誤追問分流消失**；外層行動忠實僅 T3 有界成立。T4 顯示把真 cue 留在 `repair_check` 本身還不夠，固定模板可能壓過已選的回覆行動。T2 是 selected→surface 遺失，T1/T6 則已在 selected core 失敗，不應用同一個 patch 混修。三個早先 B4/B6/A1 或跨重啟 B1 舊反例沒有重播或重新評分。

## 測試、成本與證據界線

- 零模型聚焦／相鄰 **118/118**；入口 installer 子程序解析、controller help、py_compile、preimplementation SHA **2/2**、新 product SHA **8/8**，前批 product SHA **22/22**。另試跑歷史 v62/v63 harness 共 133 項時 **131/133**：兩個 FAIL 是舊 harness 要求 `uruha_brain_mac.py` 等於歷史 SHA `53cb...`，目前分支 HEAD 與本地該檔同為 `2a0513...`，本次完全沒改核心檔；不修改舊鎖、不把 133/133 冒報成功。
- 現行 M21 full planner **6/6** 嘗試且完成，底層模型標 `qwen2.5:7b`、compact plan `max_output_tokens=256`；新修正自身模型呼叫 **0**。可見 log 不是完整全模組 token／金額 ledger，不能宣稱成本節省或與強 LLM 公平比較。
- raw `runtime_latency_m18.user_wait_seconds` 六輪 **8.0617–11.2577 秒**、平均 **9.8805 秒**，皆 ≤20；Safari 實際 UI 點擊到最終泡泡未另用獨立計時器完整量測，故只說 runtime proxy 達標，不能把它寫成獨立 Safari latency PASS。
- v2 仍是 developer-authored，不是未見正式 holdout、人類被理解感、長對話跨重啟、VRM/Function Calling 整合或已證明「人類反應方程式」。整體 Goal 與 P4 產品驗收均未完成。

**下一個必要交付**：先對 T2/T4 的 `selected core → human_speech_plan → legacy surface candidate → M39/final` 做只讀因果審查，選一個可歸因的「選定行動不被固定模板／過短表面吞掉」變因；在新題與成本/安全/source/graph gate 前瞻凍結後才動程式。T1 上游 core 品質、T6 未知來源、B1 跨重啟來源以及 B4 guard-after-frame 是分開的缺陷，不同批補規則；本六句不重送追分。
