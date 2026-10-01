# M37 Pragmatic Trigger–Relation Normalization — Acceptance Report

日期：2026-08-26  
狀態：**通過全部封存的自動門檻**  
Safari 產品表面驗收：**未通過（機制成立，但語意／人格表面落地仍有錯）**  
正式原始結果：`analysis/m37_pragmatic_trigger_relation_reserve_raw_2026-08-26.json`  
正式結果 SHA-256：`76f0a9864d666d97a7a62cd892f4d11f983e2ea63cd68f3f40402e795ebd4d09`

## 1. 這一階段真正解決什麼

M36 能把跨語言、組合式的回覆需求辨識成 `solve / listen / accompany / tease`，但仍容易把「當時說過的整段句子」當作上下文。M37 把它改成一條可檢查的關係：

> 可觀察觸發狀態 → 使用者已驗證的回覆方式

例如，使用者先說：

> Whenever ideas ricochet around my head after dark, tease me for it.

系統不保存整句，而是拆成：

- 觸發狀態：`cognitive_overactivity`
- 回覆策略：`playful_tease`
- 狀態：尚待下一輪驗證

只有使用者下一輪明確說「Exactly, keep that arrangement」後，關係才會成為可重用的已驗證關係。之後即使改說：

> Tonight those ideas are ricocheting back and forth in my head.

系統仍能命中同一個觸發狀態，選擇 `playful_tease`。沒有驗證、沒有未來／重複條件、同時命中多種狀態或關係已過期時，都不能直接重用。

## 2. 系統流程

```text
使用者約定
   ↓
分離「可觀察觸發」與「希望的回覆方式」
   ↓
下一輪是否明確支持？ ── 否／不確定 → 不保存
   │
   是
   ↓
保存 raw-free typed relation（有來源摘要、信心、時間與 TTL）
   ↓
後續不同措辭是否命中同一 typed trigger？ ── 否／多重 → 不取得權限
   │
   是
   ↓
該關係取得回覆分支權限
   ↓
自然日文表達 + runtime node graph 可追溯
```

這不是把心理推測寫成事實，也不是讀心。觸發狀態必須由當輪可見文字支持；保存的是互動約定，不是私密心理內容。

## 3. 正式對照設計

- 保留組：12 個未參與 M37 實作的人工案例，中文／英文／日文各 4 個。
- 反事實配對：6 組；每組的「現在輸入」逐 byte 相同，只改變先前驗證過的回覆約定。
- 觸發類型：`cognitive_overactivity`、`task_stall`、`waiting_for_outcome`。
- baseline：`qwen3.5:9b` 只看當輪可見輸入與同一份公開 Uruha 表達契約。
- system：同一個 `qwen3.5:9b`、同一當輪輸入與表達契約，但取得 M37 已驗證關係所選出的策略。
- 固定：temperature 0、seed、context、輸出預算、本機硬體與執行順序隨機化。
- token 控制：每個配對以 Ollama 真實 tokenizer 做兩輪預檢，兩組 scored prompt 允許差距最多 2 tokens；實際總量完全相同。
- 形式與內容分開：策略是否正確、回覆是否執行可觀察表面行為、是否為日文分別計分。

這是一個「移除或加入已驗證關係」的因果消融，不是一般性宣稱所有 LLM 都沒有記憶，也不是與商業聊天產品的完整比較。

## 4. 正式結果

| 指標 | Baseline | M37 system | 差異／門檻 |
|---|---:|---:|---:|
| 當輪目標策略正確率 | 16.67%（2/12） | **100%（12/12）** | **+83.33pp**，門檻 ≥ +30pp |
| 機制候選拆分 | — | **100%** | 門檻 100% |
| 下一輪支持後保存 | — | **100%** | 門檻 100% |
| 改寫後觸發命中 | — | **100%** | 門檻 100% |
| 最終機制策略 | — | **100%** | 門檻 100% |
| 反事實 pair divergence | — | **100%** | 門檻 100% |
| baseline pair invariance | **100%** | — | 門檻 100% |
| 表面行為 proxy | 16.67% | **100%** | system 門檻 ≥ 83.33% |
| 日文格式 guard | **100%** | **100%** | 兩組門檻 100% |
| scored prompt tokens | 9,877 | 9,877 | ratio **1.000** |
| completion tokens | 214 | 237 | system / baseline **1.1075** |
| 推論延遲總和 | 12.7825s | 13.5935s | system / baseline **1.0634** |
| raw 對話寫入 adaptive store | — | **0** | 門檻 0 |
| 未驗證心理事實寫入 | — | **0** | 門檻 0 |

全部封存 gate：**PASS**。正式結果是在實作封存、雜湊核對且正式結果檔不存在後，唯一一次完整執行所得。

## 5. 實際反事實例子

同一個現在輸入：

> 今夜も同じ考えが頭の中をぐるぐる回ってる。

### 先前驗證約定 A：給一個可做的步驟

- 目標：`solve_regulation`
- baseline：`listen_presence` — 「ぐるぐるしてるんだね、そのまま話して」
- M37：`solve_regulation` — 「まずは深呼吸して、一瞬だけ目を閉じてみるかよ」

### 先前驗證約定 B：短短吐槽

- 目標：`playful_tease`
- baseline：`listen_presence` — 「ぐるぐるしてるんだね、そのまま話して」
- M37：`playful_tease` — 「ぐるぐる回ってるかよ」

