# P4 reported-ack B 首發失敗後設計審查

狀態：同團隊只讀審查，非獨立放行；B 首批 strict FAIL 與 raw SHA `020de8e7a6b526e03b15f4f0a1a28bbaa2efc9bf6037786692ad86907e817c7e` 不變。題目、gold、前瞻 manifest 不重寫；舊 T5 不作修正後分數。

## 最小反例與精確斷點

T5 是同 DB 重啟後的普通第三者轉述。實際 A `admitted`、M31 `deferred_to_reported_ack_p4` 且無 M31 模型呼叫、M22 `general_conversation`、selected `ack_reported_check_instruction_p4`；B 卻 `not_applied/memory_or_profile_authority_present`，最後經舊 speech 的 `？。` 被語言 guard 降成泛答。B 的過寬拒絕位於 `uruha_reported_ack_selected_visible_p4.py` 對任何 truthy `memory_anchor` 的檢查。這輪 anchor 是 T1 自動檢索的 `episode/context`、`expected=false`；`memory_use_expected=false`、`memory_speakability=background_only`，explicit recall contract 與 profile grounding 均空。現行 runtime 在有 working-memory item 時可自動形成此背景 anchor；「被檢索到」並不等於「被授權為當輪答案」。

## 排除的草率修法

1. **直接刪除 `or memory_anchor`**：拒絕。`memory_use_expected=false` 仍不能證明先前記憶沒有「確認對象」；B 的現有候選句宣稱「何を確認するかはまだ分かんない」，若前文已知對象便可能是假話。T5 自動檢索的舊 T1 甚至與本輪同題型，不能靠 relevance 分數或 `background_only` 字樣當語意無關證明。
2. **只改候選句、不改 eligibility**：保護界線仍安全，但跨 session T5 會照舊被擋，沒有解決產品失敗。
3. **把 T5 改判不適用／重跑同句**：違反首輪前 gold 與 0 retry；不做。

## 可行的下一設計單元及前瞻門檻

需要把「記憶檢索」與「記憶答案權限」分成可追溯的權限契約，再讓 reported-ack 的候選只表達**當輪聽到的轉述**，不對全局記憶作「尚不知道」斷言。這是兩個互相關聯但可分別測的機制；不能把一次簡單 gate edit 冒充乾淨的單變因修正。先設計背景／顯性回憶／profile／事實 anchor 的權限表，驗證它與現有 `memory_use_expected`、source IDs、speaker scope 的一致性；再以全新、未曝光題凍結新的 B 驗收，至少含無記憶、僅背景 episode、前文已明示確認對象、顯性記憶提問、profile grounding、protected、混合直接請求與重啟。未知、缺欄位或互相矛盾時 fail closed。不能編造對象，也不能把背景 episode 的先前使用者說法當第三者當輪已確認的事實。

若無法用可核的單一授權訊號區分上述情況，B 保留 `REVIEW_REQUIRED`，先做獨立的記憶權限工程；不再在同一 B 批反覆加詞彙規則。T2 的 protected M31 主語錯、T3 的 frame shadow 警告與 T6 自介失敗另案處理，不能用 B 通過掩蓋。這份審查只定位因果缺口，不是產品修正或新的正面證據。
