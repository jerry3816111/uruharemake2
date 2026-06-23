# 工程進度報告：右腦與 GitHub 化

## 主要問題

上次報告後的核心問題是右腦輸出不穩，左腦語意可能在最後回覆消失。

## 本次改造

建立 runtime v1 契約、嚴格 gate、base-only 對照、1025 筆訓練資料與 V8 訓練實驗。

## 數據

PR #25 gate: raw accept 0.0%, final contract 100.0%, fallback 100.0%.

訓練資料 1025 筆；V8 eval loss 3.35；小型比較最佳 after 標籤：V5。

## 判定

V8 尚未通過接管門檻，因此不切換預設；這次進度的價值是建立可測與可阻擋的上線標準。
