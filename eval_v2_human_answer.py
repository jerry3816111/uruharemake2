import json
import os
import re
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, 'Style-Bert-VITS2', 'venv', 'bin', 'python')
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))
DATASET_PATH = os.path.join(BASE_DIR, 'v2_human_answer_dataset.json')
REPORT_PATH = os.path.join(BASE_DIR, 'v2_human_answer_report.json')


def _ensure_project_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ('PYTHONHOME', 'PYTHONPATH', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV'):
            clean_env.pop(key, None)
        clean_env['VIRTUAL_ENV'] = EXPECTED_VENV
        clean_env['PATH'] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get('PATH', '')
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_project_python()

from uruha_brain_mac import LeftBrain


def role_similarity(plan):
    score = 3
    if plan.get('response_mode') in {'direct_answer', 'direct_answer_with_hedge'}:
        score += 1
    if plan.get('scene') in {'casual', 'support', 'jealousy', 'boundary'}:
        score += 1
    return max(1, min(5, score))


def rate(rows, key):
    if not rows:
        return 0.0
    return round(sum(r[key] for r in rows) / len(rows), 4)


def main():
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    left = LeftBrain.__new__(LeftBrain)
    psyche = {'mood': 0, 'trust': 50}
    mem = {'profile_structured': {}, 'recent_turns': []}
    results = []

    for idx, case in enumerate(dataset, 1):
        logic = left._rule_based_plan(case['prompt'], psyche, mem)
        if logic is None:
            logic = left._fallback_plan()
        response_mode = logic.get('response_mode', 'direct_answer')
        is_direct_expected = any(m in {'direct_answer', 'direct_answer_with_hedge'} for m in case['expected_response_modes'])
        over_reframe = int(is_direct_expected and response_mode in {'clarify_light', 'premise_challenge', 'reframe_large_question'})
        over_challenge = int(is_direct_expected and response_mode == 'premise_challenge')
        mode_match = int(response_mode in case['expected_response_modes'])
        intent_match = int(not case['expected_intents'] or logic.get('intent') in case['expected_intents'])
        results.append({
            **case,
            'logic': logic,
            'response_mode_match': mode_match,
            'intent_match': intent_match,
            'over_reframe': over_reframe,
            'over_challenge': over_challenge,
            'role_similarity': role_similarity(logic),
        })
        if idx % 200 == 0:
            print(f'[{idx:04d}/{len(dataset)}] mode={response_mode} category={case["category"]}')

    by_cat = defaultdict(list)
    by_lang = defaultdict(list)
    direct_rows = []
    premise_rows = []
    reframe_rows = []
    clarify_rows = []
    for row in results:
        by_cat[row['category']].append(row)
        by_lang[row['language']].append(row)
        if any(m in {'direct_answer', 'direct_answer_with_hedge'} for m in row['expected_response_modes']):
            direct_rows.append(row)
        if 'premise_challenge' in row['expected_response_modes']:
            premise_rows.append(row)
        if 'reframe_large_question' in row['expected_response_modes']:
            reframe_rows.append(row)
        if 'clarify_light' in row['expected_response_modes']:
            clarify_rows.append(row)

    summary = {
        'mode': 'controller_v2_over_reframe_eval',
        'total_cases': len(results),
        'mode_match_rate': rate(results, 'response_mode_match'),
        'intent_match_rate': rate(results, 'intent_match'),
        'direct_answer_rate_on_simple_queries': rate(direct_rows, 'response_mode_match'),
        'over_reframe_rate': rate(direct_rows, 'over_reframe'),
        'over_challenge_rate': rate(direct_rows, 'over_challenge'),
        'premise_challenge_precision': rate(premise_rows, 'response_mode_match'),
        'reframe_precision': rate(reframe_rows, 'response_mode_match'),
        'clarify_precision': rate(clarify_rows, 'response_mode_match'),
        'avg_role_similarity_1_to_5': round(sum(r['role_similarity'] for r in results) / len(results), 3),
        'language_breakdown': {
            lang: {
                'count': len(rows),
                'mode_match_rate': rate(rows, 'response_mode_match'),
                'intent_match_rate': rate(rows, 'intent_match'),
            }
            for lang, rows in by_lang.items()
        },
        'category_breakdown': {
            cat: {
                'count': len(rows),
                'mode_match_rate': rate(rows, 'response_mode_match'),
                'intent_match_rate': rate(rows, 'intent_match'),
                'over_reframe_rate': rate(rows, 'over_reframe'),
            }
            for cat, rows in by_cat.items()
        },
        'worst_cases': [
            {
                'category': row['category'],
                'language': row['language'],
                'prompt': row['prompt'],
                'expected_response_modes': row['expected_response_modes'],
                'response_mode': row['logic'].get('response_mode'),
                'intent': row['logic'].get('intent'),
                'core_message_jp': row['logic'].get('core_message_jp'),
            }
            for row in sorted(results, key=lambda r: (r['response_mode_match'], r['intent_match'], r['over_reframe']), reverse=False)[:60]
        ],
    }

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump({'dataset_path': DATASET_PATH, 'summary': summary, 'results': results}, f, ensure_ascii=False, indent=2)
    print(REPORT_PATH)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
