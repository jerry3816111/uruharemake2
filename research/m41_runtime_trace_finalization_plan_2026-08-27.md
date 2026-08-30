# M41：讓真正執行過的檢查到達最後節點圖

## 單一工程變因

M39/M40 已把檢查結果寫在當輪 logic 與回傳 trace，但 `run_turn_debug` 最後用
`self.runtime.blackboard` 覆寫回傳 blackboard（`uruha_brain_mac.py:20344`），導致新增
節點消失。摘要卡仍從 logic 顯示，所以只看卡片的測試漏掉了這個落差。

M41 只修結果交付：將當輪已有且 schema 合格的 M39/M40 payload 在 emit 完成後，
一致地同步到 runtime blackboard、returned trace、snapshot 與當輪 history。
不改回覆、route、policy、記憶內容、M40 matcher 或任何 frozen 結果。

## 實作前驗收契約

1. 當輪兩個來源存在：圖上各有一個節點，payload 與 final logic 相同。
2. 已有節點：不重複；舊 payload 不可掩蓋當輪來源。
3. 缺少或 schema 不合格：不捏造「已執行」節點。
4. M40 位於 route classifier 前；M39 位於 utterance 前；連線沿用實際圖收集器。
5. reply、route、decision、memory writes 在同步前後不變。
6. 使用真實 `run_turn_debug` 最後快照流程，重現修正前缺節點，確認修正後仍在。
7. 在新的隔離 Safari session 核對節點、展開內容與 final utterance，不只檢查摘要卡。
8. 保留 M40 已發現的日文 `大丈夫` 被其中 `夫` 誤判為婚姻邊界，以及支持後重問；
   M41 不順便修這兩個語意／行動問題。

## 成功與限制

成功指 trace 對使用者展示的資料沒有在交付時遺失，不是新認知能力或模型優勢。
這是工程完整性契約，不需要另外創作語用題庫來包裝成 benchmark。
保留 M37–M40 frozen files；以新 module/entrypoint 實作，測試證據分開保存。
