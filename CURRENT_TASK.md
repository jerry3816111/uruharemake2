# 目前任務卡

更新：2026-09-21。這是唯一當前工作順序；歷史下一步留在 Git／交接，不直接執行。

## 唯一下一步：P4-K typed recall contract 最終交付修正

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

B69B已terminal失敗且未揭盲：唯一caption acquisition與四個context artifacts成功；cue counts=`69/66/77/55`。本機模型前6 calls
完成前三列paired conditions，第7個`s2r2400 / BASELINE_LITERAL` provider call完成但prediction parser以`schema`拒絕，第8 call未執行。
總實際prompt/completion tokens=`15,429/1,650`、model latency=`133.887876s`；future/outcome/retry/fallback=`0/0/0/0`。依事前規則
禁止同來源重跑、補第8 call或B69C揭盲。完整反例：`analysis/p3_b69b_source2_multiwindow_prediction_acceptance_2026-09-20.md`。

B70先在已曝光development fixtures建立與來源無關的介面可靠度gate，不回頭追B69分數。最小單一機制候選是：保留JSON結構、
日文與所有內容gate，只對全部finite且非負、總和大於0的label weights做相同的deterministic normalization，再以凍結精度核對sum=1
且ranking不變；baseline/system完全同規則。同時把未來schema拒絕原因映射為不含raw response的allowlisted類別。先離線contract/tests/
failure fixtures與現有合法outputs；若gate通過，另立B71在任何caption內容前選定第三來源，修正版只能在新來源前瞻測試。B69第二來源
永久保留未完成反例。

B70離線gate已完成：相同adapter把六個finite nonnegative weights以50位decimal／12位輸出精度正規化，residual固定加到label順序中
第一個最大weight，並確認selected behavior不變。例`[2,3,1,1,1,2]→[0.2,0.3,0.1,0.1,0.1,0.2]`；baseline/system
同規則。缺label、負值、nonfinite、全零、非日文與缺state仍拒絕；38項affected suite通過。model/network/future/B69 retry均0。
這不能反推B69 raw失敗原因，也不是效果證據。完整驗收：
`analysis/p3_b70_prediction_interface_reliability_acceptance_2026-09-20.md`。

B71下一步必須在查caption metadata/content前，用固定搜尋與排名規則選第三支官方長影片，排除`4y5GiQpgJgo`與`Mlk5e3hBnb8`，
同時事前固定四個context/future windows。選定後才可另做availability；任何prediction都必須事先綁B70 adapter、同一B65模型／prompt／
token上限與兩condition。因第三來源仍是在先前結果後設計，只算prospective development replication，不假稱正式independent holdout。

B71已依freeze唯一搜尋選中official rank 2的`j6Hlk9cY9LQ`，duration=`12,883s`；四組`s3r0600/1200/1800/2400`
context/future windows已同時固定。搜尋耗時`0.936168s`，raw metadata `15,402 bytes`在記憶解析後丟棄；caption metadata/content、
model、future、retry、fallback=`0/0/0/0/0/0`。完整驗收：`analysis/p3_b71_source3_selection_acceptance_2026-09-20.md`。

B71A只准對已固定source做一次metadata-only日文caption availability probe，0 caption content/model/future；不可改query、來源或windows。
若無支援的Japanese track，保存負結果並停止此來源，不使用登入、cookies、替代來源或人工挑選。

B71A事前39項affected suite與freeze commit後完成：唯一metadata-only resolver在`1.827625s`成功；無日文人工字幕，有
`automatic / ja / json3`。raw metadata `508,363 bytes`只在記憶解析後丟棄；caption content/model/future/retry/fallback=
`0/0/0/0/0`。完整驗收：`analysis/p3_b71a_source3_caption_availability_acceptance_2026-09-20.md`。

B71B只可使用B71固定的第三來源與四個context windows；一次native caption acquisition後只發布context artifacts，刪除private full
caption與future，再由fresh reader核對。模型、prompt、options、condition order與每condition 512 completion ceiling原樣沿用B65；
唯一新增介面機制是事前B70 deterministic probability normalization，baseline/system完全同規則並記錄是否實際套用。8 calls全部完成前
不得讀future；任一call或parser失敗即terminal保存，不重試、不換來源、不放寬內容／日文gate。成功也只授權另一步整批future揭盲，
不能先宣稱修正有效或system有優勢。

