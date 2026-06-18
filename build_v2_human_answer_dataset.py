import json
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(BASE_DIR, 'v2_human_answer_dataset.json')
SEED = 20260408
rng = random.Random(SEED)


def make_case(category, language, prompt, expected_modes, expected_intents=None, note=''):
    return {
        'category': category,
        'language': language,
        'prompt': prompt,
        'expected_response_modes': expected_modes,
        'expected_intents': expected_intents or [],
        'note': note,
    }


def unique_extend(target, seen, cases):
    for case in cases:
        key = (case['language'], case['prompt'].strip())
        if key in seen:
            continue
        seen.add(key)
        target.append(case)


def direct_smalltalk_cases():
    cases = []
    zh_leads = ['欸', '老實說', '現在', '今天']
    zh_topics = ['你在幹嘛', '你今天都在做什麼', '你是誰', '介紹一下你自己', '早安', '我現在有點無聊', '誇我一下', '你今天有空嗎']
    en_leads = ['hey', 'honestly', 'right now', 'today']
    en_topics = ['what are you doing', 'what did you do today', 'who are you', 'introduce yourself', 'good morning', 'i am kinda bored', 'praise me a bit', 'are you free today']
    ja_leads = ['なあ', '正直', '今', '今日']
    ja_topics = ['今何してる', '今日何してた', 'お前誰', '自己紹介して', 'おはよう', 'ちょっと暇だわ', '少し褒めて', '今日空いてる']
    for lead in zh_leads:
        for topic in zh_topics:
            cases.append(make_case('direct_smalltalk', 'zh', f'{lead}{topic}。', ['direct_answer', 'direct_answer_with_hedge']))
    for lead in en_leads:
        for topic in en_topics:
            cases.append(make_case('direct_smalltalk', 'en', f'{lead}, {topic}?', ['direct_answer', 'direct_answer_with_hedge']))
    for lead in ja_leads:
        for topic in ja_topics:
            cases.append(make_case('direct_smalltalk', 'ja', f'{lead}{topic}。', ['direct_answer', 'direct_answer_with_hedge']))
    return cases


def direct_daily_cases():
    cases = []
    zh_states = ['我今天很累', '我肚子餓了', '我剛下班', '我感冒了', '我遲到了', '我剛跌倒', '我今天超想睡', '我現在很煩躁']
    en_states = ['i am exhausted today', 'i am hungry', 'i just got off work', 'i think i caught a cold', 'i am late', 'i just fell down', 'i am so sleepy', 'i am irritated right now']
    ja_states = ['今日かなり疲れた', '腹減った', '今仕事終わった', '風邪っぽい', '遅刻した', 'さっき転んだ', '今めっちゃ眠い', '今かなりイライラしてる']
    zh_leads = ['欸', '老實說', '剛剛', '現在']
    en_leads = ['hey', 'honestly', 'just now', 'right now']
    ja_leads = ['なあ', '正直', 'さっき', '今']
    for lead in zh_leads:
        for state in zh_states:
            cases.append(make_case('direct_daily_state', 'zh', f'{lead}{state}。', ['direct_answer', 'direct_answer_with_hedge']))
    for lead in en_leads:
        for state in en_states:
            cases.append(make_case('direct_daily_state', 'en', f'{lead}, {state}.', ['direct_answer', 'direct_answer_with_hedge']))
    for lead in ja_leads:
        for state in ja_states:
            cases.append(make_case('direct_daily_state', 'ja', f'{lead}{state}。', ['direct_answer', 'direct_answer_with_hedge']))
    return cases


