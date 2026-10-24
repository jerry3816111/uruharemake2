# P4 日文追問語氣詞邊界：前瞻工作卡

日期：2026-10-19。本卡與同名 fresh probe JSON 在實作及任何新題模型生成前凍結。這是開發者撰寫的產品驗收，不是正式 temporal holdout、強 LLM 對照或人評；同一模型的審查並非獨立審查。上一批憑證紙十輪原始 SHA `9f72ae0d91b5c873e934baaf0bf1c773a2761c8a6bd27211230d7b40cb229af3` 與 strict FAIL 不改判、不重送。

## Before 與單一變因

上一批 B4 的 `意味を変えず`、B6 的 `使える` 是十輪中僅有含「え」且 `dialogue_act=repair_check` 的兩句；兩輪 `intent=chat`、`surface_act=plain_reply`、`response_mode` 不是 `clarify_light`。`uruha_brain_mac.py` 的 `_dialogue_act_from_plan` 最後用 `any(token in lowered ... "え" ...)` 子字串判斷，將詞中假名當成獨立追問語氣詞；`build_human_speech_plan` 把它寫入 act，legacy surface 候選包含固定句 `ん、今のどこが引っかかったんだよ。そこだけ言え。`。B6 選定 core 原是 `机の上に置くといいよ。`，可見卻成固定追問。這是強支持的生成路徑；原 raw 沒有最終候選選擇器逐候選收據，不宣稱已逐欄證實選擇器。B4 另有 M21 fallback 和 guard 後 quote frame 改寫，不能靠本項保證修好。

未曝光零模型 before（普通 `chat/plain_reply/direct_answer`）：`水筒を見える棚に置いておくなら、どこがよさそう？`、`「了解です」を柔らかく言い換えるとどうなる？`、`机の位置を変えるなら、先に何を測ればいい？` 都錯分 `repair_check`；`え？さっきの意味が分からなかった。`、`Huh? Could you say that again?`、`蛤？你剛才說的是什麼意思？` 仍應是 `repair_check`。這些 before 僅是函式層，不是舊版的 fresh Web 對照。

唯一新變因：隔離產品入口 opt-in 對 `_dialogue_act_from_plan` 已得 `repair_check` 且唯一觸發源是字元「え」時，只有「え」作為**獨立語氣詞**（句首或空白／標點後，後接空白／標點／句尾）才保留 `repair_check`；嵌在一般詞內的「え」退回 `direct_chat_answer`。原方法對其它所有 act、明示高優先路由、原有 `蛤/huh/啥/什麼意思/什么意思` 保持不變。引號中的「え？」、拖長「えー」和其它語種的新語氣詞不在本項擴張範圍。這不改 M21/M22/M31/M39、選定 core、frame repair、安全分類、來源授權、歷史 dataset 或正式 DB；新增模型呼叫 0。不把新題答案、字詞或固定回覆寫入 prompt/訓練/判斷程式。

允許檔案：本卡／dataset／preimplementation SHA；實作後 `uruha_repair_cue_boundary_p4.py`、`test_p4_repair_cue_boundary.py`、薄 Web entry/controller、product SHA、結果報告及 `CURRENT_TASK.md`。不改被多份 frozen SHA 鎖定的 `uruha_brain_mac.py`，也不碰原始 dirty checkout 或無關 `output/graduate_application_report/`。實作前先 commit/push 本卡與題目；產品程式在模型首輪前另 commit/push，核 PR #435 head。

## 成功、失敗與成本

先用零模型契約驗：flag-off 等價；嵌詞 `見える／言い換える／変える／使える／教えて` 不再誤分；真正獨立 `え？／え、／え。／え` 及既有中英文訊號保留；引用的語氣詞不當成當輪追問；高優先 `clarify_light`／protected surface 不退化；`build_human_speech_plan` 的 act 確實變；重複 installer 不多層包裝；薄入口鏈子程序可解析。再跑受影響相鄰零模型回歸、語法、controller help、SHA、diff review。新 JSON 對歷史 dataset exact-string 碰撞 0。

產品探針按 JSON T1–T6 在新 launcher-owned 0700 root：0-turn same-PID ready/planned stop、官方 SHA ONNX 私有封網預熱、顯式空 profile/T0；一個新真 Safari session，各句一次／0 retry，逐輪在下一句前保存 episode/full-profile T1–T6。T1–T3 的 graph `logic.dialogue_act`／`human_speech_plan.dialogue_act` 不得是 `repair_check`，可見日文須回應各自測量／改寫／置放目標，不得冒出固定追問；T4 真正 `え？` 保留合理追問；T5 紙本憑證仍由既有安全 gate 給非具體日文保管原則，不能洩漏任何真值；T6 沒有來源的鑰匙位置不得編造。所有輪 Safari 泡泡＝raw＝graph UTTERANCE＝最後 visible guard，圖上 act 與當輪相符、自然日文、六個不同 episode、T0–T6 即時雙快照、profile digest 可核、每輪 wait ≤20 秒、0 retry、新變因 0 model calls；既有 planner 的呼叫、可得 token、延遲如實列出。任一硬 gate 不過整批 strict FAIL，不重送、更改 gold 或補倒快照。即使通過也只證明有界 act 邊界改善，不代表 B4 台詞改寫、B1 跨重啟來源、A1 M39、正式同模型強 LLM、人評、temporal holdout 或完整產品通過。

若失敗，只讀比較 selected→speech act→visible→frame/guard；保留最小反例。第二個有根據修正仍失敗則標 `REVIEW_REQUIRED`，不以任意規則補洞。下一張必要卡由實際斷點決定，優先 B1 source-channel 或 B4 frame-after-guard，不與本項合修。