B71B已完成8/8 predictions：四列context cue counts=`72/60/58/68`；prompt/completion tokens=`17,312/1,763`，model latency=
`149.1632s`。B70 adapter綁定兩condition，但8個input weight sums全為`1.0`，normalization applied=`0/8`；因此成功不能歸因於
B70，只能證明adapter未破壞合法輸出。兩condition top-1在2/4列不同；future/outcome/retry/fallback=`0/0/0/0`。完整驗收：
`analysis/p3_b71b_source3_b70_prediction_acceptance_2026-09-20.md`。

B71C必須綁定B71B immutable result hash，一次private caption acquisition同時投影四個固定future windows；raw刪除後才由fresh reader
讀取。逐列原樣重用B66/B68的first-three-cues-within-12s、marker order、actual-label probability、Brier、log loss與winner rule；
禁止逐列解鎖、改prediction/marker/metric或呼叫model/human/LLM judge。正負結果都保存；仍是development proxy，不是人類真值或正式holdout。

B71C已一次揭盲第三來源四列：row wins baseline/system/tie=`2/2/0`；平均actual-label probability=
`0.375/0.2375`、平均Brier=`0.81845/0.95215`、top-1 hits=`2/4`與`1/4`，均是baseline較好。
更重要的是四列均無marker命中，全部落到default `acknowledge_then_continue`，actual label diversity=`1`。這沒有重現
B68第一來源的system 4/4 row wins，也暴露目前caption-marker proxy在第三來源缺乏區分力。完整驗收：
`analysis/p3_b71c_source3_future_aggregate_acceptance_2026-09-20.md`。

B72不得新增來源、字幕、future或模型呼叫，也不得用已曝光B68/B71C結果調marker後回報優勢。下一必要交付是綁定兩份immutable
result/release，計算跨來源描述統計、label diversity、marker hit、來源方向反轉及不同metrics是否同向；明確判定現有proxy是否足以支撐
system advantage claim。若量尺失效，保存`proxy_not_adequate`，停止累加同類影片，另立尚未看新prediction/outcome的評價目標重設計；
不得只報對system有利的row wins或Brier而隱藏actual-label probability/top-1反向結果。

B72已完成read-only audit並判定`proxy_not_adequate_for_system_advantage_claim`：跨兩來源8列的row wins雖為system 6、baseline 2，
actual-label probability卻為baseline/system=`0.31875/0.2625`，top-1=`3/8`與`2/8`；Brier/log loss反向偏system。
第三來源actual label diversity=`1`且marker hit=`0/4`，三個metrics發生source direction reversal。0新來源/future/model/judge；
完整驗收：`analysis/p3_b72_cross_source_proxy_validity_audit_acceptance_2026-09-20.md`。

B73下一步不是修改已曝光marker，而是先凍結新的prospective target設計與評價方法：target必須有可辨認的stimulus→response單位，
把直接可觀察行為與需要人類判讀的語用／被理解感分層；automatic proxy只能在與盲化真人標註達到事前可靠度後使用。B73先建立schema、
annotation packet、雙coder reliability gate、missing/ambiguous處理及同模型公平比較欄位，並用synthetic fixtures驗證工具；不得讀第四來源內容、
執行新prediction或用Codex/LLM標註冒充真人。已曝光B68/B71C只作失敗例，不可作新量尺的成功驗證資料。

B73已完成protocol/tooling：prediction view不含outcome，coder view不含condition/prediction；不可辨認boundary的episode fail-closed，
acoustics缺少只能標unavailable。target分成observable moves、goal、stance、literal/pragmatic relation、surface text與另行主觀人評；兩位
不同真人各18 episodes、四個primary alpha均需`>=0.667`且至少兩種observed categories。27項affected suite通過；新來源內容/
prediction/outcome/model/human labels=`0/0/0/0/0`。完整驗收：
`analysis/p3_b73_prospective_response_target_protocol_acceptance_2026-09-20.md`。

B74只建立可實際使用的本機雙coder收集平台：兩個不可互看的private ledgers、同一frozen packet manifest、無condition/prediction欄位的
HTML表單、逐欄validation、完成後才可由獨立analyzer讀兩份ledger。先用synthetic packets驗證啟動、提交、重啟保存、跨coder隔離、
incomplete拒絕與reliability report；不得用synthetic pass解鎖真實來源或宣稱human reliability。Safari若工具仍拒絕則保持UI pending，
不能改稱通過；也不得在B74先取第四來源內容。

