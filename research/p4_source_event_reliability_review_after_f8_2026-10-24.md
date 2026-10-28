# P4 來源事件保真：f7／f8 負結果後設計審查

日期：2026-10-24。狀態：`REVIEW_REQUIRED` 的**設計審查**；沒有新產品改碼、fresh generation、Safari Send 或新題凍結。初稿由同一開發方根據現有原件與程式完成；先前一位審查代理因額度錯誤未能審查，後續兩位獨立只讀代理提出 final no-send、資料外洩、變因歸因、實際路由與成本邊界的修正，已納入本頁。這是設計核對，不解除新題凍結／實作／Safari 的後續 gate。

## 最小反例與已排除位置

f7d 真 Safari：User 明說 `初めて自分でハーブの苗を植えた`，可見回答卻是 `種をまいただけでもすごい！そのくらいでいいだろ。`。當輪 M29 direct、M21 compact 3 真候選且無 fallback；f7 對三核心全記 `event_relation_unverified`，選擇 index 1→1，選定 core 已把種苗移成播種，RightBrain 不是首個錯誤點。f8 前瞻 M21 同起點配對：off/on 都有 3 真候選、無 fallback/repair、選定原始 core 皆 `頑張ったね！`，均未保留「第一次自己拍夜星」；f7 grounded 皆 0/3。on 的 prompt 注入 receipt 與 provider request 差異已核，+154 provider tokens、沒有本題收益。

由此可排除**本兩輪**的「來源 handoff 未到」「f8 約束未到 provider」「已有 grounded 候選但 f7 排錯」「後段把正確選定 core 改錯」作為首個已觀察瓶頸。不能排除模型在不同 seed、資料或指令下能生成有根據候選；也不能把 f7 的保守字面 coverage 視為完整語義評分。f8 的原始候選與事前完整 gold 都不合格，故不只是 verifier 太嚴。這些案例共用「第一次自己做＋一句鼓勵」結構，是 developer-authored 診斷，不是正式 temporal holdout 或強 LLM 比較。

## 設計決議：一個下一可歸因機制

**建議的單一 treatment 是「來源綁定語義槽的 plan→surface commit」整條不變式**，不是只加一個欄位就宣稱有效。保持 f8 prompt **關閉**、f7 保守 coverage 與既有模型／人格／資料／候選生成不變；只在現有 M29 `current_user_direct_request`、M33 not-applicable、f7 有效有限事件證書、M21 full route 的已准入 case，建立當輪 immutable 事件內容槽：`actor=current_user`、`first_time=observed|not_stated`、`object/action/completed` 的原文短 span、source SHA／handoff SHA。現有 f7 parser 只回 `(sentence, object, action)`；f8 opt-in receipt 有 `first_time_observed`，但它不是可進 surface 的完整事件 slot。slot 與同輪 handoff 綁定都是**待實作**，不能假裝已存在。這是**已驗證為 User 當輪自述的內容**，不是外部確認的世界事實、心理推測或長期記憶。即使選定的 `core_message_jp` 泛稱，也應讓真正的 Web surface 路由拿到此來源槽作必要內容；再於**所有最後 guard／overlay 之後**核可見 utterance 的 actor／首次（若明說）／物件／完成動作／所請求的鼓勵或勞慰。Web 目前以 `UruhaBrainV4_Mac()` 建構，未傳 persona provider；`RIGHT_BRAIN_MODEL_BLEND_ENABLED` 預設 false，因此此目標路由的 RightBrain 通常為 deterministic surface，不能假定存在「同一次既有生成」可供加 prompt。啟用 RightBrain 模型是另一個變因，非本 treatment；凍結前須核確切 route／flag，選定不增加生成呼叫的 deterministic realization 路徑，按實際路由計數。Treatment 的可歸因單位是 slot→surface constraint→post-last-guard verification 的整體 commit，不把效果歸因給其中單一欄位。

Raw 事件槽只能在**當輪 ephemeral context** 傳遞，不可直接放進持久 `logic`、一般 blackboard 或 Web JSONL；這些容器會被複製並可能寫入非私有 log。graph 只留固定 allowlist 的 stage／狀態／完整性 digest 與關係是否驗證，不能把 truncation 當 redaction；現有圖可顯示 User 原句或 utterance，本約束的「raw-free」只指**新增 slot/provenance receipt**。短事件 digest 可被字典猜中，只能作完整性／provenance 線索，不能宣稱保密。需同輪綁來源及清除 ContextVar，拒絕 stale／forged／跨 turn handoff；不向長期記憶寫推測。

