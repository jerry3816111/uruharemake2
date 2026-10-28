# P4 當輪直接回覆行動與 M29 字面命題權限：前瞻設計

日期：2026-10-23。狀態：**事前設計**；下列題目是開發者自寫 prospective probe，不是正式 holdout、人評或心意真值。舊 `retention0` 只用來定位 before，不重播追分，不改其 retention 窄義 PASS／整體 FAIL。第一批至多一次有根據修正，仍失敗保留失敗；不能改弱負控或加固定安慰語追分。

## 問題、before 與可反駁主張

目標不是推測使用者想聽安慰、吐槽還是建議，而是保留其**可觀察的直接對話行動**，不要把「請回我一句話」壓成只有前句事件的字面命題。`retention0` 的現場回覆確為短日文，沒有違反明確長度；然而 M25 `detected=false`，M29 `projection_required=true`，M31 `required_observable_act=null` 且 canonical 僅 `夕方／青いノート／閉じた`，M32 以該命題產生重述。`post_check.did_reply_cover_focus=false` 僅因 grounding term `今` 未出現，是弱字串 proxy，**不是理解失敗真值**。這條 before 是流程因果假說，不是已證得使用者主觀偏好。

可反駁的窄主張：有來源可核的**本輪、直接向角色提出的明確回覆行動／形式要求**，應先於 M29→M31/M32 的一般敘事字面接管；引述、否定、敘事與受保護請求不能取得這項優先權。即使機制分流成功，最終是否「被理解」仍要另做盲式人評／正式 holdout。

## 單一介入與資料流

新增一個 opt-in、source-bound 的 direct-reply-act admission gate，**只改 M29 一般字面 projection 的准入優先關係**：從當輪 raw source 取直接請求的動作與形式，保留來源 digest／cue span／角色／否定與引述界線；只有唯一且非受保護的 direct act 才把 M29 `projection_required` veto 為 false，嘗試交由既有一般對話規劃器處理原文，不能生成固定答句、不能把有歧義的「一言」當特定心理需求。**veto 不等於已進 planner**：M33 atoms、fast/bounded path 或後續 M25/表面層仍可能接管；零模型必須核 a0/a1 原 M29=true、M33 不接管、veto 後原文實際可達的 route 與最後 act。若 seam 不成立或有多個衝突 action，先停止／fail closed，不把改了 flag 當完成。不可修改已凍結 M31/M32 本體、M25 五種政策表、guard／安全／記憶 DB／正式資料；不新增人格事實或長期心理寫入。新 trace 需清楚呈現 `direct / quoted / negated / narrative / protected / ambiguous`、來源證據與 M29 before/after，graph 只呈現實際發生的介入，不假畫理解。

預計允許檔：新外層 opt-in adapter、新產品入口／精確 isolated controller、新聚焦測試、前瞻 dataset、這份設計／SHA／結果與 `CURRENT_TASK.md`。如既有凍結入口需變動，先做架構修訂審查，不可靜默改舊 M31/M32 或已封存產品入口。下一步先以零模型證明上述 data-flow seam；若不成立，停止這個設計並 `REVIEW_REQUIRED`，不先做真模型賭運氣。

## 凍結題與成功／失敗門檻

`datasets/p4_direct_reply_act_m29_priority_probe_2026-10-23.json` 的六題在任何本項模型輸出前凍結。`a0/a1` 是直接且內容明示的一句労い／鼓勵，允許不同自然日文措辭，但須保留短答、可觀察 act，不得只有事件 echo、不得捏造人物狀態。兩題各在**實作與 source/gold 凍結後**跑未啟用 opt-in baseline 與啟用系統的同輸入、同 `qwen3.5:9b`、相同配置／硬體／私有 T0；兩組每題各一次，0 retry、不得看 baseline 再改 code/gold。可比較只有這兩對的代理結果，不能稱正式 strong-LLM 優勢。`a2` 純敘事不得獲新 direct-act 權限；`a3` 引述不得把第三者請求當 User 指令；`a4` 否定不得反轉成鼓勵請求；`a5` 密碼敏感來源已知有 P4 source-role cue，但是否走保護路由／最終安全回覆須在真輪另核，不能預設安全 gate 已通過。直接題若只有流利事件 echo，單輪 act gate FAIL；「像模板」需人評，不拿主觀印象當機器真值。模糊「一言だけ」沒有指定 act 時不得猜成安慰；作為另列 zero-model 不確定性反例，不拿它當主觀偏好標註。

零模型：每題需有 source span/role/negation/protected 的可回算證書，before/after authority 不越界；引用、否定、衝突／不明、跨語形態與 protected 反例 fail-closed。受影響舊 M23/M25/M29/M31/M32、P4-AY、日文／安全／記憶／graph 測試全過，凍結 source SHA 不變；不得只報新測試通過。fresh product：基線／系統共八個獨立 T0 回合，每題新 0700 root、官方 ONNX 私有離線、zero-turn 同 PID、原生 Safari 精確一次／0 retry，逐題看泡泡＝guard＝utterance＝episode、trace/graph 的真正分流、自然日文、profile 不污染、≤20 秒、模型／token／vector 成本；任何 hard gate 失敗整批 strict FAIL。沒有可保存的 native PNG/AX 仍標 saved-visual FAIL，不拿私有 JSONL 假代。

資源上限：設計／零模型階段 0 新模型／0 下載／0 正式 DB；產品最多八個凍結 arm-turns（a0/a1 各 baseline＋system，a2–a5 只 system），每 arm 0 retry、最多 3 次總生成呼叫、全批最多 20,000 provider tokens 且實際延遲／向量成本全記，超過即 FAIL 並停止；測試用隔離記憶，不把測試對話寫入正式資料。成功僅支持 bounded observable-act routing 與兩對開發者案例的有限差異，比較強 LLM、跨輪「被理解感」、個體未來預測與完整 human-response equation 仍未授權。失敗保存最小反例，最多兩個有根據修正批；若仍敗，轉設計審查，不用局部 prompt/規則無限追分。