B74已完成：20項affected tests通過；Safari實際新增1 tab顯示synthetic標註頁，提交一題後`0/18→1/18`。private root/ledger
permissions=`0700/0600`，兩ledger entries=`[1,0]`；完整18×2 synthetic calculation的四個primary alpha均`1.0`，但
`synthetic_authorizes_human=false`、`real_prediction_authorized=false`。新來源/model/正式human label=`0/0/0`。完整驗收：
`analysis/p3_b74_isolated_two_coder_collection_site_acceptance_2026-09-20.md`。

B75下一步只設計並凍結real 18-episode sampling frame：來源選擇與slot規則必須在內容review前固定，每個slot需可辨認外部stimulus、
Uruha response與時間boundary；無清楚stimulus的直播獨白標unusable且不得用鄰近字幕補成對話。frame需包含controlled same-surface
context pairs與literal/pragmatic context-flip controls，並維持公開來源provenance、acoustic unavailable規則與train/dev/holdout分離。
先做metadata/source availability，不得在sampling freeze前觀看或標註response內容；B75也不得直接執行model prediction。

B75已terminal不足：唯一一次`ytsearch24:一ノ瀬うるは コラボ 雑談` metadata search exit 0、`1.323599s`、raw stdout
`33,182 bytes`丟棄，但符合official channel＋duration＋keyword＋exclusion的來源為`0`。caption/media/model/outcome/retry/fallback=
`0/0/0/0/0/0`，0 selected source／slot。這是provider ranked search discovery失敗，不是官方頻道內容不存在，也不是B73否定。
完整驗收：`analysis/p3_b75_real_episode_sampling_frame_acceptance_2026-09-20.md`。

B76是此source-discovery的第一個前瞻修正：改為一次直接列舉相同official channel公開uploads的metadata inventory，再套用事前固定的
排除、duration、title keywords與provider order；不得使用B75 query、人工選片、caption/content或playback。若仍不足三支，保存負結果並
停止本來源發現分支，不做第二個關鍵字／小參數重試。若足夠，只能建立同一6-relative-region-per-source frame；content review與model仍另 gate。

B76亦terminal不足：official channel `/videos` inventory exit 0、`0.565957s`、raw stdout `8,540 bytes`丟棄，eligible sources=`0`；
caption/media/model/outcome/retry/fallback全為0。因raw未保存，不能事後斷言是哪個metadata field造成0。B75＋B76已耗盡本source-discovery
分支原始嘗試與唯一修正；不得擴limit、換tab／keyword或人工挑選。完整驗收：
`analysis/p3_b76_official_channel_inventory_acceptance_2026-09-20.md`。

P3-C1已完成離線contract/data/metrics freeze：18個surface families、36 variants；train/dev/holdout各6 families，中文／英文／日文
各6 families。每組literal/pragmatic context保持byte-identical surface，family不跨split；prediction packet不含target，聲學固定unavailable。
baseline取得完整context且可正常推理，system唯一介入是顯式可反駁pragmatic state；兩組同模型、同一call、每item同384 completion ceiling，
額外system state token計入同budget。primary為holdout mean multiclass Brier至少改善0.03，且literal overinterpretation不得更差、paired
context-flip top-1不得更差。11項focused與43項B65/B70/B73/C1 adjacent通過；model/network/Uruha source/future/human label/production/
formal write全為0。完整驗收：`analysis/p3_c1_controlled_context_flip_acceptance_2026-09-20.md`。這只是developer-authored prospective
proxy contract，不是model效果、人評、獨立holdout或reference-person prediction。

P3-C2已完整執行但未通過事前效果量：8個train smoke後24個dev calls，32/32 validated，0 retry/fallback/holdout/Uruha future。
總成本=`22,952` prompt、`6,497` completion、`326.528142s` model latency。baseline/system mean Brier=`0.13305/0.120717`，
system改善`0.012333`，低於SESOI `0.03`；兩組dev top-1與paired flip皆100%，literal overinterpretation皆0，顯示developer題有ceiling。
English/Chinese system Brier較低，但Japanese=`0.1058/0.1583`與deixis=`0.0608/0.1658`反向。system相對baseline耗用
`1.2851×` prompt、`3.112×` completion與`2.3136×` latency；沒有成本優勢替代結論。依freeze判`controlled_lane_success=false`，
C1 holdout保持0 access，不以改門檻、改target或偷跑holdout追分。完整驗收：
`analysis/p3_c2_controlled_context_flip_acceptance_2026-09-20.md`。

