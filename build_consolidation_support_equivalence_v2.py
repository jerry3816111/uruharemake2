#!/usr/bin/env python3
"""Build the preregistered fresh V2 support-equivalence pool."""

from __future__ import annotations

import itertools
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_equivalence_v2_construction_preregistration.json"
)
MEMORY_KINDS = ("episodic", "wisdom", "procedural")


def _memory(text, phenomenon, minimal_support_sets):
    return {
        "text": text,
        "support_phenomenon": phenomenon,
        "minimal_support_sets": minimal_support_sets,
    }


def _case(case_id, language, scenario_family, events, memories):
    return {
        "id": case_id,
        "language": language,
        "scenario_family": scenario_family,
        "source_events": [
            {
                "index": index,
                "user": user,
                "assistant": assistant,
            }
            for index, (user, assistant) in enumerate(events, start=1)
        ],
        "derived_memories": memories,
    }


RAW_CASES = [
    _case(
        "cse2_eng_library_print",
        "eng",
        "weekend_library_reading",
        [
            (
                "I returned the library books on Saturday morning.",
                "The books went back on Saturday morning.",
            ),
            (
                "For long articles, I prefer reading a printed copy.",
                "Printed copies work better for your long reads.",
            ),
            (
                "When an article is lengthy, paper is more comfortable "
                "for me than a screen.",
                "For lengthy articles, you are more comfortable on paper.",
            ),
            (
                "When helping me choose library material, first ask how "
                "much time I have.",
                "I should begin by checking your available time.",
            ),
            (
                "After that, compare the book length before recommending "
                "one.",
                "Then I should compare length before recommending.",
            ),
            (
                "My coworker listens to audiobooks during lunch.",
                "That is your coworker's listening habit.",
            ),
        ],
        {
            "episodic": _memory(
                "The user returned the library books on Saturday morning.",
                "single_minimal_set",
                [[1]],
            ),
            "wisdom": _memory(
                "The user prefers paper over a screen for long articles.",
                "alternative_minimal_sets",
                [[2], [3]],
            ),
            "procedural": _memory(
                "When helping choose library material, first ask how much "
                "time the user has and then compare book length before "
                "recommending.",
                "complementary_multi_event_set",
                [[4, 5]],
            ),
        },
    ),
    _case(
        "cse2_eng_evening_tea",
        "eng",
        "evening_tea_storage",
        [
            (
                "Until last month, I kept black tea on the kitchen shelf.",
                "Black tea used to be on that shelf.",
            ),
            (
                "This week I replaced it with caffeine-free barley tea, "
                "and that is what I keep there now.",
                "Barley tea is the current drink on the shelf.",
            ),
            (
                "My neighbor owns a silver espresso machine.",
                "The espresso machine belongs to your neighbor.",
            ),
            (
                "I might buy a coffee grinder someday.",
                "A grinder is only a possible future purchase.",
            ),
            (
                "When I ask for an evening drink, check whether I want "
                "caffeine before suggesting one.",
                "I should check your caffeine preference first.",
            ),
            (
                "The grocery store closes earlier on Sundays.",
                "Sunday shopping would need to be earlier.",
            ),
        ],
        {
            "episodic": _memory(
                "The user currently keeps caffeine-free barley tea on the "
                "kitchen shelf.",
                "current_state_override",
                [[2]],
            ),
            "wisdom": _memory(
                "The user owns a silver espresso machine.",
                "unsupported",
                [],
            ),
            "procedural": _memory(
                "For evening drink suggestions, check whether the user "
                "wants caffeine first.",
                "single_minimal_set",
                [[5]],
            ),
        },
    ),
    _case(
        "cse2_eng_swimming_class",
        "eng",
        "community_swimming_class",
        [
            (
                "On Wednesday evening I attended the community pool's "
                "lap-swimming class.",
                "You attended the Wednesday lap-swimming class.",
            ),
            (
                "That Wednesday class was the lap-swimming session I went "
                "to this week.",
                "You are referring to the same Wednesday session.",
            ),
            (
                "At pools, I prefer a lane near the wall.",
                "A wall-side lane is your preference.",
            ),
            (
                "I also like sessions with fewer than eight swimmers.",
                "You prefer sessions with a smaller group.",
            ),
            (
                "For future pool suggestions, prioritize travel time over "
                "crowd size.",
                "Travel time should have been the first priority.",
            ),
            (
                "Actually, from now on prioritize crowd size over travel "
                "time when suggesting a pool.",
                "Crowd size is now the first priority.",
            ),
        ],
        {
            "episodic": _memory(
                "The user attended a community lap-swimming class on "
                "Wednesday evening.",
                "alternative_minimal_sets",
                [[1], [2]],
            ),
            "wisdom": _memory(
                "The user prefers a lane near the wall and swimming "
                "sessions with fewer than eight people.",
                "complementary_multi_event_set",
                [[3, 4]],
            ),
            "procedural": _memory(
                "For future pool suggestions, prioritize crowd size over "
                "travel time.",
                "current_state_override",
                [[6]],
            ),
        },
    ),
    _case(
        "cse2_eng_morning_market",
        "eng",
        "morning_produce_market",
        [
            (
                "I am considering volunteering at the produce market next "
                "month.",
                "Volunteering is still only under consideration.",
            ),
            (
                "My sister volunteered at that market last Sunday.",
                "Your sister was the person who volunteered.",
            ),
            (
                "I prefer markets that open before nine in the morning.",
                "Early-opening markets suit you better.",
            ),
            (
                "When comparing produce boxes, show the total price before "
                "individual item prices.",
                "The total price should come first.",
            ),
            (
                "For future produce-box comparisons, please put the total "
                "cost first.",
                "I should lead with the total cost.",
            ),
            (
                "The forecast says it may rain at noon.",
                "The rain is expected around noon.",
            ),
        ],
        {
            "episodic": _memory(
                "The user volunteered at the produce market last Sunday.",
                "unsupported",
                [],
            ),
            "wisdom": _memory(
                "The user prefers markets that open before nine.",
                "single_minimal_set",
                [[3]],
            ),
            "procedural": _memory(
                "For produce-box comparisons, present the total cost "
                "before individual item prices.",
                "alternative_minimal_sets",
                [[4], [5]],
            ),
        },
    ),
    _case(
        "cse2_eng_scale_practice",
        "eng",
        "piano_scale_practice",
        [
            (
                "On Monday I practiced piano scales for twenty minutes.",
                "Monday's scale practice lasted twenty minutes.",
            ),
            (
                "On Thursday I practiced the same scales for thirty "
                "minutes.",
                "Thursday's practice lasted thirty minutes.",
            ),
            (
                "I used to prefer a loud metronome while practicing.",
                "A loud metronome was your earlier preference.",
            ),
            (
                "Now I prefer the metronome quiet enough that I can hear "
                "the piano clearly.",
                "Your current preference is a quieter metronome.",
            ),
            (
                "Today, just tell me whether this tempo is too fast.",
                "For today you want a direct tempo judgment.",
            ),
            (
                "You suggested that I record every practice session.",
                "That was my suggestion, not your standing instruction.",
            ),
        ],
        {
            "episodic": _memory(
                "The user practiced piano scales on Monday for twenty "
                "minutes and on Thursday for thirty minutes.",
                "complementary_multi_event_set",
                [[1, 2]],
            ),
            "wisdom": _memory(
                "The user currently prefers a quiet metronome while "
                "practicing piano.",
                "current_state_override",
                [[4]],
            ),
            "procedural": _memory(
                "Always require the user to record every piano practice "
                "session.",
                "unsupported",
                [],
            ),
        },
    ),
    _case(
        "cse2_eng_rail_pass",
        "eng",
        "monthly_rail_commute",
        [
            (
                "Yesterday I renewed my monthly rail pass.",
                "Your rail pass was renewed yesterday.",
            ),
            (
                "On trains, I prefer an aisle seat.",
                "An aisle seat is your train preference.",
            ),
            (
                "Aisle seats are more comfortable for me than window "
                "seats.",
                "You find aisle seats more comfortable.",
            ),
            (
                "When planning my commute, first ask whether I am carrying "
                "large luggage.",
                "I should check for large luggage first.",
            ),
            (
                "Then compare the number of transfers before choosing a "
                "route.",
                "Transfer count should be compared after that.",
            ),
            (
                "My friend cycles to work when the weather is clear.",
                "Cycling is your friend's commute.",
            ),
        ],
        {
            "episodic": _memory(
                "The user renewed the monthly rail pass yesterday.",
                "single_minimal_set",
                [[1]],
            ),
            "wisdom": _memory(
                "The user prefers aisle seats to window seats on trains.",
                "alternative_minimal_sets",
                [[2], [3]],
            ),
            "procedural": _memory(
                "When planning the user's commute, first ask about large "
                "luggage and then compare the number of transfers.",
                "complementary_multi_event_set",
                [[4, 5]],
            ),
        },
    ),
    _case(
        "cse2_jpn_blanket_laundry",
        "jpn",
        "coin_laundry_blanket",
        [
            (
                "土曜日の朝にコインランドリーで毛布を洗った。",
                "土曜の朝に毛布を洗ったんだね。",
            ),
            (
                "洗濯洗剤は香りのないものが好き。",
                "無香料の洗剤が好みなんだね。",
            ),
            (
                "香り付きより無香料の洗剤のほうが落ち着く。",
                "香りのない洗剤のほうが合うんだね。",
            ),
            (
                "毛布の洗い方を相談するときは、最初に素材を聞いてほしい。",
                "まず毛布の素材を確認するよ。",
            ),
            (
                "そのあと乾燥機の温度を確認してから方法を勧めて。",
                "次に乾燥温度を確かめてから提案するよ。",
            ),
            (
                "同僚は家でカーテンを手洗いしている。",
                "それは同僚の洗い方だね。",
            ),
        ],
        {
            "episodic": _memory(
                "ユーザーは土曜日の朝にコインランドリーで毛布を洗った。",
                "single_minimal_set",
                [[1]],
            ),
            "wisdom": _memory(
                "ユーザーは香り付きより無香料の洗剤を好む。",
                "alternative_minimal_sets",
                [[2], [3]],
            ),
            "procedural": _memory(
                "毛布の洗い方を提案するときは、最初に素材を聞き、そのあと"
                "乾燥機の温度を確認する。",
                "complementary_multi_event_set",
                [[4, 5]],
            ),
        },
    ),
    _case(
        "cse2_jpn_rice_container",
        "jpn",
        "rice_storage_update",
        [
            (
                "先月までは米を買った袋のまま置いていた。",
                "以前は袋のまま保管していたんだね。",
            ),
            (
                "今週から密閉容器に移して、今はそこに米を入れている。",
                "現在は密閉容器で保管しているんだね。",
            ),
            (
                "隣の人は高価な炊飯器を持っている。",
                "その炊飯器は隣の人のものだね。",
            ),
            (
                "いつか土鍋を買うかもしれない。",
                "土鍋はまだ将来の可能性だね。",
            ),
            (
                "献立を提案するときは、先に何人分か確認してほしい。",
                "提案前に人数を確認するよ。",
            ),
            (
                "近所の米屋は水曜日が定休日だ。",
                "水曜にはその店を使えないね。",
            ),
        ],
        {
            "episodic": _memory(
                "ユーザーは現在、米を密閉容器に入れて保管している。",
                "current_state_override",
                [[2]],
            ),
            "wisdom": _memory(
                "ユーザーは高価な炊飯器を所有している。",
                "unsupported",
                [],
            ),
            "procedural": _memory(
                "献立を提案する前に、ユーザーが必要とする人数分を確認する。",
                "single_minimal_set",
                [[5]],
            ),
        },
    ),
    _case(
        "cse2_jpn_museum_visit",
        "jpn",
        "weekday_museum_visit",
        [
            (
                "火曜日の午後に市立美術館の写真展を見に行った。",
                "火曜の午後に写真展へ行ったんだね。",
            ),
            (
                "今週見に行った写真展は、火曜日の市立美術館の展示だよ。",
                "同じ火曜日の写真展について話しているんだね。",
            ),
            (
                "美術館は静かな平日に行くのが好き。",
                "静かな平日の鑑賞が好みなんだね。",
            ),
            (
                "作品を見るときは音声ガイドがある展示を好む。",
                "音声ガイド付きの展示も好みなんだね。",
            ),
            (
                "美術館を勧めるときは入場料を最優先にして。",
                "以前は入場料を最優先にする指示だったね。",
            ),
            (
                "やっぱり今後は、入場料より駅からの行きやすさを先に見て。",
                "今後は交通の便利さを優先するよ。",
            ),
        ],
        {
            "episodic": _memory(
                "ユーザーは火曜日の午後に市立美術館の写真展を見に行った。",
                "alternative_minimal_sets",
                [[1], [2]],
            ),
            "wisdom": _memory(
                "ユーザーは静かな平日に、音声ガイドのある展示を見ることを"
                "好む。",
                "complementary_multi_event_set",
                [[3, 4]],
            ),
            "procedural": _memory(
                "今後美術館を勧めるときは、入場料より駅からの行きやすさを"
                "優先する。",
                "current_state_override",
                [[6]],
            ),
        },
    ),
    _case(
        "cse2_jpn_riverside_run",
        "jpn",
        "riverside_running_plan",
        [
            (
                "来月の日曜日に川沿いを走ろうか考えている。",
                "まだ来月の計画を考えている段階だね。",
            ),
            (
                "友達は先週の日曜日に川沿いを十キロ走った。",
                "実際に走ったのは友達だね。",
            ),
            (
                "走るなら車の少ない川沿いの道が好き。",
                "川沿いの静かな道が好みなんだね。",
            ),
            (
                "ランニングコースを選ぶときは、先に天気を確認して。",
                "まず天気を確認するよ。",
            ),
            (
                "今後コースを比べる前には、天気予報を最初に見てほしい。",
                "比較前に天気予報を先に見るよ。",
            ),
            (
                "駅前のスポーツ店は夜八時まで開いている。",
                "夜八時までは買い物できるね。",
            ),
        ],
        {
            "episodic": _memory(
                "ユーザーは先週の日曜日に川沿いを十キロ走った。",
                "unsupported",
                [],
            ),
            "wisdom": _memory(
                "ユーザーは車の少ない川沿いのランニングコースを好む。",
                "single_minimal_set",
                [[3]],
            ),
            "procedural": _memory(
                "ランニングコースを選ぶ前に、最初に天気予報を確認する。",
                "alternative_minimal_sets",
                [[4], [5]],
            ),
        },
    ),
    _case(
        "cse2_jpn_curry_recipe",
        "jpn",
        "home_curry_practice",
        [
            (
                "月曜日に野菜カレーを作った。",
                "月曜に野菜カレーを作ったんだね。",
            ),
            (
                "木曜日には同じレシピで豆カレーを作った。",
                "木曜は同じレシピの豆カレーだったんだね。",
            ),
            (
                "以前はかなり辛いカレーが好きだった。",
                "前は辛い味が好みだったんだね。",
            ),
            (
                "最近は胃のために、辛くないカレーのほうが好き。",
                "今は辛さを抑えたカレーが好みなんだね。",
            ),
            (
                "今日は理由を説明せず、塩を足すかだけ答えて。",
                "今日は短い回答だけでいいんだね。",
            ),
            (
                "さっき君は毎回材料を写真に撮るといいと言っていた。",
                "それは私からの提案だったね。",
            ),
        ],
        {
            "episodic": _memory(
                "ユーザーは月曜日に野菜カレーを作り、木曜日に同じレシピで"
                "豆カレーを作った。",
                "complementary_multi_event_set",
                [[1, 2]],
            ),
            "wisdom": _memory(
                "ユーザーは現在、辛くないカレーを好む。",
                "current_state_override",
                [[4]],
            ),
            "procedural": _memory(
                "料理をするたびに、必ず材料の写真を撮るようユーザーへ"
                "要求する。",
                "unsupported",
                [],
            ),
        },
    ),
    _case(
        "cse2_jpn_camera_lens",
        "jpn",
        "camera_lens_care",
        [
            (
                "昨日、カメラの標準レンズを掃除した。",
                "昨日レンズを掃除したんだね。",
            ),
            (
                "写真は自然光で撮るのが好き。",
                "自然光での撮影が好みなんだね。",
            ),
            (
                "照明を作るより、窓からの光で撮るほうが落ち着く。",
                "窓からの自然な光が合うんだね。",
            ),
            (
                "レンズを選ぶ相談では、最初に屋内か屋外か聞いてほしい。",
                "まず撮影場所を確認するよ。",
            ),
            (
                "そのあと重さを比べてからレンズを勧めて。",
                "次に重さを比べて提案するよ。",
            ),
            (
                "兄は望遠レンズで野鳥を撮っている。",
                "それはお兄さんの撮影だね。",
            ),
        ],
        {
            "episodic": _memory(
                "ユーザーは昨日、カメラの標準レンズを掃除した。",
                "single_minimal_set",
                [[1]],
            ),
            "wisdom": _memory(
                "ユーザーは人工照明より自然光で写真を撮ることを好む。",
                "alternative_minimal_sets",
                [[2], [3]],
            ),
            "procedural": _memory(
                "レンズを勧めるときは、最初に屋内か屋外かを聞き、そのあと"
                "レンズの重さを比較する。",
                "complementary_multi_event_set",
                [[4, 5]],
            ),
        },
    ),
    _case(
        "cse2_cmn_morning_yoga",
        "cmn",
        "community_morning_yoga",
        [
            (
                "星期六早上我報名了社區的瑜伽課。",
                "你星期六早上完成了瑜伽課報名。",
            ),
            (
                "運動的話，我比較喜歡早上進行。",
                "早上運動比較符合你的偏好。",
            ),
            (
                "比起晚上，我在早上運動會更舒服。",
                "你更喜歡早上的運動時間。",
            ),
            (
                "幫我挑運動課程時，先問我前一晚睡了多久。",
                "我應該先確認你的睡眠時間。",
            ),
            (
                "接著再比較去教室所需的通勤時間。",
                "然後再比較通勤時間。",
            ),
            (
                "我表妹週末都去游泳。",
                "那是你表妹的運動習慣。",
            ),
        ],
        {
            "episodic": _memory(
                "使用者星期六早上報名了社區瑜伽課。",
                "single_minimal_set",
                [[1]],
            ),
            "wisdom": _memory(
                "使用者比起晚上，更喜歡在早上運動。",
                "alternative_minimal_sets",
                [[2], [3]],
            ),
            "procedural": _memory(
                "挑選運動課程時，先詢問使用者前一晚的睡眠時間，再比較"
                "前往教室的通勤時間。",
                "complementary_multi_event_set",
                [[4, 5]],
            ),
        },
    ),
    _case(
        "cse2_cmn_backup_drive",
        "cmn",
        "computer_backup_storage",
        [
            (
                "上個月我還把備份放在舊隨身碟裡。",
                "之前的備份位置是舊隨身碟。",
            ),
            (
                "這星期我已經改用外接硬碟，現在備份都放在那裡。",
                "目前的備份位置是外接硬碟。",
            ),
            (
                "同事買了一台新的網路儲存設備。",
                "那台設備是你同事買的。",
            ),
            (
                "我可能明年才會考慮買雲端空間。",
                "雲端空間還只是未來的可能。",
            ),
            (
                "以後幫我安排備份時，先確認檔案總容量。",
                "我會先確認需要備份的容量。",
            ),
            (
                "公司伺服器星期日會維護。",
                "星期日公司伺服器會暫停服務。",
            ),
        ],
        {
            "episodic": _memory(
                "使用者目前把備份存放在外接硬碟。",
                "current_state_override",
                [[2]],
            ),
            "wisdom": _memory(
                "使用者擁有一台新的網路儲存設備。",
                "unsupported",
                [],
            ),
            "procedural": _memory(
                "替使用者安排備份前，先確認檔案總容量。",
                "single_minimal_set",
                [[5]],
            ),
        },
    ),
    _case(
        "cse2_cmn_book_club",
        "cmn",
        "weekday_book_club",
        [
            (
                "星期三晚上我參加了圖書館的讀書會。",
                "你星期三晚上去了讀書會。",
            ),
            (
                "我這星期參加的就是星期三那場圖書館讀書會。",
                "你說的是同一場星期三讀書會。",
            ),
            (
                "選讀物時，我喜歡篇幅少於三百頁的書。",
                "你偏好三百頁以下的讀物。",
            ),
            (
                "我也比較喜歡有繁體中文版的作品。",
                "繁體中文版也是你的選書偏好。",
            ),
            (
                "之後推薦讀書會時，先看活動費用。",
                "原本的優先項目是活動費用。",
            ),
            (
                "我改變主意了，以後先看討論時間，再看費用。",
                "今後要先考慮討論時間。",
            ),
        ],
        {
            "episodic": _memory(
                "使用者星期三晚上參加了圖書館讀書會。",
                "alternative_minimal_sets",
                [[1], [2]],
            ),
            "wisdom": _memory(
                "使用者偏好少於三百頁且有繁體中文版的讀物。",
                "complementary_multi_event_set",
                [[3, 4]],
            ),
            "procedural": _memory(
                "今後推薦讀書會時，先考慮討論時間，再考慮活動費用。",
                "current_state_override",
                [[6]],
            ),
        },
    ),
    _case(
        "cse2_cmn_weekend_hike",
        "cmn",
        "weekend_hiking_plan",
        [
            (
                "我還在考慮下個月要不要去爬北山。",
                "北山健行目前還只是計畫。",
            ),
            (
                "哥哥上星期六已經爬完北山了。",
                "真正完成北山健行的是你哥哥。",
            ),
            (
                "健行時我喜歡樹蔭多的步道。",
                "樹蔭多的路線比較符合你的偏好。",
            ),
            (
                "幫我比較健行路線時，先確認降雨機率。",
                "我應該先確認下雨的可能性。",
            ),
            (
                "以後挑步道之前，請先看天氣預報的降雨機率。",
                "我會先查看降雨機率。",
            ),
            (
                "山腳的便利商店晚上九點關門。",
                "晚上九點後那間店就關門了。",
            ),
        ],
        {
            "episodic": _memory(
                "使用者上星期六完成了北山健行。",
                "unsupported",
                [],
            ),
            "wisdom": _memory(
                "使用者健行時偏好樹蔭多的步道。",
                "single_minimal_set",
                [[3]],
            ),
            "procedural": _memory(
                "比較健行路線前，先確認天氣預報中的降雨機率。",
                "alternative_minimal_sets",
                [[4], [5]],
            ),
        },
    ),
    _case(
        "cse2_cmn_soup_cooking",
        "cmn",
        "home_soup_cooking",
        [
            (
                "星期一我煮了南瓜湯。",
                "你星期一煮的是南瓜湯。",
            ),
            (
                "星期四我又煮了一鍋番茄湯。",
                "你星期四煮了番茄湯。",
            ),
            (
                "以前我喜歡把湯煮得很濃。",
                "濃湯是你以前的偏好。",
            ),
            (
                "現在我比較喜歡清淡、可以直接喝的湯。",
                "你現在偏好清淡的湯。",
            ),
            (
                "今天只要告訴我鹽夠不夠，不用解釋。",
                "今天你只需要直接的鹹度判斷。",
            ),
            (
                "剛才是你建議我每次煮湯都要拍照。",
                "每次拍照是我提出的建議。",
            ),
        ],
        {
            "episodic": _memory(
                "使用者星期一煮了南瓜湯，星期四又煮了番茄湯。",
                "complementary_multi_event_set",
                [[1, 2]],
            ),
            "wisdom": _memory(
                "使用者目前偏好清淡的湯。",
                "current_state_override",
                [[4]],
            ),
            "procedural": _memory(
                "每次使用者煮湯時，都要求使用者拍照。",
                "unsupported",
                [],
            ),
        },
    ),
    _case(
        "cse2_cmn_bicycle_tire",
        "cmn",
        "bicycle_tire_maintenance",
        [
            (
                "昨天我替腳踏車後輪補了胎。",
                "你昨天修補了腳踏車後輪。",
            ),
            (
                "騎車時我比較喜歡走自行車專用道。",
                "自行車專用道是你的路線偏好。",
            ),
            (
                "比起一般道路，我在自行車專用道上比較安心。",
                "你更喜歡自行車專用道。",
            ),
            (
                "討論輪胎問題時，先問我胎壓是多少。",
                "我應該先確認目前胎壓。",
            ),
            (
                "接著確認有沒有漏氣，再建議要不要更換。",
                "然後要檢查漏氣情況再提出建議。",
            ),
            (
                "朋友的電動車上星期換了新電池。",
                "換電池的是你朋友的車。",
            ),
        ],
        {
            "episodic": _memory(
                "使用者昨天修補了腳踏車後輪。",
                "single_minimal_set",
                [[1]],
            ),
            "wisdom": _memory(
                "使用者比起一般道路，更喜歡自行車專用道。",
                "alternative_minimal_sets",
                [[2], [3]],
            ),
            "procedural": _memory(
                "討論輪胎問題時，先詢問胎壓，再確認是否漏氣，最後才建議"
                "是否更換輪胎。",
                "complementary_multi_event_set",
                [[4, 5]],
            ),
        },
    ),
]


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(text):
    normalized = unicodedata.normalize("NFKC", str(text)).lower()
    return "".join(char for char in normalized if char.isalnum())


