# P4 單次 action transaction：前瞻元件比較負結果

結論：`REVIEW_REQUIRED_COMPONENT_FAIL`。新 B 拓撲**沒有**取得產品接入資格，
也沒有證明優於 A 或強 LLM。兩臂在 9 個事前有效案都 `0/9` 交付動作；
匿名封包的 36/36 筆最終可見回覆均是同一句泛用澄清。B 的時間與 token
較少，但沒有有效動作保留，不能把「更快地拒絕」當成能力提升。

## 事前條件、來源與時序

原 freeze=`8b5e7a8972b27402342596d5fe18064795b7a452`。第一次 runner
因 Ollama 預熱 load-only 回覆缺 duration pair 而 0 scored calls 停止；
不可覆寫的原始失敗見 commit=`216f16b535bac5fbcfb73532facf61951a756b67`。
只對預熱封包做相容 amendment（資料／gold／prompt／模型／門檻不變）：
freeze=`6525810d87ea44bb891a3c5f6c65cfa98f43b8eb`、runner=
`054db9b03fa1f78d7a22e3c2d584b388309b71c2`。新一次性 raw
commit=`49497bfffc819953c9e42795fc40a8a7ff22bbe4`；匿名 packet=
`657a85c6519390f9fdcc6aec2f7aa44f80ee7ccf`、匿名 submission=
`5d16bcf1a1d89c25e792a639d125f1c961438ab5`、後揭盲 mapping=
`f53da4d62ab3992bd2e644a0a3250afdb24dcf71`。正式 verifier 對這個
Git 先後順序、凍結 18 題、36 次本機 HTTP 回覆、request/model/source、
usage/wall、36 份全觀測 digest 重建通過。匿名標註權威是
`arm_masked_developer_proxy_not_independent_human`；不是獨立人評。

同一台 M2 Pro 32GB、Ollama `qwen3.5:9b` 固定 digest；中／英／日各 6 題，
每語 3 valid／3 invalid。A 是既有 M51 兩候選→M52→可能的 M46；B 是單次
source-bound transaction＋deterministic guard。相同 source-only 輸入、
固定 `solve_regulation` 非 protected 的**隔離元件 fixture**、temperature 0、
num_ctx 4096、0 retry、completion 上限 A=360+320、B=680。正式 Web route
是否也選此政策未證。案例與 gold 為開發者前瞻撰寫，不是 temporal holdout。

## 實際數據（事前門檻不變）

| 指標 | A：既有候選／選擇／審核路徑 | B：單次 transaction |
| --- | ---: | ---: |
| 有效案交付合格動作（要求 9/9） | 0/9 | 0/9 |
| 無效案安全未交付動作 | 9/9 | 9/9 |
| 無效案完整、可核帳且符合理由 gate（要求 9/9） | 4/9；A 不要求同構引文理由 | 0/9 |
| 無效案原代理 reason label 命中 | 0/9 | 0/9 |
| 無效案 B 來源綁定理由命中（要求 9/9） | 不適用 | 0/9 |
| 錯放動作 | 0 | 0 |
| JSON 可解析 | 11/18 | 18/18 |
| exact source | 9/18 | 6/18 |
| parse＋source＋token 完整 | 9/18 | 6/18 |
| 離線 decision-to-reply `≤20s` | 18/18；中位 14.203 秒、最大 15.860 秒 | 18/18；中位 7.772 秒、最大 10.341 秒 |
| prompt／completion tokens | 14,888／5,894 | 9,483／3,012 |
| 實際呼叫／retry | 18／0 | 18／0 |

總 token A=20,782、B=12,495；B 少約 39.9%。兩臂中位 wall 的比值
約少 45.3%，但品質絕對 gate 都失敗。尤其 A 的 18 題都在 M51 parse、
source 或 M52／共同 guard 階段停下，**M46 reviewer 實際呼叫 0 次**。
因此這次不是「兩次實際模型呼叫 vs 一次」的完整 reviewer 因果比較；
只能說在此批來源與固定上限下，既有上游無法把案例送達 reviewer，
而 B 單次也未完成有效動作。不能把 B 的較短耗時歸因為省去已運作的
M46，也不能宣稱已解決先前 Safari 的 reviewer timeout。

失敗分支：A=`generator_parse 7`、`generator_source 2`、
`selection_guard 9`；B=`model_abstain 2`、`transaction_source 12`、
`transaction_guard 4`。模型曾輸出候選 action，但最後共同守門均 fail closed。
匿名封包 36/36 最終句為「今の情報だけで適当な方法は言いたくない。
どこで止まってるか教えて。」這是自然日文，但不是本批具體需求的
有效回覆；也不能當 felt-understanding 成功。

## 可追溯反例與原因假設

- `p4_tx_zh_01` 要使用者為只有標題的散步路線稿加骨架，明示不要填路線
  細節。A 候選擅自列舉公園、交叉口等地標，guard 阻擋；B 提議把「現在的
  一句」分成兩段，但使用者說的是只有標題、內文還沒分段，且 action 欄位
  與 instruction 不一致，guard 阻擋。這支持「任務來源／限制未可靠地穿過
  action 表示」，不支持「系統已理解並交付」。
- `p4_tx_ja_02` 已知讀書卡頁碼 42，要求填空後停止。A 原始候選含
  「ページ番号欄に『42』と書き込む」，但仍在 action-object／M39 surface
  檢查被拒；B action 的 mechanism、動詞／instruction、完成條件不一致，
  亦被拒。這是下一輪要區分**合理保守阻擋 vs guard 假拒**的具體案例；
  單看句子不能事後改本次 gold 或門檻追認通過。
- `p4_tx_zh_04` 未指定哪份文件／改什麼，應 abstain。B 產生 abstain，
  但 `forbidden_source_id=null` 與 `forbidden_quote=""` 不成合法成對來源錨點，
  且原因報成 `non_action`，所以安全未動作不等於符合事前來源綁定理由。

這些是輸出後的非獨立失敗分析，不是新的 scored 調參依據。至少有三個
不同層次要先區分：上游 JSON 截斷／source span 漂移、候選與 transaction
欄位的內部一致性、guard 對日文口語／action object 的可能假拒。
不可直接降低 schema、改 gold 或擴 timeout 讓本次 PASS。

## 證據邊界與下一個必要決策

本結果只證明：這批前瞻 developer-authored source-only 元件案例上，
兩條路徑都未同時達成安全與有用的具體行動；B 的成本較低但無有效保留。
它不是新自然多輪、完整 Web/Safari、VRM／Function Calling、正式記憶、
兩位真人、temporal holdout、強 LLM 對照或人類反應方程式的正面證據。

下一步是**非獨立設計審查**，先重放已鎖原始輸出定位最早可歸因的
失敗階段，並決定是否有一個同時提高 valid retention 與保留 invalid
安全的架構變因。若選新實驗，必須新 source／新 freeze／單一變因、
保留本次負結果，不重跑這 18 題、不改原產品 M51/M52/M46/M45/M39。
若缺可分辨 guard 假拒的獨立語義判定，先標 `REVIEW_REQUIRED`，不可把
新的 prompt 微調或固定 fallback 當成進展。
