# P4-A 統一本機入口現況盤點

日期：2026-09-20  
狀態：`inventory_complete`

## 實際結論

長期 Goal 所需的四項能力，目前不是四項都「已存在、只差放在一起」。可重跑的 source audit 得到：

| 能力 | repository 真實狀態 | 證據範圍 |
|---|---|---|
| Chat | 已接入 product entry | `uruha_web_ui_product.py`重用base `RUNTIME`與`build_demo()`；文字送出到`submit_text`，再到實際`brain.run_turn_debug` |
| 真實 runtime node graph | 已與同一聊天回合接線 | 同一text event outputs包含`flow_html`；turn result由actual observatory result render，不是另造展示JSON |
| VRM 3D | product runtime不存在 | Git tracked 3D asset=`0`；沒有VRM renderer、action executor或product import |
| Function Calling | 只有research policy，未進product | `vrm_action_policy_v34.py`存在，但product/web/brain均未import；沒有runtime tool schema或tool-result loop |

因此「既有 VRM 3D 與 Function Calling」不能再當成已完成前提。現有的是 VRM action語意與安全研究，不是可操作的3D角色；既有
fresh holdout也未授權physical execution。這項盤點不會把離線validator包成產品功能。

## 啟動阻塞

product entry預期的Python是safe worktree內的`Style-Bert-VITS2/venv/bin/python`，但該路徑不存在；目前system Python也沒有
Gradio。原始checkout另有一個可用的既有venv，但P4不能靠操作員每次手寫跨checkout命令、也不能把記憶預設寫到正式worktree DB。

盤點期間沒有啟動runtime或Safari；當時port 7860沒有product listener。唯一看到的project-related local Python listener是已知
B74 synthetic coder site的64217，不是產品聊天入口。

## P4-B 單一變因

下一步只新增「safe isolated product launcher」，不改brain、prompt、研究資料、Function Calling或VRM：

1. 明確解析可用Python，允許以參數／環境指定既有venv；不複製或修改原始dirty checkout。
2. 每次建立獨立temporary memory DB、session DB與Web log，除非操作員明確指定持久路徑；不得碰正式DB。
3. 只綁`127.0.0.1`，拒絕public host／share／登入／付費API。
4. `--check`需能在不啟動server、model或Safari下驗證interpreter、Gradio、entry與隔離路徑。
5. contract通過後才做真實本機啟動；Safari另記為可見層驗收，不以offline check代替。

完成P4-B只代表chat＋graph的統一入口可重現啟動。VRM與Function Calling仍是後續各自需要安全contract、實作與真實驗收的缺口。

## 驗證與邊界

- focused tests：`4 passed`
- source inventory validation：`valid=true`
- model／production memory read-write／tool execution／physical VRM action／Safari：全部`0`
- 沒有外部部署、登入、cookies或付費API。
- 這是source linkage與缺口證據；不是launch pass、Safari pass、3D render pass或Function Calling pass。
