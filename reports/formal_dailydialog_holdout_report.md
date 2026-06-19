# Formal DailyDialog Holdout Report

- generated_at: 2026-06-19T12:31:07
- sample_size: 200
- source: DailyDialog official test split via the v2 benchmark loader
- scope: utterance-level act/emotion interpretation, not final chat generation
- best_by_act_accuracy: interpreter_v4
- best_by_emotion_accuracy: interpreter_v4

## Summary

| labeler | act accuracy | act macro-F1 | emotion accuracy | emotion supported macro-F1 | emotion macro-F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| interpreter_v4 | 0.965 | 0.9651 | 1.0 | 1.0 | 0.7143 |
| interpreter_v5 | 0.89 | 0.8902 | 0.93 | 0.7936 | 0.5668 |
| interpreter_v6 | 0.93 | 0.9298 | 0.955 | 0.9121 | 0.6515 |

## Label Meaning

- Act labels: 1=inform, 2=question, 3=directive, 4=commissive
- Emotion labels: 0=none, 1=anger, 2=disgust, 3=fear, 4=happiness, 5=sadness, 6=surprise

## Main Error Patterns

### interpreter_v4

Act confusion pairs:
- inform -> directive: 2
- question -> inform: 1
- question -> directive: 1
- directive -> inform: 1
- directive -> question: 1
- commissive -> inform: 1

Emotion confusion pairs:
- none

### interpreter_v5

Act confusion pairs:
- commissive -> inform: 8
- inform -> commissive: 5
- question -> directive: 3
- inform -> directive: 2
- question -> inform: 1
- directive -> inform: 1
- directive -> question: 1
- commissive -> directive: 1

Emotion confusion pairs:
- happiness -> none: 6
- none -> happiness: 3
- surprise -> none: 3
- sadness -> none: 1
- anger -> none: 1

### interpreter_v6

Act confusion pairs:
- inform -> commissive: 5
- question -> directive: 3
- inform -> directive: 2
- question -> inform: 1
- directive -> inform: 1
- directive -> question: 1
- commissive -> directive: 1

Emotion confusion pairs:
- happiness -> none: 4
- none -> happiness: 3
- surprise -> none: 2

## Example Misses

### interpreter_v4

| type | gold | pred | utterance | rule |
| --- | --- | --- | --- | --- |
| act | inform | directive | Whatever . Just make sure you go vote . | v2_service_goal_instruction_or_request |
| act | inform | directive | I want to buy a V-neck checked sweater , and it should be tight . | v2_service_goal_instruction_or_request |
| act | question | inform | I am a fireman and it is a dangerous job . I have to consider your mother's life . | default_inform |
| act | question | directive | The bartender just gave the last call . Let's order another round , okay ? | lets_directive_question |
| act | directive | inform | Oh , well this one has the , uh . | default_inform |

### interpreter_v5

| type | gold | pred | utterance | rule |
| --- | --- | --- | --- | --- |
| act | inform | commissive | OK . Here you are . | v5_train_retrieval_act:commissive |
| act | inform | directive | Whatever . Just make sure you go vote . | v2_service_goal_instruction_or_request |
| act | inform | directive | I want to buy a V-neck checked sweater , and it should be tight . | v2_service_goal_instruction_or_request |
| act | inform | commissive | Oh , great idea ! | v5_train_retrieval_act:commissive |
| act | inform | commissive | Here you are . | v5_train_retrieval_act:commissive |
| emotion | happiness | none | It is OK with me . I enjoy being busy and learning new things . | v5_train_retrieval_emotion:none |
| emotion | sadness | none | I ’ m sure they are . Oh , and a local man won the lottery . I ’ m so jealous ! I wish it were me ! I buy a lottery ticket every week and I ’ m amazed that I haven ’ t even won a small prize yet . It ’ s so unfair ! | v5_train_retrieval_emotion:none |
| emotion | none | happiness | Thanks for letting me know . | v5_train_retrieval_emotion:happiness |
| emotion | happiness | none | Yeah , I go a lot too . I saw a bear and a mountain lion on my last hike . | v5_train_retrieval_emotion:none |
| emotion | none | happiness | some time next year . We haven't set the date yet . | v5_train_retrieval_emotion:happiness |

### interpreter_v6

| type | gold | pred | utterance | rule |
| --- | --- | --- | --- | --- |
| act | inform | commissive | OK . Here you are . | v6_gated_v5_train_retrieval_act:commissive |
| act | inform | directive | Whatever . Just make sure you go vote . | v2_service_goal_instruction_or_request |
| act | inform | directive | I want to buy a V-neck checked sweater , and it should be tight . | v2_service_goal_instruction_or_request |
| act | inform | commissive | Oh , great idea ! | v6_gated_v5_train_retrieval_act:commissive |
| act | inform | commissive | Here you are . | v6_gated_v5_train_retrieval_act:commissive |
| emotion | happiness | none | It is OK with me . I enjoy being busy and learning new things . | v6_gated_v5_train_retrieval_emotion:none |
| emotion | none | happiness | Thanks for letting me know . | v6_gated_v5_train_retrieval_emotion:happiness |
| emotion | happiness | none | Yeah , I go a lot too . I saw a bear and a mountain lion on my last hike . | v6_gated_v5_train_retrieval_emotion:none |
| emotion | none | happiness | some time next year . We haven't set the date yet . | v6_gated_v5_train_retrieval_emotion:happiness |
| emotion | happiness | none | Here comes Jordan , though . | v6_gated_v5_train_retrieval_emotion:none |

## Reproduction

```bash
python run_formal_dailydialog_holdout_eval.py --sample-size 200
```

