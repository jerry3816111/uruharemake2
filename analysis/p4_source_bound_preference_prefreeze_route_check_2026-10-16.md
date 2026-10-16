# 新五輪：模型／Safari 前的來源與路由檢查

2026-10-16，在新資料 SHA freeze 與任何新產品模型呼叫**之前**執行。
使用 `.venv/product_checks/bin/python`，只匯入新產品 entry，
以 `LeftBrain.__new__`、`psyche={mood:0,trust:50}`、空 memory
呼叫原 `_ORIGINAL_RULE_PLAN`、已裝的 `_rule_based_plan` 及純讀
`admit_legacy_profile_facts`；沒有 server、生成、writer 或 Safari。
完整 exact inputs 與順序以新 JSON 為準；逐輪結果：

| turn | 舊 rule intent | 新 rule intent / planner_path | owner facts / admitted |
|---:|---|---|---|
| 1 | None | chat / source_bound_preference_fallback_p4 | like/黒豆きなこ餅 / 1 |
| 2 | None | None / None | [] / 0 |
| 3 | None | chat / source_bound_preference_fallback_p4 | like/青じそ梅せんべい / 1 |
| 4 | ask_like_me | ask_like_me / None | [] / 0 |
| 5 | None | chat / source_bound_preference_fallback_p4 | like/黒糖ほうじ茶 / 1 |

命令：

```sh
PYTHONDONTWRITEBYTECODE=1 URUHA_WEB_PREWARM_BRAIN=0 .venv/product_checks/bin/python -c 'import uruha_web_ui_product_p4_preference_fallback; from uruha_brain_mac import LeftBrain; import uruha_source_bound_preference_fallback_p4 as f; import uruha_profile_owner_admission_p4 as o; l=LeftBrain.__new__(LeftBrain); p={"mood":0,"trust":50}; xs=["私は黒豆きなこ餅が好き。","友達は小豆柚子羊羹が好き。","私は青じそ梅せんべいが好き。","ねえ、うちのこと好き？","私は黒糖ほうじ茶が好き。"]; [(lambda x, a, b, c: print({"turn":xs.index(x)+1,"prior_rule":(a or {}).get("intent"),"selected_rule":(b or {}).get("intent"),"planner_path":(b or {}).get("planner_path"),"owner_facts":c[0],"owner_admitted":c[1].get("admitted_count")}))(x,f._ORIGINAL_RULE_PLAN(l,x,p,{}),l._rule_based_plan(x,p,{}),o.admit_legacy_profile_facts(x)) for x in xs]'
```

這只證明無模型 rule/source gate；M31/M32/M33 或真 selected
plan、final 日文、graph、等待時間、DB row-ID 均未測。原先擬議
`私は青じそ梅おにぎりが好き。` 在 freeze 前測到舊規則
`food_offer_generic`，所以不用它冒充新快路正例；新句全文與
物品值在寫入 repository 前 `rg -F` 均無命中。這不是正式 holdout。
