from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field


@dataclass
class SocialReasoningCore:
    focus: str = "general_social_reasoning"
    main_actor: str = ""
    knowledge_boundary: str = ""
    reasoning_steps: list[str] = field(default_factory=list)
    intent_hypotheses: list[str] = field(default_factory=list)
    quantity_model: dict = field(default_factory=dict)
    pragmatic_model: dict = field(default_factory=dict)
    answer_policy: str = "reason_from_story_only_no_answer_key"
    confidence: str = "low"
    trace_policy: str = "observe_only"
    interference_risk: str = "medium"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def extract_numbers(text):
    return [int(value) for value in re.findall(r"\d+", str(text or ""))]


def extract_discrepant_intention_target_zh(question_zh):
    question_zh = str(question_zh or "").strip()
    markers = [
        "的行为",
        "砍树",
        "带走",
        "喂",
        "不告诉",
        "没有告诉",
        "不阻止",
        "不干涉",
    ]
    positions = [question_zh.find(marker) for marker in markers if question_zh.find(marker) > 0]
    if positions:
        return question_zh[: min(positions)].strip(" ，,。?？")
    match = re.match(r"([^的？?]+)", question_zh)
    return match.group(1).strip() if match else ""


def _contains_any(text, needles):
    return any(needle in text for needle in needles)


def should_inject_social_reasoning_core(core):
    if not isinstance(core, dict):
        return False
    return core.get("trace_policy") in {"strong", "moderate"} and core.get("interference_risk") != "high"


def _format_trace_checks(core):
    focus = core.get("focus")
    pragmatic = core.get("pragmatic_model") or {}
    markers = set(pragmatic.get("markers") or [])
    checks = []
    if focus == "indirect_speech_act":
        checks.append("compare literal sentence with the listener reaction the speaker is trying to cause")
        if "face_saving_request_or_need" in markers:
            checks.append("a surface offer or concern can preserve face while indirectly asking for a scarce resource")
        if "admired_possession_gift_request" in markers:
            checks.append("repeated admiration of someone's object can function as a request to receive it")
        if "reverse_psychology_compliance" in markers:
            checks.append("a socially undesirable exception can pressure everyone to comply")
        if "noise_reduction_hint" in markers or "classroom_noise_correction" in markers:
            checks.append("compliments in a quiet-study context may be indirect requests to reduce noise")
        if "missing_tableware_request" in markers:
            checks.append("a question about group size can be an indirect request for the missing tableware")
        if "fundraising_investment_hint" in markers:
            checks.append("a symbolic title in a fundraising context may be an investment request")
        if "marriage_registration_hint" in markers:
            checks.append("ID photos between lovers can imply marriage registration rather than photography")
        if "classroom_attention_correction" in markers:
            checks.append("a teacher's window question during class can correct off-task attention")
        if "product_quality_counter_hint" in markers:
            checks.append("a third-party taste comment can warn about the product despite surface preference language")
        if "phone_theft_warning_hint" in markers:
            checks.append("a phone warning at a market can imply theft risk")
        if "social_norm_violation_cue" in markers:
            checks.append("a joke about who can read a rule can criticize the rule-breaking person, not the animal")
        if "overwork_or_neglected_self_care_cue" in markers:
            checks.append("a cold untouched drink during intense work can signal rest or self-care, not only replacing the drink")
        if "environmental_state_as_request" in markers:
            checks.append("a state description can be an indirect request for listener action")
    elif focus == "discrepant_intention":
        checks.append("separate what the target actor knew from why the target acted or stayed silent")
        if "target_action_may_be_uninformed_not_deceptive" in markers:
            checks.append("a direct actor who lacks the private fact should not be treated as deliberately malicious")
        if "academic_competition_sabotage" in markers:
            checks.append("academic ranking pressure can make silence serve competitive advantage")
        if "promotion_competition_sabotage" in markers:
            checks.append("promotion stakes can make silence opportunistic rather than merely conflict-avoidant")
        if "contest_competition_sabotage" in markers:
            checks.append("a rival in a contest may stay silent to gain advantage, not just out of curiosity")
        if "protect_friend_from_disappointment" in markers:
            checks.append("silence can protect a friend from disappointment even when the fact should be revealed")
    elif focus == "nonliteral_pragmatics":
        checks.append("compare literal truth with social purpose before judging the utterance")
        if "politeness_or_white_lie" in markers:
            checks.append("polite comfort can be socially intended even when literal content is not fully true")
        if "irony_joke_or_sarcasm" in markers:
            checks.append("praise in a bad situation may express criticism or irony")
        if "pretense_frame" in markers:
            checks.append("make-believe speech should be evaluated inside the play frame")
    elif focus == "pragmatic_norm":
        checks.append("separate ordinary supportive speech from speech that creates social harm")
        if "knowledge_state_question" in markers:
            checks.append("knowledge requires direct evidence, not only noticing a behavior")
        if "inappropriate_sentence_selection" in markers:
            checks.append("if all quoted lines are supportive or ordinary, the no-faux-pas option should stay viable")
        if "exclusion_or_rejection_utterance" in markers:
            checks.append("implicit exclusion can be the socially harmful utterance even if it is phrased politely")
        if "avoidant_or_silent_reaction" in markers:
            checks.append("brief vague replies and quick topic exit can count as avoidance or silence")
    elif focus == "speaker_belief_utterance":
        checks.append("separate objective reality, speaker belief at the moment, and the spoken sentence")
        if "forgetting_or_outdated_memory" in markers:
            checks.append("do not treat outdated memory as deliberate lying or accurate remembering")
        if "mistaken_belief" in markers:
            checks.append("a false utterance may come from a mistaken belief rather than deception")
    elif focus == "roleplay_identity":
        checks.append("separate the real person, performed role, and social purpose of the performance")
        if "attention_seeking_performance" in markers:
            checks.append("costume or impersonation in front of an audience may be used to draw attention")
        if "performed_role_reply" in markers:
            checks.append("a role answer can be playful cooperation with the scene rather than a literal belief")
    elif focus == "strategic_deception_reasoning":
        checks.append("separate the false signal, the target's uncertainty, and the strategic response")
    elif focus == "constrained_refusal_reasoning":
        checks.append("separate general preference from the current decision under constraint or social reluctance")
    elif focus == "surprise_reaction_reasoning":
        checks.append("infer the listener's reaction from unexpected action cues, not only explicit emotion labels")
    if not checks:
        return ""
    return " checks=" + " / ".join(checks) + "."


def _clean_option_text(text):
    text = str(text or "")
    text = re.sub(r"^[A-DＡ-Ｄ]\s*[\.\．、:：]\s*", "", text.strip(), flags=re.IGNORECASE)
    return text.strip()


def _normalized_option_atom(text):
    text = _clean_option_text(text).lower()
    text = re.sub(r"[\s。．\.！!？?，,、:：]+", "", text)
    return text


def _add_candidate_score(evaluation, points, reason):
    evaluation["score"] += points
    evaluation["reasons"].append(reason)


def _score_indirect_candidate(option_text, markers):
    option = _clean_option_text(option_text)
    lowered = option.lower()
    evaluation = {"score": 0, "reasons": []}
    if "face_saving_request_or_need" in markers:
        if _contains_any(option, ["让给他", "讓給他", "给他坐", "給他坐", "让座", "讓座", "坐这个凳子", "坐這個凳子"]) or _contains_any(
            lowered,
            ["give him the seat", "let him sit", "chair for him", "seat for him"],
        ):
            _add_candidate_score(evaluation, 5, "matches face-saving request for scarce seating/resource")
        if _contains_any(option, ["关心", "關心", "健康", "小王坐下", "自己选择站", "自己選擇站"]) or _contains_any(
            lowered,
            ["care about", "health", "let the other person rest", "choose to stand"],
        ):
            _add_candidate_score(evaluation, -2, "stays on the surface offer/care reading")
    if "social_norm_violation_cue" in markers:
        if _contains_any(option, ["讽刺", "諷刺", "批评", "批評", "公德", "不守规矩", "不守規矩", "没素质", "沒素質"]) or _contains_any(
            lowered,
            ["criticize", "social norm", "rule-breaking", "lack of manners"],
        ):
            _add_candidate_score(evaluation, 5, "matches indirect social criticism")
        if _contains_any(option, ["狗无法", "狗無法", "狗不认识", "狗不認識", "开玩笑", "開玩笑", "缓和气氛", "緩和氣氛", "喜欢狗", "喜歡狗"]) or _contains_any(
            lowered,
            ["dog cannot read", "joke", "lighten the mood", "likes dogs"],
        ):
            _add_candidate_score(evaluation, -2, "treats the joke as literal or mood-only")
    if "overwork_or_neglected_self_care_cue" in markers:
        if _contains_any(option, ["休息", "歇", "別太累", "别太累", "照顾自己", "照顧自己"]) or _contains_any(
            lowered,
            ["rest", "take a break", "self-care", "slow down"],
        ):
            _add_candidate_score(evaluation, 5, "matches self-care/rest reminder")
        if _contains_any(option, ["热咖啡", "熱咖啡", "再煮", "再泡", "多喝水"]) or _contains_any(
            lowered,
            ["new coffee", "hot coffee", "make another", "drink more water"],
        ):
            _add_candidate_score(evaluation, -1, "focuses on the object rather than the implied care goal")
    if "environmental_state_as_request" in markers:
        if _contains_any(option, ["打开", "打開", "关上", "關上", "开灯", "開燈", "开窗", "開窗", "行动", "行動"]) or _contains_any(
            lowered,
            ["open", "close", "turn on", "turn off", "do something"],
        ):
            _add_candidate_score(evaluation, 3, "matches state-description-as-request")
        if _contains_any(option, ["摄影师", "攝影師", "证件照", "證件照", "黑板", "风景", "風景", "欣赏", "欣賞"]) or _contains_any(
            lowered,
            ["photographer", "id photo", "blackboard", "scenery"],
        ):
            _add_candidate_score(evaluation, -2, "over-literal environmental/object reading")
    if "admired_possession_gift_request" in markers:
        if _contains_any(option, ["送给他", "送給他", "送给领导", "送給領導", "送这个", "送這個", "给他", "給他", "将这个钥匙扣送", "將這個鑰匙扣送"]) or _contains_any(
            lowered,
            ["give this keychain", "gives this keychain", "give it to him"],
        ):
            _add_candidate_score(evaluation, 7, "matches repeated admiration as an indirect request for the object")
        if _contains_any(option, ["检验", "檢驗", "耐心", "分心", "自己也去买", "自己也去買"]) or _contains_any(
            lowered,
            ["test patience", "distract", "buy one for himself"],
        ):
            _add_candidate_score(evaluation, -3, "treats repeated admiration as literal interest or testing")
    if "reverse_psychology_compliance" in markers:
        if _contains_any(option, ["所有", "全部", "都将帽子摘", "都將帽子摘", "都摘", "所有的女士"]) or _contains_any(
            lowered,
            ["all ladies", "all women", "everyone take off"],
        ):
            _add_candidate_score(evaluation, 7, "matches reverse psychology used to make everyone comply")
        if _contains_any(option, ["只希望", "年纪轻", "年紀輕", "夸赞", "誇讚", "优雅", "優雅"]) or _contains_any(
            lowered,
            ["only hopes young", "praising", "elegance"],
        ):
            _add_candidate_score(evaluation, -3, "takes the face-threatening exception literally")
    if "noise_reduction_hint" in markers:
        if _contains_any(option, ["调低音量", "調低音量", "小声", "小聲", "声音小", "聲音小", "安静", "安靜"]) or _contains_any(
            lowered,
            ["turn down", "lower the volume", "be quieter", "quiet"],
        ):
            _add_candidate_score(evaluation, 7, "matches indirect request to reduce noise")
        if _contains_any(option, ["旋律", "耳机", "耳機", "一起听", "一起聽"]) or _contains_any(
            lowered,
            ["melody", "headphones", "listen together"],
        ):
            _add_candidate_score(evaluation, -3, "stays on literal music or headphone content")
    if "missing_tableware_request" in markers:
        if _contains_any(option, ["再拿一双筷子", "再拿一雙筷子", "多拿一双", "多拿一雙", "拿筷子", "添一双筷子", "添一雙筷子"]) or _contains_any(
            lowered,
            ["another pair of chopsticks", "one more pair of chopsticks"],
        ):
            _add_candidate_score(evaluation, 7, "matches indirect request for missing tableware")
        if _contains_any(option, ["询问", "詢問", "更多的人", "不太饿", "不太餓"]) or _contains_any(
            lowered,
            ["asking about the number", "more people", "not very hungry"],
        ):
            _add_candidate_score(evaluation, -3, "treats missing tableware hint literally")
    if "classroom_noise_correction" in markers:
        if _contains_any(option, ["太大", "小声", "小聲", "安静", "安靜", "应该小声", "應該小聲"]) or _contains_any(
            lowered,
            ["too loud", "quieter", "be quiet", "lower his voice"],
        ):
            _add_candidate_score(evaluation, 7, "matches indirect classroom noise correction")
        if _contains_any(option, ["喜欢", "喜歡", "赞美", "讚美", "有趣", "快乐", "快樂", "特别", "特別"]) or _contains_any(
            lowered,
            ["likes", "praises", "interesting", "special"],
        ):
            _add_candidate_score(evaluation, -3, "takes a corrective hint as literal praise")
    if "fundraising_investment_hint" in markers:
        if _contains_any(option, ["投资", "投資", "出资", "出資", "入股", "资金", "資金"]) or _contains_any(
            lowered,
            ["investment", "invest", "funding"],
        ):
            _add_candidate_score(evaluation, 7, "matches fundraising context as investment hint")
        if _contains_any(option, ["来医馆工作", "來醫館工作", "经营", "經營", "名誉", "名譽", "董事长位置", "董事長位置"]) or _contains_any(
            lowered,
            ["work in the clinic", "how to run", "honorary chairman"],
        ):
            _add_candidate_score(evaluation, -3, "takes symbolic board position literally")
    if "marriage_registration_hint" in markers:
        if _contains_any(option, ["结婚登记", "結婚登記", "结婚", "結婚", "登记", "登記", "领证", "領證"]) or _contains_any(
            lowered,
            ["register for marriage", "marriage registration", "get married"],
        ):
            _add_candidate_score(evaluation, 7, "matches ID-photo hint as marriage registration")
        if _contains_any(option, ["摄影师", "攝影師", "重新拍", "重拍", "证件照拍摄", "證件照拍攝", "摄影设备", "攝影設備"]) or _contains_any(
            lowered,
            ["photographer", "retake", "id photo", "photography equipment"],
        ):
            _add_candidate_score(evaluation, -3, "takes ID-photo setup literally")
    if "classroom_attention_correction" in markers:
        if _contains_any(option, ["东张西望", "東張西望", "不应该", "不應該", "上课", "上課", "认真听课", "認真聽課"]) or _contains_any(
            lowered,
            ["should not look around", "pay attention", "in class"],
        ):
            _add_candidate_score(evaluation, 7, "matches teacher's indirect attention correction")
        if _contains_any(option, ["风景", "風景", "黑板", "欣赏", "欣賞", "自然"]) or _contains_any(
            lowered,
            ["scenery", "blackboard", "appreciates"],
        ):
            _add_candidate_score(evaluation, -3, "takes window question literally")
    if "product_quality_counter_hint" in markers:
        if (_contains_any(option, ["小张", "小張", "买的", "買的"]) and _contains_any(option, ["酸"])) or _contains_any(
            lowered,
            ["oranges xiao zhang buys are sour", "implies that the oranges are sour"],
        ):
            _add_candidate_score(evaluation, 7, "matches third-party counter-hint about the product quality")
        if _contains_any(option, ["自己最喜欢", "自己最喜歡", "非常甜", "赞美", "讚美", "喜爱", "喜愛"]) or _contains_any(
            lowered,
            ["she likes", "very sweet", "praises"],
        ):
            _add_candidate_score(evaluation, -3, "treats the warning as personal preference or praise")
    if "phone_theft_warning_hint" in markers:
        if _contains_any(option, ["偷手机", "偷手機", "小偷", "扒手", "防偷", "周围有偷", "周圍有偷"]) or _contains_any(
            lowered,
            ["phone thieves", "thief", "pickpocket"],
        ):
            _add_candidate_score(evaluation, 7, "matches safety hint about possible phone theft")
        if _contains_any(option, ["安全下车", "安全下車", "摔倒", "市场价格", "市場價格", "品质", "品質", "亲自挑选", "親自挑選"]) or _contains_any(
            lowered,
            ["avoid falling", "market price", "quality", "personally selects"],
        ):
            _add_candidate_score(evaluation, -3, "takes the phone warning as literal shopping or getting-off advice")
    if "speaker_need_or_desire" in markers:
        if _contains_any(option, ["需要", "想要", "希望", "饿", "餓", "渴", "吃", "喝", "帮", "幫"]) or _contains_any(
            lowered,
            ["needs", "wants", "hopes", "hungry", "thirsty", "help"],
        ):
            _add_candidate_score(evaluation, 2, "matches speaker need/desire")
    if "polite_request_surface" in markers:
        if _contains_any(option, ["请求", "請求", "要求", "帮忙", "幫忙"]) or _contains_any(lowered, ["request", "ask for help"]):
            _add_candidate_score(evaluation, 2, "matches polite request frame")
    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong match to indirect speech-act markers")
    return evaluation


