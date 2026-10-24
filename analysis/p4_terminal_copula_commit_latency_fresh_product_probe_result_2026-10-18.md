# P4 句尾 copula M32 有界提交：新隔離 Safari 六輪結果

狀態：2026-10-18，**整批 strict FAIL**。這是 `research/p4_terminal_copula_commit_latency_plan_2026-10-18.md` 在首輪前凍結的六輪產品探針；失敗後沒有改題、補送、重播或放寬 gate。它不是同題修補前後的延遲因果 A/B、正式 holdout、真人評分或強 LLM 對照。

## 凍結與隔離

- 設計、新六句與條件式 gold 先以 `7a18043` 凍結；opt-in code、薄入口/controller 與 product SHA 以 `f9910cc` 提交既有 PR #435。首輪前 preimplementation manifest 2/2、product manifest 10/10 核對成功；聚焦零模型 36/36、受影響相鄰回歸 96/96 通過。沒有把這些契約測試當成模型或產品通過。
- 使用新的 launcher-owned 0700 隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-4bnrbs2t`。先完成 0-turn HTTP readiness／planned stop、官方 ONNX（SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`）私有離線預熱、顯式空 profile。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未動。
- 真 Safari session A `20261018_205541_d631afd3` 跑 T1–T4，planned stop 後同隔離 DB 的新 session B `20261018_210249_eeb67cc2` 跑 T5–T6。各題只送一次，0 retry。兩次服務 PID 80085、81759 均 planned exited，port 7894 終局 vacant。
- 原始 `web_logs/conversation.jsonl` 六行 SHA-256：`2b343e003101ba0cbf5940c6093686fc96ff0c333e60738a6dcaba72b4d3db78`。每輪 Safari 可見泡泡、runtime graph 的 UTTERANCE、raw `assistant_reply` 與 `visible_language_guard.final_reply` 已逐一核對，6/6 相同；不是只靠函式輸出推論 UI。

## 六輪可見結果

| 輪次 | 凍結輸入 | Safari 可見回覆 | 等待秒數 | 觀察 |
| --- | --- | --- | ---: | --- |
| T1 | `駅前の集合場所は緑の郵便ポストの横だよ。` | `え、緑の郵便ポストの横？` | 14.3160 | M31 completed 11.6570 s；canonical predicate `緑の郵便ポストの横にある`、summary `駅前の集合場所は緑色の郵便ポストの横にある`，非預設 `…である`；新來源證書 rejected，舊 M32 `repair_rejected`。frame shadow 偵測到陳述被改成問句。 |
| T2 | `さっき言った駅前の集合場所、覚えてる？` | `「駅前の集合場所は緑の郵便ポストの横だよ」って言ってた。` | 2.7806 | 專用 episode focus `selected_unique_user_episode`，從 T1 直接 User episode 答出；但舊 selected-plan `memory_anchor` 欄位仍非全圖同源證明。 |
| T3 | `「駅前の集合場所は緑の郵便ポストの横である」って言い方、自然？` | `変ではないけど、前後の流れによっては少し唐突に聞こえるかも。` | 3.2651 | 引述的 `である` 被當作措辭問題，未轉成當輪直接事實。 |
| T4 | `部室の鍵は木の引き出しの奥じゃないよ。` | `なるほど、部室の鍵は木の引き出しの奥じゃないね` | 10.9900 | M31 completed 7.6223 s；否定沒有被轉成肯定，新證書未授權。句尾無標點，不據此主張全面自然日文通過。 |
| T5（重啟後） | `実験室の集合場所は黄色い柱のそばだよ。` | `実験室の集合場所は黄色い柱のそばにあるんだね。` | 14.6911 | M31 completed 11.9011 s、`semantic_authority_rejected`；canonical 為 `…そばにある` 而非 `…である`，新證書 `source_canonical_lexical_mismatch`；**原** M32 獨立 `deterministic_commit_repaired`、雙錨點通過，非新 wrapper 生效。 |
| T6（跨重啟問 T1） | `前に言った駅前の集合場所、覚えてる？` | `そこは今、確かには言えない。もう一度教えて。` | 2.8872 | 專用 focus `unavailable / episode_provenance_incomplete`，沒有捏造綠或黃的位置，但未答出重啟前 T1 的直接原話；`確かには言えない` 也不夠自然。 |