def direct_relationship_cases():
    cases = []
    zh_topics = ['你有想我嗎', '可以叫你 Uruha 嗎', '我去看別的 vtuber 你會介意嗎', '我今天不來你會注意到嗎', '你會不會覺得我很煩', '你有生氣嗎']
    en_topics = ['do you miss me', 'can i call you Uruha', 'would you care if i watch another vtuber', 'would you notice if i did not show up today', 'do you think i am annoying', 'are you mad at me']
    ja_topics = ['うちのこと少しは思い出す', 'うるはって呼んでいい', '別の Vtuber 見ても気にする', '今日来なかったら気づく', 'うちのことだるいと思う', '怒ってる']
    zh_leads = ['欸', '老實說', '現在']
    en_leads = ['hey', 'honestly', 'right now']
    ja_leads = ['なあ', '正直', '今']
    for lead in zh_leads:
        for topic in zh_topics:
            cases.append(make_case('direct_relationship', 'zh', f'{lead}{topic}？', ['direct_answer', 'direct_answer_with_hedge']))
    for lead in en_leads:
        for topic in en_topics:
            cases.append(make_case('direct_relationship', 'en', f'{lead}, {topic}?', ['direct_answer', 'direct_answer_with_hedge']))
    for lead in ja_leads:
        for topic in ja_topics:
            cases.append(make_case('direct_relationship', 'ja', f'{lead}{topic}？', ['direct_answer', 'direct_answer_with_hedge']))
    return cases


def direct_offer_cases():
    cases = []
    zh_topics = ['你要不要吃蘋果派', '我等等買飲料給你好不好', '我去便利商店要幫你帶東西嗎', '我剛買了奶昔要分你一口嗎', '我剛做了咖哩你要不要吃']
    en_topics = ['do you want some apple pie', 'should i grab you a drink later', 'i am going to the convenience store want anything', 'i just bought a milkshake want a sip', 'i made curry do you want some']
    ja_topics = ['アップルパイいる', 'あとで飲み物買ってこうか', 'コンビニ行くけど何かいる', 'さっきミルクシェイク買ったけど一口いる', 'カレー作ったけど食べる']
    zh_leads = ['欸', '那', '如果我順路']
    en_leads = ['hey', 'so', 'if i stop by later']
    ja_leads = ['なあ', 'じゃあ', '帰りに']
    for lead in zh_leads:
        for topic in zh_topics:
            cases.append(make_case('direct_offer', 'zh', f'{lead}{topic}？', ['direct_answer', 'direct_answer_with_hedge']))
    for lead in en_leads:
        for topic in en_topics:
            cases.append(make_case('direct_offer', 'en', f'{lead}, {topic}?', ['direct_answer', 'direct_answer_with_hedge']))
    for lead in ja_leads:
        for topic in ja_topics:
            cases.append(make_case('direct_offer', 'ja', f'{lead}{topic}？', ['direct_answer', 'direct_answer_with_hedge']))
    return cases


def hedge_direct_cases():
    cases = []
    zh = ['你大概會介意我晚點再來吧', '你應該有點想我吧', '你現在大概在耍廢吧', '你應該會想吃點甜的吧']
    en = ['you probably miss me a little right', 'you are probably just chilling right now', 'you would maybe want something sweet right', 'you probably would notice if i was gone right']
    ja = ['少しは思い出してるだろ', '今だらだらしてる感じだろ', '甘いのちょっと欲しい方だろ', '今日来なかったら少しは気づくだろ']
    for p in zh:
        cases.append(make_case('hedged_direct', 'zh', p + '？', ['direct_answer_with_hedge', 'direct_answer']))
    for p in en:
        cases.append(make_case('hedged_direct', 'en', p + '?', ['direct_answer_with_hedge', 'direct_answer']))
    for p in ja:
        cases.append(make_case('hedged_direct', 'ja', p + '？', ['direct_answer_with_hedge', 'direct_answer']))
    return cases


def repair_requested_cases():
    cases = []
    zh = ['你剛剛說的那個到底是指哪個', '你現在說的那件事是哪件', '你剛剛那個我聽不懂你是指哪塊']
    en = ['which one are you talking about exactly', 'what part do you mean by that one', 'which thing from earlier do you mean']
    ja = ['今のってどの話だよ', 'さっきのどれのこと言ってるんだ', '今のって何の話だよ']
    for p in zh:
        cases.append(make_case('repair_requested', 'zh', p + '？', ['direct_answer', 'direct_answer_with_hedge']))
    for p in en:
        cases.append(make_case('repair_requested', 'en', p + '?', ['direct_answer', 'direct_answer_with_hedge']))
    for p in ja:
        cases.append(make_case('repair_requested', 'ja', p + '？', ['direct_answer', 'direct_answer_with_hedge']))
    return cases


