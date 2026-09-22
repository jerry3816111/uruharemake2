# P4-AD 當輪 desired-response ambiguity ledger 驗收

日期：2026-09-23  
狀態：**PASS（deterministic shadow contract）**，但保留第一次 holdout **FAIL**。

## 這一步真正補了什麼

過去 M18/M23 已經會從幾種回應策略中選一個行動，但「選了哪一種回法」很容易被誤讀成「系統已知道使用者心裡真正要什麼」。
P4-AD 新增一份 shadow ledger，把兩者分開：

1. 當輪可觀察證據：例如文字中可確認的 cognitive overactivity、明示要方法、明示要吐槽。
2. 仍並存的回應候選：實際解法、傾聽、陪伴、生理照顧、輕度吐槽、低壓澄清。
3. 系統為了下一步選出的 action：這是 operational action ranking，不是私人心理真值機率。
4. 仍未知的部分：為什麼這樣說、哪種回應真的會被接受、選中的策略是否正確。
5. 下一輪驗證：明確接受算 supported、拒絕或改選另一種形式算 contradicted、換話題或無法連結算 unknown；unknown 不算成功。

這使「人類反應方程式」不再只有單一路徑輸出，而先保留可反駁的候選空間。

## 實際例子

輸入：`我從早上就一直坐不住，腦子停不下來。`

- 候選六種：`practical_help / listening / companionship / physiological_care / playful_tease / low_pressure_clarification`。
- 當輪 action 選擇：`low_pressure_clarification`。
- 私人原因：`unknown_not_observed`。
- 明確邊界：`selected_action_is_private_truth_commitment=false`。

輸入若明示「先給我一個方法」，action 變成 `practical_help`；若明示「我在等你吐槽」，action 變成 `playful_tease`。即使如此，
ledger 只說回應形式有當輪文字證據，未公開的私人原因仍是 `unknown_beyond_explicit_response_form`。

## 凍結測試與負結果

- development=`3/3` status、`3/3` selected action exact。
- 第一次看 9 題中／英／日事前凍結 validation 時只有 `5/9` 啟動 ambiguity ledger；中語三題與日語一題失敗。
- 四個失敗其實都已被舊 M37 typed extractor 判為 `cognitive_overactivity`，但更舊的 lexical pragmatic label 沒有啟動
  emotional-bid path。原始負結果保存在 `p4_ad_initial_implementation_failure_2026-09-23.json`。
- 唯一一次 informed correction 沒有新增關鍵詞、沒有改題或門檻；只讓 additive shadow ledger 在舊 M37 已有 typed observable
  trigger 時建立候選。修正後同組 regression status／required candidate modes=`9/9, 9/9`。
- 6 題三語 literal control false positive=`0/6`。
- 12 個非 control 的 candidate contract=`12/12`；私人真值提交、raw input trace、可見回覆變更、model call、fact/profile/episode
  write 全部=`0`。
- additive product entry 與唯一 graph node 的合成 integration 通過；released P4-AB entry、M18、M54、核心 graph renderer 均未修改。

研究證據必須再分一層：因為第一次 `5/9` 已被看見，且它被用來決定 M37 bridge，修正後的同組 `9/9` 只是工程修復回歸，
**不能再稱為獨立 holdout 泛化證據**。下一步要在修正固定後另建一組全新 sealed cases；只有那組第一次結果才可回答修正是否泛化。

## 還不能主張什麼

這仍是 shadow 能力：它讓系統誠實保留候選與驗證條件，**沒有**證明選出的回覆比較讓人被理解，也沒有把候選真的接到跨輪結果。
它不證明使用者真正想要哪一個、不證明人類方程式、不證明優於強 LLM，也不是人評。下一步必須在事前凍結的多輪案例中，
把第一輪 ledger 與第二輪明示接受／否定／無關回覆逐一連結，確認舊候選能被支持、撤銷或保持未知，而不是每輪重新猜一次。