准入時必須由**當輪 `user_input`**、M29/M33 handoff 與**實際完成**的 M21 route 重建並驗證來源，不可信任只在 logic 中殘留的旗標。f7 可 `eligible=True` 但三個原始 core 全 `no_grounded_candidate`；本 treatment 正是檢查這種情況是否能於 surface 保全來源，不能以「原 core 已 grounded」作准入條件，否則會排除 f8 已觀察到的失敗。

嚴格定義 treatment／成功：在新隔離案例中，只有真正發給 User 的日文句子與泡泡／raw／episode 同字且承接來源事件，才是產品 PASS；圖須能看到 source certificate→內容槽→surface realization→visible check 的同輪連線。final check 必須核關係、actor、polarity/completed，不可只是多個關鍵字 substring 各自出現。若既有 surface 忽略槽、最終 guard 改成泛用句或沒有可靠的 final certificate，**品質 FAIL**；原句僅存於私有稽核，不能作成功回覆送出或寫入 episode。既有 RightBrain 可能在 final guard 前先寫 provisional history；因此 no-send 必須在 UI／episode 持久化前作用，並 rollback 或避免留下那筆 provisional history。若實作尚不能安全處理此事，應在產品測試前停於 admission FAIL，不開 treatment 真使用者輪次；不能讓 trace 的 `fail` 標籤與已送出的假成功句並存。不得以「core 有槽」「graph 有節點」冒充可見成功，也不得用固定測題答案／答案清單／完整 User 問句回聲掩飾。實作方案在 frozen plan 中必須具體核可這個 no-send／可恢復錯誤路徑及其使用者體驗；不能用另一句固定催促或杜撰話術取代。

只讀路由核對發現：`uruha_brain_mac.py` 的 `emit_response_if_ready` 在所有可改寫 reply 的步驟完成後，約第 20804 行、`runtime.last_reply`／utterance blackboard／`save_episode` 之前有**可設 final verifier 的位置**；但這**不是**現成可安全中止的 transaction。`RightBrain.speak` 在返回前已 `_remember_turn` 到 history/counter，`cognitive_tick` 在表達前已把 adaptive person model 寫成 JSON，記憶檢索亦可能更新 access time；psyche/runtime 也先變動。Web `_run_turn` 捕捉例外後重拋，現有 UI 例外支線會留下 User 與 `...` 助理泡泡，並非真正 no-send。Web admission 已有 `aborted` 終態可借用，但需新增**明確的品質 blocked 結果／UI 清理支線**，不是讓一般例外走現有 error 支線。凍結前必須選擇延後這些效果到可見核准後，或給出可測的完整回滾及明確 blocked UI 狀態；只回滾 RightBrain/跳過 episode 不能宣稱整輪沒有殘留。這是目前**入場阻礙**，不以 throw exception 或單一後驗 `FAIL` 標籤冒充已解。

這是**來源事件保真工程**，不是心智理解、人格相似或「人類反應方程式」的證明。若只靠組合原文事件槽和固定稱讚，可能只是受控複述；所以需同時檢查自然日文、角色感、過度直抄、未請求問句與成本，並保留相同模型/資料下的基線。若效果只出現在這個有限日文語法，不能外推中文／英文或隱含目的。

## 為何不選其他修正

- 再調 f7 排序：兩次原始候選 grounded 皆 0/3，沒有可選的有據核心。
- 在曝光的夜星／香草苗題重寫 prompt：會以答案反饋追分，破壞前瞻性；f8 已證明一次短指示並不足夠，且多 154 tokens。
- 看到模型失敗就再呼叫一次／多次：可能改變品質，但新增生成、延遲與 token，不能與單呼叫 baseline 直接作公平比較；先不選。
- 放寬 f7 coverage 或只修日文字元 guard：會把無事件核心誤算 pass，仍不保證可見句子承接事件。
- 寫入長期記憶以提醒系統：本題只需當輪已知事件；把未驗推測/測題寫成事實記憶增加污染風險。

## 凍結前必需的驗收設計

