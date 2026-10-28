# P4 reported-ack B：首發 Safari 產品驗收（保留失敗）

結論：**strict FAIL**。首輪前凍結的 B module／八題／條件式 gold 位於 commit `f02cf95113391e6b8512d6ee23fb0e4203060161`，本次不修改題目、標註或成功門檻。作者自編的開發題不是獨立 holdout；下述仍是本機產品實輪，不是人類評價或同模型 LLM 優勢。

## 實際可見結果

| 輪 | Safari 輸入摘要 | Safari 最終泡泡 | B / 主要觀察 |
|---|---|---|---|
| T1 | 朋友轉述「先に確認してね」 | `友人が「先に確認してね」って言ってたんだね。何を確認するかはまだ分かんないけど。` | `final_visible`；來源報告與未知對象保留，B 最終 9/9 檢查 true。 |
| T2 | 妹妹轉述「先に確認して」 | `妹が確認するって言ったね` | protected，B 不接管；原 M31 把「叫人確認」誤為「妹妹自己確認」，source fidelity 另有失敗。 |
| T3 | 學長轉述後，直接叫うるは先問回覆形式 | `じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い？` | B 不接管，直接要求被回應；P4-V/W 仍標 `statement_changed_to_question`／`unresolved`，與同句明確的「聞いて」衝突，為 shadow 警告。 |
| T4 | 集合地點改變，非轉述 | `待ち合わせ場所が急に変わったんだね。` | B 不接管。 |
| T5 | 重啟後老師轉述「先に確認してね」 | `ん、その話もう少し聞かせて。` | **正例失敗**：A `admitted`、M31 `deferred`、selected act 正確，但 B `not_applied/memory_or_profile_authority_present`；此前 session 的 episodic context 被檢索，即使 `memory_use_expected=false`、`memory_speakability=background_only`，粗門檻仍阻止可見承接；語言 guard 最後改成泛答。 |
| T6 | 要求自我介紹 | `うる、自己紹介したね` | B 不接管；既有 M31/身分路徑錯把自介請求當已完成事實，**身份產品負控制失敗**。 |
| T7 | 同事轉述「先に確認してね」 | `一回止まって聞き返す。そのくらいでいいだろ。` | protected，A `rejected`、B 不接管；不假稱此句語用品質已合格。 |
| T8 | 確認對象尚無人決定 | `確認の対象は誰にも決まっていないんだね。` | B 不接管，未憑空補對象。 |

T1/T5 預先定義的 ordinary 正例只有 **1/2** 達 final 承接；T2/T7 protected **2/2** 未被 B 接管，四個其他負控制 **4/4** 未被 B 接管。但八句不能總稱內容正確：T2、T6 的可見語義錯誤與 T3 的 frame shadow 警告保留。T5 不是臨時更改 gold 的「不適用」：預定跨重啟正例的完整產品覆蓋沒有達到，整批嚴格失敗。

## 路徑、隔離及成本

- 全新 0700 launcher-owned root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-9uon9vig`；先做零輪啟動／planned stop、離線 ONNX 預熱、明確 0-row profile T0。T1–T4 為 session `20261018_100450_a3e9ab63`，planned stop 後同 DB 重啟，T5–T8 為新 session `20261018_100903_3affe140`。兩個本機 PID 均正常停止，7894 port 空出；沒有外部部署。
- 八題各一次、0 retry；Safari 當輪目視泡泡與展開的 graph `UTTERANCE` 均等於 raw reply（8/8）；raw 內 blackboard `utterance` 亦相等（8/8）。T1 可在 graph 展開 `reported_ack_selected_visible_p4` 看到 `final_visible`；T5 同節點為 `not_applied`，沒有把 selected 成功冒充 final 成功。
- T0–T8 九份 `profile-full-tN.json` 都為 0 rows、同 SHA `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；九份 episode snapshot 從 0 增到八個不同 ID。正式 DB 與原始 dirty checkout 未碰。
- 八輪 user wait 全 ≤20 秒；平均 **10.6384 秒**、最大 **13.8012 秒**。B 自身追加模型呼叫 0；M21 completed 2 輪、M31 completed 5 輪（按各自 trace 欄位）；此批沒有經完整核對的全管線 token 合計，標 `unavailable`，不報成 0 token。前瞻 B 合約／相鄰 160/160 只證指定程式契約，不能抵銷 Safari 失敗。
- raw 原件 `web_logs/conversation.jsonl` SHA-256 `020de8e7a6b526e03b15f4f0a1a28bbaa2efc9bf6037786692ad86907e817c7e`；凍結 manifest 14/14 重驗 OK。本報告是同團隊非獨立稽核。Safari 新開的兩個 B 測試分頁保留；測試服務已關，分頁可關，不影響證據檔。

## 單變因後續

不能改寫本批 1/2 結果。下一步先對 T5 的「檢索到背景 episode」與「可授權引用記憶」分層做只讀設計審查；若能證明候選表面只用當輪 source、且既有 profile／事實記憶／protected gate 完全不被覆蓋，才另凍結一次新資料與新的 B 修正批。T2 source fidelity、T6 identity 與 T3 frame shadow 是不同故障，另列任務而不塞入 B。正式同模型強 baseline、人評、temporal holdout、VRM/Function Calling 整合仍未由本批授權。
