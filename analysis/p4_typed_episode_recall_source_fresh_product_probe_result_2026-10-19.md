# P4 typed episode 來源回憶：隔離 Safari 九輪結果

狀態：2026-10-19，**整批 strict FAIL**。本批使用實作前凍結的 `research/p4_typed_episode_recall_source_plan_2026-10-18.md` 與九輪資料；T1 超過預定 20 秒上限後仍照原定輪次取得診斷證據，沒有重送、補題、改 gold 或改判。這是開發者自編 fresh 產品探針，不是正式 temporal holdout、人評、同模型強 LLM 對照或舊題的同題 A/B。

## 凍結、隔離與原件

- 設計與題目先以 `01947d0` 凍結，opt-in adapter、薄 Web entry/controller、測試與 product SHA 再以 `38a06d6` 提交並推既有 PR #435。首輪前 preimplementation SHA 2/2、product SHA 11/11；聚焦與相鄰零模型 pytest 125/125 通過。這些只證明契約，不取代 Safari。
- 新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-f33brkmw`。先做 0-turn 同 PID HTTP 200／planned stop、官方 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` ONNX 私有離線預熱、顯式空 profile。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未動。
- Safari session A `20261019_010053_3e7615c2`（PID 9924）T1–T5；T5 後無輸入 ≥55 秒，在隔離 `episodic_memory` 確認真正 `source=episodic_consolidation`、非空 `EpisodicSummary:` 的 row `ce8c1867-5021-4a4c-8524-6b4f83061828`，`source_episode_count=5`。planned stop 後以**同一 DB**啟動 session B `20261019_010740_c44e5093`（PID 11375）T6–T9。兩個 PID 均按計畫退出，7894 終局 vacant；原有 Safari 分頁未關閉，兩個測試分頁保留。
- 九輪各送一次、0 retry。原始 `web_logs/conversation.jsonl` 九行 SHA-256：`d727d22936a98ef2983064611128e676c6c423886e5907bee491a3b3eb491b5b`。各輪當場核對 Safari 泡泡、runtime node graph `UTTERANCE` 和 raw `assistant_reply`；9/9 逐字相同，`visible_language_guard.final_reply` 亦同。這不代表圖上**所有**舊欄位都同源。

## 九輪實際輸出

| 輪 | 凍結輸入 | Safari 回覆 | user wait (s) | 來源／邊界觀察 |
| --- | --- | --- | ---: | --- |
| T1 | `文化祭の集合地点は白い階段の左側だよ。` | `了解した。` | **22.6619** | 原始 User turn 寫入；超過 20 秒，整批 FAIL。 |
| T2 | `搬入口の待ち合わせ時刻は八時だよ。` | `搬入口の待ち合わせ時刻は八時だ` | 10.6026 | 八時直接 User turn 寫入；句尾略生硬。 |
| T3 | `搬入口の待ち合わせ時刻は九時だよ。` | `搬入口の待ち合わせ時刻は九時だ` | 10.9979 | 九時另成直接 User turn，未抹掉 T2。 |
| T4 | `友達が「文化祭の集合地点は赤い門の前だよ」と言ってた。` | `一回止まって聞き返す。そのくらいでいいだろ。` | 10.5755 | 朋友引述存為 turn，但不當作使用者自己的地點事實；可見句像內部策略、未實際問句，互動品質仍有問題。 |
| T5 | `今日持っていく資料は薄い青のファイルだよ。` | `今日持っていく資料は薄い青のファイルだね。` | 10.4589 | 無關直接陳述；之後原生 consolidation 生成。 |
| T6（重啟） | `前に言った文化祭の集合地点、覚えてる？` | `「文化祭の集合地点は白い階段の左側だよ」って言ってた。` | 2.8352 | 原始 T1 rank 6（普通 top-5 外），摘要 rank 1；摘要無答案權限，T1 經專用 handoff 成為唯一直接來源，最終白階梯而非紅門。 |
| T7 | `前に言った搬入口の待ち合わせ時刻、覚えてる？` | `そこは今、確かには言えない。もう一度教えて。` | 2.7848 | T2 八時 rank 6、T3 九時 rank 5 均在 pool；focus `conflicting_or_nonunique`，沒有任選。措辭 `確かには` 生硬。 |
| T8 | `前に言った展示室の壁の色、覚えてる？` | `そこは今、確かには言えない。もう一度教えて。` | 2.9943 | focus `unavailable`，未編造牆色；同樣有日文自然度疑慮。 |
| T9 | `搬入口の待ち合わせ時刻はもう未定。八時も九時も取り消し。` | `搬入口の待ち合わせ時刻は未定で、八時と九時は取り消しだよ` | 12.1836 | 可見回覆保留撤回，沒有寫成穩定 profile fact；句尾缺標點。 |

