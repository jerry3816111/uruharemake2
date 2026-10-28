# P4-AC 隔離真實產品／Safari 可讀 graph 驗收

日期：2026-09-23  
狀態：**PASS（prospectively frozen real-product + Safari）**，failed gates=`0`。

## 為什麼做這一步

P4-AB 的單元與合成 integration 已把 `source_bound_proposition_preservation_p4` 從 `18 fields` 改成有固定語意的短句，
但那仍不能證明真實產品有把同一份 logic 送到 Safari。P4-AC 因此在執行前固定兩個沒有出現在 P4-AA 的輸入、canonical
surface chain、畫面片段、記憶與延遲門檻，再使用新的 private runtime root、port `7873` 做唯一一次兩輪實機驗收。

## 真實畫面結果

| 輪次 | 輸入 | 可見日文 | Safari graph 的 P4-Z 摘要 |
|---|---|---|---|
| 1 | `This is only a quote: "the north window stops accepting at eight," not my schedule.` | `「北側の窓口は八時に受付を終了する」っていう引用なんだね。` | `引用｜引文命題｜主體/動作/時間｜修正 3→0` |
| 2 | `今日はコーヒーを飲みながら設計を見直していた。` | `コーヒーで設計見直し` | `未支援來源｜歸屬未知｜欄位無｜保留原文 1→1` |

第一輪可直接看出：輸入是「引用」，命題屬於「引文」而不是使用者本人，已知的是主體、動作與時間，三個違規經修正後
變成零。第二輪沒有落入目前只支援 quote／hearsay／hypothetical 的受限文法，所以圖上誠實顯示來源與歸屬未知、沒有已知
欄位，並保留原文而不假裝解析成功。

## 量化證據

- successful／Japanese／durable episode／graph visible／P4-Z node visible=`2/2`。
- readable summary／logic exact／canonical surface chain=`2/2`；generic `N fields` 摘要=`0/2`。
- supported exact visible output=`1/1`；unsupported unchanged abstention=`1/1`。
- 隔離 Chroma `episodic_memory=2`，episode IDs 為
  `d9aaa2f2-97d4-431b-bdf4-bbe266890cf9`、`cfbc3b52-87e4-4dec-9666-601c7a677032`；
  `user_profile=0`，沒有污染正式資料。
- end-to-end=`16.5364s, 11.1704s`；總和=`27.7068s`，皆低於事前上限。
- P4-AB 摘要機制新增 model／memory／tool call=`0/0/0`。整體產品既有 semantic authorization 實際完成本機模型 call=`2`，
  elapsed 合計=`22.8006s`；token accounting unavailable，不能宣稱零模型或零成本。
- retry／fallback／付費 API／外部部署／正式記憶存取／function tool／VRM action／關閉使用者 tab 均=`0`。
- conversation JSONL 兩列 SHA-256：`97bf92b762c11978aae3e718874f1f5f79b978bbda8ece65430d47f1d67ad08b`。

## 可主張與不可主張

現在可以主張：在一個事前凍結、隔離且沒有重跑的真實產品＋Safari 兩輪中，P4-Z 的來源框架、歸屬、已知命題欄位、
修正動作與違規數能以由同輪 logic 導出的 exact summary 顯示在 runtime graph；unsupported 輸入也不會被包裝成已理解。

不能主張：這兩題證明 open-domain 語意、人類偏好、felt understanding、強 LLM 優勢或人類反應方程式。它只完成
「內部可追溯資料真的能讓旁觀者看懂」這個 presentation gate。下一個必要能力不是再做一張圖，而是把當輪使用者可能期待的
不同回應（解法、被接住、吐槽等）建成可反駁候選，並嚴格分開文字證據、替代假設與未知私人狀態。

Safari 保留在 `http://127.0.0.1:7873/?m36safari=1`，伺服器仍在執行，未關閉任何使用者頁籤。
