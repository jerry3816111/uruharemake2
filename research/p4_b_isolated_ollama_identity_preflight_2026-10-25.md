# P4 B：隔離 Ollama 身份預檢（非 B、零生成）

狀態：前瞻工程計畫；**不放行 A、B 或 Safari**。這是既有 P4 B hard-cap 卡中 token oracle 的單一必要子項：先移除共用 daemon 的日常 tag／runner／template 競爭，再談計數。原 A/B 題、gold、模型、上限與一次性規則不變；B 的真請求和作者評分此階段不讀、不送。

## Before 與判準

目前 `P4BResourceGate` 在 P2 轉換後攔截請求，但 `prompt_token_upper_bound` 只有測試提供的整數 callback；共用 `127.0.0.1:11434` 上的 render、runner `/tokenize`、真正生成不是原子同身份。`uruha_brain_mac.py` 亦把 LeftBrain URL 固定為 11434。非 B 兩訊息 fixture 的共享 daemon 計數 36 只能證工具可用，不能證 B 上界。修改前 SHA：gate `f95d46ffec08d344a9460fe66314b457c25b8e0fccf0e0c3c7ed9f1143baee9f`；ledger `b3210b92f7af7a50ca948a63dd5129d2d0d92bf1fc861f8808c0bba05ce278b9`；brain `c255fa631f100574dfc17108f10bf892c56c8ef54d590f6826cb61ddd6797fcd`；P2 transformer `52c8ff789fabd4c0cbbaa823aa45db725d7d08a5791c2c1660c5698ed94b455c`。

本項只證明是否能以本機 Ollama 0.34.4 在一個新 0700 臨時 root、私有 `OLLAMA_MODELS`、獨立 loopback port 啟動私有服務，並用**非 B 字串**取得零生成 rendered prompt 和同私有 runner tokenization；核 manifest／各 blob SHA、不同 inode、daemon/runner PID、binary 版本與路徑、Go-vs-GGUF 模板分支、render/template digest。預期 manifest SHA 是 `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`，GGUF `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`，template `eb4402837c7829a690fa845de4d7f3fd842c2adee476d5341da8a46ea9255175`，system `66b9ea09bd5b7099cbb4fc820f31b575c0366fa439b08245566692c6784e281e`。只可聲稱 **0 generated completions**；render-only 與 tokenizer HTTP 診斷呼叫要計數，debug response usage=0 不等於 prompt-token 數。子程序環境固定 `OLLAMA_HOST=127.0.0.1:<new port>`、`OLLAMA_MODELS=<private root>`、`OLLAMA_NO_CLOUD=1`、`OLLAMA_MAX_LOADED_MODELS=1`、`OLLAMA_NUM_PARALLEL=1`；不得修改共用 11434 服務或正式 DB。所有 raw fixture 僅為無敏感測試句，repo 只保存 digest、token 數、耗時與失敗原因。clone 後需核 inode 不同、各 blob byte digest、沒有 hardlink/symlink，及可用磁碟未顯著下降；若 clone 不是 copy-on-write 或耗費異常，停止。

成功僅表示可建立受控的**合作式身份環境**；若 runner 無法可靠歸屬私有 daemon、render 分支未知、private store 漂移或 `/tokenize` 無法安全定位，FAIL 並維持 B 常閉。即使此項成功，仍需前瞻的產品 child URL/endpoint 綁定、同 shape 非 B 真 usage parity、**B 實際 transformed request 的送前計數**、Web terminal fail-closed 和非 B Safari click→DOM 20 秒演練；A 的真人作者三項評分及 A on-only PASS 亦不可替代。此預檢不對抗同帳號惡意改檔者，不主張跨 HTTP 原子交易或產品成本硬保證。

資源上限：1 個私有 daemon、1 個 7B model CoW copy、0 模型生成、0 Safari、0 A/B 題、0 正式 DB。停止只針對本項新啟動 PID；臨時 root 若含模型副本，收尾核 exact path／disk usage 再做可恢復清理或保留並回報。驗證先用 static／clone identity 檢查，再啟動／render／tokenize；任何失敗保留負結果，不重試／替換模型或題目。即使 `127.0.0.1` 私有 port 成立，也不是同帳號其他程序無法呼叫的 OS/network authorization。
