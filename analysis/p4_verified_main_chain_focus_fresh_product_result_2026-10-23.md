# P4-D-F：新隔離 Safari 主鏈焦點圖驗收

日期：2026-10-23。事前凍結設計／f0–f2／preimplementation SHA 在 `c4d413c`，renderer／8/8 聚焦、205/205 受影響零模型測試及 product SHA 在 `c83306f`；兩個 commit 均先於本批真題推到既有 PR #435 並核 exact remote head。f0/f1/f2 是 developer-authored prospective product probes，**不是正式 holdout、人評或同模型優勢證據**。本批每題僅在原生 Safari 送一次、0 retry；D0–D10 和 dg0/dg1 未重播。

## 隔離與可追溯原件

- 新 controller-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-gd17k6wr`。官方 ONNX archive 83,178,821 bytes／SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 的 0600 私有複本，inode `48820909`，與主機 inode `4160298` 不同；archive／六個解出檔案均經 controller byte validation。預熱產生 1×384 有限向量，攔住 Chroma `_download` entrypoint 後觀察 0 呼叫；**不宣稱 OS 層完全斷網**。
- Zero-turn run `67bbf3ec588ba3da`／PID 95008：同 PID HTTP ready；兩個隔離 Chroma embeddings 和 queue 都是 0，web log 尚不存在；planned stop、原 PID 退出與 7894 vacant。產品 run `6e12fe592fd5b780`／PID 95420：同 PID HTTP ready，T0 仍是空 DB；最後 exact planned stop／port vacant。首次 ready 探測在 font cache 初始化時曾 timeout，一次稍後驗證成功，**沒有重啟或送模型題**。產品 stderr 無 download／traceback／error。
- Safari 僅新開一個 localhost 分頁（52→53→52），沒有關閉使用者其他 52 個分頁。實際 session `20261023_021044_f9ffc0b3`，raw 三行均同 session、turn 1→3；reload 後側欄一度顯示啟動 session ID，但下一輪送出仍以實際同 session 記錄，與 D-G 已知表面現象一致。私有 `web_logs/conversation.jsonl` 3 行／6,489,289 bytes／SHA `e93a8d1b640b783afde14be1c16af9c600440f7e9fdc9de061d88512552596d0`，未加入 Git。

## 逐輪觀察

| 凍結題 | 最終 Safari 日文（與 raw、guard、blackboard utterance 相同） | 原生圖與 reload | 等待 |
|---|---|---|---:|
| f0：User 決定紫門 | `そっちが2089年4月19日に陶器の羅針盤を受け取る場所を紫の工房の南扉に決めたんだな。` | 原圖 78 nodes／113 edges；焦點 input→本人決定 D→選定 D→utterance→output→trace episode，完整 input/output 和 D／selected signal 可見；reload 同焦點 | 16.3011s |
| f1：User 明示訂正白門 | `訂正ね。そっちが2089年4月19日に陶器の羅針盤を受け取る場所を白い工房の東門に決めたって話な。` | 原圖 81／121；焦點轉為本人訂正 D／訂正承接，舊紫門沒有冒充當輪決定；reload 同焦點 | 11.8980s |
| f2：朋友的決定 | `友人は2089年4月19日に紫の工房の南扉で陶器の羅針盤を受け取る場所を決定したらしいんだね。` | 沒有 D 焦點／D 原圖 node；一般完整原圖照常顯示，reload 仍無 D 焦點 | 11.8945s |

本次原生 Safari 視口中，f0/f1 的六個焦點卡都在一列、畫面不需水平捲動；未點焦點卡即能讀完整 input/output、D／selected signal 及末端 trace-reported episode 次序。**Safari 縮放倍率沒有獨立記錄，故凍結的「100%」條件未證實。**`+25/+0/+34/+9` 只代表原 `is-main` blackboard **記錄順序**中折疊的節點，寫回箭頭是原 `is-active` trace edge；不是語義因果、外部真實或 DB 持久化證明。f0 展開後原 78／113 圖及 D inspector 仍存在，D signal 與焦點一致。每輪原生 Safari screenshot／AX 是在工具內實際觀察，**沒有落盤 artifact**；不能事後假稱有可重看原生 PNG/AX。

SQLite 獨立讀取 `session_db`：T0→f0→f1→f2 的 `episodic_memory` 0→1→2→3、`user_profile` 每點 0；三筆皆 `source=turn_episode`，各自完整 User 原文與可見回覆同筆配對 1/1/1。另一個 `memory_db` 各 collection 均 0。圖面的「寫回」在 f0/f1 因此另有本批 SQLite 佐證，但**圖本身仍只表示 trace 報告**。raw 三輪泡泡＝guard＝blackboard utterance；raw 等待 3/3 ≤20s。沒有完整 prompt／completion token ledger，僅保留 runtime latency；新增 renderer 本身不增加模型呼叫的結論仍只來自零模型契約和程式邊界，不能由這三輪推成完整成本結論。

## 嚴格判定與待修

**窄義圖像功能 PASS：** f0/f1 當輪與 reload 有來源正確的六卡主鏈，f2 fail-closed 不造 D，原圖可展開，隔離 DB 與逐輪訊息一致。相對 D-G 的 78/81 nodes、113/121 edges、132px 截斷卡，指定 D 主鏈如今可在本次 Safari 視口直接閱讀；沒有刪掉原圖。這不補足未記錄的 100% 縮放條件。

**整體旁觀者展示／產品 strict FAIL：** f0/f1 原生畫面中焦點圖的大標題和箭頭呈深色低對比，並非已達無障礙清晰圖像；100% 縮放未核；原生 Safari PNG/AX 未由目前 UI 路徑保存，saved-visual gate 明確 FAIL。f2 雖保持朋友 actor，但句中「南扉で…場所を決定」易把指定的接收地點讀成做決定的地點，是獨立的日文語義／自然度問題，不用圖表局部成功掩蓋，也不在本次 renderer 單變因內偷修。D0–D10 舊 whole-batch FAIL、D2/D5、正式同模型／人評／temporal holdout、VRM／Function Calling 統一驗收與長期 Goal 仍 pending。獨立 fresh-log 複核代理在本輪遭遇額度限制；以下 SQL/raw 核對是同一主代理的非獨立複核，不能冒充第二審查者。

下一個必要交付先把**焦點圖的低對比**做只改 CSS／視覺呈現的單變因凍結與新 source-disjoint 題本，不回放 f0–f2；以原生 Safari 的可讀對比／箭頭辨識核驗，再另案處理 f2 的命題角色／日文表面。若保存原生視覺證據仍無合規工具，維持 saved-visual FAIL，不用合成圖冒充。
