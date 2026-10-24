# P4-U 前置相容性失敗

狀態：**FAIL before product integration；不得宣稱 P4-U repair 通過。**

P4-U 事前凍結的單一變因是「只有 P4-T 已經報出 frame violation 時，才把日文表面修成保留 speaker／embedding／stance／speech act 的版本」。development 四案都符合前置條件，但新的 12 案 holdout 只有 **5/12** 得到與凍結標註完全相同的 P4-T violations；第一個 repair prototype 因此只得到 exact reply **6/12**。

七個不相容案例分成三類：

- 三個 user→agent 主體顛倒使用 `整理／水をやる／直す`，超出 P4-T 已凍結的 user-state predicate 範圍。
- 英文 `The memo says, ...` 不在 P4-T 的 metalinguistic-report marker 內，因此引用被判成 direct statement。
- 三種「只是個假設」表達沒有完整落成 `frame_instruction`，或一般 `…んだね` 沒被視為把假設提升成事實。

不能在 P4-U 裡再寫一套來源分類器來補，因為那會同時改 detector 與 repair，破壞單一變因，也違反凍結契約。這個失敗發生在 unit 階段：0 model call、0 memory write、0 product integration、0 Safari turn；沒有污染正式資料或重跑 holdout。

這 12 案已因診斷而曝光，後續只能當 development evidence，不能修完後再叫 holdout。下一步必須另立 P4-V，先用新未曝光資料驗證 P4-T coverage extension；P4-V 通過後，再以另一批全新資料做 surface repair。這增加約半天工作，但比把 6/12 改門檻或偷偷增加第二個分類器更可信。