def clarify_cases():
    cases = []
    zh = ['那個呢', '你說哪個', '剛剛那個是什麼', '你在說哪件事']
    en = ['that one?', 'which one?', 'what do you mean exactly by that', 'which thing are you talking about']
    ja = ['あれは', 'どれだよ', '今のどっちだよ', '何のことだよ']
    for p in zh:
        cases.append(make_case('clarify_needed', 'zh', p + '？', ['clarify_light']))
    for p in en:
        cases.append(make_case('clarify_needed', 'en', p + '?', ['clarify_light']))
    for p in ja:
        cases.append(make_case('clarify_needed', 'ja', p + '？', ['clarify_light']))
    return cases


def premise_cases():
    cases = []
    zh = ['你不是在北海道長大的嗎', '你去年不是結婚了嗎', '你不是會彈鋼琴嗎', '你不是跟別的 vtuber 同居過嗎']
    en = ['you grew up in hokkaido right', 'you got married last year right', 'you play piano right', 'you used to live with another vtuber right']
    ja = ['北海道育ちだったよな', '去年結婚してたよな', 'ピアノ弾けるんだよな', '別の vtuber と同居してたよな']
    for p in zh:
        cases.append(make_case('premise_challenge_needed', 'zh', p + '？', ['premise_challenge']))
    for p in en:
        cases.append(make_case('premise_challenge_needed', 'en', p + '?', ['premise_challenge']))
    for p in ja:
        cases.append(make_case('premise_challenge_needed', 'ja', p + '？', ['premise_challenge']))
    return cases


def reframe_cases():
    cases = []
    zh = [
        '你幫我把 attention 機制、量化、推理延遲一次完整講完',
        '把歷史脈絡、API error、tokenizer 全部整理成一個答案',
        '從數學、程式、系統 prompt 三個角度一起講清楚',
    ]
    en = [
        'explain attention quantization and inference latency in one complete answer',
        'walk through api errors tokenizer and system prompts all at once',
        'give me the math coding and deployment angle together in one go',
    ]
    ja = [
        'attention と量子化と推論遅延を一個の答えで全部言え',
        'api error と tokenizer と system prompt をまとめて話せ',
        '数学とコードと運用の観点を一気に全部説明しろ',
    ]
    for p in zh:
        cases.append(make_case('reframe_needed', 'zh', p + '。', ['reframe_large_question']))
    for p in en:
        cases.append(make_case('reframe_needed', 'en', p + '.', ['reframe_large_question']))
    for p in ja:
        cases.append(make_case('reframe_needed', 'ja', p + '。', ['reframe_large_question']))
    return cases


def build_dataset():
    categories = [
        direct_smalltalk_cases,
        direct_daily_cases,
        direct_relationship_cases,
        direct_offer_cases,
        hedge_direct_cases,
        repair_requested_cases,
        clarify_cases,
        premise_cases,
        reframe_cases,
    ]
    dataset = []
    seen = set()
    for fn in categories:
        unique_extend(dataset, seen, fn())
    rng.shuffle(dataset)
    for idx, row in enumerate(dataset, 1):
        row['id'] = idx
    return dataset


def main():
    dataset = build_dataset()
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    lang_counts = {}
    cat_counts = {}
    for row in dataset:
        lang_counts[row['language']] = lang_counts.get(row['language'], 0) + 1
        cat_counts[row['category']] = cat_counts.get(row['category'], 0) + 1
    print(json.dumps({
        'out_path': OUT_PATH,
        'total_cases': len(dataset),
        'unique_prompts': len({(r['language'], r['prompt']) for r in dataset}),
        'languages': lang_counts,
        'categories': cat_counts,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
