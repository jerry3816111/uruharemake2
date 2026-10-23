# P4 f4：Safari 前置時序門檻失敗，0 Send

狀態：**strict FAIL（pre-Send admission gate），不是模型品質結果**。已提交 `9a18a3f` 的 opt-in schema/零模型 153/153 PASS 不因此重判；舊 f3 品質 FAIL 也保留。凍結新題 `初めて自分で味噌汁を作れた。今は一言だけ励まして。` 只在原生 Safari 本次新分頁預填，**沒有按 Send**；真 provider generation 0、token 0、episode 0、沒有本輪泡泡或 node graph 可評。不能宣稱本機 `qwen2.5:7b` 遵守 schema 或新日文回覆改善。

## 可重核原件與時間線

- 工作樹及分支仍為 `codex/v2-15-pragmatic-research-showcase`，原始 dirty checkout、正式 DB、無關 `output/graduate_application_report/` 未碰。port 7931 先空閒；本機 `qwen2.5:7b` digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。全新 controller-owned 0700 私有 root 為 `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-0thjka2f`。官方 ONNX archive SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`、size 83,178,821，host inode 4160298、私有 inode 49367977；封網 warm 1×384，下載嘗試 0。
- zero-turn rehearsal run `a67a7e6c1ddb359e`／PID 28881。首次即時 verify 為 `product_listener_not_same_pid` 啟動競態；隨後同 PID 28881、HTTP ready、listener_same_pid_before_after=true，精確 planned stop、7931 vacant。沒有送訊息。正式 opt-in run `f6c2c79f42a0c237`／PID 29155 隨後同 PID ready，原生 Safari 新頁 `127.0.0.1:7931` 顯示 session `20261024_070939_c31e7c6c`、本私有 log 路徑；tab 52→53。
- T0 私有 0600+fsync 快照 `evidence/db-t0.json` SHA `50b3ecedab346231daf9dcec6c5a57378480fd38302b9f8fb18196082810c637`，journal 0；預填後 Tpre `evidence/db-tpre.json` SHA `d153fbf9c9b45aa0da72d824977659bced9cbe739d7a6e04e4fff9d250433ecc`，journal seq1–4＝2 個完整背景 pair。兩者同 PID/session/reset0/finish0、`brain_status=ready`、同一唯一 `memory_db/chroma.sqlite3` 176128 bytes SHA `428203c09427b94d750d1082c34a880b3dbcd6d58a83514c43d5c5f9528f6643`；`session_db` 與 Web 對話 log 均無檔。兩對背景 `idle_noop`、0 reported write/vector mutation/error/unknown worker。
- **失敗點**：Tpre 結束 monotonic `1796929838081625`，準備提交前背景 seq5 `background_start` 於 `1796939420884000`（間隔 9.582802375 秒），seq6 `background_end` 於 `1796939424010750`。故 Tpre→人類 admission 之間已經有背景交錯；凍結計畫的無交錯及≤10秒保證不能成立。操作上先做 Tpre、再逐項讀取 journal 耗去預算；後續必須把所有靜態核對提前，或在下一個**事前定案的新題**於背景 pair 剛結束後迅速 Tpre→Send，並在 arrival 後嚴格驗 no interleave。不能以背景無 DB write 取代「無 interleave」硬 gate。
- 停機後私有 journal seq1–8 為 4 對完整 `idle_noop`，沒有 `human_arrival` 或任何 cognition/terminal。journal SHA `dbc750c38d61bb0bb8ef5afdee16813e50d7f5e38041f8afc0f409e4030ea7c1`；隔離 DB 停機後 SHA 仍為 `428203c0...`，receipt `human_submission_finish_count=0`。正式 run stop record SHA `888a276b092ab12abaf6a97523d4549f19c42b99d1d804bc697dc36ac04964ba`：PID 29155 exact planned stop、7931 vacant。只關新 Safari tab 53→52，原先頁面未關。

## 判定與下一步

f4 的 schema-arm code/contract 成立；真模型格式可靠度、最終鼓勵品質、記憶寫回、原生節點圖、可見成本與完整產品 gate 均**未測到**。這是實驗操作時序錯誤，不是產品回覆正負樣本，也不能與 f3 做因果對照；不重送 f4／不變更 gold。下一個必要交付是前瞻凍結新的 source-disjoint 題及「先靜態核對→背景 pair 完整結束→Tpre 快照→立即一次 Safari Send→從 journal 核無交錯」操作門檻；若無法做到即保留 pre-Send FAIL。仍需另外設計相同 stimulus 受控 A/B 才能主張 schema carrier 的因果增益。目標 Goal 保持 active。
