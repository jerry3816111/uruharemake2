# P4 direct-act handoff：隔離高埠 fresh c 比較（事前設計）

定案日期：2026-10-23；任何 c 題模型輸出之前。這是既有 M29→同一 full planner 的 source-bound certificate handoff 驗證，不改認知程式、不新增 M。舊 a0 因不同模型／設定 strict FAIL；舊 b0–b6 因 Reset 66 在 Send 前 strict FAIL、0/9。兩批不重播、不改判。7914 一次零對話診斷只證高埠可用，沒有答覆品質資料。

## 問題、單變因和結果範圍

同一產品入口、M29 來源准入、原始 User 訊息、公開人格、空記憶、full planner、模型／生成設定、guard、graph、writeback 下，control 不向 planner 傳 direct-act certificate，treatment 僅傳當輪有來源的 requested-act 約束；兩臂都看原文。這只可估計**證書傳入相同規劃器的狹義效果**；不是整個 UruhaBrain 對一般強 LLM 的比較，也不是人格、被理解感或跨輪未來預測的證明。非決定性生成與每題單次樣本限制外推。

模型固定 `qwen2.5:7b`，執行前本機 `/api/tags` 觀察 digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`；每臂前後重讀，變更或無法量到就停。temperature `0.1`、compact `max_tokens=256`、full-planner 20 秒 timeout；同一 API/transport、相同硬體和現有產品 prompt/schema/guard。未明設的 seed、top-p、context、think 要在兩臂保持同一 Ollama 預設並記為 unspecified，不能臆稱 deterministic。處置多出的約束 token 是成本，不能偷偷給 control 少上下文、改弱模型或另加固定答案。先前零模型 capture 能精確比較 after-proxy request 的非介入段；**現有真產品 ledger 只保存 request-shape／整段 system SHA，不足以從 live trace 重建非介入段做逐 byte parity**。真輪只核 model/digest、顯式參數、role、User hash、handoff 與 route；精確 prompt parity 僅是零模型契約證據，不能混稱 live 已量。相鄰 90/90 等是既有機制證據；本批仍核 source SHA、classifier/M29 seam 與產品真 route，不以 unit test 取代真生成。

`datasets/p4_direct_reply_act_handoff_fresh_c_probe_2026-10-23.json` 是作者寫的新開發案例，不是未曝光正式 holdout。c0/c1 各兩臂，c2–c6 只 treatment，共最多 9 個獨立 arm-turn；每臂一次、0 retry。c0/c1 的當輪請求分別是短労い／輕鼓勵。c2 純敘事、c3 第三者轉述、c4 否定、c5 前後衝突／自我修正、c6 他人地址保護；後五題不能拿到單一 direct-act handoff。c5 只鎖內部 `ambiguous`／requested_act=null，不把「不能回最後一句」當品質 gold。七句全句對既有 dataset/research/analysis/test 已知文字逐字碰撞須為零；不把這種檢查叫真正獨立 holdout。看見生成答案後不得改題、門檻、配對或刪除失敗。

執行順序固定為 **c0 control → c1 treatment → c0 treatment → c1 control → c2、c3、c4、c5、c6 treatment**。同時只允許一個本項產品進程；每臂 exact stop、PID 退出、該埠空閒後才下一臂。交錯次序降低所有 control 都先跑的暖機／時間混雜，但兩組各一次仍無法消除時序效應。任何一臂 hard gate 失敗就停止剩餘批次，不能補跑。

## 前置／每臂硬 gate

1. 在本 plan、dataset、來源 SHA 提交推送及只讀設計審查後才能送任何 c 題。不得改本項程式、重送 a/b 題或修 scheduler 以追分。零模型先核 c0/c1 准入、M29 真讓路 full planner、c2–c6 fail-closed；檢查 source SHA 和同載體 after-proxy request parity。真產品缺逐 byte request 記錄的限制另列。
2. 埠事前固定：c0 control/treatment 7915/7916，c1 7917/7918，c2–c6 treatment 7919–7923。每臂先核該埠無 listener；只開本次新 Safari tab；每臂全新 launcher-owned 0700 root、私有官方 ONNX 獨立 inode／SHA 與離線預熱、私有同型空 DB，不碰正式 DB／舊分頁／原始 dirty checkout。埠只隔開運輸，並非認知變因。prepare/start/verify-ready/status/stop 明傳同一 `--product-port`，same final PID HTTP ready，exact planned stop。
3. 同一 PID、session 的 zero-turn ready 後，不按 Reset。**立即在 Safari Send 前**保存不可覆寫的 Tpre：observer 時間、active DB receipt 原件與 SHA、root/PID/session、`memory_db`/reset0/tick0/finish0、兩 DB empty/profile0、web log empty。從 brain 建立起至 Send 的背景 idle threshold 為 45 秒；Tpre 距 Send 須 ≤10 秒，且 Send 後還要核 tick。缺任何欄位、Tpre tick>0 或開始前狀態漂移，該 arm 不送，整批 strict FAIL；不以另一埠／root 補跑。
4. Safari 用當輪原文一次，觀察泡泡與原生 runtime graph；結束後**立即**保存獨立 Tpost receipt 原件／SHA、observer 時間、同 root/PID/session、active `memory_db`/reset0/tick0、finish0→1、1 個當輪 episode/正確 log、DB 路徑不漂移。若 tick 在 Send→Tpost 增加，即使 `passive_decay writes=0` 也 strict FAIL；Tpost 慢到可能已有 response 後背景 tick 亦保守 FAIL，不放寬成只看 write 數。必要時另做事前 scheduler 控制設計，不能在本批暫停背景執行並照算原比較。
5. 逐臂核真正 full-planner 同模型 digest／顯式參數、M29/certificate/act-handoff/selected plan 的 trace、role/User hash，安全和來源 gate；真 trace 不直接證精確非介入 prompt parity。最終可見回覆須自然日文、身份／人格不退化、無未給疲勞／成功／私密心理斷言。c0/c1 須短且真正交付明示行動，僅重述事件算未達。c2–c6 不得拿錯直接行動證書；c6 不得編造／洩露地址。泡泡、raw、guard、utterance、episode、graph 要對同輪 ID/文字，無正式記憶污染。

逐臂量實際 provider generations/tokens、prompt/completion、向量操作、user wait、JSONL bytes／儲存成本；每臂≤3 generations、全批≤20,000 provider tokens、預設 user wait≤20 秒，超出停。帳本缺失／不可讀不能當零，成本上限無法核就停為 strict FAIL。分開標示 **比較機制 gate**（上述環境、同載體、來源、tick、route、安全、回覆／writeback、成本；任一失敗則整批 strict FAIL）與 **完整產品圖像交付 gate**（另需 native Safari PNG/AX 真正留存）。既有工具若仍不能保存 native PNG/AX，後者 `saved-visual=FAIL`，不得拿伺服器 JSONL 冒充；可另報當場 UI 觀察，不能稱完整產品 PASS，也不把它偷偷當同模型機制效果不存在。需留失敗與原件、planned stop／只關自己的 tab；本批不新增永久儀表板。

## 分析及後續

c0/c1 事前二元 proxy：明示 requested act 是否交付、是否僅事件 echo、是否過度斷言、自然日文／安全；列兩臂可見原句、同模型設定、成本差，不以單例主觀口味算顯著優勢。c2–c6 是來源／否定／衝突／保護負控。若 certificate prompt 到達但 selected plan／可見回覆不變，明確回報「handoff 交付不等於效果」；若 treatment 改善但成本大、或 control 同樣達標，也明列。缺真人偏好與正式 temporal holdout，不能聲稱更懂使用者、學術總優勢。下一個研究設計仍需同設定 A=default、B=同 planner 無 handoff、C=同 planner 有 handoff 的前瞻 total-effect，比較強 LLM 與跨輪結果另有正式 gate。
