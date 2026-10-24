# P3-B73 prospective response-target redesign plan

日期：2026-09-20

## 問題與單一變因

B72證實舊量尺把連續直播字幕前三句以少數標點marker映射成單一label；第三來源4/4落入default，五種metrics方向不一致。
B73只改「未來回應Y要怎麼定義與可靠標註」，不改模型、prompt、memory、persona、來源、prediction或已曝光結果。

本階段把M54的`P(Y[t+1] | X,H,M,S,R,N,C,theta,U)`具體化成有stimulus→response邊界的多層target：

1. **直接可觀察層**：實際response move，可多標籤；
2. **可反駁語用層**：主要interaction goal、stance、literal/pragmatic relation，保留alternative與ambiguous；
3. **表達層**：實際回應文字另封存，只作後續表達／人工偏好，不以字面重疊代替理解；
4. **主觀層**：felt understanding與過度解讀必須另做盲化真人評價，不能由automatic proxy或同一LLM自評取代。

## 參考方法與採用邊界

- Sravanthi et al., **PUB** (Findings ACL 2024), DOI `10.18653/v1/2024.findings-acl.719`：採用implicature、
  presupposition、reference、deixis作coverage buckets；不把MCQA accuracy當真實人物回應預測。
- Arai & Ren, **DRInQ** (ACL 2026), DOI `10.18653/v1/2026.acl-long.1597`：採用固定surface form、系統性改變context的
  controlled context pair，分離字面與上下文效果。
- Li et al., **PaCE** (Findings ACL 2026), DOI `10.18653/v1/2026.findings-acl.959`：採用literal/pragmatic context-flip與
  over-interpretation control；系統不能只會增加推論量。
- Lombardi & Lenci, **Conversational Implicatures through the Lens of LLMs** (LREC 2026),
  DOI `10.63317/5dqc2g73d3do`：保留人類解讀變異、alternatives與ambiguous，不假設每題必有唯一心理真值。
- Eo & Lim, **Unveiling the Limits of Large Language Models in Inferring Pragmatic Meaning from Non-Verbal Responses**
  (ACL 2026), DOI `10.18653/v1/2026.acl-long.2101`：聲學／非語言證據是獨立modality；缺少時必須unavailable。

## 前瞻資料單位

每個episode必須先凍結唯一的pre-cutoff stimulus與後續target response邊界。prediction view只含stimulus；coder view可在prediction
封存後看target response，但看不到baseline/system身份、prediction或分數。連續直播中若無法辨認刺激來源、speaker turn或response
boundary，該episode標`unusable_boundary`，不可用固定秒數假裝是一問一答。

新source正式取樣至少包含：

- controlled context pairs：相同surface form、不同context；
- context-flip controls：一側需要語用推論，另一側應保持字面；
- 對話／可歸因刺激，而非只有未對齊的遊戲獨白；
- text-only與acoustic-available分層；B73不會為了湊數製造聲學摘要。

## 標註與可靠度

兩位不同且同意參與的真人各自完成同一個18-episode pilot；互不可見、看不到condition。primary fields為response-move set、
interaction goal、stance、literal/pragmatic relation。沿用既有V7 nominal Krippendorff alpha計算，四個primary alpha都必須
`>=0.667`；每個field必須有至少兩種observed categories，constant agreement不能冒充可靠。response move逐label alpha另報。

失敗時保留兩份原ledger，只能修codebook後另建前瞻pilot；不得調到舊答案通過。Codex、LLM、synthetic fixture或同一人重複提交
不能冒充兩位真人。Synthetic只驗證schema、blinding與計算。

## 後續公平比較

可靠度通過後才能取新來源與封存prediction。相同基礎模型、可見資料、persona條件、硬體、生成參數及token ceiling下比較：

- 多標籤moves：macro Brier（primary）與per-label calibration；
- goal／stance／relation：log loss、Brier、top-1；
- context pair：context-sensitive improvement與literal-control over-interpretation rate必須同時報；
- 自然回覆：另做盲化pairwise felt-understanding、appropriateness與unsupported-inference評價。

所有metrics都報，不用row winner取代原始分數。若system在語用組變好但literal control過度解讀惡化，不算無條件優勢。

## B73完成與不完成

B73完成條件是：contract、prediction/coder view隔離、ledger validator、可靠度計算與synthetic pass/fail fixtures可重現，且0新來源／
future／model／human label。這只代表新量尺「可收資料」，不是可靠度已通過、不是system優勢、也不是人類方程式成立。
