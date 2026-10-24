# M43 接續：確認之後應結束確認，而非再猜心理

狀態：只讀定位與驗收規格已建立，尚未實作或封存 M43 reserve。

## 保留反例與原因

M40/M41：`Yes, that's exactly right.` 已使 M37 relation 支持保存，卻被 V2.13
active validation 問「要放著還是聽你說」。M42 真實第 5 輪同樣支持保存，但回
`ん、そこもう少しだけ聞かせて。`。

`uruha_adaptive_person_model.py` 的 `_pure_feedback_act_m28` 只接受完整正規化
token 的小集合；`yes...exactly...right` 不在其中。`build_feedback_topic_transition_m28`
雖拿到 supported / linked / M27 resolved_decisive，仍標 ordinary_current_content，
失去 acknowledgement surface authority。`uruha_personhood_loop.py` 的
`apply_longitudinal_model_to_plan` 又可能讓重複的 unknown entry 開新澄清，或讓舊
pending 留在模型中。這是回合行動的責任歸屬問題，不是缺一個漂亮日文模板。

## 單一核心變因

把「可觀察、已連結上一回覆的支持 act」與「當輪仍有新內容／請求」分離。
只有前者且沒有未解的新請求，才讓 acknowledgement 成為當轮行動與 surface
authority，並避免無理由再開同一需求的驗證。不得改 M27 支持真值或重寫歷史。
只關閉與該已驗證需求相連的 pending；不可把所有不確定性一律清掉。

## 必需驗收

- 新的實作前 zh/en/ja source-disjoint reserve；不把 retained exact sentences 寫成白名單。
- 純支持、支持+新請求、普通敘述中的 yes/對/そう、含否定／引用、指向不明、
  仍有真實未決資訊、protected-current-turn 分別有標準。
- 相同底層 outcome：只改 act/surface closure；support/calibration/關係保存結果不變。
- 自然日文短承接，不技術性倾倒推論；不是不管內容都回固定一句。
- fresh 隔離 Safari 三輪以上：seed → support → actual trigger；核對 M37 persistence、
  M43 act/authority、M39 surface、主圖與same-cycle history；不要用被輸入工具損壞的句子算成功。
- 不能把邊界內條件句變現況、meal-check 角色錯誤、protected dirty imagery 偷渡進同一核心改動。
  這些 M42 真實反例另保留為後續責任鏈修正。
- 舊 M37–M42 freeze/core/result 均不可改；採新 module/installer/entrypoint。

整體目標仍是能實際回溯經驗、推測期待並被修正的互動系統；M43 是讓「已被
確認的理解」真正改變下一個說話行動。它不構成人腦方程式或人類主觀理解的完成。