P3-C3是唯一下一步：只做官方、外部作者的controlled pragmatic benchmark／stimulus資源discovery，先查DRInQ、PaCE及直接相關官方
artifact的paper supplement、repository、license、資料schema、same-surface context pair與train/dev/test邊界；不得下載／讀取hidden test
answers、執行模型、取得新Uruha來源／future或把C1 developer cases改名獨立holdout。事前列fit criteria：必須能在相同完整context與同模型
條件比較direct baseline和system，必須同時量context sensitivity與literal overinterpretation，必須有可合法重現的split/provenance；若官方
artifact不可得、license不允許或任務只測另一種能力，保存負結果而不自行重建答案。P3-C3輸出只能是候選資源與是否適合的決策，不能先宣稱
外部benchmark優勢；若有合格資源，另立contract/freeze後才可取允許的train/dev部分，test仍鎖定。

P3-C3已完成並保存`no_executable_external_benchmark_now`。DRInQ具同surface context variation且作者repo有單一validated CSV，
但未見dataset license與train/dev/test split，因此只列`conditionally_eligible_blocked`，0 CSV下載／row read。PaCE的方法最符合
literal/pragmatic context-flip，但本次從ACL官方頁與官方來源搜尋未發現可核對的dataset artifact，列
`method_fit_artifact_blocked`；這不斷言資料永不存在。PUB有MIT artifact，但不是same-surface literal/pragmatic pair且專案以前已用過，
不能當新independent holdout。三者合計executable candidate=`0`；benchmark dataset download／row／hidden answer、model、new Uruha
source/future、human label、production write均為0。完整驗收：
`analysis/p3_c3_external_pragmatic_benchmark_discovery_acceptance_2026-09-20.md`。

P4-A是唯一下一步。先只讀盤點既有本機聊天入口、真實runtime node graph、VRM 3D與Function Calling的啟動方式、資料源、port／process
owner、共用session與既有Safari驗收，列出「已經整合／存在但分離／真的缺少」的可重現證據。不得先新增dashboard、複製HTTP handler、
改研究資料／gate、碰原始dirty checkout、外部部署、登入或付費API。盤點完成後，若四項已有同一入口，先以啟動／重啟／長對話／工具成功
與失敗／3D顯示建立最小acceptance contract；若尚未整合，只准選一個阻擋統一入口的最小連線作為P4-B單一變因。P3的負／混合結論、
C1 holdout鎖定與M55/M56正式門檻不因P4產品工作改變。

P4-A已完成可重跑source inventory：Chat與truthful runtime node graph都已接在`uruha_web_ui_product.py`同一產品入口與同一turn output；
但Git tracked 3D asset=`0`，沒有VRM renderer或physical action executor。`vrm_action_policy_v34.py`只存在於research/eval路徑，
product/web/brain均未import，也沒有runtime tool schema或tool-result loop，因此Function Calling狀態為
`research_policy_only_not_product_runtime`，不能說是「既有功能」。safe worktree預期的`Style-Bert-VITS2/venv/bin/python`不存在，
system Python也沒有Gradio，故direct launch尚未ready。4項focused tests與inventory validation通過；runtime/Safari/model/production memory/
tool/physical action均0。完整驗收：`analysis/p4_a_unified_local_entry_inventory_acceptance_2026-09-20.md`。

P4-B是唯一下一步，單一變因只新增safe isolated product launcher，不改brain、prompt、研究資料、VRM或Function Calling。launcher必須
明確解析操作員指定或已知可用Python、檢查Gradio與entry，但不複製／修改原始dirty checkout；每次預設建立獨立temporary memory DB、
session DB與Web logs，只綁`127.0.0.1`，拒絕public host/share、登入與付費API。先以fixtures驗證interpreter缺失、dependency缺失、
public bind、路徑碰撞、child command/env與cleanup／preserve規則；offline contract通過才可真實啟動。真實啟動後核對health、隔離路徑、
聊天＋同輪graph與重啟；Safari是獨立可見驗收。P4-B不得把啟動成功擴張成VRM／Function Calling已整合。

