# 統一評測摘要

- 生成時間：`2026-04-12T14:13:55`
- 說明：本摘要優先使用各獨立報告作為最新真值，避免巢狀總表混入舊快照。

## 現在做得好的地方
- 高低軌路由、工作記憶預算、多候選 Bayesian rerank 都已落地，控制器骨幹穩定。
- 簡單問題直接回答率很高，已經明顯脫離『每題都拆』的舊問題。
- 長對話記憶與延遲回憶能力已可用，代表工作記憶 + 三循環記憶接法有效。
- 10k 壓測下規劃與邊界穩定度很高，表示系統架構比純 prompt 基線可靠。

## 目前最主要的三個瓶頸
- `正式 ToM / 社會推理仍弱`：現在值=0.425；目標=0.65；標準=ToMBench accuracy >= 0.65，且低分 task 不再大量出現 0 分子項。
- `10k 壓測下表面回覆仍太集中`：現在值={"unique_reply_ratio": 0.0101, "top_20_reply_concentration": 0.7005}；目標={"unique_reply_ratio": 0.08, "top_20_reply_concentration": 0.35}；標準=10k unique_reply_ratio >= 0.08 且 top_20_reply_concentration <= 0.35。
- `日常狀態句與自我痛苦句仍有誤判空間`：現在值={"direct_daily_state_mode_match_rate": 1.0, "direct_daily_state_over_reframe_rate": 0.0}；目標={"direct_daily_state_mode_match_rate": 0.98, "direct_daily_state_over_reframe_rate": 0.02}；標準=direct_daily_state mode_match_rate >= 0.98，且相關 worst cases 明顯減少。

## 指標中文說明
- `簡單問題直接回答率`：越高越好。例：使用者說「你在幹嘛」，理想是直接回答，不是反問或拆題。
- `過度拆題率`：越低越好。例：使用者只說「我今天很累」，不應被誤當成要先重構問題。
- `工作記憶相關率`：越高越好。代表送進左腦的記憶真的跟當輪有關，不是亂塞背景。
- `正式心智理論分數`：越高越好。例：故事裡 A 在暗示 B，系統要能看出來不是只讀字面。
- `回覆獨特率`：越高越好。代表同類題目不會一直回同一句。
- `前 20 回覆集中率`：越低越好。這個太高就表示模板化嚴重。

## 目標達成度
- `像人類地直接回答`：score=0.9936 / target=0.95 / status=good — 這項高表示模型不會逢題拆題，簡單對話能直接回應。
- `像人類地維持工作記憶`：score=0.9167 / target=0.9 / status=good — 這項高表示不是把所有記憶亂塞進左腦，而是能抓住真正相關的少量資訊。
- `像人類地做多路徑思考`：score=1.0 / target=1.0 / status=good — 這項高表示左腦不是單一路徑，而是有候選計畫、scratchpad 與 rerank。
- `像人類地推測別人心思`：score=0.425 / target=0.65 / status=weak — 這項高表示模型不只會回話，還能在故事任務裡推測他人信念、情緒與隱含意圖。
- `像人類地避免模板化`：score=0.0202 / target=0.65 / status=weak — 這項高表示同類題目不會一直掉進同一句模板。

## 與 Prompt-only 基線的歷史對照快照
- `Avg Score`：{"dual_brain": 0.8297, "prompt_only": 0.1446, "delta": 0.6851}
- `Emotional Understanding`：{"dual_brain": 0.7364, "prompt_only": 0.0401, "delta": 0.6963}
- `Decision-Making/Moral Alignment`：{"dual_brain": 0.8788, "prompt_only": 0.2576, "delta": 0.6212}
- `In-Character Consistency`：{"dual_brain": 0.8739, "prompt_only": 0.1362, "delta": 0.7377}
- `Boundary Queries`：{"dual_brain": 1.0, "prompt_only": 0.0952, "delta": 0.9048}
- `Know-Hallucination Safe Rate`：{"dual_brain": 1.0, "prompt_only": 0.8571, "delta": 0.1429}
