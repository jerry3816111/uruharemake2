# P4-Y post-turn runtime graph trace delivery 驗收

日期：2026-09-22  
狀態：**PASS（deterministic unit／contract／synthetic full-Web integration）**；真實 Safari 尚未驗收。

## 修正的真正原因

P4-X 顯示同一輪 JSONL `logic` 已有 P4-T／P4-V／P4-W，但 Safari graph 三種 node 都是 0/4。原因不是 renderer：
三個舊 wrapper 在 `emit_response_if_ready` 時加 node，之後 `run_turn_debug` 又以 `self.runtime.blackboard` 做最後一次覆蓋，
所以 reply 與 logic 保留，runtime graph node 消失。

P4-Y 新增 additive product entry，於 `run_turn_debug` 完成最後 refresh 後，只把同一結果 `logic` 中已存在的三種 trace
投影到 `runtime_trace.blackboard`，順序固定為 P4-T → P4-V → P4-W → utterance。缺少的 trace 不合成；舊 duplicate／stale node
會先移除，再以目前 logic payload 取代。

## 凍結後結果

- `complete_clean`：3/3 exact payload，完整鏈順序正確。
- `complete_stale_duplicates`：3/3 exact payload，舊重複 node 歸零，完整鏈順序正確。
- `missing_extension_trace`：只交付實際存在的 P4-T、P4-W；P4-V 未被合成，狀態為 incomplete。
- 三案 visible reply 逐位元不變=`3/3`；logic逐位元不變=`3/3`。
- exact trace payload=`8/8`；duplicate=`0`；missing synthesized=`0`。
- 新增 model call=`0`；fact/profile/episode write=`0/0/0`。
- synthetic full-Web 路徑確認 Web 後續加入 scheduler／latency node 時，P4-T→P4-V→P4-W→utterance 相對順序仍保留。
- P4-M～P4-Y 受影響完整回歸=`227 passed`。

第一次用 system Python 單獨收集完整 Web 測試時，因沒有產品環境的 `colorama` 而 collection error；未安裝或修改環境。
改用既有 product site-packages 優先、system pytest 的既定方式後，完整回歸通過。這是測試環境依賴，不是產品邏輯重試。

## 尚未證明

本步只證明 post-turn graph delivery 的 deterministic integration。它沒有改 P4-X 的負結果，也沒有解決 P4-X 的命題遺失與
hypothetical ownership false negative；沒有證明真實瀏覽器一定收到節點，更不證明 trace 本身正確、felt understanding、
人類偏好、強 LLM 優勢或人類方程式。

下一個必要 gate 是以全新、非 P4-X prompt 做一次小型隔離 Safari graph delivery 驗收；通過後才進 P4-Z 命題保存，
兩者不能混成同一個變因。
