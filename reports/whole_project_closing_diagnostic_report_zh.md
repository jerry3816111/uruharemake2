# UruhaBrain 全案結案診斷報告

- 生成時間：2026-04-25T05:02:20+09:00
- 工程收尾總分：**90.66 / 100**
- 研究擬人化分數（輔助觀察）：**84.8 / 100**
- 結案判定：**ready_to_close_v1_engineering_line**

## 1. 結論
- 以工程收尾角度看，這個專案目前可辯護地到達 **90.66 / 100**，也就是 **全案 90+ 可成立**。
- 以研究擬人化角度看，目前約 **84.8 / 100**；主要拖分項目是正式 ToM、10k 壓測表面多樣性、以及人工標記回歸資料不足。
- 最關鍵的左腦高頻 routing 主線已經完成，且 targeted readiness audit 為 **36 / 36 = 100%**。

## 2. 整體比分
| 子系統 | 分數 | 權重 | 判定 |
| --- | ---: | ---: | --- |
| 左腦高頻路由 | 96.0 | 0.24 | high |
| Runtime / Psyche 動態 | 90.0 | 0.14 | medium_high |
| 記憶 / 工作記憶 | 91.0 | 0.14 | high |
| Planner / 認知架構 | 84.0 | 0.14 | medium |
| 主腦整合 / Smoke | 91.0 | 0.12 | medium_high |
| Regression / Quality Gate 基建 | 95.0 | 0.12 | high |
| 文件 / 可重現性 / 收尾度 | 82.0 | 0.10 | medium_low |

## 3. 關鍵證據
- `leftbrain_audit_pass_rate`: 1.0
- `route_tests_passed`: 49
- `leftbrain_rule_tests_passed`: 82
- `core_module_tests_passed`: 14
- `smoke_test_status`: PASS
- `quality_gate_validator_status`: PASS
- `formal_tombench_accuracy`: 0.55
- `delayed_recall_rate`: 0.9167
- `working_memory_relevance_rate`: 0.9474
- `small_sample_diversity_unique_ratio`: 0.7604
- `stress_unique_reply_ratio`: 0.0431
- `stress_top_20_reply_concentration`: 0.3232
- `prompt_baseline_avg_score_delta`: 0.6851

## 4. 子系統診斷
### 左腦高頻路由 — 96.0/100
- 證據：
  - run_leftbrain_90_readiness_audit.py: 36/36 = 100%
  - test_leftbrain_rules.py: 82 tests PASS
  - test_route_logic.py: 49 tests PASS
- 強項：
  - 短口語 direct answer、follow-up、re-entry、topic shift、ambiguity fallback 已經穩定
  - no-punctuation clause conflict 與 weak override bucket 已清乾淨
- 剩餘缺口：
  - 高頻路由主線已達標，剩餘風險主要轉移到系統整體整合，而非左腦規則本身

### Runtime / Psyche 動態 — 90.0/100
- 證據：
  - route_match_rate=1.0
  - autonomous_runtime_success=1
  - autonomous_open_loop_turn_rate=0.4
  - runtime self_correction_rate=0.3871
- 強項：
  - 高低軌路由按設計觸發
  - 自主循環、三速記憶整理與 blackboard trace 存在
- 剩餘缺口：
  - 動態表現多來自 probe / runtime report，仍缺更正式的長時間 production-like soak audit

### 記憶 / 工作記憶 — 91.0/100
- 證據：
  - working_memory_relevance_rate=0.9474
  - delayed_recall_rate=0.9167
  - profile_capture_rate=1.0
- 強項：
  - 工作記憶 relevance 與 delayed recall 都高
  - episodic -> semantic/procedural consolidation 已有具體輸出證據
- 剩餘缺口：
  - 英文 recall 子集仍低於中日文子集

### Planner / 認知架構 — 84.0/100
- 證據：
  - bayesian_candidate_coverage=1.0
  - scratchpad_presence_rate=1.0
  - formal_tombench_accuracy=0.55
  - dailydialog_dialog_act_accuracy=0.2833
- 強項：
  - Bayesian candidate / scratchpad / working-memory budget 這些架構性指標很好
  - Prompt-only baseline 對比中，決策、邊界與角色一致性大幅提升
- 剩餘缺口：
  - 正式 ToM 只有 0.55，社會推理仍不是強項
  - DailyDialog act 對齊分數偏低，表示 planner 的一般對話行為標籤化仍不夠漂亮

### 主腦整合 / Smoke — 91.0/100
- 證據：
  - test_uruha_logic.py: PASS
  - py_compile on core modules: PASS
  - fast smoke harness build time ~0.02s
- 強項：
  - 主入口與 fast smoke path 持續可用
  - 模組抽離後沒有把 brain integration 打壞
- 剩餘缺口：
  - 仍偏 smoke-level 驗證，缺少更大範圍整合測試矩陣

### Regression / Quality Gate 基建 — 95.0/100
- 證據：
  - regression_panel_quality_gate_contract_validator.py: PASS
  - artifact / manifest / bundle / snapshot / snapshot index 已完成
- 強項：
  - 這條基建線成熟，可做 regression / artifact / snapshot 管控
  - 對整個專案的安全收尾很重要
- 剩餘缺口：
  - 更像 CI/CD 等級的全自動整合仍可以再往前推，但不是目前主要 blocker

### 文件 / 可重現性 / 收尾度 — 82.0/100
- 證據：
  - uruhabrain_system_paper_zh.md exists
  - README.md exists
  - multiple report json/md artifacts exist under reports/
  - uruha_config.py and uruha_planner.py compile but are currently untracked
- 強項：
  - 已經有論文草稿、README、報告輸出與多個 audit entrypoints
- 剩餘缺口：
  - 部分核心支援檔仍未納入正式版本控制，降低全案正式結案信心
  - whole-project closing report 直到現在才補齊

## 5. 目前最強的地方
- 左腦高頻 routing 現在已經是工程成熟區，topic shift / re-entry / ambiguity / clause conflict 都過線。
- 記憶與 working-memory 指標穩定，delayed recall 與 relevance 都高。
- Regression / quality-gate 基建成熟，專案不再只是能跑，而是可驗證。
- 和 prompt-only baseline 相比，雙腦系統在 relevance、emotion、boundary、in-character consistency 上有明顯優勢。

## 6. 目前最弱的地方
- 正式 ToM / 社會推理分數仍偏低（0.55），這是目前最明顯的研究側弱點。
- 10k 壓測下的表面回覆多樣性仍有限，表示自然語言表層變化不是目前最強項。
- human_feedback_regression_eval_report 目前沒有有效案例，真實人工 fail-case 閉環證據不足。
- uruha_config.py 與 uruha_planner.py 目前雖可 compile，但仍是未追蹤檔，降低正式 release 信心。

## 7. 正式收尾判定
- **工程角度：可以正式收尾。**
- **研究角度：不建議宣稱已經到學術前沿完成態。** 主要原因是 ToM=0.55、10k 壓測 unique ratio=0.0431、human feedback regression 目前仍缺有效真值資料。
- **最保守可對外說法：** 目前整體工程完成度約 **90.66 / 100**，左腦主線已成熟，剩餘工作屬於研究深化與證據鏈補完。

## 8. 若進入下一版，最值得做的四件事
- 若進入 vNext，優先打 ToM / social reasoning，而不是再繼續補左腦高頻規則。
- 補人工標記 regression dataset，讓 human feedback loop 真正有數據。
- 整理並正式納管 uruha_config.py / uruha_planner.py 的角色與整合位置。
- 針對多樣性做更結構化的 right-brain / surface realization 提升。
