# P4 當輪來源角色：隔離 Safari 產品探針（首次生成前凍結）

日期：2026-10-20。前一份 13 題是零模型開發契約，這七題是在實作與聚焦測試後、**首次新產品模型／Safari 輪次前**撰寫；只能稱 developer-authored prospective product probe，不是獨立 holdout。舊兩批八輪 strict FAIL 不重跑、不改 gold。這一批檢查 source-role 憑證是否真進現有 Web graph 及是否抑制錯誤候選呼叫；不宣稱已解決候選 JSON、敬體或 M31 權限。

`datasets/p4_current_turn_source_role_safari_probe_2026-10-20.json` 固定 A1–A7、順序與條件式 gold。A1 混合改寫＋回憶、A2 `友達が` 為未來讀者的單一改寫、A3 英文單一改寫、A4 轉述、A5 敏感引述、A6 對舊改寫例子的描述、A7 身份。七句各送一次、零重試；不得事後挑題或只報好的回合。A1/A4–A7 opt-in 改寫模型呼叫必為 0；A2/A3 至多各一個 80 completion token、6 秒 timeout 的額外呼叫，若 M31/M32 或事實／保護權限競爭，必須在呼叫前 fail-closed 並在圖上說明。准入不等於最終改寫成功；A2/A3 若實際可見未交付自然、語義保留的日文改寫，產品品質仍 FAIL。

使用全新 launcher-owned 0700 runtime root、隔離 Chroma/profile/log，先 0-turn 同 PID ready/planned stop 與官方 SHA ONNX 私有離線預熱；再 product 同 root 新 PID，T0 0 episode/profile。Safari 新分頁同一 session A1–A7，逐輪在下一輪前核對泡泡、runtime node graph、原始 JSONL、episode/profile 快照；最後 planned stop、核端口空閒，只處理本次分頁。驗收要看 `USER→current_turn_source_role_p4→(rewrite action 或舊權限)→utterance` 真連線與節點內容，raw/NFKC digest、角色、lineage、不保存原文、舊 M31/M32 不被偷 shadow；每輪泡泡＝raw＝graph UTTERANCE＝最後 guard、自然日文、身份／安全、≤20 秒 runtime user-wait proxy、七個不同 episode、profile 不增加推測性事實、正式 DB 不動。逐輪列新 action calls/tokens/latency 及可取得的 full-pipeline 成本；缺項寫 unavailable。

嚴格判準：source-role 分類 7/7 且五負控 0 誤呼叫、A2/A3 真正改寫品質 2/2、七輪 final/guard/graph 與自然日文及隔離/延遲全過，才叫產品 PASS；任一硬 gate 不過整批 strict FAIL。既有 M31 來源未具跨相同原文不同輪的 event/cycle 證明，故本批**絕不覆蓋 authoritative M31/M32**；若擋住改寫，按品質失敗保留，下一項需新增上游 lineage 與完整候選語義驗證，不能回頭重送 A1–A7 追分。正式同模型對照、人評、temporal holdout、VRM／Function Calling 統一運作仍 pending。
