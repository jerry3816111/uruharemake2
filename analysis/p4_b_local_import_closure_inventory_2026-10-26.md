# P4-B 固定入口本地 import 閉包：只讀盤點與下一道設計界線

判定：**不能只補 32 個未綁的 entry 檔就宣稱 B 來源閉包。** `analysis/p4_b_entry_effect_source_inventory_2026-10-26.md` 的 33 層入口／共享工具分支結果仍有效；這次把直接／遞迴本地 import 擴成一個可重現的保守盤點。未 import 產品、未啟 Web／模型／Safari、未送 B。

盤點算法：以 `uruha_web_ui_product_p4_preference_fallback` 起，對每個 root `<name>.py` 解析 UTF-8 AST，走所有 `Import` alias 與絕對 `ImportFrom` 的第一段名稱，若 root 下同名 `.py` 存在則 BFS 入列，直到無新檔；不執行 import 或條件分支。排序所訪問的檔名後，以**無結尾換行**的 `"\n".join(names)` UTF-8 做 SHA-256。結果 **208 個 root Python 模組、合計 4,312,049 bytes，檔名列表 SHA-256 `0dd866f2bcd22708cabccfda6cfdf27930d67023649c746fdde8d59f75f96d05`**。208/208 是 regular、非 symlink；這批 AST 沒有相對 import，AST 可見 `import_module`／`__import__`／`eval`／`exec` 呼叫為 0。這個 digest 只核盤點檔名，不是每檔內容證明。

現 B controller `B_COMMITTED_SOURCES` 鎖 16 個 repo 檔；其中 9 個落在上述 208，故這個**靜態本地 import 集合**有 **199 個可達檔目前未綁**，另 7 個已鎖的是 controller/launcher 等安全檔。具名缺口包括 `uruha_brain_mac.py`、`uruha_product_function_calling_p4.py`、`uruha_read_only_function_calling_p4.py`、`uruha_product_vrm_renderer_p4.py`、`rightbrain_language_quality.py`、`uruha_memory_runtime.py`。入口另有 import-time install/patch、Web 建立 log/idle manager、Brain `load_dotenv()` 與 provider／DB 初始化；AST 可達不等於實際被執行，也不能用「無可見 dynamic import call」保證所有 runtime effects。

產品以外仍有本地資產：VRM renderer 讀 `web_assets/uruha_vrm_viewer_p4.bundle.js`，Function Calling core 讀契約 JSON；第三方 OpenAI／Chroma／Gradio、模型檔、環境輸入及某些 subprocess/eval 面板亦不由 208 `.py` 集合自動綁定。把全 repo 約 2,514 個 tracked `.py` 全鎖既過寬又仍漏資產；只把 33 入口加鎖雖可局部減缺，仍留下 Brain/overlay 等大量 B Send effect 缺口。

下一個必要設計審查應先凍結 **B Send 的 source/effect oracle**：需綁哪些 Python 源與非 Python 資產、哪些第三方/環境來源須拒絕或記錄，何時核對（controller HEAD snapshot、child pre-Web、pre-create），以及 source drift/tamper 的 fake 負控。可候選使用 208 檔的 canonical `name→SHA-256` 摘要和精簡 receipt 欄位，不能只綁上述檔名 digest；現 receipt v4 exact fields 且 8,192B 上限，直接加 199 欄不可行，若升 v5 不得默改 v4 歷史契約。每次額外約 4.3MB 來源讀和 Git HEAD 比對的延遲需實測，不能從檔案大小推斷 Safari 20 秒已過。即使本地 source manifest 完成，若上述 effect oracle 尚有 missing，**真 B Send／第四次模型／Safari 仍 NO-GO**；原 v1/v2 合成及三次真零輪判定不改。