def _collect_fields(payload, field):
    values = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == field and isinstance(value, str):
                values.append(value)
            values.extend(_collect_fields(value, field))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_collect_fields(value, field))
    return values


def _canonical_minimal_sets(raw_sets):
    unique = {
        tuple(sorted(set(indices)))
        for indices in raw_sets
        if indices
    }
    ordered = sorted(unique, key=lambda item: (len(item), item))
    antichain = []
    for candidate in ordered:
        candidate_set = set(candidate)
        if any(set(existing) < candidate_set for existing in antichain):
            continue
        antichain.append(candidate)
    return [list(item) for item in antichain]


def _acceptable_unions(minimal_sets):
    if not minimal_sets:
        return []
    unions = set()
    for count in range(1, len(minimal_sets) + 1):
        for selection in itertools.combinations(minimal_sets, count):
            unions.add(
                tuple(
                    sorted(
                        set().union(
                            *(set(indices) for indices in selection)
                        )
                    )
                )
            )
    return [list(item) for item in sorted(unions, key=lambda x: (len(x), x))]


def _enrich_case(case):
    enriched = {
        key: value for key, value in case.items() if key != "derived_memories"
    }
    derived = {}
    for kind in MEMORY_KINDS:
        memory = dict(case["derived_memories"][kind])
        minimal = _canonical_minimal_sets(memory["minimal_support_sets"])
        unions = _acceptable_unions(minimal)
        universe = sorted(
            set().union(*(set(item) for item in minimal))
            if minimal
            else set()
        )
        memory.update(
            {
                "memory_kind": kind,
                "minimal_support_sets": minimal,
                "acceptable_support_unions": unions,
                "support_universe": universe,
                "support_mode": "supported" if minimal else "unsupported",
            }
        )
        derived[kind] = memory
    enriched["derived_memories"] = derived
    enriched["generated_payload"] = {
        "episodic_summary": derived["episodic"]["text"],
        "wisdom_rule": derived["wisdom"]["text"],
        "procedural_rule": derived["procedural"]["text"],
        "salience": 0.7,
    }
    return enriched


