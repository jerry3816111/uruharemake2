# P4-BD 事前設計審查：role-aware evidence span（尚未執行模型）

狀態：**設計與離線測試已完成，等待 freeze commit SHA；本文件不是 P4-BD 結果。** 審查為開發代理與兩次隔離閱讀的 LLM-proxy 判斷，**不是獨立人類審查或人評**。原 P4-BC `1424f24` freeze／`4045947` runner／28 calls 的正式 FAIL 永久不變。

## Before 與唯一變因

P4-BC 9B/4B 各有 `0/6` single-gold evidence exact；但兩模型在 12 組 positive 的 3-role set 與 source-exact substring 上全部正確。例子同時包含可疑似合理的短／長邊界與 `email` 代替 `subject` 這種角色錯。P4-BD **只更動 evidence span 的評分邊界**：仍保留 strict `positive_exact_spec_count`、`positive_evidence_exact_count` 並逐案報告；新 eligibility 改以「非 span 欄位逐字相同＋預先列舉的同角色 exact source span」計分。若舊整包 exact 仍作新 eligibility，這個單變因實驗在邏輯上無法檢驗，因此它不作本次放行 gate；這是事前寫明的評價變更，不回寫 P4-BC。

其餘不變：原 P4-BC prompt/schema、6 個 template、完整 canonical slots、8 unavailable reason、9B/4B、M2 Pro 32GB、temperature `0`、seed `20260927`、`num_ctx=4096`、`num_predict=480`、0 retry、每 scored call `≤20s`、P4-BB compiler 與產品 runtime。新題 6 positive（繁中／英／日各 2，六 template 各 1）及 8 control（八種 reason 各 1）全為 developer-authored，僅是新的**開發 proxy**，不是獨立 holdout。與 BB/BC 原題的完整 source 逐字交集為 0，但受固定 ontology 限制，語義族重疊，不能宣稱語料獨立泛化。

## 標註代理與提前處置分歧

在任何 P4-BD 模型輸出前，兩個互不看對方結果的 LLM pass 只看 [`p4_bd_span_annotation_candidates_v1.json`](../datasets/p4_bd_span_annotation_candidates_v1.json)，對 18 個 role × 3 個 source-exact candidate 判接受／拒絕。候選與規則仍由開發者設計，故這不是雙真人。原始 54 個二元判斷有 `48/54` 相同、完整 role-set `12/18` 相同；六個分歧全是裸名詞是否足夠指認目標。原標籤與分歧保存在 [`p4_bd_annotation_proxy_pre_freeze_2026-09-29.json`](p4_bd_annotation_proxy_pre_freeze_2026-09-29.json)。**事前採兩套判斷交集**：有分歧的短詞不接受；18 個 role 中 8 個有 2 個可接受 span、10 個只有 1 個。這些數字不能報作 inter-human α。

每 role 的正式可接受值是資料中的 `accepted_exact_spans`；只能 exact membership，不能任意 substring／overlap、大小寫／Unicode 正規化、翻譯或看見模型答案後補新值。每 role 另有 1 個 exact-source hard negative，保留其餘兩個正確 atom、source、template、slots；所有 18 個 mutant 均能通過 P4-BB compiler，卻必須被 P4-BD scorer 拒絕。這直接測試評分器是否能抓到下游 compiler 未抓的錯角色／錯範圍。`raw` evidence 只作診斷：若 packet 沒通過原 normalizer，不得靠 raw span 得 eligibility。

事前修正了草稿中漏掉「一個」的 request、`decision`/數量混淆、atomic limit 的「寫入日期即完成」意義，並使 third-party control 只因 ownership 失格。這些是**模型未跑前**的設計修正；freeze 之後不再改題或金標。

## 成功／失敗與資源上限

每模型各 14 案只呼叫一次，最多 `28` scored calls；固定先 9B 後 4B，各 prewarm 一次且不計 scored latency。要成為後續候選，必須同時達 JSON `14/14`、positive normalized／non-span exact／template／role-aware evidence／完整 packet／slots／downstream compile／mechanism／自然日文各 `6/6`，controls unavailable＋reason 各 `8/8`、false spec/source violation `0`，token 完整且 max call `≤20s`。任一 gate 失敗即該模型 FAIL；不得以另一模型遮蓋。若兩者都 PASS 才比較 median latency，tie 再比 completion tokens；若只有一者 PASS，僅該模型 eligible。strict single-gold exact 不放行，但保留其結果。過往 9B control reason `7/8`、max `21.71181s` 和 4B slots `5/6` 仍是**獨立風險**；本卡沒有修它們。

正式執行前再次核 `HEAD/freeze SHA`、dataset/prompt/compiler/scorer hashes、Ollama model digests、硬體與空的新 evidence path。prewarm 失敗就不送 scored calls；輸出採逐案 checkpoint、不可覆寫／續跑。任何 timeout/JSON 失敗只保留失敗，0 retry。既有 P4-BC runner 不重跑。模型可能耗時約數分鐘；這只是本機模型開發成本，並非外部部署。

## 審查後仍有的效度限制

- 原 prompt 明寫「最短片段」；較長等價片段若被 role-aware scorer 接受，不代表模型遵守了這條 prompt 指示，需同時報 strict 分數。
- source ID/span 透過 dynamic enum 約束，`assistant_or_private_source_count=0` 主要是 schema／normalizer 加上資料全為 current user 的結果，不能當作一般開放對話來源安全證明。
- 兩個 LLM pass 的 `48/54` 只能說明本組 proxy 規則有分歧；交集保守，也可能誤拒合法短片段。正式結果即使 PASS，只能支持本組預先列舉邊界，不支持自由語用理解、建議有效、人評、強 LLM 優勢或「人腦方程式」。
- P4-BD 不改 P4-BB／BC 凍結檔、不接產品。若 role-aware 過但 slots／reason／latency 失敗，另立單變因卡；不能在本卡偷改。

## 離線證據與下一步

先前 BB/BC 相鄰測試 `57 passed`；P4-BD 新 freeze＋scorer 測試和相鄰合跑 `66 passed`（2026-09-29，無模型呼叫）。待完成 freeze commit，記 SHA，再加只調用 frozen BC 模型介面／normalizer 的一次性 runner，先測 runner 假資料契約，提交 runner 後才做正式模型 preflight 與唯一執行。所有層分開記錄；沒有 Safari 或真人驗收就標 pending。
