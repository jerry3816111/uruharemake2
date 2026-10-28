# P4 f5：真 Safari 格式成功，但可見日文與承接需求 strict FAIL

狀態：**f5 完整產品 strict FAIL；狹義 schema-format/時序 gate PASS**。f5 題、gold、成本及 admission 門檻在 `cecb10b` 先凍結並推 PR #435，新題零模型 6/6 在 `f515aed` 再推；本批產品碼沒有改。f3 原真回覆品質 FAIL、f4 pre-Send 0 Send FAIL 不重判、不重送。f3 與 f5 題目不同，下述格式差異**不是同題因果證明**。

## 實際結果（只送一次）

原生 Safari session `20261024_071633_59d7a457` 在隔離頁 `127.0.0.1:7932` 送出凍結句：`初めて自分でシャツのボタンを付け直せた。今は一言だけ励まして。`，**Send 1 次、retry 0**。最終泡泡：`頑張ったね。頑張り继续！そのくらいでいいだろ。`。其中 `继续` 是中文，違反自然日文 hard gate；整句沒提到「第一次自己把襯衫鈕扣縫回去」，且最後固定式尾句不符合自然、精準的一句鼓勵，visible gold **FAIL**。沒有捏造私密經歷或錯誤身份宣稱，但本題無法測出正向 self-identity。原生節點圖確實顯示 USER SIGNAL、compact planner、speech、utterance、language guard、記憶/寫回等節點和連線；我在 Safari 展開 compact／speech／M39／guard／utterance 核對。CUA 截圖與 AX 只在當時畫面觀察，**沒有可持久重核的 native PNG/AX 檔**，故 saved-visual gate 亦未達；不能以後端 trace 代替它。

## 隔離與 admission 原件

- port 7932 起初空閒、本機固定 `qwen2.5:7b` digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。全新 0700 controller root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-1ji13ijy`；官方 ONNX archive SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`、83,178,821 bytes，私有 inode 49370344 ≠ host 4160298；離線 warm 1×384、下載嘗試 0。zero-turn rehearsal `4bc39e05470a0c23`／PID 30367 最終同 PID HTTP ready/planned stop/port vacant；啟動瞬間第一次 verify 暫回 `product_listener_not_same_pid`，稍後同 PID 驗證成功。正式 opt-in run `048c0e3c97ac23a2`／PID 30621 同 PID HTTP ready。
- T0 `evidence/db-t0.json` SHA `93ffb10c220ddd3e742a2c31c911e77cd00bb12826aa3f4dc570ffdd96ecdb89`、journal 0；Tpre `evidence/db-tpre.json` SHA `74d0011d9aea54a1ffb82c318ddcbce1d2a24d40908a52cbf739539191ed1a23`、seq1–10＝5 對完整背景事件。兩快照均同 PID/session/reset0/finish0/DB；唯一 `memory_db/chroma.sqlite3` 176128 bytes、SHA `1bfab33bf3d91d456f71555cd3a438a34ea908591adce01c9702bffc733ad250` 位元組一致；Tpre tick1 明列。前五 pair 4 idle/1 passive_decay completed，全部 0 reported/vector writes、0 error、0 unknown worker；completed pair 有 5 次 vector read operation，無生成。
- Tpre 結束 monotonic `1797373207005750`，human seq11 `arrival` `1797377211223833`，間隔 **4.004218083 秒**且中間 0 背景/proactive 事件。seq11 arrival→12 admission_snapshot ready→13 cognition_start→14 cognition_end completed→15 terminal delivered，全部同 opaque submission ID `806e9ce430c2ea1664f88f257e9cc41e`、PID/session/reset0/DB。Tpost `evidence/db-tpost.json` SHA `adc4c57610d69a97a2d3f704c57a3e7334e1f833230b2b3ae11e3bae4a0fe5cd`，receipt finish1/tick2；journal seq1–25 最終 SHA `863362c9b9134aa97e16ed3f8f77ea389037b11af90a8df7459a6c0abb64fe68`，10 對完整背景 pair、0 vector mutation/error，無其他事件。
- 私有 Web JSONL **一行** SHA `921d7a7f72aa1de6dae0c39c887108fc03dbe6f524b8b5153d4381e116c7edc5`；泡泡＝raw `assistant_reply`＝`logic.visible_language_guard.final_reply`＝graph `utterance.reply`，隔離 Chroma 唯一 `episodic_memory` document 中的角色回覆亦為同句。隔離 Chroma `episodic_memory=1`、`user_profile=0`、knowledge/procedural/wisdom=0。正式 DB 未碰；私有失敗 episode 留在隔離 root 供稽核，不混入正式長期記憶。
- 正式 PID 30621 exact planned stop、7932 vacant，stop record SHA `215178043a37577d8d85a35847af75dca82586e1bdc82f5c115733b8bddb17f0`；僅關本次 Safari tab 53→52，原有分頁未關。

## 哪裡進步、哪裡確實失敗

真 M29 為來源綁定 `brief_encouragement`，M21 `full_planner`；opt-in compact **completed=true、candidate_count=3**，scene support、`core_message_jp=頑張ったね。頑張り继续！`、response_mode direct_answer，speech act direct_chat_answer。故這次沒有 f3 的 `candidate_missing_fields` fallback，證明此新題/本機模型的 schema carrier 可產生可解析候選；但原始三候選文本按既有隱私邊界不持久化，不能斷言另外兩個候選內容或 parser 之前的模型推理。

錯誤已在 `logic.core_message_jp`，不是 Safari 翻譯。`human_speech_plan.content_units` 也帶 `頑張り继续！`；M39 `source_frame.observable_concepts=[]`、`accepted_verified_surface`，沒有阻止失去「鈕扣／第一次」；`visible_language_guard.changed=false`、`initial_rejection_reasons=[]`，沒有識別中文 `继续`。這是**格式驗證與語意／語言品質脫鉤**的直接反例。不能用「三個 JSON 物件有效」代替「理解並給出對的回覆」。

本輪歸因 receipt：1 次本機生成（`qwen2.5:7b`，prompt 1,043＋completion 85＝**1,128 provider tokens**；model call 7.444 秒）、11 次 instrumented vector ops（10 query、1 add）、failed 0；user wait **10.0486 秒**，低於 20 秒上限，Brain/前端 queue/背景分列。Tpre 前 completed background 額外 5 vector reads、human turn 後且 Tpost 前另一輪額外 5 reads，不算進 user turn；Web delivery 之外未 instrument 的額外 Chroma/embedding token、CPU/RSS/energy 與真人被理解感均 unknown，**全產品成本 gate 未證**。

下一步須先獨立定位可見日文 guard 對漢字混寫的漏檢與模型核心訊息未保留具體來源的責任邊界；**只選一個可歸因產品變因**做事前凍結、紅綠測試，再用全新 source-disjoint 題驗真產品。f5 不重送、不改 gold；少量 developer diagnostics 不能聲稱強於一般 LLM、正式 temporal holdout 或真人偏好。Goal active。
