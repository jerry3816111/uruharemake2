# P4 f8：同起點真模型配對的負結果（planner boundary）

日期：2026-10-24。f8 事前設計／題本在 `542d4b9` 凍結；產品變因與零模型測試在 `fdea038`、一次性隔離執行器在 `ee91809` 先推 PR #435。此輪只執行凍結的「第一次自己拍夜星」M21 配對，各臂一次、**0 retry**；不是完整 Web／Safari、強 LLM 對照或正式 holdout。f7d 香草苗真 Safari strict FAIL 保留，不重判。

## 真實輸出與事前 gold

凍結 User：`初めて自分で夜の星を撮った。今は一言だけ励まして。`。事前要求核心要自然簡短地承接「第一次、自己、拍下夜星」並給低壓鼓勵；泛用稱讚或只說見到夜空都 FAIL。

| 條件 | 選定原始 `core_message_jp` | 三原始候選中 f7 narrow grounded | 事前完整 gold | 解讀 |
|---|---|---:|---|---|
| f8 off | `頑張ったね！` | 0/3 | **FAIL** | 只鼓勵，沒有首次／本人／拍攝／夜星。另有一候選談夜空美麗，仍把完成的拍攝換成發現美麗。 |
| f8 on | `頑張ったね！` | 0/3 | **FAIL** | 來源約束已送入真 request，但三候選皆未保留事件；選定核心與 off 同字。 |

兩臂的 M21 `full_planner/completed_within_budget`、compact `completed=true/candidate_count=3`、f7 eligible、0 fallback、0 planner revision，選定原始 core／最終 planner core 同 SHA `2a263a55...98738`，f7 均為 `no_grounded_candidate`、index 0→0。f8 on receipt 是 `prompt_injected=true`；off 無 receipt。初始 User＋memory＋psyche＋handoff 的序列化 SHA 同為 `552fc809...6eccda`，on 去掉 f8 suffix 後的 Python request-argument SHA 與 off 完全相同 `741ca5fe...99553f`。這證明本次單變因確實到達 provider 請求，不證明模型服從它；比較的是 Python 參數，不是 HTTP wire bytes。兩臂生成順序 off→on，無固定 sampling seed；**單一配對不足以量化一般化因果效果**。runner 無 product `persona_policy_provider` 或 RightBrain，因此上述是 planner core，不是實際使用者可見 utterance。

## 成本、原件與邊界

同一 `qwen2.5:7b` digest `845dbda0...a697e`，同 temperature 0.1、compact JSON schema、256 output token cap、同 20 秒 planner cap。off **1029 prompt＋82 completion＝1111 provider tokens、8.965s**；on **1186＋79＝1265 tokens、3.328s**。on 比 off 多 **154 tokens**（prompt +157、completion −3），本配對沒有品質收益；延遲不宜由此歸因為 f8 加速，順序／熱機／抽樣皆可能影響。每臂低於事前 ≤2000 tokens／≤20s，合計 2 completed generations／2376 provider tokens；無 DB、背景 tick、episode、Safari Send。這不是完整產品成本或 VRM／工具測試。

獨立只讀核對亦見 on 的 provider usage 標有 **997 cached prompt tokens**；因此 3.328s 比 8.965s 短更不能解讀為 f8 的速度效果。私有 `report.json` 是執行器在尚未人工判讀前寫的 `quality_pending` 原始原件，不覆寫；本頁 `off_fail_on_fail` 是事後按**事前 gold** 對私有原始核心所作的判定。私有 JSON 序列化有 key sort，磁碟檔可核欄位值／去 suffix 對等，原始 Python 參數順序 byte parity 是執行時守門及其 hash 所記，不假稱可從磁碟重建 HTTP wire bytes。

原始 request／三候選及選定 core 僅存新 0700 私有 `uruha-f8-paired-r3b9i07a`，五個 JSON 原件均 0600，不放 repository。`off_raw_response.json` SHA-256 `f9b6c1297fecc635968360716ebeb0d587ee4e003476917c3c81eaede76954d7`；`on_raw_response.json` `1885ec941b5ec7d1c0557a4e252ebae03bad888e0f95c29c41e5370274c5a34e`；`off_selected_private.json` `ea3d8e59447318b622cb161d4c8d386081341b8eff9ce5c1babbc95f894941fa`；`on_selected_private.json` `9399ed9823be859b4a2916e8a670082b1e30e3985d4e7b8b0dcd288ce7573d2e`；`report.json` `930393e11942d796a9d2cbb403c93c3a3e4794aa669ea37230d6942f6c03ad43`。無正式 DB 寫入，未碰原始 dirty checkout 或無關 output。

## 判定與下一步

依事前四分支，此次是 **off fail / on fail**，不是「on 改善」；即使 f8 on prompt 確實進入模型，原始三候選仍全欠來源事件，故目前的首個瓶頸仍是**生成核心未承接可觀察事件**。候選排序 f7 無 grounded 可選，final core 也未由後段修壞。這不能證明所有 prompt conditioning 無效，只能反駁「本次短約束已足以修好這個作者診斷題」。依凍結入場條件，**山地圖題不得送 Safari**；不能換題、調 prompt 或重跑夜星追分。此前 f7 排序與本 f8 候選 prompt 兩個有證據的前瞻修正均未達真品質 gate，標記此來源事件子項 `REVIEW_REQUIRED`，以本最小反例檢討候選形成／嚴格棄權與 final surface 接線的單一下一變因及成本，再凍結新 source-disjoint 案例。整個 Goal、P4、同模型強 LLM 比較、人評與 temporal holdout 都未完成。