下一個獨立的 source-only 設計需先固定一個**新、未交給模型**的 User 本人已完成事件（候選：`初めて自分で古いランプの電球を替えた。今は一言だけ励まして。`；目前僅做 0-call M29 `direct/brief_encouragement`、f7 grammar 可解析、寫入本頁以前 tracked 舊檔 exact object 0 hit；尚未作正式凍結或使用），以及不同物件/動作的條件式原生 Safari 題。事前 gold 應要求第一次、User 本人、確切「替換電球」而不是泛稱修燈或「買了電球」、自然短日文與一言鼓勵，並先證明在既定字數上限內有合法自然表達。負控至少包括**非首次**（不可自動補 `初めて`）、第三者、引述、否定、多句、長關係、跨語、敏感／不確定來源、stale／forged／mismatched handoff、非 full-route、guard 後改寫、no-grounded 原始 core、下一輪不洩漏。比較除 treatment 整條 commit 外須控制相同 source、model、persona、候選、生成資源。先在**固定相同 M21 原始 plan/三候選**的 surface 邊界做確切消融，避免兩次採樣差異偽裝因果；再做各一次全新完整產品診斷，無 seed 的兩次 full run 不可單靠結果差異說 treatment 因果。原始三候選、slot attestation、final visible、所有替換／guard/episode SHA 必須可核。若底層候選已全泛稱，這是檢驗 slot 是否真的造成**可見**改變的關鍵反例，不得只挑模型本來答對的例子。

資源提案（**待事前凍結，不是已測成本**）：不得因 treatment 新增 provider/local generation 或 repair；先以實際 Web 設定列出 RightBrain deterministic／可選 model route 的基線數量，再限制本 treatment 增量為 0；若選 deterministic surface，不能預寫「RightBrain prompt token 增加」。沿用單輪 ≤20 秒作初始目標而非已證上限；源槽與驗證器是本機有限運算，但需逐輪實量所有 provider+local calls、prompt/completion tokens、user wait、vector ops、背景交錯、CPU/RSS 若可取得。若為了 final 保真不得不新增一次生成，該變更需另列單一變因與新公平成本比較，不能偷偷合入。零模型證明 source/handoff/負控及新增 receipt raw-free；fresh planner 只能說語義槽形成；**隔離真產品/Safari** 才能判可見品質；正式人評、temporal holdout 和強 LLM 優勢仍分別 pending。

## 接續決策

本頁只完成兩次失敗後的原因與設計選項收斂；同一團隊的獨立代理只讀審查確認方向合理，並指出 Web 預設 deterministic surface、歸因、raw 洩漏及 final no-send 的必要修正。**審查不是新題／門檻凍結或產品放行。**下一步先用既有隔離契約夾具，事前凍結固定 M21 plan/candidates、final utterance gold、guard 改寫／錯來源負控、零新增生成與 no-send 狀態／檔案 digest 不變條件；再確定 deterministic surface 接線與可恢復 blocked UI/延後寫入或回滾，經只讀審查後才能凍結新 source-disjoint 題及實作。若此路徑不可安全實現，保留 f7/f8 負結論，優先消融或停用無益的 opt-in f8，而不是衍生 f9/f10 題號。P4 其他獨立功能可照當前產品工作流繼續，不因這個子項 `REVIEW_REQUIRED` 把整個長期 Goal 假設為受阻。

## 後續範圍釐清：診斷實驗不等於產品承諾

再對照 f7d 私有真 Safari 的做法後，將上文 **no-send／全部狀態不變** 明確限定為「產品可承諾錯答絕不送出或持久化」的強契約；它**不是**做隔離 opt-in 診斷前的技術必需。可另凍結較窄協定：相同固定 M21 候選，唯一 treatment 為來源槽→deterministic surface，最後 auditor 在兩臂都只觀察、不阻止送出；錯句若出現，私有泡泡／JSONL／episode 原樣保存並判 strict FAIL，flag 預設關閉，失敗 DB 不復用。這與 f7d/f8 保留負結果的原則相同，卻**不能**宣稱 fail-closed、無殘留、已可部署的產品修復或正式因果優勢。此窄版需以獨立的前瞻計畫、題本、gold、成本與只讀審查取代上文的產品放行門檻後，才可改碼或送模型；不能默默拿原產品契約作診斷結果。草案在 `research/p4_source_event_surface_diagnostic_plan_2026-10-24.md`。
