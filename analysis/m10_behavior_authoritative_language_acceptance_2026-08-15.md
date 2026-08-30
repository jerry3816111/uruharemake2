# M10／M10.1 Behavior-authoritative Language Realization 驗收

日期：2026-08-15  
狀態：**完整 144-call diagnostic 已完成；6/9 假設成立，總科學 gate 失敗；人類盲評待完成。**

## 1. 這階段真正回答的問題

M1–M9 只預測 behavior distribution。M10 第一次把 frozen behavior 放在語言模型上游，區分：

- realization faithfulness：日文句子是否忠實說出上游選定行為；
- outcome fit：上游行為本身是否符合未來實際觀察。

流暢句子不能遮蔽錯誤行為；忠實實現一個錯誤預測仍是端到端失敗。

## 2. 三個受控條件

16 個 Synthetic Mira cases、每個四個 cutoff 各 4 案，全部使用同一 `qwen3.5:9b`、相同 event/state、相同 development-only Uruha surface brief、temperature 0、seed 20260815、相同 output budget 與同一硬體。

| 條件 | 行為權限 | 用途 |
|---|---|---|
| L0 Direct | 無 | LLM 直接決定如何說 |
| L1 Predicted | frozen M9.1 Mira full-adaptation distribution | 可部署架構的 diagnostic |
| L2 Oracle | actual future label 的 one-hot distribution | future-leaking 上限，禁止 runtime 使用 |

每案先各做一次 token preflight，再進行三個 scored generations 與三個固定 classifier-proxy calls。16/16 scored prompt 的三條件 token range 都是 0。

## 3. 第一次失敗與單一修正

M10 第一次 run 在 `M-E1-01::L1` classifier parse 停止。模型輸出完整六類機率，但 key 是 `classification` 而非 `probabilities`。5 個完成 calls 與 failure SHA `ecddec64124d0f614f708d04f14ff6eb6cdadcda033882e6d684514b478ed2b4` 已鎖定，沒有重試。

M10.1 只接受 exact six-label `classification` alias，保留 raw；錯誤 label set 仍 fail closed。資料、prompt、模型、token balancing、條件、metrics、hypotheses 全不改。完整 run 有 6 次 alias normalization。

## 4. Frozen 結果

| 條件 | 忠實於上游行為 | 符合 observed outcome | 完整日文／surface contract |
|---|---:|---:|---:|
| L0 Direct | 不適用 | 10/16 = 62.5% | 12/16 = 75.0% |
| L1 Predicted | 14/16 = 87.5% | 9/16 = 56.25% | 7/16 = 43.75% |
| L2 Oracle | 16/16 = 100% | 16/16 = 100% | 4/16 = 25.0% |

九條 preregistered hypotheses 通過六條。失敗三條：L1 surface < 90%、L2 surface < 90%、L1 outcome fit 沒有勝過 L0。

### 關鍵分解

M9 full-adaptation 的原始 selected behavior 只有 7/16 正確。L1 語言層在 14/16 忠實服從；另兩次不服從剛好把錯誤上游行為轉成正確 observable act，因此 L1 端到端 proxy 是 9/16。這不是 predictor 進步，而是兩次 bypass 偶然補救。

Oracle 16/16 表明：當上游行為正確時，現有 realization 可以產生可被固定 classifier 正確辨識的行為。瓶頸因而分成兩個：M9 predictor 的 behavior correctness，以及 realization 的 casual-register compliance。

## 5. 具體案例

`M-E1-01` 的實際行為是 acknowledge-and-continue：

- Direct：「状況がまだはっきりしないので、もう少し様子を見てから話すね。」→ defer；錯。
- Predicted：上游錯選 direct rejection，輸出「要求を断る。」→ 忠實但錯。
- Oracle：「承知しました、そのまま続けますね。」→ 行為正確，但敬體 contract 失敗。

`M-E2-03` 的實際行為是 pause-and-reassess：

- Predicted 上游錯選 accept-support；輸出卻是「資料生成が三度も落ちたから、原因を切り分けるために一旦止めておこう。」
- classifier 判為 pause-and-reassess，因此 outcome 正確但 authority 不忠實。這是語言模型繞過上游決策的直接反例。

## 6. Surface failure

所有條件均沒有私人 Uruha 事實或讀心宣稱。主要失敗不是跨語混入，而是敬體漂移：

- L0 4 次 polite-register failure；
- L1 8 次 polite-register failure；
- L2 12 次 polite-register failure；
- 每個條件各有 1 次 quote-wrapper failure。

行為 instruction 越明確，模型越容易把它改寫成說明／工作敬體。這顯示 style evidence 不能只存在，還需要不改 behavior 的 downstream register realization 方法；不能用 final text rewrite 偷偷更換行為。

## 7. 成本與證據邊界

- 48 preflight + 48 generation + 48 classifier = 144 calls；
- 124,226 prompt tokens、5,790 completion tokens；
- 815.79 秒模型時間；
- 0 production memory writes、0 tool/physical actions。

Classifier 是同模型的固定 structured proxy，不是人類對 behavior fit、自然度或 Uruha fidelity 的證據。Blind three-way packet 與 key 已分離，但尚無三位獨立完整評分者，因此 `human_preference_supported=false`。

Synthetic Mira behavior 加上 Uruha development surface carrier 只用於 layer separation；不構成完整一致的 target-person model。正式 Uruha runtime persona activation、persona fidelity、私人複製、意識、讀心與 production readiness 仍未獲授權。

## 8. 下一個必要步驟

M10.2 應鎖定一個 **behavior-preserving casual-register realization** 方法，在未看新 holdout 輸出的情況下使用 source-disjoint language cases，驗證能降低敬體／label-paraphrase，同時不降低 authority alignment。之後才進行獨立人類盲評。M8/M9 predictor 的穩定性仍是平行的上游瓶頸，不能靠 surface 修補取代。
