# P4 可見記憶承諾與本人 profile 准入一致：事前設計

狀態：產品缺陷修正計畫；開發者自製驗收，非正式 holdout／人評／強
LLM 比較。此計畫在新產品程式與新 Safari 生成之前固定。前項已曝光
十輪原樣 FAIL，不重播追分、不改前項 freeze／資料／結果。單一核心變因
是 **P4-H「記住你的偏好」plan／surface 必須受 P4 owner 准入約束**；
不是擴寫 profile 抽取器、來源問答、模型、人格 prompt 或記憶 schema。

## Before 與最早失真

`analysis/p4_profile_owner_fresh_product_probe_result_2026-10-01.md` 的 T9
使用者轉述朋友傳話，P4-I 的顯式偏好分類仍 selected。P4-H 的 plan／
visible guard 在 profile writer 前，將最終句固定為
`ん、その好みは覚えとく。`；後續 P4 owner 才以
`selected_source_has_unresolved_preamble` 拒寫，graph `admitted_count=0`、
`profile_collection_count_delta=0`、`writer_not_invoked`。故錯誤先在
**plan／surface 提早承諾**，不是准入或 DB 再污染。舊 raw JSONL SHA 為
`85f255dd1ec2cac06bc7ae54261f59dce943e485c5c777e6a52d94358ec7ae43`。

## 允許的介入與不可碰邊界

只新增 additive 產品 overlay、入口、必要安全 launcher、聚焦測試、
新前瞻 source-only dataset／freeze／結果，並更新 `CURRENT_TASK.md`。
優先重用 P4-I 的顯式 act 擷取與 P4 owner 的**同一純函式**准入決策：
若 selected act 的來源未證實是本人，就在 planner 選「不把這個當作
你的偏好記住」，final 使用簡短自然日文非承諾句；正常本人 write／
correction 保留既有 P4-H 日文、既有 writer 與 episode。可見回覆前
再以實際 writer audit 核對 plan／surface／graph；核對未通過必須
明確 fail closed／留下 mismatch，不得顯示虛假的成功或把預檢當成
持久化證明。safety、VRM/function、source recall 與非選中普通聊天
保持既有 authority。

**凍結前的獨立 review 補充（同一承諾真實性 gate）：** P4-I correction
的 writer 另有 read-only、取決於既有 profile 的前置條件。舊值若同時
存在兩個 active scope，無明示 scope 的訂正會以
`old_value_has_multiple_active_scopes` 拒絕 typed 寫入；**獨立 writer-only
隔離預演更發現其後 fallback legacy 竟新增一筆錯誤的本人偏好**。
單靠純文字 owner 准入會在保存 episode 前錯誤承諾並污染 profile。
新入口須在 planner／surface 前用與 writer 同源的 resolved profile
active rows 檢查這個條件；已知 state-blocked 時，先選非承諾回覆，
episode 照存、typed writer 照常報出 `ambiguous_extraction`，但新
additive overlay 只對同輸入 hash、同一多 scope 理由的 legacy
fallback 做 no-op，阻止錯誤第二次寫入。graph 必須分開記純文字
owner 准入、typed writer 拒寫、legacy fallback suppression 與實際
profile delta，不能把前者冒充持久化成功。無法可靠讀取時也不得
承諾。此狀態檢查仍只服務「可見承諾
與准入一致」一個變因，不改 P4-I writer 或核心交易順序。意外 DB
寫入失敗仍只能在
writer 後拒絕 UI 交付並保留 mismatch；已保存 episode 無法用這項
事後改回覆，屬明示限制。

不得改 `uruha_brain_mac.py`、已凍結 P4-H／P4-I／P4 owner／source 模組、
舊產品入口、舊 dataset／freeze／raw／result、正式 DB、原始 dirty checkout
及無關 `output/graduate_application_report/`。如果必須改核心 save/write
順序或回寫舊 episode 才能閉環，先停於設計審查，不自行擴張。

## 成功、失敗與成本判準

- 聚焦正例：中／英／日明確本人偏好寫入、明確訂正皆保留原有自然日文
  承諾、profile 值／scope／history、原 episode 與 graph；拒絕不能
  把所有記憶關閉以拿安全分數。
- 聚焦負例：朋友傳話、引文／作文、第三人稱、P4-H cue 有但 P4-I
  value 不唯一；P4 owner 零寫時，plan 與 final 都不能說已把內容
  當作**使用者本人偏好**記住；graph 顯示來源 hash／拒絕理由、
  預檢與實際 writer outcome，不能留一個相反的 P4-H 成功節點。
- 非目標：未選中一般聊天、protected route、Function Calling／VRM、
  explicit past-source query 的 final／memory 行為不變。不能用此修正
  偷解 T10 的 source intent drift。
- 先跑新 overlay 純函式、plan／surface、假 writer outcome、隔離真
  Chroma／episode tests；再跑受影響 P4-H/I/owner、source、Web／graph
  相鄰回歸。新增 overlay 0 model calls、0 付費 API；記每輪真產品
  user wait `≤20s`，full calls/tokens 無可靠完整欄位則 `unavailable`。
- 最後另造未曝光 actor/value 的 source-only 混合多輪案例，事前凍結
  exact input、逐輪 writer/visible/graph gold 與 SHA，再用新的 launcher-
  owned 隔離 DB 在 Safari 各送一次、0 retry、指定跨重啟，核對 actual
  profile row、episode、utterance、writer audit、plan、visible reply。
  開發者自製案例只能稱 prospective product check，不是 formal holdout。
- 任一拒寫仍有「覚えとく」或 graph 說已寫、正常正例退化、DB 污染、
  程序偏離，均 strict FAIL；保留原始負例和 trace。至多兩個有根據的
  修正批次，仍失敗 `REVIEW_REQUIRED`，不改題或重跑曝光輪追分。

## 下一步

先完成 additive overlay 的單一變因實作與聚焦／相鄰測試；再獨立審查
新資料與驗收門檻、commit freeze，才啟動一次 Safari。若此狹義 gate
通過，仍需分開處理來源問答 intent 漂移、混合句角色表面與強 LLM／
真人／temporal 證據；不能宣稱完整人類反應方程式或產品完成。
