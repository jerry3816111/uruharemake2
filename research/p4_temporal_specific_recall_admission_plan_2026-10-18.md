# P4 具體過去發言的時間片語准入：下一項前瞻設計

狀態：2026-10-18，**只讀歸因完成；本項程式與新八句的首輪模型／Safari 尚未開始**。前一批關係答案權限六輪仍是 strict FAIL，raw SHA `c57f1c95087c96ee10240ae312829d359a884cae24011d7878429b974e6f3797`，不得重播 T4 或改其 gold。本項是同團隊產品開發探針，不是獨立 temporal holdout、人評或強 LLM 對照。

## Before 與唯一能力變因

上一批 T4 問 `少し前に言った集合の目印、覚えてる？`，T3 直接原話 episode 已在候選池 rank 8，相關 short-term rank 2；M22 判 `factual_or_memory`。但既有 `explicit_episode_recall_focus_p4._QUERY` 只允許 `さっき|前に|以前`，未接納有時間修飾的 `少し前に`，因此沒有 source-qualified handoff。舊 `覚えてる？` 泛用規則把 T4 選為 `chat/memory_presence_reply`，top-1 無關 T2 short-term 泛用 context 接管，最後錯答。新關係答案權限只對 `ask_miss_me` 生效，在 T4 未啟動，不能改成「禁止所有記憶」。

本項唯一核心變因：**把有界、未引述的具體過去發言時間修飾語 `少し前に`／`ちょっと前に` 准入既有來源限定 episode recall 契約**。輸入仍以原文進入 retriever、保留原文 SHA；既有契約的有效 episode ID／trace、直接 `User:` 原話、焦點唯一性、撤回／衝突／敏感來源、handoff→selected→最終可見日文驗證完整沿用。只改准入語法和其 raw-free 圖上 provenance，不能以 short-term `User:... -> Uruha:...`、模型 Summary 或高分泛用 context 當事實答案；缺來源就自然短日文不確定。其他「覚えてる？」、關係問句、引述台詞、第三者、保護路由、一般事實與舊 focus 語法不改。不得改全域 top-k／scorer、M22、舊 frozen 模組原檔、上一批資料或正式 profile。

允許新增：本項 opt-in temporal-admission module、聚焦測試、薄 Web 入口／隔離 controller、新前瞻 dataset／本計畫／SHA、結果報告和 `CURRENT_TASK.md`。沿用前項 graph；新准入須在既有 `explicit_episode_recall_focus_p4` 節點留下可核對的原文 digest、時間片語證書、source ID、selected/final 對應，不能只讓 regex 測試綠。接線設計採 opt-in 的既有 classifier 外層：只對精確的兩種時間片語去掉修飾語做舊分類，接著將契約 `input_sha256` 改綁本輪原文並加時間准入證書；retriever 與舊 source-contract 都收到原文，舊正常語法仍原樣呼叫。安裝時校驗舊分類器／模式；失配 fail closed，未安裝時全無變化。若安全接線必須改舊凍結原檔或大量複製其 source contract，先停在設計審查。此項補的是可觀察語法准入，不宣稱通用語用或任意時間表述。

## 新題、負控與 strict gate

新八句／條件式 gold 在 `datasets/p4_temporal_specific_recall_admission_fresh_probe_2026-10-18.json`；exact repo 逐字碰撞首輪前檢查。T1/T5 為兩個不同物件的直接使用者陳述；T2/T6 是近期干擾；T3/T7 分別測 `少し前に言った` 與 `ちょっと前に話した` 能否從正確 episode 回答，不拿最近關係／閒聊當答案。T4 引述編輯不得 takeover；T8 無對應來源須不捏造。T4 後 planned stop／同隔離 DB 重啟，兩個 Safari session，每句一次／0 retry。若正確來源根本未入候選池，記 coverage FAIL，不能把猜對算成功。

首輪前只讀／零模型 preflight：八句在 Git 已追蹤檔案中的 exact collision 為 0/8；未安裝新准入時，舊 source-focus classifier 對八句的 `eligible` 為 0/8，quote-scope classifier 只有 T4 為 true。這不是新能力的測試結果。至少一個來源原本落在普通 top-5 外只是前瞻 coverage gate；新批若 2 個正例都在 top-5，必須照記 FAIL，不因前批來源曾在 rank 8 而改門檻。

零模型控制另涵蓋：舊 `さっき／前に／以前` 正常准入、未安裝版本不變、原文 SHA 不因准入改寫、引述／第三者／保護／一般關係問句拒絕、唯一來源／rank>5 handoff、同焦點不同值與更正撤回、敏感來源及 malformed provenance fail closed。與新八句的字面文本隔離。先跑聚焦，再跑舊 episode focus、關係權限、quote scope、history sync 等相鄰回歸。

首輪 strict PASS 同時要求：所有零模型／相鄰回歸通過；T3/T7 2/2 原始 episode User-span、focus、trace ID、handoff、selected `recall_context`、最終正確值與圖節點同源，且至少一個正例正確 episode 原本不在普通 top-5，否則 coverage 不足；T4 不 takeover、T8 不假造；T2/T6 不因新准入被改成事實回憶；八輪自然 casual 日文、raw＝graph `utterance`＝Safari 泡泡 8/8、八個不同 episode、T0–T8 full profile 0 rows／同 digest、兩個 session／planned same-DB restart／所有 PID 退出與 7894 vacant；每輪 user wait ≤20.0 秒、此 gate 新增模型呼叫 0。可得的實際 token／模型呼叫／服務預熱成本分開報；token ledger 缺失就標 unavailable。任一 gate 失敗整批 strict FAIL，保留 raw／gold／SHA、0 retry，不拿前批 T4 改判；至多一個有根據的新修正批，仍失敗則 `REVIEW_REQUIRED`。

程序：先 commit/push 本計畫、dataset 與 preimplementation SHA，核 PR #435 head；再寫 opt-in code，受影響測試、依賴／產品 SHA、diff review、commit/push／核 head；最後才啟全新 0700 root，做 0-turn readiness／planned stop、官方 SHA ONNX 私有離線預熱、顯式空 profile，按八句真 Safari 各一次、逐輪 profile／episode／圖／泡泡／latency 核對，最後 planned stop、結果報告及任務卡。這一批若通過，只支持**有界日文時間修飾具體發言回憶**；不證完整記憶、人類被理解感、同模型優勢、VRM／Function Calling 或人類反應方程式。