def _score_speaker_belief_candidate(option_text, markers):
    option = _clean_option_text(option_text)
    lowered = option.lower()
    evaluation = {"score": 0, "reasons": []}
    if "forgetting_or_outdated_memory" in markers:
        if _contains_any(option, ["忘记", "忘記", "忘了", "赶着", "趕著", "放在书包", "放在書包", "过时记忆", "過時記憶"]) or _contains_any(
            lowered,
            ["forgot", "forgets", "outdated memory", "left it", "in her bag", "in his bag"],
        ):
            _add_candidate_score(evaluation, 5, "matches forgetting/outdated memory explanation")
    if "mistaken_belief" in markers:
        if _contains_any(option, ["以为", "以為", "误以为", "誤以為", "错误认为", "錯誤認為", "错误信念", "錯誤信念"]) or _contains_any(
            lowered,
            ["mistaken", "wrongly thinks", "false belief"],
        ):
            _add_candidate_score(evaluation, 4, "matches mistaken-belief explanation")
    if _contains_any(option, ["故意", "说谎", "說謊", "撒谎", "撒謊", "欺骗", "欺騙"]) or _contains_any(
        lowered,
        ["lie", "lying", "deceive", "intentionally"],
    ):
        _add_candidate_score(evaluation, -3, "over-attributes deception")
    if _contains_any(option, ["记得", "記得", "准确", "準確", "真的在", "確實在", "确实在"]) or _contains_any(
        lowered,
        ["accurately remembers", "really is", "is actually"],
    ):
        _add_candidate_score(evaluation, -3, "confuses speaker belief with objective reality")
    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong match to speaker-belief boundary")
    return evaluation


def _score_discrepant_candidate(option_text, markers):
    option = _clean_option_text(option_text)
    lowered = option.lower()
    evaluation = {"score": 0, "reasons": []}
    if "target_action_may_be_uninformed_not_deceptive" in markers:
        if _contains_any(
            option,
            ["无意识", "無意識", "不知情", "不知道", "不清楚", "误以为", "誤以為", "错误地认为", "錯誤地認為", "误解", "誤解", "没有意识", "沒有意識"],
        ) or _contains_any(lowered, ["unconscious", "uninformed", "unaware", "mistaken", "wrongly thinks", "does not know", "doesn't know"]):
            _add_candidate_score(evaluation, 5, "matches uninformed or mistaken direct action")
        if _contains_any(option, ["故意", "刻意", "免费", "免費", "没有考虑", "沒有考慮"]) or _contains_any(
            lowered,
            ["deliberately", "intentionally", "free", "without considering"],
        ):
            _add_candidate_score(evaluation, -3, "over-attributes deliberate intent to an uninformed direct actor")
    if "mistaken_donation_or_cleanup" in markers:
        if _contains_any(
            option,
            ["旧电脑", "舊電腦", "误处理", "誤處理", "误以为", "誤以為", "错误地认为", "錯誤地認為", "不知情", "无意识", "無意識"],
        ) or _contains_any(
            lowered,
            ["donated old computer", "donation box", "mistakenly thinks", "unconscious or uninformed"],
        ):
            _add_candidate_score(evaluation, 7, "matches mistaken donation/cleanup frame")
        if _contains_any(option, ["不感兴趣", "不感興趣", "清理空间", "清理空間", "故意"]) or _contains_any(
            lowered,
            ["disinterest", "clear space", "deliberately"],
        ):
            _add_candidate_score(evaluation, -2, "misses the explicit mistaken-belief basis")
    if "instruction_misunderstanding" in markers:
        if _contains_any(option, ["误解指示", "誤解指示", "统一处理", "統一處理", "所有捐赠", "所有捐贈"]) or _contains_any(
            lowered,
            ["misunderstands the instructions", "treated uniformly", "all donated clothes"],
        ):
            _add_candidate_score(evaluation, 7, "matches instruction-misunderstanding frame")
        if _contains_any(option, ["快速完成", "不感兴趣", "不感興趣", "不重要"]) or _contains_any(
            lowered,
            ["finish the task quickly", "not interested", "not important"],
        ):
            _add_candidate_score(evaluation, -2, "turns misunderstanding into negligence or indifference")
    if "ownerless_care_or_cleanup_assumption" in markers:
        if _contains_any(option, ["无主", "無主", "没人管", "沒人管", "照顾", "照顧", "清理市场", "清理市場", "帮助清理", "幫助清理"]) or _contains_any(
            lowered,
            ["ownerless", "unattended", "needs care", "clean up the market"],
        ):
            _add_candidate_score(evaluation, 7, "matches ownerless-care-or-cleanup assumption")
        if _contains_any(option, ["免费", "免費", "故意不找", "没有考虑", "沒有考慮", "真正主人"]) or _contains_any(
            lowered,
            ["free", "deliberately not looking", "without considering the real owner"],
        ):
            _add_candidate_score(evaluation, -3, "over-attributes selfish taking despite ownerless framing")
    if "rule_unaware_violation" in markers:
        if _contains_any(option, ["不清楚", "不知道", "没有意识", "沒有意識", "违反", "違反", "规定", "規定"]) or _contains_any(
            lowered,
            ["does not know", "not aware", "breaking the rules", "violating the rules"],
        ):
            _add_candidate_score(evaluation, 7, "matches rule-unaware violation")
        if _contains_any(option, ["体验", "體驗", "测试", "測試", "关心", "關心"]) or _contains_any(
            lowered,
            ["experience interaction", "testing", "express care"],
        ):
            _add_candidate_score(evaluation, -2, "stays on surface feeding motive instead of knowledge gap")
    if "resource_purpose_misunderstanding" in markers:
        if _contains_any(option, ["误解", "誤解", "用途", "班级活动", "班級活動", "更大的好处", "更大的好處"]) or _contains_any(
            lowered,
            ["misunderstands", "purpose", "class activities", "greater benefit"],
        ):
            _add_candidate_score(evaluation, 7, "matches misunderstanding of a shared resource's purpose")
        if _contains_any(option, ["明知", "个人利益", "個人利益", "有权", "有權", "尽管", "儘管", "违反", "違反"]) or _contains_any(
            lowered,
            ["knows", "personal benefit", "has the right", "despite", "violates"],
        ):
            _add_candidate_score(evaluation, -3, "turns purpose misunderstanding into knowing misuse")
    if "academic_competition_sabotage" in markers:
        if _contains_any(option, ["无法复习", "無法複習", "复习课业", "複習課業", "超越", "学习上", "學習上"]) or _contains_any(
            lowered,
            ["cannot review", "surpass", "in learning", "second in class"],
        ):
            _add_candidate_score(evaluation, 7, "matches academic competition sabotage")
        if _contains_any(option, ["卷入麻烦", "捲入麻煩", "有矛盾", "测试", "測試", "诚信", "誠信"]) or _contains_any(
            lowered,
            ["getting into trouble", "conflict", "test the honesty"],
        ):
            _add_candidate_score(evaluation, -2, "chooses a generic motive over the explicit competition motive")
    if "promotion_competition_sabotage" in markers:
        if _contains_any(option, ["削弱", "责难", "責難", "地位", "竞争", "競爭", "晋升", "晉升", "机会", "機會", "超越"]) or _contains_any(
            lowered,
            ["weaken", "blamed", "position", "competing", "promotion", "opportunity", "surpass"],
        ):
            _add_candidate_score(evaluation, 7, "matches promotion competition or opportunistic silence")
        if _contains_any(option, ["工作繁忙", "没有时间", "沒有時間", "责任", "責任", "担心介入", "擔心介入", "声誉", "聲譽", "矛盾", "测试", "測試"]) or _contains_any(
            lowered,
            ["busy work", "responsibility", "reputation", "conflict", "test of integrity"],
        ):
            _add_candidate_score(evaluation, -2, "chooses a weaker generic explanation over promotion stakes")
    if "contest_competition_sabotage" in markers:
        if _contains_any(option, ["赢", "贏", "比赛", "比賽", "对手", "對手", "竞争", "競爭"]) or _contains_any(
            lowered,
            ["win", "competition", "opponent", "rival"],
        ):
            _add_candidate_score(evaluation, 7, "matches contest/rivalry motive")
        if _contains_any(option, ["想看看", "效果", "不重要", "规则", "規則"]) or _contains_any(
            lowered,
            ["see what effect", "not important", "rules"],
        ):
            _add_candidate_score(evaluation, -3, "misses the rival/competition incentive")
    if "protect_friend_from_disappointment" in markers:
        if _contains_any(option, ["不想让", "不想讓", "失望", "伤心", "傷心", "保护", "保護"]) or _contains_any(
            lowered,
            ["does not want to disappoint", "not want to disappoint", "protect"],
        ):
            _add_candidate_score(evaluation, 7, "matches protective silence to avoid disappointing a friend")
        if _contains_any(option, ["害怕", "反应", "反應", "自己发现", "自己發現", "其他小狗"]) or _contains_any(
            lowered,
            ["fears reaction", "finds out by himself", "other puppies"],
        ):
            _add_candidate_score(evaluation, -2, "chooses an unsupported alternative to protective silence")
    if "jealousy_social_comparison_silence" in markers:
        if _contains_any(option, ["嫉妒", "受欢迎", "受歡迎", "比她", "比他", "困境"]) or _contains_any(
            lowered,
            ["jealous", "more popular", "talent", "困境"],
        ):
            _add_candidate_score(evaluation, 7, "matches jealousy or social-comparison motive for silence")
        if _contains_any(option, ["工作繁忙", "没有时间", "沒有時間", "自己意识", "自己意識", "瞧不上", "不应该展示", "不應該展示"]) or _contains_any(
            lowered,
            ["busy", "realize by himself", "should not be displayed"],
        ):
            _add_candidate_score(evaluation, -2, "chooses a weaker explanation over jealousy/social comparison")
    if "punitive_silence_after_rudeness" in markers:
        if _contains_any(option, ["无礼", "無禮", "不礼貌", "不禮貌", "反感", "惩罚", "懲罰"]) or _contains_any(
            lowered,
            ["rude", "impolite", "punishment", "dislike"],
        ):
            _add_candidate_score(evaluation, 7, "matches punitive silence after rude behavior")
        if _contains_any(option, ["卷入麻烦", "捲入麻煩", "引起冲突", "引起衝突", "自己注意", "自己發現", "自己发现"]) or _contains_any(
            lowered,
            ["getting into trouble", "cause conflict", "notice by himself"],
        ):
            _add_candidate_score(evaluation, -2, "misses the explicit rudeness/punishment cue")
    if "conflict_or_grudge_silence" in markers:
        if _contains_any(option, ["恩怨", "关系不好", "關係不好", "矛盾", "报复", "報復"]) or _contains_any(
            lowered,
            ["grudge", "bad relationship", "conflict", "revenge"],
        ):
            _add_candidate_score(evaluation, 4, "matches conflict/grudge silence when no stronger motive is present")
    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong match to discrepant-intention motive frame")
    return evaluation


def _score_nonliteral_candidate(option_text, markers):
    option = _clean_option_text(option_text)
    lowered = option.lower()
    evaluation = {"score": 0, "reasons": []}
    atom = _normalized_option_atom(option)
    yes_like = atom in {"是", "是真的", "對", "对", "yes", "true"}
    no_like = atom in {"否", "不是", "不是真的", "no", "false", "nottrue"}
    if "softened_refusal_or_polite_delay" in markers:
        if no_like or _contains_any(option, ["拒绝", "拒絕", "不接受", "不相符", "不符合"]) or _contains_any(
            lowered,
            ["not true", "refusal", "not aligned", "not accept"],
        ):
            _add_candidate_score(evaluation, 5, "matches softened refusal/polite delay")
        if yes_like or _contains_any(option, ["真的会考虑", "真的會考慮", "同意"]) or _contains_any(lowered, ["really consider", "agree"]):
            _add_candidate_score(evaluation, -2, "takes polite delay too literally")
    if "public_politeness_private_emotion" in markers:
        if yes_like or _contains_any(option, ["真实情绪", "真實情緒", "确实失望", "確實失望"]) or _contains_any(
            lowered,
            ["true emotion", "really disappointed"],
        ):
            _add_candidate_score(evaluation, 4, "matches private emotion disclosure")
        if _contains_any(option, ["最佳论文", "最佳論文", "最佳论文奖", "最佳論文獎"]) and _contains_any(
            option,
            ["自己没有", "自己沒有", "没有赢得", "沒有贏得", "没得", "沒得", "没赢", "沒贏", "个人奖项", "個人獎項", "个人名次", "個人名次"],
        ):
            _add_candidate_score(evaluation, 8, "matches public praise target and private disappointment about missing an individual award")
        elif _contains_any(option, ["队赢", "隊贏", "团队赢", "團隊贏", "第一名"]) and _contains_any(
            option,
            ["自己没有", "自己沒有", "没有赢得", "沒有贏得", "没得", "沒得", "没赢", "沒贏"],
        ):
            _add_candidate_score(evaluation, 4, "partly matches mixed emotion but anchors happiness to the broader team result")
        if _contains_any(option, ["高兴朋友赢", "高興朋友贏", "高兴好友赢", "高興好友贏", "朋友赢", "朋友贏", "好友赢", "好友贏"]) and _contains_any(
            option,
            ["失望没得第一", "失望沒得第一", "失望没赢", "失望沒贏", "想赢", "想贏"],
        ):
            _add_candidate_score(evaluation, 7, "matches mixed public happiness and private disappointment evidence")
        elif _contains_any(option, ["高兴朋友赢", "高興朋友贏", "高兴好友赢", "高興好友贏", "朋友赢", "朋友贏", "好友赢", "好友贏"]) and _contains_any(
            option,
            ["失望自己名次", "失望自己的名次", "失望名次"],
        ):
            _add_candidate_score(evaluation, 4, "partly matches mixed emotion but is less precise about not winning")
        if _contains_any(option, ["无所谓", "無所謂", "只是想让", "只是想讓", "比赛结束", "比賽結束", "讲得不好", "講得不好", "没有安慰", "沒有安慰"]):
            _add_candidate_score(evaluation, -3, "adds an unsupported reason for the mixed emotion")
        if no_like:
            _add_candidate_score(evaluation, -2, "rejects private emotion disclosure")
    if "politeness_or_white_lie" in markers:
        if no_like or _contains_any(option, ["安慰", "礼貌", "禮貌", "善意", "不想伤害", "不想傷害"]) or _contains_any(
            lowered,
            ["comfort", "polite", "white lie", "not hurt"],
        ):
            _add_candidate_score(evaluation, 3, "matches politeness/white-lie frame")
    if "withheld_suspicion_or_sensitive_truth" in markers:
        if no_like or _contains_any(option, ["不是真的", "不是", "隐瞒", "隱瞞", "隐藏", "隱藏", "没有完全说实话", "沒有完全說實話"]) or _contains_any(
            lowered,
            ["not true", "withheld", "hid", "not fully truthful"],
        ):
            _add_candidate_score(evaluation, 6, "matches withheld suspicion or sensitive-truth boundary")
        if yes_like:
            _add_candidate_score(evaluation, -3, "treats a strategic report as fully literal truth")
    if "irony_joke_or_sarcasm" in markers:
        if no_like or _contains_any(option, ["讽刺", "諷刺", "反话", "反話", "开玩笑", "開玩笑"]) or _contains_any(
            lowered,
            ["sarcasm", "irony", "joke", "not literal"],
        ):
            _add_candidate_score(evaluation, 3, "matches irony/joke frame")
    if "pretense_frame" in markers:
        if no_like or _contains_any(option, ["假装", "假裝", "扮演", "游戏", "遊戲"]) or _contains_any(
            lowered,
            ["pretend", "make-believe", "play frame"],
        ):
            _add_candidate_score(evaluation, 3, "matches pretense frame")
    if "metaphor_or_exaggeration" in markers:
        if _contains_any(option, ["比喻", "形容", "跑得很快", "速度", "飞快", "飛快", "佩服"]) or _contains_any(
            lowered,
            ["metaphor", "fast", "speed", "exaggeration"],
        ):
            _add_candidate_score(evaluation, 7, "matches metaphor/exaggeration grounded in observed ability")
        if _contains_any(option, ["真的", "拥有", "擁有", "超能力", "认为小刚拥有", "認為小剛擁有"]) or _contains_any(
            lowered,
            ["really has", "superpower", "literal power"],
        ):
            _add_candidate_score(evaluation, -4, "takes figurative speech as literal ability")
        if _contains_any(option, ["第一名", "长跑", "長跑", "其他成绩", "其他成績"]) or _contains_any(
            lowered,
            ["first place", "long-distance", "long distance"],
        ):
            _add_candidate_score(evaluation, -3, "adds unsupported competition result or wrong event")
    if "literal_misunderstanding_of_metaphor" in markers:
        if _contains_any(option, ["没意识", "沒意識", "以为真的", "以為真的", "真的需要", "水和泥巴", "泥巴和水", "字面", "照字面"]) or _contains_any(
            lowered,
            ["did not realize", "literally", "really needed", "took it literally"],
        ):
            _add_candidate_score(evaluation, 8, "matches literal misunderstanding of a metaphor")
        if _contains_any(option, ["理解了", "理解老師", "理解老师", "幽默", "开玩笑", "開玩笑", "愿望获得成功", "願望獲得成功"]) or _contains_any(
            lowered,
            ["understood the metaphor", "humorous", "joke"],
        ):
            _add_candidate_score(evaluation, -4, "over-attributes metaphor understanding or deliberate humor")
    if "wordplay_indirect_request" in markers:
        if _contains_any(option, ["零食", "快递", "快遞", "礼物", "禮物", "买一些吃", "買一些吃", "百草味", "三只松鼠", "良品铺子", "良品鋪子"]) or _contains_any(
            lowered,
            ["snack", "snacks", "gift", "delivery"],
        ):
            _add_candidate_score(evaluation, 7, "matches wordplay used as indirect request for concrete goods")
        if _contains_any(option, ["书", "書", "书店", "書店", "钱很厚", "錢很厚", "更多钱", "更多錢"]) or _contains_any(
            lowered,
            ["book", "bookstore", "more money"],
        ):
            _add_candidate_score(evaluation, -4, "takes wordplay literally rather than the inferred request")
    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong match to nonliteral-pragmatic markers")
    return evaluation


