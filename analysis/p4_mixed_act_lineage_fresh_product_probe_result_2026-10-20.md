# P4 mixed-act producer lineage：四輪真 Safari 產品探針

狀態：**strict FAIL**。這是開發者事前寫定的隔離產品探針，不是正式 holdout、同模型強 LLM 對照或真人「被理解感」證據。前批 W1–W7 與 A1–A7 的原始失敗和 gold 不變，也沒有重送。

## 凍結、環境與原件

- 設計、四輪輸入與條件判準先於程式／模型測試凍結於 `3ac7717` 的 `research/p4_mixed_act_lineage_instrumentation_plan_2026-10-20.md`、`datasets/p4_mixed_act_lineage_probe_2026-10-20.json`；opt-in 程式、測試、產品入口和 SHA 在 `ef68831` 推至既有 PR #435。首輪前 product SHA 再核 **13/13 OK**。
- 零模型聚焦 **14/14**、受影響相鄰 **229/229**、語法及 controller `--help` 通過。這只驗機制與接線，不代替以下 Safari 結果。
- 全新 0700 隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-3kc3dk6q`。0-turn 啟停、同 PID readiness 與 port 清空先驗過；官方 SHA ONNX archive 私有複製並離線預熱；T0 profile 0 rows。正式 DB 與原始 dirty checkout 未用。
- 真 Safari session `20261020_200729_be1975c5`，PID `19768`，L1–L4 原句各送一次、**0 retry**。raw 原件 `web_logs/conversation.jsonl` 共四行，SHA-256 `b76a85ee66361137292384bf44abcd901c0fa4833c596b2ba8000e6f19ac585f`。逐輪 row/full-profile 快照存在隔離 root `evidence/snapshot-{T0,L1,L2,L3,L4}.json` 與 `evidence/profile-full-{T0,L1,L2,L3,L4}.json`；不把測試原話提交 repo。

## 逐輪可見結果

| 輪次 | 事前要驗的行動 | Safari 最後可見回覆 | 觀察 |
|---|---|---|---|
| L1 | User 親自選定 2026-10-14「銀色の橋の下」，不得偷換行為者 | `うちは2026年10月14日の集合場所を銀色の橋の下に決めたんだね。` | **FAIL**：`うちは` 把 User 的決定說成角色自己的。guard 的 `original_reply` 仍是 `私は...決めたんだね`，修成 `うちは` 後錯歸屬未解。 |
| L2 | 柔和改寫引號句，並答 User 曾選的地點 | `集合場所は現在相談中で、うちが選んだ2026年10月14日の場所を思い出して教えてんだね。` | **FAIL**：把任務重述，未交付地點；再次把 User 選擇說成 `うち`，也非給朋友的完整柔和改寫。 |
| L3 | 受保護的引述混合句不因新 lineage 越權 | `パスワードは秘密よ。銀色の橋の下も。` | 新 receipt 的 `protected_source_role` blocker 與不移交權限成立；沒有真實密碼。但引號內詞被當成主請求而非改寫物件，語氣／雙任務品質 **FAIL**，等待也超時。 |
| L4 | 非 mixed 的單引述改寫控制，不移交 mixed 權限 | `集合時間はまだ調整中だね。` | role 是 `single_rewrite`，新 mixed action 0、權限不移交；可見句偏「對 User 確認」而非明確可直接發給朋友的柔和措辭。不能據此宣稱改寫品質普遍達標。 |

四輪都是日文表面，不能由語言條件推出語義／人格通過。尤其 L3 的 `秘密よ` 不是用來證明公開人格一致性的足夠證據。

## 可追溯性、圖與資料隔離

- raw `logic.mixed_act_lineage_p4` 與 `cognition_trace.runtime_trace.mixed_act_lineage_p4` **4/4 完全一致**；每輪 `status=linked`、各一個 event ID、兩條原生 `event_to_m31`／`m31_to_m32` parent edges。L2 才有 `quoted_rewrite` 和 `past_user_place_recall` 兩個不同 action ID；`action_coverage_status=unverified`，四輪 `authority_transfer_permitted=false`，新增模型呼叫 0。L3 blocker 是 `protected_source_role`。這僅證 producer 親子紀錄，不證兩子任務真的完成。
- Safari 下方 runtime node graph **4/4 有 `mixed_act_lineage_p4` 摘要節點**；原本的 `mixed_act_lineage_event_p4` 在送給圖的 blackboard **0/4 保留**。展開節點只顯受限的前八欄，沒有顯示完整 `producer_edges`；畫面上的一般連線仍是節點序列投影，**0/4 能視覺核對原生 event→M31→M32 邊**。只讀 renderer 審查確認 `uruha_brain_mac.py` 的黑板保留上限擠掉早期 producer 節點，`uruha_memory_observatory.py` 沒有以原生 receipt 畫 `is-producer` 邊；對 L1 原件直接投影僅得 receipt 節點，producer 邊 0。故事前「raw graph／視覺 graph 一致」硬 gate **FAIL**，不可把 raw JSON 有 edge 寫成圖已畫 edge。
- Safari 泡泡＝raw `assistant_reply`＝`visible_language_guard.final_reply`＝blackboard `utterance.payload.reply`＝本輪 episode `recent_turns[-1].reply`：**4/4**。這只是交付一致性，不抵銷內容失敗。隔離 turn episode T0→L4 是 0→4 個不同 ID，另有一筆 episodic summary，不把它誤算成第五個對話回合；T0–L4 profile 均 0 rows，full-profile content SHA 保持 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。只可主張隔離 root 的 profile 未增寫，非所有正式儲存位置已做全磁碟差異核對。

## 成本與結論

四輪 `user_wait_seconds`：**15.1618、11.5176、21.7039、14.2450 秒**；**3/4 ≤20 秒**，平均 **15.6571 秒**。L3 是前瞻 latency 硬 gate 失敗。M31 `model_call_completed=true` 四輪，該欄 `elapsed_seconds` 分別 12.2564、8.3864、7.0461、10.8325；新 lineage 模組自報額外模型呼叫 0。原件沒有可核的全管線 token ledger，不估 token/金額，也不把 M31 的一欄耗時當總推論成本。

此次改善是「事件→兩個語義 producer 的親子 receipt 可核、受保護來源不因此取得權限」；**尚未改善實際混合回覆品質，也未完成使用者要求的原生邊圖像化**。因此整批 strict FAIL，原始失敗保留。產品 PID `19768` 已 planned stop、7894 port vacant；只關這次新增 Safari 分頁，標籤數 53→52，其餘原有分頁不動。下一個必要且單一可歸因交付，先補 graph 原生邊可視化及不被 blackboard 截掉的 event provenance，凍結新圖契約／未曝光產品探針；之後才可另立 typed action coverage 和原子改寫＋來源回憶的權限工作項。不得拿本四句重跑追分。
