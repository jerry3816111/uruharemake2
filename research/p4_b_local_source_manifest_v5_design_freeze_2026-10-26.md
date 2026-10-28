# P4-B 本地來源閉包摘要：v5 設計審查草案

狀態：兩條獨立只讀複審 **GO 僅此設計基準；尚未 GO 改碼**。改碼前另須 implementation freeze，鎖定摘要序列化、239/232 範圍、archive 大小／超時及負控。不改 frozen v4 收據或歷史 B/fixture 結果；第四次真 Ollama、B Send、Web／Safari 仍 NO-GO。

## 先前證據與單一變因

`analysis/p4_b_local_import_closure_inventory_2026-10-26.md` 的首版盤點是 **208 root 單檔**，不是完整 package 閉包。獨立複審找到 `longitudinal_human_model` 本地 package：實際可達 7 檔，完整平面 package 有 21 個 tracked `.py`／159,697B。為降低相對匯入 parser 的漏列風險，本設計取 **208 root＋全 21 package＝229 檔保守 superset**、4,471,746B、排序相對路徑（無尾換行）檔名 SHA-256 `f76e79ffcf08fcd4aadc15a1810bdb820b4fd5148d72843935d85d3d49b09803`。現 source lock 16 與原 root 集交集 9，故至少 199 個可達 root 檔未綁。這項**唯一核心變因**是把 B child 的本地產品來源擴到此保守集合與兩個**明列高優先級**本地資產（`web_assets/uruha_vrm_viewer_p4.bundle.js`、`configs/p4_c_read_only_function_calling_contract_v1.json`），並使 controller HEAD snapshot 與 child receipt/pre-create 相互綁定。其他資產仍 missing；這不是完整外部套件／動態 effect 閉包，更不是 B Send 授權。

## 最小資料流與失敗行為

1. 新純函式模組 `p4_b_product_source_manifest.py`：不 import Web/Brain、無 runtime side effect；從固定 entry 以 AST root-local import BFS 重算 root 集，辨識唯一已知本地 package `longitudinal_human_model` 並納入其**全 21 個平面 `.py`**。掃 package 內的本地 root/package import 與相對匯入，若出現未列 root、另一個／巢狀／namespace package、未知動態語法或檔缺／非 regular／symlink，fail-closed，不把第三方套件誤當本地 package。新增本模組後，固定入口會經 binding import 它，預期 root 增 1、**合計 230 Python**，預期排序檔名 digest `cd9f04bfcbc517b159aa19a4de2dc77982c161722760bed8f73b9fd97aee1053`；實作若多出其他 local import 即停下重新審查，不追綠改數字。另列固定兩資產。把每個 canonical `name→SHA-256(bytes)` 排序序列聚合成一個 digest，不能只用檔名 digest。
2. controller 原 `_b_committed_source_snapshot` 對既有 16＋保守 Python 集＋兩資產（預計去重 **239 個檔案路徑**）做 live==HEAD 檢查，回每檔 SHA-256。不要逐檔開 `git show`；以單次 `git archive --format=tar HEAD -- <exact paths>` 或同等單 process 操作，要求**regular file 成員**與指定檔案集合精確相等，大小／內容逐檔相同、無重名且 archive 大小有界。Git tar 會另加 parent directory 成員：只能是指定檔案的預期 parent directories、型別 directory／size 0；額外目錄、symlink 或其他型別一律拒絕。archive／live 不符、Git error／timeout 皆拒啟 child。正常非 B 路徑不進這個新增閉包。
3. 前瞻 receipt **schema v5** 加 64-hex `product_source_manifest_sha256` 與 `product_manifest_module_sha256`；v4 原件保持歷史原判，不改名冒稱 v5，新的 v5 child 要拒 v4。issue receipt 先核既有 gate/身份，再記 live manifest；child pre-Web `_child_context` 與原本每次 create 前後的 `private_child_source_digests` 重算且與 receipt 相比，遇 nested entry、Brain、工具、package、VRM JS、契約 JSON 或 manifest module 漂移均 fail-closed。沿用 8,192B receipt 上限；不把 232 個 source/asset SHA 展開為 receipt 欄位。
4. 明確列出剩餘未閉包 effects：外部 OpenAI/Chroma/Gradio 套件、環境／`.env`、動態載入、模型檔與其他資產、Web/Brain import-time effects，以及當前 B prompt token bound/20s。v5 PASS 不准宣稱全來源閉包或端到端隔離；若能證明這些 effects 對 B Send 有作用，需另凍結單一後續修正，不能趁 v5 偷加廣泛封網或重路由。

## 允許檔、測試與成本停損

預計只新增 `p4_b_product_source_manifest.py`，修改 `p4_preference_fallback_detached_control.py`、`uruha_p4_b_private_endpoint_binding.py`、如必要的 `uruha_p4_b_private_child_bootstrap.py`；測試只改 `test_p4_b_private_controller_seam.py`、`test_p4_b_private_endpoint_binding.py`、`test_p4_b_private_child_bootstrap.py`、`test_p4_b_private_child_chain_zero_provider.py`，可新增 `test_p4_b_product_source_manifest.py`。本卡／任務卡／結果報告僅記錄。不得動原 v1/v2 synthetic fixture、Web/Brain 產品碼、正式資料、題本或原始 dirty checkout。

先 red：nested entry/Brain/tool/package/JS/JSON 各自 drift；HEAD 不符；缺失、symlink、額外 AST 本地依賴；v4 receipt 在 v5 路徑拒絕；fake zero-provider chain 仍不生模型/Web Send。改後跑上述受影響測試與必要相鄰；保留舊 v4 歷史結果，不把歷史 fixture 改綠。`py_compile`／`git diff --check`；獨立只讀 source/fake review 後 scoped commit/push PR #435 exact head。失敗至多兩個有根據修正批次，否則 `REVIEW_REQUIRED`。

只讀成本校準（同一工作樹、無模型）：舊 208 root 子集逐一 `git show` 比對 **2.336 秒**；一次 `git archive` 比對 **0.105 秒**，含 AST 解析的完整 read-only 指令 real **1.00 秒**；tar 4,485,120B。229 Python＋兩資產的單次 Git archive **exit0／0.060849 秒／5,396,480B**，含指定檔 231 與自動加入的 `configs/`、`longitudinal_human_model/`、`web_assets/` 三個 directory member；尚未加入新 helper 或既有 controller 專用檔。這些不是完整新 239 範圍或真 child/pre-create 延遲，更不證 Safari 20 秒。實作須記錄一次 fake snapshot 與 pre-create 重算的時間／bytes；若 source 摘要讓既有模型身份 SHA 的總開銷或 20 秒 gate 無法收斂，保留成本失敗，不以快取略過漂移核對。
