# 目前任務卡

更新：2026-10-23。**P4 產品 Web 每輪計算成本收據已完成零模型實作，fresh cost0/cost1 模型與 Safari 尚 0/2。** 原 Web brain 不接帳本的缺口，已以固定 `URUHA_WEB_COMPUTE_LEDGER=1` opt-in、逐輪 ID/scope/checkpoint、raw-free private 收據與 post-turn 原生圖卡補上；歷史產品入口／launcher 原檔不改，新一次性受控啟動 adapter 傳旗標。前瞻 plan、題本、SHA 和架構修訂已在實作前推既有 PR #435。聚焦 **14/14**、總受影響回歸 **181/181**、compile/diff 與產品 SHA 見 `analysis/p4_product_turn_compute_receipt_zero_model_result_2026-10-23.md`；這僅是契約/接線，不是 fresh 生成或完整成本。**唯一續接點：**核產品 SHA/diff，精確提交本次 ledger/base Web/新 adapter/新測試/報告/SHA/本卡並 push 核 PR exact head；其後不同新 0700 root＋新進程，官方私有 ONNX 離線預熱、各自 zero-turn/T0，真 Safari 各送凍結 cost0/cost1 一次／0 retry，核最終日文與來源角色、原生展開圖、private JSONL/圖 item ID、成本 coverage/權限、記憶隔離與 ≤20 秒。native Safari PNG/AX 無文件化落盤路徑，saved-visual 仍 FAIL；embedding token、TTS、啟動／背景、OS 資源及正式比較仍 pending。h0–h3 4/4 狹義與整體 strict FAIL 不改；無關 `output/graduate_application_report/`、正式 DB、原始 dirty checkout不碰，Goal active。

**獨立只讀 gate review（2026-10-23）：窄義 h0–h3 4/4，但完整產品／教師展示整批 strict FAIL。** Saved native 視覺證據 FAIL，逐題記憶隔離未達，全管線成本 pending；不能將同一 root 的四個 session 冒充四個獨立樣本。詳見下段本輪狀態與產品收據。
下段「memory DB 0」僅指這次私有 root 的資料庫；正式使用者資料庫未被本輪測試讀寫或聲稱核驗。

更新：2026-10-23。**P4 接收地點 history 綁定修正後，前瞻 h0–h3 原生 Safari 已各送一次／0 retry：窄義 4/4 通過，完整產品／展示仍非 PASS。** 全新 0700 私有 root `uruha-product-guzeagin`、官方 ONNX 私有離線預熱／0 下載、zero-turn 同 PID、T0 空 DB 之後，正例 h0/h2 的 `accepted_verified + changed=false + current_assistant_synced + pre_episode verified` 成功到可見日文、guard、utterance、episode；h1 決定地與 h3 引文負控皆 `abstain_unchanged`。四輪 ≤20 秒，平均 13.031875 秒、最大 15.6781 秒；raw 4 行 SHA `770b503ebb89c456cf4531f559e827b6c103f41a2356d57cef0dc08f6323843f`，session DB episode 4/profile 0、正式 memory DB 0；PID 33504 planned stop／7894 vacant，僅關本次 Safari tab 53→52。圖在 reload 後仍顯示，但聊天泡泡不保留；**native PNG/AX 未持久保存，saved-visual FAIL；四個 session 共用私有記憶 DB 且 h3 檢索前題，不是獨立案例；全管線 token ledger pending**。h3 的說話者／決定者仍有輕微歧義。完整證據與限制見 `analysis/p4_reported_receipt_destination_history_binding_fresh_product_result_2026-10-23.md`；舊 r0 strict FAIL 不改。**唯一續接點：**先獨立審查本報告、diff/status，只提交／推送本報告與本卡，核 PR #435 exact head。其後若要提升展示與研究證據，必須先凍結新的 source-disjoint 題、逐題獨立 root、持久原生視覺收據與完整成本採集；已曝光 h0–h3 不重播追分。正式同模型對照／人評／temporal holdout、VRM/Function Calling 一體化仍 pending，Goal active；無關 `output/graduate_application_report/`、原始 dirty checkout與正式 DB 不碰。

更新：2026-10-23。**P4 接收地點角色第一次 history 修正完成零模型／接線層，fresh h0–h3 Safari 尚 0/4。** 只在新 adapter 中，對符合來源且未保護的句子，按最後 visible 與當輪 assistant history 是否相同決定同步，沿既有 intent/四類 counter；前一筆 user row 必須同 intent，有 `jp_summary` 時還核當輪摘要。非 raw pre-episode reason code 不放寬 gate。獨立只讀審查的「同 intent 錯輪可被改寫」及 user intent 不符反例已補 guard 與測試；極簡無摘要 fixture 保留相容，不能當全面錯輪證明。新＋舊聚焦 **31/31**、受影響相鄰 **183/183**、compile/diff、歷史 P4-Z/D SHA 通過；0 新 model/download/formal DB 寫入。詳見 `analysis/p4_reported_receipt_destination_history_binding_zero_model_result_2026-10-23.md` 與新 product SHA。**唯一續接點：**核 product SHA、精確 diff/status 與只讀審查，只提交新 adapter、新測試、結果、SHA、本卡並 push 核 PR #435 exact head；再新 0700 隔離 root 離線預熱、zero-turn/T0，原生 Safari 凍結 h0–h3 各一次／0 retry。任何 hard gate 失敗整批 strict FAIL；舊 r0 不重送。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰，Goal active。

更新：2026-10-23。**P4 接收地點角色首次失敗的第一個修正設計與全新 h0–h3 題已事前凍結，尚 0 修正 code、0 新模型／Safari。** 唯讀／零模型證實一條因果路徑：上游已把 guard 入句改正時，新 adapter 只因 `visible == reply` 跳過 short history 同步，pre-episode 會擋下；這不能回推為 r0 唯一失配。單一變因是只要最後 visible 與當輪 assistant history 不同便以既有精確意圖／計數同步；不能放鬆 source/guard/episode gate。新 2103／2104 年日期、物件、地點建立前 repo 搜尋 0 命中，作者題不是 holdout；設計、四題、before SHA 在 `research/p4_reported_receipt_destination_history_binding_correction_design_2026-10-23.md`、`datasets/p4_reported_receipt_destination_history_binding_probe_2026-10-23.json`、同名 preimplementation SHA。**唯一續接點：**核 SHA/diff/status，只提交推送設計、題、SHA、本卡並核 PR #435 exact head；其後只改新 adapter 與新聚焦測試，跑受影響回歸，commit/push 新 product SHA；再新隔離 root 原生 Safari h0–h3 各一次／0 retry。舊 r0 不重播、不追分。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰，Goal active。

更新：2026-10-23。**P4 接收地點角色第一批 fresh 原生 Safari 在 r0 strict FAIL，已停止，r1–r3 未送，r0 不重試。** 新 opt-in 產品 `9999e41` 已在真題前推 PR #435；26/26 聚焦、109/109 相鄰零模型通過，但 Safari r0 約 20.618 秒後只有 `錯誤`、無最終泡泡／圖。stderr 指向 `uruha_reported_receipt_destination_relation_p4.py:226` 的 pre-episode mismatch；尚未證實是哪一 predicate。新 0700 私有 root、官方 ONNX 私有離線預熱、zero-turn 同 PID 啟停與 T0 空 DB 均完成；產品 PID 29382 exact planned stop、7894 vacant，停止後 memory/session embeddings 均 0、無 conversation log，Safari 只關本次新分頁。原始 stderr SHA、執行邊界與未覆蓋項見 `analysis/p4_reported_receipt_destination_first_fresh_failure_2026-10-23.md`。**唯一續接點：**先推本次失敗紀錄與本卡，接著零模型／唯讀定位 pre-episode 各 predicate；若有單一因果，另立事前凍結的最小修正與全新 source-disjoint Safari 題，已曝光 r0 不追分、舊結果不改。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰，Goal active。

更新：2026-10-23。**P4 接收地點角色新 opt-in adapter 已完成零模型／接線層，但 fresh Safari 尚 0/4，不能稱產品 PASS。** 凍結設計與第二版架構修訂分別已推 `1a5f27d`／`cde6b69`；P4-Z、D authority／entry／controller 保持原 SHA。新 adapter 只認單句第三者 `...受け取る場所を...に決めたらしい`，對 wrong-role 可見候選先依來源修正，再走既有 guard 一次，末端核 source-role、base guard digest、當輪 short history；pre-episode 若 trace 缺失或後續改壞即阻止 episode，錯誤時回滾 short history；第三者報告抑制 profile facts，另立原生 blackboard 節點／可讀 signal。獨立只讀審查抓的 missing-trace 寫入風險、第三人稱地名 `が好き` 偏好污染均補負例。聚焦 **26/26**、相鄰含凍結 SHA **109/109**、compile／entry import／controller help／diff check 通過；另有既存 `test_p4_ab_source_proposition_graph_summary.py` 一條硬編舊 observatory SHA 失敗，HEAD 的 `uruha_memory_observatory.py` 已是不同 SHA，與新 adapter 無關，不能稱整 repo 全綠。新 product SHA 8 檔列於 `research/p4_reported_receipt_destination_product_freeze_2026-10-23.sha256`。**唯一續接點：**diff review 後精確提交／推送本批四新檔、freeze／本卡並核 PR #435 exact head；新私有 0700 root／官方 ONNX 離線預熱／0-turn same-PID 啟停／T0 空 DB 後，用真正 Safari 依凍結 r0–r3 各送一次、0 retry，逐輪核角色、日文、原生 node／泡泡＝raw＝guard＝history＝utterance＝episode、profile、成本及 ≤20 秒。任一門檻失敗整批 strict FAIL；未保存 native PNG/AX 和 full token ledger 獨立 pending。舊 f2/c0/c1 不重送，Goal active，無關 `output/graduate_application_report/` 不碰。

更新：2026-10-23。**P4 接收地點角色第一版原檔擴充已停止且完全回退；改走新 opt-in adapter。** 聚焦契約曾 24/24，但受影響回歸 98 passed／17 failed，全是歷史 P4-AA/AB/AC 前置 P4-Z SHA 凍結違反；不能忽略或改弱舊測試。P4-Z 已恢復 `e181d1c193be74ecd5d5cadd9628216dbfbfb7cfb498c31fa6531936004c1b58`，D 既有入口/controller 也不改。原先已凍結題與單變因不變；`research/p4_reported_receipt_destination_architecture_amendment_2026-10-23.md` 在第二版實作前修正允許檔為新外層 adapter、薄產品入口與 detached controller、新聚焦測試，末端 guard／history／episode 仍需 fail-closed。**唯一續接點：**先只提交本修正紀錄並核 PR #435 exact head，然後新檔實作、聚焦及舊 SHA 回歸全通過、product freeze 與推送；最後才跑凍結 r0–r3 新隔離 Safari 各一次。尚無任何新 model/Safari 輪次；舊 f2/c0/c1 不重跑。無關 `output/graduate_application_report/` 不碰。

更新：2026-10-23。**P4 接收地點命題角色：只讀原因定位與新 source-disjoint 設計／四題已在實作前凍結；尚 0 產品修改、0 新模型／Safari。** 舊 f2 private trace 顯示 M31 已把 `場所を南扉に決めた` 改成 `南扉で…場所を決定`，M32 忠實沿用；M39／日文 guard 均 unchanged，P4-Z `source_pattern_unavailable`。不是 CSS／圖形失敗。新單變因僅擴充現有產品 P4-Z 的「第三者傳聞決定接收地點」來源句關係檢查與有來源的短日文表達，保留日期附著範圍未知；不改 M31/M32 模型或正式資料。`research/p4_reported_receipt_destination_relation_design_2026-10-23.md`、`datasets/p4_reported_receipt_destination_probe_2026-10-23.json`、同名 preimplementation SHA 列明 before、允許檔、兩個新正例／兩個負控、嚴格 Web/Safari／圖／DB／成本／安全門檻。新日期、物件、地點建檔前 tracked Git 搜尋 0 命中。**唯一當前續接點**：核 SHA/diff/status，只提交設計／題／SHA／本卡並推 PR #435 核 exact head；其後才在允許檔案做 source-slot relation 最小實作、零模型與受影響回歸、product SHA/提交推送，再用新隔離 root 原生 Safari 四個新來源各一次、0 retry。舊 f2/c0/c1 不重送、不改分；native PNG/AX、完整 token ledger、舊 D2/D5／c1 supersession、正式研究、人評／holdout、VRM/Function Calling 全部仍 pending。無關 `output/graduate_application_report/` 和原始 dirty checkout 不碰，Goal active。

更新：2026-10-23。**P4-D-F-C CSS 對比修正 fresh 原生 Safari 已完成：窄義焦點圖與對比 PASS，完整教師展示／產品 strict FAIL。** 設計 `84540b7`、產品 `02c3e33` 均先於模型題推 PR #435 exact head；11/11 聚焦、208/208 受影響零模型回歸與 HTML 逐字相同只證 CSS 單變因。新 0700 隔離 root `uruha-product-rkaru1p7`，官方 SHA ONNX 私有獨立 inode 預熱、zero-turn 同 PID ready/planned stop、T0 空 DB 後，Safari 明確實際大小 100%，同 session 凍結 c0/c1 各送一次、0 retry。78/113→81/121 原圖保留，六卡 input→D→selected→utterance→output→trace episode 當輪與 reload 正確；標題／五段箭頭在深底亮色可辨，無水平捲動。泡泡＝raw＝guard＝blackboard utterance 2/2，episode 0→1→2、profile 0，wait 15.7816／11.653 秒；私有 raw 2 行／3,609,554 bytes／SHA `2e4ea96b12ba063c11e9e02335c387082674341f3e55bb79a8c853945eb728f4`。兩個 PID planned stop、7894 vacant；只關本次 Safari tab 53→52。**未保存 native PNG/AX，saved-visual FAIL；c1 supersession unresolved，不能稱永久撤銷；舊 f2 命題角色、D0–D10／D2／D5 等原 FAIL 不變。** 詳見 `analysis/p4_d_focus_contrast_fresh_product_result_2026-10-23.md`；本結果 `32f7d7a` 已推 PR #435 exact head。**唯一當前續接點**：針對舊 f2「在南扉決定接收地點」的命題角色歧義先做只讀原因定位，再凍結單變因的新 source-disjoint 題與 before／成功失敗／成本／安全門檻；不可重送 f2、c0/c1 或改寫舊結果。native Safari PNG/AX saved-visual 保留獨立未過門檻，不用其他圖冒充。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰；正式比較／人評／temporal holdout／VRM／Function Calling 與 Goal pending。

更新：2026-10-23。**P4-D-F-C CSS-only 產品修正／零模型驗證已完成；fresh c0/c1 Safari 尚未跑，不能稱產品 PASS。** 凍結設計／source-disjoint 題／修改前 SHA `84540b7` 已先推 PR #435 exact head。`uruha_memory_observatory.py` 只增標題子 span 直接亮色及 SVG path 直接亮色 stroke 兩條 CSS（+141 source bytes），renderer HTML／graph/Web/D gate/回覆/DB 不變。新舊在記憶體對 c0/c1 HTML 逐字相同（27,867/28,166 bytes 均無變）；暖機 51 次中位 c0 1.351→1.312ms、c1 1.351→1.341ms（噪音，不稱速度改善），0 模型。聚焦 11/11、受影響 208/208（9 warning）、compile/diff/Web Blocks 通過，獨立只讀 diff review 無 blocker；靜態色值不等於 Safari 實際對比。見 `analysis/p4_d_focus_contrast_zero_model_result_2026-10-23.md` 與 product SHA。**唯一當前續接點**：核 product manifest/diff/status，僅提交 CSS/test/結果/SHA/本卡，push 並核 PR exact head；然後新 0700 隔離 root 及 zero-turn，原生 Safari 用凍結 c0/c1 各一次 0 retry，先設實際尺寸 100%，逐輪觀察標題／箭頭及 raw/DB/reload。不能保存 native PNG/AX 仍保留 saved-visual FAIL；不重播 f0/f1/f2。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰；Goal active。

更新：2026-10-23。**P4-D-F-C 低對比單變因已事前凍結，尚未改產品 code／跑新模型題。** 前一批結果 `f6684ed` 已推 PR #435 exact head，窄義 D 主鏈 PASS、整體展示 strict FAIL 保留。只讀定位：標題 `<span>`／SVG `<path>` 的亮色僅來自父層，原生 Safari 目視兩者低對比；覆蓋來源未經 computed style 證實。新設計只允許焦點圖 CSS 葉節點直接設色，c0/c1 為未曝光的 2092 年 source-disjoint 新題，日期／物件／兩地名在建檔前 tracked repo 碰撞 0；見 `research/p4_d_focus_contrast_correction_design_2026-10-23.md`、`datasets/p4_d_focus_contrast_probe_2026-10-23.json`、同名 preimplementation SHA。**唯一當前續接點**：核 manifest/diff/status，只提交本設計／題／SHA／本卡，push 並核 PR exact head；再僅改 CSS＋局部測試，零模型及受影響回歸後 commit/push，最後新隔離原生 Safari c0/c1 各一次 0 retry，明確 100% 實際尺寸與低對比核驗。不能保存 native PNG/AX 仍是 saved-visual FAIL；不重播 f0/f1/f2。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰；Goal active。

更新：2026-10-23。**P4-D-F fresh f0/f1/f2 原生 Safari 已完成；窄義 D 主鏈圖改善 PASS，整體旁觀者展示／產品 strict FAIL。** 凍結設計 `c4d413c`、產品 `c83306f` 皆在真題前推 PR #435 exact head。新隔離 0700 root `uruha-product-gd17k6wr`，官方 SHA ONNX 私有複本／封下載預熱 1×384、zero-turn 同 PID ready/planned stop 與空 DB 後，產品 PID 95420 同 PID ready；同 Safari session f0/f1/f2 各一次／0 retry。f0/f1 焦點 6 卡（原圖 78/113、81/121）與 reload 正確；f2 朋友來源無假 D 焦點，reload 仍無。泡泡＝raw＝guard＝blackboard utterance 3/3，session episode 0→1→2→3、profile 0，三筆 SQL 各自來源＋回覆相符，等待 16.3011／11.8980／11.8945 秒；私有 raw 3 行／6,489,289 bytes／SHA `e93a8d1b640b783afde14be1c16af9c600440f7e9fdc9de061d88512552596d0`。但原生 Safari 焦點標題／箭頭低對比、100% 縮放未獨立記錄、PNG/AX 未落盤，f2 日文有地點角色歧義；故**不可稱 teacher-ready 或完整產品 PASS**。planned stop、7894 vacant，只關本次新 Safari tab 53→52。詳見 `analysis/p4_verified_main_chain_focus_fresh_product_result_2026-10-23.md`。**唯一當前續接點**：fresh 獨立 reviewer 本輪受 Codex 額度限制，主代理已非獨立複核 raw/SQLite/控制記錄；核 diff/status，僅提交本結果＋本卡、push 並核 PR #435 exact head；再事前凍結單變因焦點圖 CSS 對比修正與新的 source-disjoint 題／判準，f2 語義表面另案，不重播 f0–f2／舊 D 題。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰；Goal active。

更新：2026-10-23。**P4-D-F 零模型產品實作已完成；fresh f0/f1/f2 模型／Safari 尚未跑，不能稱產品 PASS。** 設計／題／preimplementation SHA `c4d413c` 先於程式推 PR #435。`uruha_memory_observatory.py` 僅新增 verified D 的原圖主鏈折疊呈現：input→D→selected→utterance→output，真 trace-reported episodic write 才接寫回；+N 標明省略原節點，完整原圖一鍵展開。D／selected 訊號與 input/output detail 全文可見；collector/生成/記憶/DB/Web/D gate 不改。新 test 聚焦 8/8（f0/f1、f2、13/13 凍結結構負控與額外假寫回），相鄰 **205/205**，compile/diff/Web Blocks 通過；獨立只讀 review 的第二種 episodic write 唯一性問題已修。舊 D-G raw 只作離線顯示成本對照：78/113、81/121 原圖未刪，HTML +10,130／+10,146 bytes，render 中位 +0.078／+0.261ms，0 新模型呼叫。詳見 `analysis/p4_verified_main_chain_focus_zero_model_result_2026-10-23.md` 與 product SHA。**唯一當前續接點**：核 SHA、diff/status，只提交本項 renderer/test/product SHA/報告/本卡，push 並核 PR #435 exact head；再按 frozen f0/f1/f2 做全新隔離原生 Safari 逐輪／reload／原圖展開、SQLite／延遲／成本驗收，各一次 0 retry，保留任何 FAIL。無原生 PNG/AX 持久證據時 saved-visual 仍 FAIL；不重播 dg0/dg1/D0–D10。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-23。**P4-D-F 旁觀者可讀圖像的新單變因設計與未曝光 f0/f1/f2 已事前凍結，尚未改產品 code／跑模型／Safari。** D-G 收尾 `24145a7` 已推 PR #435 exact head；只讀重建兩輪圖為 78/81 nodes、113/121 edges、2890×2312；132px 卡及單行 ellipsis 令正確 D 訊號截斷。新焦點視圖將由同一原圖可驗的 `is-main` 記錄順序折疊 input→D→selected_plan→utterance→output，真 `is-active` episodic write 存在才顯寫回；完整原圖一鍵展開，不動 collector/回覆/DB。新 2089 年日期／物件／地點在建檔前 tracked repo 碰撞 0；詳見 `research/p4_verified_main_chain_focus_design_2026-10-23.md`、`datasets/p4_verified_main_chain_focus_probe_2026-10-23.json`、同名 preimplementation SHA。**唯一當前續接點**：先核 SHA、精確 diff/status，只提交設計／題／SHA／本卡，push 並核 PR #435 exact head；其後按凍結邊界只改 renderer／新測試，零模型／受影響回歸／成本，提交推送後才用新隔離 root 原生 Safari f0/f1/f2 各一次、0 retry。D-G 狹義成功與 D whole-batch FAIL 均不改；本項無原生 PNG/AX 落盤仍為 saved-visual FAIL，不得稱全部展示或研究已通過。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-23。**P4-D-G 新隔離原生 Safari 驗收已完成：權限圖訊號狹義 2/2 當輪＋2/2 reload 正確，但整體旁觀者展示／D 產品仍 strict FAIL。** 設計 `8c17b68`、產品 `9261ed8` 已先於真題推 PR #435；零模型 2/2 source-disjoint 正例、13/13 凍結結構負控及新增矛盾負控，受影響 178/178。新 0700 root `uruha-product-w2l5c6o1` 的官方 SHA ONNX 獨立 inode 0600 複本、封下載預熱 1×384／0 嘗試；zero-turn PID 88049 同 PID HTTP ready、T0 DB embeddings 0、planned stop；產品 PID 88414 同 PID ready。Safari session `20261023_013453_8090f27b` 只送凍結 dg0/dg1 各一次／0 retry：普通 D 與明示訂正 D 的泡泡＝raw＝guard＝utterance，圖 D node／selected-plan signal **2/2 正確**，各自 reload 仍還原；T0/T1/T2 episode 0→1→2、profile **0→0→0**，SQLite 各自來源＋回覆 1 筆，等待 17.0986／11.4951 秒（2/2 ≤20）。raw 2 行／3,434,242 bytes／SHA `09b02eb9302c116201bd5d4007a1c7c2bb3a640a8033c86c7ae07ee5dddcf51d`；stderr 無下載／error；planned stop、7894 vacant，只關本次 Safari tab 53→52，私有證據未刪。完整見 `analysis/p4_current_decision_graph_authority_projection_fresh_product_result_2026-10-23.md`。

**判定界線／唯一當前續接點**：真圖雖可點開且 AX 可讀，畫面仍密集、卡片文字截斷；原生 Safari screenshot/AX 沒有可落盤 artifact，完整 token ledger 未量。舊 D whole-batch strict FAIL、D2 自然度、D5 衝突值不改；正式同模型、人評/holdout、VRM／Function Calling 及 Goal pending。先對本結果做獨立只讀複核，核 diff/status，只提交本報告＋本卡、push 並核 PR #435 exact head；下一個獨立產品項應針對**旁觀者可讀圖像與持久視覺證據**先定設計／單變因新題與成功判準，不能重播 dg0/dg1 或把 D-G label 修補當成全圖自明。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-23。**P4-D-G 圖表單變因已完成零模型實作；fresh product/Safari 尚未跑，不得稱 PASS。** 凍結設計與題本先以 `8c17b68` 推 PR #435 並核 exact head。`uruha_memory_observatory.py` 僅在 D 當輪 raw／reply、重算來源 binding、terminal cert、route/guard/history、blackboard selected-plan/utterance 全一致時覆蓋 D 與 selected-plan 兩個 graph signal；其他 route／node／edge／detail／trace／回覆／DB／D gate/Web 不改。兩個 source-disjoint 合成正例、凍結 **13/13** 負控、獨立審查新增 low-road/guard/history 等負控通過；聚焦＋相鄰 **178/178** 零模型通過，compile/diff check 通過。舊 P4-AB graph summary test 3 passed/1 failed 是早於本次已 stale 的寫死 graph SHA（本批 preimplementation SHA `c716...`，舊斷言 `c95e...`），不改舊凍結追綠。詳見 `analysis/p4_current_decision_graph_authority_projection_zero_model_result_2026-10-23.md`；product SHA 已另列。D 首批 strict FAIL 不變。

**唯一當前續接點**：核 product SHA／精確 diff/status，只提交 graph collector、本批 test、product SHA、零模型報告與本卡，push 並核 PR #435 exact head；再用凍結 `dg0`/`dg1` 在新 0700 私有 root 做官方 ONNX 獨立複本/封網預熱、zero-turn 同 PID ready/planned stop 與 T0 空資料、原生 Safari 各一次/0 retry，核當輪/reload 圖與 bubble/raw/guard/episode/DB/延遲/成本，保留失敗。不可重跑 D0–D10 或宣稱 D2/D5、可保存 Safari PNG/AX、完整 token ledger、正式比較／人評／holdout 已解；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。Goal active。

更新：2026-10-23。**P4-D-G 圖表權限投影：只讀因果定位與實作前凍結已完成，尚 0 product code／0 model／0 Safari。** D 四個准入 trace 的 terminal cert、當輪來源／回覆綁定與 selected-plan marker 均存在；泛用 graph signal 優先挑舊 `intent=deterministic_semantic_commit_m32`，D cert row 又顯示 `36 fields`。非 D gate 也用 `post_gate_selected_plan_authority`，故不能全域調欄位順序。新設計 `research/p4_current_decision_graph_authority_projection_design_2026-10-23.md`、source-disjoint 純結構題 `datasets/p4_current_decision_graph_authority_projection_probe_2026-10-23.json` 與 preimplementation SHA 已凍結；新日期／地點排除本設計與題本逐字搜尋 repo 0 命中。唯一變因是對**同輪來源／回覆／terminal cert 驗證通過的 D** 改 graph `signal`，不動 D cognition、Web、DB、回覆、raw trace、node/edge topology；缺／偽／stale/foreign 退回舊圖。此項尚未證明圖或產品改善，D whole-batch strict FAIL 不改。

**唯一當前續接點**：先核凍結 SHA、精確 diff/status，只提交本設計、題本、SHA 與本卡，push 並核 PR #435 exact head；再在允許檔案做單一 graph projection 修正及 source-disjoint 零模型正負控／受影響回歸，product SHA／commit/push；其後另用新隔離來源做 prospective 真 Safari 當輪／reload 與原生視覺核對。不可重播 D0–D10、改 D 題／gold，或把圖改善當成 D2 自然度、D5 衝突值、可落盤 Safari 圖、完整 token ledger 已解。正式比較、人評、temporal holdout、VRM／Function Calling 統一驗收及 Goal 仍 pending。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-23。**D0–D10 隔離真 Safari 首批已完成；普通當輪承接 3/3、明示訂正承接 1/1 有狹義效果，但整批依凍結規則 strict FAIL，不能宣稱產品／研究總通過。** D 程式／契約/product SHA 已於模型題前以 `19a8cc4` 推 PR #435 並核遠端 head；16/16 聚焦、81/81 相鄰是零模型證據。全新私有 0700 root `uruha-product-7v817cl2` 使用官方 SHA 相同、獨立 inode 的 ONNX 私有複本與 0 下載嘗試預熱，zero-turn 同 PID ready／planned stop、T0 空 DB；產品 PID 26766 同 PID HTTP ready。原生 Safari 同一 session `20261021_222700_e34f1cd0` 依前瞻 D0–D10 各一次／0 retry。D0/D4/D9 回覆具體歸 User 的日期／地點而非泛用追問；D6 明認訂正但不自動撤銷舊值；D1/D3/D7/D10 保留角色歸屬／未知。D2 朋友引述沒有誤准入，但日文語序不自然；D5 只說有兩個地點，沒有在可見句列出兩個值；D8 安全但泛用。泡泡＝raw＝guard＝圖 utterance＝私有 episode **11/11**，D node 4/4 准入且其他 0/7，T0–T11 獨立 SQL **12/12 個檢查點 profile 均 0 rows**，session episode 0→11，另 1 consolidation；11/11 等待 ≤20 秒（均 12.9107，最大 16.6892 秒）。raw 11 行／51,242,729 bytes／SHA `1284bc9fc0d2eac1c2202c2d3f18fe84b0d1e8dadace1f4cdeee8adf6ce31529`。但 graph 的 selected-plan preview 顯示繼承的 `deterministic_semantic_commit_m32`，D node 只預覽 `36 fields`，密集截斷線圖非旁觀者自明；無可保存原生 Safari PNG/AX，完整 token ledger 不足。詳細逐輪與失敗界線見 `analysis/p4_current_decision_ack_fresh_product_probe_result_2026-10-21.md`。本次 PID 已 planned stop／7894 vacant，只關新 Safari tab 53→52；正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未動，B/C 舊 strict FAIL 不改。

**唯一當前續接點**：D 報告／本卡完成證據複核後，先對圖中「實際 D authority 已選，但 preview 仍顯示舊 intent」做只讀單因審查，確認 raw trace→graph serializer→Safari renderer 哪一層造成對旁觀者的錯誤印象；若可單變因修正，先凍結全新 source-disjoint 視覺／負控／成本／Safari 判準再實作。不可重跑 D 曝光題、改弱 gold 或把 3/3+1/1 包裝成 whole-batch 成功。D2 自然度、D5 衝突值、可落盤視覺與完整 token 成本分列獨立問題，不可與圖預覽修正合成一個補丁。正式同模型公平比較、人評、temporal holdout、VRM／Function Calling 統一驗收和 Goal 仍 pending。

更新：2026-10-21。**D 當輪 User 決定／訂正承接：opt-in 單變因產品程式與零模型驗收已完成，尚未做 D0–D10 真模型／Safari，不能稱產品 PASS。** 新入口保留 C chain，只在實際當輪 User event 上建立來源、事件、cycle、原文 SHA、typed span、選定計畫、最終日文回覆綁定；普通決定與「訂正」分型，後者不自動認定舊事實被撤銷。M31/M32 舊候選只保留 shadow 與實際成本，不作證據。final guard 後、episode 前重核來源／回覆／history；選定報告不進 factive `user_profile`，但原始話語與回覆照常進 episode。episode 後 trace／episode 只可偵測不一致並判 FAIL，**不能宣稱資料回滾**。獨立只讀 review 提出的 cert 消失、兩次決定、Unicode 控制字、草稿 history、profile 誤擷取、cycle／跨輪 stale marker 均有回歸。新 source-disjoint 聚焦 **16/16**（含真實 `run_turn_debug`、私有 DB 零模型寫回），受影響 **81/81**；compile、controller `--help`、Web `build_demo()`＝Blocks 通過，新增模型呼叫 0。`research/p4_current_decision_ack_product_freeze_2026-10-21.sha256` 固定四個產品／測試檔。這些僅是契約與隔離零模型證據，不能外推到 D Web、自然度或正式比較；B/C 既有 whole-batch strict FAIL 不變。

**唯一當前續接點**：先核 product SHA、只 stage 本 D 四檔、SHA 與本卡，diff/status review、commit/push 並核 PR #435 exact head；再依凍結 D 計畫在全新 0700 私有 root 做官方 SHA ONNX 獨立複本與無下載預熱、zero-turn 同 PID ready/planned stop、空 T0。若隔離不乾淨則 D isolation FAIL，不跑題；否則原生 Safari D0–D10 各一次／零 retry，逐輪記錄 source→plan→guard→M39→bubble→episode 與 graph、獨立 DB 快照、自然日文、延遲／成本及原生視覺保存。狹義普通承接／訂正承接／actor 回歸與 whole-batch gate 分開判；缺圖像自明、可存 Safari PNG/AX 或全管線 token ledger 仍須標 FAIL／缺證。不得重播 B/C、改 D 題／gold、碰正式 DB、原始 dirty checkout 或無關 `output/graduate_application_report/`。正式同模型比較、人評、temporal holdout、VRM／Function Calling 統一驗收與 Goal 仍 pending。

更新：2026-10-21。**P4 當輪 User 決定／訂正承接 D 項：C 失敗已只讀定位，新單變因設計與 D0–D10 未曝光題本已事前凍結；D 尚 0 product code／0 model／0 Safari。** C0/C6/C8 raw 均為 M31 rejected → M32 選 `私は…決めたんだね。` → base final guard 因 `direct_echo_certificates_not_verified` 改為 `ん、もう少し聞かせて。` → M39 原樣接受。C 入口沒有 `mixed_act_lineage_p4`，而 C8 `訂正、` 另被 plain-echo grammar 排除；不能只補 lineage 就宣稱修三輪。下一變因是 opt-in `current_user_decision_ack_authority_p4`：只從實際當輪 direct User raw 語句形成來源綁定、面向 User 的日文短承接，明示訂正作 `correction_reported` 子型且不自動撤銷舊值／選穩定現值；不放寬 base actor guard、不由 M31/M32 回聲取事實。設計與分層 gold 在 `research/p4_current_decision_ack_authority_design_2026-10-21.md`、`datasets/p4_current_decision_ack_probe_2026-10-21.json`；新日期／地點在寫入前及排除這兩檔後 repo 搜尋 0 命中。獨立只讀審查要求已補：guard 後到 episode 寫回仍有 overlay，若無前寫攔截只能事後偵測並判 FAIL，不能宣稱 fail-closed；新增模型呼叫上限明訂 0。事前原件 SHA 見 `research/p4_current_decision_ack_preimplementation_freeze_2026-10-21.sha256`。這只是 developer-authored prospective 設計，沒有 fresh generation 或產品成功證據；C whole-batch strict FAIL 不改。

**唯一當前續接點**：D 設計／題本／SHA 已提交並推送 PR #435 後，才在核准檔案做單一 authority 最小實作、零模型契約與相鄰回歸，另 freeze product SHA／推送，再隔離 zero-turn／真 Safari D0–D10 各一次。每輪獨立 DB 快照、來源／計畫／guard／M39／泡泡／episode 同一性、自然日文、圖自明與可保存原生視覺、完整成本／≤20 秒各自驗收；缺證即相應 gate FAIL。不能重播 B/C 追分、改弱 baseline、污染正式 DB 或碰無關 `output/graduate_application_report/`。正式同模型比較、人評、temporal holdout、VRM／Function Calling 統一驗收和長期 Goal 均 pending。

更新：2026-10-21。**P4 回溯決定者 C0–C9 全新隔離 Safari 十輪已完成；整批 strict FAIL，狹義決定者准入 6/6 符合前瞻條件 gold。** 設施修正 `2fbc453` 已先推 PR #435 並核遠端 head；23/23 聚焦、66/66 相鄰零模型、Web build／compile／SHA 只是設施證據。全新 0700 root `uruha-product-k2mhndim`：官方 83,178,821-byte ONNX 0600 私有複本與來源 SHA 相同、inode 不同，fresh HOME 且阻斷 Chroma download 入口預熱有限 1×384 向量、0 嘗試；零輪 PID 91138 同 PID HTTP ready／planned stop，stderr 無下載，兩個空 Chroma schema 保留作 T0。產品 PID 91657 同 PID ready；原生 Safari 同一 session `20261021_173310_1095289e` 依 C0–C9 各一次／0 retry。C1/C2 正確只說使用者曾稱自己決定，C4/C5 對第三者／未知來源棄答，C7 承認兩個互斥 User 地點而不選新值，C9 因更正保留未定；但 C0/C6/C8 三筆直接陳述仍只回 `ん、もう少し聞かせて。`，C3 自然度未證，圖雖有來源節點／箭頭卻非旁觀者自明，Safari PNG/AX 未能保存、全管線 token ledger 未量。raw 10 行／44,593,033 bytes／SHA `fb1d01c4f3ab5caf78ff2a7cb6c8b1569e56fe8e591a210e47e98fa6bc68ea85`；Safari bubble＝raw＝guard＝blackboard utterance＝私有 turn episode **10/10**，另 1 consolidation；T0/T10 DB profile 0 rows、10 輪 raw profile snapshot 均空，**逐輪獨立 DB 快照 gate 未達**；等待 **10/10 ≤20 秒**、均值 12.3257 秒、最高 15.1317 秒。服務 exact planned stop、7894 vacant，只關本次新 Safari tab 53→52。詳見 `analysis/p4_retrospective_decision_actor_fresh_product_probe_result_2026-10-21.md`。**報告與卡已只讀複核並提交／推送 PR #435；不得稱正式比較或 Goal 完成。**

**唯一當前續接點**：對 C0/C6/C8 的**直接 User 決定陳述已保存、最後卻泛用追問**做只讀因果審查，選一個來源綁定的 acknowledgment／paraphrase authority 變因，先凍結新的、未曝光 source-disjoint 正負控與安全／成本／圖／Safari gate，才可實作。不能重播 B/C 修分或改弱 gold；第三者引述、Uruha 真自稱、使用者原話、矛盾／更正及 final guard/writeback 必須是負控。圖的自明程度、可落盤視覺證據與全管線成本另列獨立交付，不合修。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰；同模型公平比較、人評、temporal holdout、VRM／Function Calling 統一驗收與長期 Goal 均 pending。

更新：2026-10-21。**P4 C 批首次啟動隔離設施已完成零模型實作，C0–C9 仍 0 model／0 Safari，不可稱產品 PASS。** 依先前已提交的 `44f5b1b` 前瞻修訂，僅在 `p4_preference_fallback_detached_control.py` 加上 `prepare` → 一次性 `start --prepared-runtime-root`；只准 product、綁私有 launcher root／receipt／實際 patched entrypoint，原子 claim，啟動前檢官方 ONNX tar 大小與 SHA、獨立 inode、六個解壓成員逐位元組一致及整棵 cache 私有性，preflight 與校準後再核。既有 default/reuse、PID/HTTP/stop 未變；起始無效 root/cache 在任何 subprocess 之前失效閉鎖，中途變造則擋在 product launch 之前。新 `test_p4_prepared_first_start_isolation.py` 含競爭啟動、錯 receipt／舊 run／不安全 cache、途中變造與成功的 mock lifecycle；聚焦 **23/23**、合併既有受影響 **66/66** 零模型通過，compile、薄入口 `--help`、base Web `build_demo()`（Blocks）與 diff check 通過。這只是驗收設施，不是認知能力或真隔離產品證據；尚待精確 SHA／commit/push/PR head。

**唯一當前續接點**：先核兩個設施檔 SHA、只 stage 這兩檔與本卡、diff/status，commit/push 核 PR #435 head；之後才用薄 local-fact controller 全新 0700 root、官方 SHA 私有獨立 ONNX 複本、fresh HOME 下阻斷 Chroma 下載並預熱，做一次 zero-turn 同 PID ready/stop、查 stderr／DB 空白，建立 T0。若 setup 不乾淨，C strict isolation FAIL 且不跑 C 題；若乾淨，才依已凍結 C0–C9 在真 Safari 各一次／0 retry，保留任何品質／圖像／成本缺證。B0–B6 strict FAIL 不改判，原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰；正式同模型比較、人評、temporal holdout、VRM／Function Calling 統一驗收與 Goal 仍 pending。

設施 product-freeze SHA-256（僅兩個實作檔）：`p4_preference_fallback_detached_control.py` = `a50c28867201afd164f031e0293c26708f7f2f34ba330455d4cc8b3adc13feca`；`test_p4_prepared_first_start_isolation.py` = `8d134074f768fc0a4101a02777cb2fbdab84f18a790988923feb64cb86f936e5`。修訂 preimplementation SHA 1/1 亦通過。這個 hash 不是模型或產品結果。

更新：2026-10-21。**回溯決定者產品修改與 18/18 聚焦、34/34 相鄰零模型測試已以 `852de83` commit/push，PR #435 OPEN 且遠端 head 完全相同；C0–C9 尚 0 model／0 Safari。** product SHA 2/2、Web `build_demo()` 與 compile 通過。繼續前只做一項隔離驗收設施修正：現有控制器首次 start 同時建 root／啟 server，無法按 C 凍結計畫在首次 server 前於私有 root 預置官方 ONNX，B 曾在 zero-turn 嘗試外部下載。前瞻修訂 `research/p4_prepared_first_start_isolation_amendment_2026-10-21.md` 限定「prepare 私有 root → 獨立官方 SHA/cache 無網路預熱 → 一次 exact-identity first start」，不改認知程式、C 題／gold、預設 start/reuse、PID/stop。**目前尚只是計畫，未更動 controller 或啟動服務。**

**唯一當前續接點**：完成上述設施修訂的只讀審查、SHA／精確 diff，僅提交修訂與本卡、push 核 PR head。再只改 `p4_preference_fallback_detached_control.py` 及新增 `test_p4_prepared_first_start_isolation.py`，先 product-free lifecycle 測試與受影響控制器回歸、compile／Web build、product SHA／diff、commit/push/PR核對；其後才依修訂做全新 0700 root 的離線 zero-turn 同 PID rehearsal，若不乾淨則 C strict FAIL，不偷跑 C 題。若準備成功，才真 Safari C0–C9 一次，保留所有舊 FAIL、圖像／成本／隔離缺證。正式同模型比較、人評、temporal holdout、VRM／Function Calling 統一驗收和長期 Goal 均 pending；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-21。**P4 回溯決定者的來源准入產品階段已實作；新 C0–C9 真模型／Safari 尚未執行，不能判產品 PASS。** 事前凍結的計畫、C 題本與 SHA 已先於產品 code 以 `67f4064` 推 PR #435；B0–B6 strict FAIL 不改判、不重播。唯一產品改動在 `uruha_local_fact_answer_authority_p4.py`，只對有日期的場所「是否うるは決定」問題，從當輪已交付且 trace 驗證的直接 User 原話生成 decision-owner 證書；同日不同事件、敏感／未准入來源、相矛盾的 place、更正、同一 episode ID 異文、來源／更正後置替換都失效閉鎖。肯定答案僅說「使用者曾說自己決定」，不推斷うるは未曾行動，也不選矛盾地點。plan→guard→final SHA、記憶監測 anchor、history 回滾與 graph receipt 已接線。不改 B0/B5、檢索／DB、M31/M32、M39、人格或 renderer。全新 source-disjoint 聚焦 **18/18**、受影響相鄰 **34/34** 零模型測試通過，compile、base Web `build_demo()`、事前 SHA 2/2、diff check 通過；圖與 episode equality 僅是使用實際 serializer 的零模型契約，尚非 Web 實測。計畫原指定的 Framework Python 3.12 缺 `colorama`，其受影響套件首次指令因環境匯入失敗；改用專案既有 `.venv/product_checks/bin/python` 3.12.10 後 34/34 通過，沒有安裝套件。產品 SHA 在 `research/p4_retrospective_decision_actor_product_freeze_2026-10-21.sha256`，本階段尚待精確提交／推送／核 PR head。

**唯一當前續接點**：先驗 product SHA、staged diff/status，僅提交本項 core、新聚焦 test、product SHA 和本卡，push 並核 PR #435 head。其後先解決**驗收設施**阻斷：現有 exact-identity 控制器首次 `start` 同時建私有 root 並啟服務，沒有「先備 root／官方 SHA ONNX 私有離線預熱，再首次啟動」入口；B 的零輪曾嘗試下載，因此不得宣稱 C 的離線隔離 gate 已過。需以單獨的 prospective 設計修訂、獨立審查及聚焦 lifecycle 測試新增 prepare→first-start 能力，或保留嚴格 isolation FAIL；不得未審手動啟動或混入認知變因。設施就緒後才依 C0–C9 凍結順序在全新私有 root 和 Safari 各一次／0 retry，核 source、自然日文、泡泡＝raw＝guard＝UTTERANCE＝episode、圖、T0–T10、≤20 秒與成本；任一 hard gate 未達則 whole-batch strict FAIL，狹義 actor 子項分列。正式同模型 LLM 比較、人評、temporal holdout、VRM／Function Calling 統一驗收仍 pending，Goal active；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-21。**目前單一項目是 P4 回溯決定者的來源准入；C0–C9 前瞻計畫與題本已寫好，尚未實作／生成／Safari。** before：B4 的完整 User 原話已由 verified `recent_turns` 交給 planner，卻選 `うるは決めたんだ。`，最後 guard／M39／Safari／episode 仍錯；不是檢索缺失。只允許改 `uruha_local_fact_answer_authority_p4.py` 增加 dated-place actor-owner 問句的來源證書與 plan→final 綁定，新增 `test_p4_retrospective_decision_actor_authority.py`；不改 B0/B5 回聲 guard、DB 檢索／寫入、M31/M32、M39、人格或 renderer。完整 before、條件 gold、十輪 developer-authored 題、第三人／未知／矛盾／更正與 zero-model 額外負控、精確命令、Safari／圖像／成本／安全硬 gate 在 `research/p4_retrospective_decision_actor_authority_plan_2026-10-21.md` 與 `datasets/p4_retrospective_decision_actor_probe_2026-10-21.json`。C2/C7/C9 同問句是**事先凍結的不同證據狀態**，不是失敗後重問；不把這批稱正式 holdout。B 批 strict FAIL 不改判。零輪啟動上批曾試外部 ONNX 下載，本批須在啟動前私有離線預熱並核 stderr 無下載。已檢查這批日期／地點在舊工作樹資料（排除無關 output）0 hit、JSON case order 10/10；仍需 preimplementation SHA、plan-only commit/push／核 PR #435 head，**在此前不能改產品 code 或跑 C 模型**。

**唯一當前續接點**：完成 C plan/dataset 只讀設計複核、SHA 與 exact diff/status，只提交 plan、dataset、SHA、本卡；push 核既有 PR head。其後只在允許檔案實作角色准入與新聚焦測試，先跑 plan 內 exact 零模型命令、affected regression、compile/Web build、diff/product SHA，提交推送後才以全新 0700 root 真 Safari C0–C9 各一次。缺 direct User 憑證、同日不同 event、引文、summary、敏感、矛盾／更正不能偷自稱或硬選地點；後置可見回覆／history／graph／SQLite 一致。任何品質、隔離、visual、cost gate 未達 whole-batch strict FAIL，狹義 actor 效果另列。正式同模型比較／人評／temporal holdout、VRM／Function Calling 統一驗收仍 pending，長期 Goal active；原始 dirty checkout、正式 DB、無關 output 不碰。

更新：2026-10-21。**B0–B6 source-bound prior User decision/place 的首輪真 Safari 已完成，整批 strict FAIL；不重跑曝光題追分。** 產品 `1d9a263` 已先推既有 PR #435 並核對遠端 head，零模型聚焦及相鄰 **346/346**、preimplementation/product SHA 通過，只屬程式證據。全新 0700 隔離 root、同 PID 零輪啟停、官方 SHA ONNX 私有離線預熱、空 T0 後，Safari 同一 session 七題各一次／0 retry：B1 正確從一筆直接 User episode 找回完整地點，B3 沒把朋友引述當 User 決定，B6 對兩筆相矛盾的直接 User 決定列出兩處並追問；但 B0 只回固定澄清、**B4 錯說「うるは決めたんだ。」**，B5 亦只回固定澄清，B2 日文可懂但生硬、自然度不能判 PASS。B4 的原始 User 決定已在交付記憶中，不是資料遺失，而是回溯 actor-owner 的 planner/最後回答准入缺口；B0/B5 則是確切回聲 guard 不認已驗證但改寫的 User 陳述，兩因不可合修。Safari 泡泡＝raw＝guard＝graph utterance 7/7，session DB 7 turn episodes＋1 consolidation，profile T0–T7 全 0 rows／同 digest，逐輪等待 7/7 ≤20 秒、平均 12.4711 秒；**零輪啟動曾嘗試外部 ONNX 下載，不能稱整段 setup 離線；Safari 圖像無可用落盤證據、自明圖示不足、全管線 token／網頁 bytes 未量，隔離／visual／cost gate 均不可判 PASS**。完整逐輪與 raw SHA 見 `analysis/p4_source_bound_prior_user_decision_recall_fresh_product_probe_result_2026-10-21.md`。服務 planned stop、7894 vacant、只關本次新 Safari tab；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。以下 B「尚未跑／下一步先跑 Safari」均為歷史，不能覆蓋此節。

**唯一當前續接點**：先只讀複核 B 報告與本卡，僅提交這兩檔、push 並核 PR #435 head。其後優先對 B4 設計**新的、未曝光、source-disjoint** 回溯角色所有權任務：before 是 User 原文已傳入但 planner 選錯 Uruha 主語；單一變因為根據已驗證直接 User 來源約束「誰作決定」問答的最後准入，不改 DB 檢索、M31/M32、角色公開資料或 B0/B5 guard。先凍結前瞻題、第三者／未知／矛盾／更正／引文負控、條件 gold、允許檔案、成本、自然日文、安全、圖／Safari／≤20 秒硬 gate，再實作、零模型與新隔離 Safari 各一次。B0/B5 的已驗證改寫回聲另立一個變因；不可粗暴全域 `私→そっち`。至多兩個有根據修正批，仍失敗就 `REVIEW_REQUIRED`。正式同模型比較、人評、temporal holdout、VRM／Function Calling 統一驗收與長期 Goal 仍 pending。

更新：2026-10-21。**B0–B6 的單變因 source-bound prior User decision/place gate 已完成產品修改與零模型驗收，尚未跑新真模型／Safari，不能判產品 PASS。** `c7f7c85` 已先凍結前瞻 plan、七句 developer-authored 題、preimplementation SHA 並推 PR #435。只改既有 `uruha_local_fact_answer_authority_p4.py`、新增一個聚焦 test：對 dated User 自身決定場所的日文問句，只承認本輪已交付的完整 direct User recent turn 或 typed episode；不同 direct 決定不靠新舊順序硬選，明確更正未釐清則棄答；朋友引述、assistant/summary、stale trace、敏感地點、超表面長度值不當來源。plan→final SHA 綁來源；guard 改寫後 RightBrain history/四計數回滾草稿，只記實際日文回覆與原始 User 問句，避免角色污染。不另查 DB、不加模型呼叫、不改 A3/A4 或正式資料。獨立只讀審查提出敏感 value、顯式更正、history User role 反例，已補測；聚焦＋相鄰 **346/346** 零模型通過，compile、base Web `build_demo()` 與 `git diff --check` 通過。產品 SHA 12 檔位於 `research/p4_source_bound_prior_user_decision_recall_product_freeze_2026-10-21.sha256`；這些只是程式證據。

**唯一當前續接點**：核 preimplementation/product SHA、精確 diff/status，只提交本項 core、新 test、product SHA、卡片；push 並核 PR #435 head。然後新 launcher-owned 0700 隔離 root／同 PID 零輪 ready+planned stop、官方 SHA ONNX 私有離線預熱、顯式空 T0；真 Safari 新 session B0–B6 每題一次／0 retry。逐輪核 direct source B0/B5 真被檢索、B1 完整 User-owned 地點、B3 引述不轉 User、B4 不轉 Uruha、B6 兩筆矛盾不武斷、自然日文、history、guard/M39/overlay、泡泡/raw/SQLite/當輪與 reload graph 真實同字、≤20 秒及成本。保存任何 FAIL，若 Safari 圖像無法落盤則 visual gate 如實未達；whole-batch strict FAIL 不因 346 個測試改判。只 planned stop 自己 PID/關自己新分頁；正式同模型／人評／temporal holdout、VRM/Function Calling 統一驗收與長期 Goal 仍 pending；無關 output、原始 dirty checkout、正式 DB 不碰。

更新：2026-10-21。**A0–A4 結果報告與本卡已於 `328d2bf` commit/push 並核 PR #435 OPEN head 一致；舊「尚待提交」是歷史。** A 批 strict FAIL 保留。這輪只讀複核 A1 raw：直接 User 完整地點及正確 `core_message_jp` 已進決策，但 generic `memory_anchor.jp_anchor` 截到 `…琥`；surface 複製 `User:私`，sanitize 留 `:`，最終 guard 誤成 `うちは`，M39 接受。A3 身份與 A4 混合任務分案，不合修。

**目前唯一項目：P4 已檢索、來源綁定的先前 User 決定／地點回想。** 單一變因是既有 `uruha_local_fact_answer_authority_p4.py` 的 dated User decision/place 問句與直接 User 命題准入／可見交付，重用 passed `recent_turns` 或 typed `direct_episode` 憑證、唯一／矛盾棄答、plan→guard→final SHA；不查新 DB、不改檢索、M31/M32、一般 planner、A3/A4、圖與安全。新 B0–B6 developer-authored 未曝光題本、條件 gold、圖/Safari/成本/隱私/≤20s 硬 gate 位於 `research/p4_source_bound_prior_user_decision_recall_plan_2026-10-21.md` 和 `datasets/p4_source_bound_prior_user_decision_recall_probe_2026-10-21.json`，實作前 SHA 2/2；非正式 holdout／同模型優勢。

**下一步**：只讀設計複核及 `shasum -a 256 -c research/p4_source_bound_prior_user_decision_recall_preimplementation_2026-10-21.sha256`，僅提交 plan/dataset/SHA/本卡並 push 核 PR head；然後只改上述 local-fact gate 和新聚焦測試，跑相鄰零模型、compile/diff、product SHA 並先提交推送。最後新 0700 root／同 PID 零輪／官方 ONNX 私有離線預熱／空 T0，真 Safari B0–B6 各一次 0 retry，逐輪核 direct source、矛盾、日文 actor、guard/M39/overlay/episode/圖、成本、≤20s/隔離。任何硬 gate 未達 whole-batch strict FAIL，狹義修補另列；若視覺保存工具不支持則如實 fail，不能假稱產品 PASS。正式同模型、人評、temporal holdout、VRM/Function Calling 統一驗收 pending；無關 output／原始 dirty checkout／正式 DB 不碰，Goal active。

更新：2026-10-21。**P4 User-first-person actor/deixis 的全新 A0–A4 真 Safari 首輪已完成，整批 strict FAIL。** 凍結 plan／五題／SHA 在 `fea758d`、單變因產品 code／36 聚焦＋246 相鄰零模型測試／13 檔 product SHA 在 `5b76fc4` 推 PR #435 後，才用新 0700 隔離 root `uruha-product-vtfukdrn` 跑模型。零輪同 PID ready／planned stop、空 schema 與 7,864,320-byte ONNX 殘檔保存在私有 evidence；官方 SHA 私有離線預熱、T0 profile 0 rows。產品 PID 50033／Safari session `20261021_121101_3861f93b` 五題各一次／0 retry：A0 的確切 M32 User `私` 回聲改為 `そっちは…琥珀色の温室の入口…`，狹義 actor 修正通過；A1 卻回 `:うちは…琥って…`，舊地點被截斷且主語又錯；A2 沒實際引用，A3 沒說自己是うるは，A4 誠實不歸屬卻未交付雙任務。Safari final／reload AX 圖逐輪核對，泡泡＝raw＝guard＝graph utterance 5/5；raw 五行 12,871,619 bytes，SHA `dc3ce4ce4945ac47bf900a9f88f8afd0ff28b394a00cd957130d0b1237bfe02a`。session DB 5 turn episodes＋1 consolidation、完整 profile 0 rows 同 digest；M19 等待 5/5 ≤20 秒，均值 12.3024 秒。Safari PNG／AX 不能落盤、全系統 token/graph bytes 未量，故 visual/cost gate 也未達。服務精確 planned stop、7894 vacant，只關本次新 Safari tab；正式資料、原始 dirty checkout、無關 output 不碰。詳見 `analysis/p4_user_first_person_actor_surface_fresh_product_probe_result_2026-10-21.md`；**報告與本卡尚待只讀複核、commit/push，不能稱 PR ready 或 Goal 完成。**

**唯一當前續接點**：先只讀複核本 A 報告／精確 diff/status，僅提交報告與本卡、push 並核 PR #435 head。其後先對 A1「內部完整地點→可見截斷與角色誤歸屬」及 A3「內部身份正確→可見拒絕」做因果設計審查，選**一個**可歸因變因；需新 source-disjoint 題、條件 gold、成本/安全/Safari gate 先凍結再實作，不能重播 A/H/G/T/N/Q/S 修分。A4 unsupported mixed 雙任務另案，不能合修；至多兩個有根據修正批，仍敗則 `REVIEW_REQUIRED`。正式同模型、人評、temporal holdout、VRM/Function Calling 統一驗收與長期 Goal 仍 pending。以下「A 尚未跑」為歷史，不覆蓋此續接點。

更新：2026-10-21。**P4 User-first-person actor/deixis 單變因產品 code 與零模型驗證已完成；真 Safari A0–A4 尚未執行，不能稱產品 PASS。** 前瞻 plan/題/manifest 已先於 code 以 `fea758d` 推 PR #435。只改 `uruha_brain_mac.py`：移除前置無條件 `私→うち`，final guard 對平衡引文保留原字；當輪 `user_input` 重算 source-role（因原 wrapper 是 emit 後才附證書），結合 pre-guard linked event→M31→M32 父鏈、M31/M32 schema/SHA/逐字相同 User 命題與 selected core，僅對精確 User `私は…んだね` 回聲改 `そっちは…`；欠證書／改命題／多 actor/不確定則低壓不歸屬，Uruha 真自稱仍 `うち`。不改 M31/M32、ledger、圖、模型或記憶。獨立只讀審查抓到證書附加時序、事件父鏈、多 actor、畸形引號，已補 zero-model 反例。新聚焦 **36/36**，含日文守門、M32/M39、P4-W、Web graph、lineage/rewrite wrapper 的受影響合併 **246/246** 零模型測試通過；compile 與 `build_demo()` 建置通過，產品 SHA 13 檔位於 `research/p4_user_first_person_actor_surface_product_freeze_2026-10-21.sha256`。這些只是程式證據，A0 真模型可能未命中；正式同模型/人評/temporal holdout、VRM/Function Calling 仍 pending。

**唯一當前續接點**：核兩個 SHA、精確 diff/status，只提交 core、新 test、product SHA 與本卡，push／核 PR #435 head；再新 launcher-owned 0700 root，同 PID 零輪 ready/planned stop、官方 SHA ONNX 私有封網預熱、顯式空 T0。Safari 新 session A0–A4 各一次／0 retry，逐輪核 M32 coverage、User/角色/引文、guard/M39/後續 overlay/泡泡/SQLite/圖同字同 hash、source、≤20 秒、成本、無正式 DB 污染；截圖無法落盤需明列 visual gate 未達。任何 gate 失敗整批 strict FAIL，狹義 actor 改善另列；H3 unsupported mixed 舊路徑另案，不重播 H/G/T。服務只 planned stop 自己 PID、只關自己新 Safari tab，無關 output/原始 dirty checkout 不碰；長期 Goal active。

更新：2026-10-21。**P4 User-first-person actor/deixis 最終表面修正已完成實作前計畫／五句新題的草案與只讀審查，尚無新 code、模型或 Safari 結果。** H 批嚴格 FAIL 及其 `ae65b7e` 報告已推 PR #435，不重播 H/G/T。before：H1 M31/M32 把 User `私` 帶到 `私は…決めたんだね`，最後語言 guard 無條件改成 `うちは…`；M39 接受，Safari/episode/graph 都顯示錯 actor。唯一變因是最終 user-visible 的 source-bound 第一人稱轉換：只有單句、未引述、確切 User `私は…`、當輪 role/SHA/M31/M32 全證書及相同命題才改為對 User 的二人稱；引文保留，真正角色自稱仍 `うち`，證據不全失效閉鎖。M32 內部候選不改，H3 unsupported mixed 舊路徑另案。設計與 A0–A4 條件 gold 在 `research/p4_user_first_person_actor_surface_plan_2026-10-21.md`、`datasets/p4_user_first_person_actor_surface_probe_2026-10-21.json`；五句對舊 dataset JSON 逐字碰撞 0。只讀 agent 審查提醒 P4-T `speaker_ownership` 不能單獨當 User 憑證，M39/後續 overlay/episode/graph 必須核最終 hash。中文/英文 actor 正例不在本項證明範圍，正式同模型、人評、temporal holdout、VRM/Function Calling 仍 pending。

**唯一當前續接點**：核本項 plan/dataset SHA、精確 Git diff/status，僅提交 plan/dataset/SHA/本卡並 push 核 PR #435 head；再只改 `uruha_brain_mac.py` 與聚焦測試，跑受影響回歸、product SHA、diff review、commit/push；最後新隔離 0700 root/官方 SHA ONNX/T0 空 profile，真 Safari A0–A4 各一次／0 retry，逐輪核 User/角色/引文、raw→guard→M39→final→episode/graph、≤20 秒、成本和污染邊界。任何 gate 失敗 whole-batch strict FAIL，局部成功另列；至多兩次有根據修正後 `REVIEW_REQUIRED`。無關 output、原始 dirty checkout、正式 DB 不碰；長期 Goal active。

更新：2026-10-21。**H browser-bound graph hydration 的新隔離 H0–H3 真 Safari 驗收已完成，整批 strict FAIL；以下「H 尚未執行」是歷史。** 設計／題／SHA 在 `9faf1ec`、產品與 37/37 聚焦＋315/315 相鄰零模型及 product SHA 11/11 在 `0942455` 先於模型推既有 PR #435。新 0700 root `uruha-product-8c85wuj0` 的 0-turn run `788942220e9ecb46` 同 PID ready／planned stop，但意外預下載與空 Chroma schema；殘檔與空 DB 原樣移入隔離 evidence，不刪除；官方 SHA 私有封網預熱與 T0_ready 零 profile 後，產品 run `475c094aed23115f`/PID 39747 同 PID HTTP ready。Safari session `20261021_111236_ff384fd4` H0–H3 每題一次／0 retry：H0/H2 最終**及 reload** 真圖均 4 ledger/action/terminal nodes、6 native arrows，H1/H3 均只有當輪 producer、沒有回退舊正例；新 Safari 私密瀏覽無前一瀏覽器圖、reset→reload 舊圖不復活。這是相較 G 正例 reload 0/2→H 2/2 的**狹義 Web 圖交付改善**，不是整體產品 PASS。

**H 嚴格 FAIL 原因與下一步**：H1 可見 `うちは…決めた` 把 User `私` 經 visible-language guard `localized_known_terms` 誤轉成角色自稱；H3 ledger 正確 abstain 但舊回覆把引述 `検討中` 當事實且漏答跨輪地點。四輪等待 17.0973／10.9005／17.8938／11.5528 秒，4/4 ≤20；隔離 `session_db` 4 個 `turn_episode`＋1 consolidation，profile 0 rows 同 digest；raw 四行 SHA `c574f34e9d8a99179931440e89832f4a2a1fd88484a3362f4e195109368ad34a`。Safari 截圖/AX 僅在工具中觀察，無法存成 local artifacts，receipt/HTML bytes 與精確 reload 時間未量；正式人評、同模型比較、holdout、VRM/Function Calling 統一驗收仍 pending。完整證據及隔離準備異常見 `analysis/p4_browser_bound_graph_hydration_fresh_product_probe_result_2026-10-21.md`。服務 planned stop、7894 vacant，僅關本次新 Safari tab/私密視窗；原始 dirty checkout、正式 DB、無關 output 未碰。

**唯一當前續接點**：先 review 本 H 報告與精確 diff/status，只提交報告和本卡、push 並核 PR #435 head；H/G/T 原題不重送。接著以前瞻、source-disjoint 題本先凍結一個**單變因 User 第一人稱→最終自然日文 actor 保全**項目，含 direct User、引述、角色真正自稱及負控，核 selected candidate→guard→final→episode／Safari 圖；H3 unsupported mixed 舊路徑是另一個獨立項目，不能合修。至多兩個有根據的修正批，失敗保留 `REVIEW_REQUIRED`。長期 Goal active，不因圖子項改善宣稱全面人類理解。

以下 H 首輪前狀態為歷史，不覆蓋上段唯一續接點。

更新：2026-10-21。**H browser-bound graph hydration 的單一產品接線與零模型驗證已完成，真模型／Safari H0–H3 尚未執行，不能判產品 PASS。** 實作前設計／H0–H3／SHA 先於程式以 `9faf1ec` 推既有 PR #435。獨立設計審查修入 Gradio BrowserState truthy tombstone、reset 與載入/送出同 human lane、enqueue-time session check；獨立程式審查另發現 load/render 與 reset 競速，已加同 lane 與 render 後 session/index 重核。`uruha_web_ui.py` 只在 text/audio final 寫短 process-key HMAC 收據；初始圖空，page-load 用同一安全 fd 的最新完整私有 JSONL 行驗來源與 MAC，缺/偽/舊/非私有/壞行不逆掃。一般對話生成、ledger、renderer、記憶寫入與 G/T 凍結檔未改。新契約 **37/37**，舊 Web **19/19**，含 M19/M20/M24、producer graph、mixed ledger 等受影響合併 **315/315** 零模型測試通過；`build_demo` 建置成功，Python compile／diff check通過。product SHA `research/p4_browser_bound_graph_hydration_product_freeze_2026-10-21.sha256` 綁 11 檔；這不是模型或 Safari 證據。G0–G3 舊 strict FAIL 不改，正式資料與無關 output 不碰。

**唯一當前續接點**：核 product SHA／精確 Git diff/status，只提交 `uruha_web_ui.py`、`test_p4_browser_bound_graph_hydration.py`、product SHA 與本卡，push 並核 PR #435 head。然後新 launcher-owned 0700 隔離 root，0-turn 同 PID HTTP ready/planned stop、官方 SHA ONNX 私有離線預熱、T0_ready 空 profile；在真 Safari 依 frozen H0–H3 各一次／0 retry，逐輪核 final+reload 原生圖/箭頭、第二 fresh browser 無收據、reset→reload tombstone、泡泡/raw/guard/SQLite/source/actor/安全、≤20 秒、receipt/HTML/log 與可得 token 成本。工具若不能落盤 Safari 截圖與 AX 就明列 saved-visual gate 未達，整批任何 gate 失敗 strict FAIL，不能回頭重播 G/T/N/Q/S。產品證據不得外推正式同模型比較、人評、temporal holdout或 VRM/Function Calling 統一入口；Goal active。

以下 H 實作前狀態與 G 結果保留為歷史；其續接點不可覆蓋本段。

更新：2026-10-21。**G0–G3 嚴格 FAIL 結果已在 `4da9ada` 推既有 PR #435；新項 P4 browser-bound page-load graph hydration 已完成實作前設計／H0–H3 條件題與獨立只讀複審，尚未有新程式或模型結果。** before：G0/G2 最終 Safari 2/2 真 ledger 4 nodes/6 arrows，reload 0/2 空圖；`build_demo()` 只在啟動時計算 flow_html。只有 server runtime session 而無瀏覽器身分不能自動讀最新圖，因 `USER SIGNAL` 含 User 原文。唯一變因是同瀏覽器最後交付輪次的短 HMAC 收據放 `gr.BrowserState`，頁面載入時只讀當前 session／最新私有 log 且驗證收據才還原圖；缺／偽／舊／壞最新行／非私有 log 全空，不退回舊 positive。初始圖空、chat 不恢復、語義／生成／記憶不改。新 plan/gold 位於 `research/p4_browser_bound_graph_hydration_plan_2026-10-21.md`、`datasets/p4_browser_bound_graph_hydration_probe_2026-10-21.json`；對既有 dataset JSON 日期／地點逐字碰撞 0。獨立審查抓到 reset 與送出交錯、Gradio BrowserState 不儲存 falsy 清除值，已在實作前補入同 lane／enqueue session 核對、truthy tombstone 與負控；未見其他 freeze blocker，實際 reload 時序仍需 Safari。H 是 Web 開發題，非 holdout；H1 actor 與 H3 舊路徑品質仍列硬 gate，不因只改 graph 放鬆。

**唯一當前續接點**：重算並核 `research/p4_browser_bound_graph_hydration_preimplementation_2026-10-21.sha256`；精確 Git diff/status，只提交 plan/dataset/SHA/本卡，push 並核 PR #435 head。其後才改 `uruha_web_ui.py` 與新聚焦測試：final-only BrowserState receipt（text/audio）、reset truthy tombstone 與同 lane／enqueue session check、load callback 只最新私有行且 browser proof 匹配；負控／隱私／無逆掃 contract，受影響回歸、product SHA、diff review、commit/push。再新隔離 root/真 Safari H0–H3 每題一次，final/reload 原生圖、第二無收據瀏覽器、泡泡/guard/記憶/來源/actor/安全/≤20 秒、成本與逐輪快照；圖像檔若無法落盤如實列未達。任何 gate 失敗仍 strict FAIL，不重跑 G/T/N/Q/S。正式比較、人評、temporal holdout、VRM/Function Calling 統一驗收 pending，Goal active；不碰原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/`。

以下 G 結果與更早內容仍有效，但續接點以本段為準。

更新：2026-10-21。**P4 Web final/reload graph evidence delivery 的 G0–G3 真模型／Safari 已完成，整批 strict FAIL；下段「G 尚未執行」是歷史。** 凍結 plan/dataset/SHA 先於程式於 `f075b22` 推 PR #435；code/19 聚焦與 276 相鄰零模型測試及 product SHA 10/10 於 `e3856b4` 推後才跑。新 0700 隔離 root、0-turn 同 PID ready/planned stop、官方 SHA ONNX 私有離線預熱、T0_ready 空 profile，Safari session `20261021_071658_c45458fa` 的 G0–G3 各送一次／0 retry。G0/G2 最終 Safari 原生 ledger/action/terminal 圖 **2/2 有 4 nodes/6 arrows**，但兩輪 reload **0/2** 空白；G1 `私`→`うち` actor FAIL，G3 ledger 不接管正確但舊回覆錯把引文當事實並漏回想。完整逐輪與未落盤 PNG/AX 限制見 `analysis/p4_web_final_graph_evidence_delivery_fresh_product_probe_result_2026-10-21.md`。raw 四行 SHA `eb58656c1395a034f4f2cd913dd947e71172721a0311b52344c2033d9a3bb43b`；wait 4/4 ≤20 秒、均值 13.4497 秒；episode 0→4、完整 profile 0 row 同 digest；product planned stop／7894 vacant，只關新 Safari tab 53→52。凍結計畫把預設 log 誤寫為私有；實測既有 0755/0644，修正只在新隔離 0700/0600 log 複製 witness，不修改凍結原文。T/N/Q/S 舊 FAIL 不改判，正式同模型、人評、temporal holdout、VRM/Function Calling 統一驗收 pending，Goal active。

**唯一當前續接點**：先獨立只讀審本 G 報告／diff，只 commit/push 報告和本卡並核 PR #435 head。然後針對已定位 reload 問題做**全新 source-disjoint 前瞻 page-load graph hydration**：`build_demo()` 只在 server 啟動時設 flow_html、無 Gradio `load` callback；凍結新的正負控、gold、成本、允許檔案及 SHA 後，僅在**瀏覽器綁定 owner proof**、當前 runtime session 與最新一筆私有 log 都相符時載入圖。圖的 `USER SIGNAL` 含原文，單靠 server session 會跨訪客洩漏；不能只恢復圖卻宣稱避免了 chat 資料洩漏。缺／錯 browser proof、壞行、舊 session、非私有 log、負控均 fail-closed，不回退上一 positive；不恢復 chat。先零模型 contract／受影響回歸，後新隔離 root 真 Safari final+reload、原生圖箭頭、日文/actor/source/記憶/安全/≤20 秒與實際成本。G/T/N/Q/S 不重播追分；G1 actor、G3 舊路徑回覆分因處理，不能合修。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

以下為 G 批前的歷史狀態，其續接點不可覆蓋上段。

更新：2026-10-21。**P4 Web final/reload ledger 圖的單變因接線與審查驅動的證據私有／失效閉鎖已實作；新 G0–G3 真模型／Safari 首輪尚未執行，不能稱圖像或產品 PASS。** `uruha_web_ui.py` 只把實際 brain `episode_doc` 保留在 server-side ledger-positive result 與最終 render；與 `Memory.save_episode` 完整格式、當輪 user/reply/logic/psyche 不符時不當證據。只有 owner-only 0700 目錄中的 0600、非 symlink／hardlink JSONL 才複製完整 witness 以供 reload；預設既有 `web_logs/` 實測 0755、JSONL 0644，**不複製 witness、reload 不亮 verified ledger**，這修正了原凍結計畫對預設 log「已私有」的錯誤前提。Annotation draft UI 遞迴去完整 episode 欄位，client turn/cognition/memory 與新 node details 不新增完整 raw episode；無／錯／附加 episode、缺 logic、空／缺記憶快照都不畫新 ledger，普通路徑保留舊 fallback。合成 Web 契約 **19/19**、含受影響 renderer/atomic/M20/M24/Web 相鄰 **276/276** 通過，Python compile/diff check 通過；G 凍結題未送模型、T 舊 FAIL 不改判。首輪前 product SHA **10/10** 位於 `research/p4_web_final_graph_evidence_delivery_product_freeze_2026-10-21.sha256`。

**唯一當前續接點**：完成獨立只讀複審、核 preimplementation/product SHA／精確 diff/status，只提交 `uruha_web_ui.py`、`test_p4_web_final_graph_evidence_delivery.py`、product SHA 與本卡，push／核既有 PR #435 head。之後新 launcher-owned 0700 隔離 root 做 0-turn same-PID ready/planned stop、官方 SHA ONNX 私有離線預熱、T0_ready 空 profile；真 Safari 依 frozen G0–G3 各一次／0 retry，每輪 final 和 reload 存 screenshot／AX 核真 native ledger 4 nodes/6 arrows 或負控 0，逐輪核可見日文／actor／source、raw/guard/utterance/SQLite、profile、≤20 秒與新增 log bytes／0 Web model calls。任何 gate 失敗 whole-batch strict FAIL，保留狹義 graph 證據；不重送舊題追分。正式同模型、人評、temporal holdout、VRM/Function Calling 統一驗收 pending，Goal active；無關 `output/graduate_application_report/`、原始 dirty checkout及正式 DB 不碰。

以下是實作前凍結和更早歷史；其下一步不能覆蓋上段。

更新：2026-10-21。**上批 T 結果報告與本卡已在 `5203b54` 推 PR #435，嚴格 FAIL 不改判。下一個必要項目是 P4 Web final/reload graph evidence delivery，現在只完成實作前凍結，尚無新程式或新 Safari 結果。** before：T0/T2/T4/T6 終端 ledger 4/4 有界內容正確，但真 Safari 原生 ledger graph 0/4；`_finalize_surface_delivery` 最終重畫遺失實際 `episode_doc`，reload 重建也未帶已記錄的 `logic`／episode witness，renderer 因防偽正常抑制。唯一變因是 Web server-side final/reload 傳遞真實 episode 證據，不改 ledger、renderer、安全、模型或記憶寫入。新 source-disjoint G0–G3 於 `research/p4_web_final_graph_evidence_delivery_plan_2026-10-21.md` 與 `datasets/p4_web_final_graph_evidence_delivery_probe_2026-10-21.json` 事前定案：2 supported mixed、一個直接 User seed/actor 控制、一個 unsupported 負控；四句在其餘 251 個 dataset JSON 逐字碰撞 0，零模型 preflight G0/G2 eligible、G1/G3 不接管，G0 no-source/G2 source-backed；preimplementation SHA 2/2。計畫要求每輪 final＋reload 真 Safari 原生圖／箭頭截圖與 AX、≤20 秒、0 新模型呼叫、bubble/raw/guard/episode/profile、私有 log 增量成本；任何 actor、回覆品質或圖失敗仍 whole-batch strict FAIL。G1 的既知 `私`→`うち` 風險未隱藏，不能以圖子項達標改寫全批結論。

**唯一當前續接點**：先核 `research/p4_web_final_graph_evidence_delivery_preimplementation_2026-10-21.sha256`、diff 與 Git，僅提交／push 新 plan、dataset、SHA 和本卡並核 PR #435 head；再按允許檔案最小接線：`uruha_web_ui.py` 私有 turn/result 保留真 episode witness，最終 render 使用它，本地 JSONL 僅 ledger-positive 保存，reload 帶 logic/witness；client payload／graph details 不新增 raw episode。加入合成 genuine/missing/tampered/final/reload/privacy 零模型測試，跑相鄰回歸、product SHA、commit/push，然後全新隔離 root/真 Safari G0–G3 一次各輪驗收。T/N/Q/S 不重播；T1/T8 actor、T7 舊路徑回覆另案不合修。正式強 LLM／真人／temporal holdout／VRM/Function Calling 統一驗收 pending，Goal active；無關 `output/graduate_application_report/`、原始 dirty checkout與正式 DB 不碰。

以下為已完成 T 批及更早歷史；其下一步不可覆蓋上段。

更新：2026-10-21。**P4 typed two-act semantic ledger 的前瞻 T0–T8 真 Safari 九輪完成，整批 strict FAIL；下方「Safari 尚未跑」已是歷史。** 設計／九題／零模型控制先以 `97873cc` 凍結，opt-in 程式、圖表來源防偽、34/34 聚焦與 261/261 含相鄰測試及 product SHA 18/18 以 `fb6f2c2` 推既有 PR #435 後才跑模型。新 0700 隔離 root `uruha-product-bhtaye8p` 完成 0-turn 同 PID ready/planned stop、官方 SHA ONNX 私有離線預熱、T0_ready 空 DB/profile；真 Safari session `20261021_063140_9f28e9e1` 依凍結 T0–T8 各一次／0 retry。raw 九行 SHA `44402c017ddb7143dd6878f9c10045eaae5d80beed695ed3c9b506daf76a6b89`。T0/T2/T4/T6 支援的雙行動 **4/4** 可見保留引文日期／狀態、外層日期及 User 來源／具日期的未知，新增 mixed rewrite 0 calls／0 completion tokens；自然 M31=true/M32=true 正例有 3 個，達 coverage。但真 Safari 最終原生圖 **0/4** 沒有新 ledger/action 節點與箭頭，只有舊 producer 3 nodes/2 arrows；不能用離線重畫改判。T1 `私`→`うち` actor FAIL，T7 新 ledger 正確 abstain 但舊回覆把引文當事實且漏回想，T8 無實際 OTP 洩漏／無新 terminal authority，卻 actor 錯且 `ことんだね` 不自然。泡泡＝raw＝guard＝utterance＝隔離 SQLite episode 9/9、episode 0→9、完整 profile T0_ready–T8 0 rows 同 digest；M19 9/9 ≤20 秒，平均 12.9052 秒／最大 17.1601 秒，這不是全系統 token ledger。兩 PID planned stop／7894 vacant，只關本次 Safari tab 53→52。完整證據和界線見 `analysis/p4_typed_act_semantic_ledger_fresh_product_probe_result_2026-10-21.md`；S/Q/N 舊 FAIL 不改判。

**唯一當前續接點**：先只讀審查 T 報告與 diff，僅 commit/push 本報告和本卡、核 PR #435 head。再針對圖像交付做新的單變因、source-disjoint 前瞻計畫／題／gold／成本／SHA 凍結：Web 最終與 reload 的 `episode_doc` 證據傳遞目前缺失，renderer 因防偽 fail-closed 抑制新圖；修正後須核真 Safari 新節點／原生箭頭與缺／偽證據負控。T1/T8 actor、T7 舊回覆品質另列缺陷，不合修；不重播 T/N/Q/S 追分，不放鬆來源／安全圖 guard。正式同模型強 LLM、人評、temporal holdout、VRM/Function Calling 統一驗收仍 pending，長期 Goal active；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

以下為本批首輪前及更早歷史狀態，不能覆蓋上段唯一續接點。

更新：2026-10-21。**新 P4 雙行動語義 ledger 架構：事前設計／9 輪 T0–T8＋4 個零模型反例已在 `97873cc` 凍結推 PR #435；opt-in 程式與圖表防偽完成零模型驗證，真模型／Safari 尚未跑，不能稱產品 PASS。** S/Q 舊批 strict FAIL／`REVIEW_REQUIRED` 不改判。針對 S3「引文年份消失、`調整中` 變義、內外兩日混淆」，唯一新變因是把符合限定文法的雙行動由自由生成改為來源綁定的兩筆 action ledger＋受約束實現：引文原樣保留日期／狀態，只改 `です→なんだ`；回想用獨立的外層日期與直接 User 來源／具日期的誠實未知。完整來源、動作、候選與最終 guard 重核；不支援的語法 fail-closed，不冒充一般語義等價。原 M31/M32、保護 gate、正式 DB 不改。獨立審查抓到圖表可被「自填一致的捏造地點」騙過；已加實際本輪 memory snapshot 的來源證書重算、兩筆 act 核對與偽造反例，缺 snapshot 不顯示新 verified 節點。聚焦 **34/34**、受影響相鄰 **259/259** 零模型測試通過；這不包含模型／Web。設計／gold／限制見 `research/p4_typed_act_semantic_ledger_design_review_2026-10-21.md`、`research/p4_typed_act_semantic_ledger_plan_2026-10-21.md`，實作前 SHA **3/3**，產品原件 SHA **18/18** 於 `research/p4_typed_act_semantic_ledger_product_freeze_2026-10-21.sha256`。

加入兩個「缺本輪記憶快照須抑制 ledger 圖」反例後，最終聚焦＋相鄰重跑 **261/261** 通過；上段 259/259 是此前的中途數值，不是最終總數。

**唯一當前續接點**：先核 product SHA／diff 與精確 Git status，僅提交／push 本項允許檔案和本卡，確認 PR #435 head；再全新 launcher-owned 0700 root 做 0-turn same-PID ready/planned stop、官方 SHA ONNX 私有離線預熱、顯式空 profile/T0，真 Safari T0–T8 逐字各一次／0 retry。逐輪核兩 act 的 date/state/actor/source 與實際圖箭頭、泡泡＝raw＝guard＝utterance＝history＝SQLite、profile、≤20 秒及 0 額外 mixed rewrite calls；至少兩個自然 M31=true/M32=true mixed 正例，否則 coverage 不足。任何硬 gate 失敗整批 strict FAIL，不能重播 N/Q/S 或削弱保護。正式同模型強 LLM、人評、temporal holdout、VRM/Function Calling 統一驗收仍 pending；Goal active。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-21。**P4 mixed atomic 第二且最後前瞻修正批 S0–S9 已在真 Safari 完成：整批 strict FAIL，這個項目進入 `REVIEW_REQUIRED`；不是整個長期 Goal blocked/complete。** 計畫／新題先以 `5e577fe` 凍結，單一 prompt-scope 程式與 301/301 零模型／相鄰測試、product SHA 14/14 以 `1402f8e` 推 PR #435 後才在新 0700 隔離 root `uruha-product-1frib3b1` 啟動；0-turn 同 PID ready/stop、官方 SHA ONNX 私有離線預熱、T0_ready 空 profile 均核。真 Safari session `20261021_021854_8140f69c` 依凍結順序 S0–S9 各一次／0 retry；raw 十行 SHA `76d10ac33fcc833bf67d101e322853296a1197c53cd127c0708283b8363eede6`。M31=true/M32=true mixed 自然出現 S3/S7 共 **2**，target variant 有覆蓋，但雙行動語義正確交付 **0/5**；S3 僅形狀上交付 1/5，改寫丟 `2027`、把「調整中」改成「還沒決定」、使回想日期指代不明。S0/S7 的改寫候選從舊 Q 的 `new_number` 類別變成 `formal_register` 並正確拒絕，不能以不同 prompt 宣稱因果改善。S1/S8 仍有 User `私`→角色 `うち` 主語問題，S2/S5 M32=false、S8 沒洩露實際 OTP 但安全表面語義不合格，S9 單改寫也不自然。Safari 每輪見 producer 3 nodes/2 edges；S3 的 atomic 3 nodes/5 edges 僅由凍結 renderer 對 raw＋隔離 SQLite episode 唯讀重建，未保存 S3 專屬 Safari UI 截圖，不外推圖像 gate 完整通過。guard／utterance／SQLite User＋reply 10/10 對齊；turn episode 0→10、profile T0_ready–S9 0 rows 同 digest；M19 **10/10** ≤20 秒、均值 12.32345 秒／最大 19.4955 秒；新 atomic 3 calls、371 prompt＋62 completion tokens／5.639415 秒，不是全系統 token ledger。PID 73648 精確 planned stop／port 7894 vacant，僅關本次 Safari tab 53→52。逐輪、原件與設計選項見 `analysis/p4_typed_mixed_atomic_rewrite_style_scope_fresh_product_probe_result_2026-10-21.md`；舊 N/Q strict FAIL 不改判。

**唯一當前續接點**：先獨立只讀審查 S 報告／diff，僅 commit/push 報告和本卡並核既有 PR #435 head；然後對 typed mixed-act 項目按既有兩批 stop rule 做設計審查，選一個必要的新架構／實驗方案，而不是第三次增量 prompt/validator 修補。最低反例 S3 已有明確的 quote 時間／語義漂移，另需分開 actor、M32、protected wording、graph UI 證據缺口；若進入新項，先凍結全新 source-disjoint 題、gold、成本和驗收層，不重播 N/Q/S、放鬆保護或削弱 baseline。正式同模型強 LLM、人評、temporal holdout、VRM/Function Calling 統一驗收仍 pending，長期 Goal active；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-21。**P4 mixed atomic 最後一個前瞻修正批 S0–S9：題目事前凍結、單變因 prompt scope 程式與零模型已完成；真模型／Safari 尚未跑，不得稱產品 PASS。** Q0–Q9 strict FAIL／raw SHA 與舊 N 等結果保留。只讀審查發現 Q0/Q3/Q7 三次獲准改寫皆 `new_number`；完整外層回想日期當作 `requested_style` 傳給改寫模型是有根據但未證明的污染假說（模型原文未存）。最後一批只讓 mixed atomic 改寫 call 從已證風格 cue 萃取有界 style，不帶第二任務日期；quote 原文、數字防護、M31/M32、來源、模型參數、單改寫與 graph 均不動。S plan／10 題／preimplementation SHA 2/2 已先 commit/push `5e577fe` 到 PR #435；12/12 role/action、5/5 合成 source 預檢、對其他 249 dataset JSON 的逐字碰撞 0。程式及 focused/neighboring **301/301** 通過，獨立只讀審查的矛盾語氣反例已 fail-closed、S/Z 語法邊界已核；product SHA **14/14**。這些只證明接線及 prompt 邊界，fresh generation／Web 結果 pending。

**唯一當前續接點**：先 diff review，僅提交本批兩個程式／測試檔、product SHA 與本卡，push／核既有 PR #435 head。其後新 0700 隔離 root 做 0-turn same-PID ready/planned stop、官方 SHA ONNX 私有離線預熱、T0 空 profile；真 Safari 按凍結 S0–S9 各送一次／0 retry。逐輪核 style 模型收據、quote 內／外日期、User/第三者/撤回來源、兩個子任務、自然日文／主語、graph atomic 實際箭頭、泡泡＝raw＝guard＝utterance＝history＝episode、profile、M19 ≤20 秒與額外 call/token cap；至少兩個 linked M31=true/M32=true mixed 才算 target variant 覆蓋。任一 hard gate 失敗整批 strict FAIL；本批後不得第三次增量追分，保留最小反例與選項為 `REVIEW_REQUIRED`，再依證據選真正必要的新產品項，不把整個 Goal 標 blocked/complete。正式同模型強 LLM、人評、temporal holdout、VRM/Function Calling 統一驗收 pending；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-21。**P4 M31 實際權限變體的 Q0–Q9 真 Safari 前瞻批完成：整批 strict FAIL，target variant coverage inconclusive。** 實作前凍結 `4f1fd59`、單變因程式／零模型 282/282／product SHA 14/14 `a780352` 已先推 PR #435；原 N0–N9 strict FAIL 不改。新 0700 隔離 root `uruha-product-9h6t7fn3` 做 0-turn same-PID ready/planned stop、官方 SHA ONNX 私有離線預熱及 T0 空 profile。真 Safari session `20261021_013318_5156c74b` 依凍結 Q0–Q9 各送一次／0 retry；raw 十行 SHA `573c1c229d0aeef649f72ce2709073c75a637ba8436c1328a36928657bfbbbdd`。Q0 合法 linked M31=true/M32=true 這次確實進入 atomic 候選路徑並如實記 prior M31=true，證明過窄准入缺陷已修；但新增候選 `new_number` 被正確拒絕。混合請求雙行動可見交付 **0/5**；M31=true/M32=true 無 blocker mixed 只自然出現 **1** 例，少於凍結要求 2。Q3/Q7 亦 `new_number`；Q2/Q5 M32=false 沒有准入。Q2 可見回覆重現 User 先前說過的地點（不能單憑此斷定記憶因果通道）、Q5 不挪用朋友地點、Q6 當輪承認撤回但尚非持久更正證據；Q1/Q0/Q3 有 User `私`→角色 `うち` 問題，Q8 protected 路由無密碼洩露但表面不自然，Q9 改寫丟失「候選尚未收斂」細節。圖 10/10 僅 producer 3 nodes/2 edges、atomic 0；泡泡＝raw＝final guard＝utterance＝history＝SQLite turn episode 10/10，但一致不等於正確。turn episodes 0→10、profile T0–Q9 0 rows 同 digest。最終 M19 ≤20 秒 **7/10**（平均 15.5922、最大 20.7730）；新 atomic 3 calls／425 prompt＋115 completion tokens／6.942871 秒，未有完整系統 token ledger。PID 65100 精確 planned stop／7894 vacant，僅關此次 Safari tab 53→52。詳見 `analysis/p4_typed_mixed_atomic_m31_authority_variant_fresh_product_probe_result_2026-10-21.md`。

**唯一當前續接點**：完成 Q 報告的只讀審核、diff review、僅提交／push 本報告與本卡並核 PR #435。之後先對 `new_number` 候選與改寫 prompt scope 做只讀因果／設計審查，再決定是否用剩餘**一批**有根據、source-disjoint、事前凍結修正；不得同批合修 M32=false、actor、Q8 語氣或 latency，也不得放寬數字安全拒絕或重播 Q/N 追分。若第二批仍 FAIL，按既有 stop rule 產 `REVIEW_REQUIRED`，不能無限加規則。正式同模型強 LLM、人評、temporal holdout、VRM/Function Calling 統一驗收和長期 Goal 均 pending；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-21。**P4 typed mixed-act atomic delivery 的第一個前瞻修正批 Q0–Q9 已事前凍結、單變因程式完成零模型驗證；真 Safari 首輪 pending。** N0–N9 strict FAIL 與原 raw 不改判、不重送。只讀審查證實 N0/N3/N7 的 M31=true 是合法 linked producer 變體，新 admission／收據／graph 卻錯寫死 false；N2 的新增數字拒絕是另一缺陷，不合修。新的 source-disjoint Q plan／10 題／preimplementation SHA 2/2 以 `4f1fd59` 先推 PR #435，舊 dataset JSON 精確碰撞 0/248；零模型 role/action/source 前檢符合凍結預期。單一修正只允許實際 bool M31=true/false 在 producer／lineage 一致時准入，於最後 guard 再核並在 graph/terminal 收據如實呈現；M32=true、父鏈、來源、安全、改寫 validator、模型參數與成本 gate 不變。聚焦與相鄰零模型 **282/282**，新 product SHA **14/14**，沒有本批模型／Web 證據；不能稱產品 PASS。

**唯一當前續接點**：diff review 後只提交本批允許的四個程式／測試檔、product SHA 與本任務卡，push／核 PR #435 head；再用全新 0700 隔離 root 做 0-turn 同 PID ready/planned stop、官方 SHA ONNX 私有離線預熱和 T0 空 profile，依凍結 Q0–Q9 在真 Safari 各送一次／0 retry。逐輪核 M31 實際 authority/receipt/graph、兩個子任務和來源、自然日文與主語、泡泡＝raw＝guard＝utterance＝episode/history、profile 不污染、≤20 秒與新增 call/token；至少兩個 linked M31=true/M32=true 才算 target variant 有覆蓋。任何 hard gate 失敗整批 strict FAIL；不能把准入或 graph 的單元 PASS 外推。第二批修正只能在新的只讀因果審查與事前凍結後做；兩批仍敗就 `REVIEW_REQUIRED`。正式同模型／真人／temporal holdout、VRM/Function Calling 統一驗收及長期 Goal pending；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-21。**P4 typed mixed-act atomic delivery 的真 Safari N0–N9 十輪已完成，整批 strict FAIL；下方首輪前待辦已是歷史。** 事前凍結 `868f828`，opt-in 程式與 product SHA 14/14、零模型／相鄰 269/269 以 `e8fd18f` 推既有 PR #435 後，才於新 0700 隔離 root `uruha-product-tqmixwn3` 完成 0-turn same-PID ready/planned stop、官方 SHA ONNX 私有無網路預熱與 T0 空 profile。真 Safari session `20261021_005305_6f1d1059` 依凍結 N0–N9 各送一次／0 retry；raw 十行 SHA `a92521592c7ad4e9d0323695cbee96cb2a62e0c30d731bf42339ad9a1b35df91`。mixed 雙行動 **0/5** 交付：N0/N3/N7 的合法 M31=true 被新 admission 過窄假設旁路；N2 已找回直接 User episode，卻因改寫候選新增數字被正確拒絕；N5 誠實未知但缺改寫。N1 重現 `私`→`うち` 主語翻轉，N8 保護路由不洩實際碼但日文 `教えろんだね` 不自然，N9 單改寫控制未完成柔和改寫。圖舊 producer 3 nodes/2 edges 10/10，新 atomic 0/0（沒有成功收據，不假畫）；泡泡＝raw＝guard＝utterance＝SQLite episode 10/10、episode 0→10、profile 0 rows 同 digest，最終 M19 等待 10/10 ≤20 秒（平均 13.3479、最大 19.9480），新交易只加 1 call／142 prompt＋40 completion tokens／4.474715 秒。完整逐輪與邊界見 `analysis/p4_typed_mixed_atomic_delivery_fresh_product_probe_result_2026-10-21.md`。產品 PID 精確 planned stop／7894 vacant，僅關本次 Safari tab 53→52；G/L/W/A 舊 FAIL 不改判。

**唯一當前續接點**：先只讀因果／設計審查 M31=true 合法變體與「實際 prior authority」收據，另分析改寫候選受外層日期污染；`私` 主語翻轉和 N8 表面品質列獨立缺陷，不合修。若有單一可歸因修正，先凍結**全新** source-disjoint 題、條件 gold、≤20 秒／日文／來源／graph／成本硬 gate 再實作一個前瞻批；本 N0–N9 不重播追分，至多兩個有根據修正批，仍失敗就 `REVIEW_REQUIRED`。正式同模型／人評／temporal holdout、VRM/Function Calling 統一驗收和長期 Goal 仍 pending；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-21。**P4 雙行動原子交付已完成 opt-in 程式與零模型契約，真 Safari N0–N9 首輪尚未執行。** 事前凍結的 `research/p4_typed_mixed_atomic_delivery_plan_2026-10-20.md`／`datasets/p4_typed_mixed_atomic_delivery_probe_2026-10-20.json` 及 preimplementation SHA 2/2 未變；新 transaction 只在正確來源、雙 typed action、M31/M32 直接父鏈與非保護路由時嘗試有界改寫＋過去地點回覆，保留舊 producer 權限戳；末端 guard／graph／episode／history 有結構收據與回滾，明標 `semantics_unverified`。原生 graph 增補 action／terminal 節點與箭頭，不改舊三節點兩箭頭。獨立只讀審查指出的來源消失、畸形競爭 contract、rewrite call 成本收據與圖 lane 重疊已修；聚焦加相鄰零模型測試 **269/269**、`git diff --check`、首輪前 product SHA **14/14** 通過。這些不是 fresh model／產品 PASS，改寫語義與 `私`→`うち` actor 缺陷仍須實際核對。

**當前唯一續接點**：精確 commit/push 本項允許檔案並核 PR #435 head，然後用新 0700 root 做 0-turn 同 PID ready/planned stop、官方 SHA ONNX 私有離線預熱與 T0 空 profile，再依凍結 N0–N9 在真 Safari 各送一次／0 retry。逐輪核兩行動內容與來源、可見自然日文／人格／主語、native graph 連線、bubble＝raw＝guard＝utterance＝episode＝history、profile／episode 快照、≤20 秒與額外模型成本。任一 hard gate 不過整批 strict FAIL，舊 G/L/W/A 不重播、不把 shape-valid 當語義已驗；正式同模型／人評／temporal holdout 與全產品完成仍 pending。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-20。**G1–G3 圖像 gate 過後已完成下一項只讀因果審查**，見 `research/p4_typed_mixed_act_authority_design_review_2026-10-20.md`。G2 兩 typed actions 與直接 User 原話記憶均存在，失敗不是完全缺記憶，而是 M32 表面權限接管後僅重述任務；現有 single-rewrite 與 past-place source gate 沒有在 mixed 請求交付兩子任務。下一個單一變因候選是來源綁定的「雙行動原子交付／顯式權限交易」，先用未曝光 source-disjoint 正負控與 ≤20 秒、模型成本、末端回滾、Safari gate 做**實作前凍結**；此審查本身尚未凍結資料或授權任何舊原件改判。`私`→`うち` 的 User 主語翻轉另案，不得合修；G/L/W/A 舊批仍 strict FAIL，正式同模型／人評／holdout pending。

更新：2026-10-20。**P4 原生 producer lineage 圖像投影首輪真 Safari G1–G3 完成：graph gate 3/3 PASS，整體 mixed-act 產品 strict FAIL。** 前瞻計畫／G 題 `1bc2647` 凍結、renderer／合成負控 `9600b75` 已推 PR #435；147/147 零模型／相鄰測試、產品前後 freeze SHA 15/15。新 0700 隔離 root `uruha-product-0w77cy3p` 經 0-turn same-PID planned stop、官方 SHA ONNX 私有離線預熱、T0 空 profile；真 Safari session `20261020_204838_90c7cd82` 三題各一次、0 retry，raw 三行 SHA `7d6221e2267d0291d76be2b35a67b0559c096a72443e94576e31b4801895e5fc`。三輪畫面都目視有 EVENT／M31／M32 三可點高對比節點、兩條原生箭頭；raw→renderer 亦各 3 nodes／2 graph edges／2 SVG paths，protected G3 明顯標 blocker／不移交，M24 budget 3/3。G1/G2 的 `私`→`うち` 可見層主語翻轉，G2 委婉改寫與過去地點回憶未交付，G3 不洩露實際密碼但答非所問；**圖像 PASS 不能抵銷回覆 FAIL**。泡泡＝raw＝guard＝blackboard utterance＝隔離 episode 3/3；episode 0→3、profile 0 rows 同 digest，3/3 ≤20 秒（平均 13.4944 秒），新 projection 0 model calls，完整 token ledger 不可得。產品 PID exact-identity planned stop、7894 vacant，僅關本次 Safari tab 53→52；詳細逐輪與邊界見 `analysis/p4_verified_producer_graph_fresh_product_probe_result_2026-10-20.md`。**唯一當前續接點：先只讀審查 typed action coverage／原子改寫＋已證 User 來源回憶的權限設計，將主語替換列獨立缺陷；再凍結新未曝光 source-disjoint probe、單一變因／成本／安全／Safari gate 才實作。** G/L/W/A 舊題不重送，正式同模型、人評、temporal holdout、VRM/Function Calling 統一驗收 pending，Goal active；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-20。**P4 原生 producer lineage 圖像投影已完成零模型實作，真 Safari G1–G3 首輪 pending。** 單一變因只改 `uruha_memory_observatory.py` 的純 renderer，從完整且再次核對的 linked receipt 投影 event/M31/M32 三個高對比可點節點與兩條 `is-producer` SVG 真實邊；錯父／錯 digest／錯 cycle／重複／缺 producer 均不畫。獨立審查發現狀態／ID 可以夾帶原話，已在同一 renderer 以 v1 UUID／狀態枚舉及原話碰撞檢查修閉；新增合成負控。明標 action coverage 未驗、權限未移交，不動回覆或核心黑板。計畫、G1–G3 新開發者題在程式前以 `1bc2647` 凍結，preimplementation SHA 2/2；聚焦與受影響相鄰 **147/147**、語法及 diff check 通過。舊隔離 L1–L4 原件**僅唯讀重畫** 4/4 有 3 節點／2 SVG 箭頭，M24 detail 預算仍通過，不改舊 strict FAIL，也不當新 Safari 證據。首輪前 `research/p4_verified_producer_graph_product_freeze_2026-10-20.sha256` **15/15**。**下一步**精確 commit/push/PR #435 head，再新 0700 root 做 0-turn 啟停、官方 SHA ONNX 私有離線預熱、T0 空 profile，Safari G1–G3 各一次／0 retry，逐輪核原生圖箭頭、保護權限、泡泡/raw/guard/episode、profile、≤20s 和成本。圖通過也不等於 mixed reply 通過；正式同模型、人評、temporal holdout、VRM/Function Calling 仍 pending，Goal active。

更新：2026-10-20。**P4 mixed-act producer lineage 真 Safari 四輪完成，整批 strict FAIL。** 計畫與四題在 `3ac7717` 先凍結，程式／測試／product SHA 以 `ef68831` 推既有 PR #435；首輪前 13/13 SHA、聚焦 14/14、相鄰 229/229 只是零模型與接線證據。新 0700 隔離 root 經 0-turn same-PID 啟停、官方 SHA ONNX 私有離線預熱、T0 空 profile；真 Safari L1–L4 各一次／0 retry，raw 四行 SHA `b76a85ee66361137292384bf44abcd901c0fa4833c596b2ba8000e6f19ac585f`。四輪原生 event→M31→M32 receipt **4/4 linked**，L2 typed mixed action 2，protected L3 不移交權限，新模組模型呼叫 0；但 Safari 圖 **0/4** 畫出原生父子邊，早期 event 節點 0/4 保留；L1 主語錯、L2 改寫＋回憶都未完成、L3 >20 秒（21.7039），整批不能 PASS。泡泡＝raw＝guard＝trace utterance＝episode 4/4，隔離 turn episode 0→4（另 1 自動摘要）、profile T0–L4 0 rows／同 digest；PID planned stop、7894 vacant，僅關這次 Safari 分頁 53→52。完整證據與限制見 `analysis/p4_mixed_act_lineage_fresh_product_probe_result_2026-10-20.md`。舊 W1–W7/A1–A7 原件及失敗不改判、不重送。

**唯一當前續接點：先做 graph 原生 lineage 可見交付。** 只讀審查已定位：核心黑板上限擠掉早期 event/M31/M32；observatory 只按節點序列畫一般線，沒有消費完整 `runtime_trace.mixed_act_lineage_p4.producer_edges`。先用 0-call 設計把已核收據投影成有標記的 event/M31/M32 三節點、兩條專用箭頭；錯 event/parent/digest/重複/未產生即不畫，清楚標 `coverage unverified` 與 `authority_transfer=false`，不修改核心權限或產品回覆。先凍結新未曝光圖探針與條件 gold、允許檔案、受影響測試、成本及 Safari gate，再實作驗收；不得重播 L1–L4 修分。只有圖可核後，才另立 typed action coverage／原子改寫與來源回憶的權限工作；現在不能宣稱 mixed product 改善、強 LLM 優勢或正式研究完成。正式同模型、人評、temporal holdout、VRM/Function Calling 統一驗收 pending；Goal active。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

歷史更新：以下是已完成的舊批次與舊續接點，均不覆蓋上面的唯一當前工作。

更新：2026-10-20。**P4 混合請求過去地點來源 gate 的真 Safari 七輪已完成，整批 strict FAIL；交付與成本證據見 `analysis/p4_mixed_past_place_source_authority_fresh_product_probe_result_2026-10-20.md`。** 事前 `0e0fd0c` 凍結題／plan，`d61167f` 凍結 opt-in code 並推既有 PR #435；零模型／相鄰 148/148、product SHA 10/10 不能代替產品。新 0700 隔離 root `uruha-product-95lby3fk` 完成 0-turn 同 PID ready/stop、官方 SHA ONNX 私有離線預熱與 T0 空 profile；真 Safari session `20261020_162122_3b388563` W1–W7 各一次、0 retry，raw 七行 SHA `1c50246f25b048b582f2fc644df84a763b3923c612f5b045909a603af6fef9df`。混合 role 4/4，但新 gate graph／trace **0/4**：四輪 M31 `surface_authority=true`，舊權限在同輪 parent/event 未證時保留，不能偷覆寫。W2 有直接原話卻未答地點，W3/W5/W7 未交付自然未知／改寫；W1/W6 主語錯歸角色。Safari 泡泡＝raw＝guard＝graph utterance＝episode 7/7、profile T0–W7 0 rows 同 digest、七輪 ≤20 秒，均不抵銷品質失敗。產品 PID 94723 planned stop、7894 vacant，只關本次新 Safari 分頁。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰；前批 strict FAIL 不改判、不重送。

**已完成的上一續接點：0-call M31/M32 × mixed-act 當輪權限設計審查。** 結論與尚未凍結的新設計在最上方及 `research/p4_mixed_act_authority_design_review_2026-10-20.md`；不能只靠同 text digest 或模型自評移交。W1/W6 主語、改寫品質、W7 殘句分開處理；正式同模型、人評、temporal holdout、VRM/Function Calling 統一驗收仍 pending，Goal active。

更新：2026-10-20。**混合請求過去地點來源授權的設計審查與 opt-in 程式已完成，真 Safari 首輪仍 pending。** 前批 A1–A7 與更早 strict FAIL／`REVIEW_REQUIRED` 不改判、不重送。只讀 before 證實 A1 在 0 記憶來源時，M21 core 已編出昨天地點、M39／guard 放行且 assistant episode 保存；來源角色本身只有分類，不是事實權限。單一變因、未曝光 11 契約題＋7 產品輪次、允許檔案、條件 gold／≤20 秒與成本 gate 在程式前以 `0e0fd0c` 凍結，見 `research/p4_mixed_past_place_source_authority_plan_2026-10-20.md`；preimplementation SHA 2/2、舊 datasets exact-string collision 0/18。新的 opt-in gate 僅對日文單引述改寫＋本人過去選的集合地點：直接且已交付的 User 原話＋同一絕對日期才可說具體值；相對日、無來源、矛盾／撤回、第三人／assistant／summary、current presupposition皆退未知。M31/M32 既有 authoritative 不移交，改寫子任務不冒稱完成。最終 guard 在 episode 寫前重查；本輪 `RightBrain.history` 與四種表面計數以 emit 交易回滾 pre-guard 草稿，只提交最後日文句。聚焦 9/9、受影響相鄰 148/148、入口與 controller `--help`、product SHA 10/10；**這些只是零模型／接線證據，不是產品 PASS**。當前下一步是 diff review、精確 commit/push 核 PR #435，然後新隔離 0700 root 做 0-turn 啟停、官方私有 ONNX 預熱、真 Safari W1–W7 各一次／0 retry，逐輪核 raw＝泡泡＝guard＝graph utterance＝episode／history、User source trace、自然日文、成本與 ≤20 秒。若失敗保留 strict FAIL，不補送；正式同模型／人評／temporal holdout／VRM/Function Calling 仍 pending。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-20。**當輪來源角色憑證已實作並以 `70080e9` 推 PR #435；七輪新隔離 Safari 實測完成，整批 strict FAIL，完整證據見 `analysis/p4_current_turn_source_role_fresh_product_probe_result_2026-10-20.md`。下方所有舊批 strict FAIL 與 `REVIEW_REQUIRED` 不改判、不重跑曝光題。**

## 唯一當前續接點：混合請求的過去事實來源授權，先設計審查

憑證零模型聚焦 **78/78**、受影響回歸 **210/210**；Safari A1–A7 source-role 7/7、五負控新改寫呼叫 0/5、泡泡＝raw＝guard＝blackboard utterance 7/7，但正例自然改寫 **0/2**。A1 無任何檢索記憶仍說「昨日は公園で待ち合わせしたよね」，A6 日文句型錯，A7 依本批較嚴非冒充 gold 有與真人同名直接自稱的界線問題（早期身份保持測試曾將同型句判 PASS，非本次新退步），A1 user-wait 23.5449 秒 >20；原始 trace 的 USER→role→action/utterance edge／event-parent lineage **0/7 可核**，只有節點與順序。T0–A7 profile 0 rows／同 digest，episode 0→7；產品與 0-turn PID 均 planned stop、7894 vacant，只關本次 Safari 新分頁。這是「來源角色分類局部成立、產品失敗」，不是整體成功、正式強 LLM 優勢或研究完成。

**下一個必要交付：先只讀設計審查 A1 的混合請求回憶事實來源權限**。分別確認原始 User 直接來源、相同/不同輪、未知／矛盾、第三人引語、assistant-output 污染及 graph lineage 能否被驗證；若有單一可歸因修正，才以前瞻未曝光 source-disjoint 案例凍結 before、允許檔案、成功／失敗、零模型／真 Safari、≤20 秒與成本 gate，再實作。A2/A3 候選品質、A6 M32 句型、A7 身份非冒充標準與早期 PASS 的調和及 runtime graph 真實 edge 另列獨立問題，不能合成一個補丁；不在此批 A1–A7 修分、改 gold 或將相同模型/舊題重播當新證據。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 不碰；正式同模型、人評、temporal holdout、VRM／Function Calling 統一驗收 pending，Goal 仍 active。

歷史更新：2026-10-20。**以下是前一個來源角色工作項開始前的指令，已由上節取代。**

上次中斷的 Safari 結果已以 `579d12a` 提交並推 PR #435；其後 0-call 設計審查見 `research/p4_current_turn_action_role_design_review_2026-10-20.md`。下方八輪 strict FAIL 不改判、不重跑。

歷史下一項曾是為「當輪 communicative-act／source-role 憑證及 M31 同輪權限仲裁」凍結新任務卡與 source-disjoint 案例，做零模型跨行動類型契約驗證。該憑證已實作並經本輪七題產品探針，不應再作為待開始工作；M31/M32 event/parent lineage 尚不足，權限覆蓋沒有實作。舊明示改寫工作項以 0/3 gold 的負結果及 `REVIEW_REQUIRED` 結束。候選 JSON、引號內敬體、N1 詞義、P4-W guard 後修改、身份退步分屬不同問題。

歷史更新：2026-10-20。**以下記錄是已完成批次；「下一步」已由本檔最上方的設計審查決定取代，不重做八輪。**

## 最新結果：P4 改寫表達權限交接有局部機制進展，fresh Safari strict FAIL／REVIEW_REQUIRED

上一批 8 輪 strict FAIL 與原 raw SHA 不改判、不重送。新 8 題／計畫在程式前以 `d3a3057` 凍結，單變因 typed candidate→speech 權限交接及 product SHA 以 `f36d1f0` 推 PR #435；118/118 受影響零模型、preimplementation SHA 2/2、product SHA 10/10。新 0700 隔離 root `uruha-product-qyrlxpja` 先 0-turn 同 PID ready/stop、官方 SHA ONNX 私有離線預熱，後真 Safari session `20261020_140152_33b8ed89` 八題各一次、0 retry；raw 8 行 SHA `3c39b219dc897314db70e1ea553867be0d9d984ca19f884c3a63322a448e63b0`。詳細逐輪、圖、成本、證據邊界見 `analysis/p4_rewrite_surface_authority_fresh_product_probe_result_2026-10-20.md`。

P2 首次有 typed 候選完整走 `speak→guard→P4-W no-op→graph→Safari`，但候選含 `ません` 敬體，品質 FAIL；P1 JSON 解析失敗退原路徑，P3 被誤把改寫指令當回答的 M31 舊權限擋住。**正例 0/3 gold，整批 strict FAIL**；負控 0/5 誤接管、N5 當輪身份通過但不抹除前批 T8 失敗。泡泡＝raw＝graph UTTERANCE 8/8、guard＝泡泡 6/8、episode 0→8；T0 profile DB absent／0 rows，P1–N5 profile 0 rows 且同 digest；8/8 runtime wait ≤20 秒（平均 12.59075 秒）。新增 3 calls／359 prompt＋58 completion tokens／5.129665 秒 call latency；非全系統成本或公平比較。兩 PID planned stop、7894 vacant；只關本次新 Safari tab，原 52 tabs 保留。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未碰；Goal active。

**下一個必要交付是 0-call 設計審查，不再沿本批曝光題修分**：分開候選 JSON/敬體品質、M31 與 typed action 的當輪來源／表達權限、P4-V/P4-W provenance，以及 N1 詞義和前批身份失真；提出一個有歸因的新設計與 source-disjoint 正負控、成本/圖/安全門檻後才可另立前瞻批。若無法提出不靠固定答案的可證明權限仲裁，保留 `REVIEW_REQUIRED`，改處其他獨立必要產品門檻；不得把 P2 機制成功寫成產品 PASS，也不能用本八句重跑。正式同模型、人評、temporal holdout、VRM／Function Calling 統一驗收 pending。

歷史更新：2026-10-20。**以下真 Safari 八輪已完成；舊「fresh pending」與「下一步」均非當前指令。**

## 最新結果：P4 明示引述改寫真 Safari 八輪 strict FAIL

前瞻 plan／八句在實作前以 `f10c972` 凍結，opt-in action／測試／薄入口與 product SHA 以 `220fa89` 推既有 PR #435。受影響零模型 135/135、preimplementation SHA 2/2、product SHA 6/6 只代表接線和契約。新 0700 隔離 root `uruha-product-qcphly1z`：0-turn same-PID 啟停、官方 SHA ONNX 私有預熱、T0 空 profile；真 Safari 同一 session `20261020_085958_00abfc97` 八句各一次、0 retry，逐輪 T0–T8 雙快照，八個不同 episode、profile 0 rows／同 digest。raw 八行 SHA `1c45c0bfeead0799849eb77017149e37488f8103f54e1ed7f72d8872d87642ad`；詳細逐輪／圖／成本見 `analysis/p4_explicit_rewrite_action_fresh_product_probe_result_2026-10-20.md`。產品 PID 35013 planned stop，7894 vacant。

新 action 三個正例 3/3 識別、三次本機模型呼叫，但 **0/3 可證明完成候選→最後改寫行動**：T1/T2 候選因敬體拒絕；T3 形狀檢查漏過 `ません` 敬體候選，speech／P4-W 又把它變成「引述內容」說明而非委婉改寫，最後 guard≠泡泡。故 T3 候選品質與下游表達是兩個未通過的門檻，不能只怪下游。T4–T8 新路徑 0/5 誤觸；T8 **身份本身失敗**，選定 `うるはだよ` 但最後是 `は？そういうのうちに求めないで。`，屬獨立 selected→surface 缺陷。Safari 泡泡＝raw＝graph `UTTERANCE` 8/8，guard＝最後 7/8；全輪日文、runtime wait proxy 8/8 ≤20s，平均 14.3962 秒；新 action 3 calls、359 prompt + 36 completion tokens，合計 call latency 4.539817 秒。這些不能外推為功能成功、正式同模型優勢或身份穩定。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰，Goal active。

**下一個必要交付**：先只讀分因審查 T1–T3 的候選敬體／檢查漏網、T3 typed action 被 speech／P4-W 當成引述轉述、T8 既有身份 core→final 失真；選對產品阻擋最重且單一可歸因變因，依新未曝光正負控與完整產品 gate 做至多一個有根據的修正批次。若仍不過，提出 `REVIEW_REQUIRED`，不重送本八句、不改 gold、不以負控／延遲通過掩蓋正例與身份失敗。正式同模型、temporal holdout、人評、VRM／Function Calling 統一驗收仍 pending。

更新：2026-10-20。**本節取代下方 repair-cue 批次的「下一步」，舊 strict FAIL 不改判。**

## 當前交付：P4 明示引述改寫 typed action 已接線，fresh 產品驗收仍 pending

上一批 raw 六句 SHA `1295179f08c0dd39b27ce4eb1964ff8034f558570205b3d2a60693528c57e2a8`、Safari strict FAIL 保留，不能重送追分。只讀因果審查：T2 的 M21 core `承知しました` 在 P2 `_sanitize_reply` 被變成 `うん`，且 core 本身也比要求的柔和改寫更拘謹；T4 是另一個 `repair_check` 固定反問與前句來源問題，精確重播並非合格修正，不合批。

新單一變因與八句 developer-authored 正負控在模型／程式前凍結於 `research/p4_explicit_rewrite_action_plan_2026-10-20.md`、`datasets/p4_explicit_rewrite_action_fresh_probe_2026-10-20.json`，preimplementation SHA **2/2**。合格的當輪明示引述改寫才用 opt-in typed action 與同模型最多一次額外生成；原 M21 receipt 留 shadow，模型內層短語與組合後完整候選分別記 digest，實際 token／延遲另記。T1–T3 必須 3/3 語義與語氣達標，T4–T6 0/3 誤接管，T7 安全、T8 身份、日文、圖／可見一致、記憶隔離、逐輪 ≤20 秒與成本都屬硬 gate。新 `uruha_explicit_rewrite_action_p4.py`、聚焦測試、薄 Web 入口／controller 已加入；零模型聚焦 **30/30**、加入相關相鄰後 **135/135**、語法與 `--help` 通過，首輪前 product SHA **6/6**。這些**只是程式／接線證據**，尚無本批 fresh model、Safari 或產品 PASS；正式同模型、人評、temporal holdout、VRM／Function Calling 仍 pending。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

**下一個必要交付**：diff 審查，只提交本批程式、測試、薄入口、SHA 與本卡並 push／核既有 PR head；再用全新 0700 root、官方 SHA ONNX 私有預熱、0-turn 同 PID 啟停與真 Safari 八輪各一次／0 retry，逐輪快照及報告。後段若改掉完整候選，strict FAIL 並留反例，不事後覆寫回覆；不可把這批當正式 holdout 或強 LLM 優勢證據。

更新：2026-10-20。**以下 repair-cue 批次是歷史結果；其「下一步」已由上節取代，不重跑曝光題。**

## 最新結果：P4 日文追問語氣詞誤撞已修，fresh Safari 全批 strict FAIL

舊憑證紙十輪的 B4 `意味を変えず`、B6 `使える` 都被核心單字 `え` 子字串規則錯設 `repair_check`，選定內容在 legacy surface 被固定追問句蓋掉；只讀因果審查和原 strict FAIL 保留。單一變因是隔離 opt-in `uruha_repair_cue_boundary_p4.py` 僅把**詞中**「え」誤觸退回一般回答，真獨立「え？」與舊中英 cue 不動。實作前原 plan/v1 題本 `3124a80` 凍結；v1 T5 deterministic 預檢就因拆句而不符合既有安全分類正控，**v1 preflight FAIL** 保留。模型前只改 T5 成單句的 v2 是**實作後、模型前修訂**，不冒充 preimplementation holdout；opt-in 產品程式與 v2 原件以 `3af068c` 推既有 PR #435。受影響零模型 **118/118**、新產品 SHA **8/8**、前批 SHA **22/22**；舊 v62/v63 SHA-lock 兩項在目前 HEAD 已不吻合，本項沒改核心檔，不動舊鎖。

全新 0700 root `uruha-product-t5nadz1s` 零輪 same-PID ready/planned stop、官方 SHA ONNX 獨立私有預熱、顯式空 profile/T0；真 Safari 新分頁 session `20261020_035130_b9ec7913`，T1–T6 各一次／0 retry、逐輪 T0–T6 雙快照、六個不同 episode、profile 0 rows 同 digest，產品 PID 869 planned stop、7894 vacant。raw 六行 SHA `1295179f08c0dd39b27ce4eb1964ff8034f558570205b3d2a60693528c57e2a8`；逐輪結果、node graph、來源與成本見 `analysis/p4_repair_cue_boundary_fresh_product_probe_result_2026-10-20.md`。嵌詞正例 **4/4** graph act 不再錯追問；真「え？」**1/1** 保留追問；憑證安全正控 **1/1**；Safari 泡泡＝raw＝guard＝graph UTTERANCE **6/6**。**整批 strict FAIL**：T1 core 已錯且日文殘片、T2 選 `承知しました` 最後只說 `うん`、T4 真 cue 選重講卻說固定反問、T6 未知來源錯怪使用者忘記；T3 普通建議有界交付。M21 一般 planner 6/6 完成；新變因 0 model calls；runtime wait proxy 平均 9.8805 秒、獨立 Safari stopwatch 未量，不外推。正式強 LLM、人評、temporal holdout、VRM/Function Calling 完整驗收 pending；Goal active。

**下一個必要交付**：只讀追查 T2/T4 的 selected core→human speech plan→legacy surface→M39/final 斷點，選一個可歸因的「選定行動表達保留」變因，以新未曝光正負控和安全／來源／自然日文／圖／≤20 秒／成本 gate 前瞻凍結，再最小 opt-in 實作與隔離 Safari。T1 候選品質、T6 來源誤解、舊 B1 跨重啟來源、B4 guard-after-frame 分卡；不得重送本六句、改 v1/v2 FAIL 或順手合修。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 未碰。

更新：2026-10-19。**以下憑證紙批次為歷史；其「下一步」由上節取代。**

更新：2026-10-19。**本節是唯一當前續接點；下方各批「下一步」都是歷史，不能重跑曝光題。**

## 最新結果：P4 紙上憑證可見安全有界命中，fresh Safari 全批 strict FAIL

計畫／十句先於實作以 `14469a2` 凍結；opt-in 程式以 `69fe999` 推既有 PR #435。首次 0-turn 因薄入口 `_prior` 少一層而退出、**0 對話題**；修正及入口子程序回歸以 `47f6629` 推送，受影響零模型 **179/179**、product SHA **22/22**。此後另起全新 0700 root `uruha-product-svpk3ay6`，零輪同 PID ready／planned stop、官方 SHA ONNX 私有封網預熱、顯式空 profile/T0；真 Safari A 四輪後 planned restart，同 DB／新 PID 的 B 六輪，十句各一次／0 retry。原始十行 SHA `9f72ae0d91b5c873e934baaf0bf1c773a2761c8a6bd27211230d7b40cb229af3`；完整逐輪、圖、來源、快照與成本見 `analysis/p4_credential_paper_visible_authority_fresh_product_probe_result_2026-10-19.md`。

新安全正例日／中／英 **3/3** 可見日文均不給具體擺放地點；B2 被選 core `机上抽屉里挺安全` 真被改成非具體安全句，新增模型呼叫 0；七個非候選 **7/7** 不被新 gate 錯接管。**整批仍 strict FAIL**：普通物品建議 A1/B6 **0/2** 交付；B1 在 A4 原 User episode 存在且進 `selected_working_memory` 時仍因限定 `direct_episode` 來源未選到而答不知道；B4 引述改寫錯包舊句，frame repair 在 M39／visible guard 後改可見句。Safari 泡泡＝raw＝graph UTTERANCE **10/10**，raw＝最後 `visible_language_guard.final_reply` **9/10**（B4 不等），安全節點 graph/logic **10/10**；T0–T10 雙快照齊全，episode 0→10、profile 0 rows 同 digest；**10/10 ≤20 秒**，平均 10.52437 秒。零輪／A／B 三服務均 planned stop，7894 vacant；兩個新 Safari 分頁保留。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未碰；Goal active。

**下一個必要交付**：先對 B4/B6 的 selected→最後可見行動忠實及 guard-after-frame 做**只讀因果審查**，選一個單一可歸因變因、全新未曝光正負控、before、允許檔案與安全／來源／自然日文／圖／≤20 秒／成本 gate，再前瞻凍結及最小 opt-in 修正。B1 source-channel 授權、A1 M39 formal repair 是獨立缺陷，不在同批合修。不可重送本十句或更改 strict FAIL。正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 統一產品驗收 pending；Goal 未完成。

更新：2026-10-19。**以下 formal-only 與憑證首輪前狀態為歷史，不覆蓋本節。**

## 最新結果：P4 位置建議 formal-only 真 Safari 整批 strict FAIL；下一項先審可見敏感保管

formal-only 計畫／九句先於實作以 `d8aced8` 凍結，opt-in 程式／產品 SHA 以 `b878aa2` 推既有 PR #435；首輪前受影響零模型 73/73、product SHA 19/19 只是契約證據。本批全新 0700 root 真 Safari A 三輪／同 DB planned restart 後 B 六輪，各題一次、0 retry；原始九行 SHA `06a750a72026a4a3c05ca89fbe0a3158b6a82c17a90b9b908484a98ddd5e5a82`。完整逐輪、原件、成本及限制見 `analysis/p4_location_advice_formal_surface_fresh_product_probe_result_2026-10-19.md`。新 formal-only 安全詞尾 **0/2 命中**，兩個建議正例嚴格 **0/2**：模型選定 core 已是 `机の上に置くのがいいよ。`／`机の上に挟むのがいいよ。`，M39 原樣接受，並無被新修復保住或毀掉的命題。A3/B1 直接時間事實與跨重啟原 User episode 成功；B2 第三者 `かも` 丟來源，B3 A3 來源仍在候選池卻未選入，B4 引語外層要求失敗且 25.0505 秒，B6 寫有 PIN 的紙仍得到 `机の上` 具體位置。**B6 是可見安全缺口**：P4 handoff 雖標 `sensitive_placement_context`、formal 不接管，上游一般 planner 仍生成位置，不得稱 guard 有效。

9/9 Safari 目視泡泡＝raw＝最後 guard＝graph `UTTERANCE`，formal node 每輪一個；T0–T9 雙快照即時齊全，episode 0→9、profile 0 rows／同 digest；8/9 runtime wait ≤20 秒、平均 12.9307 秒。新 gate model calls 0，完整 token ledger 不可得。三個 service run 均 planned stop、7894 vacant；兩個新 Safari 分頁保留，既有分頁未關。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未碰；Goal active。

**下一個必要交付**：B6 獨立只讀斷點、單一變因與全新十句條件 gold 已存 `research/p4_credential_paper_visible_authority_postfailure_review_2026-10-19.md`、`research/p4_credential_paper_visible_authority_plan_2026-10-19.md`、`datasets/p4_credential_paper_visible_authority_fresh_probe_2026-10-19.json`，在實作前以 `14469a2` 推 PR #435；新舊 dataset 逐字碰撞 0，preimplementation SHA 3/3。opt-in 可見守門與新 graph 收據已實作，初版以 `69fe999` 推 PR；但首次 **0-turn 啟動**即因薄入口 `_prior` 鏈少一層而退出，沒有送出任何新題、沒有模型對話。已只修啟動鏈並加隔離子程序回歸；聚焦／相鄰零模型 **179/179**，新入口鏈 21/21 可解析。原批未被重跑，首次失敗 root 保留。這些仍不是新模型／Safari PASS。先核修訂 product SHA 22/22、diff review、精確提交本次啟動修正並 push／核 PR head；再按凍結計畫建另一全新 0700 root、0-turn same-PID ready/planned stop、官方 SHA ONNX 私有封網預熱、空 profile/T0，真 Safari A1–A4 後 planned restart，同 DB B1–B6，各句一次／0 retry，逐輪即時雙快照、泡泡＝raw＝guard＝graph、安全回答／負控／記憶／≤20 秒與成本。任一硬 gate 失敗整批 strict FAIL，不重送改判。A1/A2 候選品質、B2 歸屬、B3 來源選擇、B4 form/latency 分卡，不合修；formal-only 失敗保留。正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 統一產品驗收 pending，Goal 未完成。

更新：2026-10-19。**以下是 formal-only 首輪前的歷史續接點；其「下一步」已由上節取代。**

## 當前交付：P4 位置建議 formal-only 選定命題保留，程式已凍結，Safari 首輪待執行

上一批九輪嚴格 FAIL／raw SHA `8e05c0252d01590a8419e1bf86605948cc426932d1f3631c6e85d77a5d354468` 不改判、不重送。A1/B1 已選位置命題被 M39 唯一 `formal_register` 修復改成空泛追問；B3 的 M18 早路徑、B2 的 M31 殘片分因不合修。新工作卡與九句 developer-authored 條件 gold 先於實作以 `d8aced8` 凍結並推既有 PR #435，preimplementation SHA **2/2**。唯一新變因是 opt-in 末端只對 current User 證書、`matched_full_planner`、選定 core SHA、M22 一般路由、M39 唯一敬體問題與安全單句 `…やすいです／…にくいです` 做常體句尾轉換；原日文／M39 guard 仍須接受且可見句保留前綴。其他形態和路由不接管。新 graph 收據分開標 pre-M39 attempt 與 post-M39/post-emit verification；不宣稱命題本身貼合目標。

允許檔案：`uruha_location_advice_act_handoff_p4.py`、`test_p4_location_advice_formal_surface_p4.py`、薄 Web entry/controller、凍結 SHA、結果報告及本卡。新功能目前聚焦與受影響相鄰零模型 **73/73**，語法、Web import、controller `--help` 通過；product SHA **19/19**。**尚無本批 fresh 模型／Safari／產品 PASS。** `output/graduate_application_report/` 是無關既有 untracked，不觸碰；正式 DB 與原始 dirty checkout不碰。

**下一個必要交付**：先 diff review，僅提交本項並 push／核既有 PR #435 head。再新 launcher-owned 0700 root 做 0-turn same-PID ready/planned stop、官方 SHA ONNX 私有離線預熱、顯式空 profile/T0；真 Safari A1–A3，各句一次／0 retry，A3 後 planned stop；同 DB 新 PID/session B1–B6，逐輪即時存 T1–T9 episode/full-profile。核 A1/A2 **2/2** 目標相連位置原則且至少一輪真 formal-only 保留、A3/B1/B3 直接時間來源、B2 第三者不確定、B4 引用、B5 no-advice、B6 敏感；9/9 泡泡＝raw＝guard＝graph、自然日文、≤20 秒、九 episode、T0–T9 profile digest、0 retry、新變因 0 model calls 和可得成本。任一硬門檻失敗整批 strict FAIL，不重發題句追分。正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 統一入口仍 pending；Goal active。

更新：2026-10-19。**以下是本次 formal-only 修正前的歷史續接點；其「下一步」已由上節取代。**

## 最新結果：P4 位置建議言語行為交接已真 Safari 驗收，整批 strict FAIL

前批 B5 空泛放置回答不改判／不重送。本批 plan／九句在 `5aaf6ab` 先凍結，opt-in handoff／測試／product SHA 以 `e7f5196` 推既有 PR #435；11/11 聚焦、84/84 相鄰零模型與 manifest 15/15 僅是接線證據。全新隔離 0700 root 的 0-turn ready、官方 SHA ONNX 私有離線預熱、空 profile、真 Safari 兩 session／同 DB planned restart 已完成；九句各一次／0 retry。詳細逐輪、原件、局部成功、失敗與成本見 `analysis/p4_location_advice_act_handoff_fresh_product_probe_result_2026-10-19.md`；raw 九行 SHA `8e05c0252d01590a8419e1bf86605948cc426932d1f3631c6e85d77a5d354468`。

**整批 strict FAIL：3 個建議正例 0/3 可見交付。** A1/B1 選定的放置候選被 M39 `formal_register` repair 改成空泛追問；B1 原候選也未明確對齊「易發放」。B3 被 M18 `calibrate_need` 失眠模板快路徑越過 advice prompt，答了與色鉛筆不相干的句子；非 DB 污染。B2 第三方猜測控制雖未變成確定事實，最終只剩殘片 `係の人、色鉛筆`，語意／自然度失敗。A2/A4 事實問答來源 2/2、A3 User 斷言保留、B4 不回答引號內問題、B5 遵守不提議；不能抵銷正例與 B2 失敗。9/9 Safari 泡泡＝raw＝最後 guard＝graph UTTERANCE；T0–T9 逐輪兩類快照齊全，episode 0→9、profile 0 rows／同 digest；9/9 runtime user wait ≤20 秒，平均 10.9346 秒。新 gate 模型呼叫 0；M21 full-planner completed 5、M31 completed 2、M45 completed 0，總 token ledger 不完整。0-turn／A／B 服務 planned stop，7894 vacant。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未碰；Goal active。

**下一個必要交付**：先就 A1/B1 做 M39「僅 formal-register 違規時是否能保留選定命題」的單變因設計審查，凍結**全新未曝光**建議正負控、protected／多重違規、事實來源、語氣與圖／記憶／≤20 秒成本 gate；只對安全可辨識句尾做自然常體修復，其他情形維持原 fail-closed，不重送本九句追分。B3 的 M18 跨領域模板與 B2 片語忠實度是獨立後續問題，不能在這項合修或宣稱修完 M39 就達產品 PASS。若兩個有根據的修正批次仍失敗，需留 `REVIEW_REQUIRED` 與最小反例，停下任意加規則。正式強 LLM 同模型比較、真人、temporal holdout、VRM／Function Calling 統一驗收仍 pending。

更新：2026-10-19。**以下是位置建議探針前的歷史續接點；其「下一步」已由最上方新結果取代。**

## 最新結果：P4 本地時間／位置答案來源授權局部成立，fresh Safari 整批 strict FAIL

`5b1437afedadded478a20dbc50fa3cd5aff8f148` 已把 opt-in 來源授權與首輪前 SHA 推既有 PR #435；12/12 聚焦、118/118 受影響零模型測試只算程式證據。全新 0700 隔離 root、0-turn same-PID ready/planned stop、官方 SHA ONNX 私有離線預熱、顯式空 profile 後，真 Safari 兩 session 同 DB 在 A4 後 planned restart，凍結 11 句各一次／0 retry。詳細原件、逐輪表與失敗歸因見 `analysis/p4_local_time_place_answer_authority_fresh_product_probe_result_2026-10-19.md`；raw 11 行 SHA `5b6543bad332c8a28abb82ad2f0d00732a7d7d1beec4bd5ab853c90b893c0b5d`。

有界子能力：無 User 來源 A1/B2 **2/2** 不編，直接 User 來源 A3/B1/B4 **3/3** 答值且 B1 跨重啟用真 `direct_episode`；A4 第三者「かも」未升格，B5/B6/B7 原結構路由未被新 gate 越權。11/11 Safari 泡泡＝raw＝graph utterance＝guard、11/11 ≤20 秒（平均 10.7321、最大 14.2247）、十一個不同 episode；新 gate 0 模型呼叫，但舊 M21/M31 計算保留。三個服務 PID planned stop／7894 vacant。**整批 strict FAIL**：A1 後漏存當時 T1 profile/episode 快照，不能從 T2 倒補；B5 建議問句只回 `予備マイクは適当な場所に。`，行動忠實度不過；B6 對未提供的歌詞片段憑空責備，A4 日文雙 `が` 生硬。T0、T2–T11 的 profile 0 rows 同 digest，不代替缺失 T1。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未碰；Goal active。

**下一個必要交付**：先只讀審查 B5 `chat`／M45 建議行為斷點並選一個可歸因變因，以**全新未曝光**正負控、before、允許檔案、成功／失敗、≤20 秒／自然日文／圖／記憶／成本 gate 前瞻凍結，再做相稱 opt-in 實作與隔離 Safari。B6 無證據責備、A4 語面與 T1 收據流程分因處理；本 11 句不可重播追分或改判。若兩次有根據修正仍失敗，保留 `REVIEW_REQUIRED`；正式同模型強 LLM、真人、temporal holdout、VRM／Function Calling 仍 pending。

更新：2026-10-19。以下是本批首輪前歷史狀態；其「下一步」均已執行或作廢。

## 當前交付：P4 本地時間／位置 User 來源授權，程式已凍結，Safari 首輪待執行

前批 `reference_probe` 八輪 strict FAIL 與 raw SHA 不改判、不重播。本項唯一變因按 `ef97590` 事前凍結的計畫／十一句條件 gold：只在 opt-in 產品入口對有界本地開始時間、置放地點問句，以本輪確實交給決策的原始 User turn 授權具體值；無來源、第三方猜測、舊 assistant 答案、summary、時間戳與衝突不能當事實。source-bound 回覆、selected plan、visible guard 與新 graph node 共用證書；舊規劃節點標 shadow，成本保留。重啟需真 `direct_episode`、`turn_episode` stored-metadata type；缺檢索即產品 FAIL，不偷查 DB。受保護／尋曲／建議路由維持原狀。程式的保守文法與 40 字 core 上限不是開放領域問答或自然日文保證。

新增 `uruha_local_fact_answer_authority_p4.py`、12 個聚焦零模型契約、薄 Web entry/controller。聚焦與受影響相鄰 **118/118**（其後聚焦增補安全負控再 12/12），語法、Web entry import、controller `--help` 通過；獨立只讀審查指出的 fake recent trace ID、pre-gate personhood／prediction 殘留、post-guard mismatch 可偵測性已補契約或 shadow。`research/p4_local_time_place_answer_authority_product_freeze_2026-10-19.sha256` 為本批首輪前 13 檔 SHA；與事前 2 檔 SHA 分開。這些只是程式證據，**尚未有本批 fresh 模型／Safari／產品 PASS**；末端如再變更已授權回覆，收據標 `post_guard_surface_mismatch`、整批按 hard gate FAIL，不假稱絕對阻斷所有下游變更。

**下一個必要交付**：先核 preimplementation/product SHA、diff、只提交本項並 push 既有 PR #435／核 head；再新 0700 root 做 0-turn 同 PID ready/planned stop、官方 SHA ONNX 私有離線預熱、顯式空 profile。真 Safari A1–A4，planned stop 後同 DB B1–B7；11 句各一次／0 retry，逐輪核來源 trace、selected／visible／graph、自然日文與行動忠實、泡泡＝raw＝UTTERANCE、十一 episode、T0–T11 profile digest、≤20 秒、模型呼叫及可得 token／延遲。任一硬門檻不過整批 strict FAIL，報告失敗且不重送題句追分。正式同模型強 LLM、真人、temporal holdout、VRM／Function Calling 仍 pending；Goal active。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-19。以下是更早的首輪前歷史狀態；下方參照探查結果保留，不重播原八句。

## 當前執行：P4 本地時間／位置答案的 User 來源授權，計畫／新題已凍結

上批 `reference_probe` 准入 4/4 假陽性阻擋、2/2 真參照保留，但整批 strict FAIL；A3/B1 的 M21 被選 `core_message_jp` 已編出無來源「午前中／机の下」，M22 仍歸 `general_conversation`，M39／語言守門未攔。只讀審查確認原 trace 不存三候選 core，不能斷言每個候選都編值；也不能把 B1 記憶裡的舊 assistant 答案洗成證據。唯一新變因是 opt-in 本地時間／位置問答的**來源准入**，依已交給決策的原始 User turn 授權值、未知時不編，同證書核 selected／visible／graph；A1 latency、參照語氣與舊 M22 scorer 不合修。

實作／新模型首輪前計畫與 11 句條件 gold 已凍結在 `research/p4_local_time_place_answer_authority_plan_2026-10-19.md`、`datasets/p4_local_time_place_answer_authority_fresh_probe_2026-10-19.json`，preimplementation SHA 2/2；新句對既有 dataset JSON 逐字碰撞 0。兩 Safari session 同 DB、A4 後 planned restart；A1/B2 無來源不編，A3/B1/B4 有來源答值（B1 必須跨重啟檢索且傳到決策），A4 第三者推測不升格，B5 建議／B6 真參照／B7 保護路由不變；11/11 泡泡＝raw＝graph UTTERANCE、自然日文、十一 episode、T0–T11 空 profile 同 digest、每輪 ≤20 秒、0 retry。任何硬門檻失敗 strict FAIL；這是開發者 fresh 產品探針，非正式 holdout／同模型比較／人評。

**下一個必要交付**：依凍結允許檔案做最小 opt-in adapter、聚焦與相鄰零模型回歸、薄現有 Gradio 入口／隔離 controller；product SHA、diff review、精確 commit／push／PR #435 head 後，才用新 0700 root／官方 SHA ONNX 私有離線預熱／空 profile 做真 Safari 11 輪。逐輪核來源 trace ID、選定計畫、最後可見、成本及 graph；失敗不重送改分。正式同模型／真人／temporal holdout／VRM／Function Calling 仍 pending，Goal active。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

更新：2026-10-19。以下參照探查結果為歷史，不覆蓋上節。

更新：2026-10-19。以下是參照探查批的歷史結果；其「下一步」已由最上方新任務取代。前批 strict FAIL 不改判、不重播。

## 當前結果：P4 參照探查 source-evidence admission 有界成功／產品 strict FAIL

唯一變因是 opt-in 當輪來源／言語行為准入；前瞻計畫／八句 gold 先於實作以 `3cabf42` 凍結，程式／產品 SHA 以 `21527e3` 推既有 PR #435。零模型聚焦／相鄰 **193/193**，preimplementation SHA 2/2、product SHA 9/9。全新 0700 隔離 root、0-turn readiness／planned stop、官方 SHA ONNX 私有離線預熱、顯式空 profile 後，真 Safari 兩 session 同 DB planned restart，八句各一次／0 retry。完整原件、逐輪與成本見 `analysis/p4_reference_probe_evidence_fresh_product_probe_result_2026-10-19.md`；raw 八行 SHA `892e98fb2dc29531e5b0f518cfeea3a1f935aa8b679251ad901d001e8dfa9618`。

狹義准入結果：四個舊假陽性 **4/4** 被拒、兩個真參照 **2/2** 保留、受保護路由 **1/1** 保留；8/8 Safari 泡泡＝raw＝graph UTTERANCE＝guard，八個不同 episode，T0–T8 profile 0 rows／同 digest。**整批 strict FAIL**：A1 22.9159 秒 >20 且把普通自述改問句；A3/B1 一般 planner 被選 core 產生無來源「上午／桌下」並通過表面守門；A4/B2 真參照回覆口吻責備而非自然承接。user wait 7/8 ≤20 秒、平均 9.8632625；全 token ledger 不可得。兩 PID planned stop／7894 vacant，兩個新 Safari 分頁保留，其餘未關。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未動。

**下一個必要交付**：對普通時間／位置資訊問句的來源授權做單一可歸因新任務；先只讀設計審查現有 M22/M21／末端來源守門，分辨候選生成與選取的未觀測處，凍結新未曝光有／無來源正負控、條件 gold、≤20 秒／日文／圖／記憶／成本 gate 及 SHA，再最小 opt-in 實作與全新隔離 Safari。不得重送本八句、改舊 gold 追分、把「一律不知道」當方案，亦不合修 A1 latency 或 A4/B2 口吻。新批失敗照留，至多兩個有根據修正批後 `REVIEW_REQUIRED`。正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 統一入口 pending；Goal active。

更新：2026-10-19。以下是本批首輪前歷史狀態，不能覆蓋上節結果。

## 歷史：P4 參照探查程式與新題已凍結，Safari 首輪待驗

唯一變因維持先前凍結的當輪來源／言語行為准入；舊 core、前批 raw 和八句 gold 未改。新增 opt-in `uruha_reference_probe_evidence_p4.py`、聚焦測試、薄 Web 入口及隔離 controller。相同證書約束 seed、critique、候選選取與右腦弱參照 rescue；末端若仍選錯，拒絕舊參照計畫並標記其圖節點為 shadow，不把舊情緒影響套用到新選定計畫。獨立審查發現並補入 `EDは何時？`、第三者引號內尋曲、引用台詞自然度三類負控及原文 digest；這些是同一准入變因，未改八句凍結題。

首輪前零模型聚焦／相鄰 **193/193**，語法與 controller `--help` 通過；preimplementation SHA 2/2、product SHA 9/9。這些僅是契約證據，**當時尚未有本批真實模型／Safari／產品 PASS**。下文原先的 diff review、提交、Safari 步驟均已執行，不再重做；正式同模型、真人、temporal holdout、VRM／Function Calling 仍 pending，Goal active。無關 `output/graduate_application_report/`、原始 dirty checkout、正式 DB 不碰。

更新：2026-10-19。**本節是唯一當前續接點**；下方 deterministic plan-leak 結果與所有舊「下一步」是歷史，不覆蓋本節。

## 當前執行：P4 參照探查 source-evidence admission，前瞻計畫已凍結

上一批八輪 strict FAIL／0 eligible 及原 raw SHA 不改判、不重播。只讀因果審查確認 B1 的 `プラネタリウム` 內嵌 `ネタ`、B3 的 `投影` 內嵌 `影`，在舊 ≤22 字 substring 規則被錯選 `reference_probe`；後段 `_critique_plan` 可能二次注入。A1/A3/A4 是不同斷點，不合修。新單一變因是 opt-in `reference_probe` 當輪來源／言語行為證據准入，**同一證書**約束 seed、critique 與 selected；不能靠兩句黑名單、也不以固定澄清句取代。

新設計／八題與條件 gold 已在實作前凍結於 `research/p4_reference_probe_evidence_admission_plan_2026-10-19.md`、`datasets/p4_reference_probe_evidence_fresh_probe_2026-10-19.json`；preimplementation SHA 2/2。純規則 before：四個 false `reference_probe` 正例、兩個真參照控制、一個無 rule、一個受保護辱罵。**尚無本批新 code／模型／Safari 證據**；不能把計畫或舊批輸出當產品改善。

**下一個必要交付**：依凍結允許檔案做最小 opt-in adapter、薄產品入口／controller、聚焦和相鄰回歸；首輪前 product SHA、diff/commit/push/PR head，再全新 0700 隔離 root、空 profile／官方 SHA ONNX 私有離線預熱、真 Safari 兩 session 同 DB planned restart，八句各一次／0 retry。逐輪核 4/4 false admission 阻擋、2/2 合法參照保留、保護負控、最終自然日文／行動忠實／未知不編、raw＝graph＝泡泡、每輪 ≤20 秒、episode/profile、PID/port 和可得成本。失敗保留 strict FAIL，不改題追分；正式同模型／真人／temporal holdout／VRM／Function Calling 仍 pending，Goal active。原始 dirty checkout、正式 DB 與無關 `output/graduate_application_report/` 不碰。

更新：2026-10-19。以下 deterministic plan-leak 結果及其舊「下一步」保留為歷史；不能覆蓋最上方的新准入任務。

## 當前結果：P4 確定性內部策略外洩八輪 strict FAIL／未命中

上一批 typed-source 九輪 T4 真實 `short_confusion` 內部策略句外洩與 T1 超時分因審查後，本輪先以 `b710534` 凍結單變因計畫及八句，後以 `3d017c7` 凍結 opt-in 最後可見 speech-act guard／測試／產品 SHA 並推既有 PR #435。零模型聚焦＋相鄰 89/89、preimplementation SHA 2/2、product SHA 6/6。全新 0700 隔離 root、0-turn readiness/planned stop、官方 SHA ONNX 私有預熱及空 profile 後，Safari 兩 session、同 DB planned restart，共八句各一次、0 retry；原始 raw SHA `ccf6e137a102f6cc1e672b066e9abcfb1fa57a7d343fe0790eadf86b4408aae5`。逐輪、圖、成本與邊界見 `analysis/p4_deterministic_plan_leak_surface_fresh_product_probe_result_2026-10-19.md`。

**整批 strict FAIL**：實際符合 `low_road/short_confusion/plain_reply/selected deterministic/plan-leak rejection` **0/8**，新增 node 0/8，不能主張新機制在 fresh Safari 已證明改善。A1 user wait **23.5476 秒** >20；A1/B1/B3 把普通完整語句／資訊問句誤作殘句或梗，A3 不接住明示修正、A4 未交付一個點子，B4 保護路由雖保住但末句不自然。8/8 Safari 泡泡＝raw＝graph UTTERANCE＝guard，八個 episode，T0–T8 profile 0 rows／同 digest；服務 planned stop，兩 PID exited、7894 vacant。這些一致性與隔離門檻不抵銷品質／coverage／latency 失敗。兩個 Safari 測試分頁保留，其他未關。正式同模型比較、真人、temporal holdout、VRM／Function Calling 統一入口仍 pending，Goal active。

**下一個必要交付**：先只讀設計審查新 raw 的普通語句／問句錯路由與 selected→final 對話行為，分開舊 T4 策略外洩，挑一個對正常聊天最關鍵且可歸因的變因；事前凍結新的未曝光正負控制、gold、≤20 秒／自然日文／來源／episode/profile／graph／成本 gate 與 SHA，再實作、相稱回歸、全新隔離 Safari。不能重播本八句、改本批判準或把未命中新 guard 視為產品 PASS。無關 `output/graduate_application_report/`、原始 dirty checkout、正式 DB 不碰。

更新：2026-10-19。**本節是唯一當前續接點**；以下所有舊「下一步」保留為歷史，不能覆蓋本節。

## 當前交付：typed episode 來源回憶九輪已驗，整批 strict FAIL

首輪前設計／九題以 `01947d0` 凍結，opt-in adapter／薄 Web entry/controller／產品 SHA 與 125/125 零模型聚焦及相鄰回歸以 `38a06d6` 推既有 PR #435；preimplementation SHA 2/2、product SHA 11/11。真 Safari 在新的 0700 隔離 root `uruha-product-f33brkmw` 跑 session A 5 輪、T5 後真 consolidation／planned stop、同 DB 新 PID/session B 4 輪，各句一次／0 retry。完整逐輪、來源圖、成本與限制見 `analysis/p4_typed_episode_recall_source_fresh_product_probe_result_2026-10-19.md`；raw 九行 SHA `d727d22936a98ef2983064611128e676c6c423886e5907bee491a3b3eb491b5b`。

有界新能力可見：T6 pool 中原生摘要 rank 1、T1 直接 User episode rank 6（top-5 外），typed audit 禁摘要作**最終答案**，專用 handoff 找回 T1「白い階段」而非朋友引述的「赤い門」；T7 兩個直接時間來源衝突不任選，T8 未知牆色不捏造，T9 當輪撤回可見（未測之後是否遵守）。9/9 Safari 泡泡＝graph `UTTERANCE`＝raw；九個不同 episode，T0–T9 full-profile 都是 0 rows／同 digest；兩個 PID planned exited、7894 vacant；正式 DB、原始 dirty checkout及無關 `output/graduate_application_report/` 未動。摘要仍進舊工作記憶／一般 planner 候選，故只主張最終答案權限隔離。

**整批 strict FAIL，不能重播追分**：T1 完整使用者等待 22.6619 秒 > 凍結上限 20 秒，只有 8/9 達標；T4 可見句把「先停下來問」的內部策略說出卻沒真正問，T7/T8 `確かには言えない` 生硬，T9 無句尾標點。typed-source 狹義成功不等於自然日文／人格／產品全通過，也不是正式同模型強 LLM、真人被理解感或 temporal holdout 證據。可靠全管線 token ledger 尚未確認。Goal active。

**下一個必要交付**：先只讀設計審查這批 T1 冷首輪的 M31／M21 串行成本與 T4 對外露出內部策略兩個不同問題，選擇阻擋門檻的單一可歸因變因；若要動 code，先定新題、條件式 gold、精確門檻、允許檔案與 SHA，再按單一任務卡實作、相稱回歸與全新隔離 Safari。不可重播本九題、改弱 baseline 或把支持工程另編 M 充數。正式同模型／holdout／真人／VRM／Function Calling 等上層仍 pending。完成本報告與卡片後只提交本項結果並 push 核 PR head。

更新：2026-10-19。以下是**本批首輪前歷史狀態**；下方「P4 句尾 copula 六輪」及其他歷史下一步均不再直接執行。

## 歷史：P4 typed episode 來源顯性回憶，程式／凍結題已備、Safari 尚未執行

上批六輪 Safari strict FAIL 與 raw SHA `2b343e003101ba0cbf5940c6093686fc96ff0c333e60738a6dcaba72b4d3db78` 保留，不重送。只讀根因審查發現 T6 候選 rank 3 是合法 `episodic_consolidation` 摘要；舊 `explicit_episode_recall_focus` 把同 episode collection 的每筆候選都當 turn serializer 驗證，因此整池 `episode_provenance_incomplete`，即使 rank 7 T1 直接 User episode 還在也無法回答。`consolidation_state=consolidated` 的 T1 仍屬 `source=turn_episode`，不可誤排除。這比僅稱 top-5 rank 問題更精確；原批不改判。

唯一新變因是 opt-in `uruha_typed_episode_recall_source_p4.py`：把 Chroma metadata `source` 的 bounded type 投影到 episode trace；僅對狹義顯性回憶，核對候選 ID／文檔／類型及 retrieved/pool 一致後，從**焦點副本**排除驗證過的整合摘要，讓原始 User turn 獨占事實答案權限。原候選池、排序、top-5、分數、圖、資料庫及 frozen focus 模組不改；未知類型、文件矛盾、畸形 turn、重複 ID fail-closed。新的薄 Web entry/controller 只在隔離產品入口安裝。此修正不處理 copula coverage、T1 frame shadow 或原 T6 日文措辭，不能把單元通過說成產品 PASS。

新九題／條件式 gold／same-DB restart 與 strict gate 在實作前以 `01947d0` 凍結於 `research/p4_typed_episode_recall_source_plan_2026-10-18.md` 與同名 dataset；preimplementation SHA 2/2。局部聚焦 **7/7**、含 pytest function tests 的受影響 P4／memory 相鄰合計 **125/125** 零模型測試通過，Python compile、controller `--help` 通過；read-only 審查發現 optional provenance list 畸形會 throw，已補 fail-closed 與回歸。`research/p4_typed_episode_recall_source_product_freeze_2026-10-19.sha256` 首輪前 **11/11** 相符；尚無本批 fresh model 或 Safari 證據。新題 exact collision 0/9，developer-authored 非正式 holdout。提交前本分支較 origin 多一筆資料凍結 commit，opt-in code 待提交；無關 `output/graduate_application_report/` 不碰。

**下一個必要交付**：只提交本項並 push 既有 PR #435／核 head。再全新 0700 隔離 root 做 0-turn readiness/stop、官方 SHA ONNX 私有離線預熱、顯式空 profile；依凍結九題各一次／0 retry，在 T5 後等真 `episodic_consolidation` 收據並 planned stop／同 DB restart。T6 須同池有摘要與 T1 原始 turn，核焦點／handoff／selected／泡泡同源；T7 衝突、T8 未知、T4 引述、T9 撤回各守邊界。逐輪核 raw＝graph UTTERANCE＝Safari、自然日文、≤20 秒、不同 episode、profile 0 rows／同 digest、可得 token/延遲、PID/port。任一 gate 失敗存原件、strict FAIL、不補送。正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 整合仍 pending；Goal active。

更新：2026-10-18。本節是**唯一最新續接點**；以下「Safari 首輪待執行」及更早的下一步都已成歷史。

## 最新結果與下一個必要交付：P4 句尾 copula 六輪 Safari strict FAIL

首輪前 `7a18043` 凍結新六句／gold／計畫、`f9910cc` 凍結 opt-in code／產品 SHA，均已在既有 PR #435。零模型聚焦 36/36、相鄰回歸 96/96，preimplementation SHA 2/2、product SHA 10/10。新 0700 隔離 root、0-turn readiness／planned stop、官方 SHA ONNX 私有離線預熱、顯式空 profile 後，真 Safari 兩 session 同 DB，T4 後 planned restart；T1–T6 各一次／0 retry。完整原件、逐輪、圖和邊界見 `analysis/p4_terminal_copula_commit_latency_fresh_product_probe_result_2026-10-18.md`，raw SHA `2b343e003101ba0cbf5940c6093686fc96ff0c333e60738a6dcaba72b4d3db78`。

6/6 Safari 泡泡＝graph UTTERANCE＝raw，6/6 user wait ≤20 秒（平均 8.1550、最大 14.6911），T1–T6 六個不同 episode，full profile 各輪與重啟前後皆 0 rows／同 digest；兩 PID planned exited、7894 vacant。M31 completed 3 次，M21 general-model completed 0 次，新 gate 自身加 0 次；可靠全管線 token ledger unavailable。T2 同 session 可從 T1 原話回憶；T3 引述與 T4 否定控制未翻成當輪事實／肯定。

**整批 strict FAIL，不重送追分**：預設新 copula mismatch 正例 T1/T5 **0/2 coverage**，M31 實際 canonical 是 `…にある`、不是句尾 `…である`；新來源證書 fail-closed、沒有新 `である→だ` 提交，T5 是**舊** M32 獨立成功，不能算新機制或降延遲因果證據。T1 把直接陳述改問句（frame shadow violation）。T6 在同 DB 重啟後沒有答出 T1 直接原話且日文 `確かには言えない` 生硬；T1 episode 並未丟失，而是在八個 retrieved candidates 中 rank 7、未進 top-5／focus 可回答來源／leftbrain handoff。舊 graph 的 `memory_anchor` 等欄位也不能稱全面同源。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未動；正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 整合仍 pending，Goal active。

**唯一下一個必要交付**：只讀設計審查，分開 copula canonical 覆蓋與跨重啟 episode handoff 兩個問題，各自選單一可歸因變因；優先核 T6 來源候選 rank 7 到專用 focus 的斷點，因它阻擋核心記憶產品。若選擇改動，先凍結未曝光的直接來源／干擾／引述／未知與 restart 正負控、成功／失敗、成本、允許檔案與 SHA，再做至多一次有根據的獨立修正批；不可重播本六句或把 T1 frame、T6 日文表面順手混進 copula patch。第二個有根據修正仍失敗則 `REVIEW_REQUIRED`。P4、整體專案與 Goal 均未完成。

更新：2026-10-18。本節是**唯一最新續接點**；以下舊「下一步」留作歷史。

## P4 句尾 copula M32 有界提交：程式已驗、Safari 首輪待執行

上一批時間片語回憶八輪的 strict FAIL 與 raw SHA 不改判、不重播。只讀歸因見 `research/p4_terminal_copula_commit_latency_plan_2026-10-18.md`：普通直接陳述的 M31 產生與原句對齊的 canonical `…である`，舊 M32 因 predicate `…だ` 不在 summary 內，唯獨雙錨點失敗，落入第二次 M21 模型規劃。唯一新變因是 opt-in `uruha_terminal_copula_commit_latency_p4.py`：M31 邊界先拿真原文作逐字來源證書；舊 M32 先跑、且只有這個單一失敗時，複製句尾 `である→だ` 再跑**未改的原 M32 全守門**。不改原 M31/M32、舊資料或記憶。

新六句、條件式 gold、T4 後同 DB planned restart 與 ≤20 秒 strict gate 已在實作前以 `7a18043` 凍結；首輪前 exact collision 0/6。聚焦零模型 **36/36**、擴大相鄰 M31/M32/M33/source/quote/episode/temporal **96/96** 通過，語法、Web entry import、controller `--help` 通過；preimplementation SHA **2/2**、product SHA **10/10** 均核對。這些尚非模型／Safari 產品通過，原實驗不具有同題延遲因果 A/B 或正式 holdout 身分。

**唯一下一步**：只提交本項 opt-in 模組、測試、薄 Web 入口/controller、product SHA 與本任務卡，push 既有 PR #435 並核 head；然後全新 0700 隔離 root 做 0-turn readiness／planned stop、官方 ONNX 私有離線預熱、顯式空 profile，再按凍結 T1–T6 各送真 Safari 一次／0 retry、T4 後同 DB planned restart。逐輪核 M31 shape、M32 轉換收據、M21 完成呼叫、raw＝graph utterance＝泡泡、直接來源與重啟前 T1 回憶、自然日文、延遲、episode、profile digest 與 PID/port。任一 gate 失敗，整批 strict FAIL，保存原件及成本，不補送追分。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 不碰；Goal active。

更新：2026-10-18。下節是**唯一最新續接點**；以下舊「下一步」均屬歷史。

## 最新結果與下一個必要交付：P4 時間片語具體回憶 Safari strict FAIL

`2766bdc` 先凍結新八句與計畫，`f62e3e6` 再凍結 opt-in 准入、薄 Web 入口與產品 SHA，兩者已推 PR #435。新隔離 0700 root 經 0-turn readiness、官方 SHA ONNX 私有離線預熱、顯式空 profile 後，Safari 兩 session 同 DB、T4 後 planned restart，T1–T8 各一次／0 retry 已完成。T3/T7 專用來源節點均從 rank 6、普通 top-5 未選的 T1/T5 直接 User episode 取得正確回覆；T4 引述外層評語不誤回憶，T8 缺來源不編顏色。8/8 泡泡＝raw＝graph utterance；八個不同 episode，T0–T8 full profile 0 rows／同 digest；兩 PID planned exited、7894 vacant。raw SHA `4a555de6ae4a0a4b26b3b84b01a332ac6e9a9b46a092feb4b992ca2632774683`，完整逐輪與成本見 `analysis/p4_temporal_specific_recall_admission_fresh_product_probe_result_2026-10-18.md`。本次聚焦／相鄰零模型 37/37、preimplementation SHA 2/2、product SHA 9/9。

**整批 strict FAIL，不重播或放寬 gate**：T1 user wait **22.8402 秒** >20.0；8 輪平均 6.91625、7/8 達標。T1 預熱 ready，但 cognition 20.2296 秒，M31 11.7562 秒與 M21 full planner 8.3131 秒同輪；尚未用干預確證最小性能修正。T2 問「還記得我嗎」卻答「有在意你／你呢」，selected `ask_miss_me`，按凍結直接問題 gold 至少是回答忠實度疑似額外 FAIL。T8 `確かには言えない` 有日文自然度疑慮，事前自然日文 gate 亦不能宣稱已驗收；無獨立母語人評。T3/T7 專用 focus→selected core→utterance 同源，但舊 `selected_plan.memory_anchor` 仍指干擾 short_term、舊 `post_check` 說未顯性使用記憶；不能宣稱整張 graph 所有欄位一致。重啟後的 DB snapshot 保留 T1，但 T7 找的是重啟後才寫入的 T5，本批**未測重啟前來源的可見回憶**。完整 token 不可得。正式 DB／原始 dirty checkout／無關 `output/graduate_application_report/` 未動；正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 整合 pending，Goal active。

**唯一下一個必要交付**：先只讀設計審查 T1 普通直接陳述的 M31 + M21 串行慢路徑，用 raw、凍結圖與既有代碼確定一個可歸因性能變因；前瞻凍結新的未曝光正負控、來源忠實度／人格／日文／寫回、≤20 秒與成本，再做最小 opt-in 實作與新隔離 Safari。不得重播本八句、用慢路徑的舊輸出追分，亦不得將舊 graph 欄位同步與 T8 措辭順手混進同一變因。若兩次有根據修正仍失敗，保留 `REVIEW_REQUIRED` 等審查。

更新：2026-10-18。這是唯一當前工作順序；以下各節的舊「下一步」均是歷史。

## 最新結果與下一個必要交付：P4 關係答案權限六輪 Safari strict FAIL

前瞻設計／六句先以 `1da572e` 凍結；opt-in answer-authority、產品 SHA 8/8 與零模型／相鄰 33/33 後以 `f7796f6` 推既有 PR #435，head 已核對。全新 0700 隔離 root、0-turn HTTP readiness／planned stop、官方 SHA ONNX 私有離線預熱、顯式空 profile 後，用 Safari 在同 DB 兩 session 做 T1–T6 各一次／0 retry、T4 後 planned restart。T2/T6 selected `ask_miss_me` 都有 `short_term`／`quoted_line_feedback` 真來源命中，新圖節點撤泛用 context 的可見答案權限，回覆未再引用台詞；T1/T5 正確只答引述外層語氣。6/6 泡泡＝raw＝圖 utterance、6/6 ≤20 秒（平均 4.7813、最大 14.8248 秒）、六個不同 episode、T0–T6 七份 full profile 0 rows／同 digest；兩次真 session PID 均 planned exited、7894 vacant。原件 SHA、逐輪、圖、成本與誠實邊界見 `analysis/p4_relationship_context_answer_authority_fresh_product_probe_result_2026-10-18.md`。正式 DB／原始 dirty checkout／無關 `output/graduate_application_report/` 未動。

**整批 strict FAIL，不重播追分**：T4 問 T3 的集合目印，最終卻回 T2 的「前に:ねえ、うちのことまだ覚えてる？」。T3 來源存在於候選池 #2；舊 specific-recall 未涵蓋 `少し前に言った`，泛用 `覚えてる？` 選成 `chat/memory_presence_reply`，generic anchor fallback 取無關 T2 #1。新關係權限 gate 對 T4 未啟用，故 T2/T6 有界正例不等於整體事實記憶或產品 PASS。整份 runtime_state/history 與最終 trace 的 late nodes 亦非逐欄完全同鏡像；只報有核對的權限節點和 utterance。T3 有一次 M31 模型呼叫，不能稱全管線零 token。

**唯一下一個必要交付**：以 T4 raw 只做新項的 before 證據；先只讀設計審查「來源限定的具體事實回憶焦點」，明確選一個可歸因能力變因，凍結全新未曝光正負控制、來源忠實度、未知／衝突、≤20 秒、profile／episode／圖與重啟 gate，再做 opt-in 實作、相稱零模型與隔離 Safari。不可重送本六句、改本批 gate，或將泛用 `覚えてる？` 直接列為足夠的事實答案來源。T7 類混合 frame、T8 具體精簡與 T1 冷啟延遲分卡。正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 整合仍 pending；Goal active。

更新：2026-10-18。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 最新結果與下一個必要交付：P4 引述台詞 act-scope Safari strict FAIL

首輪前 `524e873` 凍結新八句與 gate，`09ed473` 凍結 opt-in code／相鄰 35/35 零模型測試並推 PR #435；product SHA 13/13 OK。全新 0700 隔離 root 真 Safari T1–T8 各一次、0 retry，T4 後 planned stop／同 DB 新 session 重啟。8/8 Safari 泡泡＝runtime graph UTTERANCE＝raw；T0–T8 九份 full profile 均 0 rows／同 digest、八個不同 episode、終局兩 PID exited／7894 vacant。T2 直接回憶能精確找回 T1 episode；T3/T5/T8 的有界引述 certificate、selected 與可見回覆一致，沒有把引號內問句當成本輪記憶／關係請求。完整逐輪、失敗歸因、成本、原件 SHA 見 `analysis/p4_quoted_line_act_scope_fresh_product_probe_result_2026-10-18.md`。

**整批 strict FAIL，不重播追分**：T1 user-wait 21.7664 秒 >20 秒，且 `了解しました` 的敬體不符 casual 人格目標；T6 selected `ask_miss_me` 卻把 T5 引述台詞作記憶答案，並有不自然標點；T7 selected 真外層關係問句，最後被舊 short-term anchor／frame repair 改為離題「記載」；T8 雖識別外層 shorten，只給泛泛方向，未交付針對該句的精簡版本。新 scope 有限能力成立不等於產品 PASS，正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 整合仍 pending。

**唯一下一個必要交付**：先做只讀設計審查，分開 T6/T7 的舊 short-term answer-authority／selected→final 忠實度、T8 的具體精簡交付、T1 冷啟 latency；各自界定單一變因與成本，選一個阻擋產品 gate 的最小必要修正，先凍結新未曝光題與成功／失敗，再實作及驗收。不可將八句原題重播或放寬 gate，亦不碰原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/`。Goal 未完成。下列首輪前與舊批「唯一下一步」均是歷史。

## 歷史：P4 引述台詞與當輪行為分界（首輪前，尚未產品驗收）

上一批九輪及 T9 strict FAIL 原件不變、不重播。只讀審查確認：新 episode focus 已拒絕引號，舊關係 detector 卻把引號內 `覚えてる？` 當本輪請求，並讓上一輪短期記憶 anchor 蓋過外層「台詞自然嗎」問題。這輪唯一新變因是有界 quote/outer-act scope certificate，綁定 route／selected plan／anchor 准入／最後日文與 graph；原始候選池、top-5、profile 與舊模組不改。

八輪前瞻題與 conditional gold、strict gate 已在實作前以 `524e873` 推 PR #435；`research/p4_quoted_line_act_scope_preimplementation_freeze_2026-10-18.sha256` 2/2 OK。新 opt-in 模組／入口／controller 已寫、聚焦＋相鄰零模型 **35/35**，語法與 controller help 通過。只讀複審指出並已處理 selected-plan 晚期覆蓋、失敗收據、複合外層行動誤准入等風險；`research/p4_quoted_line_act_scope_product_freeze_2026-10-18.sha256` 現為首輪前 code／依賴／資料 SHA。**尚無新 Safari／模型生成，不能稱產品 PASS**。

**唯一下一步**：核 product SHA、diff review，精確提交本項並推 PR #435／核 head；再用全新 0700 隔離 root 做 0-turn readiness、私有官方 SHA ONNX 離線預熱、空 profile setup；依凍結八輪各一次／0 retry，在 T4 後 planned stop、同 DB 新 session 重啟。逐輪核 raw＝Safari 泡泡＝graph UTTERANCE、outer act/selected/final、延遲、profile digest 與八個 episode。任一 gate 不過整批 strict FAIL 並保存，不回放追分。T1 性能與先前 T3 引述指令時態另卡。正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 整合仍 pending；Goal 未完成。無關 `output/graduate_application_report/` 不碰。下面的「唯一下一步」均是歷史。

## 最新結果與唯一下一步：P4 顯性 episode 回憶焦點首發 strict FAIL

首輪前 `a82d4de28f2d72db8bec799d8e7e12106d7e6ef0` 已把 opt-in 實作、九輪新題、產品 SHA 與 10/10 聚焦＋45/45 相鄰零模型測試推 PR #435。隔離 root 真 Safari T1–T9 各一次／0 retry，T4 後 planned stop、同 DB／新 session 重啟；9/9 泡泡＝graph `UTTERANCE`＝raw，九個不同 episode，T0–T9 十份 full profile 0 rows／同 digest。T7 確實把 rank 8、一般 top-5 未選中的 T2 原話經專用 handoff 帶到最終「七時半」；T5 也正確，但原來源 rank 3，不當作 handoff 增益。T8 缺來源沒有捏造。完整逐輪、圖、成本、隔離與 raw SHA 見 `analysis/p4_explicit_episode_recall_focus_fresh_product_probe_result_2026-10-18.md`。服務最終 planned stop／PID 退出／7894 vacant；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 未碰。

**整批 strict FAIL，不重播改判**：T1 user wait 23.4546 秒 > 20 秒；T9 雖 focus=null，舊引述／關係 intent 及 generic memory anchor 卻把「台詞是否自然」錯答成上一輪駐輪場內容，不自然且離題；T3 另有「請確認」→「已確認」語義錯述。T5/T7 新 focus receipt、selected core、最終泡泡同源，但舊 `memory_anchor/post_check` 仍是 pre-focus 快照，不能宣稱圖所有節點一致。來源限定跨重啟回憶的狹義能力成立，非產品 PASS、同模型優勢、人類理解或正式研究結論。

**唯一下一個必要交付**：先就 T9 做只讀設計審查與新單變因工作卡，釐清引號內台詞是被討論的內容而非當前回憶／關係請求；凍結新的未曝光正負控、成功／失敗、允許檔案與成本後才實作。T1 cognition 延遲與 T3 第三者指令忠實度分開立項，不以同一修正批偷改。正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 整合仍 pending；Goal 未完成。下面的首發前「下一步」均屬歷史，不再執行。

## 當前執行：P4 顯性 episode 回憶焦點首發（T6 獨立工作項）

2026-10-18 接續：opt-in `uruha_explicit_episode_recall_focus_p4.py`、薄 Web 入口與隔離 controller 已實作；首輪前獨立只讀審查補上敏感來源阻擋、來源更正 fail-closed、handoff 原始 rank/top-k flag 與既有 direct episode passage 標記。聚焦 10/10、相鄰 45/45 零模型測試通過，語法與 controller help 通過。新入口已在專用 0700 root `uruha-product-d7ak5ika` 做 0-turn same-PID HTTP ready 與 planned stop；官方 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` ONNX 私有副本已離線封網預熱得 1×384 finite embedding，三個 DB/log 目錄仍空。這些都**不是**九輪產品通過。首輪前 code／依賴／資料 manifest 是 `research/p4_explicit_episode_recall_focus_product_freeze_2026-10-18.sha256`；下一步只提交本項並推 PR #435、核 head 後，做顯式空 profile setup 和 T0 收據，再依凍結九輪各一次／0 retry 做真 Safari 兩 session 同 DB 重啟。若 gate 失敗如實保留，不改舊題追分。無關 `output/graduate_application_report/` 不碰。

B 第二次失敗後只讀因果審查已於 `1e99d0f` 推 PR #435，B 保持 `REVIEW_REQUIRED`；不重跑其已曝光 T6。新單一能力變因是來源限定的顯性回憶契約，貫通 retrieved candidate→專用 handoff→selected plan→最終自然日文，並保留無證據／衝突時不猜。before、允許範圍、成功／失敗、成本和九輪新資料見 `research/p4_explicit_episode_recall_focus_plan_2026-10-18.md`；新資料及設計在首輪／實作前 SHA 固定於 `research/p4_explicit_episode_recall_focus_preimplementation_freeze_2026-10-18.sha256`。目前尚未新模型生成。正式 DB、原始 dirty checkout 和無關 `output/graduate_application_report/` 不碰。若 gate 不過保留 strict FAIL，不把單元、圖或 B 舊正例冒充產品通過。

## 最新結果：P4 reported-ack B 來源限定修正批 strict FAIL／`REVIEW_REQUIRED`

首輪前 `3ce45ec489ae3beb5b12174e07d1660a24bc120a` 已把 source-scoped B 修正、八句新題／條件式 gold、修訂與產品 SHA 推到 PR #435。隔離 root 真 Safari 兩 session、T4 後同 DB planned restart、每句一次／0 retry 已完成；原件 SHA `b08aaa9d85bb0bc68f28ed162d5eb63082c5c087ddf2ea5c0037abc59421f304`。完整逐題、圖、隔離、成本與歸因見 `analysis/p4_reported_ack_source_scoped_memory_fresh_product_probe_result_2026-10-18.md`。8/8 raw＝graph UTTERANCE＝當輪 Safari 泡泡、八個不同 episode、T0–T8 九份 profile 0 rows／同 digest；B 追加模型呼叫 0。服務 planned stop、7894 vacant，正式 DB 未動。前瞻 manifest 16/16 重驗 OK。

**整批未通過兩個獨立門檻**：T1 20.2395 秒，超出凍結 ≤20 秒；T5 跨重啟雖 A admitted／M31 deferred，post-planner 卻為 `ask_miss_me/affection_tease_soften`，actor selected ack 缺席，B 正確 fail-closed，最終為無關引文。只讀審查 `research/p4_reported_ack_source_scoped_postfailure_review_2026-10-18.md` 發現 `_normalize_plan` 對 casual 候選中的 `思い出` 會強制改此 intent；raw 未留原模型候選，不可斷言模型原 intent。T1/T3 的來源限定 B 正例可見，但跨重啟 T5 coverage 缺失，不能稱產品 PASS。T6 顯性回憶沒有答 T2「明日の教室番号」、T7 直接請求沒有執行，另屬非 B 路徑缺陷。T1 私有 ONNX 79.3 MB 在當輪下載而非先離線預熱，程序疏漏與耗時保留，不重跑改判。首發 B 失敗與本修正失敗都保留。

**唯一下一個必要交付**：B `REVIEW_REQUIRED` 只讀審查已保存；不得重送已曝光題、不放寬 B gate 追分。下一項選與 B 獨立、對核心目標必要的跨重啟顯性記憶焦點 T6，先定 before、前瞻資料與成功／失敗條件再實作。T7 行動忠實度與冷啟動成本分卡。正式同模型比較、人評、temporal holdout、VRM／Function Calling 整合仍 pending；Goal 未完成。無關 `output/graduate_application_report/` 保留。下面歷史「下一步／尚須 Safari」均不是當前命令。

## 當前執行：P4 reported-ack B 首發失敗後的單變因審查

B opt-in 表面實現、八句新資料與條件式 gold 已在首輪前以 `f02cf95113391e6b8512d6ee23fb0e4203060161` 凍結並推 PR #435；160/160 聚焦及相鄰契約通過。真 Safari 兩 session／同 DB planned restart、八題各一次、0 retry 已完成；原件 SHA `020de8e7a6b526e03b15f4f0a1a28bbaa2efc9bf6037786692ad86907e817c7e`。完整結果及邊界見 `analysis/p4_reported_ack_selected_visible_fresh_product_probe_result_2026-10-18.md`。T1 最終 reported-ack 成功，但重啟後 T5 雖 A admitted／M31 deferred／selected 正確，B 因自動背景 episode 的 `memory_anchor` 擋下，最終泛答，正例只有 **1/2**，整批 strict FAIL。protected 2/2 與其他負控制 4/4 沒被 B 誤接管；8/8 raw＝graph UTTERANCE＝Safari 泡泡，8/8 ≤20 秒，八不同 episode，T0–T8 profile 0 rows／同 digest。服務已 planned stop、7894 vacant。T2 source fidelity、T6 identity 與 T3 frame shadow 警告保留，不能稱全產品 PASS。

**只讀設計審查已完成**：`research/p4_reported_ack_selected_visible_postfailure_review_2026-10-18.md` 定位 T5 是泛用背景 episode anchor 被 B 當成答案權限；只刪 `memory_anchor` gate 不安全，因先前記憶可能已提供確認對象，而現 B 句會錯說「尚不知道」。沒有把 T5 改判或重播。

**下一個必要交付（新批首輪前，尚未生成）**：`research/p4_reported_ack_source_scoped_memory_correction_plan_2026-10-18.md` 將 B 的唯一主張來源限於本輪引文，背景不當答案權限。新八題／gold 已於 `ca0fb5b` 凍結；靜態 source certificate 4/4 正候選、4/4 非候選，最後逐字碰撞 0。首輪前只讀審查發現同 session 背景來自 `short_term`，修訂見 `research/p4_reported_ack_source_scoped_memory_preflight_amendment_2026-10-18.md`，原 dataset/gold SHA 未改。B opt-in 只改候選主張來源與被動 episode/short_term gate；聚焦＋A/actor 相鄰 **103/103**、P4-T/V/W **16/16** 零模型通過，沒有送新題。最終 code/依賴 SHA 在 `research/p4_reported_ack_source_scoped_memory_product_freeze_2026-10-18.sha256`；尚須核 SHA、diff/commit/push/PR head 後才可新 0700 root Safari 八輪一次性驗收。失敗即 B `REVIEW_REQUIRED`，不重播舊題；T2、T3、T6 各屬不同問題，不合包。正式同模型強 LLM、人評、temporal holdout、VRM／Function Calling 整合 pending，Goal 未完成；無關 `output/graduate_application_report/` 保留。

## 最新結果與唯一下一步：A 有限准入 PASS，reported-ack 產品 FAIL

`618c628fef40ac01eac2b272ec48e11e1c3b2f04` 首輪前已把唯一 seed-provenance 修正批的 code／新八句／條件式 gold／計畫／manifest 推到 PR #435。全新 0700 隔離 root 真 Safari 兩 session、T4 後同 DB planned restart、每題一次／0 retry 已完成，原件 SHA `9580fd65f4fd4094ae733e9bdcd12fbefba1190e7723c5b009f956cadcd74236`；完整逐題與界線見 `analysis/p4_reported_ack_route_admission_seed_provenance_fresh_product_probe_result_2026-10-18.md`。普通 no-rule 空 seed 正例 T1/T5 **2/2 admitted、原 M31 0**；protected low-road T2/T7 **2/2 rejected、原 M31 1**；四個負控制無錯 defer。8/8 等待 ≤20 秒（平均 10.7661、最大 19.8950 秒），8/8 raw＝graph UTTERANCE＝當輪目視 Safari 泡泡，八 episode；T0–T8 九份完整 profile 收據同 digest／0 rows。服務 planned stop、兩 PID exited、port 7894 vacant。這只讓 **A 有限路由子門檻通過**，不是產品完成。

**整體 reported-ack 產品仍 FAIL**：T1/T5 selected `ack_reported_check_instruction_p4` 的正確 core 被後段改成 generic，T5 更把本輪 generic fallback 錯包成引文，最終使用者看不到可信的第三者指令承接；T6 的「是否說過號碼」記憶問答錯位且冒號不自然；T7 可見句也不相稱。正式同模型強 LLM、人評、temporal holdout、完整 VRM／Function Calling 仍 pending，Goal 未完成。首發 A 0/2 正例的 strict FAIL 與原件不改算。

**B 只讀定位已完成**：`research/p4_reported_ack_selected_to_visible_design_review_2026-10-18.md` 保存 T1/T5 從 selected core → 通用 speech tail 的 `？。` → 日文 guard 泛答；T5 又被 P4-W 錯包成引文的因果證據及尚未驗證的單變因方案。同團隊審查非獨立，尚未改 B code、凍結 B 新題或取得 B 產品 PASS。

**唯一下一個必要交付**：依 B 審查先定精確 task card、未曝光的普通／保護／混合／未知負控制、條件式 gold 與成本上限，首輪前凍結；再做新 opt-in 表面實現、相稱回歸與隔離 Safari 驗收。A 的 T1/T5 只作 before，不回放追分；T6 記憶和 C 性能另卡，不合包。不碰原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/`。下面 A 首發與修正批的歷史「尚須／下一步」不再是當前命令。

## 歷史：P4 reported-ack 的 M31 路由准入 A（首發與修正前狀態）

**2026-10-18 首發產品批已完成並 strict FAIL／REVIEW_REQUIRED**；下面本節原來的「尚須 commit／Safari」是首輪前歷史，不能再當下一步。`c1ee0ec` 首輪前已凍結、推 PR #435；真 Safari 兩 session／八題一次性、T4 後同 DB planned restart、0 retry 已完成，原件 SHA `1e59785995586f5ea9247a577433d1436fbf6fdd3603eb74dfbaf0b5806d56d7`，完整逐題／圖／成本／隔離見 `analysis/p4_reported_ack_route_admission_fresh_product_probe_result_2026-10-18.md`。來源完整的普通 high-road T1/T5 **0/2 准入**，因規則 seed 在無命中時變 `{}`，A 卻要求 seed 明寫 `chat/casual`；受保護 low-road T2/T7 **2/2 拒絕**，四個負控制無錯 defer。user wait 7/8 ≤20 秒，T1 22.3399 秒；T6 記憶題另有焦點錯和不自然冒號。八個泡泡＝圖 UTTERANCE＝raw；八個 episode、T0–T8 full profile digest 不變／0 rows。服務終停、port vacant，正式資料未動。

**唯一下一個必要交付**：保存首發失敗原件，完成下方已設計、已實作的唯一 A 修正批首輪前 Git 凍結，接著全新隔離 Safari 一次性驗收。若仍失敗，維持 `REVIEW_REQUIRED` 等設計審查，不反覆加規則或重播已曝光句。B 可見忠實度、T6 記憶與 C 延遲另卡；正式同模型 LLM、真人、temporal holdout、VRM／Function Calling pending，Goal 未完成。原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

**修正批首輪前進度**：`research/p4_reported_ack_route_admission_seed_provenance_correction_plan_2026-10-18.md` 已定案；只新增 no-rule seed 來源標記並更正 A 准入，不改後段 B。新八題與條件式 gold 在 `datasets/p4_reported_ack_route_admission_seed_provenance_fresh_probe_2026-10-18.json`，八題逐字與前三批重疊 0；靜態 source certificate T1/T2/T5/T7 true，普通無規則 seed T1/T5、protected seed T2/T7。聚焦最後版 36/36、較廣相鄰 177/177（9 既有 warnings）；新 SHA manifest 全 OK。**尚須本批 diff／commit／push／PR head 核對，未送任何新 Safari 題**；之後按計畫跑一次隔離真輪，失敗照留。

### 本項首輪前紀錄（歷史，非下一步）

上兩批失敗及 `REVIEW_REQUIRED` 原封保留。before、單一變因、允許檔案、
失敗分支、≤20 秒成本與新八題／條件式 gold 已事先寫在
`research/p4_reported_ack_route_admission_plan_2026-10-18.md`、
`datasets/p4_reported_ack_route_admission_fresh_probe_2026-10-18.json`。
本項只讓主要 M31 呼叫顯式接收已計算的 seed／route／M22；欠缺或保護
上下文時回原 M31，不能把 A 子門檻當可見 reported-ack 產品 PASS。
最小 opt-in hook／入口已寫；聚焦＋相鄰零模型 **105/105**，controller
`--help` 與語法通過；真安裝鏈靜態 certificate 8/8 符合事前欄位，
新舊題逐字交集 0，舊 SHA 全 OK。新前瞻 SHA manifest 已建立，
**尚須 commit/push、核 PR head，首輪前不可送 Safari**。之後全新隔離
Safari 兩 session、同 DB restart 的八輪首發驗收、失敗與成本分析、
Git review。舊八題與
無關 `output/graduate_application_report/` 不碰。

## 最新結果與唯一下一步：reported-ack／M31 優先序八輪 Safari strict FAIL

首輪前 `1ad129c` 已把單變因 opt-in、新八句與 gold、程序和 SHA manifest
推到 PR #435。全新隔離 root 的真 Safari 兩 session、同 DB planned restart
已按凍結題各送一次、0 retry；8/8 泡泡當輪目視＝graph UTTERANCE、
8/8 raw reply＝blackboard utterance，八個持久 episode；12 份完整 profile
收據都 present／0 rows／同 digest。8/8 user wait ≤20 秒（平均 8.5395、
最大 18.8440 秒）。raw SHA 與逐輪、圖、隔離、成本、限制見
`analysis/p4_reported_ack_m31_priority_fresh_product_probe_result_2026-10-18.md`。
服務已 planned stop、PID exited、port 7894 vacant；原件與兩個 Safari
測試分頁保留。這些程序門檻通過不等於產品門檻通過。

**整批 strict FAIL／`REVIEW_REQUIRED`**：T2/T6 第三方引述均證明
M31 被 deferred，卻都沒有最終可見的 reported-ack（0/2）。T2 selected
action 正確，後段附加標點與語言 guard generic fallback 洗掉承接；T6
進入 `safety_sensitive`／M21 protected low-road 而 selected `plain_reply`，
早期 M31 certificate 卻在未知 protected seed 時略過 M31；兩者都不能以
「source 辨識正確」或 graph selected 正確稱成功。T8 unknown 負控制
最終 `確認ありがとう`，未真正釐清；T1/T3/T4/T5/T7 可見路由合格。
零模型聚焦與相鄰回歸 87/87 只證契約；本批無可信全 runtime token 數。
已是同一 reported-action 問題第二個有根據前瞻批次，不重播曝露句、
不補第三批詞彙例外追分，也不把舊失敗抹除。

同團隊、非獨立的只讀設計審查已記在
`research/p4_reported_ack_postfailure_design_review_2026-10-18.md`：
(A) M31 defer 准入須看已有的 protected seed／route／M22，
(B) selected ack 到 guard 後最終自然日文的忠實度，
(C) unknown 確認對象與串行延遲，均為不同單變因。A 先於 B，因目前
T6 已錯略過 protected 路由；只修 A 不會自動讓 T6 可見承接成功。

**唯一下一個必要交付**：依審查建立 A 的新任務卡／精確設計，先凍結
未曝光的正負控制、成本上限與各層判準，再做最小實作和相稱驗收；
不得用本批 T2/T6/T8 重新計 pass，亦不得把 A 的准入子門檻冒充
reported-ack 產品 PASS。B 待 A 的保護邊界穩定後另立單變因卡；
C 不合包。正式同模型強 LLM
比較、真人評價、temporal holdout、完整 VRM／Function Calling 仍
pending；Goal 未完成。原始 dirty checkout、正式 DB 與無關
`output/graduate_application_report/` 不碰。

## 歷史：reported-ack／M31 優先序 opt-in 首輪前狀態

前批 actor/scope 八輪 strict FAIL 與 raw/gold/凍結 SHA 不變；T3 的確是
`actor=third_party` 仍遭 M31 literal-topic 表面權限蓋掉，不是辨識來源失敗。
單變因設計見 `research/p4_reported_ack_m31_priority_design_2026-10-18.md`：
只在完整日文單句第三者引述、既有 M25/P4-AT actor proof、M29 當輪 digest
全一致時，新 opt-in `uruha_reported_ack_m31_priority_p4.py` 讓 M31 回
非權威 deferred contract，再由既有 actor wrapper 選 reported-ack；
一般字面句、混合直接請求、自述、unknown、保護 cue 仍走舊路。
入口時未有 selected plan，最終仍必須核 graph selected/final，不能單靠
certificate 宣稱成功。獨立 T7 串行延遲不合包。

零模型聚焦及相鄰 M25/M29/M31/M32/M33/P4-AT/source 回歸 **87/87**
（9 個既有 warning）；真 opt-in 安裝鏈零模型檢查及 controller `--help`
通過。全新八句作者自編題／逐輪 gold 和 2-session、同 DB restart、
0 retry、20 秒嚴格程序見 `datasets/p4_reported_ack_m31_priority_fresh_probe_2026-10-18.json`
及 `research/p4_reported_ack_m31_priority_fresh_probe_plan_2026-10-18.md`；
8/8 靜態路由核對通過、無舊題或 fixture 逐字重複。新 SHA manifest
`research/p4_reported_ack_m31_priority_fresh_probe_freeze_2026-10-18.sha256`
待末次 diff/manifest 核對及 commit/push PR #435 head 後才算首輪前凍結。
**尚未送新題 Safari，不得報產品 PASS。**

**唯一下一步**：manifest/diff 核對、只提交本項檔案、push 核 PR head；
再全新 0700 隔離 root 做 exact 入口 0-turn readiness、planned stop、
私有 ONNX 預熱、顯式空 profile setup，最後按凍結八句真 Safari 各一次並
逐輪核 selected／M31/M32/M33／泡泡／node graph／profile digest／episode／
成本。失敗保留，第二次有理由前瞻仍失敗則 `REVIEW_REQUIRED` 不再追分。
正式同模型比較、真人評價、temporal holdout、完整 VRM/Function Calling
仍 pending；Goal 未完成。無關 `output/graduate_application_report/` 不碰。

## 最新結果與唯一下一步：actor/scope 八輪 Safari strict FAIL

首輪前 `e156459` 已凍結、推到 PR #435 的 opt-in actor/scope、新八句/gold/
程序與 SHA 不變。2026-10-17～18 用全新 0700 隔離 root 做真 Safari 8/8
各送一次、0 retry；T4 後同 DB planned stop/restart，新舊各四輪、兩個 session、
最終八個不同 episode。八輪 actor/action/source、M25/M18、graph actor 在 M25
前都符合事前 gold；八個當輪目視泡泡＝graph UTTERANCE，raw 可重算
reply＝utterance 8/8。所有 T0／逐輪／停機／重啟的 full profile 內容 digest
相同、0 rows；正式 DB 與原始 dirty checkout 未動。

**整批 strict FAIL**：T3 第三者引述雖不再誤觸 `calibrate_need`，但下游 M31
把原定 reported-ack action 覆蓋為 `semantically_authorized_literal_topic_m31`，
最終只說「先輩が先に確認してと言った」；新 graph 稽核如實標
`reported_instruction_ack_missing`。T7 unknown 未誤選助手回覆形式，卻因
M21 full planner 9.5932 秒接 M31 semantic call 10.7653 秒，使用者等
23.4192 秒，超過預註冊 20 秒。其餘 7/8 輪達 latency 目標。M21 一般
planner 完成 4 次，M31 semantic 完成 2 次；本 raw 沒有可信實際 token
數，不可報零 token。raw SHA、逐輪表、啟停與證據邊界見
`analysis/p4_temporal_actor_scope_fresh_product_probe_result_2026-10-18.md`。
服務已終停／PID 退出／port vacant，原件與 Safari 分頁保留；本八題不改
gold、不重播、不作正式 holdout 或同模型優勢主張。

**唯一下一個必要交付**：先只讀設計審查 T3 的 M31 final action
arbitration，確認最小 source-qualified reported-ack 保留點與正／負控制；
再另立新前瞻版、全新未曝光題與首輪前凍結，做相稱聚焦／相鄰回歸、隔離
Safari 真輪與成本驗收。T7 的串行 latency 另列獨立性能變因，不與本項
合包。正式同模型比較、人評、temporal holdout、完整 VRM／Function Calling
仍 pending；Goal 遠未完成。無關 `output/graduate_application_report/` 不碰。

## 最新進度與唯一下一步：actor/scope opt-in 已實作，前瞻 Safari 尚未執行

依前批七輪 T3 的**既有失敗**所做的單變因設計見
`research/p4_temporal_actor_scope_design_review_2026-10-17.md`；原 raw SHA
`77b0a8cc138b73176a4a1f47369442b5407d10ca88511da6f41d15d7552016b8`
和 strict FAIL 均不變。新 `uruha_temporal_actor_scope_p4.py` 只在 opt-in 入口
啟用，共用可追溯的當輪 actor/source/action/time 證據：使用者自行先查後回覆不
再由同形字面升為助手先問；直接要求助手問回覆形式仍可通過；第三者引述、
明示第三者主詞／受詞、否定、同輪其他任務與不明歸屬 fail closed。
self-defer 與第三者報告各有相稱、非捏造的日文承接，graph 的最終稽核
綁 selected action/core 與可見句；不把心理推測寫成長期事實。

與前瞻句不同的零模型開發 fixture 最後版 21/21；最後版相鄰 M25/P4-AT/
source 回歸 40/40（8 upstream warnings），較早但非最後版廣回歸 68/68；
三個新 Python 檔與測試 compile、controller `--help`、舊 10/10 freeze SHA、
diff check 均通過。新八句/gold 與程序已事前寫在
`datasets/p4_temporal_actor_scope_fresh_probe_2026-10-17.json`、
`research/p4_temporal_actor_scope_fresh_probe_plan_2026-10-17.md`；
8/8 僅做靜態路由／gold 核對，**尚未送真 Safari**，不是產品 PASS 或正式
holdout。前批五輪 T3 的未知偏好句尾自然度仍是獨立風險。

**唯一下一個必要交付**：diff review、新 SHA manifest、commit/push 核 PR #435
head，才在新的 0700 隔離 root 做 0-turn readiness、私有 ONNX 離線預熱、
顯式空 profile setup、兩 session／同 DB restart 的八輪真 Safari 各一次；
逐輪核泡泡、graph、P4-AT/M18/selected、episode、完整 profile digest、
自然日文、來源與成本。任何失敗保留原件，不重播已曝光的舊 T3 或更換新題
追分。正式同模型比較、人評、temporal holdout、完整 VRM/Function Calling
仍 pending；Goal 未完成。

## 最新結果與唯一下一步：hash-prefix 事件傳遞五輪 Safari 局部成功、整批 strict FAIL

首輪前 `ca2621b` 凍結並推 PR #435 的**新**五句，已在全新隔離 root
真 Safari 當輪目視各送一次、0 retry；T3 後同 DB planned stop/restart，兩個
session、五個持久 episode、5/5 當輪目視泡泡＝graph UTTERANCE，
5/5 M19 等待 2.6243–3.0800 秒。T1/T4 reported-offer 最終
selected core、來源 proof 與 hash-prefix 稽核一致；`まあ、`／`いや、`
各一筆無來源固定開頭被移除，事件 selected/legacy/returned SHA 與
最終句可重算，**有限事件傳遞子門檻通過**。T2/T5 直接邀約稽核通過，
T3 未憑問句捏造後輩偏好；顯式空 profile setup receipt 與後續九份
status/count/全內容 digest 相同。聚焦＋相鄰 46/46、10/10 freeze SHA
保留；前批七輪 strict FAIL 亦保留。

但 T3 最終句尾「そのくらいでいいだろ。」在未知偏好問題後顯得敷衍，
本團隊非獨立的質性審核不能將事前「自然日文」必要 gate 報為通過；
**整批 strict FAIL／REVIEW_REQUIRED**，不可再用第三批改題追分。
另無 Safari 操作錄影，泡泡／0 retry 是當輪目視，不能由 raw 獨立重算。
完整逐字、graph、profile/episode、SHA、成本與證據界線見
`analysis/p4_hash_prefix_event_transport_fresh_product_probe_result_2026-10-17.md`。
服務已停、三個 PID exited／port vacant，原件與 Safari 分頁保留。
五輪都是 deterministic route、M21 一般模型呼叫嘗試 0/5；raw 無生成
token 計量欄位。這不是 fresh generation、同模型優勢、人評、正式
temporal holdout 或整體 P4 PASS。

**唯一下一個必要交付**：另立單變因只讀設計審查，依前批已保存的 T3
最小反例，釐清「使用者自行先查行程」與「要求助手先問」的 actor/scope
准入、負控制、可見 graph 與全新未曝光驗收；先審查，不在本批已曝光
五句／七句追加例外。未知問句尾句自然度列獨立表達風險，不能和
actor/scope 修正合包。正式同模型公平比較、人評、temporal holdout、
完整 VRM／Function Calling 仍 pending，Goal 未完成。原始 dirty
checkout、正式 DB、無關 `output/graduate_application_report/` 不碰。

## 歷史：P4 最終開頭來源准入與完整 profile 證據（首輪前狀態）

以下是七輪首輪前的工作紀錄；當時的「尚未／下一步」不覆蓋上方結果。

上一批六輪的 strict FAIL 完全保留（下一節），未重播曝露題。已用只讀 before 證明 T1 的 `先に、` 出自最終函式的八選一字元 hash，而非 selected plan；舊 source audit 又把它當成普遍可接受前綴。單變因設計見 `research/p4_hash_prefix_provenance_gate_design_2026-10-17.md`：新 opt-in 產品入口只撤回「hash 在完整候選前純新增固定開頭」的操作；上游候選本身已有連接詞則保留。新 graph audit 獨立要求 reported-offer 的 final 為 exact selected core，並連帶核舊 admission proof；不能只憑舊 `visible_report_preserved` 稱成功。這不是 T2/T5 語氣或甜食文法的修正。

上批還欠完整 profile collection 內容 hash；新獨立 `p4_profile_full_content_snapshot.py` 讀取隔離 `user_profile` 所有 subject 的 ID／metadata／documents／embeddings，僅落狀態、筆數與 digest，不把內容寫進收據。開啟 Chroma 前遞迴拒絕隔離 DB 樹內的 symlink／hardlink／特殊檔；仍受單機同帳號 TOCTOU 限制，不能回補上批缺證。新工具只是下一批的驗收儀器，不作第二個產品因果變因。

七句新開發者前瞻資料與 gold 見 `datasets/p4_hash_prefix_provenance_fresh_probe_2026-10-17.json`，程序與嚴格判準見同名前綴 `research/*_plan_2026-10-17.md`。舊 8/8 manifest hash 已核不變；最後版本的零模型聚焦 12/12、相鄰 36/36（8 warnings），六個新 Python 檔 compile 通過，10/10 新 freeze SHA 相符；尚未首輪前 commit／送 Safari，不得稱真產品 PASS。首輪前需完成 diff review、commit/push/PR head；之後新隔離 root 的 0-turn readiness、真 Safari 七輪一次性、T3 後 planned same-DB restart、逐輪完整 profile digest／episode／graph／泡泡／成本。失敗保留，不改新 gold 追分。正式同模型比較、人評、temporal holdout、VRM／Function Calling 完整交付仍 pending。

## 最新結果與下一個必要交付：reported-offer 來源作用域 Safari strict FAIL

2026-10-17 首輪前 `00e3016` 凍結的**全新**六輪已在隔離真 Safari
逐字各跑一次、0 retry；T3 後同 DB planned stop/restart。來源分流
3/3、直接邀請控制 2/2、第三者偏好未知控制 1/1；六個泡泡與 graph
utterance 相符，六筆持久 episode，`subject=user` profile 快照 rows
全程空（全 profile documents 的事前內容 hash 未驗成），M19 六輪
2.7057–3.0062 秒。但 T1 最終 `先に、同僚に…` 的無來源固定開頭
不自然／可暗示時間先後，新 scope audit 卻允許該前綴並報成功。
故**整批產品 strict FAIL**，不能以有界機制 6/6 稱產品 PASS。
T2 `いや` 接接受、T5 硬結尾另列自然度警訊。原 raw、快照、前後
SHA、完整逐輪與限制見
`analysis/p4_reported_offer_source_scope_fresh_product_probe_result_2026-10-17.md`。
服務已 planned stop／PID exited／port vacant；隔離 root 原件與 Safari
分頁保留。舊批 strict FAIL 不改，本六題/gold/freeze 不改不重播。

**唯一下一個必要交付**：對 `_finalize_surface_reply` 的固定開頭
准入及 scope audit 容許範圍先做只讀、單變因設計審查；凍結真正需要
時間轉承的正例、引述／直接邀請／未知的負控制與新未曝光 gold，
並在下一批首輪前補足全 profile 內容 hash 的獨立快照證據 gate，
再決定有界修正及一次真 Safari 前瞻。不要與上批 sweet-core audit
或 T2/T5 的人格語氣風險合包追分。正式同模型比較、人評、
temporal holdout、VRM／Function Calling 完整交付仍 pending；Goal
遠未完成。

## 歷史：reported-offer 來源作用域首輪前實作與凍結

針對下方 selected-offer 第二批 T2「使用者引述朋友提議」被誤當直接向 Uruha
邀約的保留失敗，另立**新**有限來源作用域項，而非修改或重播舊題。只在完整
「第三者角色＋配對引文內食物一口問句＋報告動詞」單句、且舊規則真的選中
casual food-offer action 時，改為 `chat/plain_reply`；最後日文承接使用者收到
邀約，不讓角色直接接受一口。新 `grounding` 攜帶可重算 admission proof，
最終 graph 以來源、舊 seed、selected plan、utterance 逐項核對；缺失或竄改
proof fail closed。其他輸入保留舊路；不寫第三者偏好事實。設計與邊界見
`research/p4_reported_offer_source_scope_design_2026-10-17.md`。

聚焦 5/5、相鄰 127/127，四個新 Python 檔 compile 通過；舊 8/8 凍結 SHA
未變。新 controller 首次 0-turn CLI 因 wrapper main 轉接錯誤失敗，已只修新
controller 並補執行 CLI 的測試；第二次新隔離 root 已同 PID `52651` 通過
唯一 localhost listener／HTTP 200，planned stop 確認 PID exited／port vacant。
官方 SHA 相符的 83,178,821-byte ONNX archive 以獨立私有副本預熱，封鎖下載
仍得到 1×384 finite embedding；memory/session/log 仍空。這些全是首輪前
工程證據，**不是**新 Safari PASS。新六輪逐字/gold 與程序見
`datasets/p4_reported_offer_source_scope_fresh_probe_2026-10-17.json`、
`research/p4_reported_offer_source_scope_fresh_probe_plan_2026-10-17.md`，
作者新題、非獨立 holdout；尚未送 Safari／模型，不得用於修程式。

**唯一下一個必要交付**：diff review，產生新 SHA manifest，commit/push 並
核 PR #435 head 作首輪前凍結；然後在上述已停機預熱 root 上以新 controller
啟動，真 Safari 按事前 gold 六輪一次性驗收（T3 後 same-DB restart，0 retry，
逐輪 ≤20 秒、profile 全內容 hash／episode／graph utterance 對泡泡）。任何
失敗保留原始結果，不修改舊 selected-offer FAIL 或新已曝光題。正式同模型
比較、人評、temporal holdout、完整 VRM／Function Calling 仍 pending。

## 最新結果與唯一下一步：selected food-offer action 第二批 Safari strict FAIL

2026-10-17 已在首輪前 `4873ead` 凍結的全新六輪與預熱過的**新**隔離 root
完成真 Safari 一次性產品批次，T3 後同 DB planned restart，6/6 泡泡＝
graph utterance、六個持久 episode、profile row-ID delta 全 0、六輪 M19 等待
均 <20 秒。但 T2 把朋友引述誤選為向 Uruha 的直接食物邀請，最終回覆
直接接受；T3 雖正面接住蘋果派，事前要求的 selected-offer verify 節點
缺席（selected core 的 `甘いのならあり` 未進有限稽核文法）。四正例只有
3/4 有新 audit `visible_action_preserved`，引述負控制語義 FAIL。**整批
strict FAIL／REVIEW_REQUIRED**；離線 ONNX 預檢與成功啟停不抹掉第一批
T1 首載 timeout FAIL。原始 SHA、逐輪、重啟、成本與根因見
`analysis/p4_selected_offer_action_surface_offline_ready_fresh_product_probe_result_2026-10-17.md`。
服務已 planned stop、兩個 PID 退出與 port vacant；root/raw 留存、Safari
分頁未任意關。原 gold／raw 不改、不重播，不再做同卡第三批追分。

**唯一下一個必要交付**：已完成同團隊非獨立、未改程式的單變因審查，
細節見 `research/p4_reported_offer_source_scope_design_2026-10-17.md`。
現在依該設計建立**新** product scope module／新入口／新 controller 和
聚焦測試，先驗「使用者報告第三者邀請」不能被 selected 為直接向
Uruha 邀請，且引文後的新直接邀請不得一律被擋；保護舊凍結 8/8 SHA。
相鄰回歸、0-turn 隔離入口與全新資料/gold/SHA 首輪前凍結後，才做
一次真 Safari 前瞻；成功／失敗照設計判定。T3 sweet-core 稽核文法
覆蓋另列後續儀器項，**不得**與來源作用域修正合包。正式同模型比較、
人評、temporal holdout、VRM／Function Calling 完整交付仍 pending。

## 歷史：P4 selected 食物邀請行動到最終日文的表面忠實度實作

以下保留首輪前任務卡與當時的下一步作時間紀錄；不得覆蓋上方最新結果。

2026-10-17 已完成同團隊非獨立的只讀設計審查，具體 before、候選機制、
source/selected 準入、單一變因、禁止檔案、負控制、資源上限與精確首層命令
見 `research/p4_selected_offer_action_surface_fidelity_design_2026-10-17.md`。
T2 的 `dynamic_anchor.variants[0]` 逐字等於最終主句，model blend disabled；
self-monitor 曾報 grounding miss 卻修後不變，M39 與舊 selected-action node 均
未涵蓋此次承諾。設計不改全域 semantic groups，因其會影響模型准入與成本；
只做有界產品 post-refine 合格候選回退，及真正最終日文的獨立 graph 稽核。
此設計已做產品限定實作；最終原句只由既有自然候選／selected core
有界回退，不改全域模型候選門檻。第一次 reviewer 找出的否定、錯物品、
不安全修飾語與 selected core 自身矛盾，第二次 reviewer 找出的第三人稱／
後句反轉假陽性，都已在首輪新題前 fail closed。零模型聚焦 7/7，
未改 overlay 的相鄰回歸 73/73（8 warnings），compile 過。隔離產品入口
0-turn 啟動有短暫 ready race，**同一次 run** 終核同 PID 單一 loopback
HTTP 200；planned stop 原 PID 退出、port vacant。這不是 Safari PASS。
全新六句與 gold 已寫入 `datasets/p4_selected_offer_action_surface_fresh_probe_2026-10-17.json`，
逐輪程序見 `research/p4_selected_offer_action_surface_fresh_probe_plan_2026-10-17.md`；
凍結時尚未送 Safari；首次送題後的 abort 狀態如下。原六輪與首次歷史
0-turn abort 仍 FAIL，不重播曝露題、不可把本項與 T1/T4 裝飾語法修正合包。

首輪前 code/gold/SHA 已由 `f622cdc` 推到 PR #435，8/8 新與 21/21 舊
manifest OK。但全新 root 的真 Safari T1 `胡椒ポテト、一口いる？` 超過
20 秒後 UI 顯示錯誤、沒有 final reply；stderr 指向隔離 HOME 中 Chroma
ONNX 首次下載 `httpx.ReadTimeout`（錯誤時曾觀察 30,412,800-byte 部分
archive；同 root 稍後完成官方 SHA 下載，不抹掉 T1 timeout）。
T0/T1 隔離 profile／episode 皆空，服務 planned stop、PID 退出／port 空；
T2–T6 未送。**整批 strict FAIL，且沒有語義結果**，不可重播這六句。
詳細 raw SHA、來源與歸因界線見
`analysis/p4_selected_offer_action_surface_fresh_product_probe_abort_2026-10-17.md`。

**下一個必要交付**：先讓**全新**隔離 0-turn root 以本機既有、SHA
符合 Chroma 官方常數的 ONNX 資產離線準備並驗證 embedding readiness，
不得修改正式 DB、凍結首批題或重播 T1；明列預熱成本。成功後另凍結
全新逐字題／gold／manifest、再做一次真 Safari 前瞻批次（仍受至多兩個
有根據修正批次上限）。若 readiness 仍失敗，保存程序 FAIL；不得用
零模型或啟動 HTTP 200 當產品 PASS。正式同模型比較、人評、temporal
holdout、VRM／Function Calling 完整交付仍 pending，Goal 遠未完成。

續作 2026-10-17：上述**新** 0700 隔離 0-turn root `uruha-product-wy07nein`
已同 PID `24249` 核單一 loopback HTTP 200、planned stop 原 PID exited／
port vacant；當時 memory/session/log 三目錄均空。本機已有的 Chroma ONNX
archive 83,178,821 bytes、官方 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`
以不同 inode／link count 1 的獨立私有副本供此 root；同 venv、同 sandbox、
封鎖網路下載的 fresh Python embedding 預檢得 1×384 finite vector，
0.405 秒，六模型檔齊，事後三個 DB/log 目錄仍空。這是**設施預檢**，
不是產品或語義 PASS。第二批全新六句/gold 已事前寫入
`datasets/p4_selected_offer_action_surface_offline_ready_fresh_probe_2026-10-17.json`，
程序與成本見同名前綴的 `research/*_plan_2026-10-17.md`；尚未送題。

**現在下一個必要交付**：完成第二批 dataset/plan/程式 SHA manifest、
diff 與 PR head 的首輪前凍結；在該已預熱且停機的 root 上按事前程序
真 Safari 六輪並於 T3 後 planned same-DB restart。保留第一批 T1 timeout
strict FAIL，不重播原六題；若第二批失敗，保留反例轉 `REVIEW_REQUIRED`，
不做第三批加規則追分。正式研究與產品其餘 gate 仍 pending。

2026-10-17 第二個全新隔離 root 已完成事前凍結的六輪 Safari（第一
root 的 0-turn 啟動 abort 獨立保留，不併入成功批次）。五個第三者真問句
5/5 selected 新 unknown gate，跨 planned same-DB restart 的 T4 同題仍不把
先前問句當偏好事實；profile row-ID delta `[0,0,0,0,0,0]`、六個
持久 turn episode、六個 graph UTTERANCE 與 Safari 泡泡逐字對齊，
6/6 等待 ≤20 秒。但 T1/T4 人格表面新增未在有限語法內的 `一回、`，
圖節點 2/5 `selected_or_visible_mismatch`；T2 food offer selected core
原為接受一口，最終卻沒有回答邀請。故**此六輪 strict FAIL**，不是
普遍理解或產品交付 PASS。原始 SHA、逐輪與兩次 stop/restart 程序在
`analysis/p4_third_party_question_evidence_fresh_product_probe_result_2026-10-17.md`。
服務已 planned stop，root/raw 保留；Safari tabs 不任意關。原六題、
gold、freeze、code 不改、不重播；本問句 gate 開發期兩批修訂後已曝光，
同卡標 `REVIEW_REQUIRED`，不做第三批加例外追分。第一次 0-turn abort
仍列產品穩定性失敗，見同項 preflight report。

**下一個必要交付**：先以 T2 為只讀 before 做獨立單變因設計審查：
`food_offer_generic`／`named_offer_accept` 已被 selected，為何 final
surface 成為泛泛的「その話なら普通に分かる」；明列哪些 selected action
在何種來源／安全邊界下必須交付，負控制、人格自然度、可見 graph
誠實稽核、成本與全新未曝光驗收。先審查而非立即改最終字串；不得
把 T1/T4 的圖表裝飾語法、原問句 gate 或 T2 修正合成一個因果變因。
正式同模型比較、人評、temporal holdout、VRM／Function Calling
完整交付仍 pending，Goal 遠未完成。正式 DB、原始 dirty checkout、
無關 `output/graduate_application_report/` 不碰。

## 已執行：P4 第三者偏好真問句的首輪前凍結與新 Safari 產品驗收

以下保留首輪前狀態與當時下一步作歷史；六輪現已完成，結論以上方最新結果為準。

首輪前 freeze 已在 commit `19f9a03` 推送，PR #435 head 已核；21/21
manifest OK。但首次新隔離產品啟動在送任何題／Safari 之前，final
Python PID `11796` 曾 LISTEN 又退出；Gradio localhost HEAD 健康檢查
報不可用。此**0-turn 啟動批次程序 strict FAIL**，不算語義失敗或成功，
DB absent、profile/episode 皆零，原六題完全未曝光。詳見
`analysis/p4_third_party_question_evidence_preflight_abort_2026-10-17.md`。
下一次如另開全新隔離嘗試，不能合併洗掉此失敗；須先核原
21/21 manifest，取得同 PID／唯一 loopback／HTTP 200 ready 才送題，
仍使用已凍結未曝光的六題和原嚴格 gold，不得答案驅動換題或重試。
整體產品穩定性須把首次 abort 算入分母；不得為通過開公開 share link。

2026-10-17：設計 `dcd095c` 後已實作產品限定問句 gate，只在完整窄日文
第三者偏好問句、既有規則回傳 `None`、且 planner 已收到的可辨識
使用者來源沒有同 X/Y 非問句時給「目前證據不足」的 deterministic plan；
不宣稱搜尋全庫或知道第三者真實偏好。RightBrain 與 writer 不改。
開發期第一次零模型 4/5 的「先前相同問句誤作證據」失敗已保留；
首輪前唯讀稽核又找出 graph 可把 unknown＋後接相反命題誤報成功、
以及未跳脫 episode 欄位造成來源截斷，已在新 probe 曝光前有界修正。
修訂後零模型聚焦 6/6（含真兩輪重複問句、對抗表面與來源注入），
相鄰 31/31；較早 112/112 屬修訂前。隔離入口 0-turn 啟停通過，
那不是產品對話 PASS。逐字六輪／gold／20 秒／0 retry／T3 後一次
same-DB planned restart 與 21/21 SHA manifest 見
`datasets/p4_third_party_question_evidence_fresh_probe_2026-10-17.json`、
`research/p4_third_party_question_evidence_fresh_probe_plan_2026-10-17.md`、
`research/p4_third_party_question_evidence_fresh_probe_freeze_2026-10-17.sha256`。
五個不同字串在 repository 只見新 dataset；T4 事前預定重問 T1，
不是看過答案後 retry。**尚未送這六輪 Safari／模型，不得稱產品通過。**

**下一個必要交付**：先封存此 0-turn abort；另開全新 0700 隔離 root
與真 Safari 逐字
T1–T6 各一次，逐輪留 profile row-ID／episode-ID、raw、graph selected／
utterance／evidence 節點、Safari bubble 與等待／成本；T3 後真 stop、
同 DB restart。若 strict 任一 gate 失敗，保留反例、按設計停止規則
報 FAIL，不能重播曝光題追分。舊六輪 strict FAIL 不改。正式同模型
比較、人評、temporal holdout、VRM／Function Calling 完整產品仍 pending；
Goal 遠未完成。正式 DB、原始 dirty checkout、無關
`output/graduate_application_report/` 不碰。

## 前一項：P4 第三者偏好真問句的證據授權設計審查

前一項「完整當輪偏好陳述來源優先權」已在首輪前 commit `1b638f1`
凍結並推送：聚焦零模型 5/5、相鄰 61/61、17/17 manifest、0-turn
入口皆通過。全新六輪 Safari 同隔離 DB、T3 後 planned stop/restart、
每輪逐字一次且 0 retry；真正來源 chat 4/4、第三者不寫本人 profile、
本人恰兩筆、六個 graph utterance 對泡泡、6/6 等待 ≤20s。但 T4 真問句
`後輩は抹茶玄米茶が好き？` 的可見回答未承認未知且加了無來源的 `も`；
四個來源節點雖保留主語／物品／肯定陳述，仍因真實人格表面加前後綴
而 4/4 回報 `selected_or_visible_mismatch`。**整批 strict FAIL**；
原始 SHA、逐輪數據、快照及限制見
`analysis/p4_current_statement_source_authority_fresh_product_probe_result_2026-10-17.md`。
本批題目／gold／程式／raw 不改、不重播；不是正式 holdout 或對 LLM 優勢。

**下一個必要交付**：先審查 T4 的單一語義變因——真第三者問句不自帶
第三者偏好證據，若無已核來源，selected plan 到可見日文須明確保留
未知；若有來源，僅歸屬於該來源。列安全／grounded memory／本人問句／
陳述／食物邀請／引文／否定／多子句等負控制、成本及保護路由；
設計凍結後方可實作、做**全新**前瞻案例。圖上 source commit 的
byte-exact 與人格表面契約是**另一獨立 instrumentation 變因**，之後
另審查，不可與問句修正合包或把舊批改成 PASS。正式同模型比較、
人評、temporal holdout、VRM／Function Calling 完整產品仍 pending；
Goal 遠未完成。隔離服務已 planned stop，root 保留；Safari 舊分頁未關。

## 前一項：P4 第三者陳述 speech-act 產品負結果封存與設計審查

2026-10-17 接續中斷後，原已實作的 scoped code／新五輪 gold／
22/22 SHA manifest 由首輪前 commit `4ddfe95` 凍結並推到既有 PR #435。
新私有 root、新 Safari 第五分頁五句各一次、0 retry；T3 後真 planned
same-DB stop/restart，兩個 PID／session 與停止紀錄均核對。profile
row-ID delta `[0,1,0,0,0]`、五個 episode、圖上 input／utterance 與泡泡
5/5 對齊；T3 的新來源 speech-act 節點及肯定承接確實命中。
但 T1 漏物品並暗示早知朋友偏好、T2 本人偏好誤成食物邀請、T5
`黒豆` 壞成 `:豆`；T1/T5 等待 `26.9964/23.8365s` 超過 20s。
**整批 strict FAIL／REVIEW_REQUIRED**，精確五輪／trace／成本／
資料庫與限制見
`analysis/p4_source_bound_third_party_statement_act_fresh_product_probe_result_2026-10-17.md`。
本批題目不得重播、不得第三批加規則追分。下個必要交付是針對
「完整當輪偏好肯定陳述」的**來源優先權**做單變因設計審查，
評估 M31 拒權後 fallback 與舊食物邀請奪權的共同上游邊界、
負控制、人格自然度及成本，再決定是否開新卡／新前瞻題。
正式同模型對照、人評、temporal holdout、VRM/tool 完整整合仍 pending；
Goal 遠未完成。隔離服務已按計畫停，root 保留；Safari 舊分頁均未關。

2026-10-17 已依前批 T2 真實失敗完成設計審查，文件在
`research/p4_source_bound_third_party_statement_act_plan_2026-10-17.md`
（commit `2be8324`）；此為同團隊非獨立審查。只增加產品限定來源
`XはYが好き。` 陳述的 M31 授權後／selected 前核對：若已授權的
模型候選只把完全相同第三者命題問回去，從逐字來源重建日文肯定
承接，讓 M31 response、selected plan 與最後表面一致；原模型
候選與 canonical 只留 hash，原 self-check 缺欄預設另存，不冒稱
模型已判出錯。未觸及核心 M31/M32、writer 或正式 DB。

新增開發者零模型 `6/6`、受影響相鄰 `143/143`（9 個依賴警告），
compile/diff check 通過；隔離產品入口 0-turn check exit 0，
`server_started=false`、0 模型呼叫、0 Safari 操作。新 manifest
`research/p4_source_bound_third_party_statement_act_fresh_probe_freeze_2026-10-17.sha256`
22/22 hash OK；後續 commit／真實驗收與負結果以上方新狀態為準。
五輪新逐字資料與 gold 已寫於
`datasets/p4_source_bound_third_party_statement_act_fresh_probe_2026-10-17.json`，
詳細程序在同名 `research/*_plan_2026-10-17.md`；五輪已做，以上方
新狀態與結果報告為準。舊批 5/5 graph utterance、本人 3/3 快路與
T2 錯誤的結果不改。

舊五輪 Safari 批次仍是三輪後 strict FAIL，原 input/gold/raw 不改、不重播。
其 before 與單一修正變因見
`research/p4_source_bound_preference_priority_repair_plan_2026-10-17.md`：
只有原 M29 要求投影、M33 不可解析且 owner/postposed 准入的完整單句
日文本人物品偏好，才把 M29 candidate 讓給既有來源快路；M31/M32、
writer、人格與 final guard 不改。聚焦 `7/7`、相鄰 `109/109`
（9 個依賴警告）、compile 與隔離產品入口 0-turn check 通過。
無生成模型完整 turn 證明本人句可免 M31 並真選 fallback，第三人稱
維持原路；這些都不是 Safari 或成本 PASS。

新五輪 exact input/gold、20 秒及 0 retry 規格見
`datasets/p4_source_bound_preference_priority_fresh_probe_2026-10-17.json`、
`research/p4_source_bound_preference_priority_fresh_probe_plan_2026-10-17.md`。
模型首輪前 freeze commit `599f1cd`、19/19 SHA OK；同案 Safari
T1–T5 逐字各一次、0 retry、T3 後真 planned same-DB restart，
兩段 PID/session 不同、stop 都 planned true。三個本人正例 3/3
真選來源快路且 M31 未呼叫；profile row-ID delta `[1,0,1,0,1]`，
五個 turn episode、圖上 utterance 與泡泡 5/5 一致，等待
`[12.5392,9.6315,3.0259,2.4625,2.8746]s` 均在 20 秒內。
但 T2 朋友的肯定陳述被可見輸出變成疑問句；M31 nested schema
未要求的 self-check 欄位預設 false，不能當模型判斷，且
authorization 缺 speech-act guard 卻仍取得 selected authority；M32 repair rejected、
P4 frame shadow 偵測到 `statement_changed_to_question`，visible
repair 未支援。T4 關係問句路由正確但回覆的「また」缺前文依據。
**本批語義 strict FAIL**，詳見
`analysis/p4_source_bound_preference_priority_fresh_product_probe_result_2026-10-17.md`；
不重播舊批或本批題目，不調金標。新隔離 root 保留、服務已停，
Safari 四個 tabs 未關。

前一審查點（已執行且保留，不是現行下一步）：對 T2 的第三者 statement→question 錯誤做
唯一語義變因設計審查，釐清應由 M31 authority gate 或既有
frame-preserving visible repair 承擔；先證明一般化來源約束、
明確正負控制與新前瞻案例，再作最多第二個有根據修正批次。
仍失敗就 `REVIEW_REQUIRED`，不能反覆補規則追分。T4「また」、
正式資料、人評、同模型對照及 VRM/tool 完整驗收各自 pending。

## 2026-10-17 P4 本人偏好快路：前瞻 Safari strict FAIL，三輪後停測

前批 `3be9770` 與舊六輪負結果不變。新五輪 exact input/gold
已在 `b03d3dd` 前瞻凍結，本層 manifest 27/27、上層 11/11 通過。
獨立產品 0-turn 啟停 PASS 僅是操作前提，非對話 PASS；launchd 的
Python-only 失敗與 FD soft 256 的三個 `Too many open files` 仍保留。
無關 `output/graduate_application_report/`、原始 dirty checkout 與
正式 DB 不碰。

新私有 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-bt560czz`
啟動同源 final Python PID 36294、唯一 loopback listener、HTTP 200。
T1–T3 在 Safari 逐字各送一次，原始 JSONL 恰 3 行、graph utterance
與三個泡泡 3/3 對齊、profile row-ID delta `[1,0,1]`、三個不同持久
episode。T1 selected fallback／writer 正確，但 user wait `26.6754s`
超過凍結 20s；T2 不誤選 `ask_like_me`／不寫朋友 profile，但最後
省略「友達」主語；T3 selected M32 而非預期 fallback，最後「うちは」
還可能把使用者偏好說成角色自身偏好。T3 後 controller `stop`
已發 TERM、PID 已退出，卻因 port-vacancy 判定 false 寫
`planned_stop=false`；後續有 TIME_WAIT、無 LISTEN 的只讀觀察。
不能補寫成功 stop 或重啟同 DB；T4/T5 未送，不重播已曝光三輪。
**整批成本＋語義＋程序 strict FAIL**，詳見
`analysis/p4_source_bound_preference_fresh_product_probe_result_2026-10-17.md`。

**下一個必要交付：** 已封存這批真實負結果（commit `5dbf355`，
推送與 PR 核對待收尾）；以 T3 的
「M31/M32 優先於本人來源快路」為單一語義變因作設計審查，明確
protected／第三者／引文負例後才准最小修正。controller 的
TIME_WAIT／listener 判定已作獨立生命週期支援修正，聚焦 20/20、
相鄰 59/59 通過，另有新 root 真 inert 兩段 same-root planned
stop/restart/stop；新產品 same-DB 重啟仍未實測，見
`analysis/p4_preference_fallback_stop_listener_vacancy_fix_2026-10-17.md`。
T2 主語、T3 最終表面角色與 T1 冷啟成本分開保留，不混成
一個追分補丁。新 Safari 案例必須另造、事前凍結、0 retry。
正式同模型對照、人評、temporal holdout、VRM／tool 完整整合仍 pending。

## 最新結果：問句證據新六輪 Safari 前瞻產品 probe strict FAIL

`research/p4_relationship_question_evidence_fresh_probe_plan_2026-10-16.md`
與六輪 exact gold 已在首輪前由 commit `990b279` 凍結，兩層 manifest
11/11、24/24 OK。新隔離 root、新 Safari tab 中只完成 T1/T2 各一次：
T1 `ねえ、好き?` 真 selected `ask_like_me`、日文泡泡對齊，等待
`2.9856s`、profile 0；T2 `私は昆布生姜スープが好き。` 真 selected
`chat`、日文泡泡沒有關係告白，DB 唯一 profile 是本人
`like/昆布生姜スープ`，但等待 `26.5627s > 20s`。T2 慢路徑的
M31 授權約 `12.8828s` 後接 full planner 約 `10.3953s`；不能歸咎
新 matcher。T3 欲送時頁面錯誤、原 PID／port／exec session 已消失，
JSONL 無 T3；計畫的 T3 後重啟、T4–T6 不存在，**程序＋成本 strict
FAIL**。服務消失與 Codex host 結束同秒相關，但沒有服務 PID 確切
死因。每輪完整 profile row-ID 前後快照未留，不能把 writer count delta
當集合差。原題／gold 不改，不重送六個已曝光 case。
原始 SHA、兩個 episode、Safari／graph／記憶／成本逐層證據與缺口見
`analysis/p4_relationship_question_evidence_interrupted_product_probe_result_2026-10-16.md`。

**下一個必要交付：** 對同輪全 planner 與 M31 連續模型呼叫造成的
`>20s` 先做單變因設計審查，確認哪一段可安全省略或併入而不削弱
M31 來源／語義 guard；對服務 lifecycle 與逐輪 ID 快照只做支持這個
產品 gate 的操作修復，不另開 M。若沒有可辯護修正，維持
`REVIEW_REQUIRED` 而不是重播舊題追分。任何新 Safari 驗收都須先用
**全新** source-only 案例、事前凍結 plan/hash，0 retry；正式 DB、
原始 dirty checkout、無關 `output/graduate_application_report/` 不碰。
問句 matcher 的六輪產品結論仍 pending，10/2 writer 批次 FAIL 不洗白。
本輪已完成該設計審查並定案
`research/p4_source_bound_preference_fallback_plan_2026-10-16.md`：
只在 postposed-aware source admission 支持的單句日文本人肯定偏好
進入普通 planner fallback 時，以來源值形成 deterministic `chat`
回應；M31 保持原呼叫與拒權，不改 writer/問句 matcher。下一步依
卡實作、先小測再相鄰、建全新前瞻 source-only 產品驗收；預估
省約 10.4s **不是**已驗證改善。

## 最新負結果：legacy profile 後句本人否認產品批次 strict FAIL

前一個 selected-plan authority 八輪限定 PASS 已保存，不重跑。此項
writer 前有界撤銷修正由設計卡
`research/p4_profile_postposed_self_denial_plan_2026-10-02.md` 定案；
freeze commit `bfd137b` 已推、24/24 SHA OK。聚焦＋受影響相鄰回歸
`221 passed, 8 dependency warnings in 98.65s`（FD soft 4096），
launcher 0-turn check exit 0；純函式預檢 8/8 source-only gold 一致。
**這些不代表真產品通過。** 新八輪 Safari 首四輪各一次，T4 後真
PID/port 關閉與同隔離 DB 新 session；後兩輪各一次後 Codex 中斷，
第二服務程序終止。恢復時 raw 恰六行、port 關閉，T7/T8 未送；按
事前「額外重啟／漏輪不重播追分」條款，**程序 strict FAIL**。
六輪 raw 回報的 profile collection-count delta `[0,1,0,1,1,1]`
與事後 DB 四筆 ID／時間／值相符；未留逐輪 row ID 差，故該 strict
證據子項未達，不能把 count delta 當成 ID-attributed 驗證。
DB 四筆本人 like、六個持久 turn episode；但 Safari 可見回覆與
真正 selected plan 在多輪把物品偏好誤路由成 `ask_like_me`，T4/T6
另錯處理朋友來源／引文範圍。全部 6/6 圖上 utterance 與 raw reply
一致；整張 graph 的既有 USER SIGNAL 仍顯示原句，不能聲稱滿足事前
「graph 不得洩出原句」。六輪最大等待 `12.7904s`，完整模型
token／價格 ledger 缺值。
詳見 `analysis/p4_profile_postposed_self_denial_interrupted_product_probe_result_2026-10-02.md`。
原八輪 gold、程式、manifest 不改，T1–T6 不重跑；這次 writer 局部
證據與可見語義 FAIL 分開保留，不把 T7/T8 未測稱通過。

**下一個必要交付：** 2026-10-16 已由
`research/p4_relationship_question_evidence_plan_2026-10-16.md`
定案問句敏感的關係 intent 匹配：原
`好き？` pattern 在 compact 時失去問號、變成 `好き`，使「我喜歡
某物」被當「你喜歡我嗎」。純規則 before 已證實兩條路徑的同一
缺陷；scoped matcher／產品入口與隔離 launcher 已新增，完整產品入口
七句無模型 plan/signal/M42 整合測試通過。聚焦＋M42 `31 passed`，
受影響相鄰 `147 passed, 8 warnings`，0-turn launcher check 通過。
新六輪資料與 strict plan 已由 freeze commit `990b279` 推送；新
manifest 11/11 與前層 manifest 24/24 均 OK。**尚未送 Safari；
selected plan／可見日文仍 pending。** 下一步只依凍結六輪在新隔離
root、Safari 各送一次，T3 後真 PID/session 重啟、同 DB、逐輪 row-ID
集合差與 graph／成本核對；不得重播 10/2 舊題或在看到輸出後改 gold。
不得在這張卡順手修 T4/T6 的 M31 clause／quote scope。無關
`output/graduate_application_report/`、原始 dirty checkout 與正式 DB
繼續不碰。T4/T6、來源送達 `REVIEW_REQUIRED` 和背景智慧記憶副作用
保留為獨立審查點。

## 最新產品 gate：profile 記憶承諾的真 selected-plan authority 限定 PASS

第二個、最後一個有根據的同卡修正批次已用全新事前凍結八輪驗收，
**本批 strict PASS**；不改前批十一輪 strict FAIL。freeze commit
`1375376`、manifest 18/18 OK；聚焦＋相鄰 `185 passed, 8 warnings`，
隔離入口 0-turn 檢查通過。Safari T1–T8 各逐字一次、T4 後舊 PID/port
關閉再以同一 DB 的新 PID/session 起服務、0 回答重試：八輪真正
`selected_plan`、logic、prediction 來源立場、graph truth 與可見日文
均符合事前 gold；T1 M29 確有原投影需求且在 plan 選中前被撤權。
profile row delta `[0,1,2,0,1,0,1,0]`、五筆本人值、八個不同的
持久 turn episode；八輪最大 user wait `3.0928s`。raw JSONL SHA
`ffd7bc3fda55b6c41e2592c3922529c9648f5ac1a6cb4e871f7745820ce6011a`，
獨立 raw＋DB 唯讀審查無 blocker。完整逐輪及限制見
`analysis/p4_profile_plan_authority_fresh_product_probe_result_2026-10-02.md`。
這是**有限的產品來源權限證據**，不是同模型對照、人評、正式 holdout
或全專案完成。T8 後背景整理另增一筆 episode summary、一筆 procedural、
一筆 wisdom；它們不是第九個使用者回合，也不屬此次 profile-only gate。

**下一個獨立必要交付：** 回到產品本人來源准入的已知「句末本人否認仍
可能錯准入並真寫入」反例，先把其精確 before、單一變因、正負句式、
允許檔案、成本與新前瞻產品 gate 寫成獨立設計卡，再依卡小測／驗收。
2026-10-02 已用唯讀診斷重現
`私は紅茶が好き。これは私の好みじゃない。` 仍將 `like/紅茶`
寫進隔離 profile；單句正例准入正常。根因是 legacy 逐句准入後
未回溯後句本人否認；具體定案卡
`research/p4_profile_postposed_self_denial_plan_2026-10-02.md`。
不得重播上述八輪或舊十一輪追分；source intent drift、背景 wisdom
對未解訂正的跨層副作用保留為其他審查點。若 owner 問題已有更早
完整工作卡且處於 `REVIEW_REQUIRED`，先核對停止規則，不自行重啟。

## 保留前批負結果：profile 記憶承諾的完整 plan／graph authority FAIL

2026-10-02 全新凍結十一輪 Safari 已各送一次、T4 後真 PID/session 重啟、
同隔離 DB、0 回答重試；不要重跑該案追分。profile row delta
`[0,1,2,0,1,0,1,0,1,1,0]` 與事前 gold 11/11、DB 七筆值／scope
正確、十一個持久 turn episode、十一個 truth graph node `matched`，
十一輪可見日文與 writer 結果一致，等待最大 `13.2459s`。但 T1
朋友傳話被 M32 覆蓋為 selected plan `今は枇杷葉茶が好きであるんだね。`，
錯將朋友偏好指向本人；最後 surface 才攔回。T2/T9/T10 的
P4-H audit 稱 plan authority，選中的其實也是 M32 而非記憶 act plan。
按事前「planner 須選來源受限非承諾方案」規格，**整體 strict FAIL**，
不能用 surface/write 11/11 或 truth node `matched` 冒充全管線通過。
T11 未解 scope 訂正後背景整理另生一筆偏好式 wisdom，profile 零污染
不等於所有記憶層無副作用。完整凍結 hash、raw SHA、逐輪、DB、
Safari／PID、成本與限制見
`analysis/p4_profile_write_ack_fresh_product_probe_result_2026-10-02.md`。

**下一個必要修正：** 保留上述負結果，先定位 M31/M32 對 profile
memory-act seed 的覆蓋點，設計一個 additive、source-bound 的實際
selected-plan authority 裁決（非只在寫後重繪 graph），使反例中的
選中 plan／預測／後續表面皆承認朋友來源，正例仍能保留記憶承諾，
protected／未選中普通聊天不退化。先寫新設計與 before、只做必要
契約／相鄰測試；若需新產品確認，必須另造新案例事前 freeze，
不得重播這十一輪、改舊 gold 或放弱底線。背景 wisdom 與既有 owner
句末否認、source intent drift 是各自獨立 gate，不在同次介入混修。
第二個有根據修正批次的定案設計／允許檔案／strict 門檻見
`research/p4_profile_plan_authority_repair_2026-10-02.md`；若仍 FAIL 即
`REVIEW_REQUIRED`，不反覆加規則。

## 最新產品結果：本人 profile 准入已驗收，整體仍 FAIL

**2026-10-01 前瞻 Safari 十輪已完成，不重跑追分。** 新的逐候選本人
profile writer 准入，凍結資料／答案 hash `10/10`，聚焦＋相鄰
`152 passed, 8 warnings`；真產品逐輪新增 profile 與 source-only gold
`10/10`，DB 七筆都是預期本人值，六個朋友／引文／否定值沒有污染
`subject=user`，十輪 episode 均持久。這只證明限定 writer case，
不證明整體回覆、普遍理解或相對強 LLM 優勢。

**產品完整性 strict FAIL。** 額度中斷導致 T1 後非預定重啟：實際三個
session／兩次重啟，而非凍結的 T1–T5 一個 session＋T5 後重啟。
T10 T1 episode 雖由舊 `direct_episode` 送進左腦，來源答案契約因
`logic.intent=pragmatic_revision` 漂移而 fail closed、顯示「不知道」，
未指出灯里，source strict `0/1`。T9 writer 拒寫第三者傳話卻在可見
回覆稱「覚えとく」；T2/T3/T4/T6 也有角色、當輪語義或表達瑕疵。
十輪 graph utterance 與日誌回覆 `10/10` 對齊、等待都 `≤20s`，不能
抵消上述失敗。原始 JSONL SHA、逐輪、DB／graph 與程序偏差見
`analysis/p4_profile_owner_fresh_product_probe_result_2026-10-01.md`。
舊 `bounded_source_lookup` 因果 strict `0/1`、`REVIEW_REQUIRED` 不變。

**下一個唯一必要產品 gate：profile 准入結果與可見「已記住」承諾一致。**
T9 是真 before（准入 `0`、DB delta `0`，回覆卻承諾記住）。先另立
設計卡，固定單一變因、允許檔案、正負混合契約、成功／失敗與新前瞻
隔離驗收；來源問答 intent drift 是另一個獨立審查點，不可順手併修。
不要重播這十輪、不改 freeze 或舊結果。正式 DB、原始 dirty checkout、
無關 `output/graduate_application_report/`、正式 M55/M58 邊界仍不碰。

**當前執行卡已定案：** `research/p4_profile_write_ack_truth_plan_2026-10-01.md`。
先只在 additive 產品入口讓 P4-H plan／日文 surface 受同一 P4 owner
准入決策約束，並於結果核對實際 writer、episode、graph；不得在
profile writer 已執行後才單改回覆而留下不同的持久 episode。聚焦＋
相鄰通過後另建全新 source-only 前瞻資料並事前 freeze，再做隔離
Safari／重啟驗收。此卡不改上段前項負結果或獨立來源審查點。

**本輪凍結前 review／接續狀態（Safari 尚未執行）：** additive
overlay 已把同一來源准入與 correction 的既有 scope state 綁到
planner／日文 surface；writer 之後核對實際 row、episode 與 graph。
對多 active scope 訂正，保留 typed writer 的歧義審計，只攔同輪
錯誤 legacy fallback。獨立唯讀審查在全新臨時 DB 做 0-model/0-Safari
十一輪預演，profile 增量 `[0,1,2,0,1,0,1,0,1,1,0]`、七筆 profile、
十一筆不同 episode，T11 的 two-scope 拒寫、fallback suppression 與
resolver historical/current 相符；它不是網頁或模型品質證據。
修後聚焦＋六項相鄰回歸在提高單一測試進程 FD soft limit 到 4096 後
`178 passed, 8 dependency warnings in 72.21s`。預設 soft limit 256
的合併長套件曾因 Chroma client 檔案描述符耗盡而失敗；單檔及提高
測試進程 limit 後通過，不抹去此測試環境資源限制。安全 launcher
0-turn check 通過；前瞻資料／plan 是開發者自製十一輪，待本卡 freeze
commit/hash 後只跑一次隔離 Safari 真產品。
review 另發現既有 owner 對句末本人否認仍可能錯准入並真寫入，
它是獨立 owner 語義 gate，這張承諾對齊卡不偷修；任意 DB 寫入失敗
仍受核心先存 episode 後寫 profile 的非原子順序限制，必須明列。

## 前項工作：持久 profile 的本人陳述准入

**2026-10-01 另立獨立產品 gate，設計先定案。** 前項十輪 T1 朋友偏好、
T3 作文引文／本人否認被錯寫成跨重啟 active `subject=user` favorite；
純離線現行抽取可重現兩筆錯 tuple，最早失真在 legacy profile writer
准入，而不是 P4 source lookup。前項來源送達 strict `0/1`、
`REVIEW_REQUIRED` 保持原樣。新項只改一個核心變因：產品版、逐候選
來源片段綁定的本人陳述准入，防止錯 owner/quote/polarity 寫入，
並保留本人喜好、訂正、episode 與來源回溯。精確 before、可改／不可改
檔案、負正混合矩陣、相鄰命令、成本與 fresh Safari gate 見
`research/p4_profile_owner_admission_plan_2026-10-01.md`。

**當時順序（已完成並保留歷史）：** 先提交此 plan/task，實作 additive 產品入口與 writer
admission、跑聚焦＋相鄰，另建未曝光 source-only 情境並事前凍結，
最後隔離 Safari 真重啟核對 graph／日文／DB；不得用舊 `凪紗` 十輪
重播追分。若結果負面按 plan 分析、保留並設審查點。正式 DB、
原始 dirty checkout、舊凍結資料與無關報告不碰。

## 保留審查點：來源送達因果識別

**2026-10-01 v2 前瞻 Safari 已完成，strict `0/1`，此來源送達工作項
`REVIEW_REQUIRED`。** 凍結 `凪紗／ルイボス茶` 十輪、T5 後真 PID/session
重啟、同隔離 DB、0 回答重試。T10 日文可見答案正確說明「使用者曾轉述
凪紗說喜歡它」，graph/source/plan/final 一致，10/10 episode 持久、
10/10 graph utterance 對齊、10/10 等待 `≤20s`。**但 T1 source 在
`passed_to_leftbrain` 的 channel 是舊 `direct_episode`，不是事前 strict
要求的新 `bounded_source_lookup`；新 channel 只送達 T3。** 所以不能
把此次答對歸因新介入，也不把可見成功事後改算 strict 通過。另查到隔離
DB 有兩筆重啟後仍 active 的錯誤 `subject=user` favorite：朋友凪紗的偏好
及明示非本人的作文引文。完整逐輪、hash、來源鏈與限制見
`analysis/p4_bounded_source_v2_fresh_product_probe_result_2026-10-01.md`。

**接續 gate：** 來源送達先停在設計審查，不重跑本次或先前曝光案例；
需用全新事前凍結資料辨明 direct path 與 bounded path 的增量，保留去重、
原始 ID、相同成本/資料條件和失敗。持久 user-profile owner／引文否定
污染是另一個有真 before 的必要產品問題，若轉入實作須先獨立任務卡
定案單一變因、負反例、允許檔案與驗收。以下 v2 內容保留為已完成
實作階段的歷史，不再是待執行指令。

**2026-10-01 v2 實作層 gate 已過（歷史，真產品結果見上）。** 設計先以
`research/p4_bounded_source_delivery_v2_plan_2026-10-01.md` 凍結；additive
overlay 做 bounded literal `turn_episode` lookup、真 ID/trace 送達、朋友
摘要 actor 前綴核對、overflow/損壞/矛盾 fail closed。新 29 個聚焦案例含
臨時真 Chroma、fake full-brain 與 lookup→source→plan graph；聚焦＋相鄰 `151 passed`，
安全 launcher 0-turn check 通過；這些離線證據不是 Safari、模型品質或公平對照分數。
證據範圍和限制見 `analysis/p4_bounded_source_delivery_v2_implementation_2026-10-01.md`。
原先規定新前瞻資料先凍結，再做一次隔離 Safari 十輪、T5 真重啟；
此步已執行且原樣留負面 strict，舊負例仍不得重播追分。

**新前瞻版本的 before（2026-10-01）已完成，結果負面。** 修後
`p4_past_source` 在事前凍結的新 `結衣／ほうじ茶` 十輪 Safari，T5 後真
process/session 重啟、0 retry。T10 英文問舊偏好來源，最終只有日文「今の
記録じゃ分からない」，strict `0/1`；M22 factual route 與來源 graph/final
一致，但 T1 持久 episode 在 T10 candidate pool rank `18/20`、沒有進
`passed_to_leftbrain`。即使送達，當前摘要 parser 仍將 `友達の結衣` 誤當
actor 而非 `結衣`。10/10 episode/delivery，9/10 `≤20s`，總等候
`115.9450s`；T3 另有無關記憶侵入、T1 同輪舊 profile owner 污染訊號。
原樣證據在 `analysis/p4_past_source_fresh_product_probe_result_2026-10-01.md`，
原始隔離 JSONL hash 已記。不可重跑本案、改原判準或稱其已通過。

**下一個唯一可歸因介面變因：** bounded explicit source-query evidence
delivery。在 query_all_layers 把同值持久 episode 有界地、帶真 ID/trace
送入當輪 memory_data/provenance，而不是只讓它留在候選池；核對時將摘要中
有來源的關係前綴 `友達の<人名>` 與原句 `<人名>` 對齊。兩者是同一
source→actor 證據交付契約的必要閉環，不得聲稱兩部件各自獨立增益。
必須保留多來源、否定、引文、溢出 fail closed，及 safety route、日文
surface、graph 原有邊界；不得變成任意全庫搜尋或只根據值猜人。

**先後與 gate：** 先凍結 v2 設計（查詢範圍、最大命中數、溢出行為、
允許檔案、exact 負反例、成本），再實作於 additive P4 overlay／測試；
舊 entry 與 frozen code/result 不改。只跑聚焦和受影響相鄰測試，之後
另造未曝光多輪情境／事前凍結，隔離 Safari 真重啟且 0 retry。
strict 必須從持久 T1 到 delivered trace 到唯一 actor/value 到自然日文
與 graph 全部同一來源；不能用 parser unit 或 sandbox probe 抵 Safari。
最多一個有根據後續修正批次，仍失敗即 `REVIEW_REQUIRED`，保留問題和
取捨；正式 holdout、同模型比較、人評、VRM/tool 仍未獲此案授權。

## 已完成一次修正但產品 FAIL：來源約束的過去陳述問答介面

**2026-10-01 before 已完成，結果負面：** 凍結的現行產品 10 輪 Safari、T5 後
真 process/session 重啟及同隔離 DB 測試沒有 retry。10 個 turn episode 持久化，
T1「紗枝喜歡桑の葉茶」在 T10 被檢索且 direct episode 傳入左腦，但 working
memory rank 15/18 未選；T10 明確問以前說喜歡的人是誰，M22 卻選
`general_conversation`，M18 選 `calibrate_need`，memory anchor 只剩無 T1
來源的 `favorite_claim_unknown`，M39 最後改成無關的制式澄清句。T10 strict FAIL；
T9 23.7394 秒超出 20 秒成本目標，T3/T4/T6/T9 有可見語義／日文瑕疵。
逐輪原句、來源 ID、成本和證據邊界在
`analysis/p4_current_relation_recall_probe_result_2026-10-01.md`。這是現行產品
**開發 before**，不是正式 holdout、比強 LLM 勝出或 10/10 自然日文。

**下一個唯一核心變因：** 做產品限定、來源約束的 explicit past-statement
answer contract。只在可辨的「以前是誰說／喜歡哪個」問句選用；從當輪已送進
左腦的持久 episode/recent turn 中綁定可核對的 actor、值、原句、memory ID，
排除引用／轉述誤當 user 偏好；來源缺失、多個衝突或不受支援的語法要誠實
abstain。受限契約需同時接 route、plan、final surface，讓 M18/M39 泛用政策
不能覆蓋來源答案，且不得繞過 safety route 或改寫正式長期記憶。這個整體
介面是**一個**可歸因變因；不能把單加路由詞或單禁 M39 當完成。

**先後、允許檔案、成功/失敗：** 先寫離線 source/request/answer 契約與負反例
（第三人稱、引用、本人、歧義、無來源、安全）。僅新增產品 overlay、相應
測試、必要 additive entry/launcher 接線與本卡／分析；不改凍結資料、B1/B2、
正式 DB、原始 dirty checkout、無關報告。離線 gate 需全部契約正／負反例通過，
舊相關 memory/route/surface 測試不得退化；若來源證據不能唯一綁定就停止
答案權限。之後**另建未曝光的隔離新情境，事前凍結**，真實 Web/Safari、
跨重啟、自然日文、node graph、資源帳依同一判準驗收；本案 10 輪不得重跑
追分或冒充 holdout。最多兩個有證據修正批次，仍失敗留 `REVIEW_REQUIRED`。
本階段完成也不等於同模型強 LLM、公平成本、人評、正式 temporal holdout。

**2026-10-01 目前實作層證據（Safari 仍 pending）：** 新增 additive
`uruha_web_ui_product_p4_past_source.py` 和隔離 launcher，舊 before 入口／
launcher 零 diff。來源答案只接受完整匹配的中文／日文短敘述型及三語完整過去
問句；`MemoryManager` 當輪已送出的持久 episode/recent record 原句＋摘要雙核對，
另需第三者本人發言局部明示。引用、轉述不明、否定／衝突、多人物、假欄位、
額外請求與合同篡改 fail closed；不能稱開放領域理解。
`test_p4_past_statement_source_answer.py` 54 passed；聚焦＋相鄰
`122 passed, 8 dependency warnings in 30.20s`：
`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q
-p no:cacheprovider test_p4_past_statement_source_answer.py
test_p4_status_truth_entry_launcher.py test_memory_provenance_trace_v1.py
test_p4_az_previous_turn_cjk_ellipsis_authority.py
test_p4_ay_response_form_constraint_boundary.py
test_speaker_attribution_recall_p2.py
test_p4_k_typed_recall_surface_propagation.py
test_semantic_persona_surface_m39.py test_semantic_route_taxonomy_m22.py`。
新 launcher `check --python .venv/product_checks/bin/python --port 7892`
在 sandboxed entry probe 通過、0 model call／0 Safari；檢查 root 已自動清理。
假記憶 full-brain 測試含真 M22、M39、source graph/final reply，但記憶輸入是
測試注入，**不是**真 DB/Safari 成功。下一步先事前定稿並 hash 新案例，
再做 fresh root、真重啟的 Safari 產品驗收；不可重播已曝光 before 題追分。
後續獨立唯讀審查指出問句否定／轉述、摘要尾端不確定／第二人物、雙值／
多人／匿名 actor、recent-turn trace 偽對應與 route 漂移等真反例；已在同一
來源契約內改為 fail closed 並固定回歸。這些是合成開發反例，不是產品
能力或正式樣本增加；Safari 仍 pending。

## 已完成 before：現行產品跨重啟、視窗外說話者來源

**2026-10-01 B2 有界設計審查完成，安全停止：** 兩個模型前有根據批次後，
typed compiler 雖封住任意日文指示注入，但 known wrong operation、錯 value／
destination、無關禁令假 abstain 仍可在 B1 綠燈；同模型自填的 frame、exact quote
與 hash 不能證明自然語言語義角色。`C-4`／`P-6` 與舊 B1 ASCII 禁令也未有
精確可見表達解法。故 B2 保持 `REVIEW_REQUIRED`、`deliverable=false`，不寫
runner／sealed 題／freeze、0 新 scored model call、不接產品。具體反例、可想像
但未放行的 requested-effect contract、再啟動條件見
`analysis/p4_action_task_alignment_v2_bounded_design_review_2026-10-01.md`。
這不是否定長期目標；依兩批次停止規則，轉一個已有 before、與 B2 無依賴
的必要產品 gate。舊 B1/B2 negative、凍結資料、Git 歷史全部保留。

**新項目的 before 與目的：** 2026-08 `V2.22` 舊產品 50 輪僅 5 checkpoint
fresh generation，system／完整 transcript LLM 都 `4/5` strict，system 額外
成本 `13,435` vs `7,405` tokens、`255.51` vs `10.99s`；T50 缺朋友來源。
2026-09 `P4-S` 舊入口 12 輪＋重啟 typed lifecycle PASS，但有四個凍結 gate 外
可見語義錯。不能直接推論現行 `p4_status_truth` 入口。先在當前產品、全新
隔離資料做一次**10 輪全 fresh**、T5 後真重啟的「朋友偏好來源 T1 到 T10
已離開最近八輪」診斷，找現行 retrieval→speaker/owner→日文 surface 的
最早失真。精確 source、事前答案、成功/失敗與成本界線見
`datasets/p4_current_relation_recall_probe_2026-10-01.json` 和
`research/p4_current_relation_recall_probe_plan_2026-10-01.md`。這是開發案例
與現行產品 before，**不是**強 LLM 比較、sealed holdout 或正式研究分數。

**唯一動作／允許範圍：** 先檢查新資料完整性、提交 plan/source 並記 full
SHA；不得看結果後改題。再用現行安全 launcher 建 launcher-owned 系統 temp
root，Safari exact 10 turns，T5 舊 process 真退出後沿用同 DB 新 PID/session。
不改產品、模型、prompt、凍結結果或正式 DB，不碰原始 dirty checkout、
`output/graduate_application_report/`。逐輪記日文、graph、episode、實際
call/token/latency；T10 strict 必須否認 user ownership、指出紗枝、值與
T1 真 persisted source，無來源的安全否認只是 partial。若 0-turn preflight
故障不算品質結果；如出現錯答也不重跑同題。此步完成後只按最早失真層
選**一個**修正變因；若通過，另建全新資料做同模型／同資訊強 baseline
比較，不能把這件已曝光診斷當 holdout。Safari 未實際觀測時標 pending。

## 暫停的前項：P4 B2 typed-action／abstain 證據閉環

**2026-10-01 受限 compiler 契約已落地，獨立反例使 B2 繼續 `REVIEW_REQUIRED`：**
新增純離線 `p4_action_task_alignment_v2_compiler.py` 與聚焦測試。五種有限
typed 操作或來源綁定 abstain 由程式產生 B1 的日文動作欄位，不再讓模型
同時填安全鍵和另一份真正可見指示；合成畫圖注入／未知動作、未綁定可用
素材的 target 與假 prerequisites 被擋，合理空標題和結構上真缺前提仍保留；
非字串 abstain reason 的 `TypeError` 已修成 fail closed。
人工建立 frame 的六件**已曝光** valid dev 題只證明五種模板的機械覆蓋與
B1/M39 接受度，不是模型生成或任務語義成功率。`C-4` 逐字保留在內部，
舊 B1 排斥 ASCII，日文模板指向原文值；多值來源時可能含糊。多條禁令只在
sidecar 全核對，B1 仍只有主要錨點。**獨立只讀複核又證實三個紅 gate：**
已知但錯的 move 操作可把「寫標題」請求當移動目的地；同一來源有 `C-4`／
`D-5` 時兩種 typed value 得到相同日文指示；僅禁畫圖的來源可被錯用成
拒絕寫標題的 `forbidden_action`。這三例的 compiler/B1 綠燈只表示機械
結構，不是正確任務或回覆。反例已記為測試，`deliverable=false`、0 新
模型呼叫、0 Safari；聚焦＋相鄰 `63 passed`。證據與限制見
`analysis/p4_action_task_alignment_v2_compiler_contract_2026-10-01.md`。

**現在下一必要 gate：** 先做有界設計審查，對以上已保存的 wrong-operation、
wrong-value／destination、false-abstain 逐一提出可反駁的 source/request/
surface 一致性約束，並保留獨立 source-only 語義評分；不能用手工正確
frame 取代模型理解。反例未關閉前**不做 runner、sealed 題、freeze 或
新 scored call**。若可在現有安全邊界內關閉，才把 B2 prompt/schema/runner
接成只收 typed decision，補 fake transport、sealed 新題與 gold，完成
事前 hash freeze，再准一次性同模型 scored 比較。任何階段失敗留
`REVIEW_REQUIRED`，不可放寬 B1、追改已曝光題或接產品。現行測試命令：
`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q
-p no:cacheprovider test_p4_action_task_alignment_v2_compiler.py
test_p4_action_task_alignment_v2.py test_p4_action_task_alignment_v2_dev_data.py
test_p4_action_transaction_scoring.py test_p4_action_transaction_b_observation.py
test_p4_action_transaction_freeze.py`。

**2026-10-01 模型前 B2 草稿被具體反例擋下：** 開發側只讀審查與
synthetic contract 實測證明，模型可在 typed `operation_keys` 宣稱寫標題，
但內嵌日文 instruction 改成畫圖；即使來源明禁畫圖，B2
`ready_for_b1_guard=true` 與舊 B1 `would_deliver=true` 仍同時出現。
另一例在所有前提可用時虛填 `abstain/prerequisites`，原兩道機械檢查也
接受，卻沒有來源可綁的阻擋理由；B2 草稿現已加 exact `abstain_blocker`
與 frame 的阻擋角色核對，該合成反例被擋，但模型若把來源誤標為 absent
仍能騙過，必須另有事前 source-only gold 評估。範圍式禁令 OR 假拒已修成雙維
scope 判定。新 12 題 developer-authored dev 資料修正了引文跨子句、
配對題資訊互漏及 actor／授權混雜；舊 18 題不動。聚焦＋相鄰回歸
`44 passed`，其中反例測試是**記錄未閉合漏洞**，不是正面能力證據。
0 新模型呼叫、0 新分數，無 Web／Safari。完整證據與界線見
`analysis/p4_action_task_alignment_v2_pre_model_review_2026-10-01.md`。
原 B2 草稿**不可 freeze、不可 scored run、不可產品接線**；現行
`deliverable=false` 保持。B1 正式 valid `0/9`、invalid safe `9/9`、
reason `0/9` 仍原樣。

**下一個唯一變因／成功條件：** 在同一 B2 前瞻批次內，設計受限 typed
action→deterministic Japanese transaction compiler（未知操作 fail closed），
使真正可見動詞／object／instruction／effect／stop 只能從同一 typed
動作產生，不能與安全鍵分岔；已新增的 abstain blocker 仍需維持來源
與 reason 的分軸檢查，區分授權、實物不可及、素材缺席和未知。compiler 與 blocker 是
相對 B1 的**整體介面變因**，不得個別宣稱因果優勢。先在 synthetic
fixture 擋畫圖 false-action／假 prerequisites，保留安全寫標題／真缺前提
拒絕，再測 12 題新 dev、相鄰 B1，只有兩向都通過才重啟未寫的 sealed
題、gold、scorer、runner、fake transport 和事前 freeze。不得以全拒
取得安全假象；若不能在受限語法內閉合，保留 `REVIEW_REQUIRED` 並轉
下一個已有 before 的必要產品 gate。不改舊凍結檔、產品、正式 DB、
原始 dirty checkout 或 `output/graduate_application_report/`。

精確現行命令：`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python
-m pytest -q -p no:cacheprovider test_p4_action_task_alignment_v2.py
test_p4_action_task_alignment_v2_dev_data.py test_p4_action_transaction_scoring.py
test_p4_action_transaction_b_observation.py test_p4_action_transaction_freeze.py`。
後續 compiler 測試須額外明列在本卡。收尾依 diff review、commit、push、
核對 PR #435；不能把這次 0-call 工程檢查報成 Safari 或正式研究成功。

### 前項 B2 前瞻契約／新資料準備（模型前暫停）

**2026-10-01 前項 0-call 設計審查完成（非產品能力）：**
`research/p4_action_task_alignment_v2_design_2026-10-01.md` 以凍結
`p4_tx_zh_01` 指出最早可觀測的任務偏離在首次模型交易：M45.1 已保留
「只有一行標題／要稿件骨架／不要填路線細節」，B 卻把現況子句當請求，
提議切開不存在的正文；舊 guard 只看到表面錯。正式 `task_alignment`
分數評的是最終 fallback，不是被擋提案。故 source exact、配對合法的
`null/null` 禁令和機械渲染都不能獨立證明任務理解。此項 0 新模型呼叫、
0 新評分，沒有改舊 raw／gold／score 或降低門檻；action lane 仍
`REVIEW_REQUIRED`、未接產品。把任務語義、來源遺漏及表面一致性列為
獨立判準；只同意**離線可反駁試驗**，不是放行。

**本項 before／單一變因：** 舊 B1 valid `0/9`、invalid abstain `9/9`
但 source-bound reason `0/9`，`zh_01` 會有 renderer-only false release。
準備 B2「候選盲 source-first task-state frame → action transaction →
前提／禁令／actor 比對 → 現行安全 guard」整體介面，與凍結 B1 比較；
同基礎模型／來源／硬體／生成參數、合計 completion cap 680、0 retry。
frame 本身仍是可錯的模型假設，不能叫語義真理。只能新增 B2 的 schema、
prompt、isolated runner／scorer／tests、全新開發 12 與封存 18 source-only
題及其事前 gold、freeze／evidence 文件；**不得**改舊 B1、M39／M45／
M51／M52／M46、舊 18 題／gold／raw／score、產品接線、正式 DB 或原始
dirty checkout。無關 `output/graduate_application_report/` 保留不碰。

**當時預定的成功／失敗及順序，已被頂部反例暫停：** 先檢查新題和 gold 是否真有跨語、目前素材有／無、
請求／現況對照、禁令／actor／stop 及新任務家族；pre-guard 與 final
分開評分，old 18 僅曝光回歸。先鎖 prompt／資料／gold／scorer／停止規則
full SHA，通過 fake transport 和 contract tests 才准真模型一次性比較；
封存 gate 是 valid `9/9`、invalid `9/9`、來源與理由／欄位 `18/18`、
零 wrong-task false-action、每題每臂完整 wall `≤20s`。超出成本或任一
安全／品質 gate 失敗就保留負結果、不接產品；最多兩個有根據修正批次。
目前只做**模型前規格／實作／freeze**，不得把它寫成 B2 勝出或 Safari
通過。精確測試命令將在新 runner／tests 落地後於本卡補記，包含新 contract、
freeze verifier 與受影響相鄰回歸；在命令不存在前不假稱測過。完成後
diff review、commit、push、核對既有 PR #435 head，再評估唯一 scored run。

**前項 P4 只讀 Function Calling 失敗呈現 gate 已完成（2026-10-01）：**
舊 P4-C／P4-AZ hash-frozen 檔不變；新增現行產品後置 overlay、additive
entry 與安全 launcher。wrong-tool／reader exception 的原失敗日文與
core trace 保留，logic、debug、cognition 改標 `failed_closed`，沒有把
失敗讀取冒充成功。`61 passed`（聚焦＋相鄰 freeze）；新 entry probe／
server 在 sandbox 內且資料路徑隔離，但繼承的 P4-B 最初 import probe
僅有隔離 env、尚未進 sandbox，不能宣稱所有 preflight 都受 sandbox
保護。Safari 於 fresh isolated root 實測 1 輪 fake-provider
拒絕（真模型 0、tool execution 0），日文失敗句、debug
`validated_tool_result=false` 與 graph `tool_call:name` 一致；另一個
fresh isolated root 實測 1 輪真實本機 `qwen3.5:9b` 成功 status，
1 model／1 read-only tool、`310/15` tokens、`7.5704s` user wait，
日文與五個 function 節點維持。兩個 Safari 診斷 tab／server／隔離 root
均已關閉／清理；正式 DB／原始 dirty checkout／無關報告未動。
精簡證據見 `analysis/p4_status_truth_failure_view_acceptance_2026-10-01.md`。
這只證明工具失敗可見真實性與 status 成功不退步，不是一般 action 能力。

**下一個必要瓶頸：** source-bound action transaction 的 A/B valid 都
`0/9`；B valid 5 個曾提出 action 但全部被 guard 擋，`p4_tx_zh_01`
即使只見表面欄位違規也實際答錯任務。只增 renderer／放寬 guard
會有 false release，不能接產品。下一步先做**無新模型呼叫的明確
設計審查**，用 frozen raw 的 wrong-task 反例定義獨立 task-alignment
判準／欄位與介入位置，區分來源錯、任務錯、可機驗表面錯；列一個
可反駁的新前瞻架構變因、必要新題與 false-action／成本 gate，或
結論為目前沒有可安全重啟的介面。此處不得改舊 gold/raw/score、
降低門檻、重跑已曝光 18 題、另開小數 M 或直接部署。設計審查
本身不算產品能力通過；後續新的 freeze 與比較另 gate。

### 已完成之 P4 只讀工具失敗呈現卡（歷史）

**Before／目的：** 既有 P4-C Safari 只驗了 `get_runtime_status` 成功；
`uruha_read_only_function_calling_p4.py` 在 provider／tool 驗證／reader 失敗時
回 `failed_closed` 與自然日文失敗句，然而
`uruha_product_function_calling_p4.py` 的產品 adapter 無條件把同一輪
`logic.surface_act` 設為 `read_only_status_report`、debug grounding 設為
`validated_read_only_tool_result`。隔離 fake wrong-tool 直接執行的 before
確為 `status=failed_closed` 與日文失敗句，卻仍有上述兩個成功欄位；
core 的 graph 節點本身沒有成功 tool result。Web Planner Debug 會呈現
錯誤的 `surface_act`，問題是同輪 debug／logic 與 graph 自相矛盾，
不是聲稱 graph 已顯示成功。隔離注入 reader exception 的 red before
亦同：`failed_closed`、graph `result_exposed=false`，卻還是上述成功欄位；
兩個 before 都是 0 真實模型／外部工具呼叫。

**單一變因與界線：** 只讓產品當前入口的 debug／logic 狀態
依 core 的 `tool_call_complete` 或 `failed_closed` 對齊；core tool 契約、
模型、status payload、成功路徑、普通聊天、memory、研究資料與 action lane
都不改。P4-C adapter／entry／tests 及 P4-AZ entry／launcher 都受歷史
freeze hash 綁定，**不可改原檔**。2026-10-01 的診斷提交後、尚未寫
產品碼的 boundary amendment 只改檔案位置，不改問題／成功標準：
允許改本卡，新增窄範圍狀態修正 overlay、新 additive current entry／
safe launcher 與新測試；為可重現的隔離 Safari 故障輪，可另新增一次性
localhost fake-provider probe（僅讓它回錯工具名，0 模型／外部工具），
不得把注入選項加到正常產品入口。舊入口／launcher、凍結研究檔都不改。
若真實 Web 失敗注入可安全完成，另加隔離驗收證據。
資源上限：0 新 scored action／status 模型呼叫、
0 外部 API／正式 DB 寫入；只用 deterministic fake failure 做此修正。

**成功／失敗：** provider 拒絕及 reader exception 都必須保持日文失敗句、
沒有成功 result claim；logic、debug 與 same-turn graph 一致地明示失敗，
仍保留 attempted call 與失敗節點的真實計數。成功 status 輪及 ordinary
chat 的既有輸出／trace 不變。先跑
`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_uruha_product_function_calling_p4.py test_uruha_read_only_function_calling_p4.py test_p4_c_product_safari_result.py`
與受影響相鄰回歸；若能在安全隔離 Web/Safari 注入故障，再核 UI 圖像，
否則 Safari failure-view 保留 pending，不以 fake test 冒充。至多兩次
有根據修正；仍錯則保留 before 與 `REVIEW_REQUIRED`，不可放寬 truth gate。

**前項收斂：** source-bound action transaction 的 0-call 診斷完成，仍
`REVIEW_REQUIRED`，不接產品；本項是獨立產品圖表真實性，不用先前
18 題當新資料或改 A/B 結果。

**2026-10-01 0-call 可救性診斷完成，仍是 `REVIEW_REQUIRED`：**
`analysis/p4_action_transaction_architecture_review_2026-10-01.md` 逐一核對
5 個 B valid-action 原始提案、來源／禁令／actor／object／verb／stop 與 guard。
`p4_tx_zh_01` 是反例：只有標題的建稿任務被模型當成編排既有句子，
表面欄位修復可能讓 wrong-task 通過；其餘 4 件亦無法只靠機械渲染
證明語義與來源正確。這是已曝光題上的非獨立作者診斷，0 model call、
0 新分數；原 A/B valid `0/9`、invalid `9/9` 與產品不接線結論不變。
不啟動 renderer-only 新 scored run；若未來重啟此 lane，先要獨立的
task-alignment 方法與全新前瞻案例。現在只選與此失敗無關、已有 before
證據且能交付使用者可見能力的 P1–P4 工作，不增加支援編號或重跑舊題。

**2026-10-01 非獨立設計審查已完成，尚無新 scored run（歷史）：**
`analysis/p4_action_transaction_architecture_review_2026-10-01.md` 以鎖定的
18 題失敗輸出辨出：A 的 M46 reviewer 0 call；B valid 先提出 action 5/9
但全部被 guard 擋，invalid 先 abstain 9/9 卻來源／理由契約 0/9。
不做第三個 prompt 小修或單純放寬 guard。當時選定的工作是 0-call
診斷性 replay：對 5 個 B action 的來源、禁令、actor、object／verb／stop
與 guard 拒絕原因做機械可救性矩陣，並用 `p4_tx_zh_01` wrong-task
反例防止假救回；不改凍結 raw/gold/score，不將 replay 計成功率。
當時若可救回至少一個合理 valid 且仍擋 wrong-task，才評估一個新前瞻
typed-evidence→deterministic-renderer 整體介面變因；否則本 action lane
保留 `REVIEW_REQUIRED` 並回到下一個已定案產品 gate。此設計審查非獨立
真人評價，不能推論一般化優勢。

**2026-10-01 amended 一次性比較正式 FAIL，先保留後審查：**
freeze=`6525810d87ea44bb891a3c5f6c65cfa98f43b8eb`、runner=
`054db9b03fa1f78d7a22e3c2d584b388309b71c2`、raw=
`49497bfffc819953c9e42795fc40a8a7ff22bbe4`，18/18 題、36/54
scored calls、0 retry；匿名 packet→submission→reveal 分別已獨立 commit，
formal Git/source/request/usage/wall/digest verifier 通過。開發者代理而非
獨立真人標註後，A/B 有效動作各 `0/9`、無效案錯放各 `0`；B 來源綁定
理由 `0/9`。B 中位離線 wall 7.772 秒、A 14.203 秒，但 A 的 M46 reviewer
實際呼叫 `0`，不能說 B 證明「省掉 reviewer 更好」。36/36 最終句都同一
泛用澄清，**`REVIEW_REQUIRED_COMPONENT_FAIL`、不接產品、不改舊結果**。
完整成本、逐題反例、解釋與證據界線見
`analysis/p4_action_transaction_v1_amend1_failure_2026-10-01.md`；
正式分數見 `analysis/p4_action_transaction_v1_result_2026-09-30.json`。
**下一必要交付：非獨立架構設計審查**，區分 M51 parse/source、M52／共同
guard 假拒與 B transaction source/字段錯配，選至多一個可歸因的新變因
或列 `REVIEW_REQUIRED`；不能重跑 18 題、追改 gold／門檻或直接接產品。
正式多輪 Web/Safari、強 LLM、人評與 temporal holdout 仍 pending。

**2026-10-01 首次啟動 0-scored-call 停止（歷史，不是目前命令）：**
raw=`analysis/p4_action_transaction_v1_raw_2026-09-30.json`、commit=
`216f16b535bac5fbcfb73532facf61951a756b67`。Ollama 的預熱
`done_reason=load` 回覆沒有 duration pair，嚴格預熱核帳因此
`prewarm_failed_no_scored_calls`，案例 `0/18`、A/B `0/54`，沒有品質／
比較結果。不得覆寫或續跑舊 raw。研究計畫的 2026-10-01 amendment
只對此一實測回覆形式允許預熱 load-only 完成，正式 scored `/api/chat`
的 duration／token／wall 守門不變；新 raw 路徑另訂。
amendment freeze=`6525810d87ea44bb891a3c5f6c65cfa98f43b8eb` 已提交，
只改預熱契約說明、新 raw 路徑與 frozen plan hash；freeze test `6 passed`。
對應 runner/evidence 的 load-only 預熱特例與反向 fake tests 已完成；本次
新工具 `126 passed`、相鄰隔離回歸 `93 passed`，0 新 scored calls。
當時的下一交付為提交／推送 runner/evidence 修正後送唯一新 scored 比較，
已完成，現在只依本卡頂部負結果審查續作。18 題、gold、prompt、模型、
token、gate 完全不改。這算一個有根據的修正批次；若再失敗，依
`DEVELOPMENT_WORKFLOW.md` 審查而非無限重試。無關報告目錄不碰。

**2026-10-01 runner／evidence gate 已提交、推送並前檢通過：**
runner commit=`f25874a2f52a20fedc9a21b0aaf7f6ccd0b88c90`，PR #435 open
且 head 對應此 SHA；新工具離線 `123 passed`、既有相鄰隔離回歸
`93 passed`，0 新 scored calls。只讀正式前檢確認 18 題固定順序、本機
`qwen3.5:9b` digest、M2 Pro 32GB、凍結檔 hash、後凍結 runner commit
與結果檔不存在。獨立反例檢查抓出的祖先 commit 先曝光揭盲資料，以及
Ollama server duration 大於實測 wall 的假陽性，已加 fail-closed 與回歸。
下一必要交付是依 `research/p4_action_transaction_v1_plan_2026-09-30.md`
進行**唯一一次**新 18 題／最多 54 scored calls；0 retry、不可續跑。
完成後先獨立提交 raw artifact，才建匿名封包、鎖定開發者代理標註、
後揭盲與核 Git 時序／正式評分。若有 partial、品質或 20 秒成本失敗，
照原門檻保存負結果，不改 freeze/gold/runner 追分。元件結果不外推成
產品、Safari、真人、時間 holdout 或完整人類反應方程式證明。

**2026-10-01 模型前 freeze 紀錄（已履行，不是目前命令）：**
`8b5e7a8972b27402342596d5fe18064795b7a452`，PR #435 仍 open 且 head
對應此 full SHA。新契約 39/39、相鄰隔離回歸 93/93，0 新 scored calls；
無關 `output/graduate_application_report/` 未納入提交。此 commit 只是
前瞻設計／資料／評分契約凍結，不是模型或產品效果。當時下一必要交付是
一次性 runner、raw Git 證據 verifier 與 arm-masked annotation harness 的
模型前假傳輸驗證；此 gate 已由本卡頂部所列 commit 與前檢履行。
舊 M46 20-call FAIL 不重跑。

**2026-09-30 freeze 前設計紀錄（已履行，不是目前命令）：** 新的 18 題 source-only
中／英／日（各 3 action／3 abstain）與獨立 developer-authored gold、
A=M51→M52→M46 原始兩階段觀測重建、B=單次 typed transaction 的 raw-stage
觀測重建、共同守門與 scorer 已準備。B 的拒絕理由要求事前 source/target/
forbidden 錨點；A 舊布林 reason 覆蓋另報，不把它無法表達的類別當 B 優勢。
18×2 的 action/abstain 都須綁同一 raw commit；token、wall、request 與
response 身份也在 digest 內。固定 `solve_regulation` 非 protected 是**隔離元件
fixture**，不能當正式 Web route 證據。M45.1 原版 source filter 的獨立測試
與會安裝 M49 overlay 的相鄰產品回歸分兩個 Python 程序，防片段 ID 漂移。

本 freeze 的模型前離線測試：新四檔 `39 passed`、相鄰舊測試 `93 passed`，
均 0 模型呼叫；命令與 gate 見
`research/p4_action_transaction_v1_plan_2026-09-30.md`。原 M46 正式 20 calls
的 FAIL 不重跑；產品 M51/M52/M46/M45/M39、正式 DB、原始 dirty checkout 與
無關 `output/graduate_application_report/` 不碰。當時的下一動作是先提交
prospective freeze 並記 full SHA；此步已完成，後續以本卡頂部的 runner／evidence
gate 為準。
新 dataset／prompt／gold／scorer 一經 freeze 不改；若出現凍結缺陷且尚未送模型，
須保留 amendment 與新的 full SHA。元件分數不外推到 Safari、真人或產品。

**非獨立架構設計審查已完成，尚未實作或送新模型。** 見
`analysis/p4_m46_two_stage_architecture_design_review_2026-09-30.md`。在前兩次
reviewer 契約均 FAIL、M51 兩候選於 360 token 截斷、Safari 第二次審核 timeout、
P4-BE raw→typed packet 僅 1/6 完整通過的 before 下，選定下一個**整體架構變因**：
用一次來源綁定、單候選、含 task／禁令／actor／前提／effect／stop 證據的 typed
action transaction，加上只核可機驗證欄位的 deterministic guard，與現行兩階段
M51→M52→M46 同題比較。此設計不是第三次 reviewer prompt 小修、不是直接
移除 guard，也不把模型自附證據當語義真理。若缺真工具 receipt，不得聲稱助手
替使用者操作；產品路徑與正式記憶維持不變。

**下一必要交付：先事前凍結新 source-only 中／英／日案例與事前獨立於輸出的
task／禁令／actor／內容／日文／abstain gold、完整 A/B 拓撲契約、同模型／硬體／
總 token 上限、0 retry／單次呼叫、品質＋完整 `≤20s` 成本 gate、精確離線測試及
失敗分支。** 原 M46／P4-BE 題都已曝光，只作回歸。先做設計資料／scorer／
0-call tests 並 commit freeze，記 full SHA；再寫一次性 runner／fake transport tests
另 commit，前檢後才可送新的 scored calls。若 new B 沒有 valid 全保留、invalid
零錯放與 wrong-task／actor 原因辨別，或以全拒換安全、超時，即保留 FAIL；
即使元件通過仍需全新自然生成、private runtime／Safari 多輪與真人／holdout
分層驗收，不能先接產品。允許新研究計畫、config、dataset、離線 scorer/tests、
本卡及後續 runner／結果；不許改已凍結結果／gold、現有產品 M51/M52/M46/M45/M39、
正式 DB、原始 dirty checkout 或無關 `output/graduate_application_report/`。

### 本次 M46 失敗結果（保存歷史，不是目前的執行命令）

**2026-09-30 正式一次性結果為 `review_required_component_fail`，不得重跑、改題、改 gold 或追認 PASS。**
模型前 freeze=`7abf74579e7793c22d3111b149037d9d7bdc5393`，
runner=`0b1dcfcaa63f9ea5af51f5c95cfca94482925848`。本機 9B、同一選定方案、
兩審核介面各 10 題，20/20 呼叫完成且 JSON／tokens／source exact、0 retry；
另 1 guard control 兩臂 0 call 阻擋。A 原版 valid=`2/3`、invalid false action=`2/7`、
舊欄位映射理由=`5/7`、reviewer-only 中位／最大=`13.60179/14.72437s`；
B 新版 valid=`0/3`、false action=`0/7`、明確預定錯誤軸＋primary 理由=`0/7`、
中位／最大=`8.64255/10.78069s`。B 將全部 10 個方案判 `actor_capability=fail`，
9/10 以此為 primary；加速只是全部拒絕，沒有品質改善資格。兩臂都未通過絕對
品質 gate；B 不可接產品，既有 M51/M46/M45/M39 不改、不旁通。原始結果與反例
見 `analysis/p4_m46_decision_interface_result_2026-09-30.json`、
`analysis/p4_m46_decision_interface_failure_2026-09-30.md`。此證據只限 developer-authored
固定封包元件，不是自然生成、完整 20 秒 runtime、Safari、真人／正式 holdout、
強 LLM 優勢或人類方程式。

當時的下一交付是兩階段架構設計審查，而非第三次 reviewer prompt／gold／timeout
小修；現已完成並列於本卡頂部。正式 M55/M56 真人與 temporal holdout 依賴
仍未解除。無關 `output/graduate_application_report/` 保留不碰。

### 前瞻 freeze 與模型前狀態（保存歷史，不是目前命令）

**2026-09-30 freeze 準備已完成，尚未送新模型。** 研究計畫
`research/p4_m46_decision_interface_plan_2026-09-30.md`、
`configs/p4_m46_decision_interface_v1.json`、
`datasets/p4_m46_decision_interface_v1.json`、
`p4_m46_decision_interface_scoring.py` 與兩份 0-call tests 已齊。
新字串但已曝光類型的 developer proxy：10 個可交審封包（3 valid／7 invalid，
中英日）＋1 個共同 guard control；10/10 selector/source/M39 exact 可交審、
control 的原 guard violation=`nonprogress_or_unknown_mechanism`，0 scored calls。
新舊同一 selected plan，唯一變因是單次 review prompt＋schema 的判斷介面；
同一 9B／320 completion token cap、最多 20 review calls、0 retry。
`uncertain` 必須 fail closed 且不計為明確辨出錯誤；`evidence_jp` 的 quote
只是逐字來源錨點，axis-label hit 不等於引文語義充分或真人理由品質。
離線命令
`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_m46_decision_interface_freeze.py test_p4_m46_decision_interface_scoring.py test_p4_m46_fixed_challenge_discrimination_result.py test_p4_m46_fixed_challenge_discrimination_freeze.py test_goal_progress_delivery_m46.py test_state_changing_candidates_m51.py test_candidate_realization_m52.py test_source_neutral_scaffold_m53.py test_p4_av_neutral_operational_role_authorization.py`
=`77 passed`（模型前 amendment 後）。**當時先提交 freeze amendment 並記 full SHA，再新增一次性 runner／fake
transport tests、提交第二個 commit，才送唯一 scored calls；這些步驟已完成。** 未達元件絕對
品質／成本 gate 即保留 FAIL、停止 reviewer 小修；即便通過仍須新自然生成與
full runtime／Safari，不能接產品。產品 M46/M45/M39 不改、不旁通。無關
`output/graduate_application_report/` 保留不碰。

**模型前 freeze amendment：** 首次 freeze commit=`fa298078a47900c1963c252cf62875dc036cb711`，
其後獨立只讀稽核發現 B 允許引用英文 source、parser 卻拒 ASCII 引文，以及
3 個 valid 的 `〜てみよ` 口語 gold 歧義。新 scored calls 仍為 `0`，已在
`research/p4_m46_decision_interface_plan_2026-09-30.md` 記錄並只修 exact
source／instruction quote 的原語豁免（外圍仍需日文）、selected instruction 的
`〜てみて` 口語表面、相應 fake tests／hash；source、機制、gold label／預定錯誤軸、
模型及 gate 不變。修後相鄰離線測試=`77 passed`。當時已提交 amendment，並用其 full SHA
取代 runner 所綁的舊 freeze SHA；沒有用原 SHA 混過前檢。

### 此前設計審查與 before（保存歷史）

2026-09-30 的**非獨立設計審查已完成**：
`analysis/p4_m46_reviewer_decision_interface_design_review_2026-09-30.md`。
它沒有新的模型、產品或真人結果。舊固定封包 FAIL 不變；中文有效案的 `止めよ`
可能是 gold／口語標準歧義，英文有效案疑似把使用者手邊可查的材料誤當未知前提，
actor/surface 負例則漏判助理代操作。選定唯一下一架構變因為**同一 9B、同候選、
同前後 guard 與 320-token cap 下的 M46 單次 review decision interface**；原產品 M46
不動。這不是逐字 prompt 追分，prompt+schema 是一個可歸因契約整體；若品質／成本仍
失敗，即審整個兩階段架構，不再對 reviewer 做第三次小修。

**下一必要交付：先事前凍結全新中／英／日完整封包、內容與日文表面分開的盲於 reviewer
gold、原／新契約、分類映射、score、模型與成本 gate；0 scored calls。** 新舊介面
對同一封包各唯一一次；明確 valid 全保留、invalid／uncertain 零錯放、每類命中原因、
JSON/source/tokens 完整、0 retry、逐案 wall/tokens；reviewer-only `≤20s` 仍不足以授權
完整產品，之後須全新自然生成與 private runtime／Safari 的完整 `≤20s`。不能用舊九題
作新分數、不能修改任何舊 gold／凍結結果或直接改產品。下一步允許新增 prospective
研究契約／dataset／scorer／離線 tests 並更新本卡；先 freeze commit，再新增一次性 runner
與 fake tests，runner commit 前不送模型。精確離線命令及最大 scored-call 數須寫入 freeze。

### 前一工作：固定辨別力 FAIL 與設計審查的 before（保存歷史）

**固定 challenge-only 正式結果為 `fixed_discrimination_fail`，不得重跑或追認 PASS。** 事前 freeze=`41bb4f02edf1bab392a001e0043eda4368d57144`、runner=`668be4b`，8/8 個本機 9B 審核完成、JSON／tokens／source identity 全部完整、0 retry、0 M51 generation、1 個 guard control 未送模型。A 保留有效行動僅 `1/3`（要求 `3/3`），無效行動錯放 `0/5`，但類別對應理由只辨出 `4/5`；B 是隔離的無審核反事實，錯放預構造負例 `5/5`，絕不授權旁通。reviewer-only wall 中位／最大=`13.210155/14.4233s`，prompt／completion=`6,568/2,304` tokens；不是完整產品 20 秒證據。結果與 runner/freeze 相關回歸=`41 passed`。逐案反例、原始結果、事前邊界見 `analysis/p4_m46_fixed_challenge_discrimination_failure_2026-09-30.md` 與同名 `.json`。原 M51 第一題 360-token 截斷的 A/B 消融仍是 `INCONCLUSIVE / NOT RUN`，不能合併兩實驗成成功鏈路。

**下一個必要交付是非獨立設計審查，而非再送模型或直接改產品。** 有效中文封包因 `casual_japanese=false` 被拒，該「止めよ」措辭也可能與 gold 的自然日文要求不一致；有效英文封包因 `no_unknown_prerequisites=false` 被拒；actor/surface 負例聲稱助手替使用者關面板，`no_identity_or_role_error` 卻仍為 true，靠無關旗標阻擋。先分清 gold／表面標準不一致、過度保守、行動者漏辨三種原因，選一個有成本與反例支持的架構變因；若再做 scored 實驗，必須用新 source／新 freeze、明確品質與成本 gate。產品 M46/M45/M39 維持 fail-closed，不旁通、不提高 timeout、不改已曝光封包／gold／門檻。正式 M55／M56 真人依賴仍未解除。

### 前一階段記錄（已完成或失敗，不是現在的執行命令）

**2026-09-30 正式生成於第一個 M51 call 即停，整個 A/B 消融為 `INCONCLUSIVE / NOT RUN`。** runner commit=`e3c1c11c2180d6c7f617e5ec72c7162f26744ee8`；前檢通過後唯一執行，prewarm成功，第一個 call 17.63697s、prompt/completion=`462/360`，輸出在第二候選字串中斷，`JSONDecodeError`；360 tokens 正好碰凍結上限。已產生0/6完整 batch、1/6 generation call、0 review、0 gold、0 retry，結果檔不可續跑／覆寫。詳細原始證據與設計分支見 `analysis/p4_m46_reviewer_necessity_generation_failure_2026-09-30.md`。**下一步是先保存此 FAIL／結果回歸，再做非獨立設計審查**：優先考慮新凍結的固定 challenge-only M46 辨別力測試（只證元件辨別、非自然生成），若有價值再以新 source 對 M51 表示／token 資源做單變因修正；不可改本次 num_predict、重跑剩餘五題、把手工封包冒充生成、直接旁通 reviewer 或接產品。P4-AZ／BA／BC／BD／BE 的既有 FAIL 不變；正式 M55／M56 仍待真人資料。

P4-BE `REVIEW_REQUIRED` 設計審查已作出**非獨立**處置：目前 raw dialogue→typed-spec 自動路徑不接產品，P4-BB 的條件式 compiler 與 BC／BD／BE 失敗證據保留，不再用第三個小 prompt／gold 修正追分。理由、互斥替代方案與限制見 `analysis/p4_be_review_required_disposition_2026-09-29.md`。這不是上游能力 PASS 或產品交付，亦不撤銷 P4-BA/BC/BD/BE 的 FAIL。

下一個對使用者可見交付的最早瓶頸是：P4-AZ Safari 真實兩輪已把 source 與 M51 候選接好，M46 第二次 model review timeout，M45/M39 fail closed、沒有交付動作；P4-BA 同資料模型大小 2×2 的完整 action 全部 `0/2`，小 reviewer 又退化 always-reject。現在先定案**review stage 是否值得其品質／成本**的單一變因，不能直接旁通 reviewer 或拉長 timeout。依前述設計處置，下一卡要凍結全新隔離中／英／日 action cases、valid 與 wrong-task／unsupported specificity／private-inference／non-action／surface controls、相同 M51 frozen generator packet、A=既有 M46 review、B=相同 deterministic guards 但無 model review、事前獨立品質標註、嚴格 false-action／valid-retention／token／latency gate 及失敗分支。兩 arm 重放相同一次 generator 輸出，僅比較 reviewer 貢獻；B 若放錯行動不能因快而接產品。此設計不是完整強 LLM baseline，也不是人評。

**事前歷史快照，不是現在的執行命令：** freeze=`2d522885b939cdb9a3dfd6d8bf4a2786527b6f31`、runner=`e3c1c11c2180d6c7f617e5ec72c7162f26744ee8`。before、單一變因、同候選兩臂、來源與品質標註次序、模型 digest／硬體／tokens／20 秒產品 gate、0 retry、最多 20 scored calls 與所有 FAIL 分支已寫入 `research/p4_m46_reviewer_necessity_plan_2026-09-30.md` 和 `configs/p4_m46_reviewer_necessity_v1.json`。`datasets/p4_m46_reviewer_necessity_v1.json` 封存 6 個全新中英日 source-only generation cases + 9 個 hand-authored challenge packets；後者是辨別力控制，不是假裝 M51 自然生成。離線 scorer 只重放同一候選到 A=既有 review／B=共用 deterministic guards，B 不接產品；M39 是隔離的 final-surface 近似而非完整 M45。3 個 valid 與 5 個 reviewer challenge 均可進入共同 guard，1 個 guard control 兩臂先擋，沒有事後挑題。runner 增加兩階段固定路徑、freeze/model/硬體前檢、唯一生成與 review、生成 packet 與 blind gold 分開提交後才能 review、逐 call checkpoint／0 retry／partial no resume，評分後出錯亦保存已完成 call。相鄰離線命令 `PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_m46_reviewer_necessity_runner.py test_p4_m46_reviewer_necessity_scoring.py test_p4_m46_reviewer_necessity_freeze.py test_goal_progress_delivery_m46.py test_state_changing_candidates_m51.py test_candidate_realization_m52.py test_source_neutral_scaffold_m53.py test_p4_av_neutral_operational_role_authorization.py` = `66 passed`；當時尚0 model calls／0 product changes。事前流程要求先唯一生成、commit packet、blind-to-review 標註且 commit，再送 eligible A reviews；本次於第一步即失敗，因此後續階段未執行。若離線合格原仍需全新 private runtime／Safari 檢查自然日文、實際圖、source、durability、latency；本次沒有取得該資格。不改正式 BC–BE 凍結檔／結果、M51/M46/M45/M39 產品 runtime、記憶、人格或原始 dirty checkout，不架外部 server、不碰無關 `output/graduate_application_report/`。

## P4-BE 正式 FAIL 與 REVIEW_REQUIRED（保存歷史）

### 已封存的 P4-BE 正式結果（不得重跑、改題、改 gold 或追認 PASS）

P4-BE freeze=`90b4c4af2583f37a43997f9662485e81584fae04`、runner=`93938c6ed8d27393a24274cc62d5b5ff12d49751`。本機 `qwen3.5:9b` 對同一批 6 positive＋8 controls，以 P4-BC 原 prompt／P4-BE 新 prompt 各唯一執行一次：`28/28` scored calls 完成且 JSON 可解析、`0` retry、tokens 完整、controls `8/8`／`8/8`、false spec/source `0`。同題 paired BE-only full pass=`1`、BC-only=`0`、source identity 合法的 BE-only raw role/value uplift=`1`，但候選的**絕對門檻失敗**：typed=`5/6`、non-span=`3/6`、role/value evidence=`2/6`、完整 packet=`1/6`、normalized atoms=`11/18`、slots=`3/6`、compile／mechanism／自然日文各=`3/6`、full accept=`1/6`（均須 `6/6`，atoms須`18/18`）。原 prompt full accept=`0/6`、compile=`6/6`；局部一案改善不抵銷退步。新／原 prompt tokens=`16,843/12,811`、median call=`10.47381/10.11207s`，max=`16.079/15.32578s`。候選沒有選用，產品 runtime 未改。正式證據與逐案限制見 `analysis/p4_be_role_value_prompt_evidence_2026-09-29.json`、`analysis/p4_be_role_value_prompt_failure_2026-09-29.md`，結果回歸見 `test_p4_be_role_value_result.py`。

P4-BD 與 P4-BE 已是這條上游路徑的兩個有根據修正批次。**下一個必要交付是設計審查，不是第三個 prompt／gold 微調，也不是直接接產品**：用中文 request 漏「只給一個／現在」而新 prompt 修好，以及新 prompt 中文混入日文 slot、英文漏 `unknown_constraint_jp`／編造 literal `...`、日文把回答形式誤當任務完成限制這些最小反例，先選定一個可歸因的能力變因及成本。選項是 source-bound 結構化角色／條件表示與獨立驗證、只修 canonical 日文 slot materializer（不解 evidence）、或縮小六模板路徑並保留 fail-closed。若變更研究問題、baseline、資料、門檻或重大架構，需明確設計審查／凍結後才可實作；已曝光 P4-BD／BE 題只能作回歸，不能充當新 holdout。成功與失敗都須有實際前後例、成本、單元→fresh model→runtime/Safari 分層證據。P4-BE 收尾只允許本次正式 evidence／失敗報告／immutable 結果回歸與本卡；收尾後只可新增獨立設計審查與更新本卡，未取得設計結論前不送新的 scored model calls。原始 dirty checkout、正式私有資料、無關 `output/graduate_application_report/`、已凍結檔及外部部署均不碰。Codex Goal 不因本卡 `REVIEW_REQUIRED` 而標為 complete／blocked。

### P4-BE 事前設計與凍結（保存歷史；下述「下一步」均已執行，不是當前命令）

### Before：P4-BD 正式 FAIL，禁止重跑或回填金標

P4-BD freeze=`26fb89821d7d1b846ff3d83aa4209f8ecd8384e8`、runner=`b6362cd`；9B／4B 對各14個全新開發案例唯一執行，28/28完成、JSON／tokens完整、0 retry。兩模型 role-aware evidence／packet 都=`0/6`，normalized accepted atoms=`5/18`、`2/18`；strict single-gold仍各=`0/6`。9B positive normalized/non-span/downstream=`5/6`，4B=`5/6,4/6,4/6`；controls unavailable＋reason均=`8/8`、false spec/source violation=`0`、max=`15.05412/9.38962s`，但任何一個 failed positive gate 都不能被成本／control 通過抵銷。產品 runtime 未改、無 selected model。正式證據和限制見 `analysis/p4_bd_role_aware_evidence_failure_2026-09-29.md`；結果回歸是 `test_p4_bd_role_aware_result.py`。P4-BD 與 P4-BC 原題、契約、gold、prompt、runner及結果不得修補或重跑；P4-BD 題也成為 exposed development，非 holdout。

P4-BD 兩種不同原因必須保留：一部分是事前列舉 span 過窄的可能假陰性（例如 `我那疊收據`），另一部分是真正錯目標／錯條件／漏完成限制／source 翻譯（例如4B日文分頁 role 錯、英文 evidence=`会議メモ`）；兩個 invalid packet 還漏 `unknown_constraint_jp`。不能把全部失敗解釋成標註，也不能靠任何 source substring 放行。P4-BD 的 `18/18` hard-negative scorer 單測只是 evaluator 契約證據，不是產品能力。

### 事前選定的單一變因與設計 gate

P4-BE 是此上游問題**第二個、最後一個有根據修正批次**，只改 raw dialogue→typed spec producer 的「source-bound evidence 角色／值擷取」系統 prompt；不得同時移動 `unknown_constraint_jp`／canonical Japanese slots 到 deterministic materializer、改 P4-BB compiler、M51/M46/M45/M39、產品模型、公開 persona、回覆或記憶。只讀審查已比較 prompt-only、source offset／ID、template regex parser，選 prompt-only：依六模板既有語義保留 owner／predicate／肯否／quantity／completion，不加入新題字面例子。source offset 只能防非來源片段，不能防錯角色；regex 會把六題變硬編碼。審查見 `analysis/p4_be_source_bound_role_prompt_design_review_2026-09-29.md`，屬非獨立開發審查，不是人評。這只是最後一次有界修正，不宣稱 prompt 是最終認知架構。

下一步事前凍結**未曝光**的新 cases、source／role 語意 gold、hard negatives、比較 arm、prompt/schema、模型與硬體／token／latency 上限及成功／失敗門檻；新評測在同一批新 cases 用相同 evaluator 比較 frozen P4-BC producer prompt 與 P4-BE prompt，不得以不同題目分數當改進。只測 `qwen3.5:9b`，`2 prompts × 14 cases=28` 次 scored calls、0 retry；這不授權 4B 選型。若仍由開發者標註，標 `developer-authored proxy`；多解歧義必須在模型輸出前處理。先離線 scorer／negative mutations、fake transport，再 commit freeze 與 runner，才可唯一一次正式生成。未凍結前=0 scored calls。結果若仍不達事前完整 gate，保留 FAIL，提出最小反例與 `REVIEW_REQUIRED` 架構取捨，不再換下一個小編號追分。產品 Safari／圖像與正式研究層仍 pending，不因離線 runner 成功升格。

### 2026-09-29 P4-BE 事前凍結準備（歷史時點為 0 scored model calls）

已準備 `configs/p4_be_role_value_prompt_v1.json`／`.txt`、`datasets/p4_be_role_value_prompt_v1.json`、`p4_be_role_value_scoring.py`、`test_p4_be_role_value_freeze.py`、`test_p4_be_role_value_scoring.py` 及設計審查。新 source 與 BB/BC/BD 全文逐字無交集，六個 positive 逐模板且中／英／日各2，八 controls 理由各1；仍是固定 ontology 下的開發 proxy。對每個 role 凍結一個原文 window 和完整 target／predicate／quantity／completion anchors，18 個 source-exact hard-negative mutants 及6個 window 內漏關鍵 anchor 反例必須被擋；quote 邊界只作診斷而不作 gate，避免重犯 BD 的有限 alias 問題，但語法不自然的 anchor-complete 片段可能通過。兩 arm 同一 scorer 與資料，唯一 producer 變因是 P4-BC prompt evidence 指示變得 role/value 完整。`unknown_constraint_jp` 等完整 slots 仍由模型負責，漏填即 FAIL。

候選 9B 必須 positive typed／non-span／template／role-value evidence／full packet／slots／downstream compile／mechanism／自然日文各6/6、accepted atoms18/18，controls unavailable＋reason各8/8、false spec/source violation0、JSON14/14、tokens完整、max call≤20s；要說 prompt 帶來額外價值還須 paired BE-only full pass≥1、BC-only full pass=0，且至少一案 BC raw role/value FAIL→BE raw role/value PASS、兩 arm source identity 均合法，避免把 slot 修好誤稱 evidence 進步。兩 arm 均須 completed／parseable 才可解釋成對比較；baseline 其他 gate 與成本照報、不作 BE eligibility。strict single-gold與實際tokens／latency逐案照報。前置合格不接產品；正式結果若仍 FAIL，停止小修小補而輸出 `REVIEW_REQUIRED`。

先跑凍結與相鄰離線測試，成功後 commit freeze、記 full SHA；**不能先寫／執行正式 runner**。凍結後不可改 dataset、anchors、prompt、schema、scorer、gates、模型或成本上限。之後只能新增一次性 runner／fake tests（先 commit）與 evidence/result test/report/本卡。正式 preflight 應核 freeze SHA、hash、9B digest、M2 Pro 32GB、既有本機 Ollama、固定輸出不存在；prewarm 失敗不送 scored calls，每 arm/case唯一一次、0 retry，partial 不可續跑。精確離線命令：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_be_role_value_freeze.py test_p4_be_role_value_scoring.py test_p4_bd_role_aware_freeze.py test_p4_bd_role_aware_scoring.py test_p4_bd_role_aware_runner.py test_p4_bd_role_aware_result.py test_p4_bb_typed_action_compiler_freeze.py test_p4_bb_typed_action_compiler.py test_p4_bc_raw_dialogue_typed_spec_freeze.py test_p4_bc_raw_dialogue_typed_spec_harness.py test_p4_bc_raw_dialogue_typed_spec_result.py
```

目前允許修改：本卡、P4-BE 設計審查與 prospective dataset／contract／scorer／tests／一次性 runner，均須按 freeze→runner→結果分階段；不得改動 P4-BB／BC／BD frozen 路徑與原始 dirty checkout。只讀設計審查及 freeze 離線測試已完成；下一步先 commit freeze、再寫 runner，不得在 runner commit 前跑模型。P4-BD 收尾驗證命令：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_bd_role_aware_freeze.py test_p4_bd_role_aware_scoring.py test_p4_bd_role_aware_runner.py test_p4_bd_role_aware_result.py test_p4_bb_typed_action_compiler_freeze.py test_p4_bb_typed_action_compiler.py test_p4_bc_raw_dialogue_typed_spec_freeze.py test_p4_bc_raw_dialogue_typed_spec_harness.py test_p4_bc_raw_dialogue_typed_spec_result.py
```

## P4-BD role-aware evidence span evaluation：已凍結與失敗（保存歷史）

### 2026-09-29 模型呼叫前的設計／凍結紀錄（歷史時點）

Before 仍是下述 P4-BC 正式 FAIL；本卡唯一變因是**evidence span 的評分契約**。P4-BD 新增 6 個 developer-authored positive（繁中／英／日各 2、六 template 各 1）及 8 個不同 unavailable reason controls；與 BB/BC 完整 source 逐字無交集，但固定 ontology 語義重疊，**不是獨立 holdout**。每個 positive 的 3 個 role 有事前 exact-source candidate、hard negative 與 conservative `accepted_exact_spans`。兩次分開的 LLM-proxy 判斷在 54 個二元 label 中同意 `48/54`、完整 role-set `12/18`；六個分歧候選在模型輸出前全部從可接受集合排除。這不是兩位真人的 inter-rater reliability。原始判斷與非獨立設計審查見 `analysis/p4_bd_annotation_proxy_pre_freeze_2026-09-29.json`、`analysis/p4_bd_role_aware_design_review_2026-09-29.md`。

Freeze 檔限 `configs/p4_bd_role_aware_evidence_v1.json`、`datasets/p4_bd_role_aware_evidence_v1.json`、`datasets/p4_bd_span_annotation_candidates_v1.json`、上述兩份 analysis、`p4_bd_role_aware_scoring.py`、`test_p4_bd_role_aware_freeze.py`、`test_p4_bd_role_aware_scoring.py` 與本卡。先執行精確離線命令：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q -p no:cacheprovider test_p4_bd_role_aware_freeze.py test_p4_bd_role_aware_scoring.py test_p4_bb_typed_action_compiler_freeze.py test_p4_bb_typed_action_compiler.py test_p4_bc_raw_dialogue_typed_spec_freeze.py test_p4_bc_raw_dialogue_typed_spec_harness.py test_p4_bc_raw_dialogue_typed_spec_result.py
```

已在 2026-09-29 的 freeze 準備版得到 `66 passed`、0 模型呼叫，之後完成 freeze commit `26fb898`。凍結後任何新題、gold、accepted span、prompt/schema、門檻及模型條件均不可改。runner 與其 tests 在正式呼叫前另 commit `b6362cd`，正式後沒有改 runner。

P4-BD eligibility 的事前數值：每模型 14 案，JSON `14/14`，6 positive 的 normalized typed／非 span exact／template／role-aware evidence／role-aware 完整 packet／canonical slots／P4-BB compile／mechanism／自然日文均 `6/6`；8 controls 的 unavailable＋reason `8/8`，false spec／source violation `0`，token accounting 完整，max scored call `≤20s`。原 strict single-gold exact evidence/spec **仍逐案和總數報告，但不作新的放行 gate**；這是本卡唯一評分邊界變更，否則 role-aware 即使正確也會被整包 equality 強制判 FAIL。仍保留 9B／4B、原 BC prompt/schema／full slots／compiler、M2 Pro 32GB、temperature `0`、seed `20260927`、`num_ctx=4096`、`num_predict=480`、固定順序各一次 prewarm、0 retry。最多 `28` scored calls；任一必要 gate 不過即該模型 FAIL，不接產品。若兩者過才按 median latency 再 completion tokens 選。

正式 runner 的 preflight 要核對 freeze SHA、所有 hash、模型 digest、硬體、Ollama 服務與新 evidence path 不存在；prewarm 失敗不送 scored calls，逐案 checkpoint，但 partial result 一律 FAIL 且不可續跑。P4-BC 舊正式題與 runner 不重跑／不覆寫。模型輸出之前不進 Safari 或正式 DB；P4-BD 結果只能是 bounded offline evidence，真實 Web、建議效果、強 LLM 優勢及人類方程式仍 pending。

P4-BC已依freeze=`1424f24`、runner=`4045947`唯一執行28 calls，正式 **FAIL**，不得重跑或改原gate。28/28 completed、JSON parse成功、token完整。9B的template／slots／downstream compile／mechanism／自然日文=`6/6`，controls unavailable=`8/8`，但gold-boundary exact evidence=`0/6`、control reason=`7/8`、max=`21.71181s`；4B controls reason=`8/8`且max／median=`14.39932/9.32895s`，但positive normalized／compile=`5/6`，日文atomic raw output雖選對template，漏掉required `unknown_constraint_jp`而fail closed。兩者false control spec=`0`，產品runtime未改。完整證據：`analysis/p4_bc_raw_dialogue_typed_spec_failure_2026-09-27.md`。

重要診斷：兩模型12組positive evidence atoms的required role set都正確，atom也全是原source exact substring，但與唯一gold邊界逐字不同，所以formal exact=`0/6`。部分是明顯合理的短／長span（`空白` vs `還是空白`、`收據` vs `桌上的收據`），部分仍可能角色不精確（`email` vs `subject`）。因此不能把P4-BC洗成PASS，也不能只要substring就算對。

P4-BD唯一變因是**evidence span評價**。P4-BC只作exposed development；用完全新raw-dialogue cases，在模型執行前為每個role凍結一組acceptable exact spans、允許的containment關係與語意改變的hard negatives。template、full slots、controls、9B/4B、prompt/schema、硬體、0 retry與20秒gate保持；不得同時把canonical slots移進deterministic compiler。正式判定同時報strict single-gold exact與role-aware score，前者不刪除。

先設計annotation contract與inter-annotation consistency proxy（至少兩組獨立規則標註或可重現雙標註；若沒有獨立人類只能稱developer-authored），commit freeze後才可新跑。若role-aware仍失敗，保留semantic grounding缺口；若通過，只能說span evaluator不再懲罰預先承認的等價邊界，不能直接接產品。canonical slot responsibility另留下一卡。

## P4-BC raw dialogue typed spec freeze 與結果（保存歷史，不是當前下一步）

P4-BB 已在 freeze commit=`a4dd116` 後 0 correction 一次完整 **PASS**：繁中／英文／日文 6 positive 覆蓋 M46 六種 allowed progress mechanism；compiled／exact expected plan／M46 structural／source exact／mechanism exact／自然日文／deterministic repeat 全為`6/6`。12 個 identity／provenance／schema／language／safety／unsupported controls 依預定原因 blocked=`12/12`，false plan=`0`。model call／raw dialogue trace／factual memory write=`0/0/0`，最大 compile=`0.00090479s`。產品 runtime 未改。完整證據：`analysis/p4_bb_typed_action_compiler_acceptance_2026-09-27.md`。

P4-BB 真正證明的是：**若**已有正確且授權的 source-bound typed task spec，下游 action plan 可以不用模型自由猜 mechanism，並可 deterministic、source-exact、自然日文、fail-closed 地形成。它沒有證明 raw dialogue 能正確產生 spec，也不能和 P4-BA 的 raw-source 兩階段時間直接相除；模板 coverage 只有六種 bounded action ontology。

下一個單一未證明邊界是 P4-BC：`new raw dialogue → source-bound typed task spec`。先事前凍結完全新的繁中／英文／日文 positive 與 ambiguous／unsupported／risky／third-party／private-inference controls；P4-BB cases只能作 exposed development，不得當formal。比較`qwen3.5:9b`與`qwen3.5:4b`在相同 schema、資料、硬體、temperature、seed、token上限與0 retry下，能否選對 template、複製exact source identity/span、擷取exact evidence atoms、產生合法日文slots，且unsupported輸出`unavailable`。

P4-BC gate 必須同時含 typed-spec exactness、P4-BB downstream exact compile、positive coverage、negative rejection、private/assistant source=`0`、完整tokens與單一model-call latency `<=20s`。任一模型只有全部通過才可作後續 integration候選；都失敗就保留負結果，不改產品。先commit P4-BB結果，再freeze P4-BC dataset／contract／tests；不得先改M51/M46/M45/M39或接Safari。

P4-BC freeze 已準備：6 個完全新positive（繁中／英文／日文各2，逐一覆蓋六個P4-BB template）與8個ambiguous／third-party／medical／financial／unsupported／no-action／quoted-meta／private-state controls；P4-BB來源逐字交集=`0`。9B與4B各對14案只呼叫一次，共28個scored calls，模型固定順序各prewarm一次且不計case latency；prompt、dynamic schema、case order、硬體、temperature=`0`、seed=`20260927`、num_ctx／num_predict與0 retry完全相同。

每個模型只有JSON=`14/14`、positive typed／exact spec／template／evidence／slots／downstream compile／mechanism／日文=`6/6`、controls unavailable＋reason=`8/8`、false spec與assistant/private source=`0`、tokens完整、max call `<=20s`才eligible。先commit本freeze後才實作一次性runner；任一近似答案、compiler僥倖可編譯或另一模型較好都不能洗掉該模型的failed gates。

## P4-BB typed action compiler freeze 與結果（保存歷史，不是當前下一步）

P4-BA 已依事前凍結的 2×2 配置各唯一執行一次，正式 **FAIL**，不得重跑或在結果後改 gate。20 個 scored model calls 全部 completed、JSON 可解析、token accounting 完整，所以這次不是 transport failure。四個 arm 都不具產品資格：`g9_r9` 的 generation structural／allowed mechanism=`1/2,0/2`、review fixture=`3/4`、full accept=`0/2`、max=`35.71618s`；`g9_r08`=`1/2,0/2,2/4,0/2,22.22539s`；`g4_r9`=`0/2,0/2,3/4,0/2,29.86752s`；`g4_r08` 雖唯一通過 latency（max=`16.78266s`），但品質為`0/2,0/2,2/4,0/2`。

兩個 generator 在兩案都選 `group_by_rule`，allowed mechanism=`0/2`；0.8B reviewer 接受=`0/4`，退化成 always-reject；9B reviewer 的 report relabel content checks 全通過，只因 surface flag 拒絕，不能證明真正辨別 task progress。exact source、自然日文、0 raw dialogue trace、0 factual-memory write仍保持。產品 runtime 未改。完整證據：`analysis/p4_ba_stage_model_allocation_failure_2026-09-26.md`。

這否定的只有「單靠較小的 stage model allocation 可同時保住既有品質與 20 秒成本」；不是人評、自然分布、強 LLM 比較、人類方程式或所有小模型的結論。

下一個單一架構變因是 P4-BB **typed action compiler boundary**。先事前凍結新 dataset／contract：deterministic 層只根據已授權 source、task kind 與明列 allowed mechanisms 產生可審計 slots；模型不能自行發明 mechanism，只能填寫或實現允許欄位。semantic progress 與 persona-surface 分開記分，但任一失敗仍 fail closed；unknown task 必須保持 uncovered，不得硬套模板。P4-BA cases只能作 exposed development，正式需全新中／英／日 action cases與 false-source／unsupported-task controls。

P4-BB freeze 已準備為 6 個全新 positive（繁中／英文／日文各 2，覆蓋 M46 六種 allowed mechanism）與 12 個 identity／provenance／schema／language／safety／unsupported controls。正式 gate 是 exact expected plan、M46 structural、source／mechanism exact、自然日文、deterministic repeat=`6/6`；controls blocked＋reason=`12/12`、false plan=`0`；model call／raw dialogue trace／factual memory write=`0`；max compile `<=0.01s`。

本卡只證明「already-authorized typed task spec → bounded action plan」；raw dialogue 如何形成正確 task spec 明確不在本卡。先 commit 這份 freeze，再只新增 `uruha_typed_action_compiler_p4.py` 與結果測試／證據；不得先改產品M51/M46/M45/M39或runtime model。即使offline全通過，也只授權另凍結 upstream typed-spec producer 測試，不直接授權 Safari 或產品接線。

## P4-BA stage allocation freeze 與結果（保存歷史，不是當前下一步）

P4-AZ real pair 已唯一執行並正式 **FAIL**，但把最早因果缺口往後推進：P4-AY 找到 1 個response-form／feedback ref、0 個genuine replacement task並只停在prior role；P4-AZ=`authorized_previous_turn_cjk_ellipsis`，source role仍為`unspecified`且0 rewrite；P4-AU=`prior_source_linked`，新增`prior:1` digest與T1 exact相同，assistant/private source=`0/0`。P4-AV/M53 integrity、graph ordering、2/2自然日文、2/2 durable、isolated Chroma=`2`均通過。

完整pair仍FAIL：M51生成2個候選、1個structurally valid；第一個model call完成`876+300` tokens，第二個M46 counterfactual review `TimeoutError`，M46=`counterfactual_review_unavailable`、M45 withheld、M39 fail closed，再次澄清而沒有交付動作。T1/T2=`3.507/38.1682s`，僅1/2達20秒門檻。正式pair不得重跑。完整證據：`analysis/p4_az_real_previous_turn_ellipsis_to_action_delivery_failure_2026-09-26.md`，result commit=`7a280c8`。

這個review timeout亦已在P4-AT、P4-AW、P4-AZ三個fresh Safari pair重現；不再把它當偶發錯誤，也不直接拉長產品timeout。P4-BA只回答一個資源配置問題：相同frozen M51 prompt/schema、M46 checks/schema、資料、硬體、temperature、seed與token上限下，generator=`qwen3.5:9b/4b`、reviewer=`qwen3.5:9b/0.8b`的2×2配置，是否有任一組同時保持generation structural validity、review positive/negative discrimination、full-pipeline acceptance與每案two-stage `<=20s`。

允許新增：P4-BA frozen dataset/config、freeze test、一次性offline benchmark harness、result evidence/test/report，以及本節更新。不得先改產品runtime、M51/M46/M45/M39、prompt、schema、gate、資料或既有正式結果；每個unique model/case只執行一次，0 retry。generation output可在不同reviewer arm重用以維持factorial歸因；所有arm正負結果都保留。模型依`9b→4b→0.8b`各做一次不計分prewarm並維持`30m`，prewarm耗時另記，避免把不同cold-load順序混入stage latency。

正式gate：generation JSON、selected structurally-valid及case-specific allowed progress mechanism=`2/2`；四個fixed reviewer fixture=`4/4`，不可always-true；full pipeline source exact、自然日文、M46 content/surface accept=`2/2`；raw dialogue trace／factual memory write=`0/0`；token accounting完整；各案two-stage最大`<=20s`。任何arm只有全部gate通過才可作後續產品整合候選；多組通過取median latency最低，其次completion tokens最少。全部失敗就產出負結果，不改runtime，下一步依失敗分支重設架構而非追分。

先完成freeze commit，再實作harness並跑唯一一次四arm評測；這只是development-only本機模型配置證據，不是人評、建議有效、自然分布、強LLM優勢或人類方程式。

## P4-AZ offline 與 real freeze 保存歷史（不是當前下一步）

P4-AZ於`ad2ca9b`事前凍結，只修exact previous-turn中文省略第一人稱的prior-source authority，0 correction一次通過完整offline gate：development=`1/1`；全新繁中／簡中positive authorized與exact source linked=`6/6`，deterministic fake-M45 downstream structural contract=`6/6`；third-party／quoted-meta／news-report／physical-object／resolved／hypothetical controls=`12/12` blocked且false source=`0`；P4-AY predecessor source=`6/6` preserved。target source role仍為`unspecified`=`7/7`，沒有改寫成明示第一人稱；exact feedback chain與typed trigger=`7/7`。

P4-AY task mutation、P4-AU non-role bypass、candidate/order、visible reply、新增model、factual memory、assistant/private source、raw trace、完整fresh字串patch=`0`。聚焦與相鄰回歸=`42 passed`；port `7891` sandbox preflight=`ready`且0 model／Safari／VRM-tool operation。這只證明frozen deterministic source-authority接線，fake downstream不是live建議品質。完整證據：`analysis/p4_az_previous_turn_cjk_ellipsis_authority_acceptance_2026-09-26.md`。

下一步先commit本offline結果，再事前凍結**完全新的**兩輪private runtime／Safari pair，不得重用P4-AX正式句。T1需建立subjectless Chinese exact executed `calibrate_need`；T2需為全新compound support＋response-form request，並分別通過P4-AX、P4-AY、P4-AZ、P4-AU exact source、P4-AV/M53、M46/M45/M39 visible immediate action。timeout、JSON parse failure、再澄清、generic promise、只有internal plan、缺席node都FAIL；須記錄日文、durability、graph、tokens、latency與0 assistant/private source。正式pair PASS也只是一條fresh product path，不是建議有效、人評、人類方程式或強LLM優勢。

## P4-AY offline 結果與 P4-AZ 來源（保存歷史，不是當前下一步）

P4-AY 於`5735fc9`事前凍結，只區分「同一問題的feedback／response-form constraint」與「真的換了問題」。完整 frozen gate 為 **FAIL**：development=`0/1`，全新中／英／日positive=`6/6`、controls=`12/12`、genuine topic replacement=`3/3` blocked、既有P4-AU positive links=`6/6` preserved。第一次實作 fresh=`5/6` 且predecessor統計錯算，唯一 correction 只補日文肯定語尾`だった`與already-present source計數；沒有改資料／gate／中文來源角色。

失敗原因已收斂到下一個既有guard：P4-AX正式T1的中文句省略第一人稱，M39 source role=`unspecified`；P4-AY證明T2沒有新task後，P4-AU仍以`prior_source_not_direct_user_first_person`阻擋。P4-AY保持`blocked_non_task_p4_au_guard`，沒有繞過它。P4-AX authority=`7/7` preserved；P4-AT mutation、P4-AU non-task bypass、candidate/order、visible reply、model、factual memory、assistant/private source、raw trace、完整fresh字串patch=`0`。聚焦與相鄰回歸=`33 passed`；port `7890` sandbox preflight=`ready`且0 model／Safari／VRM-tool operation。完整證據：`analysis/p4_ay_response_form_constraint_boundary_failure_2026-09-26.md`。

P4-AZ唯一能力變因是exact previous-turn CJK省略第一人稱的prior-source authority。只在typed cognitive-overactivity、direct current-user frame、無第三人／引用／report、exact earlier executed M44/P4-AT chain、P4-AX supported、P4-AY所有current refs已授權時，允許上一輪source role仍誠實保持`unspecified`但作為exact prior problem來源。先事前凍結新的中／日正例與third-party、meta、news/report、physical-object、resolved、ambiguous controls；不得改P4-AY task boundary、P4-AU其他guard、M45/M46/M39、prompt、model、memory、visible reply或本次獨立`JSONDecodeError`。offline通過後仍需全新Safari pair。

## P4-AX real 結果與 P4-AY 來源（保存歷史，不是當前下一步）

P4-AX implementation=`33fd460`、real pair freeze=`7d2bf25`。全新的兩輪 private runtime／Safari pair 已在 port `7889` 各唯一執行一次，完整正式結果為 **FAIL**，不得重跑、改題或改 gate。

新能力的真實產品邊界確實通過：T2 的 P4-AX=`bounded_support_composed`，把對 exact 上一輪澄清的支持與本輪 `solve_regulation/practical_help` request 分開；P4-AT=`closed_supported`、P4-AG previous resolution=`supported`，prediction id 精確相同。P4-AX node `66` 位於 P4-AT/P4-AG/temporal/utterance `67/68/69/70` 前；P4-AX predecessor mutation、P4-AU bypass、新增 model／factual memory／raw trace 都是 0。

完整 pair 的最早失敗是 P4-AU 把「給我一個步驟、能馬上開始、完成就停止」誤判成新的 independent task source，得到 `blocked_current_task_replacement`；雖核對到 T1 digest=`4ebe80e6d582690d`，但沒有加入 prior source。P4-AV/M53 因未到達不能計為 pass。另有獨立 downstream failure：M45 一次完整 model call 回傳非契約資料而 `JSONDecodeError`，M51 未執行、M46=`plan_unavailable`、M39 對 `practical_action_not_delivered_m45` fail closed。T1/T2 latency=`3.776/31.0372s`，calls=`1/1`，tokens=`1001+360`但 accounting incomplete。2/2 自然日文、2/2 durable、isolated Chroma=`2`、2/2 graph；Safari 展開 P4-AX/P4-AU/M45，0 tab 關閉。完整證據：`analysis/p4_ax_real_compound_feedback_to_action_delivery_failure_2026-09-26.md`。

P4-AY 唯一能力變因是：在 P4-AU 裡區分**本輪真正換了問題／主題**，與**只約束回答形式或動作形狀**。後者例如「一個步驟／立即開始／完成即停」，不應遮掉 exact 上一輪 problem source；前者仍必須 fail closed。先事前凍結全新中／英／日 positive response-form constraints，以及 genuine topic replacement、third-party、quoted/meta、receipt mismatch、非 practical policy 等 controls。不得改 P4-AT outcome、receipt identity、direct-user authority、M45/M46/M39、prompt、model call、memory、visible reply，亦不得同時修本次 `JSONDecodeError`。offline 通過後仍需全新的 Safari pair；本次正式 FAIL 永久保留。

## P4-AX offline 與 real freeze 保存歷史（不是當前下一步）

P4-AX於`4bd1664`事前凍結，只修同一當輪同時含有「明示支持exact上一輪澄清」與「本輪新的practical-help request」的bounded
compositional split。第一次實作為development=`0/1`、fresh positive=`9/9`、controls=`10/12`、predecessor=`6/6`，已保存；唯一informed
correction只讓offline harness傳入真實產品已有的M25 base-request trace，並修日文第三人稱報告與CJK hypothetical guard，不改資料／gate／
positive grammar／P4-AT結果／request routing／P4-AU／M46-M45／prompt／model／memory／visible reply。

修後development=`1/1`；全新中／英／日response-kind confirmation、need-direction clarification、pre-answer need-clarity=`9/9`；third-party／
quoted-meta／generic-confirmation／hypothetical controls=`12/12` unknown；既有P4-AT question support=`6/6` core exact保留。16個支持案例均為
exact receipt且current policy=`solve_regulation`；false support、predecessor mutation、P4-AU bypass、candidate rerank、visible change、model、
factual memory、raw trace、private truth、完整fresh字串patch=`0`。focused=`13 passed`、P4-AT～AX affected=`74 passed`；port `7888`
sandbox preflight=`ready`、0 model／Safari／VRM-tool operation。完整證據：
`analysis/p4_ax_compound_feedback_request_split_acceptance_2026-09-26.md`。

該階段後續要求是先commit本offline結果，再事前凍結**完全新的**兩輪private runtime／Safari pair；此要求已由上節的正式結果完成並封存。原 gate 要求為：T1需建立exact executed `calibrate_need`；T2使用未曝光
三語任一compound support＋request，必須P4-AX node在P4-AT/P4-AG/temporal前、P4-AT=`closed_supported`、P4-AU加入exact T1 source，並由既有
M51/M52/M53/P4-AV/M46/M45/M39真正交付可立即開始且有停止條件的日文action。timeout、再澄清、generic promise、只有internal plan均FAIL；
不能用P4-AW正式pair重跑。本offline PASS不改寫P4-AW real FAIL，也不保證後段model review會成功。

## P4-AW real 結果與 P4-AX 來源（保存歷史，不是當前下一步）

P4-AW offline結果、實作與事前凍結pair分別固定於`a0e8c4a`、`8487644`、`acb562e`。新的private runtime／Safari兩輪已在
port `7887`各唯一執行一次，完整正式結果為 **FAIL**，不得重跑或改gate。

T1新能力確實進入真實產品：中文省略第一人稱時，P4-AW=`authorized_current_user_ellipsis`且source role誠實保留`unspecified`；
P4-AS=`executed_and_committed`、M44 exact receipt=`p1-1-6c5f453019d919e9`、P4-AR authorized、P4-AG六候選與future lock均通過。
P4-AW沒有改source frame／trigger detector／候選排序／feedback／P1-P4-AR guard／visible reply，新增model／factual memory／raw trace／
private truth=`0/0/0/0`。這是P4-AW的real-product bounded PASS，不是完整pair PASS。

T2同時暴露兩個獨立失敗。最早是複合句`你剛才先確認我需要什麼是對的；現在給我…`沒有被拆成「支持前輪action」與「本輪新request」：
P4-AT=`closed_unknown`、`two_independent_acts=false`，P4-AU因`earlier_action_not_explicitly_supported`沒有加入T1 prior source。後段仍辨識
`solve_regulation/practical_help`並由M51產生2個不同且structurally valid=`2/2`候選、M52 realized=`2/2`；但兩次model operation只有一次完成，
第二次`TimeoutError`，M46=`counterfactual_review_unavailable`、M45=`withheld_model_unavailable`，M39對
`practical_action_not_delivered_m45` fail closed，最後又澄清而未交付動作。T1/T2 latency=`3.8869/38.1546s`；model attempted/completed=
`2/1`，已記錄tokens=`546+272`但accounting不完整。2/2自然日文、2/2 durable、isolated Chroma=`2`、2/2 graph；Safari展開AW、AT、AU、
AV、M45節點，0 tab關閉。另T1 logic有P4-AG exact binding，但blackboard沒有獨立P4-AG node，所以凍結ordering gate也誠實FAIL。

下一個單一能力變因只修**同一當輪同時含有對上一行動的明示支持，以及新的practical-help request**的bounded compositional split。
先把本次句子降為exposed development，另凍結全新的中／英／日正例與false-link controls；不得改receipt identity、current request routing、
候選排序、M46/M45 review與fail-closed、visible reply、prompt或記憶。修後本題只能作regression，仍需全新Safari pair。完整證據：
`analysis/p4_aw_real_cjk_ellipsis_to_action_delivery_failure_2026-09-26.md`。

## P4-AW offline 與 freeze 保存歷史（不是當前下一步）

P4-AW 只修 CJK 省略第一人稱時的 executed-action authority。契約於 `a0e8c4a` 先凍結；第一次實作只達 development=`0/1`、
fresh positive=`4/6`，但 controls=`12/12`、明示第一人稱 predecessor=`2/2`，失敗已保存。唯一 informed correction 只把 upstream 已有的
typed `cognitive_overactivity` compose 到 copied shadow state，不改 detector／資料／gate。修後 development=`1/1`、全新中／日文
subjectless positive=`6/6`、third-party／quoted-meta／news-report／physical-object／resolved／ambiguous-role control=`12/12` blocked、
explicit predecessor=`2/2` preserved；typed trigger與完整 P4-AS→P4-AR exact chain=`7/7`，false authority=`0`。source frame／detector／
P1-P4-AR guard／candidate order／feedback／visible reply／model／memory／raw trace／private truth／完整fresh字串patch變更皆=`0`。
focused=`15 passed`，affected total=`74 passed`（P4-AW 15＋predecessor/adjacent 59）；port `7886` sandbox preflight=`ready`，
0 model／Safari／VRM-tool operation。完整證據：
`analysis/p4_aw_cjk_subject_ellipsis_action_authority_acceptance_2026-09-26.md`。

這只證明 frozen CJK grammar 的 deterministic authority bridge；P4-AV 舊 Safari FAIL 不改寫。下一步須先 commit 本 offline 結果，再凍結
**完全新的**兩輪 private runtime／Safari pair，T1 是未曝光 subjectless direct-user cognitive-overactivity，必須 P4-AW final、P4-AS executed、
M44/P1/P4-AR/P4-AG exact、future locked；T2 才能驗 P4-AT support、P4-AU exact prior-source handoff、P4-AV neutral role、M53/M46/M45/M39
真正 visible practical action。題目、gate、port與no-retry先commit；generic promise、再澄清、timeout、只有internal plan都算FAIL。

## P4-AU 正式結果已凍結；P4-AV／P4-AW 的來源（保存歷史，不是當前下一步）

P4-AU offline freeze與修正後固定結果通過：development=`1/1`、全新中／英／日positive source handoff=`6/6`、9個false-link control正確阻擋=`9/9`，
deterministic fake M45 downstream structural contract=`6/6`，predecessor mutation／candidate order／新增model／factual memory／assistant或private來源／raw trace=`0`；
相鄰回歸=`85 passed`。它只把exact previous-user problem接到本輪action delivery，沒有放寬M45/M46/M53/M39。

`9c33ccc`事前凍結的全新中文private runtime／Safari兩輪已於port `7884`唯一執行，正式 **FAIL**，不得重跑、改題或改gate。前半整鏈通過：
T1 executed `calibrate_need`、exact M44 receipt=`p1-1-c47bcaefa644b5b4`、P4-AG六候選與future lock；T2 P4-AT=`closed_supported`，並把當輪
新要求分開判定為`solve_regulation/practical_help`。P4-AU=`prior_source_linked`，`prior:1` digest=`e0fcdf502c58532a`與T1 exact user source相同，
assistant/private fallback=`0/0`、raw trace／新增model／factual memory=`0/0/0`。P4-AU node index=`50`，在M50/M53/M46/M45/utterance
`51/55/56/57/69`前；Safari已展開核對。2/2自然日文、2/2 durable episode、isolated Chroma=`2`。

正式交付仍失敗：M45一次model call產生2個不同候選，但structurally valid=`0/2`；選中候選含2個quoted scaffold labels，M53判定
exact source=`0`、neutral role=`0`、unsupported=`2`，觸發`unsupported_concrete_scaffold_label_m53`。因此M46=`plan_rejected`、
M45=`withheld_goal_plan_failed`、M39對`practical_action_not_delivered_m45` fail closed，最後再次詢問而沒有交付立即步驟。凍結failed gates為
M45 delivery、M46 verified/content/surface、M39 practical act與generic clarification prohibition；T2=`711+288` tokens、`20.7275s`。
這證明exact跨輪來源接通與真正source-safe action delivery是不同gate；前者通過、後者失敗，不能宣稱felt understanding、人類方程式或強LLM優勢。
完整證據：`analysis/p4_au_real_source_bound_current_action_delivery_failure_2026-09-26.md`。

P4-AV唯一能力變因是**區分中性操作角色標籤與自行發明的具體主題分類**。P4-AU正式題只能作exposed development，不得重跑。先事前凍結
M53 development反例、新的中／英／日source-neutral operational-role positives，以及invented topical categories、hidden-priority／emotion／diagnosis labels、
source-quoted labels與unquoted controls。只允許對來源無關且不聲稱內容真值的操作角色做typed authorization；任意`「環境」「經濟」「社會」`或
`「重要」「不重要」`等具體分類仍須阻擋。不得改plan文字、M46 review、M45/M39 gate、候選分數／排序、prompt、model call、記憶或visible reply。
offline通過並commit後，才能凍結完全新的real Safari兩輪；PASS仍只證明一條source-safe action delivery產品路徑，不證明建議對真人有用。

P4-AV已於`3c5437d`事前freeze後0 correction一次通過offline：development=`1/1`；新的中／英／日source-neutral workflow-role
positive=`6/6`且predecessor M53原本全阻擋；invented topic／priority／emotion／diagnosis／preference／feasibility／attribute controls=`7/7`
仍阻擋；exact-source／existing-neutral／unquoted predecessor controls=`3/3`保持。plan mutation、candidate rerank、新增model、factual memory、
raw label trace、M46 bypass、M45/M39 weakening、visible reply及完整題字串patch=`0`。聚焦與相鄰回歸=`56 passed`；port `7885` sandbox
product preflight=`ready`、0 model／Safari operation。完整證據：
`analysis/p4_av_neutral_operational_role_authorization_acceptance_2026-09-26.md`。

P4-AV實作commit=`83ea808`。另於`2fdfbdd`事前凍結**完全新的**兩輪private runtime／Safari case，port `7885`正式執行在T1即 **FAIL**
並停止，T2未送、同題不得重跑。T1可見日文`ん、寝てないのか、考え事で止まんないのか、まずそこだけどっち？`確實執行澄清，M39=
`accepted_verified_surface`且policy act=`true→true`；但中文省略第一人稱使source frame=`unspecified`，P4-AS因`early_authority_exact`與
`direct_user_first_person`失敗為`not_applicable`，M44=`not_registered`，P4-AR=`blocked_unexecuted_shadow_action`。雖P4-AG仍有六個shadow
候選，temporal正確顯示current candidates=`0`、future=`not_available`。P4-AS／P4-AR／P4-AG／temporal／utterance index=
`64/65/66/68/69`，Safari已展開P4-AS節點；1輪自然日文／durable／graph=`1/1/1`、latency=`3.0913s`、0 model call。
P4-AV／M53未到達，所以不能把本次寫成P4-AV產品效果。完整證據：
`analysis/p4_av_real_neutral_operational_role_delivery_failure_2026-09-26.md`。

P4-AW唯一能力變因是**CJK省略第一人稱時的executed-action authority**。P4-AV正式T1只能作exposed development，不得重跑。先凍結新的中／日
主詞省略direct-user cognitive-overactivity正例，以及third-party、quoted／metalinguistic、news/report、physical-object motion、resolved-state與
ambiguous-role controls；只能在existing typed trigger、direct source、third_party=false、M39已驗證可見`calibrate_need`、exact P1 pending與plan identity
均成立時，將`unspecified`視為本輪direct-user ellipsis，不得把一般無主詞句都升成user-first-person。不得改trigger detector、candidate ranking、P1/P4-AR
guard、feedback、visible reply、prompt、model call、記憶或private truth。offline通過並commit後，P4-AV仍需另一組全新Safari pair。

原P4-AV real gate要求如下，保存作為失敗邊界：正式gate仍須
同時通過P4-AS→AT→AU exact來源鏈、P4-AV node在M53/M46/M45/utterance前、M53不阻擋中性workflow role、M46 content/surface verified、
M45 delivered、M39 practical act與自然日文／durable graph；generic promise、再澄清、model unavailable或只有internal plan都算FAIL。即使PASS也
只證明一條產品action-delivery path，不是建議有用的人評、自然分布、強LLM優勢或人類方程式。

## P4-AT 正式結果已凍結；P4-AU 的來源依據（保存歷史，不是當前下一步）

P4-AT offline在事前freeze後通過：17案的上一個action outcome與本輪request policy=`17/17`、development=`1/1`、全新中／英／日
positive=`9/9`、false-prior-link controls=`0/7`、unrelated unknown=`3/3`、exact receipt identity=`17/17`，候選分數／排序、model call、
factual memory與raw dialogue leakage變更=`0`。P4-AT只把上一輪observable action feedback與本輪response request分開，不改P4-AG classifier、
P1 identity、M44 truth、候選排名或visible reply；實作commit=`a1600e2`，相鄰回歸=`51 passed`。

另於`f2d1ecd`事前凍結完全新的中文兩輪private runtime／Safari case，port `7883`唯一一次正式執行為 **FAIL**，不得重跑、改題或改gate。
真正的因果閉環通過：T1以`calibrate_need`建立exact M44 receipt、P4-AG六候選與future commitment；T2把使用者支持精確綁回同一
`p1-1-54b3425d01de0b33`事件，P4-AT=`closed_supported`、M44/P4-AG=`supported`，並把當輪新要求另外辨識為
`solve_regulation/practical_help`。performed action strictly-earlier、prior future consumed、same-turn backdating=`true/true/false`；P4-AT／P4-AG／
temporal／utterance graph index=`66/67/68/69`，Safari可見；2/2自然日文、2/2 durable episode、P4-AT新增model/factual memory=`0/0`。

凍結的T2 action-act gate失敗：候選表面原為`今すぐできる一個だけ、一緒に決めよ。`，沒有真正交付步驟；M45嘗試兩次、完成一次model call後
`TimeoutError`，成為`withheld_model_unavailable`，M46=`counterfactual_review_unavailable`。M39因此對
`practical_action_not_delivered_m45` fail closed，最後可見為`今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。`；
T2 latency=`37.9706s`，高於20秒。唯一failed gate=`turn_2_m39_practical_act_count`。這證明「理解前一個行動的回饋」、「辨識現在要什麼」與
「真的做出現在要的行動」是三個不同gate；前兩個通過、第三個失敗，不能宣稱felt understanding、人類方程式或強LLM優勢。完整證據：
`analysis/p4_at_real_executed_action_outcome_closure_failure_2026-09-26.md`。

P4-AU唯一能力變因是**把剛才問題的source-bound context接給本輪明示action request**，不是放寬M39/M45或把timeout當成功。P4-AT正式兩輪已曝光，
只能作before/development，不能重跑。先事前凍結新的中／英／日兩輪：T1需有direct first-person problem context與真正executed receipt；T2需同時
包含exact action feedback與明示`practical_help` request。只有exact receipt identity、strict next-turn window、direct first-person ownership且本輪沒有
observable topic correction時，才可把T1的最小source atoms交給既有M45/M46；不得把persona推測、內部candidate、第三人稱、引用、過期或跨題內容當source。
fresh positive必須實際產生一個source-consistent、自然日文、可立即執行的步驟；controls需涵蓋topic correction、unrelated feedback、third-party、
receipt mismatch與timeout，全部fail closed。不得改P4-AT outcome、P4-AG/M44、候選分數、M39 action-act gate、語言guard、prompt、記憶真值或把 generic
promise-to-help算實際action。先freeze／commit，再offline implementation與回歸；只有另凍結全新real Safari兩輪後才能主張一條產品action delivery閉環。

P4-AU已完成offline freeze與實作。第一批凍結測試失敗保留：fresh positive=`4/6`、control正確阻擋=`6/9`；根因是日文省略主詞、M47 ref未切細、
metalinguistic predecessor guard未compose，以及expired fixture改了會被M44重算的衍生欄位。唯一一次informed correction不改題／gate／prompt／M39／M45，
只compose既有P4-AT direct-source guard、細分ref、為無third-party/meta的日文direct user turn處理主詞省略，並讓fixture真正改authoritative created turn。
修後development=`1/1`、全新中／英／日source linked與exact identity=`6/6`，九個third-party／meta／unrelated／new-task／identity／window／no-feedback／
wrong-policy／oversize controls誤加=`0/9`且block reason=`9/9`；六個positive以fake generation/review通過既有M45 structural contract=`6/6`，但這不是
live model品質或人評。候選score/order、predecessor source、model call、factual memory、assistant/private-inference source、raw trace變更=`0`；相鄰回歸
=`84 passed`，sandbox product preflight=`ready`。完整證據：`analysis/p4_au_source_bound_current_action_delivery_acceptance_2026-09-26.md`。

P4-AU唯一下一步是另commit本offline結果後，事前凍結**完全新的**private runtime／Safari兩輪，不得使用P4-AT或P4-AU任何已曝光句子。正式gate需同時看：
T1真正executed `calibrate_need`與exact receipt；T2 P4-AT支持閉環、P4-AU exact prior source handoff、M45/M46實際交付一個source-consistent且可立即開始的日文步驟、
M39 action-act match、P4-AU node在M50/M45/utterance前、2/2 durable與日文、實際model call/token/latency。timeout、generic promise、再問一次或只有內部policy正確都算FAIL；
即使PASS也只是一條fresh產品閉環，不等於人評、自然泛化、人類方程式或強LLM優勢。

## P4-AS／P4-AT 保存歷史（不是當前下一步）

P4-AS已完成offline、產品接線、開發Safari及正式one-shot驗收。offline prospective gate=`13/13`：development=`1/1`、
全新中／英／日positive=`6/6`、third-party／metalinguistic／resolved／ordinary-motion controls=`6/6`，M39 surface、M44 receipt、
product pending及P4-AR authority=`7/7`，false execution／role violation／新增model／factual memory=`0`。第一次開發Safari保留一個真實
FAIL：產品已先建立exact P1 pending，但P4-AS誤要求pending必須為空，所以receipt缺失、P4-AR阻擋。唯一一次informed correction只允許
pending absent或prediction/policy/turn/input全部exact；exact pending與ledger逐字保留，只補missing receipt，mismatch仍fail closed。
修正後全新開發Safari通過，完整正負證據保存在`analysis/p4_as_product_development_*_2026-09-25.*`。

實作commit=`81e6ba6`後另於`83bcb2c`事前凍結全新中文private runtime／Safari題，port `7882`唯一一次正式執行為 **FAIL**，不得重跑或改gate。
真正機制鏈通過：P4-AS=`executed_and_committed`、M39=`accepted_verified_surface`、M44 exact receipt、P4-AR=
`authorized_executed_product_event`、六候選pending、P1 sequence=`1`、temporal=`過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`；
Safari展開P4-AS／P4-AR／temporal，graph index=`65/66/67`均在utterance `69`前，logic→runtime exact，日文／durable embedding=`1/1`，
latency=`3.216s`，P4-AS新增model/factual memory=`0/0`。但凍結要求逐字
`今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？`，實際為
`しんどくて止まらないのと、楽しみで止まらないの、今はどっち寄り？`；兩句都實現`calibrate_need`，但exact surface=`0/1`，所以正式
failed gates=`turn:visible_reply`,`metric_mismatch:exact_visible_reply_count`。這證明action-level因果正確與逐字可重現是不同主張，不能用前者
洗掉後者FAIL。完整結果：`analysis/p4_as_real_selected_action_surface_execution_failure_2026-09-25.md`。

P4-AT唯一能力目標是**已執行行動的下一輪因果閉環**，不是追逐P4-AS逐字答案。先以P4-AS正式題作已曝光development，只讀驗證其M44 receipt
可被下一輪observable feedback精確連結；不得重跑該正式輸入。再事前凍結全新的兩輪中／英／日序列，至少包含：使用者確認要方法、確認只想被聽、
否定兩個選項／轉向其他需求，以及無關訊息保持unknown。T1必須有released visible `calibrate_need`、exact M44/P1/binding；T2必須把支持／否定／
未知綁回同一performed action，將T1 commitment從future移入strictly-earlier past，並在需要時撤銷或換policy，unknown不得算成功。表面驗收以事前固定的
action-act rubric與M39 observable surface contract為準，另記exact string但不把單一措辭混同理解；不得改P4-AG classifier、P1 identity、M44 outcome、
候選分數、語言guard、prompt或記憶真值。offline通過並commit後，才能另凍結完全新的private runtime／Safari兩輪；即使PASS也只證明一條
action→feedback→calibration產品閉環，不等於使用者偏好、人評、自然分布、人類方程式或強LLM優勢。

## P4-AS／P4-AR 保存歷史（不是當前下一步）

P4-AR在重新檢查產品因果語意後，沒有把P4-AQ的fallback硬升成P1 identity：P4-AQ所選`calibrate_need`只存在於late shadow，
released M18 decision仍是`not_applied`，M44 action receipt是`not_registered`，可見回覆也沒有執行澄清。若直接簽P1事件，下一輪會把
使用者反應錯誤歸因給未曾顯示的行動。P4-AR因此改為**executed-action authority gate**：只有existing desired decision、applied
decision／plan、exact product pending及registered receipt全部綁同一真正P1事件與policy時才允許outcome verification；fallback不能升P1，
P1 guard不降低。

offline freeze／implementation與相鄰P4-AD～AR回歸=`144 passed`。事前另凍結一個全新English one-turn private runtime／Safari case，
唯一一次正式執行為 **PASS**：P4-AQ先`0→6`候選並選`calibrate_need`；P4-AR正確得到
`blocked_unexecuted_shadow_action`，保留6個候選供查看，但current binding=`not_available/0`、temporal=`過去 0｜現在 0候選/選択 なし｜
本輪未來 無承諾`，fallback→P1=`0`。graph index為guard/order/binding/temporal/utterance=`64/65/66/67/68`，四個logic→graph
payload exact且Safari可展開guard；日文／durable episode／graph=`1/1`，等待`17.6066s`，P4-AR新增model／factual memory=`0/0`。
完整證據：`analysis/p4_ar_real_executed_action_identity_gate_acceptance_2026-09-25.md`。

這個PASS只證明**不替未執行的內部候選造假後續驗證**。可見回覆
`うちの頭は考えで埋まって今夜落ち着かないんだね。`雖為日文，卻把使用者第一人稱誤成角色的`うちの頭`，也沒有真的執行
`calibrate_need`；因此不是felt understanding、語意忠實、使用者偏好、預測正確、人類方程式或強LLM優勢證據。

P4-AS下一個唯一能力變因是**selected-action surface execution**。先把P4-AR已曝光case當development反例，不重跑正式題；再事前凍結
新的中／英／日cognitive-overactivity正例與speaker-ownership／resolved／literal controls。只有當P4-AF/AD已授權且選出一個bounded action，
才允許在M39之後以source-bound proposition與persona約束把該action實現為自然日文；`calibrate_need`必須是短、低壓、可否定的澄清，
不得把候選心理狀態說成事實。visible surface真的表達該policy後，M44才可登記exact executed receipt並由既有P1簽發下一輪事件；若surface
未表達、ownership錯、M39拒絕或receipt不一致，一律fail closed且不得建立future commitment。不得改AH detector、AF authority、AD候選
分數／排序、AG feedback classifier、P1 guard、記憶內容、persona facts或新增模型call。離線通過並commit後，才能另凍結全新real
Safari case；即使通過也只證明選擇→表達→receipt→可驗證事件的單一路徑，不等於使用者喜歡、預測正確或研究全面優勢。

P4-AM與P4-AN各保存一個不同的真實產品FAIL：P4-AM的temporal payload存在於logic但被最後一次blackboard refresh覆蓋；P4-AN已修好
post-turn delivery，Safari也能在utterance前看到節點，但全新P4-AH trigger在P4-AD／AF／AG之後才建立，因此當輪仍是0候選、無future
commitment。不得把「圖有顯示」改寫成認知整鏈通過。完整負結果：
`analysis/p4_am_real_runtime_temporal_graph_failure_2026-09-25.md`、
`analysis/p4_an_post_turn_temporal_graph_failure_2026-09-25.md`。

P4-AO改用舊M37已可達的全新三輪case，不改產品程式。第一輪真實Safari成功顯示`過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`，
但第二輪在P4-AG把真實`p1-2`事件放進每輪重建的sequence floor=0空白shadow時，被P1正確拒絕為跳號，正式 **FAIL** 並停止；不得重跑。
完整負結果：`analysis/p4_ao_reachable_temporal_graph_failure_2026-09-25.md`。

P4-AP只修classifier-only shadow的prediction identity continuity，不降低P1 guard、不複製product ledger。事前freeze後離線／相鄰回歸=`75 passed`；
唯一一次全新隔離Safari三輪正式 **PASS**：prediction sequence=`1→2→3`、shadow floor=`0→1→2`、identity-bound supported=`2/2`；三輪
past=`0→0→1`、present六候選=`3/3`、future locked=`3/3`、identity／temporal node均在utterance前=`3/3`、日文／durable episode／graph
=`3/3`，最大單輪`3.7837s`、總和`10.4651s`，新增model／factual memory／raw graph leakage=`0/0/0`。這只證明一條真實產品路徑能以
精確事件identity完成commit→next-turn verification→later-past promotion；不證明心理預測正確、人評、自然分布泛化、人類方程式或強LLM優勢。
另保留gate外觀察：T2/T3表面回覆相同，不能用mechanism PASS宣稱felt understanding。完整證據：
`analysis/p4_ap_shadow_identity_continuity_acceptance_2026-09-25.md`。

P4-AQ完成上述單一ordering修正：development=`1/1`、全新中／英／日base-M37-miss正例=`3/3`均由固定P4-AH命中並在同輪形成
六候選／typed authority／pending binding／locked future；六個literal／resolved／ordinary-motion controls=`6/6` abstain，候選排序、detector、
classifier、visible reply、model call、factual memory、source state與既有temporal/identity規則變更=`0`。P4-AD→AQ相鄰回歸=`104 passed`。

事前另凍結全新三輪private runtime／Safari case後執行唯一一次，正式 **FAIL** 並於第一輪停止。ordering本身在真實產品成功：0→6候選、
`calibrate_need`、typed `cognitive_overactivity`、pending binding、future locked；Safari可見P4-AQ節點與
`過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`，日文／durable episode／graph=`1/1`、latency=`17.2761s`、新增model／
factual memory／raw leakage=`0/0/0`。但released M18 decision仍為`not_applied`且無product prediction ID，P4-AG只可建立
`additive_shadow_identity` fallback；P4-AP正確拒絕把fallback冒充`p1-N`事件，因此identity node、sequence與floor均不存在。凍結三輪
identity gate已不可能通過，T2/T3未送出、同題不得重跑。可見日文`考えが湧き続けるのは無理だよ`也只過語言guard，語氣生硬，不能宣稱
felt understanding。完整負結果：`analysis/p4_aq_real_live_extended_trigger_ordering_failure_2026-09-25.md`。

P4-AR下一個唯一能力變因是**late-trigger product prediction identity bridge**。先用P4-AQ已曝光T1作before/development，不修改或重跑正式case；
再凍結新的中／英／日late-only離線正例與inactive／literal controls。修正必須讓「P4-AH後才成立的同一個corrected shadow decision」取得由既有
P1規則簽發、且與product model sequence floor一致的真正`p1-N-*`事件，再交給既有P4-AG/P4-AP；不得把fallback字串解析成sequence、手寫
`p1-*`、跳過P1 guard、複製已驗證ledger、改AH detector、AF authority、AD候選分數／排序、AG feedback classifier、temporal promotion、
visible reply、prompt、模型call或factual memory。離線須證明P4-AQ before為fallback／無identity，after為exact product P1 identity且control no-op；
通過後另凍結完全新的三輪private runtime／Safari case，P4-AQ輸入永不再用。即使P4-AR通過，也只證明一條late-trigger產品事件能跨輪保持
identity，不等於預測準確、被理解感、人類方程式或強LLM優勢。

P4-Z deterministic contract 已完成：development=`3/3`、全新 synthetic holdout=`9/9`、faithful no-op=`6/6`、
unsupported abstain=`3/3`，P4-M..Z=`247 passed`。它只支援 quote／hearsay／hypothetical 三種受限文法，不能寫成
open-domain semantics、felt understanding 或強 LLM 優勢。

P4-AA 依 freeze 在private root／port `7872`完成唯一一次四輪真實產品與 Safari 執行：4/4自然日文、4/4 durable
episode、supported exact=`3/3`、unsupported no-op=`1/1`、P4-T/V/W/Z logic→graph payload=`16/16`，最大單輪
`17.5013s`；P4-Z新增model call=`0`，既有semantic authorization實際本機model call=`4`。但是正式凍結 gate 必須保留
**FAIL**：合約把實際P4-V node `utterance_frame_coverage_extension_p4`誤寫為
`utterance_frame_shadow_extension_p4`，所以逐字 frozen surface chain=`0/4`。不得事後改 gate 或重跑同題；工程觀察不能
取代正式 PASS。完整負結果：`analysis/p4_aa_real_product_source_proposition_acceptance_2026-09-23.md`。

P4-AB已以additive entry完成：四種事前凍結trace摘要exact=`4/4`，payload mutation／raw token／reply／logic／detail／model／
memory change=`0`；P4-M→AB與M24 graph=`266 passed`。圖上訊號從`18 fields`變為「來源框架｜說話者歸屬｜已知命題欄位｜
動作｜違規數 before→after」，且能顯示repair failed-closed。核心renderer hash保持不變。第一次直接改核心時完整P4掃描的舊
immutable gate失敗已保存並改為additive entry；另發現branch既存P4-D product-entry hash mismatch，本次不修改也不宣稱repo全綠。
完整證據：`analysis/p4_ab_source_proposition_graph_summary_acceptance_2026-09-23.md`。

P4-AC已依freeze完成唯一一次private root／port `7873`真實產品與Safari兩輪：2/2自然日文、2/2 durable episode、2/2 graph與
P4-Z node；可讀摘要與同輪logic exact=`2/2`、canonical surface chain=`2/2`、generic `N fields`摘要=`0/2`。supported引用
exact=`1/1`，unsupported control誠實顯示「來源／歸屬未知、欄位無、保留原文」=`1/1`。最大單輪`16.5364s`、總和
`27.7068s`；P4-AB新增model/memory/tool call=`0/0/0`，既有semantic authorization實際本機model call=`2`、elapsed
`22.8006s`、token unavailable。P4-M→AC與M24 graph回歸=`273 passed`。完整證據：
`analysis/p4_ac_real_readable_graph_acceptance_2026-09-23.md`。Safari與server保留，0 tab關閉。

P4-AD已完成additive shadow ledger：它把observable evidence、六種response action candidates、選出的operational action、下一輪
support/contradict/unknown驗證與private reason unknown分開；action score明定不是心理真值機率，選擇也不是private truth commitment。
第一次事前凍結9題中／英／日validation只有`5/9`啟動，四個失敗雖都已有舊M37 `cognitive_overactivity` typed trigger，較舊語用層卻
未啟動。負結果完整保存。唯一一次informed correction不加關鍵詞、不改題／gate／舊M18/M54，只在additive shadow內接通既有typed
trigger；同組修復回歸=`9/9`、6個literal controls false positive=`0`、12/12 candidate contract，0 reply/model/memory change；
P4-M→AD與M24=`286 passed`。因為這9題答案已被用來決定修正，修後`9/9`只算exposed development regression，不能再稱獨立
holdout泛化。完整證據：`analysis/p4_ad_desired_response_ambiguity_acceptance_2026-09-23.md`。

P4-AE已在P4-AD修正固定後另建並commit六個全新中／英／日paraphrase與六個near-miss controls，再執行唯一一次。真ambiguity的
status／selected clarification／required candidates／private unknown均=`6/6`，但near-miss只有`5/6`，正式gate **FAIL**，0 retry／fallback。
反例`風扇一直轉，但我已經把報告寫完了。`被錯誤建立六個候選。靜態根因是舊`_explicit_atom_assignments`只要看到`報告`就建立
`task_pressure`，而`build_current_state`把任何explicit atom當成desired-response activation；它也沒有理解`已經…寫完`的completion。
這代表topic cue被誤當need signal，不是P4-AD cognitive-overactivity bridge的主體判定。完整負結果：
`analysis/p4_ae_fresh_ambiguity_generalization_failure_2026-09-23.md`。P4-AE關閉，不改同組追分。

P4-AF已把P4-AE反例降為development，並以additive guard只修**是否應建立desired-response ledger**的因果邊界；M18/P4-AD、
候選分數／排序、可見回覆、prompt、模型與記憶均不改。current-turn authority限於typed cognitive-overactivity、明示response-form、
bounded emotional/support signal或當輪matched verified trigger relation；task topic／task_pressure／domain不能單獨授權。結果為4個development
status/authority/action=`4/4`；6個fresh positive=`6/6`，6個fresh negative=`6/6`；8個eligible case候選policy/order/score保持
`8/8`，topic-only authorization=`0`，0 reply/model/memory change。P4-M→AF與M24=`304 passed`。完整證據：
`analysis/p4_af_desired_response_eligibility_acceptance_2026-09-23.md`。

P4-AG已凍結9條兩輪序列後執行；正式結果 **FAIL**。在7個有第一輪authorized ledger的序列中，prediction/ledger identity
binding=`7/7`，support selected=`3/3`，contradiction舊候選撤銷且明示replacement取得可撤銷權威=`2/2`，unknown誤算成功=`0`，
0 visible/model/factual-memory change。但兩個fresh first turn（日文`頭の中が回り続けて…`與英文`thoughts will not slow down…`）
在舊M37均為`no_bounded_observable_trigger`，所以整體first-turn eligible=`7/9`、正式gate不可寫PASS。完整負結果：
`analysis/p4_ag_multiturn_outcome_binding_failure_2026-09-24.md`。這兩題已曝光，只能作development regression。

P4-AH下一個單一能力變因是**multilingual observable-trigger coverage**，不得改P4-AG binding／feedback classifier／P4-AF authority或
可見回覆。先把兩個P4-AG upstream failure降為development，再凍結未看過的中／英／日compositional cognitive-overactivity正例與
literal／completed-task／ordinary-motion近鄰反例；修正必須是typed head+predicate composition或等價結構，不可只加兩句完整字串。
先證明trigger predicate與private-state boundary，0 candidate rerank／model／memory／visible change；通過後另開全新多輪集，才能驗證
P4-AH→AF→AG完整鏈，不能把P4-AG原fresh題修後重跑包裝成獨立泛化。

P4-AH已依freeze一次通過：兩個P4-AG曝光development=`2/2`、全新中／英／日compositional positive=`9/9`、ordinary object motion／
metalinguistic／resolved-state／physical-head control abstention=`12/12`；完整case字串寫入source=`0`，base M37 mutation=`0`，
private-truth claim=`0`，0 candidate／visible／model／memory change。它只證明有限developer-authored多語組合感知覆蓋，不回溯改寫
P4-AG FAIL；P4-M→AH與M24回歸=`317 passed`。完整證據：
`analysis/p4_ah_multilingual_trigger_coverage_acceptance_2026-09-24.md`。

P4-AI下一個單一驗收目標是**固定後的整鏈可達性**，不再改任何規則：事前凍結完全未出現在P4-AG／AH的全新中／英／日兩輪序列，
至少support、explicit contradiction+replacement、unrelated unknown各3條。每條必須依序有P4-AH typed trigger→P4-AF authority→P4-AD
六候選→P4-AG exact prediction/ledger binding→candidate outcome與reversible next-use；unknown不得算成功，contradiction不得保留舊候選
priority。只允許compose既有固定模組，不改detector／classifier／threshold／prompt／reply／memory。PASS仍只算synthetic chain contract，
之後才決定是否授權real product/Safari與visible reply planner接線。

P4-AI已依freeze做唯一一次、0 correction／retry，正式結果 **FAIL**：typed P4-AH path=`8/9`，但P4-AF authority／六候選／exact identity
binding／exact outcome均=`9/9`；support=`3/3`、contradiction+replacement=`3/3`、unknown=`3/3`、unknown誤算成功=`0`。失敗案日文
`止められなくて`沒有命中P4-AH固定的`止められない`終止形，雖被舊bounded-emotional路徑授權而得到正確outcome，仍不能冒充指定
因果路徑PASS。完整負結果：`analysis/p4_ai_fresh_ambiguity_learning_chain_failure_2026-09-24.md`。

P4-AJ下一個單一變因是**日文形態覆蓋**：把P4-AI漏判降為development，事前凍結新的否定／接續／口語活用正例與已平息、引用字詞、
身體動作近鄰反例；只能擴充typed predicate morphology，不得改P4-AI chain、P4-AF authority、feedback、候選或可見回覆。通過後仍需
再用完全新的P4-AK兩輪集確認整鏈；不可重跑P4-AI後宣稱獨立PASS。

P4-AJ已依freeze一次通過：P4-AI曝光miss=`1/1`、全新日文活用正例=`6/6`、已平息／引用／身體／物體controls abstain=`8/8`；
predecessor mutation／完整句patch／private truth claim=`0/0/0`，0 visible/model/memory change。它不回溯改寫P4-AI FAIL。完整證據：
`analysis/p4_aj_japanese_morphology_acceptance_2026-09-24.md`。

P4-AK下一步必須在P4-AJ固定後另凍結完全新的中／英／日兩輪序列，compose AH→AJ→AF→AD→AG，至少support／contradiction／unknown
各3條；不得再改任何detector、classifier或門檻。只有指定typed path、六候選、identity binding與outcome全通過，才可稱synthetic
end-to-end chain PASS；仍不等於Safari可見品質、自然分布、人評或強LLM優勢。

## 已完成的 P4 前置歷史

P4-S 已依事前 freeze 完成唯一一次真實 Safari 12 輪、兩 process lifecycle，failed gates=`0`。12/12 日文、12/12 durable
episode、12/12 graph；七個非寫入干擾誤寫=`0`，兩次答案不在 query 的 recall exact=`2/2`。真 restart 為 PID
`30321→30585`、session `20260922_183428_41a5a0e9→20260922_184133_5916e29d`，最終 profile 恰有 active drink/game、
historical drink、negative drink 各一筆。最慢一輪=`16.3151s`、總等待=`121.1807s`。product planner追加model call=`0`，但
一般語意授權另有9次本機模型call、provider elapsed=`86.457s`且token accounting unavailable；不得把它寫成零模型系統。
完整證據：`analysis/p4_s_real_product_multiturn_acceptance_2026-09-22.md`。

P4-S同時暴露4個凍結gate外的可見失敗：T4丟掉引用框架、T7把使用者第一人稱行為改成角色行為、T9把第三人稱傳聞陳述改成向對方
提問、T10完全誤解「將內嵌句視為假設」的指令；現有M39 verifier四次都接受。P4-T已把speaker ownership、embedding mode、
evidential stance、speech act分開，shadow gate在4個曝光development failure=`4/4`、12個事前凍結中／英／日failure=`12/12`、
8個faithful control false positive=`0`；24/24 visible candidate逐字不變，0 model/fact/profile/episode write，trace node位於utterance前。
第一次integration修改released product entry，正確觸發5個immutable-hash failure；最後修正改用`uruha_web_ui_product_p4_t.py` additive
entry，舊hash恢復，P4-M..T=`181/181 passed`。完整證據：
`analysis/p4_t_utterance_frame_shadow_acceptance_2026-09-22.md`。

P4-U先凍結「只有P4-T已報出frame violation才修表面」的單一變因；development前置條件=`4/4`，但12個新holdout只有`5/12`
得到凍結標註的P4-T violations，第一個repair prototype因此只有exact reply=`6/12`。差異是三個新user→agent動詞、一個英文
`The memo says`報告標記與三個hypothetical／frame-instruction缺口。若在P4-U再寫第二套分類器，會同時改detector與repair並破壞
凍結契約，所以在product integration前判FAIL：0 model／memory／product／Safari。12案已曝光，只能降為development；不得修完再稱
holdout。完整負結果：`analysis/p4_u_preimplementation_compatibility_failure_2026-09-22.md`。

P4-V以additive entry擴充P4-T，不改可見回覆、模型／prompt／memory或released hashes。結果為7個曝光development反例的
base/evidence/effective exact=`7/7`、9個新中／英／日holdout=`9/9`、9個faithful control false positive=`0`；25/25 candidate逐字
不變，0 raw source/reply trace、0 model/fact/profile/episode write。英文`Suppose I said ...`的舊quote false positive仍留在base trace，
但新effective frame正確撤銷，能看出判定被校正而非掩蓋。P4-M..V回歸=`200 passed`；第一次回歸命令因測試環境把不相容的
system transformers置於product peft前而collection error，改用system pytest＋product site-packages優先後完整通過，未安裝或修改
環境。完整證據：`analysis/p4_v_utterance_frame_coverage_extension_acceptance_2026-09-22.md`。

P4-W只在P4-V effective trace已有violation時修正可見日文，沒有violation嚴格no-op；不重做before分類、不改detector、模型／prompt／
memory或released hashes。4個曝光development與12個新中／英／日holdout的before／exact reply／after-zero全部通過，8個faithful control
逐字不變；24/24 Japanese、0 raw trace、0 model/fact/profile/episode write。graph順序固定為P4-T→P4-V→P4-W→utterance，P4-M..W
完整回歸=`212 passed`。這已證明有限developer-authored frame family的deterministic visible repair，但尚未證明真模型或Safari會走到它。
完整證據：`analysis/p4_w_frame_preserving_visible_repair_acceptance_2026-09-22.md`。

P4-X已依事前freeze在新private runtime／port `7870`完成唯一一次4輪Safari執行，原案例不得重跑。4/4日文、4/4 durable
episode、4/4 generic graph可見；三輪自然觸發P4-W，logic內P4-T／P4-V／P4-W均為4/4，branch consistency與visible digest均4/4，
但Safari graph的三種P4 node皆為`0/4`，凍結gate為FAIL。另有三個gate外語意反例：T1修復引用框架卻包住無關命題、T3恢復傳聞
卻漏掉`なくした`事件、T4保留假設卻把使用者的I改成角色`うちは`且未被偵測。完整負結果：
`analysis/p4_x_real_product_frame_repair_failure_2026-09-22.md`。

P4-Y只處理trace delivery：把已存在於同輪`logic`的P4-T／P4-V／P4-W資料送入最後一次blackboard refresh之後，不改可見回覆、
detector／repair、模型、prompt或memory。合成complete／stale duplicate／missing trace三案通過，visible與logic逐位元不變、exact payload
`8/8`、missing synthesized=`0`；P4-M..Y回歸=`227 passed`。另以兩個全新日／英prompt在private runtime、port `7871`與新Safari tab
完成唯一一次實機驗收：2/2日文、2/2 durable episode、2/2 graph，P4-T/V/W各2/2，logic→graph exact payload=`6/6`，固定順序
2/2，failed gates=`0`；單輪=`16.1522/11.8162s`。P4-Y新增model call=`0`，但產品semantic authorization實際本機call=`2`，
token accounting unavailable。完整證據：`analysis/p4_y_real_product_graph_delivery_acceptance_2026-09-22.md`。

P4-Z不得重用P4-X或P4-Y輸入追分。先從P4-X已曝光反例抽象出source-bound proposition contract：輸入中的核心subject／predicate／object／
embedding stance／speaker ownership必須在visible reply有可追溯對應，不能只看quote／hearsay／hypothetical外框是否存在。先建立已曝光development
fixture與全新中／英／日holdout、faithful controls和no-op邊界；單一變因必須放在P4-W之後、可見回覆前，或證明現有M33/M39足以提供權威
source atoms後再修復。不得由關鍵詞自行造出來源沒有的命題，也不得把P4-X frame after-zero重新包裝成語意成功。先freeze／commit，才實作與驗收。

狀態：**P3-B54完成；P3-B55 REVIEW_REQUIRED。** capability-separated extractor在事前freeze後，以5秒合成raw驗證generation只取得
`1..3`秒artifact；3秒後2000 Hz sentinel／可見440 Hz能量比`6.781521697810383e-31`，低於凍結門檻
`0.0001`。raw在2個fresh reader process前刪除、private root mode `000`、兩次SHA-256一致、0 forbidden field／
private canary hit／private import。超長artifact、hash、禁止欄位、symlink、hardlink與permission均fail-closed；
B52全版本至B54共58項回歸通過。仍為0 reserved-source media、0 hidden future、0 prediction、0 model call。
完整release：`research/p3_b54_unidirectional_context_extraction_release_2026-09-18.json`。

B55 V1因ffmpeg version flag錯誤在0 network時fail；保存後V2只把`--version`改為`-version`，offline 24項通過後
消耗唯一transport invocation。V2在1.978149秒以yt-dlp exit 1結束：1 request、0 local/public artifact、0 future、
0 playback／semantic inspection／prediction／model。依事前規則不再重試或追加修正。完整反例與選項：
`analysis/p3_b55_reserved_source_context_transport_review_required_2026-09-18.md`。

### B56 執行結果與新設計審查

使用者以「請繼續」授權review建議1，覆蓋B55 `next_execution_authorized=false`，但不改其他邊界。B56另凍結
一次diagnostic transport，使用相同source、`*3000-3180`、工具、0 retry／fallback與B54 public gate；private worker
只把stderr映射成allowlisted error class，不保存／顯示原文、hash或token。允許類別為availability、provider challenge／
authentication、TLS／network、extractor／format、ffmpeg／postprocessing、command／option、unknown；分類必須先以fixture
凍結並涵蓋redaction canary。

若同一請求成功，只可輸出B54 exact 180秒artifact／manifest，private transport刪除後以fresh reader核對duration與hash；
若失敗，保存category、return code、stderr byte count與elapsed，0 public artifact後停止。不得再次修正／重跑，不得登入、
cookies、換來源、改cutoff、存stderr文字、人工播放／語意檢查、取得hidden future、執行prediction／model、寫正式M56或
production memory。

B56事前41項通過後消耗唯一請求：yt-dlp在2.944204秒exit 1，診斷類別`ffmpeg_or_postprocessing`，stderr
35 bytes只計數後丟棄；private runtime已刪除，0 public artifact、0 future／prediction／model。離線確認yt-dlp可找到
ffmpeg/ffprobe 8.0.1，direct ffmpeg synthetic pipeline exit 0，因此不是缺少ffmpeg，但現有redacted evidence不足以判定
postprocessing子原因。完整驗收：`analysis/p3_b56_allowlisted_diagnostic_transport_acceptance_2026-09-19.md`。

2026-09-19使用者再次以「請繼續」明確授權B57，並確認YouTube公開影片作為未來prediction資料來源方向。B57單一架構
變因：private yt-dlp resolver只把一個`bestaudio` signed URL留在記憶，direct ffmpeg再裁`3000..3180`並走B54 gate。
URL／resolver stdout／stderr／metadata不得落盤、hash或進receipt；只記byte count、URL count、allowlisted host category與
failure category。仍為0 retry／fallback、無cookies／登入、同source/cutoff；成功前不得人工播放／語意檢查，成功後也只
能把context artifact交給下一個prediction freeze，不得在本步讀`3181..3241`。

B57事前52項通過後執行：resolver exit 0，在1.927396秒取得1個private `googlevideo_cdn` URL；URL text/hash/excerpt
均未保存。direct ffmpeg在0.081831秒exit 8，分類`tls_or_network`；private runtime刪除，0 public artifact、0 future／
prediction／model。這排除source resolver失敗，但不能把原因斷言為特定HTTP status或header。完整驗收：
`analysis/p3_b57_split_resolver_direct_ffmpeg_acceptance_2026-09-19.md`。

2026-09-19～20使用者明確授權依既定計畫持續執行並使用Codex token，不必逐步停下確認；授權不包含花錢、付費API、
登入、cookies／帳號資料、hidden future洩漏、改弱baseline、降低gate或無限重試。此授權覆蓋B57 review的
`next_execution_authorized=false`，允許B58唯一一次新provider capability。

B58只改resolver同時在private memory提供allowlisted HTTP headers；明確拒絕Cookie／Authorization／Proxy-Authorization／
Set-Cookie，丟棄Range與未列入的非敏感header，URL與header name/value/hash都不落盤。69項affected suite通過後執行：
resolver exit 0、`1.560216s`、1個private URL與3個allowlisted header；direct ffmpeg仍在`0.079168s` exit 8、
`tls_or_network`。0 artifact／future／semantics／prediction／model／paid access。完整驗收：
`analysis/p3_b58_private_allowlisted_header_transport_acceptance_2026-09-20.md`。

B57 headerless與B58 allowlisted-header是兩個前瞻direct-audio修正批次，均失敗；依流程關閉此分支，不再加header、換小參數或
重跑。B59改走metadata-only caption availability probe；87項affected suite後執行成功：resolver exit 0、`1.598962s`，同一來源
沒有日文人工字幕，但有`automatic / ja / json3`，0 caption content／future／semantics／prediction／model。完整驗收：
`analysis/p3_b59_source_semantic_availability_probe_acceptance_2026-09-20.md`。

B60事前104項affected suite通過；resolver成功選出同一track，但唯一urllib caption GET在取得內容前以`tls_or_network`失敗：
0 raw caption／public artifact／prediction-side future access。完整驗收：
`analysis/p3_b60_private_caption_cutoff_extractor_acceptance_2026-09-20.md`。

B61事前114項affected suite通過後成功：yt-dlp native downloader exit 0、`1.888588s`；private full caption
`1,483,058 bytes`投影後刪除，發布65個cue，first/last=`3002.760/3176.079s`；fresh reader exit 0、hash一致、
不回傳text。prediction-side future／prediction／model仍為0。完整驗收：
`analysis/p3_b61_native_subtitle_cutoff_extractor_acceptance_2026-09-20.md`。

B62凍結同一qwen3.5:9b、context、兩call graph、每條512 completion上限、seed／temperature與六label；第一個
`BASELINE_LITERAL` representation call已回傳，但exact schema validation失敗，system未執行、prediction未凍結、future仍0。
raw result因call record只在condition成功後append而誤記0 calls；依控制流程operational actual=`1`，tokens/latency=`unavailable`，
不可填0。完整驗收：`analysis/p3_b62_real_context_prediction_acceptance_2026-09-20.md`。

B63事前22項測試後，以Ollama JSON schema執行；第一個baseline representation call完成並正確記錄：1986 prompt、256
completion（等於num_predict上限）、22.292540秒，回傳後仍parse失敗；system與prediction未執行，future仍0。這支持output
被completion ceiling截斷，但未保存raw，不能斷言確切截斷內容。完整驗收：
`analysis/p3_b63_schema_enforced_prediction_acceptance_2026-09-20.md`。

B64是prediction execution第二個、最後一個修正；保持每個condition總completion ceiling=512與所有研究條件不變，只把兩call
相同分配由256+256改為320 representation +192 prediction。provider-boundary accounting與JSON schemas不變。B64成功才可封存
兩條prediction並進separate future unlock；B64失敗則停止prediction修正，不再放寬schema、增加總token或重跑。任何結果都不得
以單一row宣稱全面優勢或formal M56。

B64事前26項suite通過並凍結提交後執行；第一個baseline representation call完成，`1986/320` prompt/completion tokens、
`25.001742s`，completion再次精確等於ceiling，回傳後仍parse失敗。model call=`1`，system/prediction/future/outcome/retry/
fallback=`0`。因此B62 two-call interface兩個修正批次已用完並關閉；不得把後續工作說成第三次修正。完整驗收：
`analysis/p3_b64_final_equal_budget_prediction_acceptance_2026-09-20.md`。

B65若繼續，必須另立新研究介面：用相同`qwen3.5:9b`、同一real pre-cutoff context、相同condition order、seed、temperature、
`num_ctx`及每condition completion ceiling `512`，把失敗的free-standing representation→prediction兩call改為一次bounded joint
representation-and-prediction。兩condition使用同一個有長度上限的JSON schema與相同一call graph；prompt只允許baseline採literal
state、system採可反駁pragmatic state。先contract/tests/freeze/commit，才可各做一次model call。完成兩條prediction前仍不得讀
3181秒後future；成功也只授權另一步outcome unlock，不是正確率或優勢結論。失敗原樣保留，不以同一介面追參。

B65事前37項affected suite與freeze commit後成功：同一`qwen3.5:9b`完成baseline/system各1 call；實際prompt tokens=
`2224/2217`、completion=`261/233`、latency=`23.262607/18.687710s`，均低於相同512 ceiling。baseline最高label為
`accept_support_and_continue=0.65`，system為`acknowledge_then_continue=0.60`；兩條prediction已封存，state文字只留hash。
future/outcome/retry/fallback仍為0。完整驗收：`analysis/p3_b65_bounded_joint_prediction_acceptance_2026-09-20.md`。

B66先以B65 immutable saved result與canonical result hash綁定prediction，再凍結outcome-only worker：使用同一source的日文automatic
caption，但只公開`3181.0..3241.0`內完整cue；private full caption取得後刪除，禁止回讀3000..3180 context、禁止改prediction、
禁止新model/judge call。評分必須在看future前定案：以可重現的observable behavior mapping取得實際label，再對兩組預測分布計算
selected-label hit、actual-label probability、Brier score與log loss；文字預測只做有證據的token/phrase overlap描述，不假裝是語意人評。
單一row無論正負都只算exploratory counterexample，不得宣稱全面優勢或formal M56。

B66在freeze commit後成功揭盲：first 3 cues=`3182.520..3190.559s`，固定marker `?`令actual proxy label=
`ask_clarification`。baseline/system對actual label機率=`0.05/0.10`、Brier=`1.360/1.235`、log loss=
`2.9957/2.3026`；依凍結rule system勝，但兩組top-1都錯。0 model/judge/retry/prediction mutation；private full caption在fresh
future reader前刪除。完整驗收：`analysis/p3_b66_future_outcome_scoring_acceptance_2026-09-20.md`。

B67不使用B66已曝光row調prompt、marker或門檻；事前固定同一來源四個尚未公開給prediction side的time windows：context/future分別為
`600..780/781..841`、`1200..1380/1381..1441`、`1800..1980/1981..2041`、`2400..2580/2581..2641`。
先一次private caption acquisition只發布四個context artifact，刪除raw與所有future後，原樣重用B65 joint schema、qwen3.5:9b、
condition order、seed、temperature、num_ctx及每condition 512 ceiling，封存8條prediction。任一row/call失敗即保留不完整batch，
不得先讀任何四個future；全部完成才可另立B68一次揭盲aggregate。這是same-source replication development evidence，不是獨立holdout。

B67事前31項affected suite與freeze commit後完成：四列context cue counts=`77/72/66/72`；同一B65介面8/8 calls完成，
prompt/completion tokens total=`18,908/1,697`、model latency=`152.907164s`。top-1有三列condition差異，八條prediction均已
封存；future/outcome/retry/fallback=`0/0/0/0`。完整驗收：
`analysis/p3_b67_same_source_multiwindow_prediction_acceptance_2026-09-20.md`。

B68必須綁定B67 immutable result hash，以一次private acquisition同時投影四個凍結future windows，raw刪除後才由fresh reader
讀取。每列原樣重用B66 frozen first-3-cues/12-second target、marker order、actual-label probability、Brier、log loss與winner rule；
禁止逐列解鎖、改marker/metric、改prediction或呼叫model/human/LLM judge。報告逐列正負與aggregate平均，但四列仍是同一影片的
development replication，不得外推成independent holdout或全面優勢。

B68在freeze commit後一次揭盲四列：row wins system/baseline/tie=`4/0/0`，mean actual-label probability=
`0.2875/0.2625`、mean Brier=`1.0134/1.17095`、top-1 hits兩組皆`1/4`。r0600與r1200的actual-label probability
相同，system只因Brier稍低取勝；baseline mean log loss被r1800的zero-probability放大。0 model/judge/prediction mutation/retry。
完整驗收：`analysis/p3_b68_multiwindow_future_aggregate_acceptance_2026-09-20.md`。

B69不得繼續切同一支影片追分。下一必要交付是事前選定另一支公開一ノ瀬うるは長影片，先只做metadata/caption availability與
duration檢查，不讀字幕內容；選擇規則、source id、context/future windows必須在內容取得前commit。後續原樣重用B65介面與B66 proxy，
但因新source是在看過B68後選定，仍稱source-level prospective replication，不假稱正式independent holdout。若找不到合法可用caption，
保存availability負結果，不用登入/cookies/替換到有利來源。

B69 source selection已完成但尚未查caption metadata：固定query與selection rule選中官方頻道rank 1、duration `12,933s`的
`Mlk5e3hBnb8`，排除原source；四個context/future windows也已固定為600秒間隔的同一組位置。下一步B69A只准一次
metadata-only日文caption availability probe，0 caption content/model/future；若不可用就保存負結果，不換來源。

B69A事前28項affected suite與freeze commit後完成：唯一一次metadata-only resolver在`1.678007s`成功，第二來源無日文人工字幕、
有`automatic / ja / json3`；raw metadata `508,363 bytes`只在記憶解析後丟棄。caption content／future／model／retry／fallback=
`0/0/0/0/0`。完整驗收：`analysis/p3_b69a_source2_caption_availability_acceptance_2026-09-20.md`。

B69B只可使用B69事前固定的第二來源與四個context windows；一次native yt-dlp acquisition後，只發布600..780、1200..1380、
1800..1980、2400..2580的context artifacts，刪除private full caption與四個future內容，再由fresh reader核對。原樣重用B65
bounded joint schema、同一qwen3.5:9b、condition order、seed、temperature、num_ctx與每condition 512 completion ceiling，依序完成
4列×2條prediction。全部8 calls完成前不得讀任何future；任一失敗即保存不完整batch並停止，不重試、不換來源、不調prompt／
門檻。這仍是source-level prospective replication，不是正式independent holdout。

B69B已terminal失敗且未揭盲：唯一caption acquisition與四個context artifacts成功；cue counts=`69/66/77/55`。本機模型前6 calls
完成前三列paired conditions，第7個`s2r2400 / BASELINE_LITERAL` provider call完成但prediction parser以`schema`拒絕，第8 call未執行。
總實際prompt/completion tokens=`15,429/1,650`、model latency=`133.887876s`；future/outcome/retry/fallback=`0/0/0/0`。依事前規則
禁止同來源重跑、補第8 call或B69C揭盲。完整反例：`analysis/p3_b69b_source2_multiwindow_prediction_acceptance_2026-09-20.md`。

B70先在已曝光development fixtures建立與來源無關的介面可靠度gate，不回頭追B69分數。最小單一機制候選是：保留JSON結構、
日文與所有內容gate，只對全部finite且非負、總和大於0的label weights做相同的deterministic normalization，再以凍結精度核對sum=1
且ranking不變；baseline/system完全同規則。同時把未來schema拒絕原因映射為不含raw response的allowlisted類別。先離線contract/tests/
failure fixtures與現有合法outputs；若gate通過，另立B71在任何caption內容前選定第三來源，修正版只能在新來源前瞻測試。B69第二來源
永久保留未完成反例。

B70離線gate已完成：相同adapter把六個finite nonnegative weights以50位decimal／12位輸出精度正規化，residual固定加到label順序中
第一個最大weight，並確認selected behavior不變。例`[2,3,1,1,1,2]→[0.2,0.3,0.1,0.1,0.1,0.2]`；baseline/system
同規則。缺label、負值、nonfinite、全零、非日文與缺state仍拒絕；38項affected suite通過。model/network/future/B69 retry均0。
這不能反推B69 raw失敗原因，也不是效果證據。完整驗收：
`analysis/p3_b70_prediction_interface_reliability_acceptance_2026-09-20.md`。

B71下一步必須在查caption metadata/content前，用固定搜尋與排名規則選第三支官方長影片，排除`4y5GiQpgJgo`與`Mlk5e3hBnb8`，
同時事前固定四個context/future windows。選定後才可另做availability；任何prediction都必須事先綁B70 adapter、同一B65模型／prompt／
token上限與兩condition。因第三來源仍是在先前結果後設計，只算prospective development replication，不假稱正式independent holdout。

B71已依freeze唯一搜尋選中official rank 2的`j6Hlk9cY9LQ`，duration=`12,883s`；四組`s3r0600/1200/1800/2400`
context/future windows已同時固定。搜尋耗時`0.936168s`，raw metadata `15,402 bytes`在記憶解析後丟棄；caption metadata/content、
model、future、retry、fallback=`0/0/0/0/0/0`。完整驗收：`analysis/p3_b71_source3_selection_acceptance_2026-09-20.md`。

B71A只准對已固定source做一次metadata-only日文caption availability probe，0 caption content/model/future；不可改query、來源或windows。
若無支援的Japanese track，保存負結果並停止此來源，不使用登入、cookies、替代來源或人工挑選。

B71A事前39項affected suite與freeze commit後完成：唯一metadata-only resolver在`1.827625s`成功；無日文人工字幕，有
`automatic / ja / json3`。raw metadata `508,363 bytes`只在記憶解析後丟棄；caption content/model/future/retry/fallback=
`0/0/0/0/0`。完整驗收：`analysis/p3_b71a_source3_caption_availability_acceptance_2026-09-20.md`。

B71B只可使用B71固定的第三來源與四個context windows；一次native caption acquisition後只發布context artifacts，刪除private full
caption與future，再由fresh reader核對。模型、prompt、options、condition order與每condition 512 completion ceiling原樣沿用B65；
唯一新增介面機制是事前B70 deterministic probability normalization，baseline/system完全同規則並記錄是否實際套用。8 calls全部完成前
不得讀future；任一call或parser失敗即terminal保存，不重試、不換來源、不放寬內容／日文gate。成功也只授權另一步整批future揭盲，
不能先宣稱修正有效或system有優勢。

B71B已完成8/8 predictions：四列context cue counts=`72/60/58/68`；prompt/completion tokens=`17,312/1,763`，model latency=
`149.1632s`。B70 adapter綁定兩condition，但8個input weight sums全為`1.0`，normalization applied=`0/8`；因此成功不能歸因於
B70，只能證明adapter未破壞合法輸出。兩condition top-1在2/4列不同；future/outcome/retry/fallback=`0/0/0/0`。完整驗收：
`analysis/p3_b71b_source3_b70_prediction_acceptance_2026-09-20.md`。

B71C必須綁定B71B immutable result hash，一次private caption acquisition同時投影四個固定future windows；raw刪除後才由fresh reader
讀取。逐列原樣重用B66/B68的first-three-cues-within-12s、marker order、actual-label probability、Brier、log loss與winner rule；
禁止逐列解鎖、改prediction/marker/metric或呼叫model/human/LLM judge。正負結果都保存；仍是development proxy，不是人類真值或正式holdout。

B71C已一次揭盲第三來源四列：row wins baseline/system/tie=`2/2/0`；平均actual-label probability=
`0.375/0.2375`、平均Brier=`0.81845/0.95215`、top-1 hits=`2/4`與`1/4`，均是baseline較好。
更重要的是四列均無marker命中，全部落到default `acknowledge_then_continue`，actual label diversity=`1`。這沒有重現
B68第一來源的system 4/4 row wins，也暴露目前caption-marker proxy在第三來源缺乏區分力。完整驗收：
`analysis/p3_b71c_source3_future_aggregate_acceptance_2026-09-20.md`。

B72不得新增來源、字幕、future或模型呼叫，也不得用已曝光B68/B71C結果調marker後回報優勢。下一必要交付是綁定兩份immutable
result/release，計算跨來源描述統計、label diversity、marker hit、來源方向反轉及不同metrics是否同向；明確判定現有proxy是否足以支撐
system advantage claim。若量尺失效，保存`proxy_not_adequate`，停止累加同類影片，另立尚未看新prediction/outcome的評價目標重設計；
不得只報對system有利的row wins或Brier而隱藏actual-label probability/top-1反向結果。

B72已完成read-only audit並判定`proxy_not_adequate_for_system_advantage_claim`：跨兩來源8列的row wins雖為system 6、baseline 2，
actual-label probability卻為baseline/system=`0.31875/0.2625`，top-1=`3/8`與`2/8`；Brier/log loss反向偏system。
第三來源actual label diversity=`1`且marker hit=`0/4`，三個metrics發生source direction reversal。0新來源/future/model/judge；
完整驗收：`analysis/p3_b72_cross_source_proxy_validity_audit_acceptance_2026-09-20.md`。

B73下一步不是修改已曝光marker，而是先凍結新的prospective target設計與評價方法：target必須有可辨認的stimulus→response單位，
把直接可觀察行為與需要人類判讀的語用／被理解感分層；automatic proxy只能在與盲化真人標註達到事前可靠度後使用。B73先建立schema、
annotation packet、雙coder reliability gate、missing/ambiguous處理及同模型公平比較欄位，並用synthetic fixtures驗證工具；不得讀第四來源內容、
執行新prediction或用Codex/LLM標註冒充真人。已曝光B68/B71C只作失敗例，不可作新量尺的成功驗證資料。

B73已完成protocol/tooling：prediction view不含outcome，coder view不含condition/prediction；不可辨認boundary的episode fail-closed，
acoustics缺少只能標unavailable。target分成observable moves、goal、stance、literal/pragmatic relation、surface text與另行主觀人評；兩位
不同真人各18 episodes、四個primary alpha均需`>=0.667`且至少兩種observed categories。27項affected suite通過；新來源內容/
prediction/outcome/model/human labels=`0/0/0/0/0`。完整驗收：
`analysis/p3_b73_prospective_response_target_protocol_acceptance_2026-09-20.md`。

B74只建立可實際使用的本機雙coder收集平台：兩個不可互看的private ledgers、同一frozen packet manifest、無condition/prediction欄位的
HTML表單、逐欄validation、完成後才可由獨立analyzer讀兩份ledger。先用synthetic packets驗證啟動、提交、重啟保存、跨coder隔離、
incomplete拒絕與reliability report；不得用synthetic pass解鎖真實來源或宣稱human reliability。Safari若工具仍拒絕則保持UI pending，
不能改稱通過；也不得在B74先取第四來源內容。

B74已完成：20項affected tests通過；Safari實際新增1 tab顯示synthetic標註頁，提交一題後`0/18→1/18`。private root/ledger
permissions=`0700/0600`，兩ledger entries=`[1,0]`；完整18×2 synthetic calculation的四個primary alpha均`1.0`，但
`synthetic_authorizes_human=false`、`real_prediction_authorized=false`。新來源/model/正式human label=`0/0/0`。完整驗收：
`analysis/p3_b74_isolated_two_coder_collection_site_acceptance_2026-09-20.md`。

B75下一步只設計並凍結real 18-episode sampling frame：來源選擇與slot規則必須在內容review前固定，每個slot需可辨認外部stimulus、
Uruha response與時間boundary；無清楚stimulus的直播獨白標unusable且不得用鄰近字幕補成對話。frame需包含controlled same-surface
context pairs與literal/pragmatic context-flip controls，並維持公開來源provenance、acoustic unavailable規則與train/dev/holdout分離。
先做metadata/source availability，不得在sampling freeze前觀看或標註response內容；B75也不得直接執行model prediction。

B75已terminal不足：唯一一次`ytsearch24:一ノ瀬うるは コラボ 雑談` metadata search exit 0、`1.323599s`、raw stdout
`33,182 bytes`丟棄，但符合official channel＋duration＋keyword＋exclusion的來源為`0`。caption/media/model/outcome/retry/fallback=
`0/0/0/0/0/0`，0 selected source／slot。這是provider ranked search discovery失敗，不是官方頻道內容不存在，也不是B73否定。
完整驗收：`analysis/p3_b75_real_episode_sampling_frame_acceptance_2026-09-20.md`。

B76是此source-discovery的第一個前瞻修正：改為一次直接列舉相同official channel公開uploads的metadata inventory，再套用事前固定的
排除、duration、title keywords與provider order；不得使用B75 query、人工選片、caption/content或playback。若仍不足三支，保存負結果並
停止本來源發現分支，不做第二個關鍵字／小參數重試。若足夠，只能建立同一6-relative-region-per-source frame；content review與model仍另 gate。

B76亦terminal不足：official channel `/videos` inventory exit 0、`0.565957s`、raw stdout `8,540 bytes`丟棄，eligible sources=`0`；
caption/media/model/outcome/retry/fallback全為0。因raw未保存，不能事後斷言是哪個metadata field造成0。B75＋B76已耗盡本source-discovery
分支原始嘗試與唯一修正；不得擴limit、換tab／keyword或人工挑選。完整驗收：
`analysis/p3_b76_official_channel_inventory_acceptance_2026-09-20.md`。

P3-C1已完成離線contract/data/metrics freeze：18個surface families、36 variants；train/dev/holdout各6 families，中文／英文／日文
各6 families。每組literal/pragmatic context保持byte-identical surface，family不跨split；prediction packet不含target，聲學固定unavailable。
baseline取得完整context且可正常推理，system唯一介入是顯式可反駁pragmatic state；兩組同模型、同一call、每item同384 completion ceiling，
額外system state token計入同budget。primary為holdout mean multiclass Brier至少改善0.03，且literal overinterpretation不得更差、paired
context-flip top-1不得更差。11項focused與43項B65/B70/B73/C1 adjacent通過；model/network/Uruha source/future/human label/production/
formal write全為0。完整驗收：`analysis/p3_c1_controlled_context_flip_acceptance_2026-09-20.md`。這只是developer-authored prospective
proxy contract，不是model效果、人評、獨立holdout或reference-person prediction。

P3-C2已完整執行但未通過事前效果量：8個train smoke後24個dev calls，32/32 validated，0 retry/fallback/holdout/Uruha future。
總成本=`22,952` prompt、`6,497` completion、`326.528142s` model latency。baseline/system mean Brier=`0.13305/0.120717`，
system改善`0.012333`，低於SESOI `0.03`；兩組dev top-1與paired flip皆100%，literal overinterpretation皆0，顯示developer題有ceiling。
English/Chinese system Brier較低，但Japanese=`0.1058/0.1583`與deixis=`0.0608/0.1658`反向。system相對baseline耗用
`1.2851×` prompt、`3.112×` completion與`2.3136×` latency；沒有成本優勢替代結論。依freeze判`controlled_lane_success=false`，
C1 holdout保持0 access，不以改門檻、改target或偷跑holdout追分。完整驗收：
`analysis/p3_c2_controlled_context_flip_acceptance_2026-09-20.md`。

P3-C3是唯一下一步：只做官方、外部作者的controlled pragmatic benchmark／stimulus資源discovery，先查DRInQ、PaCE及直接相關官方
artifact的paper supplement、repository、license、資料schema、same-surface context pair與train/dev/test邊界；不得下載／讀取hidden test
answers、執行模型、取得新Uruha來源／future或把C1 developer cases改名獨立holdout。事前列fit criteria：必須能在相同完整context與同模型
條件比較direct baseline和system，必須同時量context sensitivity與literal overinterpretation，必須有可合法重現的split/provenance；若官方
artifact不可得、license不允許或任務只測另一種能力，保存負結果而不自行重建答案。P3-C3輸出只能是候選資源與是否適合的決策，不能先宣稱
外部benchmark優勢；若有合格資源，另立contract/freeze後才可取允許的train/dev部分，test仍鎖定。

P3-C3已完成並保存`no_executable_external_benchmark_now`。DRInQ具同surface context variation且作者repo有單一validated CSV，
但未見dataset license與train/dev/test split，因此只列`conditionally_eligible_blocked`，0 CSV下載／row read。PaCE的方法最符合
literal/pragmatic context-flip，但本次從ACL官方頁與官方來源搜尋未發現可核對的dataset artifact，列
`method_fit_artifact_blocked`；這不斷言資料永不存在。PUB有MIT artifact，但不是same-surface literal/pragmatic pair且專案以前已用過，
不能當新independent holdout。三者合計executable candidate=`0`；benchmark dataset download／row／hidden answer、model、new Uruha
source/future、human label、production write均為0。完整驗收：
`analysis/p3_c3_external_pragmatic_benchmark_discovery_acceptance_2026-09-20.md`。

P4-A是唯一下一步。先只讀盤點既有本機聊天入口、真實runtime node graph、VRM 3D與Function Calling的啟動方式、資料源、port／process
owner、共用session與既有Safari驗收，列出「已經整合／存在但分離／真的缺少」的可重現證據。不得先新增dashboard、複製HTTP handler、
改研究資料／gate、碰原始dirty checkout、外部部署、登入或付費API。盤點完成後，若四項已有同一入口，先以啟動／重啟／長對話／工具成功
與失敗／3D顯示建立最小acceptance contract；若尚未整合，只准選一個阻擋統一入口的最小連線作為P4-B單一變因。P3的負／混合結論、
C1 holdout鎖定與M55/M56正式門檻不因P4產品工作改變。

P4-A已完成可重跑source inventory：Chat與truthful runtime node graph都已接在`uruha_web_ui_product.py`同一產品入口與同一turn output；
但Git tracked 3D asset=`0`，沒有VRM renderer或physical action executor。`vrm_action_policy_v34.py`只存在於research/eval路徑，
product/web/brain均未import，也沒有runtime tool schema或tool-result loop，因此Function Calling狀態為
`research_policy_only_not_product_runtime`，不能說是「既有功能」。safe worktree預期的`Style-Bert-VITS2/venv/bin/python`不存在，
system Python也沒有Gradio，故direct launch尚未ready。4項focused tests與inventory validation通過；runtime/Safari/model/production memory/
tool/physical action均0。完整驗收：`analysis/p4_a_unified_local_entry_inventory_acceptance_2026-09-20.md`。

P4-B是唯一下一步，單一變因只新增safe isolated product launcher，不改brain、prompt、研究資料、VRM或Function Calling。launcher必須
明確解析操作員指定或已知可用Python、檢查Gradio與entry，但不複製／修改原始dirty checkout；每次預設建立獨立temporary memory DB、
session DB與Web logs，只綁`127.0.0.1`，拒絕public host/share、登入與付費API。先以fixtures驗證interpreter缺失、dependency缺失、
public bind、路徑碰撞、child command/env與cleanup／preserve規則；offline contract通過才可真實啟動。真實啟動後核對health、隔離路徑、
聊天＋同輪graph與重啟；Safari是獨立可見驗收。P4-B不得把啟動成功擴張成VRM／Function Calling已整合。

P4-B已完成，保留一次真實失敗與一次sandbox修正。v1雖localhost HTTP 200與Safari可見，但Human Annotation path仍指向repo，故在0聊天、
0 repo write時判fail。v2以macOS sandbox拒絕child寫safe worktree與原始dirty checkout，synthetic deny／isolated allow通過；32項完整相鄰
suite後，以同manifest及明確reuse重開。Safari維持48個tabs且沿用既有tab，真實英文輸入要求只聽、不給建議，最終日文為
`うん。今は方法出さないから、そのまま話して。`；trace選`listening/listen_presence`、否定`solve_regulation`、surface matched，
同輪graph有69節點，user wait=`3.3884s`。1筆`1,353,575 bytes`JSONL、memory DB與adaptive model都只在isolated root；Git clean，
沉默後0可見催促。server仍在`127.0.0.1:7860`供使用者查看。完整驗收：
`analysis/p4_b_safe_isolated_product_launcher_acceptance_2026-09-20.md`。尚未驗post-chat process restart recall、voice、VRM或Function Calling。

P4-C是唯一下一步：新增一個allowlisted、read-only、零副作用的`get_runtime_status` Function Calling seam，作為未來VRM action transport的
前置，但不可接physical VRM。先凍結explicit status-request與ordinary conversation／negation／hypothetical／prompt-injection guards、唯一tool
schema、空argument、single-call、bounded result與日文surface contract；tool只能回傳不含路徑／對話／secret的brain-loaded、turn count、
memory isolation、tool capability狀態。offline fake-provider先驗證valid call、no-call、wrong tool、extra args、duplicate、malformed與executor exception
全部fail-closed，並把request→model decision→validated call→tool result→Japanese surface加入現有node graph。contract/tests/freeze/commit前
不得做real model call；real call通過與negative guards通過後才可整合product。shell、file write、external network、login、paid API與VRM execution
一律不授權。P4產品工作不改P3/M55/M56研究結論。

P4-C已完成產品真實驗收：status輪在全新session、brain仍lazy時以英文詢問，模型1 call選中唯一
`get_runtime_status({})`，tool 1 execution、side effect/memory-content read/brain initialization/retry=`0/0/0/0`；日文回覆正確顯示
brain待機、0 turn、isolated memory及read-only能力。同輪graph有request→model decision→validated call→tool result→surface五個
function nodes，共7 nodes，端到端=`6.2512s`。下一輪普通英文聊天仍回`うん。今は方法出さないから、そのまま話して。`，走原本
69-node path，P4-C新增model/tool/function-node=`0/0/0`，端到端=`2.697s`。後續4次background cycle未新增visible idle prompt。
core gate＋產品Safari真實本機model calls合計2，0 paid/external/retry。完整驗收：
`analysis/p4_c_product_function_calling_acceptance_2026-09-20.md`。這只證明一個read-only status tool，不是一般Function Calling、
state-changing action、VRM或研究優勢。

P4-D是唯一下一步。先做read-only local capability inventory，確認safe worktree與原始checkout是否已有可合法重用的VRM/GLB/GLTF asset、
renderer package、license/provenance、3D canvas入口與既有animation/action transport；原始dirty checkout只讀不改。若有合法asset與renderer，
凍結同一localhost產品入口的最小render contract；若沒有，保存缺口並只設計user-supplied `.vrm` 邊界與離線synthetic fixture，不下載或
重散布來路不明角色模型。P4-D只先做到可視3D renderer與truthful load/error node，不接未通過holdout的personality/action decision，
不執行physical state-changing action，不改P3資料／gate，也不使用登入、付費API或外部部署。

P4-D已完成並 release：同一Safari產品頁新增browser-only Local VRM Stage；初始只顯示`NEUTRAL STAGE · NOT URUHA`中性舞台。
以隔離runtime內自製4,020-byte VRM 1.0 mannequin實測，canvas真正畫出紫色T-pose且「選擇→驗證→解析→呈現」四節點全綠；
9-byte破損檔案則parse節點紅、render未完成、placeholder回復，沒有假稱顯示。valid→invalid→valid只做瀏覽器本機解析，conversation rows
維持`3→3`，server upload／asset persistent write／action／P4-D model/tool call全為0。viewer無remote URL/fetch/XHR且只允許blob/data；
這是application-level no-network evidence，不是假稱量測Safari其他48個既有分頁。status Function Calling與ordinary chat真實回歸仍通過，
端到端=`6.3426s/2.842s`；VRM始終可見。第一次raw http-literal proxy失敗亦保留，沒有改dependency或放寬runtime規則。
完整驗收：`analysis/p4_d_local_vrm_renderer_acceptance_2026-09-20.md`；release：
`research/p4_d_local_vrm_renderer_release_2026-09-20.json`。這不代表有一ノ瀬うるはasset、角色授權、動作智慧、tool-controlled avatar或研究優勢。

P4-E是唯一下一步，單一變因只驗證一個明示、speaker-qualified事實能否跨真正product process restart保存與回溯。必須在第一輪前固定
兩session腳本、唯一事實、可接受日文內容、ownership/relationship錯置反例、retrieval provenance、restart證據與失敗判準；只使用P4-B
既有isolated runtime，不讀production memory。第一session明確告知一個親屬所屬寵物名稱後停止process；以同一isolated root新PID／新session
重啟，第二session問題不得包含答案。成功需同時有正確名稱、正確speaker/owner關係、實際persisted retrieval trace、自然日文與graph可見，
且VRM local asset因browser-only不應被server記住。任何錯名、把親屬寵物說成使用者自己的、只靠prompt含答案、沒有retrieval證據或未真正
換process都算fail。結果一次保存，不因失敗改題、改prompt、手動注入memory或重跑；不把單一成功外推成長對話／open-world memory可靠。

P4-E已依事前freeze一次通過：全新隔離root第一個PID `62778`收到「Rina喜歡black coffee、使用者偏好herbal tea」，日文回覆
`記憶に残すよ`後真正退出；同一root／memory DB以新PID `62949`與新session重啟。答案不在第二題時，Safari回覆
`あんたが好みって言ってたのはハーブティー。`；唯一candidate的persisted episode ID=
`b992ec7e-cea9-4dca-81eb-e0760050b140`，來源時間早於新process，selected speaker=`user`而非Rina，圖上有
`speaker_qualified_fact_p3`，general planner model call=0。VRM stage在新page回到waiting，證明browser-local asset未被server持久化。
兩process／兩turn合計只有第一輪1次本機planner call，0 retry／tool／VRM action／paid API／production memory。完整驗收：
`analysis/p4_e_cross_restart_memory_recall_acceptance_2026-09-20.md`。這是developer-authored bounded product integration，不是open-domain、
長對話、人類記憶或研究優勢證據。

P4-F已依事前freeze一次通過：第一個process保存「偏好herbal tea」與另一筆「不再偏好herbal tea，現在偏好black tea」；舊process
真正退出後以同一isolated root／memory DB、新PID／新session重啟。答案不在recall問題時，Safari回覆
`今の好みは紅茶。前のハーブティーから更新してる。`。graph狀態=`resolved_explicit_preference_supersession`，兩個immutable episode
分別綁定historical／correction trace，current／revoked digest不同，DB rewrite=0。舊episode retrieval score=`1.4813`仍略高於更正
episode=`1.4801`，因此結果不是任選最高分。3 turns／2 processes／1 restart／2 write-turn planner calls，0 retry／fallback／paid API／
production memory；frozen gate failed=`0`。完整驗收：
`analysis/p4_f_cross_restart_preference_supersession_acceptance_2026-09-21.md`。這只證明一個bounded English tea correction case，
不等於一般信念修正、長對話、人類式記憶或研究優勢。

P4-G是唯一下一步，原因來自同一真實P4-F執行暴露的可見產品缺口：兩個寫入輪分別回`了解しました`與`了解しました。`，雖然是日文，
卻過度禮貌且制式，不符合既有casual Uruha surface要求。先把這兩個raw輸出、原planner route與P4-F memory semantics凍結為before；定位
現有full-planner輸出到visible surface之間最窄的authority。唯一允許變因是「使用者明示請系統記住偏好」與「使用者明示更正同一偏好」
兩類 acknowledgement 的自然、簡短、casual日文表達；不得改general persona prompt、模型、memory ranking、episode寫入、supersession／
recall adapter、P3研究資料或baseline。

成功需先用offline fixtures證明中／英／日三語的明示記憶與更正輸入都不再顯示`了解しました`系模板，仍只輸出自然日文、保留うるは公開
人格邊界，且普通聊天、拒絕、求助、身份、回溯與P4-F current／revoked均不退化。必須有negative guards，避免把普通「了解嗎？」、第三人稱
偏好、假設句或非偏好更正誤套成確認。P4-F同一真實案例不得重跑；離線contract、tests、freeze及commit完成後，另用未曝光的isolated新案例
做一次真實runtime／Safari驗收，並核對episode write、graph、語言與0 retry。這一步只改善可見surface，不得宣稱研究優勢或更深理解。

P4-G已完成但正式gate為`fail`，且負結果不可重跑／追分。全新isolated root的中文寫入輪正確辨識`zh/write`，但模型回
`了解。茉莉花茶が今の飲み物だ`，因不在frozen formal-ack allowlist，post-guard authority沒有啟動；等待`25.2079s`亦超過20秒。
日文更正輪的P4-G classifier正確辨識`ja/correction`，但既有rule route誤判`ask_like_me`，顯示與偏好更正無關的
`はいはい、全くじゃないとは言わない。そこ聞いて安心したいだけだろ。`。兩輪graph node與不同episode均存在、模型call=`1/0`、
retry/fallback=`0/0`，但frozen gate共10項surface失敗。完整負結果：
`analysis/p4_g_multilingual_preference_acknowledgement_acceptance_2026-09-21.md`。

P4-H是唯一下一步，單一變因從失敗診斷直接收斂為「明示偏好記憶act在general planner與舊intent碰撞之前取得deterministic plan／surface
authority」。先綁定P4-G immutable result，沿用已通過的中／英／日classifier，不擴allowlist、不改general persona prompt；對write與
correction各建立一個bounded rule plan，明確intent、dialogue act、core Japanese與0新增推測，讓寫入行為不需要任意模型措辭且不會被
`ask_like_me`先攔走。最終surface須由同一typed act contract接管，而不是只在reply剛好等於制式敬語時接管。

P4-H不可改episode/schema、memory ranking、P4-F parser／localization／recall、研究資料或baseline；「記住訂正內容」只代表原episodic
turn確實保存，不宣稱所有語言都已形成typed current preference。需把P4-G trace中未啟動authority卻顯示
`final_visible_surface_matches_contract=true`的誤導欄位修正。先以六個正例及普通聊天／第三人稱／假設／引文／安全路由做offline regression，
commit後另凍結全新案例才可真實執行；P4-G茉莉花茶／冰咖啡案例不得重跑。成功只代表bounded product act與surface，不代表人類理解或研究優勢。

P4-H已完成且 frozen product gate=`pass`。全新 English write／Chinese correction 在同一新隔離 process 各執行一次，實際顯示
`ん、その好みは覚えとく。`與`ん、訂正の内容はそのまま覚えとく。`；兩輪皆為 deterministic rule plan、正確
`explicit_preference_memory_write/correction` intent、graph `select` node、不同 episode、planner model call=`0`、retry/fallback=`0`，
使用者等待`2.1027s／11.2373s`，0 failed gates。P4-G舊案例未重跑。完整證據：
`analysis/p4_h_multilingual_preference_memory_act_acceptance_2026-09-21.md`。

同一結果也直接暴露 P4-I 的唯一問題：第一輪 English `sparkling water` 寫入後 typed profile `likes=[]`；第二輪 Chinese 更正後
profile 為`likes=[]`、`dislikes=[氣泡水]`，新 current preference `熱可可`沒有成為 typed like。兩輪 episode 都正確保留，因此不能再改
P4-H planner／surface，也不能說資料完全沒記住；缺口是 current preference 內容從多語 observable utterance 到 typed active state／superseded
history 的 projection 不完整。

P4-I先只讀定位既有 profile extraction、episode write 與 P4-F typed supersession 路徑，再綁定 P4-H immutable result，凍結 English／Chinese／
Japanese write與correction的 typed contract。current preference 與 superseded history必須分開，來源、時間、語言與更正鏈可查；不得只把舊項目
粗暴加入dislikes、不得抹掉原episode、不得把偏好內容當心理推測。先做offline parser／writeback／negative guard與受影響回歸，commit後才可另立
全新cross-restart real case；P4-H氣泡水／熱可可與P4-G舊案例都不得重跑。這一步仍不碰研究baseline、production memory、外部部署或人類優勢claim。

P4-I已依事前freeze一次通過：第一個process以English寫入scope=`drink`的`oolong tea` active typed positive，真正退出後，第二個process
以相同isolated root／memory DB及新PID／新session啟動，送出Chinese correction為`barley tea`。最終P4-I validity resolver得到一筆
active新positive、一筆historical舊positive及一筆active明示negative；舊record沒有刪除或改寫，兩個positive共用相同scope predicate。
Safari兩輪顯示自然日文與P4-H `select`／P4-I `memory` nodes；2 process／2 turn／0 retry／0 planner model call，等待
`2.3411s／16.2815s`，frozen gate failed=`0`。完整驗收：
`analysis/p4_i_cross_restart_current_preference_acceptance_2026-09-21.md`。

P4-J只處理仍明確未授權的read path：目前P4-I profile shadow仍是`answer_use_authorized=false`、`affects_working_memory=false`，所以typed state
持久化成功不等於產品會用它回答「我現在喜歡什麼？」。先凍結一條read-only adapter：僅對明示第一人稱、current-preference、exact supported
scope的問題讀取active P4-I current record；scope缺失／不支援／多active候選必須fail closed，historical與negative不能當current answer。
非selected問題完全保留P4-F episode recall。回覆仍須自然日文，graph要顯示typed source id與active-only決策；回答本身不得寫profile。
P4-I oolong／barley案例不得重跑。contract／tests／freeze／commit前不得送新real turn，也不得把這一步外推成一般記憶、人評或研究優勢。

P4-J 已依事前 freeze 做完唯一 cross-restart 案例並判定 `fail`，不得重跑。第一個 process 以 English 寫入
`drink=rooibos tea`，active typed memory id=`b1ae941d-5120-47c2-81fb-77194545ce78`；第二個 process 重用同一隔離 DB，
Chinese answer-absent query 成功把同一 id 讀進 `typed_current_preference_recall_authority_p4` plan，且 planned core 正確為
`今の飲み物の好みはルイボスティー。前のじゃなくて、今の方ね。`。但 Safari／JSONL 最終顯示 episode timestamp 回覆
`前に: 2026-09-21 13:15:5って言ってたろ。そこは忘れてない。`，graph 也缺 P4-J node。profile 仍為1筆且 hash 前後一致；
2 process／2 turn／0 retry／0 planner model call，frozen gate 7項失敗。完整負結果：
`analysis/p4_j_cross_restart_typed_recall_acceptance_2026-09-21.md`。

P4-K 只修這個已定位的 propagation seam：planner normalization 會保留 P4-J intent/core，卻丟掉自訂 contract，導致 visible guard 只查
final logic 時無法接管 surface，materializer 也沒有 payload 可畫。允許從當輪 `memory_data` 恢復已選中、已授權的 P4-J contract，先複製到
final logic 再套用 exact surface authority，最後產生 select-stage graph node。必須新增模擬 normalized logic 缺少自訂欄位的回歸；safety route
仍不得被覆寫，非selected query、P4-F、typed storage、active resolver、localization、expected surface與P4-J舊freeze一律不改。

先完成implementation與受影響回歸；在另立新acceptance freeze前真實產品輪次=`0`。之後只可用未執行的新值／新語言案例，P4-J rooibos、
P4-I oolong/barley、P4-H sparkling-water/hot-cocoa及P4-G案例都不得重跑。成功也只代表bounded跨重啟typed recall交付，不是一般記憶、
長對話、人評、強LLM優勢或人類方程式。

P4-K 離線實作已完成：visible guard 先沿用 final logic 內合法 contract，若 planner normalization 已移除自訂欄位，才從同一輪
`memory_data` 恢復並複製到 final logic；safety route 在恢復前就返回。事前紅燈=`2 failed, 3 passed`，修正後 P4-K=`5 passed`，
P4-F～P4-K affected suite=`179 passed`。freeze verifier 的 current-file hash 假失敗已改為讀 freeze commit 的 immutable Git blob；
freeze JSON、contract與產品案例皆未改。完整離線驗收：
`analysis/p4_k_typed_recall_surface_propagation_acceptance_2026-09-21.md`。

唯一下一步是 P4-K-REAL：在任何新real turn前另凍結全新兩程序案例；使用未在P4-J真實案例執行的exact source value與query language form，
第一程序明示寫入，真正退出後第二程序以答案不在題目的exact-scope current query回溯。需同時通過exact自然日文、P4-J select node綁同一
active id、profile count/id/content hash不變、不同PID/session、0 retry／planner model call／production memory／external deployment。
P4-J rooibos失敗仍為fail，不得重跑或改寫。

P4-K-REAL 已依事前 freeze 一次通過，failed gates=`0`。第一個 process 以 English 明示寫入 `drink=紅茶`，Safari 顯示
`ん、その好みは覚えとく。`，active typed id=`15d6830f-10cf-4b08-9935-3f69624d3a9d`；真正退出後，第二個
process 重用同一 mode-0700 isolated root／DB，以新 PID／session 回答 Japanese answer-absent query，Safari 精確顯示
`今の飲み物の好みは紅茶。前のじゃなくて、今の方ね。`，graph 有 `typed_current_preference_recall_p4` select node，
且使用同一 active id。profile count／id／content hash 前後不變，episode `1->2`；2 process／2 turn／0 retry／fallback／planner model call，
等待 `2.1570s／2.1684s`。完整證據：`analysis/p4_k_cross_restart_surface_delivery_acceptance_2026-09-21.md`。

這只證明 P4-K propagation 與跨重啟 delivery；`紅茶` 和舊 P4-F black-tea 語意重疊已事前揭露，不能宣稱 unseen semantic
generalization。下一步 P4-L 只處理目前已知的 cross-language exact-scope gap：Chinese／Japanese 明示 current-preference write 可能保留
surface scope `飲料` 或退成 `general`，但 P4-J query 已 canonicalize 為 `drink`。單一變因是把既有 supported write aliases 映射到
canonical scope，同時保留 source language／hash／provenance；不可同時改 value extraction、value localization、P4-J query／surface、
研究 baseline 或 frozen real cases。先做 before regression、contract與freeze；另立新 product acceptance freeze 前 real turn=`0`。

P4-L offline implementation 已完成。Before 證據顯示繁中 `飲料`、簡中 `饮料`、日文 `飲み物` 與 P4-J canonical
`drink` 形成不同 predicate；新 product-only adapter 只對 P4-I 已選中且 explicit-scope 的三個 frozen exact aliases 投影成
`drink`，不依 value 猜 `general`，不改 `snack`／未選中句。P4-I、P4-J 原檔未改；source language／input hash／value hash保留，
typed metadata另留alias id與source alias hash，graph新增 raw-free P4-L memory node且無 answer authority／model call。

Prospective test由implementation前collection error轉為P4-L=`9 passed`；P4-I～P4-L affected regression=`98 passed`，只有既有
Chroma SWIG warnings 2項。安裝後 temporary-Chroma smoke確認繁中 `桂花茶` 寫成 `scope=drink`、canonical predicate與
`drink:zh-Hant:v1` provenance，而 direct P4-I frozen tests不安裝adapter時仍保留舊結果。完整驗收：
`analysis/p4_l_preference_scope_canonicalization_acceptance_2026-09-21.md`。此層尚未有真實Safari證據；下一步P4-L-REAL必須先
凍結全新 Chinese explicit-scope write → real restart → English answer-absent query，freeze commit前 real turn=`0`。

P4-L-REAL 已依事前 freeze 一次通過，failed gates=`0`。第一個 process 以繁中明示 scope `飲料` 寫入 `麦茶`，P4-L
投影成 canonical `drink` 並保存 `drink:zh-Hant:v1` 與 source alias hash；Safari 顯示 `ん、その好みは覚えとく。`，graph
同時有 P4-I/P4-L memory nodes，active id=`c62640d7-ab6a-4edc-8f42-d44f8fd4fa01`。真正退出並關閉 listener 後，第二個
process 重用同一 mode-0700 root／DB，以新 PID/session 接受英文 answer-absent query，Safari 精確顯示
`今の飲み物の好みは麦茶。前のじゃなくて、今の方ね。`，graph 有 P4-J select node，使用同一 active id。

profile count／id／content hash、canonical scope與alias provenance在recall前後不變，episode `1->2`；2 process／2 turn／
0 retry／fallback／planner model call，等待 `2.2757s／2.2885s`。`麦茶` 與舊 P4-I barley-tea 語意重疊已事前揭露，
所以只證明 bounded跨語scope alignment與delivery，不證明novel value semantics或一般理解。完整驗收：
`analysis/p4_l_cross_language_scope_delivery_acceptance_2026-09-21.md`；下一步是上方 P4-M，不再重跑本案。

## 工作環境

- 安全 worktree：`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`。
- 分支：`codex/v2-15-pragmatic-research-showcase`，PR #435。查實際 HEAD，不碰原始 dirty checkout。
- Python：產品測試用 `.venv/product_checks/bin/python`；純標準庫 verifier 可用系統 python3。
  不全域安裝依賴。Gradio／Torch／brain 的 import 留在 isolated worker，不放純資料 module 的頂層。
- 長期目標檔：`LONG_TERM_GOAL.md`。2026-09-09 Goal 工具讀到 usageLimited；文件更新不等於 app 已恢復。
  不清除／假完成／改內部 DB 來換 Goal。使用者手動回合仍可執行已授權工作。
- 本機 Safari 已完成P4-B、P4-C與P4-D真實驗收；目前沿用1個Uruha頁面、沒有關閉使用者tab。P3-A不依賴瀏覽器。

## 已完成、不要重做

- P1 prediction identity 跨重啟保存；P2 compact planner、表達 core commit、當輪求助、婉拒、
  獨處要求與 speaker-qualified recall 的有限產品 baseline 已凍結：
  `research/p2_integrated_product_baseline_freeze_2026-09-09.json`。4 mechanism＋1 abstention、結構4/4。
- P3成本記錄收尾 commit：`34bef3d01d236873b4aa384b76aba2893ff9949d`。
  `research/p3_compute_accounting_freeze_2026-09-09.json`；121 passed／8 dependency warnings。
  `analysis/p3_complete_product_compute_accounting_acceptance_2026-09-09.md`。
- P3-A fail-closed comparison harness 與自審修正已凍結；P3-B1 isolated product worker 將產品真實 OpenAI／
  native M31 globals 綁到同一 gate，兩次 lazy import、same-case restart、cross-case refusal 均通過。驗收：
  `analysis/p3_b1_product_worker_acceptance_2026-09-13.md`。仍為 0 real model/network/paid calls。
- P3-B2 developer smoke source／annotations 已分離凍結：6 cases、24 user turns、12 sessions、三語各2、
  六 family 各1，建立 72 個 allowlisted views。驗收：
  `analysis/p3_b2_developer_smoke_acceptance_2026-09-13.md`；未執行任何生成。
- P3-B3 provider/tokenizer binding 在既有四種 fixture 通過；P3-B4 找到產品 call shape drift；P3-B5 adapter 已補齊並驗證
  seed/top_p/num_ctx。P3-B6 單一 product canary 工程通過，但品質未定。P3-B7 baseline 執行保留負結果：3 calls、2 complete、
  1 prompt-count failure，沒有三條件比較。詳見 `analysis/p3_b7_canary_baselines_acceptance_2026-09-14.md`。
- 真實本機run2：5 sessions／9輪，與P2可見回覆9/9相同；ledger 2生成＋130記憶操作，
  2,901生成tokens、30.834245秒；四個結構checks通過。兩次run均保存。
- native M31只mocked transport驗證，這九輪未實際觸發；Chroma embedding token／CPU/RSS/energy未量測。
  HTML是runtime graph產物，Safari未驗收。開發控制不是新holdout或全面能力證據。
- 不為新純資料harness重跑未變動的121項或M57.9八分鐘套件。

## 仍需保留的限制

- P2只在已曝光開發案例通過，不等於open-world對話、50輪可靠、人評、強LLM優勢或人腦方程式。
- 原生M31預設qwen3.5:9b，而一般planner是qwen2.5:7b；P3必須按config在isolated worker import前統一，
  transport核對所有路徑。不是改永久產品預設。
- P3共同歷史目前是system-anchored paired；報告必須揭露其條件性，不能當獨立對話偏好實驗。
- 正式研究依據上次封存紀錄仍缺真人／真實temporal資料；此輪未新讀私人ledger。M57.9 partial，
  M58沒有新授權。產品比較不能補造正式結果。
- developer smoke僅逐案推進，case06在B27仍為0 generation；未執行的cases／turns、case06評分、真人與formal confirmation仍不可宣稱。

## 回報方式

使用中文，先回答使用者新問題，再依卡片工作。短報實際成果、必要數據／例子、限制、Git與下一gate。
不要用「測試很多」代表使用者感受到的進步。兩次有證據的修正仍失敗就列反例進review，不亂加功能。
