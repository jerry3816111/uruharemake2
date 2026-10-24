# P3-B73 prospective response-target protocol acceptance

日期：2026-09-20

## 結論

`PROTOCOL_TOOLING_READY / HUMAN RELIABILITY NOT STARTED`。B73已把B72失效的caption marker target替換成前瞻、分層、可盲化的
stimulus→response資料契約；沒有用新target回頭重評已曝光8列，也沒有開始新來源、prediction或真人標註。

## 已完成

- prediction view明確移除outcome；coder view只能看stimulus與真實response，看不到condition、prediction或winner。
- 無法辨認刺激—回應邊界的episode直接拒絕，不再自動落到default label。
- outcome拆成observable response moves、interaction goal、stance、literal/pragmatic relation及另存surface text；多個moves、alternatives、
  ambiguous均可表示。
- acoustics缺失時只能是`unavailable + null`，虛構語氣特徵會被validator拒絕。
- 兩位不同真人、各18 episodes；四個primary nominal Krippendorff alpha均需`>=0.667`且每欄至少兩個observed categories。
- synthetic一致／不一致／同人／不完整fixtures均通過預期分支，但synthetic明確不授權真人可靠度。
- 對照設計納入controlled context pair與literal/pragmatic context flip，同時測情境敏感與過度解讀。

## 證據與限制

受影響suite為27/27 passed。實際計數：新來源內容、prediction/outcome、model call、human label、production memory write=
`0/0/0/0/0`。因此B73只證明收集與計算契約ready；真人可靠度、felt understanding、system advantage、Uruha相似度與Equation V1
仍全部未證明。

下一步是以同一contract建立本機雙coder收集平台與隔離ledger；在真實pilot packet事前凍結前仍不得讓任何人先看內容。
