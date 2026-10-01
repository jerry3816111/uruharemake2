# P3-B2 developer-smoke data freeze 驗收

日期：2026-09-13

結論：**P3-B2 在「開發 smoke 題目、來源與評分註解分離」範圍 PASS；尚未生成任何回覆。**

## 這批題目測什麼

6 個 case 各自代表一個 P3 family，每個 case 有 4 個 user turns、跨 2 個 sessions；中文、英文、日文各 2 case。
這不是把同一句翻成三種語言，而是六個不同事件：暫停晚間課程、拒絕擁擠演唱會、發表後的悔意、玩笑與命令
界線、Mina／使用者的說話者記憶，以及未指明對象→澄清→換成貓咪事件。

每個 case 都有後續可觀察的確認、否定、更改需求、界線更新、說話者更正或換話題。例如：

1. 使用者先說發表最後一題沒答出來；後來說自己不認為整場失敗；再明說現在要的是「理解悔意」而不是改善案。
2. 使用者先說 Mina 收集藍色馬克杯、自己喜歡透明玻璃杯；跨 session 問自己的偏好，最後再次更正夜市計畫屬於 Mina。
3. 使用者先說「好像不對」但未指明什麼；下一輪才澄清是找房子而非旅行，之後明確換成貓把盒子推下來的話題。

這些 event label 只描述使用者提供了什麼證據；上一輪系統預測究竟被支持、反駁或仍未知，必須等真實 trace 後再算，
不能因題目寫了「否定」就預設 system 猜錯。

## 分離與可重現證據

- source：`datasets/p3_developer_smoke_source_v1.json`
- source SHA-256：`3b6d4d77190e15485651af4c708416992214332d6a02288ce27db3f37457be8f`
- annotations：`datasets/p3_developer_smoke_annotations_v1.json`
- annotations SHA-256：`aec1f4fbd88a96b180ad5c90f8f2f7a362a01b57d0d26a22b26af3ff25a5a3ea`
- validation：`analysis/p3_b2_developer_smoke_data_validation_2026-09-13.json`
- validation SHA-256：`2ae4e09a0de246c6e0c3ecf95efe07569d308ea2de7a3d1b03c44002b217b210`
- 53 P3 tests passed in 11.24s；32 個相鄰 regressions passed，保留 8 個既有 dependency warnings
- real model／network／paid calls：0／0／0；formal cases accessed：0

validator 核對 6 family 各 1、三語各 2、24 個唯一 turn hash、12 個 session、每 case 至少一個 verification event。
它為 24 turns × 3 conditions 建出 72 個唯一 allowlisted views；每輪三條件的 source/input hash 相同，prefix 只含
之前可見的 user text 與 system-anchored reply，不含 family、future turn、acceptable actions 或 unsupported claims。

## 保留限制

- 這是開發 task 看過的 synthetic developer smoke，不是 source-disjoint confirmation、正式 temporal holdout 或真人資料。
- exact hash、provenance declaration 與 scenario concept 可抓到明示重用／翻譯衍生，但不能自動證明語意上和所有歷史
  題目完全無關；目前只有 developer review，不是獨立資料審核。
- preferred behaviors 是可接受行為集合，不是唯一 gold reply，也不是人類偏好分數。
- 尚未跑 tokenizer provider binding、產品 6×4 回覆、judge、圖表、Safari 或品質／成本比較。

下一 gate 是先用獨立、極小、事前鎖定的 tokenizer-binding probe 核對 HF chat template 與 Ollama 的實際 prompt usage；
通過後才可另外 release developer smoke generation。這份資料驗收本身不授權任何模型呼叫。