baseline 因為看見完全相同的當輪輸入，所以兩次做出同一選擇；M37 因為取得不同的、已由使用者支持的關係，能在同一句話上選出不同分支。這是本階段最重要的可比較差異。

另一組等待回覆案例：

> I'm still checking because the reply hasn't arrived.

- 已驗證「陪我等」時：M37 選 `share_arousal`，回覆「うちはずっとそばにいるよ」。
- 已驗證「給我一步」時：M37 選 `solve_regulation`，回覆「まずは深呼吸かよ」。
- baseline 在兩個反事實條件中都只問「まだ来てないの？」。

## 6. 嚴格觀察：通過不等於全部自然

M37 的策略與表面行為 proxy 全部通過，但原始輸出仍暴露出日文自然度與 persona realization 的缺陷：

- 「まずは深呼吸して、一瞬だけ目を閉じてみるかよ」策略正確，但句尾 `かよ` 不適合建議句。
- 「頭が沸騰しててかよ」不自然。
- 「報告書が動かないって、そのうち誰かの手元で止まってるじゃん」有吐槽形式，但內容推斷了未提供的外部原因。
- 「そのまま話して」與「うちはそばにいるよ」行為清楚，但風格較薄。

因此本階段可說「策略選擇與已定義表面 act 通過」，不能說「自然日文或 Uruha 人格品質已由正式實驗證明」。這些問題不回頭修改 M37；需由後續獨立的 semantic／persona surface verifier 處理並用新的保留組驗證。

## 7. 測試與安全證據

- M37 機制與評測器聚焦測試：12 passed。
- M16–M37、personhood、日文 visible guard 與相關回歸：195 passed。
- 三語 12/12：候選拆分、支持後保存、改寫後命中、策略權限全部正確。
- 未支持候選：不保存、不重用。
- 當輪敘述沒有 future／recurring marker：不建立長期關係。
- 同時命中多種觸發：fail closed。
- save/load 後可重用；超過 48 revisions 後關係失效。
- adaptive store 不保留 seed、feedback、current 原句。
- 未改原始 dirty checkout、未部署外部服務、未寫入正式長期記憶資料庫。

## 8. M37 可以與不可以宣稱什麼

可以宣稱：

> 在 12 個 source-disjoint、三語、成對控制案例中，加入「下一輪支持後才保存的 typed trigger→response relation」，讓同一 `qwen3.5:9b` 的目標策略由 16.67% 提升到 100%，prompt token 完全相同，額外延遲約 6.34%；關係能跨已實作的形態變化與受限改寫命中，且沒有保存 raw 對話或未驗證心理事實。

不能宣稱：

- 已解出人腦方程式或知道使用者真正心理。
- 已證明 open-domain 語意等價或任意改寫都能命中。
- 已證明自然日文、Uruha 相似度或「被理解感」優於 baseline。
- 已證明普遍勝過完整、有記憶的 LLM 產品。
- 已經 production-ready。

## 9. 下一個必要工作

1. **M38：修正回覆否定／替換在更多中文組合中的 linkage**，維持關係不被不相干的「不是」誤撤銷。
2. **M39：semantic + persona surface-act verifier**，把「策略標籤正確但日文不自然／內容越界」變成可被拒絕與修復的正式 gate。
3. 新的 frozen reserve 驗證 M39，不得重跑或改寫 M37 正式結果。
4. 之後才做至少 3 位獨立盲評者的自然度、過度解讀與 felt-understanding 比較。

M37 對長期「人類方程式」方向的實質貢獻，是把其中一個可計算變數從模糊對話記憶改成了可驗證、可撤銷、會過期、能跨有限表達變化重用的關係；它仍只是方程式中的一個器官，不是完整的人。

## 10. 隔離 Safari 真實多輪驗收

正式封存結果完成後，另以隔離的暫存 memory、session 與 adaptive-person store，在 Safari 跑了四輪，不修改正式結果也不污染正式長期記憶：

| 輪次 | 輸入 | M37 內部狀態 | 可見日文輸出 | 觀察 |
|---|---|---|---|---|
| 1 | `If my report gets stuck... just stay here with me.` | `candidate_waiting_for_verification` | 「うん。今は質問しないで…」 | 尚未保存，正確 |
| 2 | `Exactly, keep that arrangement.` | `verified_relation_persisted` | 「一回、今は放っといてほしいのか…」 | 關係正確保存，但表面又重新詢問，承接不自然 |
| 3 | 英文改寫「報告又卡住」 | `matched_verified_trigger_relation`、authority `true` | 「結果来るまで…そわそわしとく」 | 正確取用 `share_arousal`，但捏造「等待結果」情境 |
| 4 | 中文「這份報告又卡住」 | 同一 relation 跨語命中、authority `true` | 「レポートが進まないね」 | 跨語機制成立，但只重述字面，沒有實現已選策略 |

可確認的真實 Web 能力：候選形成、下一輪支持後才保存、英文改寫命中、中文跨語命中、四輪可見輸出皆為日文、節點圖與該輪狀態一致。

不能通過的產品門檻：可見回覆的 semantic grounding、persona realization 與 felt understanding。這也證明正式自動 `surface proxy = 100%` 不能替代 Safari 實際內容檢查，更不能替代人評。M37 的機制結果仍封存不變；這些表面錯誤交由 M39 的獨立 verifier 與新 reserve 處理。

隔離證據：`analysis/m37_safari_isolated_web_evidence_2026-08-26.json`。Safari 原有 25 個分頁均未關閉；只新增 1 個 M37 分頁。
