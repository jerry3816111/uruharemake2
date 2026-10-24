# P4 hash-prefix 事件傳遞：第二批前瞻產品驗收計畫

狀態：2026-10-17，首輪 Safari 輸入前。逐字資料與預期路由見
`datasets/p4_hash_prefix_event_transport_fresh_probe_2026-10-17.json`。這五句是開發者依既有有限文法與靜態 hash 桶新寫，並非獨立 holdout；不能重新評分前批七輪 strict FAIL，也不能據此主張開放域理解或同模型優勢。因果設計與 before 見同日 `p4_hash_prefix_event_transport_design`。

## 前置凍結

1. 只用 opt-in `uruha_web_ui_product_p4_hash_prefix_transport.py` 與相應 detached controller。新增 per-speak 事件傳遞為唯一產品變因；空 profile collection 的 T0 前初始化是**揭露的量測 setup**，不算產品能力。原 frozen hash gate、前兩批資料、gold、raw、manifest、正式 DB 不動。
2. 零模型 focused 要證明：真 `RightBrain.speak` 會把現存 finalizer 的 SHA-only 事件傳回原 logic，且只留下同一個實際 `speak` 回覆；既有最終 graph 稽核只計與可見句相符者。直接邀約、第三者偏好未知、原候選已有連接詞、候選不符、重複/跨輪、例外與非字串均為負控制。相鄰回歸、Python compile、舊 10/10 freeze SHA、產品 controller CLI 也須核對。
3. 五句對 repository 先前資料 exact 搜尋 0 命中；新題目、gold、本計畫、程式和 SHA manifest 必須在任何新 Safari 答案前 commit、push，並核 PR #435 head。凍結後 0 answer-driven 修改、0 retry、0 換題；若事前審查發現錯誤，先修且重凍結，**首輪不得已送**。

## 隔離程序與逐輪證據

1. 使用新 launcher-owned 0700 root，隔離 HOME／memory／session／logs。新入口先跑唯一 0-turn readiness：同 PID、單一 loopback listener、HTTP 200；planned stop 後核 PID/group 退出與 port 空。若本機官方 SHA 的 ONNX 已備妥，可在**已停的新 root** 私有複製並離線核 embedding，成本獨立列；複製／解壓後只在**新 root 快取**把所有目錄/檔案限制為 0700/0600，再逐項檢查 symlink/hardlink 與 archive SHA。不能改舊隔離 root 或正式 cache；若做不到私有快取與下述 helper 全樹驗證，程序 FAIL、不送五句。
2. 在上述**已停的同一個** root，helper CLI **父程序**的 `HOME`／`XDG_CACHE_HOME` 指向新 root，但父程序 `TMPDIR` 保持 launcher 所在 temp parent，使 `validate_runtime_root` 對同一父目錄核對；helper 派生的 sandbox **子程序**則由既有 `_isolated_env` 設 `HOME=TMPDIR=<新 root>`（未顯式設 XDG）。以 `p4_profile_preinitialize_isolated.py` 的明示一次性 0600 intent/receipt，使用同 venv/既有 sandbox 建立 0-row `user_profile` collection。CLI 的 `--entrypoint`、回傳 receipt 的 `entrypoint`、0-turn metadata 的實際入口都須逐字等於本項新入口的絕對路徑 `uruha_web_ui_product_p4_hash_prefix_transport.py`，不能只接受 helper 的泛用 `uruha_web_ui_product_p4_*.py` 檢查。記錄耗時、DB bytes、before `absent/unavailable/0/null` 與 after `present/present/0/non-null digest`。這是真實 setup DB write，不是 read-only，也不能回補舊七輪。既有 sandbox 是 allow-default 且只封鎖 repo/原始 checkout 寫入，父程序的 Chroma 讀取亦不在 child sandbox 內；只能主張經路徑核對的**邏輯 DB 隔離**，不能稱不可突破的檔案寫隔離。若 helper 拒絕或 setup 後不只空 profile collection，程序 FAIL。
3. setup 後另存 T0 完整 profile snapshot；其 status/count/digest 須與 setup after 完全相同。T1–T3 在真 Safari 各送一次，逐輪保存 raw/graph、profile 全內容 snapshot、episode IDs、泡泡逐字與 M19 wait；T3 後 planned stop，stop 前後保存 snapshot，並同 DB 不同 PID 重啟；T4–T5 各送一次，再 planned stop、保存 final snapshot。每輪 0 retry，使用者等待 ≤20 秒；出現 UI/runtime error 時終止後續並保留 FAIL。語義失敗可照事前固定順序完成尚未曝光輪次，但不得修改規則追分。
4. 每輪核 selected intent/action、reported source admission、舊 source audit、prefix audit、graph UTTERANCE 與實際泡泡。reported T1/T4 的最終 reply 須等於已選 core、舊 `visible_report_preserved` 與新 `visible_core_exact`，不加入無來源固定開頭、不把第三者邀請當成使用者邀請；其中至少一輪 `final_related_hash_additions_removed > 0`，而事件中的 selected（finalizer sanitize 後、legacy 前）/legacy/returned SHA、prefix 必須能重算並與最終交付 core、來源 proof 一致。計數是去重後、與交付 reply 相符的事件列，不是人類認知操作次數。若兩輪都 0，**不論其他指標如何，有限移除路徑 FAIL**；不能用 static bucket 代替實際事件。T2/T5 直接邀約須正確選擇與稽核，T3 不得捏造後輩偏好；這些負控制不應冒出 reported/prefix audit。
5. 必要整批 gate：5/5 真輪、0 retry、兩個對話 session、一次 same-DB planned restart、5 個相異 episode、T3→restart episode 3→3、5/5 真泡泡＝graph utterance、自然日文且來源正確、上述路由/正負控制與至少一筆可核實移除、每輪 ≤20 秒；從 setup after、T0、每輪、stop/restart 到最終 stop 的 profile `db_status=present`、`collection=present`、rows=0、完整內容 digest 完全相同。任一缺失整批 strict FAIL。Safari 畫面若沒有持久操作錄影，只能分別報告「當輪目視」與「raw 可重算」，不冒充可獨立重算泡泡或 0 retry。
6. 分別報告準備/ONNX、profile setup、兩次啟停、五輪等待、model calls/tokens、DB 增量；0 model call 不算 fresh generation。圖像節點應能看到真正被交付的來源/selected/utterance 與 prefix provenance；事件 SHA 可在研究收據核，不向普通聊天傾倒技術分析。完全停機後保留私有原件，結果文件附 SHA、逐輪表、失敗與證據限制。即使 strict PASS，也不抹除前批 T3 主語語義錯誤，不能推論 P4 整體完成、人評、正式 temporal holdout 或人類反應方程式。

若此第二次前瞻仍未過，保留 raw 與最小反例，進 `REVIEW_REQUIRED`；不做第三批換題追分。下一個**獨立**可歸因項是 T3「使用者自行先查行程」與「請助手先提問」的主語/作用域准入，不與本 transport 結果混合。
