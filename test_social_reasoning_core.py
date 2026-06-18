import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_test_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        clean_env["URUHA_SKIP_AUTO_VENV"] = "1"
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_test_python()

from uruha_social_reasoning import (
    analyze_social_reasoning,
    format_candidate_verifier_trace,
    format_social_reasoning_trace,
    infer_discrepant_intention_option,
    infer_scalar_quantity_option,
    merge_leftbrain_social_frame,
    should_inject_social_reasoning_core,
    verify_social_reasoning_candidates,
)


class TestSocialReasoningCore(unittest.TestCase):
    def test_scalar_quantity_core_generalizes_to_non_tombench_story(self):
        story = "仓库共有40个箱子，大多数箱子贴着红色标签。检查后发现只有6个是蓝色标签。"
        question = "检查之后，大概还有多少个红色标签箱子？"
        options = {
            "A": "10个左右",
            "B": "20个左右",
            "C": "30个左右",
            "D": "39个左右",
        }
        answer, payload = infer_scalar_quantity_option(story, question, options)
        self.assertEqual(answer, "")
        self.assertEqual(payload["social_reasoning_core"]["focus"], "scalar_quantity")
        self.assertEqual(payload["rule"], "process_only_no_option_selection")
        self.assertNotIn("selected_option", payload["social_reasoning_core"])
        self.assertIn("visible_numbers", payload["social_reasoning_core"]["quantity_model"])
        self.assertTrue(should_inject_social_reasoning_core(payload["social_reasoning_core"]))

    def test_discrepant_intention_core_generalizes_to_competitive_silence(self):
        story = (
            "主管正在考虑选择谁晋升。小林知道小周的材料放错了位置，"
            "但小林和小周正在竞争同一个名额，所以选择不告诉主管。"
        )
        question = "小林不告诉主管的行为，最可能是什么原因？"
        options_zh = {
            "A": "小林误以为材料没有放错。",
            "B": "小林因为竞争晋升而故意保持沉默。",
            "C": "小林完全不知道小周有材料。",
            "D": "小林只是随手忘记了。",
        }
        answer, payload = infer_discrepant_intention_option(story, question, options_zh)
        self.assertEqual(answer, "")
        self.assertEqual(payload["rule"], "process_only_no_option_selection")
        self.assertIn("possible_competition_motive", payload["social_reasoning_core"]["intent_hypotheses"])
        self.assertNotIn("selected_option", payload["social_reasoning_core"])
        self.assertEqual(payload["social_reasoning_core"]["trace_policy"], "moderate")

    def test_discrepant_candidate_verifier_handles_motive_and_knowledge_families(self):
        cases = [
            (
                "mistaken_donation_or_cleanup",
                "李雷把他的笔记本电脑忘在了图书管里。韩梅梅在图书馆志愿服务，发现了这台电脑，但以为是有人捐赠的旧电脑，于是她将其放入了捐赠箱。李华看见了，他知道这是李雷的电脑，但他一直是班上的第二名，每次多落李雷一名，故意不告诉韩梅梅真相。",
                "韩梅梅的行为可能是出于什么样的意图？",
                {
                    "A": "A. 韩梅梅可能认为这台电脑是图书馆的冗余设备，所以她决定将其放入捐赠箱以清理空间。",
                    "B": "B. 韩梅梅可能由于个人对电子设备的不感兴趣，对电脑的归属不加考虑，随意将其视为可捐赠物品。",
                    "C": "C. 韩梅梅可能想要帮助那些需要电脑却买不起的人，因此她故意将这台看似无主的电脑放入捐赠箱。",
                    "D": "D. 韩梅梅可能无意识或不知情，因为她错误地认为李雷的笔记本电脑是有人捐赠的旧电脑，因此放入了捐赠箱。",
                },
                "D",
            ),
            (
                "academic_competition_sabotage",
                "李雷把他的笔记本电脑忘在了图书管里。韩梅梅误以为这是有人捐赠的旧电脑。李华看见了，他知道这是李雷的电脑，但他一直是班上的第二名，每次多落李雷一名，故意不告诉韩梅梅真相。",
                "李华的行为可能是出于什么样的意图?",
                {
                    "A": "A. 李华可能因为担心自己会被卷入麻烦，所以选择不揭露真相。",
                    "B": "B. 李华希望李雷没有电脑而无法复习课业，从而在学习上超越他。",
                    "C": "C. 李华可能因为与李雷有矛盾，选择不告诉李雷他被误处理了的笔记本电脑。",
                    "D": "D. 李华可能认为电脑是李雷故意留在图书馆的，为了测试他人的诚信和道德。",
                },
                "B",
            ),
            (
                "promotion_competition_sabotage",
                "经理艾米丽错误地将裁员文件放入普通文件夹中。清洁工鲍勃误以为这是废纸。高级主管苏珊不告诉鲍勃这件事，因为她与艾米丽在竞争经理的岗位。",
                "苏珊的行为可能是出于什么样的意图?",
                {
                    "A": "A. 苏珊可能因为工作繁忙，没有时间告诉鲍勃文件的重要性。",
                    "B": "B. 苏珊认为鲍勃会自己意识到错误并承认，因此选择不告诉他。",
                    "C": "C. 苏珊可能因为想削弱艾米丽的地位，故意选择沉默以看到她因失误受到责难。",
                    "D": "D. 苏珊可能因为与艾米丽有矛盾，选择不告诉鲍勃文件的重要性。",
                },
                "C",
            ),
            (
                "promotion_competition_sabotage",
                "为了晋升到更高层次的职位，艾米、鲍勃和克莱尔需要在项目中取得成绩。鲍勃看到项目的重要信息，但不知道那是艾米未公开分享的文件。克莱尔知道上司在她与艾米之间纠结选择谁晋升，所以决定保持沉默。",
                "克莱尔的行为可能是出于什么样的意图?",
                {
                    "A": "A. 克莱尔是为了与艾米竞争，她希望利用这个机会超越鲍勃。",
                    "B": "B. 克莱尔可能认为鲍勃已经知道这些信息是艾米的，并认为他有责任处理这个问题。",
                    "C": "C. 克莱尔可能担心介入会影响她自己在公司中的声誉和立场。",
                    "D": "D. 克莱尔可能以为艾米有意将信息留在鲍勃的办公桌上，作为测试他的诚信。",
                },
                "A",
            ),
            (
                "instruction_misunderstanding",
                "李娜负责收集捐赠的衣物。阿里是她的助手，由于误会，他把一位居民特别标记要捐给特定慈善机构的衣物错误地打包到了一般捐赠箱中。",
                "阿里的行为可能是出于什么样的意图？",
                {
                    "A": "A. 阿里可能是为了快速完成任务而忽视了特殊标记。",
                    "B": "B. 阿里可能因为对捐赠衣物不感兴趣，所以没有注意到特殊标记。",
                    "C": "C. 阿里可能是由于误解指示，错误地认为所有捐赠衣物都应统一处理。",
                    "D": "D. 阿里可能认为特殊标记不重要，因此没有按照指示行事。",
                },
                "C",
            ),
            (
                "contest_competition_sabotage",
                "利亚在烹饪比赛中准备特别菜肴。萨姆不小心把错误调料加入菜中，以为这是利亚的指示。克里斯是利亚的对手，知道了萨姆的错误，但决定不告诉任何人。",
                "克里斯的行为可能是出于什么样的意图？",
                {
                    "A": "A. 克里斯可能因为对比赛规则的理解有误，认为不应干涉对手。",
                    "B": "B. 克里斯可能因为希望在比赛中赢得萨姆。",
                    "C": "C. 克里斯可能因为认为萨姆的错误不重要，故意忽略。",
                    "D": "D. 克里斯可能因为想看看错误调料会产生什么效果。",
                },
                "B",
            ),
            (
                "ownerless_care_or_cleanup_assumption",
                "小明和小刚一起去山上探险。他们发现一只非常可爱的小狗，小明很喜欢狗，将它抱回家养。小刚知道这只小狗是村里王大爷的，但他选择保持沉默。",
                "小明带走小狗的行为可能是出于什么样的意图？",
                {
                    "A": "A. 小明可能因为喜欢小狗，故意不寻找狗的主人。",
                    "B": "B. 小明可能认为带走小狗是给它一个更好的家。",
                    "C": "C. 小明可能因为不知情，认为那只无主的小狗需要被照顾。",
                    "D": "D. 小明可能因为想要一个宠物而没有考虑狗的真正主人。",
                },
                "C",
            ),
            (
                "protect_friend_from_disappointment",
                "小明和小刚是好朋友，在山顶发现一只小狗，小明很喜欢狗。小刚知道这只小狗是村里的老人王大爷的，但他选择保持沉默。",
                "小刚不告诉小明小狗的真正主人可能是出于什么样的意图？",
                {
                    "A": "A. 小刚可能因为害怕小明的反应而选择不告诉真相。",
                    "B": "B. 小刚可能认为小明会自己发现真相。",
                    "C": "C. 小刚可能认为王大爷可以找到其他小狗。",
                    "D": "D. 小刚可能不想让小明失望，因此选择了沉默。",
                },
                "D",
            ),
            (
                "ownerless_care_or_cleanup_assumption",
                "张伟无意中在市场后面发现一箱没人管、也很碍事的苹果，便把它们带回家。王莉知道这些苹果是李华的，但她和李华关系不好，因此选择保持沉默。",
                "张伟带走苹果的行为可能是出于什么样的意图？",
                {
                    "A": "A. 张伟可能因为认为苹果无主，而认为自己在帮助清理市场。",
                    "B": "B. 张伟可能因为想要免费的苹果，故意不找寻苹果的主人。",
                    "C": "C. 张伟可能认为拿走苹果是对市场的一种帮助。",
                    "D": "D. 张伟可能因为喜欢免费的东西而没有考虑苹果的真正主人。",
                },
                "A",
            ),
            (
                "rule_unaware_violation",
                "小华和小强一起去动物园，看到小兔子觉得非常可爱，小强给小兔子喂了胡萝卜。小华知道动物园是不允许私自给动物喂食不明来源的食物的，但他没告诉小强。",
                "小强喂小兔子胡萝卜的行为可能是出于什么样的意图？",
                {
                    "A": "A. 小强想通过喂食来体验与可爱小动物互动，获得满足感。",
                    "B": "B. 小强是在测试小兔子对胡萝卜的反应。",
                    "C": "C. 小强可能不清楚且没有意识到自己违反了规定。",
                    "D": "D. 小强希望通过喂食小兔子来表达自己对动物的关心。",
                },
                "C",
            ),
        ]
        for marker, story, question, options, expected in cases:
            with self.subTest(marker=marker):
                core = analyze_social_reasoning(story, question, options_zh=options)
                self.assertEqual(core["focus"], "discrepant_intention")
                self.assertIn(marker, core["pragmatic_model"]["markers"])
                verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
                self.assertEqual(verifier["top_option"], expected)
                self.assertEqual(verifier["confidence"], "high")

    def test_discrepant_candidate_verifier_keeps_direct_actor_separate_from_bystander_silence(self):
        cases = [
            (
                "鲍勃正好在柜台旁结账，没看见合同被咖啡毁了。店主刚好看到这一幕，但选择不告诉鲍勃。",
                "鲍勃的行为可能是出于什么样的意图？",
                {
                    "A": "A. 鲍勃可能认为清理办公室比保留文件更重要。",
                    "B": "B. 鲍勃可能无意识或不知情，因为他错误地认为艾米丽的文件是废纸。",
                    "C": "C. 鲍勃可能知道文件所属于某人，但是为了方便完成工作就不多加过问。",
                    "D": "D. 鲍勃可能因为想快速完成任务而忽视了文件的重要性。",
                },
                "B",
            ),
            (
                "为了晋升，鲍勃看到一个项目的重要信息，但他不知道那是艾米未公开分享的文件。克莱尔知道上司在她与艾米之间选择谁晋升，所以保持沉默。",
                "鲍勃的行为可能是出于什么样的意图?",
                {
                    "A": "A. 鲍勃可能故意使用艾米的信息，认为这是合法的竞争手段来取得项目上的优势。",
                    "B": "B. 鲍勃可能因为对艾米的个人不满，故意使用她的信息来确保自己的成功。",
                    "C": "C. 鲍勃可能无意识地使用了艾米的信息，因为他不知道这些信息是未公开的重要文件。",
                    "D": "D. 鲍勃可能认为信息已被艾米公开分享，因此他认为使用这些信息是合理的。",
                },
                "C",
            ),
            (
                "萨姆不小心把错误调料加入菜肴中，认为这是利亚的指示。克里斯是利亚的对手，知道了萨姆的错误，但决定不告诉任何人。",
                "萨姆的行为可能是出于什么样的意图？",
                {
                    "A": "A. 萨姆可能出于想要尝试新的烹饪方法，故意改变配方。",
                    "B": "B. 萨姆可能出于误解利亚的指示，无意中加入了错误的调料。",
                    "C": "C. 萨姆可能因为分心，没有注意到自己的错误。",
                    "D": "D. 萨姆可能因为对菜肴的味道有自信，故意加入不同的调料。",
                },
                "B",
            ),
            (
                "张伟看到李华手头的捐款箱，误以为是用来筹集班级活动资金的，便私自拿了一部分钱用于购买班级用品。王芳发现了张伟的行为，但选择不告诉李华。",
                "张伟的行为可能是出于什么样的意图？",
                {
                    "A": "A. 张伟可能认为他有权使用这笔钱，因为他是班级的一员。",
                    "B": "B. 张伟明知捐款箱是用于学校的捐赠活动，但为了个人利益而私自拿走了一部分钱。",
                    "C": "C. 张伟可能因为误解捐款箱的用途，认为使用这笔钱能够为班级活动带来更大的好处。",
                    "D": "D. 张伟可能认为使用这笔钱能够为班级活动带来更大的好处，尽管这违反了捐款的初衷。",
                },
                "C",
            ),
        ]
        for story, question, options, expected in cases:
            with self.subTest(expected=expected):
                core = analyze_social_reasoning(story, question, options_zh=options)
                self.assertEqual(core["focus"], "discrepant_intention")
                self.assertFalse(core["pragmatic_model"]["target_is_silent_actor"])
                self.assertIn("target_action_may_be_uninformed_not_deceptive", core["pragmatic_model"]["markers"])
                verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
                self.assertEqual(verifier["top_option"], expected)
                self.assertEqual(verifier["confidence"], "high")

    def test_leftbrain_frame_merge_exposes_core_without_options(self):
        fallback = {
            "focus": "belief_state",
            "main_actor": "小林",
            "current_goal": "状況を読む",
            "prior_goal": "",
            "belief_boundary": "",
            "knowledge_gap": "",
            "emotion_driver": "",
            "social_subtext": "",
            "decision_rule": "",
            "best_option_shape": "",
        }
        text = "小林知道真相但没有告诉朋友，因为他怕朋友失望。"
        frame = merge_leftbrain_social_frame(fallback, text)
        self.assertEqual(frame["social_reasoning_core"]["focus"], "discrepant_intention")
        self.assertIn("知道什么", frame["belief_boundary"])

    def test_pragmatic_norm_core_is_process_only(self):
        frame = analyze_social_reasoning(
            "小美不知道小王刚被裁员，就在聚会上问他新工作是不是很顺利。",
            question="Does anyone say something inappropriate in this story?",
        )
        self.assertEqual(frame["focus"], "pragmatic_norm")
        self.assertIn("敏感事实", frame["knowledge_boundary"])
        self.assertIn("possible_faux_pas_or_norm_violation", frame["intent_hypotheses"])
        self.assertNotIn("selected_option", frame)
        self.assertTrue(should_inject_social_reasoning_core(frame))

    def test_pragmatic_norm_detects_chinese_faux_pas_question(self):
        frame = analyze_social_reasoning(
            "小丹对妈妈说：新窗帘真好看。朋友也说：这窗帘真漂亮，很配你的卧室。",
            question="这个故事中是否有人说了不合适的话?",
        )
        self.assertEqual(frame["focus"], "pragmatic_norm")
        self.assertIn("faux_pas_presence_question", frame["pragmatic_model"]["markers"])
        self.assertIn("no_clear_faux_pas_context", frame["pragmatic_model"]["markers"])
        self.assertTrue(should_inject_social_reasoning_core(frame))

    def test_pragmatic_candidate_verifier_selects_no_faux_pas_for_benign_compliment(self):
        story = "小丹对妈妈说：新窗帘真好看。朋友也说：这窗帘真漂亮，很配你的卧室。"
        question = "这个故事中是否有人说了不合适的话?"
        options = {
            "A": "故事中有人说了不合适的话。",
            "B": "故事中没有人说不合适的话。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_pragmatic_candidate_verifier_selects_no_inappropriate_quote_for_supportive_visit(self):
        story = (
            "小杰做了小手术，朋友提前得知情况，因此非常小心。"
            "小芳说：这些故事应该能让你开心点。小美说：我们可以聊聊天，也可以静静坐着，看你喜欢。"
        )
        question = "如果有的话，哪句话是不合适的?"
        options = {
            "A": "这些故事应该能让你开心点。",
            "B": "我们可以聊聊天，也可以静静坐着，看你喜欢。",
            "C": "谢谢你们，我已经好多了。",
            "D": "没有人说不该说的话。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "D")
        self.assertEqual(verifier["confidence"], "high")

    def test_pragmatic_candidate_verifier_treats_observed_preference_as_not_full_knowledge(self):
        story = (
            "饭桌上，客人只挑没有香菜的菜。李阿姨注意到了，说：你多尝尝这个香菜牛肉。"
            "客人笑着说：谢谢阿姨好意，还是没动筷子。"
        )
        question = "李阿姨知道客人不吃香菜吗?"
        options = {
            "A": "知道",
            "B": "不知道",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "B")
        self.assertIn("observed_preference_without_direct_knowledge", verifier["markers"])

    def test_pragmatic_candidate_verifier_scores_roommate_exclusion_sentence(self):
        story = (
            "小张问小李：新学期你想和谁做室友？"
            "小李回答：我在考虑几个选项，可能会选一个我以前没住过的人。"
            "小张听后沉默了一下，说：祝你选择顺利，然后转移话题。"
        )
        question = "如果有的话，哪句话是不合适的?"
        options = {
            "A": "新学期你想和谁做室友？",
            "B": "我在考虑几个选项，可能会选一个我以前没住过的人。",
            "C": "祝你选择顺利。",
            "D": "没有不合适的话。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_pragmatic_candidate_verifier_scores_avoidant_silence_reaction(self):
        story = "小李问小王会议内容，小王简短回答：没，不是什么大事。然后快步离开。"
        question = "小王对小李的问题作出了什么反应？"
        options = {
            "A": "高兴",
            "B": "困惑",
            "C": "生气",
            "D": "沉默",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "D")
        self.assertEqual(verifier["confidence"], "high")

    def test_pragmatic_candidate_verifier_keeps_polite_greeting_from_becoming_faux_pas(self):
        story = "小芳和小刚分手后，小刚的现任女友走了过来，小芳礼貌地问候：你好，我是小芳。"
        question = "如果有的话，哪句话是不合适的?"
        options = {
            "A": "最近有什么新鲜事吗？",
            "B": "我最近开始学习摄影。",
            "C": "你好，我是小芳。",
            "D": "没有不合适的话。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "D")
        self.assertIn("no_clear_faux_pas_context", verifier["markers"])

    def test_scalar_quantity_core_derives_semantic_estimate_without_option_letter(self):
        answer, payload = infer_scalar_quantity_option(
            "树上有15个苹果，几乎一半是红苹果。小红采摘了7个，然后说其中有3个是红苹果。",
            "请问在小红采摘之后树上还有几个红苹果？",
            {"A": "0个", "B": "1个", "C": "2个", "D": "4个"},
        )
        model = payload["social_reasoning_core"]["quantity_model"]
        self.assertEqual(answer, "")
        self.assertEqual(model["semantic_estimate"], 4)
        self.assertNotIn("selected_option", payload["social_reasoning_core"])

    def test_scalar_majority_with_residual_estimate_is_not_fixed_ratio(self):
        answer, payload = infer_scalar_quantity_option(
            "茶馆有30种茶叶，大部分是绿茶，小部分白茶和红茶。顾客品尝后，发现只有2种是红茶。",
            "请问顾客品尝前，推测有多少种是绿茶？",
            {"A": "25种", "B": "30种", "C": "28种", "D": "10种"},
        )
        model = payload["social_reasoning_core"]["quantity_model"]
        self.assertEqual(answer, "")
        self.assertEqual(model["semantic_estimate"], 25)
        self.assertEqual(model["derivation"], "majority_with_some_and_almost_none_residual")

    def test_roleplay_identity_core_separates_role_from_lie(self):
        frame = analyze_social_reasoning(
            "王小明穿着机械战士装束参加展览，小朋友问他是谁，他回答：我就是最厉害的机械战士。",
            question="王小明为什么这么说？",
        )
        self.assertEqual(frame["focus"], "roleplay_identity")
        self.assertIn("扮演身份", frame["knowledge_boundary"])
        self.assertIn("speaker_answers_from_performed_role_identity", frame["intent_hypotheses"])
        self.assertIn("no option letter", format_social_reasoning_trace(frame))

    def test_roleplay_candidate_verifier_prefers_playful_role_answer(self):
        story = "赵丽丽在角色扮演活动中扮演魔法师。游客问她是不是会魔法，她回答：是的，我精通各种魔法术。"
        question = "赵丽丽为什么这么说？"
        options = {
            "A": "她实际上是一位魔法师。",
            "B": "观众低估了她的表演技巧。",
            "C": "她扮演的是魔法师，所以开玩笑地配合角色。",
            "D": "活动规则要求她这样回答。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "roleplay_identity")
        self.assertEqual(verifier["top_option"], "C")
        self.assertEqual(verifier["confidence"], "high")

    def test_roleplay_candidate_verifier_detects_attention_performance(self):
        story = "李明是体育账号博主，在体育馆装扮成体育明星，引起观众拍照和互动。"
        question = "李明为什么这样做？"
        options = {
            "A": "为了娱乐效果，也真的觉得自己是体育明星。",
            "B": "他误以为自己是那位体育明星。",
            "C": "他希望被镜头捕捉，成为焦点。",
            "D": "他在做社会心理学实验。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "roleplay_identity")
        self.assertEqual(verifier["top_option"], "C")
        self.assertEqual(verifier["confidence"], "high")

    def test_roleplay_candidate_verifier_keeps_costume_identity_nonliteral(self):
        story = "李浩然正在庆祝万圣节，要参加化装派对。他打扮成一个鬼，穿着鬼装回答叔叔说：是鬼。"
        question = "李浩然所说的是真的吗？"
        options = {"A": "A. 是", "B": "B. 否"}
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "roleplay_identity")
        self.assertIn("performed_role_reply", core["pragmatic_model"]["markers"])
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_indirect_speech_act_core_separates_hint_from_literal_text(self):
        frame = analyze_social_reasoning(
            "Emma looks at the closed window and says, It is cold in here.",
            question="What does Emma really want to say?",
        )
        self.assertEqual(frame["focus"], "indirect_speech_act")
        self.assertIn("indirect_request_for_listener_action", frame["intent_hypotheses"])
        self.assertEqual(frame["trace_policy"], "moderate")
        self.assertTrue(should_inject_social_reasoning_core(frame))
        self.assertIn("no option letter", format_social_reasoning_trace(frame))

    def test_nonliteral_pragmatics_core_handles_irony_without_answer_key(self):
        frame = analyze_social_reasoning(
            "小周明明把杯子打碎了，朋友开玩笑地说：你真是太小心了。",
            question="朋友说的是真的吗？",
        )
        self.assertEqual(frame["focus"], "nonliteral_pragmatics")
        self.assertIn("possible_irony_or_sarcasm", frame["intent_hypotheses"])
        self.assertIn("字面真假", frame["knowledge_boundary"])
        self.assertTrue(should_inject_social_reasoning_core(frame))
        self.assertNotIn("selected_option", frame)

    def test_nonliteral_candidate_verifier_uses_private_emotion_evidence(self):
        story = "小李公开对朋友说：恭喜你赢了。晚上回家后，小李对弟弟说：我真的很失落。"
        question = "小李对弟弟说的话是真的吗？"
        options = {"A": "是", "B": "否"}
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "nonliteral_pragmatics")
        self.assertIn("public_politeness_private_emotion", verifier["markers"])
        self.assertEqual(verifier["top_option"], "A")

    def test_nonliteral_candidate_verifier_prefers_grounded_mixed_emotion(self):
        story = "李晨比赛获得第二名，好友赢得第一名。李晨对老师说：我很高兴好友赢了；对爸爸说：我很失望，我想赢。"
        question = "为什么李晨感到既高兴又失望？"
        options = {
            "A": "他高兴朋友赢了，但失望自己名次。",
            "B": "他对比赛结果无所谓。",
            "C": "他高兴朋友赢了，但失望没得第一名。",
            "D": "他高兴因为比赛结束，但失望因为觉得自己讲得不好。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "nonliteral_pragmatics")
        self.assertEqual(verifier["top_option"], "C")

    def test_nonliteral_candidate_verifier_anchors_private_disappointment_to_public_praise(self):
        story = "李晓和王强组队赢了第一名，王强获得最佳论文奖。李晓对王强说：我真高兴朋友获得了最佳论文奖。晚上她对爸爸说：我很难过。"
        question = "为什么李晓说她既高兴又难过？"
        options = {
            "A": "她高兴王强赢得了最佳论文，但难过自己没有赢得个人奖项。",
            "B": "她高兴他们队赢得了第一名，但难过王强没有安慰她。",
            "C": "她高兴王强赢得了最佳论文，但难过王强没有安慰她。",
            "D": "她高兴他们队赢得了第一名，但难过自己没有赢得个人奖项。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "nonliteral_pragmatics")
        self.assertEqual(verifier["top_option"], "A")

    def test_nonliteral_candidate_verifier_handles_metaphor_without_literal_superpower(self):
        story = "小刚是短跑选手，每次比赛都能迅速冲向终点。同学说：你肯定会瞬间移动的超能力吧。"
        question = "为什么同学这么说？"
        options = {
            "A": "他认为小刚拥有瞬间移动的超能力。",
            "B": "他用比喻表示佩服，祝贺他又得第一名。",
            "C": "他认为小刚是长跑选手。",
            "D": "他用比喻形容小刚跑得很快。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "nonliteral_pragmatics")
        self.assertEqual(verifier["top_option"], "D")
        self.assertEqual(verifier["confidence"], "high")

    def test_nonliteral_candidate_verifier_handles_literal_metaphor_misunderstanding(self):
        story = "小明不爱开玩笑。老师用比喻说成功像种子，需要浇灌。小明愣了一下，说：我去搞点泥巴和水，浇灌成功种子。"
        question = "为什么小明会这么说？"
        options = {
            "A": "培养种子确实需要土和水。",
            "B": "小明没意识老师是用比喻回答，以为真的需要用水和泥巴培育。",
            "C": "小明理解了老师的比喻，但用幽默表达愿望。",
            "D": "小明不知道如何回应，于是顺着说。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "nonliteral_pragmatics")
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_nonliteral_candidate_verifier_handles_wordplay_request(self):
        story = "女生说自己在思钱想厚，又说发现良品铺子和从百草味到三只松鼠，男朋友秒懂后买了礼物。"
        question = "为什么女生这么说？"
        options = {
            "A": "女生想要更多钱。",
            "B": "女生想买书。",
            "C": "女生想让男朋友买一本书。",
            "D": "女生使用比喻想要男朋友给她买一些零食。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "nonliteral_pragmatics")
        self.assertEqual(verifier["top_option"], "D")

    def test_nonliteral_candidate_verifier_detects_withheld_suspicion(self):
        story = "王警官怀疑李先生，但为了避免麻烦，在报告中写道：案件仍在进一步调查中，尚未确定嫌疑人。"
        question = "王警官说的是真的吗？"
        options = {"A": "是", "B": "不是"}
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "nonliteral_pragmatics")
        self.assertEqual(verifier["top_option"], "B")

    def test_strategic_deception_candidate_verifier_prefers_observation(self):
        story = "李华和王强竞争。李华故意泄露他也在准备更大项目的假消息，王强听说后暂停项目。"
        question = "王强为什么暂停他的项目？"
        options = {
            "A": "他害怕和李华的竞争。",
            "B": "他想要观察李华的下一步举动。",
            "C": "他需要更多资金。",
            "D": "他对项目失去信心。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "strategic_deception_reasoning")
        self.assertEqual(verifier["top_option"], "B")

    def test_constrained_refusal_candidate_verifier_respects_current_constraint(self):
        story = "小华很喜欢足球，但最近高三课业很忙，父母希望他好好学习。校队问他要不要参加选拔，他说：我就不去参加了。"
        question = "小华真的不想参加校队选拔么？"
        options = {"A": "是", "B": "否"}
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "constrained_refusal_reasoning")
        self.assertEqual(verifier["top_option"], "A")

    def test_surprise_reaction_candidate_verifier_uses_unexpected_action(self):
        story = "小平第一次给妈妈做菜。妈妈回家后看到儿子竟然做好了菜，吃后很欣慰和感动，眼角湿润。"
        question = "妈妈听了儿子的话感到惊讶吗？"
        options = {"A": "是", "B": "否"}
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(core["focus"], "surprise_reaction_reasoning")
        self.assertEqual(verifier["top_option"], "A")

    def test_speaker_belief_utterance_separates_mistake_from_lie(self):
        frame = analyze_social_reasoning(
            "李明忘记把足球带回家，但他以为足球在背包里。哥哥问足球在哪，李明回答：在我包里。",
            question="李明为什么这么说？",
        )
        self.assertEqual(frame["focus"], "speaker_belief_utterance")
        self.assertIn("speaker_may_be_mistaken_rather_than_lying", frame["intent_hypotheses"])
        self.assertIn("客观事实", frame["knowledge_boundary"])
        self.assertTrue(should_inject_social_reasoning_core(frame))
        self.assertIn("outdated memory", format_social_reasoning_trace(frame))

    def test_indirect_speech_act_detects_face_saving_request(self):
        frame = analyze_social_reasoning(
            "老科长站了半天感觉很累，现场只有一个凳子。他对年轻同事说：你也站半天了，你坐一会儿吧。",
            question="老科长真正的意图是什么？",
        )
        self.assertEqual(frame["focus"], "indirect_speech_act")
        self.assertIn("speaker_may_indirectly_request_help_while_preserving_face", frame["intent_hypotheses"])
        self.assertTrue(should_inject_social_reasoning_core(frame))
        self.assertIn("scarce resource", format_social_reasoning_trace(frame))

    def test_candidate_verifier_scores_face_saving_request_without_answer_key(self):
        story = "主任很累，休息室只有一张椅子。他对新人说：你站很久了，你坐一下吧。"
        question = "主任真正的意图是什么？"
        options = {
            "A": "主任希望新人把椅子让给他坐。",
            "B": "主任只是关心新人健康，希望新人休息。",
            "C": "主任想讨论休息室设备。",
            "D": "主任决定自己一直站着。",
        }
        core = analyze_social_reasoning(story, question)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "A")
        trace = format_candidate_verifier_trace(verifier)
        self.assertIn("highest_fit_option=A", trace)
        self.assertIn("candidate-fit scores", trace)

    def test_hinting_candidate_verifier_handles_indirect_intent_families(self):
        cases = [
            (
                "admired_possession_gift_request",
                "明凯在大学爬泰山的时候买了个钥匙扣。他参加工作后，他的领导偶然看到这个钥匙扣，说“你这钥匙扣真漂亮啊，哪里买的？”明凯便把自己在泰山的经历绘声绘色说了一遍。过了几天，领导又看到明凯的钥匙扣，好像失忆了一样，又问“你这钥匙扣真漂亮啊，哪里买的？“",
                "领导说这句话的时候，真正的意图是什么？",
                {
                    "A": "A. 领导对明凯的钥匙扣很感兴趣，考虑自己也去买一个。",
                    "B": "B. 领导希望明凯能将这个钥匙扣送给他。",
                    "C": "C. 领导想检验明凯的耐心，探究他是否愿意反复解释同一件事。",
                    "D": "D. 领导提醒小明这个钥匙扣使他分心了",
                },
                "B",
            ),
            (
                "reverse_psychology_compliance",
                "19世纪，在奥地利的维也纳，妇女们喜欢戴一种高高耸起的帽子。她们进剧场看戏也不愿将帽子摘下，以致后排的观众被挡住了视线。经理上台请在座的女观众将帽子摘下来，然而说了半天妇女们也不予以理睬。最后经理又补充了一句：“那么，这样吧，年纪大一点的女士可以照顾，不必脱帽。”",
                "剧场经理说这些话时，他真正想说的意思是什么？",
                {
                    "A": "A. 他希望所有的女士都将帽子摘下来。",
                    "B": "B. 他只希望年纪轻的女士将帽子摘下来。",
                    "C": "C. 他对戴帽子的女士感到恼火。",
                    "D": "D. 他在夸赞年纪大的女士的优雅。",
                },
                "A",
            ),
            (
                "noise_reduction_hint",
                "阿宾在准备期末考试的过程中，室友小乐正在使用音响听歌。阿宾说：“这首歌的旋律很棒，但你有找到我的耳机吗？”",
                "当阿宾说这句话的时候，他真正想说的是什么？",
                {
                    "A": "A. 他想强调这首歌的旋律很好",
                    "B": "B. 他寻找自己的耳机",
                    "C": "C. 他暗示室友应当调低音量",
                    "D": "D. 他想要加入小乐一起听歌",
                },
                "C",
            ),
            (
                "missing_tableware_request",
                "妈妈做完晚餐，来到餐厅和爸爸儿子一起吃饭，看到桌上摆放着两双筷子，说到：“奇怪，今天我们是几个人一起吃饭呀？”",
                "当妈妈说这句话的时候，她真正想说的是什么？",
                {
                    "A": "A. 妈妈在询问一起吃饭的人数。",
                    "B": "B. 妈妈暗示家里应该有更多的人来。",
                    "C": "C. 妈妈暗示应该给她再拿一双筷子。",
                    "D": "D. 妈妈暗示她不太饿，可能不会吃太多的食物。",
                },
                "C",
            ),
            (
                "classroom_noise_correction",
                "在自习课上上，明明忽然发出了爽朗的笑声。同坐一桌的淑华看过去，笑着对他说：“明明，你的笑声真有特色。”",
                "当淑华说这句话时，她真正想说的是什么？",
                {
                    "A": "A. 淑华非常喜欢明明的笑声，并认为它很特别。",
                    "B": "B. 淑华暗示明明他的笑声太大了，应该小声一些。",
                    "C": "C. 淑华在赞美明明，认为他的笑声有独特的吸引力。",
                    "D": "D. 淑华觉得明明的笑声很有趣，让她感到快乐。",
                },
                "B",
            ),
            (
                "fundraising_investment_hint",
                "小周和张姐是多年的老朋友。小周是一名医生，正在到处筹钱开医馆。前阵子小周来张姐家里泡茶，问张姐：“张姐，我是否要给你留个医馆的董事长位置？”",
                "当小周说这句话的时候，她真正想说的是什么？",
                {
                    "A": "A. 小周想请张姐来医馆工作",
                    "B": "B. 小周想拉取张姐对医馆的投资",
                    "C": "C. 小周想向张姐请教如何经营医馆",
                    "D": "D. 小周想邀请张姐成为医馆的名誉董事长",
                },
                "B",
            ),
            (
                "marriage_registration_hint",
                "小雨和小华是一对恋人。一天，小雨将两人身份证放一起，说是比谁更好看，小华说：“比对不是得同样的灯光，同样的摄影师，同等条件下才能得出正确的结论吗？改天我们一起去拍证件照？”",
                "当小华说这句话的时候，他真正想说的是什么？",
                {
                    "A": "A. 小华希望换一个摄影师重新拍摄他和小雨的证件照。",
                    "B": "B. 小华觉得自己的证件照拍摄的不满意，希望重新拍摄。",
                    "C": "C. 小华建议两人去办理结婚登记。",
                    "D": "D. 小华希望他和小雨购买一套专业的摄影设备。",
                },
                "C",
            ),
            (
                "classroom_attention_correction",
                "欧阳是个高中生，他的坐位在班上的最后一排。一天，他的老师陈老师在课上问他：“欧阳，窗外的风景怎么样呢？”",
                "当陈老师说这句话时，他真正想说的是什么？",
                {
                    "A": "A. 陈老师担心欧阳坐在最后一排，可能看不清黑板。",
                    "B": "B. 陈老师在提醒欧阳上课不应该东张西望。",
                    "C": "C. 陈老师想知道窗外的风景是什么样子。",
                    "D": "D. 陈老师希望欧阳能够欣赏窗外的风景，感受大自然的美好。",
                },
                "B",
            ),
            (
                "product_quality_counter_hint",
                "小张在街边小摊上买橘子，他问老板：“橘子酸不？”\n老板说：“甜得很”\n旁边一个买橘子的大姐说：：“太甜了齁牙，略微带点酸的最好。我最喜欢这种。”",
                "当大姐说这句话时，她真正想说的是什么？",
                {
                    "A": "A. 她想表达她自己最喜欢吃带点酸的橘子。",
                    "B": "B. 她想告诉小张这个地方的橘子非常甜。",
                    "C": "C. 她在赞美摊主的橘子，表示对这种味道的喜爱。",
                    "D": "D. 她暗示小张买的橘子是酸的。",
                },
                "D",
            ),
            (
                "phone_theft_warning_hint",
                "陈威骑着电动车去市场买水果，路过水果摊位，他刚停下电车，在车上转过头问老板：“橘子多少钱一斤？”老板回了一句：“手机拿好，下来看吧。”",
                "当老板说这句话时，他真正想说的是什么？",
                {
                    "A": "A. 老板希望陈威安全下车，避免摔倒。",
                    "B": "B. 老板希望陈威用手机查看橘子的现在的市场价格。",
                    "C": "C. 老板暗示周围有偷手机的小偷。",
                    "D": "D. 老板建议陈威亲自挑选看看橘子的品质。",
                },
                "C",
            ),
        ]
        for marker, story, question, options, expected in cases:
            with self.subTest(marker=marker):
                core = analyze_social_reasoning(story, question, options_zh=options)
                self.assertEqual(core["focus"], "indirect_speech_act")
                self.assertIn(marker, core["pragmatic_model"]["markers"])
                verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
                self.assertEqual(verifier["top_option"], expected)
                self.assertEqual(verifier["confidence"], "high")

    def test_hinting_candidate_verifier_supports_english_real_intention_wording(self):
        story = (
            "Mingkai buys a keychain when he climbs Mount Tai in college. After he starts working, "
            'his leader accidentally sees this keychain and says, "This keychain of yours is really beautiful, '
            'where do you buy it?" Mingkai then vividly tells his experience on Mount Tai. After a few days, '
            'the leader sees Mingkai\'s keychain again, as if he forgets, and asks again, '
            '"This keychain of yours is really beautiful, where do you buy it?"'
        )
        question = "What is the real intention of the leader when he says this?"
        options = {
            "A": "The leader is very interested in Mingkai's keychain and considers buying one for himself.",
            "B": "The leader hopes that Mingkai gives this keychain to him.",
            "C": "The leader wants to test Mingkai's patience, to explore whether he is willing to explain the same thing repeatedly.",
            "D": "The leader reminds Mingkai that this keychain distracts him.",
        }
        core = analyze_social_reasoning(story, question, options_en=options)
        verifier = verify_social_reasoning_candidates(story, question, options_en=options, core=core)
        self.assertEqual(core["focus"], "indirect_speech_act")
        self.assertIn("admired_possession_gift_request", core["pragmatic_model"]["markers"])
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_indirect_speech_act_detects_social_criticism(self):
        frame = analyze_social_reasoning(
            "有人无视谢绝带宠物入场的牌子，还显得不屑。孩子笑着说：狗又不认识字。",
            question="孩子真正想说的意思是什么？",
        )
        self.assertEqual(frame["focus"], "indirect_speech_act")
        self.assertIn("indirect_social_criticism", frame["intent_hypotheses"])
        self.assertTrue(should_inject_social_reasoning_core(frame))
        self.assertIn("rule-breaking person", format_social_reasoning_trace(frame))

    def test_candidate_verifier_scores_mistaken_belief_over_lie(self):
        story = "小林忘记把奖状放进书包里了，但她以为奖状挂在墙上。妈妈问奖状在哪，小林说：挂在墙上。"
        question = "小林为什么这么说？"
        options = {
            "A": "小林故意撒谎，不想让妈妈知道。",
            "B": "小林记得奖状确实挂在墙上。",
            "C": "小林忘了奖状在书包里，并且以为它在墙上。",
            "D": "小林想测试妈妈有没有注意墙。",
        }
        core = analyze_social_reasoning(story, question)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "C")
        self.assertGreater(verifier["margin"], 3)

    def test_scalar_candidate_verifier_uses_threshold_estimate(self):
        story = "树上有15个苹果，几乎一半是红苹果。小红采摘了7个，然后说其中有3个是红苹果。"
        question = "请问在小红采摘之前树上有几个红苹果？"
        options = {
            "A": "小红摘水果之前，推测树上有7个红苹果",
            "B": "小红摘水果之前，推测树上有4个红苹果",
            "C": "小红摘水果之前，推测树上有8个红苹果",
            "D": "小红摘水果之前，推测树上有2个红苹果",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "A")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_uses_actual_observed_after_count(self):
        story = "车库里停着10辆自行车，主人认为大部分都需要修理。朋友检查后，发现实际上只有5辆需要修理。"
        question = "朋友检查后，推测有几辆需要修理？"
        options = {
            "A": "朋友检查后，推测有1辆需要修理。",
            "B": "朋友检查后，推测有5辆需要修理。",
            "C": "朋友检查后，推测有8辆需要修理。",
            "D": "朋友检查后，推测有3辆需要修理。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        model = core["quantity_model"]
        self.assertEqual(model["observed_target_count"], 5)
        self.assertTrue(model["observed_matches_question"])
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_uses_parallel_some_residual(self):
        story = "图书馆里有30个学生，绝大多数在看数学书，有些在看历史书，还有一些在看物理书。老师观察后，发现只有5个学生在看历史书。"
        question = "老师观察后，推测有多少个学生在看数学书？"
        options = {
            "A": "25个学生在看数学书。",
            "B": "20个学生在看数学书。",
            "C": "10个学生在看数学书。",
            "D": "9个学生在看数学书。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        model = core["quantity_model"]
        self.assertEqual(model["paired_residual_strategy"], "parallel_some_categories")
        self.assertEqual(model["semantic_estimate"], 20)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_uses_paired_small_part_residual(self):
        story = "停车场里停着50辆车，大多数是国产车，有少部分是德系车有少部分是美系车。检查后，发现5辆是德系车。"
        question = "检查后，推测有多少辆国产车？"
        options = {
            "A": "45辆国产车。",
            "B": "50辆国产车。",
            "C": "35辆国产车。",
            "D": "30辆国产车。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        model = core["quantity_model"]
        self.assertEqual(model["paired_residual_strategy"], "paired_small_part_categories")
        self.assertEqual(model["semantic_estimate"], 35)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "C")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_keeps_shared_small_part_conservative(self):
        story = "茶馆有30种茶叶，大部分是绿茶，小部分白茶和红茶。顾客品尝后，发现只有2种是红茶。"
        question = "顾客品尝后，推测有多少种是绿茶？"
        options = {
            "A": "20种是绿茶。",
            "B": "26种是绿茶。",
            "C": "28种是绿茶。",
            "D": "10种是绿茶。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        model = core["quantity_model"]
        self.assertEqual(model["paired_residual_strategy"], "shared_small_part_categories")
        self.assertEqual(model["semantic_estimate"], 26)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_uses_large_total_before_anchor(self):
        story = "电影院有40场排片，大多数是喜剧电影，一部分是动作片，很少有爱情片。小美数了数，发现只有5场动作片。"
        question = "小美数前，推测多少场喜剧电影？"
        options = {
            "A": "小美数前，推测40场喜剧电影。",
            "B": "小美数前，推测39场喜剧电影。",
            "C": "小美数前，推测20场喜剧电影。",
            "D": "小美数前，推测35场喜剧电影。",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "D")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_stays_conservative_for_broad_majority(self):
        story = "电影院有20个电影可以选，大多数电影都是动作片，一些是科幻片，但几乎没有恐怖片。小红查看后发现只有5部科幻片。"
        question = "小红查看电影列表前，推测有几部动作片？"
        options = {
            "A": "小红查看前，推测有12部动作片",
            "B": "小红查看前，推测有15部动作片",
            "C": "小红查看前，推测有19部动作片",
            "D": "小红查看前，推测有11部动作片",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["semantic_estimate"], 12)
        self.assertEqual(core["quantity_model"]["derivation"], "small_total_before_majority_conservative_anchor")
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertNotEqual(verifier["confidence"], "high")
        self.assertEqual(format_candidate_verifier_trace(verifier), "")

    def test_scalar_candidate_verifier_handles_half_split_consumed_majority(self):
        story = "厨房原本放着10个苹果，有红苹果和青苹果各占一半。小李已经吃了大部分红苹果。王丽数了数，发现还剩下5个青苹果。"
        question = "请问在王丽数之前，厨房有几个苹果？"
        options = {
            "A": "王丽数之前，推测厨房有1个苹果",
            "B": "王丽数之前，推测厨房有4个苹果",
            "C": "王丽数之前，推测厨房有6个苹果",
            "D": "王丽数之前，推测厨房有9个苹果",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["derivation"], "half_split_consumed_majority_remaining_total")
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "C")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_handles_popularity_remaining_inverse(self):
        story = "超市原本有60瓶饮料，汽水、果汁和咖啡数量一样。汽水是最受欢迎的，果汁卖得也还行，几乎没人爱喝咖啡。经理数了数，确实果汁还有8瓶没有售卖。"
        question = "经理数前，推测汽水剩下几瓶？"
        options = {
            "A": "汽水剩下10瓶",
            "B": "汽水剩下2瓶",
            "C": "汽水剩下15瓶",
            "D": "汽水剩下7瓶",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["derivation"], "popularity_remaining_inverse_from_observed_moderate_seller")
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_handles_after_almost_none_residual(self):
        story = "实验室里有30副耳机，大部分耳机都是好的，小部分耳机有一只坏了，几乎没有完全坏掉的耳机。老师检查后，发现只有5副耳机坏了一只。"
        question = "老师检查后，推测有多少副耳机是好的？"
        options = {
            "A": "25副耳机是好的",
            "B": "20副耳机是好的",
            "C": "26副耳机是好的",
            "D": "22副耳机是好的",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["semantic_estimate"], 22)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "D")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_handles_before_almost_none_residual(self):
        story = "菜单上有50道菜，大多数是川菜，也有一些粤菜，但几乎没有鲁菜。小陈浏览后，发现只有10道粤菜。"
        question = "小陈浏览前，推测有多少道川菜？"
        options = {
            "A": "30道川菜",
            "B": "49道川菜",
            "C": "50道川菜",
            "D": "45道川菜",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["derivation"], "before_majority_almost_none_residual_ignore_observed_some")
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "D")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_handles_tiny_total_before_observed_anchor(self):
        story = "今天有8场电影放映，大多数是喜剧片，一些是动画片，但几乎没有恐怖片。小刘看了时间表，发现只有2场动画片。"
        question = "小刘看电影时间表前，推测有几场喜剧片？"
        options = {
            "A": "8场喜剧片",
            "B": "7场喜剧片",
            "C": "6场喜剧片",
            "D": "2场喜剧片",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["semantic_estimate"], 6)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "C")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_keeps_small_total_after_very_few_residual_small(self):
        story = "小区里有10棵树，大部分是银杏树，很少有松树，几乎没有柏树。李阿姨查看后，发现只有3棵是松树。"
        question = "李阿姨数后，推测有多少棵银杏树？"
        options = {
            "A": "1棵银杏树",
            "B": "3棵银杏树",
            "C": "6棵银杏树",
            "D": "7棵银杏树",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["semantic_estimate"], 6)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "C")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_uses_sparse_observed_anchor_for_small_before_some(self):
        story = "宠物店有30只动物，大部分是猫，一些是狗，但几乎没有兔子。小张看了看，发现只有4只狗。"
        question = "小张看前，推测有多少只猫猫？"
        options = {
            "A": "30只猫猫",
            "B": "24只猫猫",
            "C": "15只猫猫",
            "D": "26只猫猫",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["derivation"], "before_majority_almost_none_residual_sparse_observed_anchor")
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "B")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_uses_unit_mismatch_as_prior_guard(self):
        story = "农场种植了40种不同的蔬菜，大多数是番茄，一些是胡萝卜，但几乎没有茄子。小李仔细检查后，发现只有5个胡萝卜。"
        question = "小李仔细检查后，推测有多少种番茄？"
        options = {
            "A": "20种番茄",
            "B": "35种番茄",
            "C": "30种番茄",
            "D": "25种番茄",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["derivation"], "after_majority_unit_mismatch_unit_mismatch_use_majority_prior")
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "C")
        self.assertEqual(verifier["confidence"], "high")

    def test_scalar_candidate_verifier_when_observed_category_is_almost_none_category(self):
        story = "面包店做了20个面包，大多数是法棍面包，一些是葡萄干面包，但几乎没有巧克力面包。小玲看后，发现只有5个巧克力面包。"
        question = "小玲看后，推测有多少法棍面包？"
        options = {
            "A": "20个法棍面包",
            "B": "15个法棍面包",
            "C": "18个法棍面包",
            "D": "14个法棍面包",
        }
        core = analyze_social_reasoning(story, question, options_zh=options)
        self.assertEqual(core["quantity_model"]["almost_none_category"], "巧克力面包")
        self.assertEqual(core["quantity_model"]["semantic_estimate"], 14)
        verifier = verify_social_reasoning_candidates(story, question, options_zh=options, core=core)
        self.assertEqual(verifier["top_option"], "D")
        self.assertEqual(verifier["confidence"], "high")

    def test_literal_truth_question_without_nonliteral_signal_stays_silent(self):
        frame = analyze_social_reasoning(
            "Tom tells Mia that the meeting starts at 3 PM. Mia writes it down.",
            question="Is what Tom says true?",
        )
        self.assertEqual(frame["focus"], "general_social_reasoning")
        self.assertEqual(frame["trace_policy"], "observe_only")
        self.assertFalse(should_inject_social_reasoning_core(frame))

    def test_generic_social_reasoning_is_observed_not_injected(self):
        frame = analyze_social_reasoning("小明和小华一起走路。", question="小明为什么这么做？")
        self.assertEqual(frame["focus"], "general_social_reasoning")
        self.assertEqual(frame["trace_policy"], "observe_only")
        self.assertFalse(should_inject_social_reasoning_core(frame))


if __name__ == "__main__":
    unittest.main()
