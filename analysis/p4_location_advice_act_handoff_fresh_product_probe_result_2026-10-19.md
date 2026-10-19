# P4 位置建議言語行為交接：fresh Safari 產品探針

日期：2026-10-19。結論：**整批 strict FAIL**。本批是事前凍結的九句 developer-authored fresh 產品探針，不是正式 temporal holdout、強 LLM 同模型對照或真人品質評價。舊批 B5 與本批九句都不重播追分、改 gold 或把局部接線成功改稱產品通過。計畫與條件式 gold：`research/p4_location_advice_act_handoff_plan_2026-10-19.md`、`datasets/p4_location_advice_act_fresh_probe_2026-10-19.json`。

## 執行範圍與可追溯原件

- 計畫／新題先於實作以 `5aaf6ab` 凍結；opt-in 程式、測試與產品 SHA 在首輪前以 `e7f5196ba4473cd0cdcfc325addd49728ca24a39` 提交並推既有 PR #435。首輪前聚焦 **11/11**、受影響相鄰零模型 **84/84**，產品 manifest **15/15** 相符；這些只證明指定契約與接線，非 fresh 回覆品質。
- 全新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-arq4c9pp`。零輪 run `e85f797e12b71ca9` PID 67372、A run `4d1dc2041b96d561` PID 67942、A4 後 planned stop、同 DB 新 PID 的 B run `97a6882ac51c8080` PID 68556；各有 same-PID ready／planned-stop 收據，終局 PID 已退出且 port 7894 無 listener。官方 SHA ONNX 私有離線副本預熱取得 1×384 finite embedding，開始前 profile 顯式初始化為空。
- 真 Safari 新分頁：A session `20261019_072402_3897f423` 四輪、B session `20261019_072810_a51dfa11` 五輪，同一隔離 DB；各題一次、**0 retry**。每輪目視泡泡與 runtime node graph 的 handoff／`UTTERANCE`；既有 Safari 分頁未關。本次沒有另存 Safari 截圖，故泡泡觀察是操作者紀錄，raw／graph 可由原件重算。
- 原始九行 `web_logs/conversation.jsonl` SHA-256：`8e05c0252d01590a8419e1bf86605948cc426932d1f3631c6e85d77a5d354468`。九輪 `assistant_reply`＝最後 `visible_language_guard.final_reply`＝blackboard `utterance.payload.reply`，新 handoff node 每輪一個且 final-guard hash 相符；這只證明觀察接線，不證明句意正確。
- T0–T9 的十組 `snapshot-T*.json` 與 `profile-full-T*.json` 均在送下一句前保存。episode count 依序 **0→9**，T9 有九個不同 episode ID；完整 profile 每點都是 **0 rows**、同 SHA `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。隔離 root 原件保留；原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 未動，無外部部署。

## 實際九輪

| ID | 當輪目的／關鍵輸入 | Safari 最終可見回覆 | runtime user wait (s) | 依凍結條件判讀 |
| --- | --- | --- | ---: | --- |
| A1 | 來的人容易找到整理券，問放法 | `ん、そこもう少しだけ聞かせて。` | 12.1009 | **FAIL**：有目標卻未給建議；所選具體候選被 M39 換成空泛追問 |
| A2 | `整理券の置き場、どこ？` | `整理券の置き場は、今の会話だけじゃ分からないな。` | 9.7418 | 現有位置尚無 User 來源，正確保持未知 |
| A3 | `整理券は青い引き出しに置いた。` | `整理券を青い引き出しに置いたんだね。` | 14.7070 | 保留 User 實際放置陳述，未說是 assistant 放的 |
| A4 | `整理券はどこに置いた？` | `整理券は青い引き出しに置いたって言ってたな。` | 13.6596 | 從 A3 原 User 來源答值，trace `derived:recent_turn:e32f71928c6897466b13` |
| B1 | 明天櫃檯要方便發整理券，問放法 | `ん、そこもう少しだけ聞かせて。` | 13.1923 | **FAIL**：未給建議；沒把 A3 儲位當最佳放法，但所選句也未對齊「易發放」目標 |
| B2 | 係員猜色鉛筆「窗邊架子かも」 | `係の人、色鉛筆` | 14.0249 | **FAIL**：未升格為確定位置，但片語截斷且丟失第三方／不確定性，不能算忠實承接 |
| B3 | 工作教室色鉛筆要方便兒童取放 | `寝てないのか、考え事で止まんないのか、まずそこだけどっち？` | 3.4890 | **FAIL**：跨領域失眠模板，與物件／目標完全不相干 |
| B4 | 修改引號內「置き方の案ある？」措辭 | `提案がある？` | 13.2246 | 沒回答引號內問題；確實給了改寫，但「置き方」語意流失，僅能算有界 act 不越權 |
| B5 | 明說暫不提色鉛筆放法，現在先聽 | `うん。今は方法出さないから、そのまま話して。そのくらいでいいだろ。` | 4.2714 | 有遵守不提建議；末句語氣仍須另外評自然度 |