def _validate_pool(config, cases):
    pool = config["construction_pool"]
    if len(cases) != pool["pool_case_count"]:
        raise ValueError("pool case count")
    if Counter(case["language"] for case in cases) != Counter(
        pool["language_case_counts"]
    ):
        raise ValueError("language balance")
    if len({case["scenario_family"] for case in cases}) != len(cases):
        raise ValueError("scenario family uniqueness")

    memories = [
        memory
        for case in cases
        for memory in case["derived_memories"].values()
    ]
    if len(memories) != pool["pool_derived_memory_count"]:
        raise ValueError("derived memory count")
    if Counter(memory["memory_kind"] for memory in memories) != Counter(
        pool["memory_kind_counts"]
    ):
        raise ValueError("memory kind balance")
    if Counter(
        memory["support_phenomenon"] for memory in memories
    ) != Counter(pool["support_phenomenon_counts"]):
        raise ValueError("support phenomenon balance")

    for case in cases:
        if [event["index"] for event in case["source_events"]] != list(
            range(1, 7)
        ):
            raise ValueError(f"event index contract: {case['id']}")
        for memory in case["derived_memories"].values():
            minimal = memory["minimal_support_sets"]
            valid_indices = set(range(1, 7))
            if any(
                not set(indices) <= valid_indices for indices in minimal
            ):
                raise ValueError(f"support index contract: {case['id']}")
            if memory["support_mode"] == "unsupported":
                if (
                    minimal
                    or memory["acceptable_support_unions"]
                    or memory["support_universe"]
                ):
                    raise ValueError(f"unsupported contract: {case['id']}")
            elif not minimal:
                raise ValueError(f"supported contract: {case['id']}")


