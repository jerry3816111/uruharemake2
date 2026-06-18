import json
import os
import tempfile

import uruha_brain_mac as brain_mod

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(BASE_DIR, 'long_dialogue_memory_report.json')

FILLERS = {
    'zh': ['今天有點累。', '你有想我嗎？', '我回來了。', '你要不要吃蘋果派？'],
    'en': ["I'm exhausted today.", 'Did you miss me?', "I'm back.", 'Do you want some apple pie?'],
    'ja': ['今日ちょっとしんどい。', 'うちのこと少しは恋しかった？', 'ただいま。', 'アップルパイいる？'],
}


def build_cases():
    cases = []
    idx = 0
    specs = [
        ('name_recall', {
            'zh': ('叫我小傑。', '你還記得我叫什麼嗎？', ['小傑']),
            'en': ('Call me Jerry.', "What's my name?", ['jerry']),
            'ja': ('ジェリーって呼んで。', 'うちの名前覚えてる？', ['ジェリー']),
        }),
        ('favorite_recall', {
            'zh': ('我最喜歡草莓牛奶。', '你記得我最喜歡什麼嗎？', ['草莓牛奶']),
            'en': ('My favorite drink is strawberry milk.', 'Do you remember my favorite drink?', ['strawberry milk']),
            'ja': ('いちごミルクが一番好き。', 'うちの一番好きなの覚えてる？', ['いちごミルク']),
        }),
        ('dislike_recall', {
            'zh': ('我討厭吃辣。', '那我討厭什麼來著？', ['辣']),
            'en': ('I hate spicy food.', 'What do I hate again?', ['spicy']),
            'ja': ('辛いの嫌い。', 'うち何が嫌いって言ってたっけ？', ['辛い']),
        }),
        ('recent_action_recall', {
            'zh': ('我先去洗澡。', '我剛剛說我要去幹嘛？', ['風呂', '洗澡']),
            'en': ("I'm going to shower.", 'What did I just say I was going to do?', ['風呂', 'shower']),
            'ja': ('風呂入ってくる。', 'さっき何するって言ったっけ？', ['風呂', '入って']),
        }),
    ]
    for category, examples in specs:
        for lang in ['zh', 'en', 'ja']:
            idx += 1
            intro, query, expected = examples[lang]
            cases.append({
                'id': idx,
                'category': category,
                'language': lang,
                'intro': intro,
                'query': query,
                'expected': expected,
                'fillers': FILLERS[lang],
            })
    return cases


def contains_expected(reply, expected):
    lowered = reply.lower()
    return any(token.lower() in lowered for token in expected)


def profile_captured(memory, category, expected):
    profile = memory.session_profile
    values = []
    if category == 'name_recall' and profile.get('name'):
        values = [profile['name']]
    elif category == 'favorite_recall':
        values = profile.get('favorites', []) + profile.get('likes', [])
    elif category == 'dislike_recall':
        values = profile.get('dislikes', [])
    return any(any(token.lower() in value.lower() for token in expected) for value in values)


def simulate_user_turn(brain, utterance):
    brain.memory.save_episode(utterance, '', brain.psyche.get_state(), {'intent': 'chat', 'scene': 'casual', 'jp_summary': utterance})


def main():
    cases = build_cases()
    brain = brain_mod.UruhaBrainV4_Mac()
    brain.memory.reflect_experience = lambda *_args, **_kwargs: None
    results = []

    for case in cases:
        tempdir = tempfile.mkdtemp(prefix='uruha_long_memory_eval_')
        brain.reset_session(db_path=tempdir)
        brain.memory.reflect_experience = lambda *_args, **_kwargs: None

        simulate_user_turn(brain, case['intro'])
        captured = profile_captured(brain.memory, case['category'], case['expected'])
        for filler in case['fillers']:
            simulate_user_turn(brain, filler)

        mems = brain.memory.query_all_layers(case['query'])
        logic = brain.left_brain._rule_based_plan(case['query'], brain.psyche.get_state(), mems)
        reply = brain.right_brain._template_reply(logic, user_input=case['query'], current_psyche=brain.psyche.get_state(), memory_data=mems)
        results.append({
            **case,
            'logic_intent': logic['intent'],
            'profile_captured': captured if case['category'] != 'recent_action_recall' else None,
            'reply': reply,
            'recall_success': contains_expected(reply, case['expected']),
        })

    summary = {
        'total_cases': len(results),
        'delayed_recall_rate': round(sum(r['recall_success'] for r in results) / len(results), 4),
        'profile_capture_rate': round(
            sum(r['profile_captured'] for r in results if r['profile_captured'] is not None)
            / max(1, len([r for r in results if r['profile_captured'] is not None])),
            4,
        ),
        'by_category': {},
        'by_language': {},
    }

    for category in sorted(set(r['category'] for r in results)):
        rows = [r for r in results if r['category'] == category]
        summary['by_category'][category] = {
            'count': len(rows),
            'delayed_recall_rate': round(sum(r['recall_success'] for r in rows) / len(rows), 4),
            'profile_capture_rate': round(
                sum(r['profile_captured'] for r in rows if r['profile_captured'] is not None)
                / max(1, len([r for r in rows if r['profile_captured'] is not None])),
                4,
            ) if any(r['profile_captured'] is not None for r in rows) else None,
        }

    for language in sorted(set(r['language'] for r in results)):
        rows = [r for r in results if r['language'] == language]
        summary['by_language'][language] = {
            'count': len(rows),
            'delayed_recall_rate': round(sum(r['recall_success'] for r in rows) / len(rows), 4),
        }

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump({'summary': summary, 'results': results}, f, ensure_ascii=False, indent=2)
    print(REPORT_PATH)


if __name__ == '__main__':
    main()