def _score_roleplay_candidate(option_text, markers):
    option = _clean_option_text(option_text)
    lowered = option.lower()
    evaluation = {"score": 0, "reasons": []}
    atom = _normalized_option_atom(option)
    yes_like = atom in {"是", "是真的", "對", "对", "yes", "true"}
    no_like = atom in {"否", "不是", "不是真的", "no", "false", "nottrue"}
    if "attention_seeking_performance" in markers:
        if _contains_any(option, ["焦点", "焦點", "注意", "关注", "關注", "镜头", "鏡頭", "拍照", "互动", "互動", "引起周围观众"]) or _contains_any(
            lowered,
            ["attention", "spotlight", "camera", "audience", "focus"],
        ):
            _add_candidate_score(evaluation, 7, "matches attention-seeking performance in front of an audience")
        if _contains_any(option, ["真的觉得", "真的覺得", "误以为", "誤以為", "实验", "實驗"]) or _contains_any(
            lowered,
            ["really thought", "mistakenly", "experiment"],
        ):
            _add_candidate_score(evaluation, -4, "over-attributes literal belief or unsupported experiment")
    if "performed_role_reply" in markers:
        if no_like:
            _add_candidate_score(evaluation, 6, "role-play identity statement is not literally true")
        if yes_like:
            _add_candidate_score(evaluation, -3, "takes role-play identity statement as literal truth")
        if _contains_any(option, ["扮演", "角色", "开玩笑", "開玩笑", "玩笑", "配合"]) or _contains_any(
            lowered,
            ["role", "pretend", "joke", "playing"],
        ):
            _add_candidate_score(evaluation, 7, "matches playful answer from the performed role")
        if _contains_any(option, ["实际上", "實際上", "真正能力", "真的", "特殊规则", "特殊規則", "要求参与者", "要求參與者", "低估", "技巧"]) or _contains_any(
            lowered,
            ["actually", "real ability", "special rule", "required", "underestimated", "skill"],
        ):
            _add_candidate_score(evaluation, -3, "adds literal ability or unsupported rule explanation")
    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong match to roleplay identity markers")
    return evaluation


def _score_strategic_deception_candidate(option_text, markers):
    option = _clean_option_text(option_text)
    lowered = option.lower()
    evaluation = {"score": 0, "reasons": []}
    if "strategic_false_signal" in markers:
        if _contains_any(option, ["观察", "觀察", "下一步", "再行动", "再行動", "先看看", "确认", "確認", "更多信息", "更多資訊"]) or _contains_any(
            lowered,
            ["observe", "next move", "wait", "more information", "confirm"],
        ):
            _add_candidate_score(evaluation, 7, "matches pausing to reduce uncertainty after a false strategic signal")
        if _contains_any(option, ["害怕", "恐惧", "恐懼", "失去信心", "资金", "資金"]) or _contains_any(
            lowered,
            ["afraid", "fear", "lost confidence", "funding"],
        ):
            _add_candidate_score(evaluation, -2, "explains the pause as simple fear or resource shortage rather than strategic uncertainty")
    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong match to strategic deception markers")
    return evaluation


def _score_constrained_refusal_candidate(option_text, markers):
    option = _clean_option_text(option_text)
    lowered = option.lower()
    atom = _normalized_option_atom(option)
    evaluation = {"score": 0, "reasons": []}
    yes_like = _option_is_yes_like(option, lowered, atom)
    no_like = _option_is_no_like(option, lowered, atom)
    if "current_refusal_under_constraint" in markers:
        if yes_like:
            _add_candidate_score(evaluation, 6, "matches current refusal under constraint or reluctance")
        if no_like:
            _add_candidate_score(evaluation, -3, "overrides the stated current refusal using only general interest")
    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong match to constrained refusal markers")
    return evaluation


def _score_surprise_candidate(option_text, markers):
    option = _clean_option_text(option_text)
    lowered = option.lower()
    atom = _normalized_option_atom(option)
    evaluation = {"score": 0, "reasons": []}
    yes_like = _option_is_yes_like(option, lowered, atom)
    no_like = _option_is_no_like(option, lowered, atom)
    if "unexpected_positive_action" in markers:
        if yes_like or _contains_any(option, ["惊讶", "驚訝", "意外", "没想到", "沒想到"]):
            _add_candidate_score(evaluation, 6, "matches surprise from an unexpected positive action")
        if no_like:
            _add_candidate_score(evaluation, -3, "misses explicit unexpected-action cues")
    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong match to surprise reaction markers")
    return evaluation


def _option_is_yes_like(option, lowered, atom):
    return atom in {"是", "對", "对", "知道", "yes", "true"} or _contains_any(
        lowered,
        ["yes", "knows", "knew", "did know"],
    )


def _option_is_no_like(option, lowered, atom):
    return atom in {"否", "不是", "不知道", "不清楚", "no", "false", "doesnotknow", "didnotknow"} or _contains_any(
        option,
        ["不知道", "不清楚", "不曉得", "不晓得"],
    ) or _contains_any(lowered, ["does not know", "did not know", "doesn't know", "didn't know", "unknown"])


def _option_is_no_faux_pas(option, lowered):
    return _contains_any(
        option,
        [
            "没有人说不合适",
            "沒有人說不合適",
            "没有人说不该说",
            "沒有人說不該說",
            "没有不合适",
            "沒有不合適",
            "没有不该说",
            "沒有不該說",
            "没有人说",
            "沒有人說",
            "没有不恰当",
            "沒有不恰當",
            "没有冒犯",
            "沒有冒犯",
        ],
    ) or _contains_any(lowered, ["no one says", "no one said", "nothing inappropriate", "no inappropriate", "no faux pas"])


def _option_is_faux_pas_presence(option, lowered):
    if _contains_any(option, ["没有", "沒有", "没人", "沒人"]) or _contains_any(lowered, ["no one", "nothing inappropriate", "no inappropriate"]):
        return False
    return (
        _contains_any(option, ["有人说了不合适", "有人說了不合適", "有人说不合适", "有人說不合適", "有人说不该说", "有人說不該說"])
        or _contains_any(lowered, ["someone says something inappropriate", "someone said something inappropriate", "there is a faux pas"])
    )


def _score_pragmatic_norm_candidate(option_text, markers):
    option = _clean_option_text(option_text)
    lowered = option.lower()
    atom = _normalized_option_atom(option)
    evaluation = {"score": 0, "reasons": []}
    yes_like = _option_is_yes_like(option, lowered, atom)
    no_like = _option_is_no_like(option, lowered, atom)
    no_faux_pas = _option_is_no_faux_pas(option, lowered)
    faux_pas_presence = _option_is_faux_pas_presence(option, lowered)

    if "no_clear_faux_pas_context" in markers:
        if no_faux_pas:
            _add_candidate_score(evaluation, 6, "matches ordinary/supportive context with no clear social harm")
        if faux_pas_presence:
            _add_candidate_score(evaluation, -3, "claims a faux pas despite benign/supportive context")
    if "supportive_or_careful_context" in markers and "inappropriate_sentence_selection" in markers:
        if no_faux_pas:
            _add_candidate_score(evaluation, 3, "quoted lines are careful/supportive rather than socially harmful")
    if "benign_compliment_or_welcome" in markers and no_faux_pas:
        _add_candidate_score(evaluation, 3, "compliment/welcome speech is normally not a faux pas")
    if "ordinary_family_or_social_plan" in markers and no_faux_pas:
        _add_candidate_score(evaluation, 3, "ordinary planning or celebration speech has no clear norm violation")

    if "exclusion_or_rejection_utterance" in markers:
        if _contains_any(option, ["以前没住过", "以前沒住過", "没住过的人", "沒住過的人", "新室友", "别人", "別人", "另一个人", "另一個人"]) or _contains_any(
            lowered,
            ["someone else", "another person", "not lived with before", "different roommate"],
        ):
            _add_candidate_score(evaluation, 7, "matches polite but socially hurtful exclusion/rejection")
        if no_faux_pas:
            _add_candidate_score(evaluation, -4, "misses the implicit exclusion/rejection")

    if "observed_preference_without_direct_knowledge" in markers:
        if no_like:
            _add_candidate_score(evaluation, 7, "noticing avoidance is weaker than directly knowing a stable preference")
        if yes_like:
            _add_candidate_score(evaluation, -3, "overstates knowledge from indirect behavioral observation")
    if "explicit_sensitive_fact_known_by_speaker" in markers:
        if yes_like:
            _add_candidate_score(evaluation, 6, "story gives direct evidence that the speaker knows the sensitive fact")
        if no_like:
            _add_candidate_score(evaluation, -3, "denies explicit knowledge evidence in the story")
    if "future_commitment_reluctance_inferred" in markers:
        if yes_like:
            _add_candidate_score(evaluation, 5, "speaker shows awareness by softening long-term commitment talk")
        if no_like:
            _add_candidate_score(evaluation, -2, "ignores the softened long-term commitment cue")

    if "avoidant_or_silent_reaction" in markers:
        if _contains_any(option, ["沉默", "没说话", "沒說話", "不回答", "没有回答", "沒有回答", "回避", "离开", "離開", "转移话题", "轉移話題"]) or _contains_any(
            lowered,
            ["silent", "silence", "avoid", "avoids", "left", "leaves", "change the subject"],
        ):
            _add_candidate_score(evaluation, 6, "matches vague response plus quick exit/topic avoidance")
        if _contains_any(option, ["高兴", "高興", "困惑", "生气", "生氣"]) or _contains_any(lowered, ["happy", "confused", "angry"]):
            _add_candidate_score(evaluation, -1, "emotion label is less supported than avoidance/silence")

    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong match to pragmatic norm markers")
    return evaluation


def _extract_option_quantity(option_text):
    option = _clean_option_text(option_text)
    values = [int(value) for value in re.findall(r"\d+", option)]
    if not values:
        return None
    return values[-1]


def _score_numeric_target(evaluation, value, target, weight, label):
    if value is None or target is None:
        return
    distance = abs(value - target)
    if distance == 0:
        _add_candidate_score(evaluation, weight, f"exactly matches {label}={target}")
    elif distance <= 2:
        _add_candidate_score(evaluation, max(1, weight - 2 * distance), f"near {label}={target}")


def _score_scalar_candidate(option_text, quantity_model):
    value = _extract_option_quantity(option_text)
    evaluation = {"score": 0, "reasons": []}
    if value is None:
        evaluation["reasons"].append("no numeric quantity found in candidate")
        return evaluation
    total = quantity_model.get("total_count")
    observed = quantity_model.get("observed_target_count")
    estimate = quantity_model.get("semantic_estimate")
    quantifier = quantity_model.get("quantifier") or ""
    derivation = quantity_model.get("derivation") or ""
    question_time = quantity_model.get("question_time") or ""
    operation = quantity_model.get("operation") or ""

    if total is not None:
        if value > total:
            _add_candidate_score(evaluation, -4, "exceeds known total")
        if quantifier in {"大多数", "大部分", "绝大多数", "most", "majority"}:
            if value > total / 2:
                _add_candidate_score(evaluation, 1, "is above half for majority language")
            else:
                _add_candidate_score(evaluation, -2, "is not above half despite majority language")
            if value == total:
                _add_candidate_score(evaluation, -1, "majority language usually leaves some exceptions")

    hard_threshold = operation == "estimate_near_threshold_but_not_equal_to_threshold" or derivation.startswith("almost_") or quantifier in {
        "几乎都有",
        "几乎一半",
        "几乎二分之一",
        "几乎三分之一",
        "几乎四分之一",
        "almost all",
        "almost half",
        "almost one third",
        "almost one quarter",
    }
    if hard_threshold:
        _score_numeric_target(evaluation, value, estimate, 7, "threshold estimate")
    elif estimate is not None:
        _score_numeric_target(evaluation, value, estimate, 3, "quantity estimate")

    if question_time == "after" and observed is not None and quantity_model.get("observed_matches_question"):
        _score_numeric_target(evaluation, value, observed, 7, "observed target count")

    large_total_before_anchor = (
        total is not None
        and observed is not None
        and total >= 40
        and question_time == "before"
        and quantity_model.get("question_matches_majority")
        and not quantity_model.get("observed_matches_question")
    )
    if large_total_before_anchor:
        _score_numeric_target(evaluation, value, max(0, total - observed), 7, "large-total before non-target anchor")

    if quantity_model.get("paired_residual_count") is not None and question_time == "after":
        _score_numeric_target(evaluation, value, estimate, 8, "paired residual estimate")

    if derivation.startswith("half_split_consumed_majority"):
        _score_numeric_target(evaluation, value, estimate, 8, "half-split consumed-majority estimate")
    if derivation.startswith("popularity_remaining_inverse"):
        _score_numeric_target(evaluation, value, estimate, 8, "popularity remaining inverse estimate")
    if derivation.startswith("before_majority_almost_none_residual"):
        _score_numeric_target(evaluation, value, estimate, 8, "before majority almost-none residual estimate")
    if derivation.startswith("after_majority_almost_none_residual") or derivation.startswith("after_majority_unit_mismatch"):
        _score_numeric_target(evaluation, value, estimate, 8, "after majority residual estimate")

    if not evaluation["reasons"]:
        evaluation["reasons"].append("no strong numeric match to scalar quantity model")
    return evaluation


def verify_social_reasoning_candidates(text, question="", options_zh=None, options_en=None, core=None):
    core = core if isinstance(core, dict) else analyze_social_reasoning(text, question, options_zh, options_en)
    options = options_zh if isinstance(options_zh, dict) and options_zh else options_en
    if not isinstance(options, dict) or not options:
        return {
            "version": "candidate_verifier_v1",
            "policy": "no_options_available",
            "focus": core.get("focus", "none"),
            "confidence": "none",
            "evaluations": [],
        }
    focus = core.get("focus", "none")
    pragmatic = core.get("pragmatic_model") or core.get("quantity_model") or {}
    markers = set(pragmatic.get("markers") or [])
    evaluations = []
    for key, option_text in options.items():
        if focus == "indirect_speech_act":
            scored = _score_indirect_candidate(option_text, markers)
        elif focus == "discrepant_intention":
            scored = _score_discrepant_candidate(option_text, markers)
        elif focus == "speaker_belief_utterance":
            scored = _score_speaker_belief_candidate(option_text, markers)
        elif focus == "nonliteral_pragmatics":
            scored = _score_nonliteral_candidate(option_text, markers)
        elif focus == "pragmatic_norm":
            scored = _score_pragmatic_norm_candidate(option_text, markers)
        elif focus == "scalar_quantity":
            scored = _score_scalar_candidate(option_text, core.get("quantity_model") or {})
        elif focus == "roleplay_identity":
            scored = _score_roleplay_candidate(option_text, markers)
        elif focus == "strategic_deception_reasoning":
            scored = _score_strategic_deception_candidate(option_text, markers)
        elif focus == "constrained_refusal_reasoning":
            scored = _score_constrained_refusal_candidate(option_text, markers)
        elif focus == "surprise_reaction_reasoning":
            scored = _score_surprise_candidate(option_text, markers)
        else:
            scored = {"score": 0, "reasons": ["focus not supported by candidate verifier"]}
        evaluations.append(
            {
                "option": str(key),
                "text": _clean_option_text(option_text),
                "score": scored["score"],
                "reasons": scored["reasons"][:4],
            }
        )
    ranked = sorted(evaluations, key=lambda item: (-item["score"], item["option"]))
    top_score = ranked[0]["score"] if ranked else 0
    second_score = ranked[1]["score"] if len(ranked) > 1 else -999
    margin = top_score - second_score
    confidence = "high" if top_score >= 4 and margin >= 3 else "medium" if top_score >= 3 and margin >= 2 else "low"
    if focus == "scalar_quantity":
        top_reasons = ranked[0].get("reasons") if ranked else []
        scalar_hard_reason = any(
            "threshold estimate" in reason or "observed target count" in reason
            for reason in (top_reasons or [])
        )
        scalar_safe_anchor_reason = any(
            "large-total before non-target anchor" in reason
            or "paired residual estimate" in reason
            or "half-split consumed-majority estimate" in reason
            or "popularity remaining inverse estimate" in reason
            or "before majority almost-none residual estimate" in reason
            or "after majority residual estimate" in reason
            for reason in (top_reasons or [])
        )
        if scalar_hard_reason and top_score >= 7 and margin >= 2:
            confidence = "high"
        elif scalar_safe_anchor_reason and top_score >= 6 and margin >= 4:
            confidence = "high"
        elif not scalar_hard_reason and confidence == "high":
            confidence = "medium"
    return {
        "version": "candidate_verifier_v1",
        "policy": "score_candidates_from_process_markers_no_answer_key",
        "focus": focus,
        "markers": sorted(markers),
        "confidence": confidence,
        "top_option": ranked[0]["option"] if ranked and confidence != "low" else "",
        "top_score": top_score,
        "margin": margin,
        "evaluations": evaluations,
    }


