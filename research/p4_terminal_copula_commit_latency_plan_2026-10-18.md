# P4 句尾 copula 的 M32 表面提交：前瞻速度修正設計

狀態：2026-10-18，**只讀歸因完成；本項程式及新六句的首輪模型／Safari 尚未開始**。上一批八輪原件 SHA `4a555de6ae4a0a4b26b3b84b01a332ac6e9a9b46a092feb4b992ca2632774683`，整批 strict FAIL，T1/T5 不重播改判。這是產品性能／來源保護探針，不是獨立 holdout、人評或強 LLM 對照。

## Before、單一變因及因果假說

上一批 T1 `校庭の集合場所は銀色の門の前だよ。`，預熱 ready，等待 22.8402 秒。M31 用 11.7562 秒取得 canonical subject `校庭の集合場所`、predicate `銀色の門の前だ`、summary `校庭の集合場所は銀色の門の前である`，但因可見 proposal 未通過來源錨點而不授權。M32 只做 `です` 等口語化，未把 summary 的**句尾** `である` 變成 `だ`；predicate 逐字不在 summary 內，two-anchor guard 唯一失敗，於是一般 M21 full planner 再耗 8.3131 秒。對照 T5 的 canonical predicate 已在 summary 內，M32 deterministic commit 成功，沒有第二個 planner call，等待 13.7760 秒。這是同批觀察；不能推論只修 copula 必然把所有回合壓到 20 秒內。

唯一能力／成本變因：**只在 M31 的 source-first canonical、肯定句、無顯式時間欄、舊 M32 僅因第二錨點字面失配而拒絕時，把 summary 終止的 `である` 表面化為 `だ`，重新交給原 M32 的同一雙錨點／日文／來源守門**。不改 M31 的模型、提示或來源審核，不改 M22／M21 路由、檢索排序、記憶、profile、舊門檻、回覆其他修復或全域日文 guard。只在 M31 當輪邊界由**真實原輸入**建立 raw-free 語義對齊證書：未引述的簡單日文肯定句 `<subject>は<predicate stem>だよ。`，原文左／右詞串與 M31 canonical subject、predicate 及 summary 的 `…である` 形式逐字對齊，且原文 SHA 與 M31/projection digest 相符。`input_digest` 本身僅能證身分，不能當語義對齊證據。引號內、句中、否定、時間／數量關係不一致、不同 subject/predicate、低信心或缺原文證書均 fail closed；不把 candidate 自動當事實。新 graph 的 M32 contract 加 raw-free 轉換證書（原／後摘要 SHA、原拒絕與新檢查）；是否真的省 M21 call 必須另看同輪實際 M21 節點，最終泡泡與 graph 必須一致。

允許新增本項 opt-in module、聚焦測試、薄 Web 入口／隔離 controller、前瞻 dataset／本計畫／兩份 SHA、結果報告，以及更新 `CURRENT_TASK.md`。**不得修改** `uruha_adaptive_person_model.py`、`uruha_brain_mac.py`、舊 frozen 模組或上一批資料。若包裝原 M32 必須繞過原雙錨點／來源檢查，就停止實作、要求設計審查；未安裝 opt-in 必須完全保持舊行為。

## 新資料、控制與 strict gate

新六句及條件式 gold 在 `datasets/p4_terminal_copula_commit_latency_fresh_probe_2026-10-18.json`；首輪前對 Git 已追蹤檔案 exact collision 為 0/6。T1/T5 是兩個不同、各在新 server session 首輪的直接陳述；T2 同 session 原話回憶，T6 planned restart 後回憶**重啟前 T1**，不再把「同 DB 有 row」代替「重啟後能答來源」。T3 的 quoted `である` 只問措辭，不得轉成事實；T4 否定不能被 copula 轉成肯定。T4 後 planned stop、同隔離 DB 重啟；每句一次、0 retry。不補跑上一批 T1/T5。

零模型控制至少涵蓋：終止 `である` + source-aligned predicate 正例；舊 M32 拒絕 shape 核對；不同 predicate／subject、句中或引述 `である`、否定與錯 polarity、顯式 time、低信心、缺 canonical/source-first/provenance、舊 M32 本來已通過的分支，以及 installer idempotence／未安裝版本不變。先聚焦，再跑 M31/M32/M33、P4 source、quote、episode focus、日文 surface 受影響回歸；不靠文字小抄讓模型答新題。

首輪 **strict PASS 同時**要求：上述零模型與相鄰回歸通過；T1/T5 兩個 source-first M31 canonical 具有事前指定的句尾 copula mismatch，原 M32 單獨失敗而 opt-in 來源對齊／轉換證書生效，原雙錨點等 checks 全部通過、selected `semantic_commit_repair_m32`、M21 general-planner completed calls 0、來源忠實的自然 casual 日文；T2/T6 從正確 T1 direct User episode 回答，T6 確認來源在重啟**以前**；T3 不把引用當當輪事實，T4 否定不翻正；6/6 raw＝graph utterance＝Safari 泡泡、六個不同 episode、T0–T6 full profile 0 rows／同 digest、兩個真 Safari session／planned same-DB restart／所有 PID exited／7894 vacant、每輪 user wait ≤20.0 秒、新 gate 本身 model calls 0。若 M31 新模型根本不產生受限 copula shape，記 coverage FAIL，不以另一條路徑湊 PASS。若任何一項失敗，整批 strict FAIL、原件與 SHA 保留，不重播追分；至多一個有根據的新修正批，仍失敗則 `REVIEW_REQUIRED`。

成本：一個新 0700 launcher-owned root、0-turn readiness、官方 SHA ONNX 私有離線預熱、空 profile，最多六個新真 Safari user turns／0 retry、兩次 run（T4 後重啟）。記錄每輪 user wait、M31／M21 完成呼叫、實際可得 token、ONNX／啟動成本；沒有可靠全管線 token ledger 就明列 unavailable，不寫 0。沒有正式 DB、外部部署、付費或真人冒名評分。

順序：先 commit/push 本計畫、dataset 與 preimplementation SHA／核 PR #435，再寫 opt-in code 和回歸；code／依賴／資料 product SHA、diff review、commit/push／核 head；最後才啟全新 root、真 Safari 六輪、逐輪圖／profile／episode／速度、planned stop、結果報告、任務卡。通過只支持**有界 copula 形狀避開第二次 planner call**與本批來源控制，不是同題修補前後的延遲因果 A/B：T1/T5 是兩個不同新輸入，T5 同 DB 重啟後也不是獨立空 DB；更不是普遍降延遲、所有日文忠實、人類理解或人類反應方程式。
