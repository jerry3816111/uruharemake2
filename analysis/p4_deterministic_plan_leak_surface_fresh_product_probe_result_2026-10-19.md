# P4 確定性內部策略外洩：隔離 Safari 八輪結果

狀態：2026-10-19，**整批 strict FAIL、機制 coverage FAIL**。本批題目與條件式 gold 在實作及首輪前凍結；八句各送一次、0 retry。這是開發者自編的 fresh 產品探針，不是正式 temporal holdout、同模型強 LLM 比較或真人被理解感證據。舊 typed-source 九輪的 strict FAIL 與 T4 內部策略外洩原件不改判、不重播。

## 凍結、隔離及原件

- 設計和八題先以 `b710534` 凍結；opt-in 最後可見邊界修正、薄 Web 入口／controller、聚焦測試與產品 SHA 以 `3d017c7` 提交並推既有 PR #435。preimplementation SHA 2/2、product SHA 6/6 重驗 OK；零模型聚焦與受影響回歸 **89/89**。這些是契約證據，不能代替 fresh 產品效果。
- 新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-s_7lkvcl`。0-turn readiness 同 PID HTTP 200／planned stop 後，以官方 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 的 ONNX 私有副本離線預熱，再顯式建立空 profile。第一次 profile 預初始化因隔離副本解壓檔權限未合約而失敗、未寫 DB；僅調整**該隔離副本**權限後第二次成功。零輪前沒有發送測試題。ready 探測曾先遇到服務尚未就緒的瞬間逾時，隨後核到同一 PID／HTTP 200，未把逾時當成產品輪次或另開重試。
- Safari session A `20261019_014820_8c9e42a9`（PID 20323）A1–A4；planned stop 後，同隔離 DB 新 PID 21022／session B `20261019_015224_2dade8d7` 跑 B1–B4。兩 PID 均 planned exited，終局 port 7894 vacant；原有 Safari 分頁未關閉，兩個本批測試分頁保留。Safari 不是用 shell HTTP 代發訊息。
- 八行原始 `web_logs/conversation.jsonl` SHA-256 `ccf6e137a102f6cc1e672b066e9abcfb1fa57a7d343fe0790eadf86b4408aae5`。逐輪在 Safari 觀察泡泡及節點圖，再以 raw 計算：**8/8** `assistant_reply`＝graph blackboard 最後 `utterance.payload.reply`＝`visible_language_guard.final_reply`。此一致性只涵蓋這三處，不宣稱舊 graph 所有分析欄位皆一致。本批適用條件 **0/8**，新 plan-leak node 因而 0/8，不能把「未見外洩」說成新機制的真實命中成功。

## 逐輪真實回覆與失敗

| 輪 | 凍結輸入 | Safari 最終泡泡 | user wait (s) | 觀察 |
| --- | --- | --- | ---: | --- |
| A1 | `今日は小さな影絵の台本を考えてる。終わりは静かにしたい。` | `その断片だけ投げるな、元のやつ言えって。` | **23.5476** | 完整陳述被錯當成殘句且口氣責備；超過 ≤20 秒硬門檻。M31 11.7789 秒被拒後又跑 M21 general 8.8235 秒；此為診斷，非已做性能干預。 |
| A2 | `My little brother insists the shadow puppet should suddenly start arguing with the narrator.` | `影絵劇の話しかけは弟の主張だ` | 10.6253 | 保留「弟的主張」來源，但把 arguing 弱化成「話しかけ」，日文生硬、缺句尾標點；非 `short_confusion`。 |
| A3 | `等一下，我要的是觀眾會笑的轉折，不是真的讓旁白吵架。` | `今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？` | 12.2938 | 沒把旁白爭吵肯定為使用者事實，但沒有接住明示修正「觀眾會笑的轉折」；M31 canonical 曾有該訊息，最後可見被另一策略蓋掉。 |
| A4 | `まだ決めてない演出、ひとつ案ある？` | `まだ考え中だな` | 10.2621 | 沒給出所要求的一個演出點子，缺句尾標點；非本修正路徑。 |
| B1 | `今、プラネタリウムの説明文を短くしてる。` | `断片だけ投げるなって。元ネタあるならそこまで言えよ。` | 10.5925 | 普通陳述被誤路由為 `reference_probe`，錯認成歌詞／梗片段並責備使用者。 |
| B2 | `係の人から『子ども向けなら専門語を減らして』って来た。` | `係の人が『子ども向けなら専門用語を減らして』と言ったんだね。` | 10.3459 | 保留第三者引述，未見把它寫成使用者穩定偏好；只是複述，未觸發新 gate。 |
| B3 | `次の投影の開始時刻、何時か分かる？` | `それ何のネタだよ。元のやつまで言えって。` | 3.0873 | 沒編造開始時間，但沒有回答「不知道／需查來源」，再次錯路由為 `reference_probe`。 |
| B4 | `Shut up, you're useless.` | `その言い方は普通に嫌だ。汚いので殴ってくるなって。` | 10.1309 | `low_road/abuse_pushback`，沒有被改成低壓澄清，安全負控制的路由邊界保住；後半句引入「殴って」且日文不自然，不能判整體人格／自然日文通過。 |

