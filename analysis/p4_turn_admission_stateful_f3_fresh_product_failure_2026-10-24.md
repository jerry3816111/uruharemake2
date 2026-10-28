# P4 stateful f3：wrapper 修後第一次新 Safari，嚴格 FAIL

**結論：f3 真產品 strict FAIL；Safari 一次 Send、0 retry。** 前瞻題本／gold／單次與成本限制於 `4a68154` 先推 PR #435，零模型 route 於 `8fa9806` 通過，私有持久取證工具於 `5cf8511` 推送後才開真產品。f0 pre-Send、f1 原始 route、f2 舊 Web wrapper 各自原判不變；這輪只測新 f3，並非正式 temporal holdout、人評或同模型 LLM 對照。

## 一次真輪的可見結果

- Safari 原生使用者泡泡：「初めて自分で自転車のパンクを直せた。今は一言だけ励まして。」原生助手泡泡：**「ん、そこもう少しだけ聞かせて。」**。它是日文、沒有錯誤身分聲稱，卻沒承接第一次自己修好腳踏車破胎，也沒有給明示的一句鼓勵，反而要求多說；事前 visible gold **FAIL**，不因語言正確而通過。
- Safari 原生圖當場可見本輪 `USER SIGNAL` 原句、`compact_general_plan_p2` 節點展開的 `completed:false / ValueError / candidate_missing_fields / candidate_index:0 / missing_field_count:1`、`UTTERANCE` 與泡泡同字。圖上有節點與連線，但無法把原生 PNG/AX 存為可重核本地檔，也未對整條 input→retrieval→decision→utterance→writeback 箭頭做完整可重核計數；**saved-native-visual 與完整 graph gate 缺證**，不以私有 JSONL/HTML 重畫補判。

## 隔離與 admission：狹義通過，不抵銷品質失敗

全新 controller-owned `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-afnt7nqo` 0700 root／7930，`qwen2.5:7b` digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。官方 ONNX 83,178,821-byte archive SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 複製成 0600 私有不同 inode 49363346（host 4160298），離線預熱有限 1×384 向量、`httpx.stream` 下載入口 0；非 OS 全面封網證明。zero-turn run `7303ead575290608`／PID 26348 同 PID HTTP ready、無對話 journal、planned exact stop、7930 vacant；正式 control＋repair cue＋journal run `a8609a0c31022034`／PID 26586 同 PID ready，初次 listener race 僅同 PID 重查。

本次新增不可覆寫、fsync、0600 私有 T0/Tpre/Tpost 原件：T0 SHA `ebc8b7cc57b182dab49c972992247c27f7fa30a0640533a4bf613f89ec0287fd`；Tpre SHA `a8d5245170a118f5c8332964402f3ebaf982692b3cc989b28778babe172e8e6f`；Tpost SHA `94d53918a5551966e61f648e58d9b749fa0c6244e8774aaf3c9353157a1aec3c`。T0/Tpre regular-file DB tree byte-identical：唯一 `memory_db/chroma.sqlite3` 176,128 bytes／SHA `d156f57883f7abbded8a298b6d9fb0b85924bada64c5b9637f173a4e1334d46b`，session DB 無檔。Tpre receipt 同 PID 26586／session `20261024_065545_52294ee4`／active `memory_db`／reset0／finish0／brain ready，**autonomous tick1**；五個先前背景 start/end pairs 完整連續、ledger coverage 完整、0 error/unknown worker/向量 mutation。最後一組 `passive_decay` 改了 in-memory fingerprint，故這是**已揭露的實際 pre-state，不是 pristine tick0 或完全無背景影響**。

Tpre monotonic 結束 `1796125758547666`，Safari click-call wall `1792796200932` ms；server browser `arrival` monotonic `1796130300080125`，間隔 **4.541532459 秒**，Tpre 不確定窗口至 arrival 無背景 event。相同 opaque ID `005e21804162534aab2988843c050ab7` 的 journal sequence 11→15 為 `arrival registered → admission_snapshot ready → cognition_start ready → cognition_end completed → terminal delivered`，同 PID/session/reset/DB/tick1，無 interleave、error 或 state drift。這只證 server delivery；Safari 泡泡另由原生畫面確認。舊 f2 的 `unexpected admission_token` 本輪沒有重現，窄義 wrapper 修復獲真產品通路支持。

## 真正失敗點與成本

私有單行 `conversation.jsonl` 的 trace 顯示 M29 admitted `brief_encouragement`、M33 `not_applicable`、M21 實際 `full_planner`，但真 `qwen2.5:7b` compact 候選 0 因第一個候選**缺 1 個必填欄位**而被既有嚴格契約拒絕：`failure_code=candidate_missing_fields`、`candidate_index=0`。raw completion 不持久化，**不能推定缺的欄名或內容**。provider 生成實際完成且計費，planner 將驗證失敗記為 `error_fallback`，退為 `core_message_jp=軽く返事する`／scene casual；表面先形成「軽く返事する。そのくらいでいいだろ。」；M39 判 unsupported external reply/result 並修為「ん、そこもう少しだけ聞かせて。」。因此明示鼓勵在**模型格式驗證→fallback→表面**鏈中掉失，不是 admission、M29 分類或記憶檢索沒啟動。零模型的假候選 shape-valid，沒有覆蓋真模型 schema 遵循率。

本輪 scoped compute：**1 真 generation**，prompt 1,044＋completion 58＝**1,102 provider tokens**；11 向量操作（10 query、1 add）、0 failed instrumented calls；M19 user wait **10.2814 秒**≤20。此 receipt 不含 startup/background、embedding tokens、Web delivery 額外 Chroma 計量或 CPU/能耗，故不可稱完整 runtime 成本。停止後隔離 Chroma `episodic_memory=1`，`user_profile=0`、其他三 collection=0；episode document 的 User 與 Uruha 回覆與原生泡泡／JSONL 最終逐字一致，表示**錯誤回覆也被隔離 episode 記錄**，不能把一致性誤當品質。正式 DB 未用，`session_db` 無檔。

正式 journal 最終 33 events／14 背景 pairs、0 mutation returned/error，SHA `57867da37a4952e9a0dcd72de402b0459a849e52c202f7a971a4245d62f76c24`；私有單行 JSONL SHA `752b7388d66f6a58964d8bb969c745692583de8fb3c98bfc0bf34c21c7fe6aeb`。正式 PID 26586 exact planned stop／7930 vacant，stop record SHA `171cb258357a7671193bf202f530d36da87eeb978a171946f93fbf047b85e94f`；只關本次 Safari 新 tab，53→52，舊 tabs 不動。私有 root 留供審核，不回收或重送。

## 下一個必要設計審查

將 compact schema 遵循率與 reply-act 保全列成**一個可歸因問題鏈**，先讀審現有 `uruha_compact_planner_p2.py` 與本輪 `candidate_missing_fields`，選一個前瞻變因（例如本機 provider 支援的 required-field structured output，而非替缺欄任意補預設值），保持三個真候選、固定模型、token cap、嚴格驗證與既有安全邊界。先 source-only 凍結新 f4 題／gold／成本／負控與產品 SHA，零模型驗證後只在新隔離 root 送一次；f3 永不重用追分。若只修格式卻最終仍沒承接鼓勵，保留新的真 FAIL，另作表面行動保全因果審查，不硬碼「鼓勵」固定話術。正式同模型優勢、人評、temporal holdout、VRM＋Function Calling 統一產品與長期 Goal 均未完成。
