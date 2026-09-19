# 目前任務卡

更新：2026-09-19。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B58 private allowlisted-header transport review（REVIEW_REQUIRED）

狀態：**P3-B54完成；P3-B55 REVIEW_REQUIRED。** capability-separated extractor在事前freeze後，以5秒合成raw驗證generation只取得
`1..3`秒artifact；3秒後2000 Hz sentinel／可見440 Hz能量比`6.781521697810383e-31`，低於凍結門檻
`0.0001`。raw在2個fresh reader process前刪除、private root mode `000`、兩次SHA-256一致、0 forbidden field／
private canary hit／private import。超長artifact、hash、禁止欄位、symlink、hardlink與permission均fail-closed；
B52全版本至B54共58項回歸通過。仍為0 reserved-source media、0 hidden future、0 prediction、0 model call。
完整release：`research/p3_b54_unidirectional_context_extraction_release_2026-09-18.json`。

B55 V1因ffmpeg version flag錯誤在0 network時fail；保存後V2只把`--version`改為`-version`，offline 24項通過後
消耗唯一transport invocation。V2在1.978149秒以yt-dlp exit 1結束：1 request、0 local/public artifact、0 future、
0 playback／semantic inspection／prediction／model。依事前規則不再重試或追加修正。完整反例與選項：
`analysis/p3_b55_reserved_source_context_transport_review_required_2026-09-18.md`。

### B56 執行結果與新設計審查

使用者以「請繼續」授權review建議1，覆蓋B55 `next_execution_authorized=false`，但不改其他邊界。B56另凍結
一次diagnostic transport，使用相同source、`*3000-3180`、工具、0 retry／fallback與B54 public gate；private worker
只把stderr映射成allowlisted error class，不保存／顯示原文、hash或token。允許類別為availability、provider challenge／
authentication、TLS／network、extractor／format、ffmpeg／postprocessing、command／option、unknown；分類必須先以fixture
凍結並涵蓋redaction canary。

若同一請求成功，只可輸出B54 exact 180秒artifact／manifest，private transport刪除後以fresh reader核對duration與hash；
若失敗，保存category、return code、stderr byte count與elapsed，0 public artifact後停止。不得再次修正／重跑，不得登入、
cookies、換來源、改cutoff、存stderr文字、人工播放／語意檢查、取得hidden future、執行prediction／model、寫正式M56或
production memory。

B56事前41項通過後消耗唯一請求：yt-dlp在2.944204秒exit 1，診斷類別`ffmpeg_or_postprocessing`，stderr
35 bytes只計數後丟棄；private runtime已刪除，0 public artifact、0 future／prediction／model。離線確認yt-dlp可找到
ffmpeg/ffprobe 8.0.1，direct ffmpeg synthetic pipeline exit 0，因此不是缺少ffmpeg，但現有redacted evidence不足以判定
postprocessing子原因。完整驗收：`analysis/p3_b56_allowlisted_diagnostic_transport_acceptance_2026-09-19.md`。

2026-09-19使用者再次以「請繼續」明確授權B57，並確認YouTube公開影片作為未來prediction資料來源方向。B57單一架構
變因：private yt-dlp resolver只把一個`bestaudio` signed URL留在記憶，direct ffmpeg再裁`3000..3180`並走B54 gate。
URL／resolver stdout／stderr／metadata不得落盤、hash或進receipt；只記byte count、URL count、allowlisted host category與
failure category。仍為0 retry／fallback、無cookies／登入、同source/cutoff；成功前不得人工播放／語意檢查，成功後也只
能把context artifact交給下一個prediction freeze，不得在本步讀`3181..3241`。

B57事前52項通過後執行：resolver exit 0，在1.927396秒取得1個private `googlevideo_cdn` URL；URL text/hash/excerpt
均未保存。direct ffmpeg在0.081831秒exit 8，分類`tls_or_network`；private runtime刪除，0 public artifact、0 future／
prediction／model。這排除source resolver失敗，但不能把原因斷言為特定HTTP status或header。完整驗收：
`analysis/p3_b57_split_resolver_direct_ffmpeg_acceptance_2026-09-19.md`。

B58尚未授權。建議只改resolver同時在private memory提供allowlisted HTTP headers，禁止Cookie／Authorization與任何
header落盤，再由direct ffmpeg執行同一`3000..3180`窗口與B54 gate。此為新provider invocation/capability，不能從B57
授權外推；審查前不再請求來源、不讀future。