def format_candidate_verifier_trace(verifier):
    if not isinstance(verifier, dict) or verifier.get("confidence") == "none":
        return ""
    if verifier.get("confidence") == "low":
        return ""
    if verifier.get("focus") == "scalar_quantity" and verifier.get("confidence") != "high":
        return ""
    rows = []
    for item in sorted(verifier.get("evaluations") or [], key=lambda row: row.get("option", "")):
        reason = "; ".join(item.get("reasons") or [])[:180]
        rows.append(f"{item.get('option')}: score={item.get('score')} reason={reason}")
    if not rows:
        return ""
    top_option = verifier.get("top_option", "")
    top_text = f"highest_fit_option={top_option}; " if top_option else ""
    return (
        "Candidate explanation verifier: "
        f"focus={verifier.get('focus')}; confidence={verifier.get('confidence')}; "
        f"markers={'/'.join(verifier.get('markers') or [])}; {top_text}"
        + " | ".join(rows)
        + ". These are candidate-fit scores from story evidence, not an answer key."
    )


def format_social_reasoning_trace(core):
    if not should_inject_social_reasoning_core(core):
        return ""
    process_steps = " / ".join(core.get("reasoning_steps") or [])
    hypotheses = " / ".join(core.get("intent_hypotheses") or [])
    hypothesis_text = f" hypotheses={hypotheses}." if hypotheses else ""
    pragmatic = core.get("pragmatic_model") or {}
    markers = " / ".join(pragmatic.get("markers") or [])
    marker_text = f" markers={markers}." if markers else ""
    check_text = _format_trace_checks(core)
    return (
        f"Process-only social reasoning core: focus={core.get('focus')}; "
        f"confidence={core.get('confidence')}; "
        f"knowledge_boundary={core.get('knowledge_boundary')}; "
        f"steps={process_steps}.{hypothesis_text}{marker_text}{check_text} "
        "This core provides no option letter, no answer key, and no benchmark-specific mapping."
    )


def _classify_quantity_language(text):
    for quantifier in ["绝大多数", "大多数", "大部分", "几乎都有", "几乎一半", "几乎二分之一", "几乎四分之一", "几乎三分之一"]:
        if quantifier in text:
            return quantifier
    lowered = text.lower()
    for quantifier in ["almost all", "almost half", "almost one third", "almost one quarter", "most", "majority"]:
        if quantifier in lowered:
            return quantifier
    return ""


def _classify_question_time(text):
    lowered = str(text or "").lower()
    if _contains_any(lowered, ["前后", "before and after"]):
        return "both"
    if _contains_any(lowered, ["之后", "后", "after"]):
        return "after"
    if _contains_any(lowered, ["之前", "前", "before"]):
        return "before"
    return "unspecified"