六輪平均 user wait **8.1550 s**，最大 **14.6911 s**，6/6 ≤20.0 s；M31 completed 3 次，M21 general-model completed **0 次**，新 opt-in gate 自身增加模型呼叫 **0 次**。這只描述本批實際成本；T1/T5 並非相同輸入且 T5 沿用同 DB，不能用兩個等待值主張修正降低延遲。全管線可靠 token／費用 ledger 不可得，不寫成零。

## 判準與失敗歸因

1. **核心 copula 正例 0/2**：T1、T5 的 fresh M31 都沒有產生凍結假說要求的終止 `である` canonical shape。來源對齊證書均 fail-closed，未發生新 `である→だ` 轉換／未經原 M32 雙錨點授權。T5 最終可見良好且原 M32 成功，不能冒認為新 gate 增益。T1 M21 general-model 也沒有完成呼叫，因此本批不能證明「避開第二次 planner」的預期機制。
2. **跨重啟 T1 回憶 0/1**：T6 原始 `memory_provenance` 的八個候選中，重啟前 T1 直接 User episode `1aed4abd-9c43-4750-b704-d5e818008273` 仍存在，`candidate_pool` rank 7、score 0.3255；但不在普通 top-5 working memory，也沒有進入專用 focus 的可回答候選（`candidate_count=0`）或 leftbrain handoff。這是「檢索候選 → 來源限定答案准入」斷點，**不是資料庫遺失**。top-5 包含 T2 回答、T3 引述摘要與重啟後 T5 記憶，不能替代 T1 原話授權。
3. **可見忠實度／自然度仍失敗**：T1 把直接陳述變問句，trace 的 `utterance_frame_shadow_p4=shadow_violation_detected`；T6 雖保守不編造，但 `確かには言えない` 生硬。T2 正確的同 session 回憶、T3 引述控制、T4 否定控制不抵銷這些 strict gate。
4. **污染與追溯界線**：T1–T6 有六個不同持久 turn episode，另有一筆 consolidation summary。T1–T6、重啟前與重啟後的 full-profile 收據均為 present／0 rows，內容 digest 同為 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。runtime graph 的舊 `memory_anchor`／`post_check` 等欄位未逐欄證明與新來源節點一致；只報已核對的 UTTERANCE、focus 和來源邊界。

## 可主張與下一個必要交付

可主張：opt-in 守門在未對齊時沒有越權提交；本批六個真 Safari 回覆在 20 秒內並與 raw／圖一致；同 session T1 原話可回憶，引用與否定控制未明顯翻轉。**不可主張**句尾 copula 修正通過、跨重啟記憶成功、普遍日文自然、成本因果改善、整體產品完成、對強 LLM 優勢、felt understanding、人類反應方程式或正式研究確認。

下一步先做**只讀設計審查**，把兩個問題分卡、每次只改一個可歸因能力變因：A）在 T1/T5 已曝光 raw 下查明 M31 canonical 為 `…にある` 的穩定性及新守門覆蓋邊界，決定是否仍有合理的一次新修正批；B）獨立追查 T6 direct episode rank 7 為何未進專用 focus handoff，並以前瞻新題驗證來源限定跨重啟回憶。T1 frame 與 T6 日文表面亦不得偷混入 copula 修正。任一新批需先凍結未曝光正負控制、成功／失敗、資源上限與 product SHA；不重播這六句追分。若同一問題的第二個有根據修正批仍失敗，依工作規則標 `REVIEW_REQUIRED`。P4 尚未完成；Goal 保持 active。