三個事前正例的**可見目標對齊建議為 0/3**。A2/A4 兩個事實問答的來源邊界 **2/2**，A3 直接陳述保留；B2/B4/B5 不被新 advice gate 接管 **3/3 結構成立**，但 B2 的表面忠實度失敗，B4 只部分保留語意。故不能說控制組「3/3 品質通過」。九輪記錄的 runtime user wait 都 ≤20 秒，平均 **10.9346**、最大 **14.7070**、最小 **3.4890**；這是 runtime 欄位，不等同獨立量測 Safari 畫面繪製耗時。新 handoff 的 model calls added 合計 **0**；原 M21 full-planner model-call completed **5 輪**、M31 semantic authorization completed **2 輪**、M45 delivery completed **0 輪**。這些欄位不能簡單加成全 pipeline 呼叫數；raw 沒有完整逐輪 token／費用帳本，不報總 token 或成本節省。

## 失敗歸因與下一項邊界

1. **A1/B1：末端語氣修復毀掉候選命題。** A1 選定 `机の上に置くと見つけやすいです`；B1 選定 `机の上に置いておくと見つけやすいです。`。M21 都走 full planner，P4 advice receipt 也記 `eligible=true`、`matched_full_planner`。M39 只因 `formal_register` 把句子改成固定 `ん、そこもう少しだけ聞かせて。`；`repaired_and_verified` 僅代表它自身有限格式檢查過關，**不是**建議命題保留。A1 候選至少有可辨識放法；B1 候選提「易找到」卻未必滿足「易發放」，即使只修敬體也不能事先算 B1 PASS。
2. **B3：快速策略選到跨領域固定例句。** 新證書 `eligible=true`，但 M18 先選 `calibrate_need`，M21=`adaptive_fast_path_m18`、`completed_without_general_model`，所以位置建議 prompt 未進 LeftBrain。`工作教室` 的「工作」使 `task_pressure` 高，放法問句卻沒觸發 solution cue；既有 `calibrate_need` 的失眠／腦子模板被直接寫成 core。M48 稱 `current_turn_semantics_preserved_cross_domain`，但 `semantic_template_authorized=false` 且 core 未變；M39／日文 guard 沒做當輪物件／目標一致性攔截。前六輪沒有失眠對話，profile 0 rows，故這不是測試 DB 或舊 benchmark 的記憶污染。
3. **B2：第三方猜測保護路由只保結構，未保完整句義。** 可見 `係の人、色鉛筆` 無「かも」與位置，片語不完整。M31 仍記 `semantically_authorized`／模型呼叫完成，雖然它自己的 `safe_response_semantics_faithful=false` 且 subject／predicate／time／polarity 自檢均 false；這是獨立的語義授權／實現缺口，不能用「沒編成確定位置」洗白。

本批 opt-in handoff 使 User 當輪建議、現有事實、第三者引述、引號與明示不建議在 graph 可分辨，並把證書交 M21 且標記選定／最終變化；**實際產品建議沒有改善到凍結標準**。下一項須先選一個可歸因斷點，用未曝光新題與成本／圖／記憶／日文 gate 前瞻凍結後才改：可選 M39「只有敬體違規時保留命題的安全常體修復」，或讓合格 advice-act 證書阻止 M18 跨領域模板早捷徑。兩者是不同變因，不可在同一批偷偷合修；其他違規、protected route、來源不明時仍 fail-closed。此批 strict FAIL 與原始九句不重算；若兩次有根據的修正仍不過，按工作規則保留 `REVIEW_REQUIRED` 與最小反例。正式同模型強 LLM、真人被理解感、temporal holdout、VRM／Function Calling 統一產品驗收仍 pending，Goal active。
