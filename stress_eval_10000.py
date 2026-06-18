import json
import os
import re
import sys
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_project_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_project_python()

import uruha_brain_mac as brain_mod

DATASET_PATH = os.path.join(BASE_DIR, 'stress_eval_dataset_10000.json')
REPORT_PATH = os.path.join(BASE_DIR, 'stress_eval_report_10000.json')

PERSONA_BAD = ['私', 'わかりました', '承知', 'かしこまり', 'assistant', 'AIとして', 'サポート']
POLITE_BAD = ['です。', 'ます。', 'でしょう', 'くださいませ']


class MemoryState:
    def __init__(self):
        self.session_turns = []
        self.session_profile = {
            'name': None,
            'likes': [],
            'dislikes': [],
            'favorites': [],
        }

    def _clean_fact_value(self, value):
        value = re.sub(r"^[\s:=：,，.。!?！？'\"`]+|[\s:=：,，.。!?！？'\"`]+$", '', value)
        value = re.sub(r"\s+", ' ', value).strip()
        return value[:32]

    def _extract_profile_facts(self, user_input):
        text = user_input.strip()
        lowered = text.lower()
        facts = []
        patterns = [
            ('name', [r'(?:my name is|call me|use the name|you can call me|please call me|i want you to call me)\s+([a-z0-9_\-]{2,20})']),
            ('name', [r'(?:use the name)\s+([a-z0-9_\-]{2,20})\s+for me']),
            ('name', [r'(?:我叫|叫我|你可以叫我|請叫我|请叫我|稱呼我|称呼我)([^\s，。！？?]{1,20})']),
            ('name', [r'([^\s、。！？?]{1,20})って呼んで', r'([^\s、。！？?]{1,20})と呼んで', r'([^\s、。！？?]{1,20})って呼んでね', r'(?:名前は|名前)([^\s、。！？?]{1,20})']),
            ('favorite', [r'(?:my favorite(?: drink| food| snack)? is)\s+([a-z0-9 \-]{2,30})']),
            ('favorite', [r'(?:我最喜歡|我最喜欢)([^，。！？?]{1,20})']),
            ('favorite', [r'(.{1,20})(?:が一番好き|が好き一番)']),
            ('like', [r'(?:i (?:really )?(?:like|love))\s+([a-z0-9 \-]{2,30})']),
            ('like', [r'(?:我喜歡|我喜欢|我愛|我爱)([^，。！？?]{1,20})']),
            ('like', [r'(.{1,20})が好き']),
            ('dislike', [r'(?:i (?:really )?hate)\s+([a-z0-9 \-]{2,30})']),
            ('dislike', [r'(?:我討厭|我讨厌)([^，。！？?]{1,20})']),
            ('dislike', [r'(.{1,20})嫌い']),
        ]
        for fact_type, regexes in patterns:
            for regex in regexes:
                source = lowered if regex.startswith('(?:my') or regex.startswith('(?:i') else text
                match = re.search(regex, source, re.IGNORECASE)
                if not match:
                    continue
                value = self._clean_fact_value(match.group(1))
                if fact_type == 'name':
                    bad_name_values = {
                        'baby',
                        'babe',
                        'sweetheart',
                        'darling',
                        'honey',
                        'dear',
                        '宝贝',
                        '寶貝',
                        '亲爱的',
                        '親愛的',
                    }
                    if value.lower() in bad_name_values:
                        continue
                if value:
                    facts.append((fact_type, value))
                break
        seen = set()
        deduped = []
        for fact_type, value in facts:
            key = (fact_type, value.lower())
            if key not in seen:
                seen.add(key)
                deduped.append((fact_type, value))
        return deduped[:3]

    def remember(self, utterance):
        for fact_type, value in self._extract_profile_facts(utterance):
            if fact_type == 'name':
                self.session_profile['name'] = value
            elif fact_type == 'favorite' and value not in self.session_profile['favorites']:
                self.session_profile['favorites'].append(value)
            elif fact_type == 'like' and value not in self.session_profile['likes']:
                self.session_profile['likes'].append(value)
            elif fact_type == 'dislike' and value not in self.session_profile['dislikes']:
                self.session_profile['dislikes'].append(value)
        self.session_turns.append({'user': utterance, 'reply': ''})
        self.session_turns = self.session_turns[-24:]

    def _profile_snapshot(self):
        return {
            'name': self.session_profile['name'],
            'likes': list(self.session_profile['likes'][:6]),
            'dislikes': list(self.session_profile['dislikes'][:6]),
            'favorites': list(self.session_profile['favorites'][:6]),
        }

    def _profile_summary(self):
        parts = []
        if self.session_profile['name']:
            parts.append(f"Name={self.session_profile['name']}")
        if self.session_profile['favorites']:
            parts.append('Favorites=' + '/'.join(self.session_profile['favorites'][:3]))
        if self.session_profile['likes']:
            parts.append('Likes=' + '/'.join(self.session_profile['likes'][:3]))
        if self.session_profile['dislikes']:
            parts.append('Dislikes=' + '/'.join(self.session_profile['dislikes'][:3]))
        return ' ; '.join(parts) if parts else '無個人偏好資料'

    def _recent_dialogue_summary(self):
        if not self.session_turns:
            return '無近期對話'
        slices = self.session_turns[-6:]
        return ' | '.join(f"User:{turn['user']} -> Uruha:{turn['reply']}" for turn in slices)

    def snapshot(self):
        return {
            'knowledge': '',
            'episodes': '',
            'wisdom': '',
            'profile': self._profile_summary(),
            'profile_structured': self._profile_snapshot(),
            'recent_dialogue': self._recent_dialogue_summary(),
            'recent_turns': list(self.session_turns[-8:]),
        }


