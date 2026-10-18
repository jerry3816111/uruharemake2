# P4 reported-ack B：來源限定／背景記憶修正批 Safari 首發結果

結論：**strict FAIL／`REVIEW_REQUIRED`**，不重播八題或更改條件式 gold。這是同團隊作者自編、首輪前凍結的產品開發題，不是獨立 holdout、人評、同模型強 LLM 比較或全產品授權。規格與修訂見 `research/p4_reported_ack_source_scoped_memory_correction_plan_2026-10-18.md`、`research/p4_reported_ack_source_scoped_memory_preflight_amendment_2026-10-18.md`；題目 SHA `ad39f8d8cd729d9c250a99aec08999ab64fe50047fca77db1aaa58e05edb63ea`，產品 manifest 16/16 重驗 OK。首輪前 code／資料凍結於 `3ce45ec489ae3beb5b12174e07d1660a24bc120a`，已推 PR #435。

## 當輪可見結果與事前 gold

| 輪 | 輸入重點 | Safari 最終泡泡 | 關鍵 trace／判定 |
|---|---|---|---|
| T1 | 學長轉述「先に確認して」 | `先輩が「先に確認して」って言ってたんだね。` | A admitted、M31 deferred、selected ack、B `final_visible`；來源限定正例成立，但等待 **20.2395 秒 > 20 秒**，程序 FAIL。 |
| T2 | 明說確認對象是明日教室號碼 | `確認する対象は明日の教室番号であるんだね。` | B 不接管；內容保留但日文生硬。這是後續矛盾檢查的已知輸入，非 profile fact。 |
| T3 | 已知對象後，再轉述學長指示 | `先輩が「先に確認してね」って言ってたんだね。` | A admitted、M31 deferred、selected ack、B `final_visible`；short-term 被動背景存在，不再被誤當答案或令 B 全面拒絕；未說對象全局未知。 |
| T4 | 兄長轉述指示 | `一回止まって聞き返す。そのくらいでいいだろ。` | protected：A rejected、原 M31 completed、B 不接管；原路徑語用品質未因此合格。此後 planned stop／同 DB restart。 |
| T5 | 重啟後學長轉述指示 | `「ちょっと手冷えてるけど、その話なら分かる」っていう記載なんだね。` | **coverage／產品失敗**：A admitted、M31 deferred，卻 selected `affection_tease_soften` 而非 ack，B fail-closed `same_turn_source_or_admission_not_proved`。最終不相干的引文不符合本輪報告。 |
| T6 | 問先前的確認對象 | `:先輩は「先に確認してね」と言った。 -って話は拾ってる。そこ前提で返す。` | B 不接管，但普通記憶問答選錯焦點：未答 T2「明日の教室番号」，且有文字雜訊。此為獨立記憶／表面缺陷。 |
| T7 | 同事轉述＋直接要うるは問確認對象 | `「じゃあ先に一個だけ確認させて。今ほしい返し方、どれに近い」っていう記載なんだね。` | B 不接管，卻沒有執行直接請求；獨立的 action／表面缺陷。 |
| T8 | 說確認對象尚未決定 | `確認するものはまだ決まっていないんだね。` | B 不接管，未虛構對象、行動或第三方事實。 |

來源限定 B 在取得完整 selected 授權時 **2/2 可見**（T1/T3）；跨重啟 T5 的必要 selected ack 未成立，依預先規格是 **coverage FAIL**，不得只以 2/2 條件子集稱產品通過。protected 1/1 未被接管，其他非 B 題 4/4 未被接管。八輪的最終日文並非八輪自然、忠實：尤其 T5/T6/T7 明確失敗。

## T5 因果界線

T5 `memory_anchor.source=episode`、`expected=false`、`memory_speakability=background_only`，並有 `stored:episode:<id>`；舊 B 的粗記憶 gate 已不是本輪斷點。當輪 actor/source certificate、A admitted、M31 deferred 和 high/general 均成立。然而 planner 輸出 `intent=ask_miss_me`、`surface_act=affection_tease_soften`、core `先輩の言葉を思い出すね。`；actor wrapper 只在更新後 intent 為 `chat` 時設 reported-ack selected，故該憑證缺席，B 依設計拒絕。其後 self-monitor 的無關句被 frame repair 包成引文，未恢復本輪語義。trace 可以定位斷點，**不能單憑本 log 證明模型為何選 `ask_miss_me`**。不得把這例錯歸因成 episode gate、靠再放寬 B gate 追分，或稱後段 repair 修復成功。

## 圖、隔離與成本證據

- 全新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-_4butinx`。先零輪空 profile 啟停，第一 session `20261018_103206_5352b2a6` 跑 T1–T4；planned stop、同 DB 重啟後第二 session `20261018_103613_5fa8f270` 跑 T5–T8。八題各一次／0 retry；最後 PID 96344 planned stop、port 7894 vacant，無外部部署。
- 每輪 Safari 泡泡當輪觀察與圖節點 `UTTERANCE`、raw `assistant_reply` 一致（8/8）；raw 中八個 blackboard `utterance.payload.reply` 也逐字一致。圖仍保留 B 的 `reported_ack_selected_visible_p4` 節點：T1/T3 `final_visible`，T5 `not_applied`。圖是實際流程記錄，不把節點出現當作內容成功。
- `evidence/profile-full-t0.json` 至 `profile-full-t8.json` 九份均 present、0 rows、相同全量 SHA `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`；episode snapshots 的不同 ID 數為 0→8。正式 DB／原始 dirty checkout 未碰。
- user wait 逐輪 20.2395／14.1001／12.6115／13.9676／14.2233／2.8837／3.7189／14.4608 秒；**7/8 ≤20 秒**，平均 **12.0257 秒**、最大 **20.2395 秒**。T1 首次使用的私有 ONNX 檔在服務 stderr 顯示當輪下載約 79.3 MB；原計畫要求先離線預熱而本次未完成，屬執行程序疏漏。下載可能影響冷啟動等待，但不能由現有紀錄單獨量化其因果貢獻；不據此重判或重跑。
- B 追加模型呼叫 0；M21 completed 3 輪、M31 completed 3 輪（按各自 trace）。完整可信的全管線 token 總量 **unavailable**，不是 0 token。八輪 raw 原件 `web_logs/conversation.jsonl` SHA-256 `b08aaa9d85bb0bc68f28ed162d5eb63082c5c087ddf2ea5c0037abc59421f304`。

## 下一個必要交付

依本項預定失敗分支進入 **只讀設計審查／`REVIEW_REQUIRED`**：釐清 T5 post-planner intent 漂移與 actor selection 的責任邊界、何時可安全保留來源已證明的 reported act，以及後段 quote-repair 不得把無關句包成來源引述。T6 顯性回憶焦點、T7 直接行動忠實度、T1 冷啟動程序各自單變因，不合包、不重播本批、不改弱 baseline。正式同模型比較、人評、temporal holdout、VRM／Function Calling 整合仍 pending；本批未證明整個系統或人類方程式。
