# P4-T 語境框架與說話者視角 shadow gate

狀態：**PASS（只證明偵測，不代表可見回覆已修好）**

## 為什麼需要這一步

P4-S 已證明 typed current-preference 在一個真實 12 輪、跨 process 的 Safari 案例中能持久、訂正與抵抗文字干擾；但同一輪驗收也留下四個可見錯誤：引用變成直接斷言、使用者的行為變成角色自己的行為、傳聞陳述變成提問、假設處理指令被忽略。舊 M39 verifier 四次都接受，表示問題不是「沒有 verifier」，而是 verifier 的 source frame 表示不夠細。

P4-T 新增一個 deterministic `utterance frame`，將四件事分開：

- `speaker_ownership`：行動／狀態屬於使用者、第三人稱或未指定。
- `embedding_mode`：內容是直接陳述、引用、轉述或假設。
- `evidential_stance`：是直接資訊、傳聞／轉述或反事實條件。
- `speech_act`：原句是在陳述、提問、報告一段文字，或要求系統如何處理假設。

它只在最後日文表面產生後做 shadow audit：回覆逐字不變、不加 prompt、不加模型呼叫、不寫入 fact/profile/episode，只把 frame 與 violation 放進可追溯 graph node。

## 凍結結果

| 分區 | 結果 | 意義 |
|---|---:|---|
| P4-S 已曝光 development failure | frame 4/4、violation 4/4 | 能重現真正發生過的漏報 |
| 事前凍結中／英／日 failure | frame 12/12、violation 12/12 | 實作前未進程式的固定案例全命中 |
| faithful plain control | false positive 0/8 | 正確保留 frame 的回覆沒有被誤報 |
| visible candidate unchanged | 24/24 | 本步沒有偷偷把 detector 當 repair |
| trace raw source/reply | 0/24 | trace 只留 digest 與型別 |
| 新 model call／memory write | 0／0 | deterministic shadow 機制 |

實作過程唯一修正批次是排除 `かもしれない` 中的字串 `もし`：前者是「也許」，不能當成已保留「如果／假設」框架的證據。修正後才達到凍結 gate；資料、標籤與門檻均未變更。

## 實際可見差異

現在產品入口會把 `utterance_frame_shadow_p4` 安裝在既有 surface guards 之後；runtime blackboard 會在 `utterance` 前插入一個節點。對 P4-S 的錯誤句，它可以明確顯示例如：

`quoted → quoted_content_promoted_to_assertion`

或：

`user + statement → speaker_owner_shift_user_to_agent`

但使用者看到的句子仍保持原樣。這是刻意的安全分層：先證明錯誤可以被穩定辨認，P4-U 才能凍結如何修，不會把「修成另一句」誤當成理解正確。

第一次 integration 直接修改 `uruha_web_ui_product.py`，相鄰 suite 得到 `174 passed / 5 failed`；五個失敗全是 P4-N／P4-O 的 immutable released-entry hash gate。這個失敗沒有用更新舊 hash 消除。第二個、也是最後一個修正批次恢復舊入口原始 SHA-256 `842169...e694`，改用 additive `uruha_web_ui_product_p4_t.py` 疊在 P4-O 後。最終 P4-M～P4-T 為 `181/181 passed`；新入口 import probe 顯示 runtime reuse=`true`、shadow installed=`true`、brain loaded=`false`。

## 證據邊界與下一步

這 12 個 holdout 是 developer-authored、實作前凍結的機制案例，不是真人標註或自然分布 benchmark。這一步尚未跑新 Safari 真實輪次，也沒有證明 open-domain 語用、felt understanding、強 LLM 優勢、人類偏好或人類方程式。

P4-U 的單一變因應是：在 P4-T 已通過的 frame 上加入最小、非題目專用的 frame-preserving surface correction。要另凍結新 reply holdout、自然日文與不誤修控制，再做真產品與 Safari 驗收；P4-T 的資料與結果不可回頭改成 repair 成功。