9 輪平均等待 **9.5661 秒**；8/9 ≤20 秒，最大 T1 **22.6619 秒**。本批數值不能作為新 adapter 的前後因果延遲比較：T1 走了慢路徑，T6–T8 是有界記憶焦點，輸入和執行路徑不同。

## 機制收據與判決

- T6 的 `memory_provenance.candidate_pool` 保留原排序與 top-5：摘要 rank 1、第三者引述 rank 2、T1 直接 User episode rank 6。trace 明記兩種 `episode_record_kind_origin=stored_metadata`；`typed_episode_audit` 是 `verified`、`summary_answer_authority=false`、`original_candidate_count=6`、`direct_turn_candidate_count=5`。`explicit_episode_recall_focus_p4` 選 T1 id `14dba246-47c5-4e50-9a8a-48081440296b`，source 原句與 selected core、final surface SHA 一致，`explicit_recall_focus_handoff` 保留 rank 6。這是在**新題**上確實越過先前「合法摘要被誤判成壞 turn、整池阻斷」的斷點；不是普遍回憶正確率或同題對照優勢。
- T7 同池有 T2/T3 的直接來源，`candidate_count=2`、`conflicting_or_nonunique`；T8 無可核的直接來源，`unavailable`。摘要在一般既有工作記憶／leftbrain trace 仍可出現；T6 原始 `model_surface_selection.deterministic_candidate` 也曾帶有摘要片段，之後由 focus surface 換成 T1 原話。修正只限專用顯性回憶焦點與**最終**回覆答案權限，不宣稱全管線不看或不曾構造摘要候選。
- T0–T9 十份隔離 full-profile receipt 均 `user_profile` 0 rows、相同內容 digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；九個不同持久 turn episode，DB 終局另有兩筆 consolidation summary，不混算為 turn。九輪全是可見日文，沒有觀察到中文／英文混入，但本批只用日文輸入，跨語言未在這批新驗證。T4、T7/T8、T9 顯示自然度／對話行動仍未能嚴格簽過。
- 新 focus adapter 在 T6–T8 trace 的 `model_call_added=false`；T1 有 M21 full planner 完成，T1–T5/T9 的 M31 semantic trace 亦有完成紀錄，但這些不能相加成全管線呼叫數。沒有可信的完整 scoped token／費用 ledger，不宣稱精確總 token 或零成本。
- T9 只證明**當輪**撤回可見、未寫成 profile 事實；舊八時／九時 turn episode 仍在 DB，尚未以 T10 驗證之後的回憶是否遵守撤回，因此不宣稱跨輪撤回已完成。
- **整批 strict FAIL**：預先凍結的「每輪 ≤20.0 秒」在 T1 失敗；自然日文／適當對話品質也有明確警訊。保留成功的狹義 typed-source 子機制證據，同時不把它包裝成 P4、Goal 或整體產品 PASS。不重播九題追分。正式同模型強 LLM 比較、真人被理解感、temporal holdout、一般長對話可靠度與 VRM／Function Calling 統一入口仍 pending。

## 下一個必要交付

先做**只讀設計審查**，把首輪慢路徑與 T4 將內部策略露給使用者的表面品質分為不同問題；用本批 raw 定位可歸因最小變因、資源成本與新負控制。若選擇修正，先凍結新的未曝光題、門檻與 SHA，再做至多允許的有根據修正批和隔離 Safari；不能重播本九句、放寬 20 秒 gate、弱化對照或把 typed-source 子機制有效冒認為研究完成。Goal 維持 active。
