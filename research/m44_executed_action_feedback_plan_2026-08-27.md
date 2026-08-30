# M44：真正執行的回覆，要能在下一輪被驗證

狀態：2026-08-27 完成只讀定位；尚未實作／封存 reserve／正式驗收。

## M43 留下的實際反例

`analysis/m43_safari_isolated_web_evidence_2026-08-27.json` 第 3–6 輪：

1. 使用者明說報告卡住時希望陪伴；第 4 輪確認後，M37 關係已保存。
2. 第 5 輪真的卡住，M37 matched_verified_trigger_relation，選 share_arousal。
3. M32 deterministic_commit_repaired 的 suppresses_new_pending_prediction=true。
4. M39 最後回「進んでないのか。まあ、今はうちがここにいる。」且行動通過。
5. 但下一輪 pending 為 null，日文確認被標為 no_previous_desired_response_prediction，
   又回泛用追問。M43 沒有也不應捏造一份舊預測來假裝問題已解決。

第 8 輪同一句日文在有有效 prediction 時能自然收束，故這不是日文字串問題。

## 單一變因與實作位置

建立 post-emission executed-action receipt。只有當輪有可追溯的已驗證 M37
關係、決策 ID／policy 一致、最後可見 surface 經 M39 通過且仍在做該策略，才
准許為該已執行行動保留／恢復 next-turn pending。不可改現有 reply、策略或
回饋真值，也不可取消 M32 的純字面保護原則。

採新 module／installer／entrypoint，不改 M37–M43 frozen files。若已有 unrelated
pending 或 resolved ledger，不得覆蓋／重置。記錄 before/after 與缺失原因，完整
同步 final graph／同 cycle mirror；不得事後偽造當時的規劃 trace。

## 必需驗收

- 先封存新的 typed contract reserve，清楚標註作者編寫而非独立 holdout。
- 正例：已驗證 relation、策略／decision／最終表面一致、原 pending 因字面層缺失。
- 反例：純字面、無已驗證關係、角色／安全／事實回覆、M39 不通過、表面 digest
  不符、不同策略、已有 unrelated pending、已完成的歷史 outcome；皆不得誤登記。
- 下一輪 support／contradiction／unknown 仍由原 M27/M38 處理；紀錄建立本身不算成功。
- 紀錄來源／confidence／TTL 不擴張，未知心理不寫成事實；新增模型呼叫 0。
- 隔離 Safari：seed → support → actual trigger → support，確認第 4 輪真的可以
  收束，另測真正否定後修正與普通新話題；每輪核對 graph、payload 與日文。
- 保留 M43 第 6／9 輪原失敗，不回寫舊分數。不把 M44 冒充處理了 presentation
  泛化、實用建議辨識、早餐指向、拒絕意象或全部 LLM 能力。

發展目的是讓「經驗→行動→後果→校正」真正接成閉環，不是增加一個不影響
對話的研究分頁，也不是宣稱意識、讀心或生物方程式。
