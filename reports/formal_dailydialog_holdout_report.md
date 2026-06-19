# Formal DailyDialog Holdout Report

- generated_at: 2026-06-19T12:24:04
- sample_size: 200
- source: DailyDialog official test split via the v2 benchmark loader
- scope: utterance-level act/emotion interpretation, not final chat generation
- best_by_act_accuracy: interpreter_v6
- best_by_emotion_accuracy: interpreter_v5

## Summary

| labeler | act accuracy | act macro-F1 | emotion accuracy | emotion supported macro-F1 | emotion macro-F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| interpreter_v4 | 0.765 | 0.7625 | 0.825 | 0.5198 | 0.3713 |
| interpreter_v5 | 0.755 | 0.7537 | 0.83 | 0.4995 | 0.3568 |
| interpreter_v6 | 0.775 | 0.7735 | 0.82 | 0.462 | 0.33 |

## Label Meaning

- Act labels: 1=inform, 2=question, 3=directive, 4=commissive
- Emotion labels: 0=none, 1=anger, 2=disgust, 3=fear, 4=happiness, 5=sadness, 6=surprise

## Main Error Patterns

### interpreter_v4

Act confusion pairs:
- directive -> commissive: 11
- inform -> commissive: 6
- directive -> inform: 6
- commissive -> inform: 6
- inform -> directive: 5
- commissive -> directive: 5
- directive -> question: 3
- question -> directive: 2

Emotion confusion pairs:
- none -> happiness: 12
- happiness -> none: 10
- none -> anger: 3
- none -> sadness: 2
- sadness -> none: 2
- none -> surprise: 2
- sadness -> happiness: 1
- surprise -> none: 1

### interpreter_v5

Act confusion pairs:
- directive -> commissive: 11
- commissive -> inform: 10
- inform -> commissive: 7
- directive -> inform: 5
- commissive -> directive: 4
- inform -> directive: 3
- question -> directive: 3
- directive -> question: 3

Emotion confusion pairs:
- none -> happiness: 13
- happiness -> none: 9
- surprise -> none: 4
- none -> anger: 2
- sadness -> none: 2
- none -> sadness: 1
- anger -> none: 1
- surprise -> happiness: 1

### interpreter_v6

Act confusion pairs:
- directive -> commissive: 11
- inform -> commissive: 9
- directive -> inform: 5
- commissive -> inform: 4
- commissive -> directive: 4
- inform -> directive: 3
- question -> directive: 3
- directive -> question: 3

Emotion confusion pairs:
- none -> happiness: 13
- happiness -> none: 9
- none -> anger: 3
- sadness -> none: 3
- surprise -> none: 3
- none -> sadness: 2
- anger -> none: 1
- surprise -> happiness: 1

## Example Misses

### interpreter_v4

| type | gold | pred | utterance | rule |
| --- | --- | --- | --- | --- |
| act | inform | commissive | OK . Here you are . | v2_accept_permission_or_service_fulfillment |
| act | inform | directive | Whatever . Just make sure you go vote . | v2_service_goal_instruction_or_request |
| act | inform | commissive | Yes , Madam . The reporting desk for the British Airway's flight to London is over there . | v2_service_answer_or_commitment |
| act | inform | directive | I want to buy a V-neck checked sweater , and it should be tight . | v2_service_goal_instruction_or_request |
| act | inform | question | Milk ? I thought you didn't like milk . | question_mark_default |
| emotion | none | anger | Now with video rentals it's all a personal matter . | v2_anger_frustration_or_rebuke |
| emotion | happiness | none | It is OK with me . I enjoy being busy and learning new things . | emotion_default_none |
| emotion | sadness | happiness | I ’ m sure they are . Oh , and a local man won the lottery . I ’ m so jealous ! I wish it were me ! I buy a lottery ticket every week and I ’ m amazed that I haven ’ t even won a small prize yet . It ’ s so unfair ! | happiness_lexical |
| emotion | none | happiness | You have a lovely house , Jack . | happiness_lexical |
| emotion | none | happiness | Great ! And remember , a taxi , not a limo . | happiness_lexical |

### interpreter_v5

| type | gold | pred | utterance | rule |
| --- | --- | --- | --- | --- |
| act | inform | commissive | OK . Here you are . | v5_train_retrieval_act:commissive |
| act | inform | directive | Whatever . Just make sure you go vote . | v2_service_goal_instruction_or_request |
| act | inform | commissive | Yes , Madam . The reporting desk for the British Airway's flight to London is over there . | v2_service_answer_or_commitment |
| act | inform | directive | I want to buy a V-neck checked sweater , and it should be tight . | v2_service_goal_instruction_or_request |
| act | inform | commissive | Oh , great idea ! | v5_train_retrieval_act:commissive |
| emotion | none | anger | Now with video rentals it's all a personal matter . | v2_anger_frustration_or_rebuke |
| emotion | happiness | none | It is OK with me . I enjoy being busy and learning new things . | v5_train_retrieval_emotion:none |
| emotion | sadness | none | I ’ m sure they are . Oh , and a local man won the lottery . I ’ m so jealous ! I wish it were me ! I buy a lottery ticket every week and I ’ m amazed that I haven ’ t even won a small prize yet . It ’ s so unfair ! | v5_train_retrieval_emotion:none |
| emotion | none | happiness | Great ! And remember , a taxi , not a limo . | happiness_lexical |
| emotion | surprise | none | Milk ? I thought you didn't like milk . | emotion_default_none |

### interpreter_v6

| type | gold | pred | utterance | rule |
| --- | --- | --- | --- | --- |
| act | inform | commissive | OK . Here you are . | v2_accept_permission_or_service_fulfillment |
| act | inform | directive | Whatever . Just make sure you go vote . | v2_service_goal_instruction_or_request |
| act | inform | commissive | Yes , Madam . The reporting desk for the British Airway's flight to London is over there . | v2_service_answer_or_commitment |
| act | inform | directive | I want to buy a V-neck checked sweater , and it should be tight . | v2_service_goal_instruction_or_request |
| act | inform | commissive | Oh , great idea ! | v6_gated_v5_train_retrieval_act:commissive |
| emotion | none | anger | Now with video rentals it's all a personal matter . | v2_anger_frustration_or_rebuke |
| emotion | happiness | none | It is OK with me . I enjoy being busy and learning new things . | emotion_default_none |
| emotion | sadness | none | I ’ m sure they are . Oh , and a local man won the lottery . I ’ m so jealous ! I wish it were me ! I buy a lottery ticket every week and I ’ m amazed that I haven ’ t even won a small prize yet . It ’ s so unfair ! | v6_gated_v5_train_retrieval_emotion:none |
| emotion | none | happiness | Great ! And remember , a taxi , not a limo . | happiness_lexical |
| emotion | surprise | none | Milk ? I thought you didn't like milk . | emotion_default_none |

## Reproduction

```bash
python run_formal_dailydialog_holdout_eval.py --sample-size 200
```

