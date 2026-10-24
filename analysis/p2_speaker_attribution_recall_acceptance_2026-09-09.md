# P2 speaker-qualified quoted recall：bounded acceptance

日期：2026-09-09
證據等級：產品開發案例、隔離測試與本機 qwen2.5:7b runtime；不是 holdout、人評、正式 M56 結果或 open-domain memory QA。

## 解決的實際問題

同一個隔離產品流程先保存 `謝謝。不過現在請幫我想一個做法。`，之後在新 session 問
`「ありがとう」は誰の言葉だった？`。修改前最終回覆是 `ん、そこもう少しだけ聞かせて。`。

修改前 graph 已證明相關 episode 被選進 working memory，且原資料仍保有 `User:`／`Uruha:`；真正缺口不是記憶沒找到，
而是 planner 沒有「引號中的話由誰說」的 typed task，也沒有把跨語言 gratitude act 接回 speaker provenance。
凍結證據：`analysis/p2_speaker_attribution_recall_prechange_gap_probe_2026-09-08.json`。

## 唯一核心變因

新增產品限定 `uruha_speaker_attribution_recall_p2.py`，只處理中／英／日明確的 quoted-source 問句：

1. 一般字串只接受 normalized exact match；跨語言只接受目前明列的 `gratitude` semantic atom。
2. 只使用當輪 retrieval 已選入的 recent／working-memory evidence，不掃未選記憶，不讓模型猜 speaker。
3. 唯一 role 才回答；user 與 Uruha 都有證據時澄清；找不到時明確 abstain。
4. contract 帶 speaker role、match type、來源語言、digest、trace／memory ID；新節點不複製 raw dialogue，也不寫心理或長期事實。
5. factual/memory plan 走 deterministic route，最後日文 surface authority 位於既有 visible guard 之後；safety route 保留。

review 時發現第一版把跨語言 user gratitude 一律說成「中国語」。在正式收尾前修成依已選 utterance 的可觀察文字／marker
標示 `zh`／`en`／`ja`，並新增英語、日語來源回歸。這是同一 speaker-evidence contract 的正確性修補，不擴張任務範圍。

## 自動與整合證據

- focused：17/17 passed，6.79 秒；JUnit：`analysis/p2_speaker_attribution_recall_focused_tests_2026-09-09.xml`。
- affected adjacent：162/162 passed，40.91 秒；JUnit：`analysis/p2_speaker_attribution_recall_adjacent_tests_2026-09-09.xml`。
- 覆蓋 zh/en/ja 問句、user/Uruha 唯一來源、雙角色歧義、missing/unselected fail-closed、translation／meaning 排除、
  exact Japanese surface、safety 不覆蓋、graph idempotence／排序／連線、真實 `LeftBrain` 產品入口與 pending 不新增。
- 9 個既有 deprecation warning 來自 protobuf/pkg_resources/speech_recognition；本次沒有新增測試錯誤。

## 本機產品控制：修改前／修改後

最終結果：`analysis/p2_speaker_attribution_recall_local_run2_2026-09-09.json` 與同名 HTML。五個隔離 session、九輪，
四個結構 checks 全部 true；formal DB=false、formal holdout=false、human ratings=0、Safari=false。

| 指標 | 修改前 explicit-space run1 | speaker recall 最終 run2 | 觀察 |
|---|---:|---:|---|
| 目標 final | `ん、そこもう少しだけ聞かせて。` | `それ、あんたが言ったやつ。前に中国語でお礼を言ってた。` | 已選 episode 的唯一 speaker=user |
| 目標 planner | full planner | deterministic rule plan | 0 新增模型呼叫 |
| 目標延遲 | 8.744554 s | 1.532377 s | 此回合少一次一般 planner；下降 82.48% |
| 全九輪 OpenAI-compatible calls | 3 | 2 | 只移除目標回合的 planner call |
| 全九輪計入 tokens | 4,459 | 2,900 | 下降 34.96% |
| 全九輪 elapsed | 37.827457 s | 28.973048 s | 下降 23.41% |
| 結構 checks | 4/4 | 4/4 | 持久化、current graph、pending、calibration 皆保留 |

九輪可見回覆中只有目標回合改變，其餘 8/9 逐字相同。run1 是在來源語言修補前生成、也與最終目標回覆一致；
最終 run2 額外證明 graph 內 `selected_utterance_language=zh`。本機生成有 stochastic latency，故只把「目標 route 不再呼叫
一般 planner」視為機制因果；總時間與 token 是本次控制的觀察值，不外推成所有對話的性能提升。

## 圖像化資料流核對

最終 HTML 的 target graph 在 `selected_plan` 前有唯一且有連線的 `speaker_attribution_recall_p2` 節點：

`quoted source query → selected memory evidence → speaker-role join → unique-or-abstain → visible Japanese surface`

節點顯示：`resolved_unique_speaker`、`selected_speaker=user`、
`match_kind=bounded_crosslingual_semantic_atom`、`semantic_atom=gratitude`、
`selected_utterance_language=zh`、實際 episode trace/memory ID、`raw_dialogue_persisted=false`；下游 plan 為
`speaker_attribution_recall`，route 為 `factual_or_memory → deterministic_rule_plan`，最終 surface 與 contract 一致。
原本 episodic-memory 節點仍會顯示它所保存的對話內容；「raw-free」只指本次新增 contract 沒有再複製原文，不能說整頁無原文。

## 判定與限制

預先條件在 bounded scope 內全部成立。這證明 UruhaBrain 現在能把「已被取回且保留角色的記憶」接成一個可追溯的
跨語言話者回答，並在歧義／缺證據時不猜。它對人類方程式方向的實際貢獻，是把記憶內容、來源角色、當輪問題與可見回答
變成可檢查的中間變數，而不是只靠 LLM 隨機補一句。

它不證明 open-domain coreference、翻譯能力、一般 retrieval 優勢、長對話全面理解、Uruha 真人等價、被理解感的人類偏好，
也不證明已得到「人類方程式」。Safari 工具仍拒絕目前網址並終止控制階段，因此外部 Safari 操作／視覺驗收維持 pending；
離線 HTML 不冒充 Safari pass。

P2 五組既有產品控制現在各自有 bounded 修正／保守行為，但尚需做一次不新增機制的整批整合判定，確認它們共同存在時沒有
相互覆蓋，才可把這批 P2 產品控制收斂並進入 P3 同模型成本／效果比較。
