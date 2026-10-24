# P4 直接回覆行動優先關係：實作前零模型 preflight

日期：2026-10-23。這是 source 函式／控制流的只讀稽核，**不是**新產品生成、完整 cognitive turn、同模型比較或可見回覆品質證據。設計／六題／前置七檔 SHA 已先以 `6533026` 推 PR #435，舊 `retention0` 不重播。

用 frozen `a0/a1` 做 deterministic 函式 preflight，兩題都得到 M25 `detected=false`、M28 `surface_authority=false`、原 M29 `projection_required=true`、原 M33 `source_pattern_unavailable`。只在記憶中的候選副本把 `projection_required` 設 false 後，M33 回 `not_applicable`。這說明預定介入可移除這條 M29→M31/M32 字面接管候選，**還不能證明會說出較合適的話**。

控制流稽核：`uruha_brain_mac.py` 先於 19024 取 M29 候選，19395 抽 M33，19743–19774 的候選優先順序為 low-road→grounded→M33→M32→M31→M29→M18 fast→M21 bounded→full planner。對 a0/a1 的空 T0 deterministic state/route，seed 為 chat/casual、high-road、M22 general；adaptive `active=false` 故 M18 fast 不用，M21 不是 presence。**在無其他外層 P4 接管的此條件下**，移除 M29 後推導會落 full planner；實際 opt-in chain 的 selected plan／原文傳遞仍需隔離、零生成的整輪 stub 實驗驗證，未過即停。

重要負控風險：`a5` 的 `パスワード` 在既有 P4 source-role 有敏感 cue，但基本 `classify_user_signal`/router/M22 零模型實得 chat/casual、high-road、general。**不能用 source-role cue 冒充已完成安全路由或可見拒絕**；新介入必須對此 fail-closed、不賦予 direct-act 權限，產品若無安全輸出須誠實 FAIL。`a3` 已在凍結前由 `『』` 改成現有可核的 `「」`；引述與否定均不得取得 direct authority。正式語用與被理解感仍需額外人評／holdout。

Go/no-go：先在 isolated fake-model/full-turn fixture 中核 a0/a1 的原文確實進 `full_planner` 且 M31/M32 不終端覆寫，同時 a2–a5 及不明/衝突請求保持原路由；只有這一步與受影響回歸通過，才可按凍結計畫作 product SHA 與八個 fresh Safari arm-turn。不得把目前這份 preflight 推導寫成產品 PASS。
