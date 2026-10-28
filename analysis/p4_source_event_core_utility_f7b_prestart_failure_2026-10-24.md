# P4 f7b：隔離產品首次啟動前預檢失敗，0 Send

狀態：**strict FAIL（pre-start setup gate），沒有 zero-turn ready 或 fresh 模型回覆**。f7b source/gold/硬門檻已先以 `17346189cd4c0a90fcc4198acc7f15fe1946b844` 推 PR #435；本次沒有改產品程式、沒有把新題交給模型或 Safari，也沒有寫入長期記憶。f7a 的 pre-Send FAIL 不受影響。

## 發生了什麼

- 啟動前確認 7935 無 listener、f7b source manifest 3/3 和 f7 product manifest 10/10 SHA 正確；本地 `qwen2.5:7b` digest 仍是 `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。
- Controller `prepare` 產生全新 0700 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-mi1ez08g`。複製先前已核對的官方 ONNX cache 到此 root 的獨立私有檔案；archive 為 83,178,821 bytes、SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`。已安裝 Python 3.12 的離線 warm 終端觀察為 1×384 有限 embedding、`httpx.stream` 下載入口 0 次，未另存持久 warm receipt。第一次以系統 `python3` 呼叫 warm 因缺 `httpx` 而失敗，隨後改用已安裝 Python 3.12 完成 warm；兩次都沒有聊天或 generation。
- 本次 zero-turn product `start --python` **指定了** `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3` 作為產品 interpreter。Controller 先寫 `p4_preference_fallback_detached.prepared-claim.json`（SHA-256 `fd1d1cd9db6b2efc6863bf2184d25547002ccc0124fc1c261aebf342d81ad77b`），接著 product import preflight 以 `product_python_probe_failed:returncode=1` 停止。獨立重現的該 interpreter 匯入 `uruha_web_ui_product` 明確報 `ModuleNotFoundError: colorama`；這是此次預檢失敗的可重現原因，不是 controller 自選 Python、f7 來源效用或模型輸出錯誤。未再對已 claim 的 root 呼叫 start。
- 啟動前只讀確認專案既有 `.venv/product_checks/bin/python` 可匯入 `colorama`、`gradio`、`chromadb`，並通過同樣的 `uruha_web_ui_product`/demo-builder Python probe（`gradio 6.5.1`；有一條既有 `pkg_resources` warning）。這是**下一次選 interpreter 的前置證據**，不是本輪 zero-turn ready。7935 仍無 listener、root 的 `memory_db`/`web_logs` 皆空；沒有存活的產品服務 PID 可 stop，沒有新 Safari tab、預填或 Send。

## 判定與下一步

此輪在 zero-turn ready 之前就依凍結 fail-closed 規則停止，故 f7b 新題不重跑、不改 gold；不能宣稱真產品、可見日文、node graph、成本或人格通過。正式 DB、原始 dirty checkout、無關 `output/` 未碰；私有失敗 root 保留供稽核。下一次若要驗同一 f7 utility，須先對正確 product interpreter 做 source-free preflight，再前瞻凍結**另一個 source-disjoint 題**和新隔離 root，維持原 ≤10 秒／無 interleave、一次 Send／0 retry、可見 gold、graph/cost 硬門檻。這個環境失敗不等於能力進展，Goal 仍 active。
