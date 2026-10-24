# M10.2 Behavior-preserving Casual-register 驗收

日期：2026-08-15  
狀態：**source-disjoint 72-call remediation 完成；surface 100%，但出現 1 個 authority regression，總 gate 失敗。**

## 1. 問題與資料

M10.1 的主要 surface failure 是 polite-register drift。M10.2 不重用那 16 個已曝光場景，而是建立 18 個全新 synthetic language cases：中文／英文／日文各 6，六個 behavior labels 各 3，遊戲、隊友、邀約、隱私與裝置故障等事件文字和 M9/M10 重疊 0。

這是知道失敗類型後建立的 source-disjoint remediation fixture，不是 untouched global holdout；此限制已在 dataset 與 preregistration 先寫明。

## 2. 單一處理差異

- `S0_ONE_PASS`：沿用 frozen M10 behavior-authoritative realization。
- `S1_REGISTER_REPAIR`：把同一個 S0 raw utterance 再交給同一 `qwen3.5:9b`，只允許改 casual register／surface naturalness；behavior、肯否、問句／斷定、事實、關係距離與安全邊界不得改。

所有 18 案都進 repair，不依 S0 是否通過選擇，避免只修可見 failure 的 selection bias。沒有 scored retry。

## 3. Frozen 結果

| 條件 | 完整 visible contract | authority alignment |
|---|---:|---:|
| S0 One-pass | 13/18 = 72.22% | 18/18 = 100% |
| S1 Register repair | 18/18 = 100% | 17/18 = 94.44% |

12/18 句子真的改變。S0 的五個 surface failures 全為 polite register；S1 全部修正，且 0 個原 surface pass 被修成 fail。沒有私人 Uruha 事實或讀心宣稱。

七個 preregistered hypotheses 通過五個。兩個失敗為：S1 authority 沒有至少等於 S0，以及 aligned→misaligned regression 不是 0。因此不能只看 surface 100% 宣稱修正完成。

## 4. 唯一 proxy regression

`R-JA-06` authority 是 `pause_and_reassess`：

- S0：「同じミスが三回も起きたから、ちょっと待ってて確認し直そう。」
- S1：「同じミス三回もやらかすなら、ちょっと待ってて確認し直そう。」

固定 same-model classifier 把 S0 解為 pause-and-reassess，把 S1 解為 defer-commitment。人類讀者可能仍認為 S1 表達了 pause/reassess，因此這是必須交給 blind human semantic-preservation rating 的 proxy disagreement；在真人評分前，正式結果仍按 preregistered proxy 記為 regression，不能事後改 classifier。

## 5. 成本

- 18 initial + 18 repair + 36 classifier = 72 calls；
- 25,612 prompt tokens、4,261 completion tokens；
- 374.93 秒模型時間；
- 2 次 classifier-key alias normalization；
- 0 retries、0 production memory writes。

單看 generation，register repair 增加 18 calls、6,682 prompt tokens、248 completion tokens、51.79 秒。它帶來 +27.78 pp surface gain，但同模型 proxy 顯示 -5.56 pp authority alignment。

## 6. 證據邊界與下一步

Blind paired packet 與 condition key 已分離，尚無三位獨立完整評分者，因此不能宣稱人類偏好、語意保留或 Uruha naturalness。Public Uruha brief 仍是 development-only surface hypothesis，不能支援 persona fidelity 或 runtime activation。

下一步不是再對這 18 案改 prompt，而是：

1. 讓獨立評分者對 S0/S1 做 semantic preservation、behavior fit、casual naturalness 盲評；
2. 若人評確認 `R-JA-06` 仍保留 pause/reassess，將其記為 classifier proxy limitation，而不是修分；
3. 若人評也判定行為漂移，另立全新 holdout 評估結構化／確定性 register normalizer；
4. M9 predictor accuracy 仍是上游獨立瓶頸，不能靠 surface repair 取代。
