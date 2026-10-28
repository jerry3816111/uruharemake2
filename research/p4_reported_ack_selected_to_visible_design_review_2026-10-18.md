# P4 reported-ack B：selected → visible 只讀設計審查

狀態：2026-10-18，同團隊、非獨立；**只讀定位，尚未凍結 B 新題、修改 B code 或取得 B 產品 PASS**。A 的唯一 seed-provenance 修正批已在隔離真 Safari 達成有限准入子門檻，但整體產品 FAIL；原件 SHA `9580fd65f4fd4094ae733e9bdcd12fbefba1190e7723c5b009f956cadcd74236`。本審查不重播 A 已曝光句、不重算舊 gold、不解除 T6 記憶與 C 性能限制。

## 可反駁的 before 與因果邊界

兩個新普通來源報告 T1/T5 的 M31 都 `deferred_to_reported_ack_p4`，selected `surface_act=ack_reported_check_instruction_p4`、core `そう言ってたんだ。何を先に確認する話？`。但原件 `visible_language_guard.original_reply` 兩輪均是 `そう言ってたんだ。何を先に確認する話？。そのくらいでいいだろ。`，接在 `？` 後多出 `。`；guard 因 `malformed_japanese_punctuation` 以通用 casual fallback `ん、その話もう少し聞かせて。` 取代。T1 最終就是此泛答。T5 的 P4-T 因 `「…」`＋`と言った` 把 source 當 quoted frame；P4-W 再對**本輪 guard 產生的泛答**做 `quote_embedding_restore`，最終變 `「ん、その話もう少し聞かせて」っていう記載なんだね。`。這是錯把泛答包成被轉述內容，不是正確的引述承接。

程式靜態對應：`uruha_brain_mac.py` 的 `_speech_plan_variants` 對一般 `direct_chat_answer` 用 `f"{core}。そのくらいでいいだろ。"`；`_fallback_reply`／`speak` 可選它，語言 guard 對 `！？` 後接 `。` 拒絕並改 casual fallback。原件未保存 `speak()` 當下逐字回傳，故「這個 variant 是本輪唯一來源」是**高信心靜態推論**；已觀察事實是 guard 前候選逐字同形及後續實際轉換。M39 對 fallback 回 `accepted_verified_surface`，T5 的 M39 甚至 `third_party_present=false`；它不是 selected reported-ack fidelity 的充分證據。

單純刪 `？。` 不足以解決 B：T5 的 P4-T `frame_violations_p4` 要可見句具有引述／報告標記；現有 selected core 雖口語上像承接，卻不符合該有限 quote-preservation 判準，仍可能被 P4-W 改寫。不能為了讓這兩句通過而關閉全域日文 guard、P4-T/W、安全路由，或把 guard fallback 當成選中行動的成功。

## B 唯一產品變因候選：來源綁定的 reported-ack 表面實現

只在 **同輪來源／digest certificate 完整、A admission `admitted`、M31 deferred 且無新增 M31 呼叫、actual chat/casual、高路由、M22 單一 general、selected `ack_reported_check_instruction_p4`、無 profile/memory grounding** 同時成立時，讓 selected action 的日文 core 採能被原日文 guard 與 P4-T/W 認可的**第三者報告語態**，並阻止通用 `direct_chat_answer` 額外尾句破壞它。候選語態如「先に確認してって言ってたんだね。何の確認？」；這只是待新資料驗證的設計例，不是將此句寫成開放域答案。來源 grammar 的 `確認／チェック` 與 `先に／まず` 必須支持實際措辭；若不支持，fail closed 保留原路，不虛構引述原文、聽者、動機或已確認結果。

實作優先採**新 opt-in B 表面 hook／入口**並重用既有 A certificate；A 已凍結的 code、manifest、dataset 不改。Hook 的單一因果目的為「已選中的 source-qualified reported-ack 作為可見日文行動存活」，不是重新路由、改 seed、改 M31 語義、修記憶或調延遲。若需要同步更新 selected core 與 actor final audit，這兩者是同一可見 commitment 的兩端，不可把新候選只塞進最末端而讓 graph 虛報。原日文 firewall、P4-T/V/W frame 修復與 M39 仍照常執行；後段若再改寫或拒絕，當輪計 **FAIL**，不能用 B hook 的預期句覆蓋實際最終句。新 trace 僅記來源 digest、選中 act、guard 前後／最終 digest、檢查狀態，不存未授權原文或心理事實，不新增模型呼叫或 profile fact。

## 下一項先凍結，然後才實作／驗收

1. 定精確 B task card：允許的新 opt-in 檔與必要共用 hook、同輪證明 schema、fail-closed 條件、上游不變契約。先用零模型開發 fixture 覆蓋 certificate 完整普通正例；缺／錯 digest、保護 seed／low road／safety M22、混合直接要求、無引文、記憶／身份、unknown、自述與一般 `direct_chat_answer` 均不得被 B 接管。既有 A 36 tests 和相鄰回歸不退化。
2. 在任何 B 新生成前另凍結**全新**未曝光的開發者自編 Safari 多輪題、條件式 gold、順序、≤20 秒每輪與資源上限、SHA，commit/push 並核 PR head。A 的 T1/T5 只能是 before，不能作 B 前瞻 pass 題；新題不得與既有曝露題／fixture 逐字重合。必要時核相同來源在不同報告動詞、不同第三者及重啟後仍有效；protected/混合/unknown 不得錯接管。
3. 隔離產品入口真 Safari 各句一次、0 retry，逐輪核 `source → A/M31 → selected core/act → guard → P4-T/V/W → 最終泡泡＝graph UTTERANCE＝raw`，以及自然日文、無假引述／無不被授權的事實、完整 profile digest／episode、重啟／啟停、實際模型呼叫與可信成本。B 嚴格通過至少需普通正例的最後可見句自然且保留第三者報告／未知確認對象，且 protected/直接/負例不退化；單靠 selected 或 guard 布林值不及格。
4. 若第一個有根據 B 前瞻批失敗，保存 raw/gold 與最小反例；至多一個**事前再凍結的新**有根據修正批，仍失敗就 `REVIEW_REQUIRED`，不換舊句追分。T6 記憶焦點與 C 延遲各自另卡。沒有可信 token 數記 `unavailable`；不得用此工程驗收主張強 LLM 優勢、人評、temporal holdout 或完整 Goal。
