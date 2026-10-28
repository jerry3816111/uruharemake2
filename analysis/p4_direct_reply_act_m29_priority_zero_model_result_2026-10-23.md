# P4 當輪直接回覆行動優先權：產品前零模型結果

日期：2026-10-23。事前問題、六題及 7/7 preimplementation SHA 已於 `6533026` 凍結推送；只讀前檢於 `4e43a56` 保存。本報告是零模型／接線證據，不是 fresh generation、Safari、同模型品質比較、人評或正式 holdout。

## 改動與反例

新增 opt-in `uruha_direct_reply_act_m29_priority_p4.py`，只在原 M29 字面投影確實要求接管、同輪來源摘要吻合、M28 無更高權限、M33 無來源原子路徑、且唯一直接請求是「一言だけ労って／軽く励まして」時，將這一次 M29 projection veto。它不產生固定安慰句、不改 M25/M31/M32 或來源資料，也不把心理推測寫入長期記憶。新產品入口及 detached controller 明確選用此 overlay；原產品入口保持原 SHA。

第一版聚焦 15/15 過，但只讀對抗審查指出無引號的筆記、翻譯題、第三者傳話，以及 `飛び降りたい／人を殴った` 會被薄弱文字規則錯認成一般直接請求；新產品入口也因新加一層 `_prior` 後複製舊層數，首次 full-chain import 出現 `AttributeError`。已保留這些失敗事實，在**同一項、首次有根據修正**中只改新 overlay／入口：來源歸屬與已知敏感語境 fail closed，入口改成具名逐層安裝，二次安裝／覆寫偵測需顯式成立。這只是列明的反例，不是全面語用來源辨識或完整安全分類；舊安全路由本身沒有被修正。

## 實測範圍

- 新六題及額外語法、來源、否定、敏感、安裝覆寫共 **25/25**；真正 `cognitive_tick→emit` 的隔離子程序中，a0/a1 原產品路由 M29=true／M31 接管，opt-in M29=false 後 M33 不接管，原字串交給 `LeftBrain.think` 的 full planner，fake plan 的 `brief_care／brief_encouragement` 保留至回覆與 episode。**fake planner 按關鍵字直接給理想句，只能證接線，不能算真模型品質。**
- 受影響 M23/M25/M28/M29/M31/M32、P4-AY、reported-receipt／controller 共 **125/125**；另一組產品 chain、日文、Web graph、compute receipt 相鄰 **97/97**。Python 3.12 專案產品環境，無新模型、下載或正式 DB 寫入；`python3` 系統 3.14 沒有 pytest，先前一次命令只因環境失敗，換既有 `.venv/product_checks/bin/python`，沒有安裝套件。
- 新入口 `install_product_chain()` 再 `base.build_demo()` 的零模型啟動煙測建立 Gradio `Blocks`；controller `--help` 正常。前置 7/7 SHA 再核通過，原 M31/M32/Web 舊入口沒有修改。

## 判定與下一層

有限 direct-act 路由接線 **PASS**，產品／Safari **pending**。這只把使用者明示的回覆行動從事件字面投影中保留到一般 planner，不證明系統會猜中未明示的心意、日文自然度或優於強 LLM。凍結的 a0/a1 仍需同模型、同輸入、獨立 T0 的 baseline／system 配對；a2–a5 只跑 system，總計最多八 arm-turn、每題一次／0 retry。圖、泡泡、私有收據、隔離 DB、≤20 秒、token／向量成本與安全負控分別核；未保存原生圖檔則 saved-visual FAIL。若真模型只重述事件或任何 hard gate 失敗，保留整批 strict FAIL，不用零模型結果洗白。
