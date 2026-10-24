# P4 句末標點前瞻計畫：路由 go/no-go 補充 1

原 source-only 計畫與題本已在 `77434bd` 凍結。獨立只讀審查在**任何本項 code 或新題模型生成前**指出：只有 `_speech_plan_variants` 單元向量，不能確保新作者題進入真正的 `support + direct_chat_answer` legacy 分支；P2 若先接管，也會使本項在真 Safari 變成 `not_exercised`。原計畫／dataset／5 SHA 保持原字節，不後改結果或降低原 hard gate。

因此在真 Safari 之前加一個必須通過的零模型 go/no-go：新題以隔離 fake client 跑完整 `run_turn_debug`，需有 M29 `brief_encouragement` direct certificate 與 literal veto、M33 不接管、M18 不接管、M21 full planner、compact completed、P2 `support` 不接管、`human_speech_plan.dialogue_act=direct_chat_answer`，且 selected core 以 `！` 結束，最後 raw `_speech_plan_variants` 實際經此修正分支。假 client 固定三個 valid 候選只是機制注入，不是現實模型輸出或品質 gold。任一條失敗即**不得**送新題 Safari；保留失敗並先重審，不能換題、調模型或把 `not_exercised` 算 pass。

受影響測試需明確涵蓋 `support + direct_chat_answer` 的變化及其他 protected dialogue acts 不變；直接畸形 `！。`／`？。` 仍由 guard 拒絕。`。。` 可能在下游 sanitizer 自動合併，故其 raw variant 改善不得宣稱可見品質改善。真 Safari 仍以原計畫的 Tpre/Tpost tick0、自然日文、可觀察進展、鼓勵、成本及圖像 gate 判定；此補充不授權重播 d1 或正式 holdout。
