# P4 f4：compact planner 格式可靠度的單變因設計

狀態：**source-only 事前凍結，f4 零模型／真模型／Safari 均尚未執行**。f3 原生 Safari 已 strict FAIL，私有原件和原因見 `analysis/p4_turn_admission_stateful_f3_fresh_product_failure_2026-10-24.md`；不能重送 f3 或改其 gold。f3 M29 正確分成 `brief_encouragement`，但真 `qwen2.5:7b` 在 `json_object` carrier 下的 compact candidate 0 缺一個必填欄，嚴格驗證後落入 generic fallback。raw 模型文字未留，缺欄名稱未知；不得猜成特定欄或用預設值補成有效候選。d1 曾有同模型 shape-valid 結果，所以此項是格式**可靠度**問題，非聲稱永遠不會成功。

## 單一變因與 before 證據

唯一產品變因：僅在明示 `--compact-json-schema` 的隔離 P4 product start，將現有 compact 呼叫的 OpenAI-compatible `response_format={"type":"json_object"}` 改為 `{"type":"json_schema","json_schema":{"name":...,"strict":true,"schema":...}}`。schema 只描述原本的 root `plans`、恰三個 candidate、既有 scene/response_mode 枚舉、非空≤32字的 `core_message_jp`、全部必填／無額外欄。**原 prompt、模型／digest、temperature、max_tokens=256、三候選 strict parser、輸入、人格／記憶／背景、安全／表面、無重試、token/user-wait cap 均不改；不修 f3 fallback 或 M39。** 所以若 carrier 無效或模型仍缺欄，現有 parser 原樣 fail-closed，而不是合成候選。無 flag 預設與既有測試 `json_object` 不變，舊 c/d/f3 結果不可重判。

來源：Ollama [官方 structured outputs 說明](https://ollama.com/blog/structured-outputs) 有 OpenAI-compatible 介面例子；[官方 OpenAI compatibility 文件](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx) 列 `response_format`。本機服務 `0.34.4`／OpenAI Python `2.14.0`，**官方支援不等於這台、此模型、此完整 prompt 的成功保證**；第一次真 f4 仍須實測。先前 P3-B18 的另一模型/路徑 schema 失敗、B19 native 成功均不能代替此產品層證據。

允許程式：`uruha_compact_planner_p2.py`、`p4_direct_reply_act_m29_priority_detached_control.py` 與相稱新測試；不動 Brain/Web/Function Calling wrapper、基礎題本、原始 dirty checkout、正式 DB、baseline、f3 或其他歷史 gold。因 flag 是 carrier 的範圍開關，控制器只能對 product `start` child 注入，不能外溢 `prepare/status/verify-ready/stop`、preflight、無 flag 或 shell env。先以 fake client/CLI 斷言新 schema 的 required/enum/additionalProperties/3 件數、其他 request 欄逐字不變、非法候選仍拒絕、0 額外呼叫、0 原文持久化；相鄰 product/handoff/compact 回歸與 compile/diff check 才能稱 code gate。任何既有測試因預設路徑變動即停止。

## f4 前瞻產品 gate

新作者題與 gold 在 `datasets/p4_compact_schema_f4_probe_2026-10-24.json`，與 f3 腳踏車／舊家具／列名精確不同；凍結前 full sentence 與 `初めて自分で味噌汁を作れた` 在 tracked project source/datasets 排除無關 output 後精確命中 0。這仍是同一明示鼓勵格式的開發診斷，**不是正式 holdout 或 open-domain 泛化**。先提交推送本設計／題／preimplementation SHA／任務卡並核 PR #435 exact head；再實作、測試、提交推送 code。之後先用隔離真 RightBrain＋假 LeftBrain 作 full route，核 M29 `brief_encouragement`、M21 full/compact completed、scene support、act direct_chat_answer、final＝episode、只 1 fake call，且實際 fake request 帶 schema carrier。若路由或 code gate 失敗，0 真 provider/Safari。

若上述均通過，才在 port 7931 空閒／全新 0700 controller root／官方 ONNX 私有不同 inode與離線預熱／同 PID zero-turn ready+planned stop 後正式 opt-in 起服務；本機固定 `qwen2.5:7b` SHA `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。依 f3 的 B-stateful admission 方法保存不可覆寫 0600+fsync T0/Tpre/Tpost DB/receipt/journal 私有原件，T0/Tpre tree byte-equal、同 PID/session/reset0/finish0/DB，Tpre 前背景 pair 完整且 0 mutation/error/unknown worker；tick>0 揭露，Tpre→browser arrival 目標≤10秒且無 background/proactive interleave；同 opaque ID arrival→snapshot→cognition start/end completed→terminal delivered。任一硬 gate 不合即不 Send 或 strict FAIL，**只准新 Safari Send 一次、0 retry**。

結果需同時有：三個**真**候選與 strict parser `completed=true`、M29→M21→表面保留一句鼓勵，原生 Safari 泡泡短自然日文承接「第一次自己做味噌湯」、無教學/追問/捏造，泡泡＝raw＝guard＝graph utterance＝隔離 episode，原生圖至少 input→retrieval→decision→utterance→writeback 可逐段核；保存 native PNG/AX 或誠實標 visual gate 缺證。上限 3 completed Brain user-turn generations、2,000 provider tokens、20秒 user wait；Brain／背景／Web-delivery 分列，後者額外 Chroma 成本目前 unknown。若 carrier 格式成功但可見行動仍錯，明列**格式狹義改善、整體產品 FAIL**；不得順手合修 fallback、M39、模型 prompt 或降低 gold。只有 fresh f4 narrow PASS 也不證同模型 LLM 優勢、真人被理解感、formal holdout、VRM+Function Calling 或 Goal 完成。