def contains_any(text, needles):
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def role_similarity(reply):
    score = 3
    if contains_any(reply, ['だろ', 'じゃん', 'って', 'し。', 'よな', 'かよ', 'いいし', '落ち着け', '別に', 'うち']):
        score += 1
    if not contains_any(reply, PERSONA_BAD) and not contains_any(reply, POLITE_BAD) and 4 <= len(reply) <= 48:
        score += 1
    if contains_any(reply, ['ご案内', '承知', 'サポート', 'かしこまり']):
        score -= 2
    return max(1, min(5, score))


def in_character(reply):
    return int(not contains_any(reply, PERSONA_BAD) and not contains_any(reply, POLITE_BAD) and len(reply.strip()) >= 3)


def summarize(results):
    total = len(results)
    replies = Counter(r['reply'] for r in results)
    prompts = Counter(r['prompt'] for r in results)
    languages = defaultdict(list)
    categories = defaultdict(list)
    subcategories = defaultdict(list)
    rarity = defaultdict(list)

    def rate(rows, key):
        vals = [r[key] for r in rows]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    for row in results:
        languages[row['language']].append(row)
        categories[row['category']].append(row)
        subcategories[row.get('subcategory') or row['category']].append(row)
        rarity[row['rarity']].append(row)

    return {
        'mode': 'controller_fast_eval_no_generation',
        'total_cases': total,
        'unique_prompt_ratio': round(len(prompts) / total, 4),
        'duplicate_prompt_count': sum(1 for _, count in prompts.items() if count > 1),
        'planner_rule_hit_rate': rate(results, 'planner_rule_hit'),
        'fallback_plan_rate': rate(results, 'fallback_plan_used'),
        'intent_match_rate': rate(results, 'intent_match'),
        'required_marker_hit_rate': rate(results, 'required_marker_hit'),
        'surface_required_marker_hit_rate': rate(results, 'surface_required_marker_hit'),
        'forbidden_leak_rate': rate(results, 'forbidden_leak'),
        'overall_pass_rate': rate(results, 'overall_pass'),
        'avg_role_similarity_1_to_5': round(sum(r['role_similarity'] for r in results) / total, 3),
        'in_character_consistency': rate(results, 'in_character_consistency'),
        'unique_reply_ratio': round(len(replies) / total, 4),
        'top_20_reply_concentration': round(sum(c for _, c in replies.most_common(20)) / total, 4),
        'language_breakdown': {
            lang: {
                'count': len(rows),
                'overall_pass_rate': rate(rows, 'overall_pass'),
                'planner_rule_hit_rate': rate(rows, 'planner_rule_hit'),
                'fallback_plan_rate': rate(rows, 'fallback_plan_used'),
                'avg_role_similarity': round(sum(r['role_similarity'] for r in rows) / len(rows), 3),
                'in_character_consistency': rate(rows, 'in_character_consistency'),
            }
            for lang, rows in languages.items()
        },
        'category_breakdown': {
            cat: {
                'count': len(rows),
                'overall_pass_rate': rate(rows, 'overall_pass'),
                'intent_match_rate': rate(rows, 'intent_match'),
                'required_marker_hit_rate': rate(rows, 'required_marker_hit'),
                'forbidden_leak_rate': rate(rows, 'forbidden_leak'),
                'planner_rule_hit_rate': rate(rows, 'planner_rule_hit'),
                'fallback_plan_rate': rate(rows, 'fallback_plan_used'),
                'avg_role_similarity': round(sum(r['role_similarity'] for r in rows) / len(rows), 3),
            }
            for cat, rows in categories.items()
        },
        'subcategory_breakdown': {
            cat: {
                'count': len(rows),
                'overall_pass_rate': rate(rows, 'overall_pass'),
                'intent_match_rate': rate(rows, 'intent_match'),
                'required_marker_hit_rate': rate(rows, 'required_marker_hit'),
                'forbidden_leak_rate': rate(rows, 'forbidden_leak'),
                'planner_rule_hit_rate': rate(rows, 'planner_rule_hit'),
                'fallback_plan_rate': rate(rows, 'fallback_plan_used'),
                'avg_role_similarity': round(sum(r['role_similarity'] for r in rows) / len(rows), 3),
            }
            for cat, rows in subcategories.items()
        },
        'rarity_breakdown': {
            key: {
                'count': len(rows),
                'overall_pass_rate': rate(rows, 'overall_pass'),
                'planner_rule_hit_rate': rate(rows, 'planner_rule_hit'),
                'fallback_plan_rate': rate(rows, 'fallback_plan_used'),
            }
            for key, rows in rarity.items()
        },
        'top_replies': replies.most_common(30),
        'worst_cases': sorted(
            results,
            key=lambda r: (
                r['overall_pass'],
                r['intent_match'],
                r['required_marker_hit'],
                1 - r['forbidden_leak'],
                r['in_character_consistency'],
                r['role_similarity'],
            ),
        )[:80],
    }