P4-B已完成，保留一次真實失敗與一次sandbox修正。v1雖localhost HTTP 200與Safari可見，但Human Annotation path仍指向repo，故在0聊天、
0 repo write時判fail。v2以macOS sandbox拒絕child寫safe worktree與原始dirty checkout，synthetic deny／isolated allow通過；32項完整相鄰
suite後，以同manifest及明確reuse重開。Safari維持48個tabs且沿用既有tab，真實英文輸入要求只聽、不給建議，最終日文為
`うん。今は方法出さないから、そのまま話して。`；trace選`listening/listen_presence`、否定`solve_regulation`、surface matched，
同輪graph有69節點，user wait=`3.3884s`。1筆`1,353,575 bytes`JSONL、memory DB與adaptive model都只在isolated root；Git clean，
沉默後0可見催促。server仍在`127.0.0.1:7860`供使用者查看。完整驗收：
`analysis/p4_b_safe_isolated_product_launcher_acceptance_2026-09-20.md`。尚未驗post-chat process restart recall、voice、VRM或Function Calling。

P4-C是唯一下一步：新增一個allowlisted、read-only、零副作用的`get_runtime_status` Function Calling seam，作為未來VRM action transport的
前置，但不可接physical VRM。先凍結explicit status-request與ordinary conversation／negation／hypothetical／prompt-injection guards、唯一tool
schema、空argument、single-call、bounded result與日文surface contract；tool只能回傳不含路徑／對話／secret的brain-loaded、turn count、
memory isolation、tool capability狀態。offline fake-provider先驗證valid call、no-call、wrong tool、extra args、duplicate、malformed與executor exception
全部fail-closed，並把request→model decision→validated call→tool result→Japanese surface加入現有node graph。contract/tests/freeze/commit前
不得做real model call；real call通過與negative guards通過後才可整合product。shell、file write、external network、login、paid API與VRM execution
一律不授權。P4產品工作不改P3/M55/M56研究結論。

P4-C已完成產品真實驗收：status輪在全新session、brain仍lazy時以英文詢問，模型1 call選中唯一
`get_runtime_status({})`，tool 1 execution、side effect/memory-content read/brain initialization/retry=`0/0/0/0`；日文回覆正確顯示
brain待機、0 turn、isolated memory及read-only能力。同輪graph有request→model decision→validated call→tool result→surface五個
function nodes，共7 nodes，端到端=`6.2512s`。下一輪普通英文聊天仍回`うん。今は方法出さないから、そのまま話して。`，走原本
69-node path，P4-C新增model/tool/function-node=`0/0/0`，端到端=`2.697s`。後續4次background cycle未新增visible idle prompt。
core gate＋產品Safari真實本機model calls合計2，0 paid/external/retry。完整驗收：
`analysis/p4_c_product_function_calling_acceptance_2026-09-20.md`。這只證明一個read-only status tool，不是一般Function Calling、
state-changing action、VRM或研究優勢。

P4-D是唯一下一步。先做read-only local capability inventory，確認safe worktree與原始checkout是否已有可合法重用的VRM/GLB/GLTF asset、
renderer package、license/provenance、3D canvas入口與既有animation/action transport；原始dirty checkout只讀不改。若有合法asset與renderer，
凍結同一localhost產品入口的最小render contract；若沒有，保存缺口並只設計user-supplied `.vrm` 邊界與離線synthetic fixture，不下載或
重散布來路不明角色模型。P4-D只先做到可視3D renderer與truthful load/error node，不接未通過holdout的personality/action decision，
不執行physical state-changing action，不改P3資料／gate，也不使用登入、付費API或外部部署。

P4-D已完成並 release：同一Safari產品頁新增browser-only Local VRM Stage；初始只顯示`NEUTRAL STAGE · NOT URUHA`中性舞台。
以隔離runtime內自製4,020-byte VRM 1.0 mannequin實測，canvas真正畫出紫色T-pose且「選擇→驗證→解析→呈現」四節點全綠；
9-byte破損檔案則parse節點紅、render未完成、placeholder回復，沒有假稱顯示。valid→invalid→valid只做瀏覽器本機解析，conversation rows
維持`3→3`，server upload／asset persistent write／action／P4-D model/tool call全為0。viewer無remote URL/fetch/XHR且只允許blob/data；
這是application-level no-network evidence，不是假稱量測Safari其他48個既有分頁。status Function Calling與ordinary chat真實回歸仍通過，
端到端=`6.3426s/2.842s`；VRM始終可見。第一次raw http-literal proxy失敗亦保留，沒有改dependency或放寬runtime規則。
完整驗收：`analysis/p4_d_local_vrm_renderer_acceptance_2026-09-20.md`；release：
`research/p4_d_local_vrm_renderer_release_2026-09-20.json`。這不代表有一ノ瀬うるはasset、角色授權、動作智慧、tool-controlled avatar或研究優勢。

