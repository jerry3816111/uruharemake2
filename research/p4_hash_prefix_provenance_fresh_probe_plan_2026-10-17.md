# P4 hash-prefix provenance：首輪前產品驗收計畫

狀態：2026-10-17。此檔與 `datasets/p4_hash_prefix_provenance_fresh_probe_2026-10-17.json` 在任何新 Safari 輸入前封存。這七句由開發者編寫，不是獨立 holdout；前批六輪 strict FAIL、原 raw、gold、程式與 8/8 SHA 不改也不重播。單變因與 before 見同日 `p4_hash_prefix_provenance_gate_design`。

## 事前證據與上限

1. 先核本項 focused、相鄰回歸、compile、launcher CLI；核原 8/8 frozen manifest。七句對 repository 既有資料 exact 搜尋先前命中 0。新資料／程式／本計畫 SHA、Git commit/push、PR #435 head 皆在首輪前固定。凍結後不依結果改 gold／判準／prefix gate；若審查找出失誤，必須先改、重測、重新凍結，且真輪仍不得開始。
2. 使用 launcher-owned 新 0700 temp root、隔離 HOME／memory／session／log，不讀正式 DB。不依賴網路下載；如本機 Chroma ONNX archive SHA 符合官方常數，可在 0-turn 時獨立複製、離線驗 embedding readiness，預熱成本另記。只以新 controller 啟產品、核同 PID／唯一 loopback listener／HTTP 200；不建立公網 share link。若 0-turn readiness 失敗，保留程序 FAIL，七句不曝光。
3. 完整 profile 快照使用獨立 `p4_profile_full_content_snapshot.py`：T0、每輪 UI 完成後、T3 stop/restart 前後及最後 stop，各保存不可覆寫 0600 receipt。`db_status`、`profile_collection_status`、row count、所有 subject 的 ID＋metadata＋document＋embedding canonical SHA 一起比較；缺一個快照或狀態不明即 gate FAIL。它不是 byte-read-only SQLite；必要時另存 DB 檔 SHA，不能把其讀取副作用隱藏。正式個人資料絕不進工具。
4. 真 Safari 新測試分頁 T1–T3 逐字各送一次、0 retry、每輪最多 20 秒；T3 後 planned stop 核原 PID exited／port vacant，同 DB 新 PID 重啟再跑 T4–T7。每輪核可見 bubble 與 graph utterance 完全相同、selected/source/新舊 audit、episodes IDs、寫回類型、完整 profile digest、M19 wait 和實際 model/token 成本。UI／runtime 錯誤終止後續；語義 FAIL 可完成尚未曝光的其他輪並各列結果。
5. strict PASS 條件：7/7 真輪、0 retry、2 sessions、一次 same-DB restart，七個相異 episode，T3→restart episode 3→3，profile 整 collection digest/count/status 全程不變；7/7 bubble＝graph utterance、最終日文自然且不編來源；T1/T4/T7 reported route 舊 audit `visible_report_preserved` 且新 audit `visible_core_exact`、不能多一個固定前綴或替 Uruha 接受；其中至少一輪新 audit 的 `final_related_hash_additions_removed > 0`，否則尚未在 Safari 真路徑觸發被修機制，strict FAIL；T2/T6 直接邀請 selected/action 原 audit 正確且新 reported/prefix audit 缺席；T5 未知偏好不可捏造；T3 的回覆須尊重「先確認再回答」順序。七輪 M19 user wait 都 ≤20 秒。任一缺失整批 strict FAIL。T3 若上游 selected candidate 沒有時間連接詞，則只能算「順序語意控制」，**不能**宣稱 Safari 已驗證保留上游連接詞；保留性正例只由首輪前零模型契約證明。

新 graph audit 只保證這個 finite reported-offer core 不再由 hash 裝飾遮蔽；直接邀請、未知與 T3 的自然度仍須 Safari 目視核對，不可因新節點不存在就推斷成功。模型生成、瀏覽器、人評、正式 temporal holdout 分軸記錄；本項即使 PASS 也只改善產品表面來源准入，不證明開放域語用理解或完整人類反應方程式。