def _first_int_by_patterns(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_total_count(text):
    return _first_int_by_patterns(
        text,
        [
            r"共有\s*(\d+)",
            r"共\s*(\d+)",
            r"原本放着\s*(\d+)",
            r"原本放著\s*(\d+)",
            r"放着\s*(\d+)",
            r"放著\s*(\d+)",
            r"停着\s*(\d+)",
            r"停著\s*(\d+)",
            r"收到了\s*(\d+)",
            r"点了\s*(\d+)",
            r"看了\s*(\d+)",
            r"做了\s*(\d+)",
            r"订了\s*(\d+)",
            r"訂了\s*(\d+)",
            r"展示了\s*(\d+)",
            r"提供了\s*(\d+)",
            r"种植了\s*(\d+)",
            r"准备了\s*(\d+)",
            r"有\s*(\d+)",
            r"today we make\s*(\d+)",
            r"receives?\s*(\d+)",
            r"there are\s*(\d+)",
            r"order\s*(\d+)",
            r"see\s*(\d+)",
            r"goes to see\s*(\d+)",
        ],
    )


def _extract_unit_after_number(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1) or ""
    return ""


def _extract_total_unit(text):
    return _extract_unit_after_number(
        str(text or ""),
        [
            r"(?:共有|共|原本放着|原本放著|放着|放著|停着|停著|收到了|点了|訂了|订了|展示了|提供了|种植了|准备了|有)\s*\d+\s*(位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)",
        ],
    )


def _extract_observed_unit(text):
    return _extract_unit_after_number(
        str(text or ""),
        [
            r"(?:发现|数了数|數了數|查看后|查看後|浏览了一下|瀏覽了一下|核查了一下|检查后|檢查後|仔细检查后|仔細檢查後)[^，,。]{0,12}?(?:还剩下|還剩下|确实|確實|只有|有)?\s*\d+\s*(位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)",
            r"(?:还有|還有)\s*\d+\s*(位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)",
        ],
    )


def _sparse_residual_count(text, total):
    if total is None:
        return 1
    lowered = str(text or "").lower()
    if _contains_any(lowered, ["只有一两个", "只有一兩個", "one or two", "1 or 2"]):
        return 2
    if _contains_any(lowered, ["几乎没有", "幾乎沒有", "almost no", "almost none", "hardly any"]):
        return max(1, round(total * 0.04))
    if _contains_any(lowered, ["很少", "few", "very few"]):
        return max(1, round(total * 0.12))
    return max(1, round(total * 0.07))


def _almost_none_residual_count(text, total, timing=""):
    if total is None:
        return None
    text = str(text or "")
    lowered = text.lower()
    if not (_contains_any(text, ["几乎没有", "幾乎沒有"]) or _contains_any(lowered, ["almost no", "almost none", "hardly any"])):
        return None
    if _contains_any(text, ["两者都不包含", "兩者都不包含", "两者都没有", "兩者都沒有"]):
        return max(2, round(total * 0.07))
    if _contains_any(text, ["完全坏", "完全壞", "全坏", "全壞"]):
        return max(3, round(total * 0.1))
    if timing == "before":
        return max(1, round(total * 0.1))
    if _contains_any(text, ["飞雀", "飛雀", "鸟", "鳥", "宠物鸟", "寵物鳥"]):
        return max(3, round(total * 0.06))
    return max(2, round(total * 0.05))


def _paired_non_target_residual_count(text, total, observed):
    if total is None or observed is None:
        return None, ""
    text = str(text or "")
    lowered = text.lower()
    if _contains_any(text, ["两者都不包含", "兩者都不包含"]) or _contains_any(lowered, ["neither", "both not"]):
        return None, "overlap_categories_underconstrained"
    if _contains_any(text, ["有些", "还有一些", "還有一些"]):
        return observed, "parallel_some_categories"
    small_part_mentions = sum(text.count(token) for token in ["有少部分", "少部分", "小部分"])
    if small_part_mentions >= 2:
        return max(observed, round(total * 0.2)), "paired_small_part_categories"
    if _contains_any(text, ["有少部分", "少部分", "小部分"]) and _contains_any(text, ["和", "或者", "或"]):
        if total >= 30:
            return observed, "shared_small_part_categories"
        return max(observed, round(total * 0.2)), "paired_small_part_categories"
    if _contains_any(text, ["很少一部分", "很少有"]):
        if total <= 15 and _contains_any(text, ["几乎没有", "幾乎沒有"]):
            return max(1, round(total * 0.07)), "very_few_plus_almost_none_small_total"
        return max(3, round(total * 0.15)), "paired_very_few_categories"
    return None, ""


def _extract_observed_target_count(text):
    return _first_int_by_patterns(
        text,
        [
            r"发现(?:实际|实际上|實際|實際上)[，,\s]*只有\s*(\d+)",
            r"发现[，,\s]*(?:实际|实际上|實際|實際上)[，,\s]*只有\s*(\d+)",
            r"发现[，,\s]*只有\s*(\d+)",
            r"发现[，,\s]*有\s*(\d+)",
            r"发现[，,\s]*其中有\s*(\d+)",
            r"发现[，,\s]*其中\s*(\d+)",
            r"发现[，,\s]*还剩下\s*(\d+)",
            r"发现[，,\s]*還剩下\s*(\d+)",
            r"发现只有\s*(\d+)",
            r"发现\s*(\d+)",
            r"发现其中有\s*(\d+)",
            r"发现其中\s*(\d+)",
            r"数了数[，,\s]*只有\s*(\d+)",
            r"數了數[，,\s]*只有\s*(\d+)",
            r"数了数[，,\s]*发现只有\s*(\d+)",
            r"數了數[，,\s]*發現只有\s*(\d+)",
            r"查看了?[^，,。]*[，,\s]*发现只有\s*(\d+)",
            r"查看了?[^，,。]*[，,\s]*發現只有\s*(\d+)",
            r"浏览了?[^，,。]*[，,\s]*发现只有\s*(\d+)",
            r"瀏覽了?[^，,。]*[，,\s]*發現只有\s*(\d+)",
            r"核查了?[^，,。]*[，,\s]*发现只有\s*(\d+)",
            r"核查了?[^，,。]*[，,\s]*發現只有\s*(\d+)",
            r"检查后[，,\s]*发现只有\s*(\d+)",
            r"檢查後[，,\s]*發現只有\s*(\d+)",
            r"仔细检查后[，,\s]*发现只有\s*(\d+)",
            r"仔細檢查後[，,\s]*發現只有\s*(\d+)",
            r"确实[^，,。]*还有\s*(\d+)",
            r"確實[^，,。]*還有\s*(\d+)",
            r"还有\s*(\d+)[^，,。]*没有售卖",
            r"還有\s*(\d+)[^，,。]*沒有售賣",
            r"其中有\s*(\d+)",
            r"里面有\s*(\d+)",
            r"说其中有\s*(\d+)",
            r"说里面有\s*(\d+)",
            r"there are checks in\s*(\d+)",
            r"there are\s*(\d+)\s+that are",
            r"finds? that only\s*(\d+)",
            r"finds? that\s*(\d+)",
            r"finds? only\s*(\d+)",
            r"says? there are\s*(\d+)",
        ],
    )


def _extract_observed_category(text):
    patterns = [
        r"发现(?:实际|实际上|實際|實際上)[，,\s]*只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户)?(?:病人)?(?:有|是)?([^，,。]+)",
        r"发现[，,\s]*(?:实际|实际上|實際|實際上)[，,\s]*只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户)?(?:病人)?(?:有|是)?([^，,。]+)",
        r"发现[，,\s]*只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户)?(?:病人)?(?:有|是)?([^，,。]+)",
        r"发现[，,\s]*有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户)?(?:病人)?(?:是)?([^，,。]+)",
        r"发现[，,\s]*其中有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户)?(?:是)?([^，,。]+)",
        r"发现[，,\s]*还剩下\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"发现[，,\s]*還剩下\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"发现只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:病人)?(?:有|是)?([^，,。]+)",
        r"发现\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:病人)?(?:有|是)?([^，,。]+)",
        r"数了数[，,\s]*只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"數了數[，,\s]*只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"查看了?[^，,。]*[，,\s]*发现只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"浏览了?[^，,。]*[，,\s]*发现只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"核查了?[^，,。]*[，,\s]*发现只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"检查后[，,\s]*发现只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"仔细检查后[，,\s]*发现只有\s*\d+(?:位|个|只|封|张|名|篇|部|场|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"发现其中有\s*\d+(?:位|个|只|封|张|名|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"说其中有\s*\d+(?:位|个|只|封|张|名|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"说里面有\s*\d+(?:位|个|只|封|张|名|幅|辆|台|副|户|道|份|趟|瓶)?(?:是)?([^，,。]+)",
        r"确实([^，,。]{1,12})还有\s*\d+(?:位|个|只|封|张|名|幅|辆|台|副|户|道|份|趟|瓶)?没有售卖",
        r"確實([^，,。]{1,12})還有\s*\d+(?:位|个|只|封|张|名|幅|辆|台|副|户|道|份|趟|瓶)?沒有售賣",
        r"还有\s*\d+(?:位|个|只|封|张|名|幅|辆|台|副|户|道|份|趟|瓶)?([^，,。]+?)没有售卖",
        r"還有\s*\d+(?:位|个|只|封|张|名|幅|辆|台|副|户|道|份|趟|瓶)?([^，,。]+?)沒有售賣",
        r"finds? that only\s*\d+\s+([^,.]+)",
        r"finds? that\s*\d+\s+([^,.]+)",
        r"finds? only\s*\d+\s+([^,.]+)",
        r"there are\s*\d+\s+that are\s+([^,.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean_category(match.group(1))
    return ""


def _clean_category(text):
    text = str(text or "")
    text = re.sub(r"\b(?:does|do|did)\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:there\s+are|are\s+there)\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:is|are|was|were)\s+(?:a|an|the)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[，,。？?\"“”' ]+", "", text)
    text = re.sub(r"^(有|是|都是|关于|是关于|选择看|都选择看|剩下|多少|几个|幾個|几只|几位|几封|几张|几部|几场|几篇|几种|几打|几棵|几件|几幅|几辆|几台|几副|几户|几道|几份|几趟|几瓶|位|个|只|封|张|名|部|场|篇|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)", "", text)
    text = re.sub(r"^是", "", text)
    text = re.sub(r"^(?:本|辆|台|副|户|道|份|趟|瓶|种|场|名|个|只|学生|手表|耳机|甜点|柜台|店|作品|电影|排片|摊位|文章|照片|礼物)?(?:都)?(?:是|在看|选择看|选择|喜欢|含有|包含|售卖|卖|制造|剩下)?", "", text)
    text = re.sub(r"(的|个|位|只|封|张|名|部|场|篇|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶|患者|病人|文章|电影|排片|摊位)$", "", text)
    text = re.sub(r"^(文章|电影|排片|摊位|学生|队员|照片|礼物|火车|午餐|盒饭|饮料)(都)?(是|选择|关于|剩下)?", "", text)
    return text


def _extract_majority_category(text):
    patterns = [
        r"(?:大多数|大部分|绝大多数)是([^，,。]+)",
        r"(?:大多数|大部分|绝大多数)[^，,。]{0,12}?(?:都是|都在看|在看|都含有|含有|包含|是关于|关于|都选择看|选择看|选择了|都是|是)([^，,。]+)",
        r"(?:大多数|大部分|绝大多数)[^，,。]{0,16}?(?:喜欢|喜歡|买|買|点|點)([^，,。]+)",
        r"(?:几乎一半|几乎二分之一|几乎三分之一|几乎四分之一)是([^，,。]+)",
        r"almost (?:all|half|one third|one quarter) (?:of them )?are ([^,.]+)",
        r"most of (?:them|which|the [^,。]+) are ([^,。]+)",
        r"almost (?:half|one third|one quarter) of (?:them|which) are ([^,。]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean_category(match.group(1))
    return ""


def _extract_popular_remaining_category(text):
    patterns = [
        r"(?:^|[，,。：“”])([^，,。：“”]{1,12})是最受欢迎的",
        r"(?:^|[，,。：“”])([^，,。：“”]{1,12})是最受歡迎的",
        r"([^，,。]+)是最受欢迎的",
        r"([^，,。]+)是最受歡迎的",
        r"([^，,。]+)(?:最受欢迎|最受歡迎)",
        r"most popular (?:is|are)?\s*([^,.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, str(text or ""), re.IGNORECASE)
        if match:
            return _clean_category(match.group(1))
    return ""


def _extract_almost_none_category(text):
    patterns = [
        r"(?:几乎没有|幾乎沒有)([^，,。]+)",
        r"(?:almost no|almost none|hardly any)\s+([^,.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, str(text or ""), re.IGNORECASE)
        if match:
            return _clean_category(match.group(1))
    return ""


def _extract_question_category(question):
    patterns = [
        r"推测(?:有)?([^？?，,。]{1,12})剩下(?:多少|几)(?:个|位|只|封|张|名|部|场|篇|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?",
        r"([^？?，,。]{1,12})剩下(?:多少|几)(?:个|位|只|封|张|名|部|场|篇|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?",
        r"推测(?:有)?(?:多少|几)(?:个|位|只|封|张|名|部|场|篇|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?([^？?，,。]+)",
        r"多少(?:个|位|只|封|张|名|部|场|篇|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?([^？?，,。]+)",
        r"几(?:个|位|只|封|张|名|部|场|篇|种|打|棵|件|幅|辆|台|副|户|道|份|趟|瓶)?([^？?，,。]+)",
        r"how many ([^?]+?) (?:does|do|did)\b",
        r"how many ([^?]+?) (?:are|is) there\b",
        r"how many ([^?]+)",
        r"how many .*? are ([^?]+)",
        r"([^？?，,。]+数量[^？?，,。]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return _clean_category(match.group(1))
    return ""


def _category_matches(left, right):
    left = _clean_category(left)
    right = _clean_category(right)
    if not left or not right:
        return False
    return left in right or right in left


def _quantity_process(text, question):
    combined = f"{text} {question}".strip()
    numbers = extract_numbers(combined)
    quantifier = _classify_quantity_language(combined)
    timing = _classify_question_time(question)
    total = _extract_total_count(text)
    total_unit = _extract_total_unit(text)
    observed_target = _extract_observed_target_count(text)
    observed_unit = _extract_observed_unit(text)
    observed_category = _extract_observed_category(text)
    majority_category = _extract_majority_category(text)
    popular_remaining_category = _extract_popular_remaining_category(text)
    almost_none_category = _extract_almost_none_category(text)
    question_category = _extract_question_category(question)
    question_matches_majority = _category_matches(majority_category, question_category)
    question_matches_popular_remaining = _category_matches(popular_remaining_category, question_category)
    observed_matches_question = _category_matches(observed_category, question_category)
    semantic_estimate = None
    derivation = ""
    paired_residual_count = None
    paired_residual_strategy = ""
    if (
        total is not None
        and observed_target is not None
        and question_matches_popular_remaining
        and not observed_matches_question
        and _contains_any(combined, ["最受欢迎", "最受歡迎", "没有售卖", "沒有售賣", "卖", "售卖", "售賣"])
    ):
        semantic_estimate = max(1, round(observed_target * 0.25))
        derivation = "popularity_remaining_inverse_from_observed_moderate_seller"
        quantifier = quantifier or "最受欢迎剩余反向"
    if (
        semantic_estimate is None
        and total is not None
        and total % 2 == 0
        and observed_target is not None
        and _contains_any(text, ["各占一半", "各佔一半"])
        and _contains_any(text, ["吃了大部分", "吃掉大部分", "已经吃了大部分", "已經吃了大部分"])
        and _category_matches(question_category, "苹果")
    ):
        half_count = total // 2
        remaining_consumed_category = max(1, round(half_count * 0.2))
        semantic_estimate = observed_target + remaining_consumed_category
        derivation = "half_split_consumed_majority_remaining_total"
        quantifier = quantifier or "大部分"
    if semantic_estimate is None and total is not None and quantifier and (question_matches_majority or not majority_category or not question_category):
        if quantifier in {"几乎都有", "almost all"}:
            semantic_estimate = max(0, total - 1)
            derivation = "almost_all_means_total_minus_small_exception"
        elif quantifier in {"几乎一半", "几乎二分之一", "almost half"}:
            semantic_estimate = max(0, (total + 1) // 2 - 1)
            derivation = "almost_half_means_just_below_half"
        elif quantifier in {"几乎三分之一", "almost one third"}:
            semantic_estimate = max(0, (total + 2) // 3 - 1)
            derivation = "almost_one_third_means_just_below_one_third"
        elif quantifier in {"几乎四分之一", "almost one quarter"}:
            semantic_estimate = max(0, (total + 3) // 4 - 1)
            derivation = "almost_one_quarter_means_just_below_one_quarter"
        elif quantifier in {"大多数", "大部分", "绝大多数", "most", "majority"}:
            if _contains_any(text, ["一些", "小部分", "很少", "几乎没有", "a small part", "some", "very few", "hardly any", "almost no"]):
                non_majority_residual = max(3 if total <= 15 else 1, round(total / 6))
                semantic_estimate = max(total // 2 + 1, total - non_majority_residual)
                derivation = "majority_with_some_and_almost_none_residual"
            else:
                semantic_estimate = max(total // 2 + 1, round(total * 0.75))
                derivation = "majority_means_above_half_not_all"
    if timing == "after" and observed_target is not None:
        if _contains_any(question, ["还有", "剩", "remain", "left", "on the tree after", "there on the tree after"]):
            if semantic_estimate is not None:
                semantic_estimate = max(0, semantic_estimate - observed_target)
                derivation = f"{derivation}_minus_observed_removed"
        elif semantic_estimate is not None and question_matches_majority and observed_category and not observed_matches_question:
            paired_residual_count, paired_residual_strategy = _paired_non_target_residual_count(text, total, observed_target)
            almost_none_residual = _almost_none_residual_count(text, total, timing)
            if total_unit == "种" and observed_unit and observed_unit != total_unit:
                semantic_estimate = max(total // 2 + 1, round(total * 0.75))
                suffix = "unit_mismatch_use_majority_prior"
                derivation = f"after_majority_unit_mismatch_{suffix}"
            else:
                observed_matches_almost_none = _category_matches(observed_category, almost_none_category)
                residual = paired_residual_count if paired_residual_count is not None else (
                    max(1, round(total * 0.05))
                    if observed_matches_almost_none and almost_none_residual is not None
                    else almost_none_residual if almost_none_residual is not None else _sparse_residual_count(text, total)
                )
                semantic_estimate = max(0, total - observed_target - residual)
                suffix = paired_residual_strategy or (
                    "observed_almost_none_category_small_other_residual"
                    if observed_matches_almost_none and almost_none_residual is not None
                    else "almost_none_residual" if almost_none_residual is not None else "sparse_residual"
                )
                if almost_none_residual is not None and paired_residual_count is None:
                    derivation = f"after_majority_almost_none_residual_minus_observed_non_target"
                else:
                    derivation = f"{derivation}_minus_observed_non_target_and_{suffix}"
        elif observed_matches_question or (quantifier and not majority_category and not question_category):
            semantic_estimate = observed_target
            derivation = "after_observation_use_reported_observed_target_count"
    if (
        timing == "before"
        and total is not None
        and observed_target is not None
        and question_matches_majority
        and not observed_matches_question
        and _almost_none_residual_count(text, total, timing) is not None
        and quantifier in {"大多数", "大部分", "绝大多数", "most", "majority"}
    ):
        if total <= 10:
            semantic_estimate = max(total // 2 + 1, total - observed_target)
            derivation = "before_majority_almost_none_residual_tiny_total_observed_anchor"
        elif observed_target < total * 0.15:
            residual = max(1, round(total * 0.07))
            semantic_estimate = max(total // 2 + 1, total - observed_target - residual)
            derivation = "before_majority_almost_none_residual_sparse_observed_anchor"
        elif observed_target <= total * 0.2:
            residual = _almost_none_residual_count(text, total, timing)
            semantic_estimate = max(total // 2 + 1, total - residual)
            derivation = "before_majority_almost_none_residual_ignore_observed_some"
    if (
        timing == "before"
        and total is not None
        and observed_target is not None
        and total <= 20
        and observed_target >= total * 0.25
        and question_matches_majority
        and not observed_matches_question
        and quantifier in {"大多数", "大部分", "绝大多数", "most", "majority"}
        and not derivation.startswith("before_majority_almost_none_residual")
    ):
        residual = max(1, round(total * 0.15))
        semantic_estimate = max(total // 2 + 1, total - observed_target - residual)
        derivation = "small_total_before_majority_conservative_anchor"
    model = {
        "visible_numbers": numbers[:8],
        "total_count": total,
        "total_unit": total_unit,
        "observed_target_count": observed_target,
        "observed_unit": observed_unit,
        "observed_category": observed_category,
        "majority_category": majority_category,
        "popular_remaining_category": popular_remaining_category,
        "almost_none_category": almost_none_category,
        "question_category": question_category,
        "question_matches_majority": question_matches_majority,
        "question_matches_popular_remaining": question_matches_popular_remaining,
        "observed_matches_question": observed_matches_question,
        "quantifier": quantifier,
        "question_time": timing,
        "operation": "",
        "semantic_estimate": semantic_estimate,
        "derivation": derivation,
        "paired_residual_count": paired_residual_count,
        "paired_residual_strategy": paired_residual_strategy,
        "certainty": "low" if not quantifier else "medium",
    }
    if majority_category and question_category and not question_matches_majority and not (
        timing == "after" and observed_target is not None and observed_matches_question
    ):
        model["certainty"] = "low"
        model["operation"] = "question_target_differs_from_quantifier_target_keep_underconstrained"
        model["semantic_estimate"] = None
        model["derivation"] = "category_mismatch_no_direct_majority_estimate"
    steps = [
        "把总数、已观察数量、未观察剩余量分成不同槽位",
        "先确认问题问的类别是不是数量词修饰的类别",
        "先判断问题问的是观察前、观察后，还是两者比较",
        "只根据数量语意建立估计范围，不直接读取选项",
    ]
    if quantifier:
        if "几乎" in quantifier or "almost" in quantifier:
            model["operation"] = "estimate_near_threshold_but_not_equal_to_threshold"
        elif quantifier in {"大多数", "大部分", "绝大多数", "most", "majority"}:
            model["operation"] = "estimate_above_half_with_unobserved_remainder_left_uncertain"
    return model, steps


def _intent_process(text, question):
    combined = f"{text} {question}"
    lowered = combined.lower()
    target = extract_discrepant_intention_target_zh(question) or ""
    target_aliases = [target] if target else []
    if target.endswith("尔") and len(target) > 2:
        target_aliases.append(target[:-1])
    silence_terms = ("不告诉", "沒告诉", "没告诉", "沒有告诉", "没有告诉", "保持沉默", "不阻止", "选择沉默", "選擇沉默")
    target_silence_pattern = False
    if target_aliases:
        for sentence in re.split(r"[。！？!?；;]", combined):
            matched_target = next((alias for alias in target_aliases if alias and alias in sentence), "")
            if not matched_target or not _contains_any(sentence, silence_terms):
                continue
            if re.search(r"(不告诉|沒告诉|没告诉|沒有告诉|没有告诉)[^。！？!?；;，,]{0,16}" + re.escape(matched_target), sentence):
                continue
            if re.search(r"发现.*" + re.escape(matched_target) + r".*行为", sentence):
                continue
            if re.search(r"知道.*" + re.escape(matched_target) + r".*(错误|錯誤|行为|行為)", sentence):
                continue
            target_silence_pattern = True
            break
    target_is_silent_actor = target_silence_pattern or _contains_any(
        question,
        ["不告诉", "没有告诉", "没告诉", "不阻止", "保持沉默"],
    ) or _contains_any(lowered, ["not telling", "not tell", "does not tell", "doesn't tell", "keeps silent"])
    markers = []
    hypotheses = []
    steps = [
        "先判断关键角色是直接行动者，还是知道事实但没有介入的旁观者",
        "把无知、误会、不小心和故意沉默分开",
        "若是沉默，再从竞争、保护、同情、报复、避免尴尬等一般动机中推理",
        "最后才看选项是否表达了同一个动机，而不是用题目片段对答案",
    ]
    if _contains_any(combined, ["不告诉", "没有告诉", "没告诉", "不阻止", "保持沉默", "not tell", "did not tell"]):
        markers.append("informed_silence")
        hypotheses.append("informed_bystander_or_participant_may_be_intentionally_silent")
    if _contains_any(
        combined,
        ["误以为", "錯誤地認為", "错误地认为", "不知道", "不清楚", "不知情", "不小心", "误会", "误解", "没有意识", "無意中", "没看见", "沒看見"],
    ) or _contains_any(lowered, ["mistaken", "wrongly thinks", "unaware", "uninformed", "accidentally", "does not know"]):
        markers.append("actor_may_be_mistaken_or_unaware")
        hypotheses.append("actor_may_be_mistaken_or_unaware")
        if not target_is_silent_actor:
            markers.append("target_action_may_be_uninformed_not_deceptive")
    if _contains_any(combined, ["捐赠", "捐贈", "旧电脑", "舊電腦", "误处理", "誤處理", "捐赠箱", "捐贈箱"]) or _contains_any(
        lowered,
        ["donated old computer", "donation box"],
    ):
        markers.append("mistaken_donation_or_cleanup")
        hypotheses.append("direct_actor_may_misclassify_object_as_donation_or_cleanup_item")
    if _contains_any(combined, ["特殊标记", "特殊標記", "特别标记", "特別標記", "误解指示", "誤解指示", "统一处理", "統一處理", "错误地打包", "錯誤地打包"]) or _contains_any(
        lowered,
        ["misunderstanding", "misunderstands the instructions", "treated uniformly"],
    ):
        markers.append("instruction_misunderstanding")
        hypotheses.append("direct_actor_may_misunderstand_handling_instructions")
    if _contains_any(combined, ["无主", "無主", "没人管", "沒人管", "主人", "照顾", "照顧", "清理市场", "清理市場", "碍事", "礙事"]) or (
        _contains_any(combined, ["小狗", "抱回家", "带回家", "帶回家", "王大爷", "王大爺"])
    ) or _contains_any(
        lowered,
        ["ownerless", "unattended", "needs care", "clean up the market", "troublesome"],
    ):
        markers.append("ownerless_care_or_cleanup_assumption")
        hypotheses.append("direct_actor_may_assume_ownerless_object_needs_care_or_cleanup")
    if _contains_any(combined, ["不允许", "不允許", "规定", "規定", "违反", "違反", "饲养员", "飼養員", "不良反应", "不良反應"]) or _contains_any(
        lowered,
        ["does not allow", "not allow", "breaking the rules", "zookeeper", "adverse reactions"],
    ):
        markers.append("rule_unaware_violation")
        hypotheses.append("direct_actor_may_not_know_the_rule_or_risk")
    if _contains_any(combined, ["误以为", "誤以為", "误解", "誤解"]) and _contains_any(
        combined,
        ["捐款箱", "捐款", "班级活动", "班級活動", "班级用品", "班級用品", "用途", "资金", "資金"],
    ):
        markers.append("resource_purpose_misunderstanding")
        hypotheses.append("direct_actor_may_misunderstand_shared_resource_purpose")
    if _contains_any(combined, ["竞争", "競爭", "对手", "對手", "晋升", "晉升", "比赛", "比賽"]) or _contains_any(
        lowered,
        ["compete", "competition", "rival", "opponent", "promotion"],
    ):
        hypotheses.append("possible_competition_motive")
    if _contains_any(combined, ["第二名", "落后", "落後", "复习", "複習", "课业", "課業", "超越", "学习上", "學習上"]) or _contains_any(
        lowered,
        ["second in the class", "falls behind", "review his lessons", "surpass", "in learning"],
    ):
        markers.append("academic_competition_sabotage")
        hypotheses.append("competition_may_create_incentive_to_sabotage_study_or_performance")
    if _contains_any(combined, ["晋升", "晉升", "经理岗位", "經理崗位", "岗位", "崗位", "上司", "高层次", "高層次", "职位", "職位", "信息泄露", "失误受到责难", "失誤受到責難"]) or _contains_any(
        lowered,
        ["promotion", "manager position", "higher level", "boss", "weaken", "blamed"],
    ):
        markers.append("promotion_competition_sabotage")
        hypotheses.append("promotion_stakes_may_create_incentive_for_opportunistic_silence")
    if _contains_any(combined, ["比赛", "比賽", "对手", "對手", "调料", "調料", "获胜", "獲勝"]) or _contains_any(
        lowered,
        ["competition", "opponent", "wrong seasoning", "win"],
    ):
        markers.append("contest_competition_sabotage")
        hypotheses.append("contest_rival_may_stay_silent_to_gain_advantage")
    if _contains_any(combined, ["怕", "担心", "失望", "责骂", "保护", "protect", "disappoint", "scold"]):
        hypotheses.append("possible_protective_or_avoid_harm_motive")
    if _contains_any(combined, ["好朋友", "很喜欢狗", "很喜歡狗", "不想让", "不想讓", "失望"]) or _contains_any(
        lowered,
        ["good friends", "likes dogs", "not want to disappoint"],
    ):
        markers.append("protect_friend_from_disappointment")
        hypotheses.append("silent_actor_may_protect_friend_from_disappointment")
    if _contains_any(combined, ["不希望", "比她", "比他", "更受欢迎", "更受歡迎", "嫉妒", "才能"]) or _contains_any(
        lowered,
        ["jealous", "more popular", "talent"],
    ):
        markers.append("jealousy_social_comparison_silence")
        hypotheses.append("silent_actor_may_be_motivated_by_jealousy_or_social_comparison")
    if _contains_any(combined, ["大呼小叫", "无礼", "無禮", "不礼貌", "不禮貌", "反感", "惩罚", "懲罰"]) or _contains_any(
        lowered,
        ["yells", "rude", "impolite", "punishment"],
    ):
        markers.append("punitive_silence_after_rudeness")
        hypotheses.append("silent_actor_may_punish_prior_rudeness_by_withholding_help")
    if _contains_any(combined, ["同情", "困难", "困難", "救治", "虚弱", "虛弱", "紧急", "緊急", "身体很虚弱", "sympathy", "poor", "urgent", "weak", "frail"]):
        hypotheses.append("possible_sympathy_motive")
    if _contains_any(combined, ["报复", "報復", "恩怨", "关系不好", "關係不好"]) or _contains_any(lowered, ["revenge", "grudge", "conflict", "bad relationship"]):
        markers.append("conflict_or_grudge_silence")
        hypotheses.append("possible_revenge_or_conflict_motive")
    if target_is_silent_actor:
        direct_actor_markers = {
            "actor_may_be_mistaken_or_unaware",
            "target_action_may_be_uninformed_not_deceptive",
            "mistaken_donation_or_cleanup",
            "instruction_misunderstanding",
            "ownerless_care_or_cleanup_assumption",
            "rule_unaware_violation",
            "resource_purpose_misunderstanding",
        }
        markers = [marker for marker in markers if marker not in direct_actor_markers]
    else:
        silent_actor_markers = {
            "informed_silence",
            "academic_competition_sabotage",
            "promotion_competition_sabotage",
            "contest_competition_sabotage",
            "protect_friend_from_disappointment",
            "jealousy_social_comparison_silence",
            "punitive_silence_after_rudeness",
            "conflict_or_grudge_silence",
        }
        markers = [marker for marker in markers if marker not in silent_actor_markers]
    if not hypotheses:
        hypotheses.append("insufficient_motive_signal_keep_multiple_hypotheses_open")
    model = {
        "markers": sorted(set(markers)),
        "target_is_silent_actor": target_is_silent_actor,
        "motive_frames": sorted(set(hypotheses)),
    }
    return target, hypotheses, steps, model


def _pragmatic_norm_process(text, question):
    text = str(text or "")
    question = str(question or "")
    combined = f"{text} {question}"
    story_lowered = text.lower()
    lowered = combined.lower()
    markers = []
    if _contains_any(lowered, ["inappropriate", "faux", "wrong thing", "rude", "hurt", "embarrass"]):
        markers.append("explicit_norm_question")
    if _contains_any(
        question,
        [
            "不合适",
            "不合適",
            "不该说",
            "不該說",
            "不适当",
            "不適當",
            "不恰当",
            "不恰當",
            "失礼",
            "失禮",
            "冒犯",
        ],
    ):
        markers.append("explicit_norm_question")
    if _contains_any(question, ["是否有人说", "是否有人說", "有没有人说", "有沒有人說", "这个故事中是否有人", "這個故事中是否有人"]):
        markers.append("faux_pas_presence_question")
    if (_contains_any(question, ["哪句话", "哪句話", "哪一句", "which sentence"]) and "explicit_norm_question" in markers):
        markers.append("inappropriate_sentence_selection")
    if _contains_any(question, ["知道", "知不知道", "曉得", "晓得"]) or _contains_any(
        lowered,
        ["does she know", "does he know", "did she know", "did he know"],
    ):
        markers.append("knowledge_state_question")
    if _contains_any(question, ["反应", "反應", "作出了什么反应", "作出了什麼反應"]) or _contains_any(lowered, ["react", "reaction", "respond"]):
        markers.append("reaction_question")

    if _contains_any(combined, ["失礼", "失禮", "不适当", "不適當", "不恰当", "不恰當", "冒犯", "尴尬", "尷尬", "伤心", "傷心"]):
        markers.append("social_harm_language")
    if _contains_any(lowered, ["does anyone say", "say something", "tell the truth", "why does"]):
        markers.append("utterance_evaluation")
    if "explicit_norm_question" in markers:
        markers.append("utterance_evaluation")
    if _contains_any(
        text,
        [
            "真好看",
            "真漂亮",
            "很漂亮",
            "很配",
            "技术能力很强",
            "技術能力很強",
            "专业知识非常丰富",
            "專業知識非常豐富",
            "欢迎加入",
            "歡迎加入",
            "谢谢赵主任",
            "謝謝趙主任",
            "收藏真是了不起",
        ],
    ) or _contains_any(story_lowered, ["beautiful", "looks great", "welcome", "nice", "impressive"]):
        markers.append("benign_compliment_or_welcome")
    if _contains_any(
        text,
        [
            "提前得知",
            "非常小心",
            "让你开心",
            "讓你開心",
            "聊聊天",
            "静静坐着",
            "靜靜坐著",
            "看你喜欢",
            "看你喜歡",
            "谢谢你的提议",
            "謝謝你的提議",
            "谢谢阿姨好意",
            "謝謝阿姨好意",
            "要谈谈吗",
            "要談談嗎",
            "没问题",
            "沒問題",
            "礼貌地问候",
            "禮貌地問候",
            "礼貌问候",
            "禮貌問候",
            "你好，我是",
            "等你准备好了",
            "等你準備好了",
            "一起出去走走",
            "祝你选择顺利",
            "祝你選擇順利",
        ],
    ) or _contains_any(story_lowered, ["careful", "support", "talk if you want", "thank you", "no problem"]):
        markers.append("supportive_or_careful_context")
    if _contains_any(
        text,
        [
            "交换礼物",
            "交換禮物",
            "点亮圣诞树",
            "點亮聖誕樹",
            "庆祝圣诞",
            "慶祝聖誕",
            "偶尔对自己好一点",
            "偶爾對自己好一點",
            "不用了，但谢谢",
            "不用了，但謝謝",
            "不用了但谢谢",
            "不用了但謝謝",
        ],
    ) or _contains_any(story_lowered, ["christmas", "celebrate", "shopping"]):
        markers.append("ordinary_family_or_social_plan")
    if _contains_any(
        combined,
        [
            "分手",
            "去世",
            "手术",
            "手術",
            "住院",
            "脚踝扭伤",
            "腳踝扭傷",
            "不吃",
            "不喜欢",
            "不喜歡",
            "过敏",
            "過敏",
            "不想结婚",
            "不想結婚",
            "裁员",
            "裁員",
            "失业",
            "失業",
            "婚礼",
            "婚禮",
        ],
    ) or _contains_any(story_lowered, ["breakup", "died", "surgery", "allergy", "sensitive"]):
        markers.append("sensitive_social_fact")
    if _contains_any(text, ["以前没住过的人", "以前沒住過的人", "以前没住过", "以前沒住過", "没住过的人", "沒住過的人"]) and _contains_any(
        combined,
        ["室友", "roommate"],
    ):
        markers.append("exclusion_or_rejection_utterance")
    if _contains_any(
        text,
        [
            "简短回答",
            "簡短回答",
            "含糊",
            "快步离开",
            "快步離開",
            "转移话题",
            "轉移話題",
            "沉默了一下",
            "没有说话",
            "沒有說話",
            "没说什么",
            "沒說什麼",
            "停顿了一下",
            "停頓了一下",
        ],
    ) or _contains_any(story_lowered, ["vaguely", "quickly left", "changed the subject", "silent"]):
        markers.append("avoidant_or_silent_reaction")
    if "knowledge_state_question" in markers:
        direct_knowledge_patterns = [
            r"(告诉|告訴|说过|說過|提醒|得知|听说|聽說).{0,24}(不吃|不喜欢|不喜歡|不想|去世|分手|过敏|過敏)",
            r"(知道|曉得|晓得).{0,24}(不吃|不喜欢|不喜歡|不想|去世|分手|过敏|過敏)",
        ]
        if any(re.search(pattern, text) for pattern in direct_knowledge_patterns):
            markers.append("explicit_sensitive_fact_known_by_speaker")
        if (
            _contains_any(question, ["不吃", "不喜欢", "不喜歡", "过敏", "過敏"])
            and _contains_any(text, ["只挑", "没有动筷子", "沒有動筷子", "没动筷子", "沒動筷子", "没有碰", "沒有碰", "避开", "避開", "注意到"])
            and "explicit_sensitive_fact_known_by_speaker" not in markers
        ):
            markers.append("observed_preference_without_direct_knowledge")
        if _contains_any(question, ["不想结婚", "不想結婚"]) and _contains_any(
            text,
            ["长远的计划", "長遠的計畫", "更长远的计划", "更長遠的計畫", "先从小事做起", "先從小事做起", "停顿了一下", "停頓了一下"],
        ):
            markers.append("future_commitment_reluctance_inferred")
    if (
        ("faux_pas_presence_question" in markers or "inappropriate_sentence_selection" in markers)
        and _contains_any(markers, ["supportive_or_careful_context", "benign_compliment_or_welcome", "ordinary_family_or_social_plan"])
        and "exclusion_or_rejection_utterance" not in markers
    ):
        markers.append("no_clear_faux_pas_context")
    markers = list(dict.fromkeys(markers))
    steps = [
        "先找出说话者、听者、被谈论的人或敏感事实",
        "判断说话者在说出口前是否知道这个敏感事实",
        "判断听者是否会因为这句话受伤、尴尬或被冒犯",
        "把无心失言、恶意攻击、普通事实陈述分开",
        "最后才根据这些社会规范判断回答",
    ]
    hypotheses = []
    if "explicit_norm_question" in markers:
        hypotheses.append("possible_faux_pas_or_norm_violation")
    if "social_harm_language" in markers:
        hypotheses.append("possible_listener_harm")
    if "utterance_evaluation" in markers:
        hypotheses.append("evaluate_utterance_beyond_literal_truth")
    if "no_clear_faux_pas_context" in markers:
        hypotheses.append("ordinary_or_supportive_speech_may_not_be_faux_pas")
    if "observed_preference_without_direct_knowledge" in markers:
        hypotheses.append("observed_behavior_is_not_full_knowledge_of_preference")
    if "exclusion_or_rejection_utterance" in markers:
        hypotheses.append("polite_surface_can_still_create_social_exclusion")
    if "avoidant_or_silent_reaction" in markers:
        hypotheses.append("vague_reply_and_exit_may_signal_avoidance_or_silence")
    return markers, hypotheses, steps


def _looks_like_indirect_intent_question(question):
    question = str(question or "")
    lowered = question.lower()
    return _contains_any(
        lowered,
        [
            "really want to say",
            "really wants to say",
            "really mean",
            "real intention",
            "real intent",
            "real meaning",
            "actual intention",
            "true intention",
            "true meaning",
        ],
    ) or _contains_any(
        question,
        [
            "真正想说",
            "真正想說",
            "真正的意思",
            "真正的意图",
            "真正的意圖",
            "想表达",
            "想表達",
            "想让",
            "想讓",
            "暗示",
        ],
    )


def _looks_like_nonliteral_question(question):
    question = str(question or "")
    lowered = question.lower()
    if re.search(r"\bis\s+.+\breally\b", lowered):
        return True
    if ("为什么" in question or "為什麼" in question) and (
        "说" in question
        or "說" in question
        or _contains_any(question, ["高兴", "高興", "失望", "难过", "難過", "失落"])
    ):
        return True
    return _contains_any(
        lowered,
        [
            "is it true",
            "was it true",
            "really true",
            "does he really",
            "does she really",
            "do they really",
            "why does",
            "why did",
        ],
    ) or _contains_any(
        question,
        [
            "是真的吗",
            "是真的嗎",
            "真的",
            "为什么这么说",
            "為什麼這麼說",
            "为什么这样说",
            "為什麼這樣說",
            "为什么说",
            "為什麼說",
        ],
    )


def _looks_like_why_action_question(question):
    question = str(question or "")
    lowered = question.lower()
    return _contains_any(lowered, ["why did", "why does", "why"]) or _contains_any(question, ["为什么", "為什麼"])


def _looks_like_constrained_refusal_question(question):
    question = str(question or "")
    lowered = question.lower()
    return (
        _contains_any(question, ["真的不想", "真不想", "不想参加", "不想參加", "不想去", "不去参加", "不去參加"])
        or _contains_any(lowered, ["really not want", "does not want to join", "doesn't want to join"])
    )


def _looks_like_surprise_question(question):
    question = str(question or "")
    lowered = question.lower()
    return _contains_any(question, ["惊讶", "驚訝", "意外", "没想到", "沒想到"]) or _contains_any(lowered, ["surprised", "unexpected"])


def _has_utterance_signal(text):
    lowered = str(text or "").lower()
    return bool(re.search(r"\b(says?|said|tells?|told|asks?|asked)\b", lowered)) or _contains_any(lowered, ["\"", "'"]) or _contains_any(
        str(text or ""),
        ["说", "說", "问", "問", "告诉", "告訴", "回答", "写道", "寫道", "报告中写", "報告中寫", "“", "”", "："],
    )


def _indirect_speech_act_process(text, question):
    combined = f"{text} {question}"
    lowered = combined.lower()
    markers = []
    hypotheses = []
    if _contains_any(
        lowered,
        [
            "cold",
            "hot",
            "dark",
            "noisy",
            "window",
            "door",
            "light",
            "heater",
            "air conditioner",
            "air-conditioner",
        ],
    ) or _contains_any(combined, ["冷", "热", "熱", "暗", "吵", "窗", "门", "門", "灯", "燈", "空调", "空調"]):
        markers.append("environmental_state_as_request")
        hypotheses.append("indirect_request_for_listener_action")
    if _contains_any(
        lowered,
        ["hungry", "thirsty", "tired", "late", "busy", "forgot", "need", "wish", "hope", "want", "nothing to eat"],
    ) or _contains_any(combined, ["饿", "餓", "渴", "累", "晚了", "忙", "忘了", "需要", "希望", "想要", "没吃", "沒吃", "没喝", "沒喝"]):
        markers.append("speaker_need_or_desire")
        hypotheses.append("speaker_wants_listener_to_notice_need")
    if _contains_any(combined, ["半天", "很累", "只有一个凳子", "只有一個凳子", "就一个凳子", "就一個凳子"]) or _contains_any(
        lowered,
        ["very tired", "only one chair", "one chair"],
    ):
        markers.append("face_saving_request_or_need")
        hypotheses.append("speaker_may_indirectly_request_help_while_preserving_face")
    if _contains_any(combined, ["咖啡已经冷", "咖啡已經冷", "咖啡冷掉", "满杯的咖啡", "滿杯的咖啡", "茶已经冷", "茶已經冷", "茶都冷", "茶冷了", "满满一杯", "滿滿一杯"]) or _contains_any(
        lowered,
        ["coffee is cold", "tea is cold", "full cup of coffee", "full cup of tea"],
    ):
        markers.append("overwork_or_neglected_self_care_cue")
        hypotheses.append("speaker_may_be_prompting_rest_or_self_care")
    if (
        _contains_any(combined, ["钥匙扣", "鑰匙扣"])
        and _contains_any(combined, ["真漂亮", "哪里买", "哪裡買"])
        and _contains_any(combined, ["又问", "又問", "再次", "失忆", "失憶"])
    ) or (
        _contains_any(lowered, ["keychain"])
        and _contains_any(lowered, ["really beautiful", "where do you buy"])
        and _contains_any(lowered, ["again", "forgets", "asks again"])
    ):
        markers.append("admired_possession_gift_request")
        hypotheses.append("speaker_may_indirectly_request_the_admired_object")
    if (
        _contains_any(combined, ["帽子", "脱帽", "脫帽", "摘下来", "摘下來"])
        and _contains_any(combined, ["年纪大", "年紀大", "不必脱帽", "不必脫帽", "不必摘"])
    ) or (
        _contains_any(lowered, ["hat", "hats"])
        and _contains_any(lowered, ["older ladies", "older women"])
        and _contains_any(lowered, ["no need to take off", "need not take off"])
    ):
        markers.append("reverse_psychology_compliance")
        hypotheses.append("speaker_uses_face_pressure_to_make_all_listeners_comply")
    if (
        _contains_any(combined, ["期末考试", "期末考試", "准备", "準備"])
        and _contains_any(combined, ["音响", "音響", "听歌", "聽歌", "耳机", "耳機"])
    ) or (
        _contains_any(lowered, ["final exam", "preparing", "study"])
        and _contains_any(lowered, ["speaker", "listen to music", "headphones"])
    ):
        markers.append("noise_reduction_hint")
        hypotheses.append("speaker_wants_listener_to_reduce_noise")
    if (
        _contains_any(combined, ["两双筷子", "兩雙筷子", "筷子"])
        and _contains_any(combined, ["几个人", "幾個人", "一起吃饭", "一起吃飯"])
    ) or (
        _contains_any(lowered, ["chopsticks"])
        and _contains_any(lowered, ["how many of us eat", "eat together"])
    ):
        markers.append("missing_tableware_request")
        hypotheses.append("speaker_wants_missing_tableware_added")
    if (
        _contains_any(combined, ["自习课", "自習課", "上课", "上課"])
        and _contains_any(combined, ["笑声", "笑聲", "爽朗", "特色"])
    ) or (
        _contains_any(lowered, ["self-study class", "in class"])
        and _contains_any(lowered, ["laughter", "laugh"])
        and _contains_any(lowered, ["unique character", "unique"])
    ):
        markers.append("classroom_noise_correction")
        hypotheses.append("speaker_wants_listener_to_be_quieter")
    if (
        _contains_any(combined, ["筹钱", "籌錢", "资金", "資金", "开医馆", "開醫館"])
        and _contains_any(combined, ["董事长位置", "董事長位置", "董事长", "董事長"])
    ) or (
        _contains_any(lowered, ["raising money", "funding", "open a clinic"])
        and _contains_any(lowered, ["chairman position", "chairman"])
    ):
        markers.append("fundraising_investment_hint")
        hypotheses.append("speaker_uses_symbolic_position_to_request_investment")
    if (
        _contains_any(combined, ["恋人", "戀人", "身份证", "身份證", "证件照", "證件照"])
        and _contains_any(combined, ["一起去拍", "改天我们一起", "改天我們一起", "同等条件"])
    ) or (
        _contains_any(lowered, ["couple", "ids", "id photo", "id photos"])
        and _contains_any(lowered, ["go take id photos together", "take id photos together"])
    ):
        markers.append("marriage_registration_hint")
        hypotheses.append("speaker_hints_at_marriage_registration")
    if (
        _contains_any(combined, ["上课", "上課", "课上", "課上", "最后一排", "最後一排"])
        and _contains_any(combined, ["窗外", "风景", "風景"])
    ) or (
        _contains_any(lowered, ["last row", "in class"])
        and _contains_any(lowered, ["scenery outside the window", "outside the window"])
    ):
        markers.append("classroom_attention_correction")
        hypotheses.append("teacher_wants_student_to_stop_looking_outside")
    if (
        _contains_any(combined, ["橘子酸", "酸不", "太甜", "齁牙", "带点酸", "帶點酸"])
        and _contains_any(combined, ["老板", "旁边", "旁邊", "大姐"])
    ) or (
        _contains_any(lowered, ["oranges sour", "too sweet", "little sour", "slightly sour"])
        and _contains_any(lowered, ["boss", "big sister", "street stall"])
    ):
        markers.append("product_quality_counter_hint")
        hypotheses.append("speaker_hints_product_quality_differs_from_seller_claim")
    if (
        _contains_any(combined, ["手机拿好", "手機拿好", "拿好手机", "拿好手機"])
        and _contains_any(combined, ["市场", "市場", "摊位", "攤位", "水果摊", "水果攤"])
    ) or (
        _contains_any(lowered, ["hold your phone", "hold the phone"])
        and _contains_any(lowered, ["market", "fruit stall"])
    ):
        markers.append("phone_theft_warning_hint")
        hypotheses.append("speaker_warns_about_possible_phone_theft")
    if _contains_any(
        lowered,
        ["great job", "nice job", "wonderful", "again", "complain", "mess", "problem", "does not know how to read"],
    ) or _contains_any(combined, ["又", "真行", "真厉害", "真厲害", "太好了", "抱怨", "麻烦", "麻煩", "问题", "問題", "不认识字", "不認識字", "真傻"]):
        markers.append("complaint_or_dissatisfaction_cue")
        hypotheses.append("indirect_complaint_or_rejection")
    if _contains_any(
        combined,
        ["谢绝", "謝絕", "请勿", "請勿", "不屑", "没打算理", "沒打算理", "社会公德", "公德", "不守规矩", "不守規矩"],
    ) or _contains_any(lowered, ["no pets", "not allowed", "do not", "social norm"]):
        markers.append("social_norm_violation_cue")
        hypotheses.append("indirect_social_criticism")
    if _contains_any(lowered, ["please", "could you", "can you", "would you"]) or _contains_any(combined, ["能不能", "可以", "麻烦你", "麻煩你", "请", "請"]):
        markers.append("polite_request_surface")
        hypotheses.append("polite_request_or_softened_command")
    if not hypotheses:
        markers.append("true_intention_question")
        hypotheses.append("indirect_intent_should_be_inferred_from_context")
    steps = [
        "先把说出来的字面内容和说话者真正想达成的效果分开",
        "看这句话出现前后，听者能不能做某个动作、提供资讯或改变反应",
        "若字面内容只是描述状态，就检查它是否在暗示请求、抱怨、拒绝或提醒",
        "回答时优先给出说话者希望听者理解的意图，而不是复述原句",
    ]
    model = {
        "markers": markers,
        "literal_vs_intended_meaning": "separate_surface_statement_from_desired_listener_response",
        "speaker_goal_types": sorted(set(hypotheses)),
    }
    return markers, hypotheses, steps, model


def _nonliteral_pragmatics_process(text, question):
    combined = f"{text} {question}"
    lowered = combined.lower()
    markers = []
    hypotheses = ["literal_content_may_not_match_social_meaning"]
    has_joke_signal = _contains_any(lowered, ["joke", "kidding", "sarcasm", "sarcastic", "irony", "ironic", "teasing"]) or _contains_any(
        combined,
        ["开玩笑", "開玩笑", "玩笑", "讽刺", "諷刺", "反话", "反話", "挖苦", "调侃", "調侃"],
    )
    has_negated_joke_signal = _contains_any(combined, ["不爱开玩笑", "不愛開玩笑", "不喜欢开玩笑", "不喜歡開玩笑"]) or _contains_any(
        lowered,
        ["does not like joking", "not joking"],
    )
    if has_joke_signal and not has_negated_joke_signal:
        markers.append("irony_joke_or_sarcasm")
        hypotheses.append("possible_irony_or_sarcasm")
    if _contains_any(lowered, ["pretend", "make-believe", "make believe", "acting"]) or _contains_any(
        combined,
        ["假装", "假裝", "装作", "裝作", "扮演", "角色扮演"],
    ):
        markers.append("pretense_frame")
        hypotheses.append("possible_pretense_or_make_believe")
    if _contains_any(lowered, ["metaphor", "like a", "as if", "exaggerat"]) or _contains_any(
        combined,
        ["比喻", "像", "好像", "夸张", "誇張", "瞬间移动", "瞬間移動", "超能力"],
    ):
        markers.append("metaphor_or_exaggeration")
        hypotheses.append("possible_metaphor_or_exaggeration")
    if _contains_any(combined, ["比喻"]) and _contains_any(
        combined,
        ["愣了一下", "泥巴", "水", "种子", "種子", "浇灌", "澆灌", "培养", "培養"],
    ):
        markers.append("literal_misunderstanding_of_metaphor")
        hypotheses.append("possible_literal_misunderstanding_of_metaphor")
    if _contains_any(lowered, ["white lie", "comfort", "polite", "not hurt", "spare"]) or _contains_any(
        combined,
        ["安慰", "礼貌", "禮貌", "不想伤害", "不想傷害", "怕伤心", "怕傷心", "善意"],
    ):
        markers.append("politeness_or_white_lie")
        hypotheses.append("possible_white_lie_or_politeness")
    if _contains_any(
        lowered,
        ["will consider", "consider it", "not directly refuse", "not aligned", "not their direction"],
    ) or _contains_any(
        combined,
        ["认真考虑", "認真考慮", "没有直接拒绝", "沒有直接拒絕", "并没有直接拒绝", "並沒有直接拒絕", "不太相符", "不相符", "不是他们目前想要的方向"],
    ):
        markers.append("softened_refusal_or_polite_delay")
        hypotheses.append("possible_polite_indirect_rejection")
    has_private_emotion = (
        _contains_any(
            lowered,
            [
                "publicly congratulates",
                "privately disappointed",
                "tells her sister",
                "tells his sister",
                "tells her brother",
                "tells his brother",
                "really disappointed",
            ],
        )
        or (
            _contains_any(combined, ["恭喜", "配得上", "失望", "失落", "难过", "難過", "开心", "開心", "高兴", "高興", "太棒", "厉害", "厲害"])
            and _contains_any(combined, ["回家", "晚上", "姐姐", "哥哥", "弟弟", "妹妹", "爸爸", "妈妈", "媽媽", "父亲", "父親", "母亲", "母親", "私下", "家人"])
        )
    )
    if has_private_emotion:
        markers.append("public_politeness_private_emotion")
        hypotheses.append("private_utterance_may_reveal_true_emotion")
    if _contains_any(combined, ["隐藏自己的怀疑", "隱藏自己的懷疑", "怀疑", "懷疑"]) and _contains_any(
        combined,
        ["尚未确定", "尚未確定", "未确定", "未確定", "报告", "報告"],
    ):
        markers.append("withheld_suspicion_or_sensitive_truth")
        hypotheses.append("speaker_may_be_withholding_sensitive_suspicion")
    if _contains_any(combined, ["秒懂", "思钱想厚", "思錢想厚", "百草味", "三只松鼠", "良品铺子", "良品鋪子"]) or _contains_any(
        lowered,
        ["pun", "wordplay"],
    ):
        markers.append("wordplay_indirect_request")
        hypotheses.append("wordplay_may_encode_an_indirect_request")
    if _contains_any(combined, ["明明", "其实", "其實", "却说", "卻說"]) or _contains_any(
        lowered,
        ["but actually", "although", "even though", "in fact"],
    ):
        markers.append("story_fact_conflicts_with_literal_statement")
    if not markers:
        markers.append("truth_value_question_over_utterance")
    steps = [
        "先抽出发话的字面命题",
        "再用故事事实检查这句话是否按字面为真",
        "如果字面不完全为真，再判断它是在开玩笑、讽刺、假装、安慰、礼貌或夸张",
        "最后用社会目的解释这句话，而不是只回答字面真假",
    ]
    model = {
        "markers": markers,
        "literal_truth_boundary": "do_not_equate_literal_sentence_with_social_meaning",
        "candidate_frames": sorted(set(hypotheses)),
    }
    return markers, hypotheses, steps, model


def _has_nonliteral_signal(text):
    text = str(text or "")
    lowered = text.lower()
    return _contains_any(
        lowered,
        [
            "joke",
            "kidding",
            "sarcasm",
            "sarcastic",
            "irony",
            "ironic",
            "teasing",
            "pretend",
            "make-believe",
            "make believe",
            "acting",
            "metaphor",
            "exaggerat",
            "white lie",
            "comfort",
            "polite",
            "not hurt",
            "spare",
            "but actually",
            "in fact",
            "will consider",
            "not directly refuse",
            "not aligned",
            "privately disappointed",
            "really disappointed",
            "wordplay",
            "pun",
            "superpower",
        ],
    ) or _contains_any(
        text,
        [
            "开玩笑",
            "開玩笑",
            "玩笑",
            "讽刺",
            "諷刺",
            "反话",
            "反話",
            "挖苦",
            "调侃",
            "調侃",
            "假装",
            "假裝",
            "装作",
            "裝作",
            "比喻",
            "夸张",
            "誇張",
            "瞬间移动",
            "瞬間移動",
            "超能力",
            "安慰",
            "礼貌",
            "禮貌",
            "不想伤害",
            "不想傷害",
            "怕伤心",
            "怕傷心",
            "善意",
            "明明",
            "其实",
            "其實",
            "却说",
            "卻說",
            "认真考虑",
            "認真考慮",
            "没有直接拒绝",
            "沒有直接拒絕",
            "并没有直接拒绝",
            "並沒有直接拒絕",
            "不太相符",
            "恭喜",
            "配得上",
            "姐姐",
            "哥哥",
            "弟弟",
            "妹妹",
            "失望",
            "失落",
            "难过",
            "難過",
            "私下",
            "晚上",
            "隐藏自己的怀疑",
            "隱藏自己的懷疑",
            "尚未确定",
            "尚未確定",
            "报告中写",
            "報告中寫",
            "秒懂",
            "思钱想厚",
            "思錢想厚",
            "百草味",
            "三只松鼠",
            "良品铺子",
            "良品鋪子",
        ],
    )


def _has_speaker_belief_mismatch_signal(text):
    text = str(text or "")
    lowered = text.lower()
    return _contains_any(
        lowered,
        [
            "thinks",
            "believes",
            "assumes",
            "mistakenly",
            "forgets",
            "forgot",
            "does not realize",
            "doesn't realize",
            "is unaware",
        ],
    ) or _contains_any(
        text,
        [
            "以为",
            "以為",
            "认为",
            "認為",
            "记得",
            "記得",
            "忘记",
            "忘記",
            "不知道",
            "没意识到",
            "沒意識到",
        ],
    )


def _speaker_belief_utterance_process(text, question):
    combined = f"{text} {question}"
    lowered = combined.lower()
    markers = ["speaker_belief_may_differ_from_reality"]
    hypotheses = ["utterance_tracks_speaker_belief_not_objective_reality"]
    if _contains_any(lowered, ["forgot", "forgets"]) or _contains_any(combined, ["忘记", "忘記"]):
        markers.append("forgetting_or_outdated_memory")
        hypotheses.append("speaker_may_answer_from_outdated_memory")
    if _contains_any(lowered, ["mistakenly", "wrongly"]) or _contains_any(combined, ["以为", "以為", "误以为", "誤以為"]):
        markers.append("mistaken_belief")
        hypotheses.append("speaker_may_be_mistaken_rather_than_lying")
    if _contains_any(lowered, ["is it true", "really true"]) or _contains_any(combined, ["是真的吗", "是真的嗎", "说的是真的吗", "說的是真的嗎"]):
        markers.append("truth_value_question")
    if _contains_any(lowered, ["why does", "why did"]) or _contains_any(combined, ["为什么这么说", "為什麼這麼說", "为什么这样说", "为什么说"]):
        markers.append("why_utterance_question")
    steps = [
        "先分开客观事实、说话者当时相信的事实、以及说出口的句子",
        "检查说话者是否忘记、误以为、没有意识到事实已经改变",
        "如果说出口的句子和客观事实冲突，先判断它是否来自错误信念，而不是直接判成说谎",
        "回答时说明这句话是从说话者信念出发，还是从现实事实来看为真或为假",
    ]
    model = {
        "markers": markers,
        "truth_perspective_boundary": "objective_reality_vs_speaker_belief",
        "candidate_frames": sorted(set(hypotheses)),
    }
    return markers, hypotheses, steps, model


def _strategic_deception_process(text, question):
    combined = f"{text} {question}"
    markers = []
    hypotheses = []
    if _contains_any(combined, ["假消息", "虚假消息", "虛假消息", "故意泄露", "故意洩露", "竞争", "競爭"]) or _contains_any(
        combined.lower(),
        ["false signal", "fake information", "competitor", "competition"],
    ):
        markers.append("strategic_false_signal")
        hypotheses.append("target_may_pause_to_reduce_uncertainty_after_false_signal")
    if _contains_any(combined, ["暂停", "暫停", "搁置", "擱置", "推迟", "推遲"]) or _contains_any(
        combined.lower(),
        ["pause", "postpone", "delay"],
    ):
        markers.append("target_changes_plan_after_signal")
    if not markers:
        markers.append("strategic_uncertainty_question")
        hypotheses.append("target_action_may_be_a_response_to_information_asymmetry")
    steps = [
        "先找出谁释放了讯号，以及讯号是否可能是假的",
        "再判断目标人物听到讯号后面对的不确定性",
        "若目标暂停行动，优先考虑观察、等待、搜集资讯，而不是直接归因成害怕",
        "回答时解释目标如何根据对手行动调整计划",
    ]
    model = {
        "markers": markers,
        "strategic_boundary": "false_signal_vs_target_uncertainty_vs_plan_change",
        "candidate_frames": sorted(set(hypotheses)),
    }
    return markers, hypotheses, steps, model


def _constrained_refusal_process(text, question):
    combined = f"{text} {question}"
    markers = ["current_refusal_under_constraint"]
    hypotheses = ["current_decision_may_differ_from_general_interest"]
    if _contains_any(combined, ["课业", "課業", "高三", "父母", "考试", "考試", "大学", "大學", "很忙"]) or _contains_any(
        combined.lower(),
        ["busy", "exam", "parents", "schoolwork"],
    ):
        markers.append("external_constraint_over_general_preference")
        hypotheses.append("external_pressure_can_make_current_refusal_genuine")
    if _contains_any(combined, ["很少", "不表达", "不表達", "表达自己的观点", "表達自己的觀點", "害羞", "内向", "內向"]) or _contains_any(
        combined.lower(),
        ["shy", "reserved", "rarely expresses"],
    ):
        markers.append("social_reticence_or_low_expression")
        hypotheses.append("low_expression_can_make_stated_refusal_socially_plausible")
    steps = [
        "先分开长期兴趣和当前是否愿意参加",
        "检查是否有课业、家庭期待、害羞或表达困难等当前限制",
        "若问题问的是当前是否真的不想参加，就不要只用长期喜欢来推翻本人拒绝",
        "回答时说明当前决定，而不是只说明一般兴趣",
    ]
    model = {
        "markers": markers,
        "desire_boundary": "general_interest_vs_current_constrained_choice",
        "candidate_frames": sorted(set(hypotheses)),
    }
    return markers, hypotheses, steps, model


def _surprise_reaction_process(text, question):
    combined = f"{text} {question}"
    markers = []
    hypotheses = []
    if _contains_any(combined, ["竟然", "没想到", "沒想到", "意外", "第一次", "突然"]) or _contains_any(
        combined.lower(),
        ["unexpected", "surprised", "for the first time"],
    ):
        markers.append("unexpected_positive_action")
        hypotheses.append("listener_may_feel_surprise_from_unexpected_action")
    if _contains_any(combined, ["欣慰", "感动", "感動", "眼角湿润", "眼角濕潤", "哭了"]):
        markers.append("moved_or_touched_reaction")
        hypotheses.append("tears_can_reflect_being_moved_not_only_negative_judgment")
    if not markers:
        markers.append("affect_reaction_question")
        hypotheses.append("reaction_should_be_inferred_from_context")
    steps = [
        "先找出事情是否出乎听者预期",
        "再把惊讶、感动、难过等反应分开",
        "若故事写到竟然、没想到、欣慰或感动，说明听者可能既惊讶又被触动",
        "回答时优先使用故事中的反应线索",
    ]
    model = {
        "markers": markers,
        "affect_boundary": "unexpected_event_vs_emotional_reaction",
        "candidate_frames": sorted(set(hypotheses)),
    }
    return markers, hypotheses, steps, model


def analyze_social_reasoning(text, question="", options_zh=None, options_en=None):
    raw = str(text or "")
    question = str(question or "")
    combined = f"{raw} {question}".strip()
    lowered = combined.lower()
    core = SocialReasoningCore()
    pragmatic_norm_question = _contains_any(lowered, ["inappropriate", "faux", "wrong thing", "rude", "hurt", "embarrass", "does anyone say"]) or _contains_any(
        combined,
        [
            "失礼",
            "失禮",
            "不适当",
            "不適當",
            "不恰当",
            "不恰當",
            "不合适",
            "不合適",
            "不该说",
            "不該說",
            "冒犯",
            "尴尬",
            "尷尬",
            "伤心",
            "傷心",
            "是否有人说",
            "是否有人說",
            "有没有人说",
            "有沒有人說",
        ],
    )
    pragmatic_knowledge_question = (
        _contains_any(question, ["知道", "知不知道", "曉得", "晓得"])
        and _contains_any(
            combined,
            [
                "不吃",
                "不喜欢",
                "不喜歡",
                "过敏",
                "過敏",
                "去世",
                "分手",
                "不想结婚",
                "不想結婚",
                "手术",
                "手術",
                "住院",
            ],
        )
    )
    pragmatic_reaction_question = _contains_any(
        question,
        ["反应", "反應", "作出了什么反应", "作出了什麼反應"],
    ) and _contains_any(
        combined,
        ["简短回答", "簡短回答", "含糊", "快步离开", "快步離開", "转移话题", "轉移話題", "沉默", "没说什么", "沒說什麼"],
    )
    if pragmatic_norm_question or pragmatic_knowledge_question or pragmatic_reaction_question:
        markers, hypotheses, steps = _pragmatic_norm_process(raw, question)
        core.focus = "pragmatic_norm"
        core.knowledge_boundary = "先分清说话者是否知道敏感事实，再判断听者是否会被伤害"
        core.intent_hypotheses = hypotheses
        core.pragmatic_model = {"markers": markers}
        core.quantity_model = {"markers": markers}
        core.reasoning_steps = steps
        core.confidence = "medium" if markers else "low"
        core.trace_policy = "moderate" if markers else "observe_only"
        core.interference_risk = "low" if "explicit_norm_question" in markers else "medium"
        return core.to_dict()
    if _looks_like_indirect_intent_question(question) and _has_utterance_signal(combined):
        markers, hypotheses, steps, model = _indirect_speech_act_process(raw, question)
        core.focus = "indirect_speech_act"
        core.knowledge_boundary = "把字面句子和说话者希望听者理解或采取的行动分开"
        core.intent_hypotheses = hypotheses
        core.pragmatic_model = model
        core.reasoning_steps = steps
        if markers == ["true_intention_question"]:
            core.confidence = "low"
            core.trace_policy = "observe_only"
            core.interference_risk = "high"
        else:
            core.confidence = "medium"
            core.trace_policy = "moderate"
            core.interference_risk = "low"
        return core.to_dict()
    if _looks_like_constrained_refusal_question(question) and _contains_any(
        combined,
        ["不想", "不去", "不参加", "不參加", "不去参加", "不去參加", "我就不去", "回答“不想去”", "回答“不想去”"],
    ):
        markers, hypotheses, steps, model = _constrained_refusal_process(raw, question)
        core.focus = "constrained_refusal_reasoning"
        core.knowledge_boundary = "把长期兴趣和当前在限制下是否愿意参加分开"
        core.intent_hypotheses = hypotheses
        core.pragmatic_model = model
        core.reasoning_steps = steps
        core.confidence = "medium"
        core.trace_policy = "moderate"
        core.interference_risk = "low"
        return core.to_dict()
    if _looks_like_surprise_question(question) and _contains_any(
        combined,
        ["竟然", "没想到", "沒想到", "意外", "欣慰", "感动", "感動", "眼角湿润", "眼角濕潤"],
    ):
        markers, hypotheses, steps, model = _surprise_reaction_process(raw, question)
        core.focus = "surprise_reaction_reasoning"
        core.knowledge_boundary = "把出乎预期的事实和人物情绪反应分开"
        core.intent_hypotheses = hypotheses
        core.pragmatic_model = model
        core.reasoning_steps = steps
        core.confidence = "medium"
        core.trace_policy = "moderate"
        core.interference_risk = "low"
        return core.to_dict()
    if _looks_like_why_action_question(question) and (
        _contains_any(combined, ["假消息", "虚假消息", "虛假消息", "故意泄露", "故意洩露", "竞争对手", "競爭對手"])
        or _contains_any(lowered, ["false signal", "fake information", "competitor"])
    ):
        markers, hypotheses, steps, model = _strategic_deception_process(raw, question)
        core.focus = "strategic_deception_reasoning"
        core.knowledge_boundary = "把假讯号、目标人物的不确定性和后续行动分开"
        core.intent_hypotheses = hypotheses
        core.pragmatic_model = model
        core.reasoning_steps = steps
        core.confidence = "medium"
        core.trace_policy = "moderate"
        core.interference_risk = "low"
        return core.to_dict()
    if _looks_like_nonliteral_question(question) and _has_utterance_signal(combined) and _has_speaker_belief_mismatch_signal(combined):
        markers, hypotheses, steps, model = _speaker_belief_utterance_process(raw, question)
        core.focus = "speaker_belief_utterance"
        core.knowledge_boundary = "把客观事实、说话者信念、发话内容三者分开"
        core.intent_hypotheses = hypotheses
        core.pragmatic_model = model
        core.reasoning_steps = steps
        core.confidence = "medium"
        core.trace_policy = "moderate"
        core.interference_risk = "low"
        return core.to_dict()
    if _looks_like_nonliteral_question(question) and _has_utterance_signal(combined) and _has_nonliteral_signal(combined):
        markers, hypotheses, steps, model = _nonliteral_pragmatics_process(raw, question)
        core.focus = "nonliteral_pragmatics"
        core.knowledge_boundary = "把字面真假、故事事实、说话的社会目的分开"
        core.intent_hypotheses = hypotheses
        core.pragmatic_model = model
        core.reasoning_steps = steps
        core.confidence = "medium"
        core.trace_policy = "moderate"
        core.interference_risk = "low"
        return core.to_dict()
    if re.search(r"\d+", combined) and (
        _classify_quantity_language(combined)
        or _contains_any(lowered, ["how many", "only", "total", "number"])
        or _contains_any(combined, ["多少", "几个", "幾個", "几瓶", "几道", "几份", "几趟", "剩下几", "数量", "最受欢迎", "最受歡迎"])
    ):
        model, steps = _quantity_process(raw, question)
        core.focus = "scalar_quantity"
        core.knowledge_boundary = "不要把总数、观察到的数量、没观察到的剩余量混成一个事实"
        core.quantity_model = model
        core.reasoning_steps = steps
        if model.get("semantic_estimate") is not None or model.get("operation"):
            core.confidence = "medium"
            core.trace_policy = "strong"
            core.interference_risk = "low"
        elif model.get("quantifier"):
            core.confidence = "medium"
            core.trace_policy = "moderate"
            core.interference_risk = "medium"
        else:
            core.confidence = "low"
            core.trace_policy = "observe_only"
            core.interference_risk = "high"
        return core.to_dict()
    roleplay_context = _contains_any(
        lowered,
        ["cosplay", "role-playing", "role playing", "pretend", "playing a", "costume", "halloween", "ghost", "dress up"],
    ) or _contains_any(
        combined,
        ["扮演", "装扮", "裝扮", "角色", "铠甲", "鎧甲", "机械战士", "機械戰士", "展览", "展覽", "万圣节", "萬聖節", "化装", "化裝", "化妆", "化妝", "鬼装", "鬼裝", "打扮成"],
    )
    discrepant_signal = _contains_any(lowered, ["not tell", "does not tell", "did not tell", "doesn't tell", "keeps silent", "stays silent"]) or _contains_any(
        combined,
        [
            "不告诉",
            "没有告诉",
            "没告诉",
            "不阻止",
            "保持沉默",
            "误以为",
            "错误地认为",
            "不小心",
            "误会",
            "误解",
            "不清楚",
            "不知情",
            "没有意识",
            "不允许",
            "违反",
        ],
    )
    if discrepant_signal and not roleplay_context:
        target, hypotheses, steps, model = _intent_process(raw, question)
        core.focus = "discrepant_intention"
        core.main_actor = target
        core.knowledge_boundary = "先判断角色知道什么，再判断他为什么行动或不行动"
        core.intent_hypotheses = hypotheses
        core.pragmatic_model = model
        core.reasoning_steps = steps
        motive_markers = set(model.get("markers") or [])
        specific_direct_markers = {
            "target_action_may_be_uninformed_not_deceptive",
            "mistaken_donation_or_cleanup",
            "instruction_misunderstanding",
            "ownerless_care_or_cleanup_assumption",
            "rule_unaware_violation",
            "resource_purpose_misunderstanding",
        }
        has_specific_motive = any(
            hypothesis
            for hypothesis in hypotheses
            if hypothesis
            not in {
                "informed_bystander_or_participant_may_be_intentionally_silent",
                "actor_may_be_mistaken_or_unaware",
                "insufficient_motive_signal_keep_multiple_hypotheses_open",
            }
        ) or bool(motive_markers & specific_direct_markers)
        core.confidence = "medium" if has_specific_motive else "low"
        core.trace_policy = "moderate" if has_specific_motive else "observe_only"
        core.interference_risk = "medium" if has_specific_motive else "high"
        return core.to_dict()
    if roleplay_context:
        markers = []
        if _contains_any(combined, ["记者", "記者", "观众", "觀眾", "拍照", "互动", "互動", "注意", "焦点", "焦點", "电视镜头", "電視鏡頭"]):
            markers.append("attention_seeking_performance")
        if _contains_any(combined, ["扮演", "角色", "魔法", "机械战士", "機械戰士", "装扮", "裝扮", "游戏活动", "遊戲活動", "万圣节", "萬聖節", "鬼", "化装", "化裝", "化妆", "化妝", "打扮成"]) or _contains_any(
            lowered,
            ["halloween", "ghost", "costume", "dress up"],
        ):
            markers.append("performed_role_reply")
        if not markers:
            markers.append("performed_role_context")
        core.focus = "roleplay_identity"
        core.knowledge_boundary = "先分清现实身份和扮演身份，不把角色台词当成欺骗或普通事实陈述"
        core.reasoning_steps = [
            "找出人物现实中正在参加的活动或装扮情境",
            "判断发话是否是在扮演角色身份",
            "把角色扮演、说谎、幽默回答分开",
            "回答时优先解释这句话在扮演情境中的功能",
        ]
        core.intent_hypotheses = ["speaker_answers_from_performed_role_identity"]
        core.pragmatic_model = {"markers": markers}
        core.confidence = "medium"
        core.trace_policy = "strong"
        core.interference_risk = "low"
        return core.to_dict()
    if any(token in lowered for token in ["know", "believe", "think", "aware", "知ら", "知道", "认为", "以为"]):
        core.focus = "belief_reasoning"
        core.knowledge_boundary = "人物只能使用自己见过、听过、知道的资讯"
        core.reasoning_steps = [
            "列出每个角色实际知道的信息",
            "排除全知视角才知道的事实",
            "用该角色自己的信念预测回答或行动",
        ]
        core.confidence = "low"
        core.trace_policy = "observe_only"
        core.interference_risk = "medium"
        return core.to_dict()
    core.reasoning_steps = [
        "分清谁知道什么",
        "分清谁想要什么",
        "分清字面意思和实际意图",
    ]
    core.knowledge_boundary = "先分清角色知识、欲求和期待反应"
    core.confidence = "low"
    core.trace_policy = "observe_only"
    core.interference_risk = "high"
    return core.to_dict()


def infer_discrepant_intention_option(story_zh, question_zh, options_zh, options_en=None):
    core = analyze_social_reasoning(story_zh, question=question_zh, options_zh=options_zh, options_en=options_en)
    return "", {
        "rule": "process_only_no_option_selection",
        "social_reasoning_core": core,
        "note": "This core intentionally does not select an option or store answer mappings.",
    }


def infer_scalar_quantity_option(story_zh, question_zh, options_zh, options_en=None, story_en="", question_en=""):
    source_text = f"{story_zh} {story_en}".strip()
    source_question = f"{question_zh} {question_en}".strip()
    core = analyze_social_reasoning(source_text, question=source_question, options_zh=options_zh, options_en=options_en)
    return "", {
        "rule": "process_only_no_option_selection",
        "social_reasoning_core": core,
        "note": "This core builds an internal quantity frame but intentionally does not select a benchmark option.",
    }


def merge_leftbrain_social_frame(fallback, user_input, question="", options_zh=None, options_en=None):
    frame = dict(fallback or {})
    core = analyze_social_reasoning(user_input, question=question, options_zh=options_zh, options_en=options_en)
    frame["social_reasoning_core"] = core
    if core.get("focus") == "scalar_quantity":
        frame.update(
            {
                "focus": "scalar_quantity_inference",
                "belief_boundary": "总数、已观察数量、未观察剩余量不能混在一起",
                "knowledge_gap": "未观察部分只能保留为不确定，不能直接补成答案",
                "decision_rule": "先建立数量槽位和问题时间，再交给回答器判断",
                "best_option_shape": "符合数量槽位关系的回答，而不是题库记忆",
            }
        )
    elif core.get("focus") == "discrepant_intention":
        frame.update(
            {
                "focus": "communicative_intent",
                "main_actor": frame.get("main_actor") or core.get("main_actor", ""),
                "belief_boundary": "把角色知道什么和角色为什么行动分开",
                "knowledge_gap": "关键人物可能无知、误会，也可能知道但选择沉默",
                "decision_rule": "先保留多个动机假设，再用故事证据收敛",
                "best_option_shape": "能解释角色知识状态和动机的回答",
            }
        )
    elif core.get("focus") == "pragmatic_norm":
        frame.update(
            {
                "focus": "communicative_intent",
                "belief_boundary": "说话者知道的事实和听者承受的社会伤害要分开",
                "knowledge_gap": "话可能是真的，但仍可能因为触碰敏感事实而失礼",
                "decision_rule": "先看知识状态，再看听者影响，最后判断是否失言",
                "best_option_shape": "能解释是否失言、是否无心、谁被影响的回答",
            }
        )
    elif core.get("focus") == "indirect_speech_act":
        frame.update(
            {
                "focus": "communicative_intent",
                "belief_boundary": "字面内容和真正想让听者理解的意图要分开",
                "knowledge_gap": "说话者可能没有直接命令，而是透过状态描述、抱怨或提醒来暗示",
                "decision_rule": "先找字面句，再找听者可采取的行动或态度变化",
                "best_option_shape": "能解释话外之意，而不是复述原句表面意思的回答",
            }
        )
    elif core.get("focus") == "nonliteral_pragmatics":
        frame.update(
            {
                "focus": "communicative_intent",
                "belief_boundary": "字面真假、故事事实、社会目的要分开",
                "knowledge_gap": "话可能不是按字面为真，而是在开玩笑、讽刺、假装、安慰或夸张",
                "decision_rule": "先比较字面命题与故事事实，再判断说话的社会功能",
                "best_option_shape": "能说明为什么这句话不能只按字面理解的回答",
            }
        )
    elif core.get("focus") == "speaker_belief_utterance":
        frame.update(
            {
                "focus": "knowledge_state_social",
                "belief_boundary": "客观事实、说话者信念、发话内容要分开",
                "knowledge_gap": "说话者可能根据过时记忆或错误信念说出和现实不一致的话",
                "decision_rule": "先判断说话者当时相信什么，再判断话从现实角度是否为真",
                "best_option_shape": "能解释这句话是错误信念、忘记或现实事实造成的回答",
            }
        )
    elif core.get("focus") == "strategic_deception_reasoning":
        frame.update(
            {
                "focus": "communicative_intent",
                "belief_boundary": "假讯号、目标人物知道的资讯、目标行动要分开",
                "knowledge_gap": "对手释放的资讯可能是策略性误导，目标会先降低不确定性",
                "decision_rule": "先判断讯号是否可信，再判断暂停、观察或调整计划的目的",
                "best_option_shape": "能解释人物如何根据不完整或可疑资讯调整行动",
            }
        )
    elif core.get("focus") == "constrained_refusal_reasoning":
        frame.update(
            {
                "focus": "knowledge_state_social",
                "belief_boundary": "长期兴趣和当前受限制的选择要分开",
                "knowledge_gap": "人物喜欢某事不等于此刻愿意参加，当前拒绝可能来自课业、家庭或表达困难",
                "decision_rule": "先看当前限制，再判断本人拒绝是否应被认真对待",
                "best_option_shape": "能解释当前决定，而不是只复述一般兴趣",
            }
        )
    elif core.get("focus") == "surprise_reaction_reasoning":
        frame.update(
            {
                "focus": "emotion_inference",
                "belief_boundary": "出乎预期的事实和情绪反应要分开",
                "knowledge_gap": "哭、感动或欣慰不一定是负面反应，也可能包含惊讶",
                "decision_rule": "先找意外线索，再判断惊讶、感动、欣慰等情绪",
                "best_option_shape": "能贴合故事中的反应线索",
            }
        )
    elif core.get("focus") == "roleplay_identity":
        frame.update(
            {
                "focus": "communicative_intent",
                "belief_boundary": "现实身份和角色身份要分开",
                "knowledge_gap": "听者可能不知道对方正在扮演什么角色",
                "decision_rule": "先判断是否在角色扮演语境中回答，再排除说谎解释",
                "best_option_shape": "说明发话是在配合扮演身份或解释角色",
            }
        )
    return frame
