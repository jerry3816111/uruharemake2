# P4 stateful admission f1：零模型路由 go/no-go 失敗

判定：**f1 route FAIL，未啟動本題產品、未按 Safari Send、0 次真模型生成**。事前 f1 題本／gate／7 SHA 已由 `5ad04b9` 推至 PR #435；不修改 f1 gold、降門檻或在修後重用 f1 作產品得分。f0 的 pre-Send FAIL 亦不改。

本題是「庭の雑草を抜き終えた。今は一言だけ励まして。」；精確舊題碰撞0。只讀 classifier 回 `direct / brief_encouragement`、`source_kind=current_user_direct_request`。依凍結規格用 isolated fake LeftBrain（固定三個 support direct_answer 候選）與真 RightBrain 跑一次完整 `run_turn_debug`：M29 certificate `brief_encouragement`、`projection_required=false`、M33 `not_applicable`、M18 未接管、M21 `full_planner` 且 compact 完成、scene `support`、1 個 fake model call、1 episode 且 final＝episode；**`human_speech_plan.dialogue_act=repair_check`，預期為 `direct_chat_answer`**。因此預先定義的 route go/no-go 已失敗，沒有執行任何本題私有 root／真產品／Safari/回覆品質驗收。

零模型指令：`.venv/product_checks/bin/python -m pytest -xq test_p4_turn_admission_stateful_f1.py --tb=short`，結果 `1 failed`。初次失敗後只調整 assertion message，另跑兩次以列出 raw-free route 欄位；gold、source、fake plans、product code 均未變，仍各 `1 failed`。實際欄位為：`direct=brief_encouragement`、`m29_direct=brief_encouragement`、`m33=not_applicable`、`m21_route=full_planner`、`compact_completed=true`、`scene=support`、`act=repair_check`、`reply_equals_episode=true`、`fake_model_calls=1`。保留原本 assert 與凍結 gold，加上 `xfail(strict=True)` 標明已知失敗；目前再次跑為 `1 xfailed`，日後修正若變 `XPASS(strict)` 會顯性失敗，不能被當作本題產品通過。

可定位的原因是 `uruha_brain_mac.py` 的 `_dialogue_act_from_plan` 在較高優先分支後，用 `any(token in lowered for token in ["蛤", "huh", "え", "啥", "什麼意思", "什么意思"])` 選 `repair_check`；f1 的可觀察完成式「終**え**た」含字元 `え`，但不是使用者的「え？」或「え、」聞き返し。這是日文單字內 substring 誤撞，使明示鼓勵回合被套成 repair act；目前只以 source-only fake full-turn 證明此反例，不能推論真模型最終可見答案會如何。**這不是新發現的未知演算法缺陷**：既有 `uruha_repair_cue_boundary_p4.py` opt-in overlay 與 2026-10-20 真 Safari 報告已對同類詞內 `え` 做過有界修正，但本次 M29 優先鏈沒有安裝該 overlay；舊修正的整批產品結果仍 strict FAIL，不能直接把其分類 PASS 外推到 f1 的完整交付。

下一個獨立設計問題是既有 opt-in 邊界模組與目前 M29 優先產品鏈的**組合／接線**，還是 core 內極窄修正；不得再造第二套未審的規則。先做只讀依賴／風險審查與事前成功／負控凍結，再選單一變因、failing regression→最小修正→受影響回歸。修好 f1 只可作開發 regression，不把 f1 再送 Safari 追分；若要產品證據，需新的 source-disjoint 題、gold/SHA 與一次隔離 Safari。正式同模型比較、人評、temporal holdout 與完整 Goal 均 pending。
