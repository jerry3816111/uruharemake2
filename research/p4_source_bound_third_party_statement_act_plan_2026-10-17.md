# P4 第三者直接陳述 speech-act：第二個前瞻修正批次設計

狀態：2026-10-17 設計先行；這是同工作團隊、非獨立審查。前批五輪
`599f1cd` 凍結資料與 `8e60093` strict FAIL 結果不改、不重播。

## Before 與單一可歸因變因

前批 T2 來源 `友達は紅玉りんごタルトが好き。` 是第三者肯定陳述；
M31 已抽出 `友達`／`affirmed`，卻授權並選中
`友達、紅玉りんごタルト好き？`。P4-T/V 有
`statement_changed_to_question`，P4-W 無對應修復；M32 因 grounded
anchors 不足拒修，最後 Safari 泡泡仍是問句。這是來源 speech-act
在取得 selected authority 前的缺口，不是 profile writer 錯誤。

唯一語義變因：對**完整、直接、非引文／傳聞／假設、單句日文第三者
`XはYが好き。`**，若 M31 回覆把同一個 X/Y/好き命題問回使用者，
且沒有先肯定承接該命題，該模型候選失去表面權。只從當輪逐字
來源取 X/Y，形成有界日文肯定承接 `XはYが好きなんだね。`，
同時填入選中 plan `core_message_jp` 與 M31 `response_jp`；保留模型
候選 digest、來源 hash、拒權與 deterministic repair 出處在內部 trace。
既有 M31 的已授權其他句子不變；不能拿缺欄預設 false 的
`surface_self_checks` 假裝模型已自判錯。修正後的 source-rule 檢查
可標明非模型來源，M32 不得再以舊缺欄將正確來源句覆蓋。最後
可見階段僅對本輪已標記的修正 plan 核對同一來源命題，不得把
任意陳述後的合理澄清問句一律改掉。

## 範圍、保護與驗收

允許修改：一個產品限定來源 speech-act guard、目前產品入口的
安裝線、相應聚焦／相鄰測試、當前任務卡與新前瞻 probe 文件。
不修改 M31/M32 核心研究實作、P4-T/V/W 的歷史規則、profile
writer、人格／日文 guard、舊 frozen input/gold/result、正式 DB、
原始 dirty checkout 或無關 `output/graduate_application_report/`。

先測純來源解析及模型候選：不同第三者／物品應從來源重建陳述；
本人偏好、真問句、否定、引文、傳聞、假設、複句／後置推翻、
來源 hash 不符、未獲 M31 authority 與「先承接再合理追問」須保留
原路或拒絕插手。再測產品安裝鏈，無模型完整 turn 注入壞 M31
候選：selected、M31 contract、最終可見句、graph utterance 相同；
profile 第三者 0 寫，本人偏好／關係問句與 protected routes 不退步。
先聚焦測試，後受影響相鄰回歸與隔離 0-turn check。

完整產品層須另選未曝光的新 X/Y，先固定逐字 input/gold、0 retry、
20 秒每輪等待上限、profile row-ID、真 selected／Safari 泡泡／graph、
一次同庫重啟、freeze SHA／commit，才可呼叫模型。保留包括
「T4 類無前文 `また`」在內的其他表面風險；不以新題修它。
若第二修正批次 strict FAIL，交 `REVIEW_REQUIRED`，列反例、
可撤回／簡化選項，不進第三輪追分。

本變因最多能驗證一種第三者直接陳述的來源語義穩定；不代表
跨語言／開放域語用理解、強 LLM 相對優勢、真人感受、正式
temporal holdout 或完整 P4 已通過。實際模型呼叫、token、延遲
缺值須逐項如實記。
