# P4 profile owner／引文極性准入：設計先行

狀態：產品缺陷的事前介入設計，非正式 holdout、模型品質或真人驗證。
本項只處理**新 `subject=user` profile 寫入的 owner/quote/polarity 正確性**。
原始 episode 及上一項 `凪紗／ルイボス茶` strict `0/1` 結果不得改。

## Before 與最早失真

隔離 Safari 十輪原樣結果在
`analysis/p4_bounded_source_v2_fresh_product_probe_result_2026-10-01.md`：
T1 朋友偏好和 T3 作文引文／本人否認各被寫成一筆 active `subject=user`
favorite，跨 process 重啟仍在隔離 DB。純離線現行 `MemoryManager._extract_profile_facts`
對兩句分別產生 `('favorite', '友達の凪紗はルイボス茶')`、
`('favorite', '「私は炭酸水')`，`classify_profile_assertion_scope` 均錯判
`unmarked_japanese_self_assertion`。`save_episode` 在 profile 寫入之前；
P4-I 對兩句未 selected、委回舊 writer；`compile_profile_memory_record`
將任何舊 tuple 標成 user/active。另有同型可反駁反例：
`紅茶が一番好きじゃない。` 被現行抽成正向 favorite；朋友＋本人雙句
會同時抽出本人與朋友，甚至跨句吞成單一值。

## 單一可歸因變因與邊界

增加**產品版、逐候選來源片段綁定的本人陳述准入**，在 session 與
Chroma mutation 前只准來源片段可支持的本人 profile fact。它是 profile
writer 的一個事務邊界，不改記憶檢索、來源問答、回覆 prompt、模型、
評分器或既有 episode。適用現行產品 P4-I selected 與 legacy fallback：

1. 選中的 P4-I typed write／correction 須保留既有顯式本人 cue 與正負值
   歷史，不因本 gate 粗暴封鎖；若來源含未解的引文／第三人歸屬則
   fail closed，不能退回 legacy 補寫。
2. legacy 的抽取候選須綁到有界原句子句，逐候選判 owner、報述／引文
   範圍及偏好謂詞極性。朋友／親人或無法唯一確認本人者、引文內陳述、
   正向 `好き` 後接否定者不寫 `subject=user`。`不是我的偏好` 不可
   自動反轉成 dislike；明確本人 dislike／correction 繼續依既有路徑。
3. 同輪第三者＋本人分句不能整輪丟棄；僅本人候選可寫。候選若跨越
   分句、引文界線或無法對到原樣 evidence span，零寫入而非猜 owner。
   子句數及文字長度有上限；超出範圍 fail closed、保留 episode。
4. graph 要新增本輪 profile admission 決策／准入及拒絕數的真實節點，
   僅存 hash、類別與計數，不複製私人原句。它不能假稱持久 profile
   已授權回答；原 `profile_state_shadow.answer_use_authorized=false` 不改。

允許新增 additive `uruha_profile_owner_admission_p4.py`、
`uruha_web_ui_product_p4_profile_owner.py`、相應隔離 launcher／聚焦測試、
本 plan、後續新前瞻 case／freeze、結果、`CURRENT_TASK.md`。只在現行產品
入口安裝；**不得修改**已凍結的 v68 guard／brain、P4-I、過去的 P4
source overlay、舊 dataset／raw／score、正式 DB、原始 dirty checkout
及無關 `output/graduate_application_report/`。若實作發現必須修改上述
核心或 schema，先停在設計審查，不自行擴張。

## 開發測試與產品驗收（先定判準，後建新案例）

聚焦 synthetic/dev 矩陣先於實作固定：

- 失敗應被拒：原 T1/T3（只作已曝光回歸）、`友人の<名前>は<飲料>が一番好き`
  無「言った」版、`私の友達は...`、內嵌作文引文後明示非本人、
  正向 `好き` 後接 `じゃない／ではない`、問句／報述。上述 profile
  add count 必須 0，session 不變；不刪 episode、不自動寫 dislike。
- 必須保留：日文省略主詞 `海が好き`、明確 `私の一番好きな飲み物は...`、
  英中日直接本人陳述、既有 name、明確本人 dislike、P4-I 三語 scoped
  write／correction 的精確值、歷史與 active state。
- 混合兩個順序：朋友句＋本人句、本人句＋朋友句；及引文句＋獨立本人句，
  必須只寫本人 exact value（非人物前綴／跨句污染）。
- 聚焦層核對 extractor 候選、hash/owner/reason 的 graph audit、
  session favorites、真暫存 Chroma 的 metadata 與重啟 readback；
  相鄰至少跑 v68、日文／v69、P4-I、profile shadow、來源問答／圖表測試。

聚焦與相鄰通過後，另選與以上 actor/value 不同、repo 原樣 0-hit 的
**新前瞻隔離產品案例**；exact inputs／source-only gold／成本事前提交 hash，
然後只跑一次新 Safari session、T5 後真重啟，0 回答重試。產品 strict：
所有負句 profile 零新增但 episode 仍持久；兩種順序混合句只留本人；
直接本人與 P4-I typed 正向仍留正確值及 active/history；重啟後隔離 DB
一致；若問舊朋友來源，仍可用原 episode ID 說出是使用者轉述朋友，
圖上的 admission／memory writeback／utterance 同輪與最終日文一致。
每輪等待目標 `≤20s` 分開報，不能以少寫資料抵語義品質。
全產品 tokens/calls 若未暴露記 unavailable；不得把 0 extra overlay model
calls 當全系統 0。規格、資料凍結後不改題、不重跑曝光案例追分。

最先跑純函式負／正例與暫存 DB，後跑相鄰：
`PYTHONDONTWRITEBYTECODE=1 .venv/product_checks/bin/python -m pytest -q
-p no:cacheprovider test_p4_profile_owner_admission.py
test_profile_assertion_boundary_v68_integration.py
test_profile_assertion_multilingual_boundary_regression.py
test_profile_state_shadow_v69_integration.py
test_p4_i_multilingual_current_preference.py
test_p4_past_statement_source_answer.py
test_p4_bounded_source_delivery_v2.py`。
若重現未解、混合句仍寫錯、既有本人寫入退化或真 Safari 任一 strict 失敗，
保留負結果；至多兩個有根據批次，仍失敗 `REVIEW_REQUIRED`。
