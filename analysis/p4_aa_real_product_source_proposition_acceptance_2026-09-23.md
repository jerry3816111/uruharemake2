# P4-AA 隔離真實產品／Safari source-bound proposition 驗收

## 結論

P4-AA 的正式凍結 gate 為 **FAIL**，不得重跑。事前合約把 P4-V 的實際節點名
`utterance_frame_coverage_extension_p4` 誤寫為 `utterance_frame_shadow_extension_p4`，所以四輪各有一個
`surface_chain_mismatch`，彙總 `exact_surface_chain_count=0/4`。這是驗收合約缺陷，不得在看完結果後修改 gate 追成 PASS。

工程觀察仍完整保留：三個受支援的全新組合題都得到事前鎖定的自然日文命題；一個不支援的一般對話沒有被 P4-Z
套入固定模板。每輪 Safari 下方 graph 都實際顯示真實的 P4-T → P4-V → P4-W → P4-Z → utterance，保存的 runtime
trace 也證明四個 P4 logic payload 與 graph payload 完全相同。這些只能當作正向診斷證據，不能取代失敗的正式 gate。

## 實際回覆

1. 中文引用：`「東側入口は六時に閉まる」っていう引用なんだね。`
2. 英文假設：`「そっちが明日青い鍵を動かす」っていう仮定の話ね。`
3. 日文傳聞：`先生が緑の傘を教室に置き忘れたらしいって話ね。`
4. 不支援控制：`今日は昼までずっと考え事が止まらなかったんだね。`，P4-Z=`source_pattern_unavailable / abstain_unchanged`。

## 數據

- exact supported visible output=`3/3`；repair 後未解命題違規=`0/3`。
- unsupported abstain/no-op=`1/1`。
- natural Japanese=`4/4`；durable episode=`4/4`。
- Safari graph visible=`4/4`；實際鏈相鄰順序正確=`4/4`，但與誤寫的凍結名稱逐字相等=`0/4`。
- exact logic→graph payload=`16/16`；每個 P4 node 都只有一份。
- typed preference write=`0`；P4-Z 額外模型呼叫=`0`。
- 既有 semantic authorization 本機模型呼叫=`4`，provider elapsed 合計=`42.285s`，token accounting 不可得。
- 產品 end-to-end=`17.5013 / 11.6430 / 12.3028 / 12.1339s`；最大=`17.5013s`，合計=`53.5810s`，均在凍結上限內。
- paid API、外部部署、production memory、function tool、VRM action、關閉 Safari 分頁=`0`。

## 證據邊界

這次正式證明的是：凍結驗收因節點名稱契約錯誤而失敗，而且研究流程能保留這個失敗，不用事後改規則掩蓋。
正向工程觀察支持 P4-Z 在四個實際產品輪次中運作，但尚未取得一個「完全符合事前凍結 gate」的實機 PASS。
即使未來以全新題目通過，也仍只涵蓋三種受限文法與既有詞彙組合，不是 open-domain 意義恢復、自然分布準確率、
felt understanding、人類偏好、強 LLM 優勢或人類方程式證據。
