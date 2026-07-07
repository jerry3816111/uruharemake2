# RightBrain Repair Selection Eval v1

## 一句話結論

右腦直接修復 LoRA 連續沒有淨增益後，下一步改成候選選擇問題：先確定同一套合約規則能穩定分辨乾淨回答與錯誤回答，再把這個任務交給後續 selector/verifier 學習。

## 分數總表

| 指標 | 結果 | 意義 |
|---|---:|---|
| case_count | 360 | 選擇題數 |
| candidate_count | 3233 | 候選總數 |
| invalid_candidate_error_detection_rate | 100.0% | 錯誤候選可被規則檢出的比例 |
| gold_selection_rate | 100.0% | selector 選到乾淨候選的比例 |
| valid_selection_rate | 100.0% | selector 選到合約有效候選的比例 |
| invalid_selection_rate | 0.0% | selector 錯選壞候選的比例；越低越好 |

## 這對右腦的意義

- F 右腦補強不是讓 ToMBench 推理變強，而是避免左腦已經想好的答案在最後表達層消失。
- 直接讓小模型重生一句話效果不穩，所以這次把問題改成更可控的「多候選選擇」。
- 這個 harness 先證明：錯誤候選能被合約規則穩定標出，後續才值得訓練 selector 或 verifier。

## 被檢出的錯誤候選

| 錯誤 | 數量 |
|---|---:|
| ascii_leak | 722 |
| polite_tone_drift | 361 |
| chinese_leak | 360 |
| forbidden_marker | 360 |
| instruction_or_plan_leak | 360 |
| nonstandard_cjk_surface | 360 |
| required_marker_missing | 360 |
| over_max_chars | 356 |

## 抽樣個案

| case | selected | gold | errors | text |
|---|---|---|---|---|
| rb_repair_selection_v1_0001 | rb_repair_curriculum_v1_0348_cand_gold | rb_repair_curriculum_v1_0348_cand_gold | none | 肩痛きついなら無理に話すな。休め。 |
| rb_repair_selection_v1_0002 | rb_repair_curriculum_v1_0679_cand_gold | rb_repair_curriculum_v1_0679_cand_gold | none | 暗示っぽく刺したのは分かる。言うならはっきり言え。 |
| rb_repair_selection_v1_0003 | rb_repair_curriculum_v1_0275_cand_gold | rb_repair_curriculum_v1_0275_cand_gold | none | 悠斗、おやすみ。急に振るなって。 |
| rb_repair_selection_v1_0004 | rb_repair_curriculum_v1_0039_cand_gold | rb_repair_curriculum_v1_0039_cand_gold | none | たこ焼きなら少し食べる。今それでいい。 |
| rb_repair_selection_v1_0005 | rb_repair_curriculum_v1_0171_cand_gold | rb_repair_curriculum_v1_0171_cand_gold | none | ゲーム挿入歌の話なら、何の作品か曲名どれ？ |
| rb_repair_selection_v1_0006 | rb_repair_curriculum_v1_0554_cand_gold | rb_repair_curriculum_v1_0554_cand_gold | none | 暗示で刺したのは分かる。言うならはっきり言え。 |
| rb_repair_selection_v1_0007 | rb_repair_curriculum_v1_0273_cand_gold | rb_repair_curriculum_v1_0273_cand_gold | none | 病院予約前に不安なのは分かる。一つずつ確認しろ。 |
| rb_repair_selection_v1_0008 | rb_repair_curriculum_v1_0053_cand_gold | rb_repair_curriculum_v1_0053_cand_gold | none | 一人で閉じる前に止まれ。誰かに連絡しろ。 |
| rb_repair_selection_v1_0009 | rb_repair_curriculum_v1_0135_cand_gold | rb_repair_curriculum_v1_0135_cand_gold | none | 悠って何だよ。そこを先に言え。 |
| rb_repair_selection_v1_0010 | rb_repair_curriculum_v1_0519_cand_gold | rb_repair_curriculum_v1_0519_cand_gold | none | 山から魚は生えないだろ。何の発想だよ。 |
| rb_repair_selection_v1_0011 | rb_repair_curriculum_v1_0486_cand_gold | rb_repair_curriculum_v1_0486_cand_gold | none | 既読で返事が止まると不安になるよな。けど、自分がうるさいって決めつけるのは早い。 |
| rb_repair_selection_v1_0012 | rb_repair_curriculum_v1_0089_cand_gold | rb_repair_curriculum_v1_0089_cand_gold | none | スマホを切る前に止まれ。一人で決めず誰かに連絡しろ。 |