## 工作環境

- 安全 worktree：`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`。
- 分支：`codex/v2-15-pragmatic-research-showcase`，PR #435。查實際 HEAD，不碰原始 dirty checkout。
- Python：產品測試用 `.venv/product_checks/bin/python`；純標準庫 verifier 可用系統 python3。
  不全域安裝依賴。Gradio／Torch／brain 的 import 留在 isolated worker，不放純資料 module 的頂層。
- 長期目標檔：`LONG_TERM_GOAL.md`。2026-09-09 Goal 工具讀到 usageLimited；文件更新不等於 app 已恢復。
  不清除／假完成／改內部 DB 來換 Goal。使用者手動回合仍可執行已授權工作。
- 本機 Safari 目前有既知工具拒絕記錄，驗收 pending；不以其他 UI 技術繞過。P3-A 不依賴瀏覽器。

## 已完成、不要重做

- P1 prediction identity 跨重啟保存；P2 compact planner、表達 core commit、當輪求助、婉拒、
  獨處要求與 speaker-qualified recall 的有限產品 baseline 已凍結：
  `research/p2_integrated_product_baseline_freeze_2026-09-09.json`。4 mechanism＋1 abstention、結構4/4。
- P3成本記錄收尾 commit：`34bef3d01d236873b4aa384b76aba2893ff9949d`。
  `research/p3_compute_accounting_freeze_2026-09-09.json`；121 passed／8 dependency warnings。
  `analysis/p3_complete_product_compute_accounting_acceptance_2026-09-09.md`。
- P3-A fail-closed comparison harness 與自審修正已凍結；P3-B1 isolated product worker 將產品真實 OpenAI／
  native M31 globals 綁到同一 gate，兩次 lazy import、same-case restart、cross-case refusal 均通過。驗收：
  `analysis/p3_b1_product_worker_acceptance_2026-09-13.md`。仍為 0 real model/network/paid calls。
- P3-B2 developer smoke source／annotations 已分離凍結：6 cases、24 user turns、12 sessions、三語各2、
  六 family 各1，建立 72 個 allowlisted views。驗收：
  `analysis/p3_b2_developer_smoke_acceptance_2026-09-13.md`；未執行任何生成。
- P3-B3 provider/tokenizer binding 在既有四種 fixture 通過；P3-B4 找到產品 call shape drift；P3-B5 adapter 已補齊並驗證
  seed/top_p/num_ctx。P3-B6 單一 product canary 工程通過，但品質未定。P3-B7 baseline 執行保留負結果：3 calls、2 complete、
  1 prompt-count failure，沒有三條件比較。詳見 `analysis/p3_b7_canary_baselines_acceptance_2026-09-14.md`。
- 真實本機run2：5 sessions／9輪，與P2可見回覆9/9相同；ledger 2生成＋130記憶操作，
  2,901生成tokens、30.834245秒；四個結構checks通過。兩次run均保存。
- native M31只mocked transport驗證，這九輪未實際觸發；Chroma embedding token／CPU/RSS/energy未量測。
  HTML是runtime graph產物，Safari未驗收。開發控制不是新holdout或全面能力證據。
- 不為新純資料harness重跑未變動的121項或M57.9八分鐘套件。

## 仍需保留的限制

- P2只在已曝光開發案例通過，不等於open-world對話、50輪可靠、人評、強LLM優勢或人腦方程式。
- 原生M31預設qwen3.5:9b，而一般planner是qwen2.5:7b；P3必須按config在isolated worker import前統一，
  transport核對所有路徑。不是改永久產品預設。
- P3共同歷史目前是system-anchored paired；報告必須揭露其條件性，不能當獨立對話偏好實驗。
- 正式研究依據上次封存紀錄仍缺真人／真實temporal資料；此輪未新讀私人ledger。M57.9 partial，
  M58沒有新授權。產品比較不能補造正式結果。
- developer smoke僅逐案推進，case06在B27仍為0 generation；未執行的cases／turns、case06評分、真人與formal confirmation仍不可宣稱。

## 回報方式

使用中文，先回答使用者新問題，再依卡片工作。短報實際成果、必要數據／例子、限制、Git與下一gate。
不要用「測試很多」代表使用者感受到的進步。兩次有證據的修正仍失敗就列反例進review，不亂加功能。