P4-E是唯一下一步，單一變因只驗證一個明示、speaker-qualified事實能否跨真正product process restart保存與回溯。必須在第一輪前固定
兩session腳本、唯一事實、可接受日文內容、ownership/relationship錯置反例、retrieval provenance、restart證據與失敗判準；只使用P4-B
既有isolated runtime，不讀production memory。第一session明確告知一個親屬所屬寵物名稱後停止process；以同一isolated root新PID／新session
重啟，第二session問題不得包含答案。成功需同時有正確名稱、正確speaker/owner關係、實際persisted retrieval trace、自然日文與graph可見，
且VRM local asset因browser-only不應被server記住。任何錯名、把親屬寵物說成使用者自己的、只靠prompt含答案、沒有retrieval證據或未真正
換process都算fail。結果一次保存，不因失敗改題、改prompt、手動注入memory或重跑；不把單一成功外推成長對話／open-world memory可靠。

P4-E已依事前freeze一次通過：全新隔離root第一個PID `62778`收到「Rina喜歡black coffee、使用者偏好herbal tea」，日文回覆
`記憶に残すよ`後真正退出；同一root／memory DB以新PID `62949`與新session重啟。答案不在第二題時，Safari回覆
`あんたが好みって言ってたのはハーブティー。`；唯一candidate的persisted episode ID=
`b992ec7e-cea9-4dca-81eb-e0760050b140`，來源時間早於新process，selected speaker=`user`而非Rina，圖上有
`speaker_qualified_fact_p3`，general planner model call=0。VRM stage在新page回到waiting，證明browser-local asset未被server持久化。
兩process／兩turn合計只有第一輪1次本機planner call，0 retry／tool／VRM action／paid API／production memory。完整驗收：
`analysis/p4_e_cross_restart_memory_recall_acceptance_2026-09-20.md`。這是developer-authored bounded product integration，不是open-domain、
長對話、人類記憶或研究優勢證據。

P4-F已依事前freeze一次通過：第一個process保存「偏好herbal tea」與另一筆「不再偏好herbal tea，現在偏好black tea」；舊process
真正退出後以同一isolated root／memory DB、新PID／新session重啟。答案不在recall問題時，Safari回覆
`今の好みは紅茶。前のハーブティーから更新してる。`。graph狀態=`resolved_explicit_preference_supersession`，兩個immutable episode
分別綁定historical／correction trace，current／revoked digest不同，DB rewrite=0。舊episode retrieval score=`1.4813`仍略高於更正
episode=`1.4801`，因此結果不是任選最高分。3 turns／2 processes／1 restart／2 write-turn planner calls，0 retry／fallback／paid API／
production memory；frozen gate failed=`0`。完整驗收：
`analysis/p4_f_cross_restart_preference_supersession_acceptance_2026-09-21.md`。這只證明一個bounded English tea correction case，
不等於一般信念修正、長對話、人類式記憶或研究優勢。

P4-G是唯一下一步，原因來自同一真實P4-F執行暴露的可見產品缺口：兩個寫入輪分別回`了解しました`與`了解しました。`，雖然是日文，
卻過度禮貌且制式，不符合既有casual Uruha surface要求。先把這兩個raw輸出、原planner route與P4-F memory semantics凍結為before；定位
現有full-planner輸出到visible surface之間最窄的authority。唯一允許變因是「使用者明示請系統記住偏好」與「使用者明示更正同一偏好」
兩類 acknowledgement 的自然、簡短、casual日文表達；不得改general persona prompt、模型、memory ranking、episode寫入、supersession／
recall adapter、P3研究資料或baseline。

