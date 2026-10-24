# P4 direct-act planner handoff：零模型結果（真產品待驗）

日期：2026-10-23。這是同一 P4 工作項的程式／契約階段，不是新的 M、正式 holdout、真模型、人評或 Safari 結論。舊 `a0` 的同模型比較 strict FAIL 不改判；新凍結 `b0–b6` 尚未送出任何 fresh arm-turn。

## Before 與本項唯一操縱

先前真產品顯示 M29 direct-act veto 後會改走 full planner，但來源證書未進 planner；同時原 `a0` 兩臂使用不同模型／設定，無比較效度。新前瞻設計固定兩臂相同 M29 gate、full planner `qwen2.5:7b`、temperature 0.1、compact 256 token、同輸入與同資料；只在 treatment 送來源綁定的直接回覆行動約束。所估的是「已准入證書交給同一 planner」的狹義效果，不是整體 UruhaBrain 對強 LLM 的優勢。

## 已測機制

- `b0/b1` 的兩臂都由 M29 准入、M33 `not_applicable` 且真接線路由為 full planner。假 client 在 compact proxy **之後**捕捉的 request：同 model、temperature、max_tokens、JSON schema、timeout、User 原文與其餘 system 內容；treatment 只多來源 digest／requested act／不推測私人狀態的內部約束。無固定日文答句；off arm 沒有新 prompt 或 trace。
- `b2–b6` treatment 不准入 handoff；tampered source、M29、M33、certificate 均拒絕。共享同一 brain 的後續 control／敘事輪沒有沿用前一輪約束。`direct_reply_act_planner_handoff_p4` graph/logic 收據不含原對話，狀態只代表 planner 請求交付。
- 獨立只讀審查重現原共同 M29 gate 將 `母が言った。…一言だけ労って。` 錯認 User 直接請求；形態修正後，第二次審查又發現 `母に言われた／母から聞いた／母からのお願い` 等漏網。本項在真模型前作雙臂共同的保守 fail-closed 修正：先前發話／傳話／請託 cue 使來源 ambiguous、拒絕 handoff，即使某些實際 User 直述也會被保守排除；普通 planner 仍看原文。`母と仕事を終えた。…労って。` 非發話近鄰仍准入。規則不是完整日語來源解析，其他未列形式仍可能錯判。
- Web 額外 opt-in 私有同 PID receipt 讀 **活的** `brain.memory.client.get_settings().persist_directory`；不能讀時 unavailable，不退回 env。prewarm ready／reset／背景／human submission 完成後更新 path、session、reset generation、tick、finish count。只寫 0700 isolated root 下 0600 原子檔，不經公開 UI 傳 raw 對話。兩臂 controller 配置相同 prewarm／receipt。這只證可測量途徑；尚無真進程活 DB 路徑結果。

測試命令：

`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q test_p4_direct_reply_act_m29_priority.py test_p4_direct_reply_act_planner_handoff.py test_p4_product_active_db_receipt.py test_desired_response_mode_m23.py test_cross_lingual_explicit_desired_response_m25.py test_generalized_literal_topic_projection_m29.py test_semantic_authorization_m31.py test_semantic_commit_repair_m32.py test_compact_planner_p2.py test_user_visible_japanese_guard_v2_11.py test_progressive_runtime_graph_m24.py`

最終保守修正後結果：**130/130 passed，9 個既有套件警告，24.17 秒**。較小聚焦組在修正前是 49/49；不得把它當最後版本的獨立結果。尚需產品 source SHA 與 final diff review；所有上項都是 fake planner／Web contract 證據。

## 尚未通過的硬 gate

本項 fresh model 0/9 arm-turn、Safari 0/9；同 PID zero-turn active DB receipt、兩臂 T0 空 DB／ONNX 離線預熱、真模型／guard／selected plan／可見日文／episode／原生圖／≤20 秒／token 成本都 pending。`treatment_prompt_injected` 只證 request delivery，不是 selected plan 採納或最後回覆改善；原生 graph 的排序連線也不是因果證明。若無法保存 Safari 原生 PNG/AX，saved-visual gate 仍 FAIL。任何來源、DB、模型設定、路由、writeback 或安全 hard gate 失敗，整批 strict FAIL、0 retry，不拿小樣本改稱普遍優勢或真人被理解感。
