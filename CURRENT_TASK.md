# 目前任務卡

更新：2026-09-20。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P3-B69B source2 context-only acquisition and prediction batch（FUTURES LOCKED）

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

2026-09-19～20使用者明確授權依既定計畫持續執行並使用Codex token，不必逐步停下確認；授權不包含花錢、付費API、
登入、cookies／帳號資料、hidden future洩漏、改弱baseline、降低gate或無限重試。此授權覆蓋B57 review的
`next_execution_authorized=false`，允許B58唯一一次新provider capability。

B58只改resolver同時在private memory提供allowlisted HTTP headers；明確拒絕Cookie／Authorization／Proxy-Authorization／
Set-Cookie，丟棄Range與未列入的非敏感header，URL與header name/value/hash都不落盤。69項affected suite通過後執行：
resolver exit 0、`1.560216s`、1個private URL與3個allowlisted header；direct ffmpeg仍在`0.079168s` exit 8、
`tls_or_network`。0 artifact／future／semantics／prediction／model／paid access。完整驗收：
`analysis/p3_b58_private_allowlisted_header_transport_acceptance_2026-09-20.md`。

B57 headerless與B58 allowlisted-header是兩個前瞻direct-audio修正批次，均失敗；依流程關閉此分支，不再加header、換小參數或
重跑。B59改走metadata-only caption availability probe；87項affected suite後執行成功：resolver exit 0、`1.598962s`，同一來源
沒有日文人工字幕，但有`automatic / ja / json3`，0 caption content／future／semantics／prediction／model。完整驗收：
`analysis/p3_b59_source_semantic_availability_probe_acceptance_2026-09-20.md`。

B60事前104項affected suite通過；resolver成功選出同一track，但唯一urllib caption GET在取得內容前以`tls_or_network`失敗：
0 raw caption／public artifact／prediction-side future access。完整驗收：
`analysis/p3_b60_private_caption_cutoff_extractor_acceptance_2026-09-20.md`。

B61事前114項affected suite通過後成功：yt-dlp native downloader exit 0、`1.888588s`；private full caption
`1,483,058 bytes`投影後刪除，發布65個cue，first/last=`3002.760/3176.079s`；fresh reader exit 0、hash一致、
不回傳text。prediction-side future／prediction／model仍為0。完整驗收：
`analysis/p3_b61_native_subtitle_cutoff_extractor_acceptance_2026-09-20.md`。

B62凍結同一qwen3.5:9b、context、兩call graph、每條512 completion上限、seed／temperature與六label；第一個
`BASELINE_LITERAL` representation call已回傳，但exact schema validation失敗，system未執行、prediction未凍結、future仍0。
raw result因call record只在condition成功後append而誤記0 calls；依控制流程operational actual=`1`，tokens/latency=`unavailable`，
不可填0。完整驗收：`analysis/p3_b62_real_context_prediction_acceptance_2026-09-20.md`。

B63事前22項測試後，以Ollama JSON schema執行；第一個baseline representation call完成並正確記錄：1986 prompt、256
completion（等於num_predict上限）、22.292540秒，回傳後仍parse失敗；system與prediction未執行，future仍0。這支持output
被completion ceiling截斷，但未保存raw，不能斷言確切截斷內容。完整驗收：
`analysis/p3_b63_schema_enforced_prediction_acceptance_2026-09-20.md`。

B64是prediction execution第二個、最後一個修正；保持每個condition總completion ceiling=512與所有研究條件不變，只把兩call
相同分配由256+256改為320 representation +192 prediction。provider-boundary accounting與JSON schemas不變。B64成功才可封存
兩條prediction並進separate future unlock；B64失敗則停止prediction修正，不再放寬schema、增加總token或重跑。任何結果都不得
以單一row宣稱全面優勢或formal M56。

B64事前26項suite通過並凍結提交後執行；第一個baseline representation call完成，`1986/320` prompt/completion tokens、
`25.001742s`，completion再次精確等於ceiling，回傳後仍parse失敗。model call=`1`，system/prediction/future/outcome/retry/
fallback=`0`。因此B62 two-call interface兩個修正批次已用完並關閉；不得把後續工作說成第三次修正。完整驗收：
`analysis/p3_b64_final_equal_budget_prediction_acceptance_2026-09-20.md`。

B65若繼續，必須另立新研究介面：用相同`qwen3.5:9b`、同一real pre-cutoff context、相同condition order、seed、temperature、
`num_ctx`及每condition completion ceiling `512`，把失敗的free-standing representation→prediction兩call改為一次bounded joint
representation-and-prediction。兩condition使用同一個有長度上限的JSON schema與相同一call graph；prompt只允許baseline採literal
state、system採可反駁pragmatic state。先contract/tests/freeze/commit，才可各做一次model call。完成兩條prediction前仍不得讀
3181秒後future；成功也只授權另一步outcome unlock，不是正確率或優勢結論。失敗原樣保留，不以同一介面追參。

B65事前37項affected suite與freeze commit後成功：同一`qwen3.5:9b`完成baseline/system各1 call；實際prompt tokens=
`2224/2217`、completion=`261/233`、latency=`23.262607/18.687710s`，均低於相同512 ceiling。baseline最高label為
`accept_support_and_continue=0.65`，system為`acknowledge_then_continue=0.60`；兩條prediction已封存，state文字只留hash。
future/outcome/retry/fallback仍為0。完整驗收：`analysis/p3_b65_bounded_joint_prediction_acceptance_2026-09-20.md`。

