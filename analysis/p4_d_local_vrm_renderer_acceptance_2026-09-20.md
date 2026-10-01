# P4-D 本機 VRM 圖像顯示驗收

日期：2026-09-20
結論：`local_vrm_renderer_and_product_regressions_pass`

## 真正新增的能力

同一個 `127.0.0.1:7860` UruhaBrain 產品頁面現在有一個 browser-only 的 **Local VRM Stage**。它讓使用者選擇自己電腦上的
`.vrm` 檔案，直接在 Safari 分頁內解析與顯示；檔案不經 Gradio upload、不寫入 server，也不會被當成長期記憶。面板把流程畫成
四個可見節點：選擇本機檔案 → 格式與大小檢查 → VRM 解析 → 畫面呈現。

P4-D 沒有下載或附帶一ノ瀬うるは角色模型。沒有模型時只顯示中性的紫色 wireframe 舞台，畫面明寫
`NEUTRAL STAGE · NOT URUHA`，因此不能把 placeholder 誤認為完成角色複製。

## Safari 實際三狀態

1. 初始狀態：canvas 與中性舞台可見，四個流程節點皆未完成，文字明寫尚未載入 VRM。
2. 合法檔案：使用暫存在隔離 runtime 的 `4,020 bytes` 自製 VRM 1.0 T-pose mannequin；Safari 實際畫出紫色人形，四節點全綠，
   顯示「VRM 已在本機畫面呈現／模型資訊：Neutral P4-D Fixture。未連接動作決策。」
3. 破損檔案：`9 bytes` 非 VRM 內容被 parser 拒絕，parse 節點變紅、render 節點沒有完成、placeholder 回復，顯示
   「解析器拒絕此檔案；沒有宣稱已顯示。」之後重新載入合法 fixture，畫面與四個綠色節點恢復，並留在 Safari 給使用者查看。

這三步不是只測 HTML 字串；是 Safari 實際 file picker、parser、WebGL canvas 與 accessibility state 的可見驗收。

## 沒有把 3D 面板偷偷接到其他能力

- valid → invalid → valid 的純 VRM 操作期間，conversation JSONL 維持 `3→3` rows；VRM 操作新增聊天／記憶寫回=`0`。
- P4-D 自己新增模型呼叫=`0`、tool execution=`0`、action execution=`0`、production memory access=`0`。
- viewer entry 沒有 remote URL、`fetch` 或 XHR；GLTF loader 只允許 `blob:`／`data:`，其他 URL 直接
  `external_resource_blocked`。有效 fixture 也不含外部 texture／buffer URI。
- 上述是 renderer 本身的 application-level no-network 證據，不是假稱抓取了整個 Safari 的封包；Safari 當時共有 49 個既有分頁，
  所以沒有把其他分頁的網路活動冒充為此 viewer 的精確量測。
- 原本第一個「bundle 任何位置都不能有 http 字面」proxy 確實失敗：`http://=2`、`https://=1`；來源分別是 XHTML namespace、
  shader comment 與官方 license URL。失敗被保留，之後只修正量測方式，沒有更換 dependency 或放寬 runtime no-network 行為。

## 原產品功能回歸

VRM 保持可見時，以新 session 實際跑兩輪：

- status tool：英文詢問 runtime 狀態，得到自然日文
  「うん、脳はまだ待機中。記録は0ターン、記憶は隔離環境。今使えるのは読み取り専用の状態確認だけ。」；仍為 1 次既有
  P4-C 本機模型呼叫、1 次 read-only tool、0 side effect，五個 function 節點可見，端到端 `6.3426s`。
- ordinary chat：英文要求只聽、不給建議，得到
  「うん。今は方法出さないから、そのまま話して。」；仍選 `listen_presence`、排除 `solve_regulation`，P4-D 新增模型／工具呼叫
  都是 0，69-node 原 cognitive path 保留，端到端 `2.842s`。

因此這次單一變因是「本機 3D 顯示面」，不是把聊天或 Function Calling 路由改掉。

## 資源與邊界

一次 npm install 安裝 17 個 package；直接固定 `@pixiv/three-vrm 3.5.5`、`three 0.180.0`、build-only
`esbuild 0.25.10`。runtime 是一個 `726,773 bytes` self-contained inline IIFE，沒有 CDN。付費 API、外部部署、角色 asset 下載皆為 0。

P4-D 證明「使用者提供的本機 VRM 能在同一產品頁誠實顯示，成功與失敗流程可視化」。它不證明角色像一ノ瀬うるは、不提供角色
asset 的授權、不代表動作智慧，也沒有把未經研究驗證的 action policy 接到 avatar。下一個必要產品 gate 應驗證隔離記憶在 process
重啟後能否真的回溯，因為這是目前統一入口仍未完成的核心長期要求。
