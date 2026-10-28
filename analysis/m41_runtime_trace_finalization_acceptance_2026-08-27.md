# M41 + M41.1：做過的檢查，現在真的能在圖上找到並回溯

完成的是「當輪認知證據的交付一致性」，不是新增理解能力。

## 原因與修正

M39/M40 在回覆階段加入節點，但最後的 `run_turn_debug` 又從 runtime owner
複製黑板，覆蓋回傳結果。結果是：摘要卡看起來正常，真正的節點卻不見了。
M41 把來源 payload 同步到擁有黑板的 runtime，再交給最後快照。

第一次 Safari 五輪證明主圖已有全部 9 個可用節點；但還發現同輪歷史副本未更新。
這個失敗沒有回寫消除。M41.1 是分開保存的小修正，只在 cycle 相符時更新最後
一份歷史副本，不動舊回合、不造缺少的歷史、不改回覆／策略／記憶。

## 實際證據

| 證據層 | 觀察 |
|---|---|
| 契約 | M41 6 項 + M41.1 3 項；重現最後快照覆写、缺來源、重複／過時節點、非 trace 內容不變 |
| 選定回歸 | 225 passed，3 個依賴棄用警告，22.76 秒 |
| M41 Safari | 5 輪，9/9 可用節點到主圖；實際展開 M40 與 M39 節點查內容 |
| M41.1 Safari | 2 輪，3/3 可用 payload 在 final logic、節點、歷史副本完全一致 |
| 缺來源 | self identity 回合沒有執行 M40，只留 M39；沒有補造 M40 節點 |
| 隔離 | temp DB/session/store，沒有 raw 測試輸入進 adaptive store；27 Safari tabs 未關閉 |

![實際展開的 M40 節點](/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance/analysis/m41_safari_m40_node_expanded_2026-08-27.jpeg)

這是第二輪的實際節點：舊判定 sexual_boundary、修正後無 boundary、排除一個
跨詞誤撞。不是額外製作的實驗結果網頁；它就在當輪 runtime graph 裡。

![實際展開的 M39 節點](/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance/analysis/m41_safari_m39_surface_node_expanded_2026-08-27.jpeg)

這是第三輪：M37 已確認的 task-stall → companionship 被重用，M39 顯示
repaired_and_verified；最後實際回覆是 `進んでないのか。まあ、今はうちがここにいる。`

## 沒有被這次修掉的事

- 認同後仍可能重問需求；日文「大丈夫」仍可能被「夫」誤判成婚姻要求。
- Web 在 brain snapshot 之後補上傳遞時間／scheduler 等資訊，所以整份 JSON 並非
  byte-identical。已驗證相同的是 M39/M40 當輪認知 payload，不冒充全部 telemetry 同步。
- 圖上舊的通用 category 仍把 route 類節點標成 PERSONA APPRAISAL；節點標籤與來源
  payload 正確，但外行可讀性仍需改進。節點圖仍偏擁擠，不稱完整展示 UX 已完成。
- 契約測試的 generation 是 fixture；Safari 是實際本機模型。二者不能混稱。

## 交付

目前本機入口是 `uruha_web_ui_m41_1.py`；live/voice 入口為 `start_uruha_live_m41_1.py`。
原 M37–M41 frozen files 未改；M40 formal 結果沒有重跑。無 commit/PR/merge、無部署。
報告索引：`m41_runtime_trace_finalization_web_evidence_2026-08-27.json`。

下一個核心工作是 CJK 關係邊界的來源證據：區分「字出現在詞裡」與「真的在對角色
提出關係要求」。再處理已確認支持不該被不確定性澄清覆蓋；不混成同一變因。