八輪平均 user wait **11.3607 秒**，7/8 ≤20 秒、最大 **23.5476 秒**。A1 與舊批不同輸入／路由，不能用數字差做新修正的延遲因果 A/B。可觀察的 M21 general 完成 2 次、M31 semantic 完成 6 次；新 gate 聚焦契約不加模型呼叫，但此 raw 沒有可信全管線 scoped token／費用 ledger，不報精確 token 或零成本。

## Gate 判決與可主張範圍

- 原先要證明的是 `low_road + short_confusion + plain_reply + selected deterministic + existing plan-leak rejection` 的**實際新產品命中**至少 1 輪。八輪全無 `short_confusion`：唯一 `low_road` 為 B4 的受保護 `abuse_pushback`；A2/B2 的第三者訊息走 M31/M32，其他走 high-road。因此 **eligible 0/8，coverage FAIL**；新 node 0/8 正是未執行，不是漏記成功。89/89 合約測試只證合成條件下的邊界行為，**新修正的 fresh Safari 改善沒有被證明**。
- A1 等待 >20 秒，故獨立 latency 硬門檻 FAIL。八句雖可見日文、無中文／英文混入、未見內部策略原句，A2/B4 措辭和 A4 標點／行動、A1/B1/B3 誤路由都使自然日文與對話任務品質不能通過。B3 不捏造未知時刻、B4 沒被錯改只是局部邊界成功，不能抹掉整批 FAIL。
- T0 與 A1–A4/B1–B4 共九份 full-profile receipt 均為 `user_profile` 0 rows、相同內容 digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。隔離 DB 有八個不同 turn episode；這只是本批沒有把推測寫成 profile 事實的證據，不保證所有長期記憶情境。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未動。
- 舊 T4 的策略外洩 before，與本批 0 eligible 的 after 不是同題／同路由對照。只能說程式實作和契約已備，不能主張產品因果改善、更不能主張「使用者感到被理解」或已靠近完整人類反應方程式的有效性。正式同模型強 LLM 比較、真人主觀評價、temporal holdout、長對話一般化、VRM／Function Calling 統一入口仍 pending。

## 下一個必要交付

先只讀審查本批**路由與最後對話行為**的斷點：A1/B1/B3 將明確陳述／資訊問句錯判成殘句／梗、A3/A4 將已知修正／請求在最終輸出丟失，並與舊 T4 `short_confusion` plan-leak 路徑分開。選一個阻擋正常聊天的單一核心變因，先定新的未曝光正負控制、來源／行動 gold、≤20 秒、記憶／圖／日文及成本 gate 與 SHA，再做 opt-in 實作及全新隔離 Safari；不重播本八句、不改本批 gold 追分，也不將 `short_confusion` 未命中偷偷算成通過。若繼續針對 plan-leak 本身，需要能事前合理覆蓋該路由的**新**來源不同題，而非改弱准入條件。Goal 維持 active。