成功需先用offline fixtures證明中／英／日三語的明示記憶與更正輸入都不再顯示`了解しました`系模板，仍只輸出自然日文、保留うるは公開
人格邊界，且普通聊天、拒絕、求助、身份、回溯與P4-F current／revoked均不退化。必須有negative guards，避免把普通「了解嗎？」、第三人稱
偏好、假設句或非偏好更正誤套成確認。P4-F同一真實案例不得重跑；離線contract、tests、freeze及commit完成後，另用未曝光的isolated新案例
做一次真實runtime／Safari驗收，並核對episode write、graph、語言與0 retry。這一步只改善可見surface，不得宣稱研究優勢或更深理解。

P4-G已完成但正式gate為`fail`，且負結果不可重跑／追分。全新isolated root的中文寫入輪正確辨識`zh/write`，但模型回
`了解。茉莉花茶が今の飲み物だ`，因不在frozen formal-ack allowlist，post-guard authority沒有啟動；等待`25.2079s`亦超過20秒。
日文更正輪的P4-G classifier正確辨識`ja/correction`，但既有rule route誤判`ask_like_me`，顯示與偏好更正無關的
`はいはい、全くじゃないとは言わない。そこ聞いて安心したいだけだろ。`。兩輪graph node與不同episode均存在、模型call=`1/0`、
retry/fallback=`0/0`，但frozen gate共10項surface失敗。完整負結果：
`analysis/p4_g_multilingual_preference_acknowledgement_acceptance_2026-09-21.md`。

P4-H是唯一下一步，單一變因從失敗診斷直接收斂為「明示偏好記憶act在general planner與舊intent碰撞之前取得deterministic plan／surface
authority」。先綁定P4-G immutable result，沿用已通過的中／英／日classifier，不擴allowlist、不改general persona prompt；對write與
correction各建立一個bounded rule plan，明確intent、dialogue act、core Japanese與0新增推測，讓寫入行為不需要任意模型措辭且不會被
`ask_like_me`先攔走。最終surface須由同一typed act contract接管，而不是只在reply剛好等於制式敬語時接管。

P4-H不可改episode/schema、memory ranking、P4-F parser／localization／recall、研究資料或baseline；「記住訂正內容」只代表原episodic
turn確實保存，不宣稱所有語言都已形成typed current preference。需把P4-G trace中未啟動authority卻顯示
`final_visible_surface_matches_contract=true`的誤導欄位修正。先以六個正例及普通聊天／第三人稱／假設／引文／安全路由做offline regression，
commit後另凍結全新案例才可真實執行；P4-G茉莉花茶／冰咖啡案例不得重跑。成功只代表bounded product act與surface，不代表人類理解或研究優勢。

P4-H已完成且 frozen product gate=`pass`。全新 English write／Chinese correction 在同一新隔離 process 各執行一次，實際顯示
`ん、その好みは覚えとく。`與`ん、訂正の内容はそのまま覚えとく。`；兩輪皆為 deterministic rule plan、正確
`explicit_preference_memory_write/correction` intent、graph `select` node、不同 episode、planner model call=`0`、retry/fallback=`0`，
使用者等待`2.1027s／11.2373s`，0 failed gates。P4-G舊案例未重跑。完整證據：
`analysis/p4_h_multilingual_preference_memory_act_acceptance_2026-09-21.md`。

同一結果也直接暴露 P4-I 的唯一問題：第一輪 English `sparkling water` 寫入後 typed profile `likes=[]`；第二輪 Chinese 更正後
profile 為`likes=[]`、`dislikes=[氣泡水]`，新 current preference `熱可可`沒有成為 typed like。兩輪 episode 都正確保留，因此不能再改
P4-H planner／surface，也不能說資料完全沒記住；缺口是 current preference 內容從多語 observable utterance 到 typed active state／superseded
history 的 projection 不完整。

P4-I先只讀定位既有 profile extraction、episode write 與 P4-F typed supersession 路徑，再綁定 P4-H immutable result，凍結 English／Chinese／
Japanese write與correction的 typed contract。current preference 與 superseded history必須分開，來源、時間、語言與更正鏈可查；不得只把舊項目
粗暴加入dislikes、不得抹掉原episode、不得把偏好內容當心理推測。先做offline parser／writeback／negative guard與受影響回歸，commit後才可另立
全新cross-restart real case；P4-H氣泡水／熱可可與P4-G舊案例都不得重跑。這一步仍不碰研究baseline、production memory、外部部署或人類優勢claim。