def main():
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        cases = json.load(f)

    left_brain = brain_mod.LeftBrain(None)
    right_brain = brain_mod.RightBrain(load_model=False)
    results = []

    for i, case in enumerate(cases, start=1):
        memory = MemoryState()
        psyche = brain_mod.Psyche()
        right_brain.history = []
        for utterance in case.get('prelude', []):
            memory.remember(utterance)

        mems = memory.snapshot()
        logic = left_brain._rule_based_plan(case['prompt'], psyche.get_state(), mems)
        planner_rule_hit = int(logic is not None)
        fallback_plan_used = int(logic is None)
        if logic is None:
            logic = left_brain._fallback_plan()

        planner_reply = logic.get('core_message_jp', '').strip() or '軽く返事する'
        reply = right_brain.speak(case['prompt'], logic, mems, psyche.get_state()).strip() or planner_reply

        expected_intents = case.get('expected_intents', [])
        required_markers = case.get('required_markers_any', [])
        forbidden_markers = case.get('forbidden_markers_any', [])

        intent_match = int((not expected_intents) or logic.get('intent') in expected_intents)
        required_marker_hit = int((not required_markers) or contains_any(planner_reply, required_markers))
        surface_required_marker_hit = int((not required_markers) or contains_any(reply, required_markers))
        forbidden_leak = int(bool(forbidden_markers) and contains_any(reply, forbidden_markers))
        in_char = in_character(reply)
        overall_pass = int(intent_match and required_marker_hit and not forbidden_leak and in_char)

        row = {
            **case,
            'logic': logic,
            'planner_reply': planner_reply,
            'reply': reply,
            'planner_rule_hit': planner_rule_hit,
            'fallback_plan_used': fallback_plan_used,
            'intent_match': intent_match,
            'required_marker_hit': required_marker_hit,
            'surface_required_marker_hit': surface_required_marker_hit,
            'forbidden_leak': forbidden_leak,
            'overall_pass': overall_pass,
            'role_similarity': role_similarity(reply),
            'in_character_consistency': in_char,
        }
        results.append(row)

        if i % 500 == 0:
            print(f'[{i:05d}/{len(cases)}] pass={overall_pass} category={case["category"]} intent={logic.get("intent", "")}', flush=True)

    report = {
        'model': {
            'brain_file': os.path.abspath(brain_mod.__file__),
            'evaluation_mode': 'controller_fast_eval_surface_generation',
            'base_model': brain_mod.RIGHT_BRAIN_BASE_MODEL,
            'right_brain_adapter': brain_mod.RIGHT_BRAIN_ADAPTER_PATH,
        },
        'dataset_path': DATASET_PATH,
        'summary': summarize(results),
        'results': results,
    }

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(REPORT_PATH)


if __name__ == '__main__':
    main()
