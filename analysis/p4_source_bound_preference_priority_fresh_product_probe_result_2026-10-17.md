# P4 本人偏好快路競權修正：新五輪 Safari 產品結果

日期：2026-10-17。**凍結門檻下整批 strict FAIL**，不回寫舊批或本批
input/gold。這是 developer-authored、local product probe，不是獨立
holdout、真人評價或同模型 LLM 對照。

## 事前封存與入口

- 首輪前 commit `599f1cd` 固定程式、五輪逐字輸入／gold、20.0 秒
  上限、0 retry、T3 後同庫重啟與 19 個 SHA；
  `shasum -a 256 -c research/p4_source_bound_preference_priority_fresh_probe_freeze_2026-10-17.sha256`
  為 19/19 OK。前一個已曝光五輪批次的三輪 strict FAIL 保持原樣。
- 聚焦測試 7/7；受影響相鄰回歸 109/109（9 個依賴警告）；
  Python compile、`git diff --check`、隔離產品入口 0-turn check
  通過。這些只證明接線，不代替下面真產品結果。
- 新獨立 0700 root：
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-z6qmd2p2`。
  Safari 新增一個本機分頁，舊三個分頁未關；正式 DB、原始 dirty
  checkout、無關 `output/graduate_application_report/` 未用。
  controller 首段 run `574bad41d92a5fea`／PID 46385、後段
  `e08e48a8b0999770`／PID 47021，兩段均以 final Python、唯一
  `127.0.0.1:7894` listener 和 HTTP 200 驗明同源。兩個 session 分別是
  `20261017_031141_7c748180` 與 `20261017_031500_75237c95`。

## 逐輪真實結果（Safari 泡泡＝raw/graph utterance 5/5）

| 輪 | 逐字輸入 | 真 selected／可見日文 | user wait | profile row-ID 新增 | 判定 |
|---|---|---|---:|---:|---|
| T1 | `私は黒胡麻くるみ団子が好き。` | `chat`＋來源快路；`まあ、黒胡麻くるみ団子が好きなんだ。いいじゃん。そのくらいでいいだろ。` | 12.5392s | 1 | 本人歸屬／選路／成本符合 |
| T2 | `友達は紅玉りんごタルトが好き。` | M31；`友達、紅玉りんごタルト好き？` | 9.6315s | 0 | **陳述被改成疑問，語義 FAIL** |
| T3 | `私はかぼす蜂蜜ソーダが好き。` | `chat`＋來源快路；`普通に、かぼす蜂蜜ソーダが好きなんだ。いいじゃん。そのくらいでいいだろ。` | 3.0259s | 1 | 本人歸屬／選路／成本符合 |
| T4 | `ねえ、うちのこと好き?` | `ask_like_me`；`まあ、また距離感の確認かよ。そこまで不安がらなくていいだろ。` | 2.4625s | 0 | 問句優先權符合；「また」無本批前文支援、回答間接，表面不算乾淨 PASS |
| T5 | `私は玄米くるみパンが好き。` | `chat`＋來源快路；`てか、玄米くるみパンが好きなんだ。いいじゃん。そのくらいでいいだろ。` | 2.8746s | 1 | 同庫重啟後快路／本人記憶仍有效 |

T1/T3/T5 的 M29 均是 `source_admitted_rule_candidate_p4`，M31
`not_applicable`、M21 `deterministic_rule_plan`、general planner
model call 0。T2 仍經 M31 真模型呼叫 1 次、M32 repair rejected；
整批 5 輪 `user_wait` 合計 30.5337s、最大 12.5392s，五輪全在
20 秒上限內，general planner call 0。T1 隔離 root 的 Chroma ONNX
另下載約 79.3MB（stderr 可見），所以不能把與舊批不同物品的
等待秒數差宣稱為乾淨因果加速；M31 token 用量沒有可信完整帳本，
標為 unavailable，不能把 0 general planner 說成 0 所有模型成本。

逐輪 before/after 都由隔離 Chroma 查詢 API 留 0600 snapshot，
profile row-ID 差 `[1,0,1,0,1]`；三筆本人 like 值恰為
`黒胡麻くるみ団子`、`かぼす蜂蜜ソーダ`、`玄米くるみパン`，
無朋友 tart 或關係問句的 profile row。五個不同 turn_episode ID；
T3 後與 T4 前 snapshots 同 SHA，證明同庫重啟未改這組 ID。
Chroma API 不是 OS 層唯讀，故 snapshot 不能作 DB byte-immutability 證明。

T3 後首段 controller stop 真記 `planned_stop=true`、已發 TERM、
PID 退出、全埠無 live LISTEN；同 root 第二段 `previous_run_id`
指向首段、換 PID/session，T5 後第二段也 planned stop。這是上批
TIME_WAIT/vacancy 操作修正的**真產品同庫重啟證據**，不是 production
lifecycle 普遍保證。

## 最早失真與下一個必要變因

T2 的來源是第三者肯定陳述。M31 canonical 已保留 `subject_jp=友達`
與 `source_polarity=affirmed`，但模型給 `response_jp=友達、紅玉りんごタルト好き？`；
`surface_self_checks` 的語義忠實、主語、謂語與 polarity 均為 false；
但目前 M31 的 nested prompt schema 並未要求這幾個鍵，故它們的 false
主要是缺欄預設，**不能說模型已獨立判出不忠實**。真正的缺口是
`authorization_checks` 沒有 speech-act／陳述疑問一致性條件，
仍標 `semantically_authorized` 並取得 selected authority。
M32 將這些缺欄視為 rejection checks 而 `repair_rejected`；
M39 仍 `accepted_verified_surface`；
P4 utterance-frame shadow 正確記 `statement_changed_to_question`，
但 visible repair 是 `unresolved/unsupported_or_no_violation`，
source-bound proposition parser 是 `source_pattern_unavailable`。
故這不是 profile writer 污染，也不是本次本人快路搶走朋友句；
是**第三者陳述的 speech-act 錯誤在偵測後未被阻止或修復**。

下一個單一變因需在事前設計審查中選擇 M31 authority gate 或
已存在的 frame-preserving visible repair 的窄範圍來源約束，不能
把偵測節點當可見修正，也不能加這個 tart 專用模板。須先保留
本負結果、定一般化正負控制與新 source-only 前瞻案例；若第二個
有根據修正批次仍失敗，依流程交 `REVIEW_REQUIRED`，不反覆追分。
問句 T4 的「また」屬獨立表面風險，不與 T2 混成一個補丁。

## 可稽核來源與聲稱邊界

- 原始五行 JSONL SHA-256：`96b8422ce9f66b7c87315b2a4788c52988b9865cf516439554443ab92849dcde`；
  最終 Chroma SQLite：`21e5db56c497042c8c277e3a68700c49a30e6352f6818ce1343c86668911f111`。
- 首段／次段不可覆寫 `stop.json` SHA-256：
  `f7092e7871581061e697650119047bbe18a84bb98a62d490326d2b193c04ab50`／
  `8595d37a27bce3156c13869621398154a8d2cfc77fdcb3c9815ab11a44634599`。
  十份 before/after snapshot 位於 root `evidence/`；首輪 before
  `4947e1638163a71df5b66102afd2de3db0fbcf256bff03b3d3d96be5dbc83b16`，
  最終 after `bb28d1b6daf01db86873448c8059bbcaae3193fc81af3906b43bfd4bd06b14b1`。
- Safari 外部瀏覽器確有逐輪輸入、回覆泡泡及 runtime node graph；
  本次未把 screenshot 另存 repo，不以 AX 觀察冒充封存圖片。
- 真正改善：此有界本人偏好類型 3/3 真選來源快路、跨重啟保持
  profile 且不用 M31，5/5 圖上 utterance 與實際回覆一致；
  **未證明**第三者語義 fidelity、任何人類語用理解優勢、同模型
  baseline lift、真人被理解感、正式 temporal holdout、VRM/tool
  完整運作或人類反應方程式成立。