P4-I已依事前freeze一次通過：第一個process以English寫入scope=`drink`的`oolong tea` active typed positive，真正退出後，第二個process
以相同isolated root／memory DB及新PID／新session啟動，送出Chinese correction為`barley tea`。最終P4-I validity resolver得到一筆
active新positive、一筆historical舊positive及一筆active明示negative；舊record沒有刪除或改寫，兩個positive共用相同scope predicate。
Safari兩輪顯示自然日文與P4-H `select`／P4-I `memory` nodes；2 process／2 turn／0 retry／0 planner model call，等待
`2.3411s／16.2815s`，frozen gate failed=`0`。完整驗收：
`analysis/p4_i_cross_restart_current_preference_acceptance_2026-09-21.md`。

P4-J只處理仍明確未授權的read path：目前P4-I profile shadow仍是`answer_use_authorized=false`、`affects_working_memory=false`，所以typed state
持久化成功不等於產品會用它回答「我現在喜歡什麼？」。先凍結一條read-only adapter：僅對明示第一人稱、current-preference、exact supported
scope的問題讀取active P4-I current record；scope缺失／不支援／多active候選必須fail closed，historical與negative不能當current answer。
非selected問題完全保留P4-F episode recall。回覆仍須自然日文，graph要顯示typed source id與active-only決策；回答本身不得寫profile。
P4-I oolong／barley案例不得重跑。contract／tests／freeze／commit前不得送新real turn，也不得把這一步外推成一般記憶、人評或研究優勢。

P4-J 已依事前 freeze 做完唯一 cross-restart 案例並判定 `fail`，不得重跑。第一個 process 以 English 寫入
`drink=rooibos tea`，active typed memory id=`b1ae941d-5120-47c2-81fb-77194545ce78`；第二個 process 重用同一隔離 DB，
Chinese answer-absent query 成功把同一 id 讀進 `typed_current_preference_recall_authority_p4` plan，且 planned core 正確為
`今の飲み物の好みはルイボスティー。前のじゃなくて、今の方ね。`。但 Safari／JSONL 最終顯示 episode timestamp 回覆
`前に: 2026-09-21 13:15:5って言ってたろ。そこは忘れてない。`，graph 也缺 P4-J node。profile 仍為1筆且 hash 前後一致；
2 process／2 turn／0 retry／0 planner model call，frozen gate 7項失敗。完整負結果：
`analysis/p4_j_cross_restart_typed_recall_acceptance_2026-09-21.md`。

P4-K 只修這個已定位的 propagation seam：planner normalization 會保留 P4-J intent/core，卻丟掉自訂 contract，導致 visible guard 只查
final logic 時無法接管 surface，materializer 也沒有 payload 可畫。允許從當輪 `memory_data` 恢復已選中、已授權的 P4-J contract，先複製到
final logic 再套用 exact surface authority，最後產生 select-stage graph node。必須新增模擬 normalized logic 缺少自訂欄位的回歸；safety route
仍不得被覆寫，非selected query、P4-F、typed storage、active resolver、localization、expected surface與P4-J舊freeze一律不改。

先完成implementation與受影響回歸；在另立新acceptance freeze前真實產品輪次=`0`。之後只可用未執行的新值／新語言案例，P4-J rooibos、
P4-I oolong/barley、P4-H sparkling-water/hot-cocoa及P4-G案例都不得重跑。成功也只代表bounded跨重啟typed recall交付，不是一般記憶、
長對話、人評、強LLM優勢或人類方程式。

## 工作環境

- 安全 worktree：`/Users/jerrychang/Desktop/uruharemake2_worktrees/persona-data-provenance`。
- 分支：`codex/v2-15-pragmatic-research-showcase`，PR #435。查實際 HEAD，不碰原始 dirty checkout。
- Python：產品測試用 `.venv/product_checks/bin/python`；純標準庫 verifier 可用系統 python3。
  不全域安裝依賴。Gradio／Torch／brain 的 import 留在 isolated worker，不放純資料 module 的頂層。
- 長期目標檔：`LONG_TERM_GOAL.md`。2026-09-09 Goal 工具讀到 usageLimited；文件更新不等於 app 已恢復。
  不清除／假完成／改內部 DB 來換 Goal。使用者手動回合仍可執行已授權工作。
- 本機 Safari 已完成P4-B、P4-C與P4-D真實驗收；目前沿用1個Uruha頁面、沒有關閉使用者tab。P3-A不依賴瀏覽器。

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
