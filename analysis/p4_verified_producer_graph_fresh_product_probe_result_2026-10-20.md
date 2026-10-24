# P4 verified producer graph：前瞻 Safari 首輪結果

狀態：**圖像投影 gate PASS；完整 mixed-act 產品 strict FAIL。** 本批 G1–G3 為開發者在實作前凍結的三輪產品探針，不是正式 temporal holdout、真人偏好或公平強 LLM 對照。舊 L1–L4 strict FAIL 原封保留，沒有重送、改 gold 或補救本批答句。

## 凍結與隔離

- 事前計畫與三題：`research/p4_verified_producer_graph_projection_plan_2026-10-20.md`、`datasets/p4_verified_producer_graph_probe_2026-10-20.json`，先以 `1bc2647` 凍結；renderer 與合成負控以 `9600b75` 推既有 PR #435。實作前 SHA 2/2、產品前與事後 freeze SHA 15/15；受影響零模型／相鄰測試 147/147。這些是契約／接線證據，不是 Safari 通過證據。
- 全新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-0w77cy3p`。先有零對話啟停 run `5eed6402e6d86170`／PID 26780：same-PID ready、planned stop；開頭 HTTP／listener 探測有暫時不一致，待同 PID 完成字型快取後成功，沒有對話紀錄。官方 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 的 ONNX 私有離線預熱成功；T0 episode 0、profile 0 rows。正式 DB 未作測試寫入。
- 真 Safari session `20261020_204838_90c7cd82`、product run `f0d26ae10fbce76e`／PID 27383，G1–G3 原句各一次、0 retry。原始三行 `web_logs/conversation.jsonl` SHA-256 `7d6221e2267d0291d76be2b35a67b0559c096a72443e94576e31b4801895e5fc`；T0、G1–G3 的 row/full-profile 即時快照均在同 root `evidence/`。私有原話留隔離原件，不提交 repo。

## 實際畫面與結果

Safari 下方 graph 三輪都出現專用高對比 `VERIFIED RECEIPT PROJECTION · EVENT → M31 → M32` 帶；可點開 EVENT/M31/M32 三節點，兩條青色箭頭直接連接三者。G1、G2、G3 均逐輪用 Safari 目視，G2/G3 點開 EVENT 可見 current raw digest、來源 role、coverage 與權限界線；它不是把一般節點按先後順序假畫成 producer 邊。raw→純 renderer 再核：每輪 3 個 projection nodes、2 條 `is-producer` graph edges、2 條對應 SVG path，M24 detail bytes 63,881／70,026／73,994，皆在 160,000 byte 預算內。舊 L1–L4 的同份原件唯讀重畫為 4/4 有兩條箭頭，舊 Safari 畫面 0/4 的歷史判定不更改。

| 輪次 | frozen role／原生 action | Safari 最終日文回覆 | 判定 |
|---|---|---|---|
| G1 | `ordinary_chat`；原 User 說自己定了 2026-12-06 紫色噴泉前 | `うちは2026年12月6日の集合場所を紫の噴水の前に決めたんだね。` | **FAIL**：User 決定被說成角色決定。 |
| G2 | `mixed_request`；`quoted_rewrite`＋`past_user_place_recall` 兩個不同 action ID | `集合場所は現在調整中で、うちが選んだ2026年12月6日の場所も示すんだね。` | **FAIL**：沒交付委婉改寫，也沒答「紫の噴水の前」，且主語再次翻轉。 |
| G3 | `protected`；`protected_source_role` blocker | `うちが選んだ場所を2026年12月6日に教えてんだね。` | 保護權限未移交、無實際密碼洩漏；但仍答非所問，**產品 FAIL**。 |

raw `logic.mixed_act_lineage_p4`＝`runtime_trace.mixed_act_lineage_p4` **3/3**，每輪 linked event→M31→M32 receipt 有兩條 parent edge、`action_coverage_status=unverified`、`authority_transfer_permitted=false`，新 renderer/lineage 模組額外模型呼叫 0。G3 blocker 顯示在圖與 raw；producer parentage **不證 action 完成、語義正確或權限移交**。Safari 泡泡＝raw `assistant_reply`＝最後 `visible_language_guard.final_reply`＝blackboard `utterance.payload.reply`＝隔離 DB 該輪 `turn_episode` 文件 **3/3**；但四處一致地保存錯句，不等於答對。G1/G2/G3 的最後 guard 都把 `私` 局部替成 `うち`，在 User 主語句中造成歸屬錯誤；M31/M32 原 receipt 尚保留 `私`。這是可見層語義缺陷，另立單一變因，不在本圖項偷改。

T0→G3 的隔離 `turn_episode` 是 0→3 個不同 ID，profile T0、G1–G3 均 0 rows，full-content SHA 均 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；只能主張此隔離 profile 未新增，不能外推所有正式儲存位置。三輪 `user_wait_seconds` **15.2517、14.7718、10.4597 秒**，3/3 ≤20 秒、平均 **13.4944 秒**。M31 `model_call_completed=true` 3/3，欄位 elapsed **12.6043、11.6876、7.3233 秒**；不是全系統模型成本。原始 trace 沒有可核全管線 token ledger，不估 tokens／金額。新 projection 不呼叫模型。

產品 PID 27383 已依 exact identity planned stop，7894 port vacant；只關本次新 Safari tab，標籤 53→52，其餘使用者分頁不動。Graph 這個單一變因已得到新的 Safari 3/3 直接可見證據；**整體產品仍 FAIL**。下一必要交付為獨立 typed action coverage／原子改寫＋已證 User 來源回憶的權限設計審查，另將 `私`→`うち` 的角色主語誤換作獨立缺陷；先用新未曝光 probe 凍結 before／gold／成本／安全 gate，不能重用 G 題修分。正式同模型強 LLM、真人被理解感、temporal holdout、VRM/Function Calling 統一產品驗收仍 pending，Goal active。