B66先以B65 immutable saved result與canonical result hash綁定prediction，再凍結outcome-only worker：使用同一source的日文automatic
caption，但只公開`3181.0..3241.0`內完整cue；private full caption取得後刪除，禁止回讀3000..3180 context、禁止改prediction、
禁止新model/judge call。評分必須在看future前定案：以可重現的observable behavior mapping取得實際label，再對兩組預測分布計算
selected-label hit、actual-label probability、Brier score與log loss；文字預測只做有證據的token/phrase overlap描述，不假裝是語意人評。
單一row無論正負都只算exploratory counterexample，不得宣稱全面優勢或formal M56。

B66在freeze commit後成功揭盲：first 3 cues=`3182.520..3190.559s`，固定marker `?`令actual proxy label=
`ask_clarification`。baseline/system對actual label機率=`0.05/0.10`、Brier=`1.360/1.235`、log loss=
`2.9957/2.3026`；依凍結rule system勝，但兩組top-1都錯。0 model/judge/retry/prediction mutation；private full caption在fresh
future reader前刪除。完整驗收：`analysis/p3_b66_future_outcome_scoring_acceptance_2026-09-20.md`。

B67不使用B66已曝光row調prompt、marker或門檻；事前固定同一來源四個尚未公開給prediction side的time windows：context/future分別為
`600..780/781..841`、`1200..1380/1381..1441`、`1800..1980/1981..2041`、`2400..2580/2581..2641`。
先一次private caption acquisition只發布四個context artifact，刪除raw與所有future後，原樣重用B65 joint schema、qwen3.5:9b、
condition order、seed、temperature、num_ctx及每condition 512 ceiling，封存8條prediction。任一row/call失敗即保留不完整batch，
不得先讀任何四個future；全部完成才可另立B68一次揭盲aggregate。這是same-source replication development evidence，不是獨立holdout。

B67事前31項affected suite與freeze commit後完成：四列context cue counts=`77/72/66/72`；同一B65介面8/8 calls完成，
prompt/completion tokens total=`18,908/1,697`、model latency=`152.907164s`。top-1有三列condition差異，八條prediction均已
封存；future/outcome/retry/fallback=`0/0/0/0`。完整驗收：
`analysis/p3_b67_same_source_multiwindow_prediction_acceptance_2026-09-20.md`。

B68必須綁定B67 immutable result hash，以一次private acquisition同時投影四個凍結future windows，raw刪除後才由fresh reader
讀取。每列原樣重用B66 frozen first-3-cues/12-second target、marker order、actual-label probability、Brier、log loss與winner rule；
禁止逐列解鎖、改marker/metric、改prediction或呼叫model/human/LLM judge。報告逐列正負與aggregate平均，但四列仍是同一影片的
development replication，不得外推成independent holdout或全面優勢。

B68在freeze commit後一次揭盲四列：row wins system/baseline/tie=`4/0/0`，mean actual-label probability=
`0.2875/0.2625`、mean Brier=`1.0134/1.17095`、top-1 hits兩組皆`1/4`。r0600與r1200的actual-label probability
相同，system只因Brier稍低取勝；baseline mean log loss被r1800的zero-probability放大。0 model/judge/prediction mutation/retry。
完整驗收：`analysis/p3_b68_multiwindow_future_aggregate_acceptance_2026-09-20.md`。

B69不得繼續切同一支影片追分。下一必要交付是事前選定另一支公開一ノ瀬うるは長影片，先只做metadata/caption availability與
duration檢查，不讀字幕內容；選擇規則、source id、context/future windows必須在內容取得前commit。後續原樣重用B65介面與B66 proxy，
但因新source是在看過B68後選定，仍稱source-level prospective replication，不假稱正式independent holdout。若找不到合法可用caption，
保存availability負結果，不用登入/cookies/替換到有利來源。

B69 source selection已完成但尚未查caption metadata：固定query與selection rule選中官方頻道rank 1、duration `12,933s`的
`Mlk5e3hBnb8`，排除原source；四個context/future windows也已固定為600秒間隔的同一組位置。下一步B69A只准一次
metadata-only日文caption availability probe，0 caption content/model/future；若不可用就保存負結果，不換來源。

B69A事前28項affected suite與freeze commit後完成：唯一一次metadata-only resolver在`1.678007s`成功，第二來源無日文人工字幕、
有`automatic / ja / json3`；raw metadata `508,363 bytes`只在記憶解析後丟棄。caption content／future／model／retry／fallback=
`0/0/0/0/0`。完整驗收：`analysis/p3_b69a_source2_caption_availability_acceptance_2026-09-20.md`。

B69B只可使用B69事前固定的第二來源與四個context windows；一次native yt-dlp acquisition後，只發布600..780、1200..1380、
1800..1980、2400..2580的context artifacts，刪除private full caption與四個future內容，再由fresh reader核對。原樣重用B65
bounded joint schema、同一qwen3.5:9b、condition order、seed、temperature、num_ctx與每condition 512 completion ceiling，依序完成
4列×2條prediction。全部8 calls完成前不得讀任何future；任一失敗即保存不完整batch並停止，不重試、不換來源、不調prompt／
門檻。這仍是source-level prospective replication，不是正式independent holdout。

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