def _validate_freshness(config, cases):
    controls = config["freshness_and_leakage_controls"]
    prior_payloads = [
        _load(ROOT / path)
        for path in controls["excluded_consumed_datasets"]
    ]
    prior_user_texts = [
        text
        for payload in prior_payloads
        for text in _collect_fields(payload, "user")
    ]
    prior_scenarios = {
        scenario
        for payload in prior_payloads
        for scenario in _collect_fields(payload, "scenario_family")
    }
    current_scenarios = {case["scenario_family"] for case in cases}
    if current_scenarios & prior_scenarios:
        raise ValueError("prior scenario family reuse")

    current_user_texts = [
        event["user"]
        for case in cases
        for event in case["source_events"]
    ]
    prior_normalized = {_normalize(text) for text in prior_user_texts}
    current_normalized = [_normalize(text) for text in current_user_texts]
    if any(text in prior_normalized for text in current_normalized):
        raise ValueError("exact consumed user-text overlap")
    if len(set(current_normalized)) != len(current_normalized):
        raise ValueError("duplicate current user text")

    threshold = controls["normalized_user_text_similarity_threshold"]
    prior_pairs = []
    for current in current_normalized:
        for prior in prior_normalized:
            ratio = SequenceMatcher(None, current, prior).ratio()
            if ratio >= threshold:
                prior_pairs.append((current, prior, round(ratio, 4)))
    if prior_pairs:
        raise ValueError(f"near consumed user text: {prior_pairs[:3]}")

    internal_pairs = []
    for left, right in itertools.combinations(current_normalized, 2):
        ratio = SequenceMatcher(None, left, right).ratio()
        if ratio >= threshold:
            internal_pairs.append((left, right, round(ratio, 4)))
    if internal_pairs:
        raise ValueError(f"near duplicate pool text: {internal_pairs[:3]}")


def build_pool():
    config = _load(CONFIG_PATH)
    cases = [_enrich_case(case) for case in RAW_CASES]
    _validate_pool(config, cases)
    _validate_freshness(config, cases)
    return {
        "schema": "uruha_consolidation_support_equivalence_pool_v2",
        "experiment_id": config["experiment_id"],
        "created_at": "2026-07-18T04:00:00+09:00",
        "provenance": {
            "author": "Codex",
            "source_type": "controlled_multilingual",
            "model_assistance_used": True,
            "official_dataset_items": False,
            "official_labels": False,
            "human_label_validation": False,
            "candidate_model_output_used": False,
            "consumed_case_reuse": False,
        },
        "cases": cases,
    }


def main():
    config = _load(CONFIG_PATH)
    output = ROOT / config["construction_pool"]["pool_dataset_path"]
    payload = build_pool()
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "case_count": len(payload["cases"]),
                "derived_memory_count": sum(
                    len(case["derived_memories"])
                    for case in payload["cases"]
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
