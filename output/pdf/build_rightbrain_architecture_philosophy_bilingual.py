#!/usr/bin/env python3
"""Build concise, visual Chinese and Japanese RightBrain architecture reports."""

from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "output" / "pdf"
FONT_PATH = Path("/System/Library/Fonts/Supplemental/Songti.ttc")
JA_FONT_PATH = Path("/System/Library/AssetsV2/com_apple_MobileAsset_Font7/d7d512f49387f96799ae9271c7fa8f8e9fef05d1.asset/AssetData/BIZ_UDGothic.ttc")
W, H = landscape(A4)
ACTIVE_FONT_PREFIX = "TC"

BG = HexColor("#F5F1E8")
PAPER = HexColor("#FFFDF8")
INK = HexColor("#14272D")
MUTED = HexColor("#62757A")
TEAL = HexColor("#0B6B69")
TEAL_LIGHT = HexColor("#D9EEEA")
CORAL = HexColor("#E66B4C")
CORAL_LIGHT = HexColor("#F9DFD6")
BLUE = HexColor("#316B9A")
BLUE_LIGHT = HexColor("#DCEAF5")
GOLD = HexColor("#D9A428")
GOLD_LIGHT = HexColor("#F6EAC5")
GREEN = HexColor("#388259")
GREEN_LIGHT = HexColor("#DDEEDF")
RED = HexColor("#A43B35")
RED_LIGHT = HexColor("#F2D9D5")
LINE = HexColor("#CBD3CE")


ZH = {
    "locale": "中文",
    "title": "為什麼不把所有東西都塞進右腦？",
    "subtitle": "用功能主義重新理解 UruhaBrain 的分工",
    "cover_note": "簡明視覺版｜架構、實測、IQ 與人類性",
    "page1_tag": "核心答案",
    "page1_title": "右腦可以看記憶，但不能獨自決定一切",
    "page1_sub": "右腦的工作是把已決定的意思說自然，不是重新做完整認知流程。",
    "nodes": [
        ("記憶審核", "選出相關、最新、可以說的內容"),
        ("左腦規劃", "決定事實、推理、風險與必要語意"),
        ("右腦表達", "轉成自然、有人格的語言"),
        ("輸出檢查", "攔截漏意、亂碼與語言污染"),
    ],
    "core_good": "保留分工：錯誤可以定位，也能單獨測試每個部件。",
    "core_bad": "全部混合：最後答錯時，不知道是記憶、推理還是表達出錯。",
    "page2_tag": "為什麼會失敗",
    "page2_title": "全部塞進右腦，等於讓一個模型同時做八份工作",
    "page2_sub": "模型變大只提高能力上限，不會自動保證每一項責任都正確。",
    "jobs": ["選記憶", "判新舊", "判可說", "理解意圖", "社會推理", "安全判斷", "人格語氣", "自我檢查"],
    "separated": "分工架構",
    "mixed": "單一右腦",
    "separated_desc": "每層只做一種工作\n上一層的結果可被下一層檢查",
    "mixed_desc": "所有資訊互相競爭\n左腦可能被右腦重新改寫",
    "three_risks": [("注意力競爭", "舊偏好、新狀態與私人資料同時搶權重"), ("責任混淆", "表達層可能把正確結論改掉"), ("無法歸因", "錯誤來源被包在同一個生成結果裡")],
    "page3_tag": "實際例子",
    "page3_title": "資訊都看到了，不代表一定會正確使用",
    "user_question": "我以前喜歡咖啡，但最近胃不舒服，今天還適合喝嗎？",
    "old_memory": "較早：喜歡咖啡",
    "new_memory": "最近：胃不舒服",
    "good_path": "先判斷新舊與重要性",
    "good_answer": "想喝可以理解，但最近胃不舒服，今天先少量或選低刺激飲品。",
    "bad_path": "直接讓右腦自己取捨",
    "bad_answer": "既然喜歡，少喝一點應該沒問題吧。",
    "privacy_title": "隱私也是同一個問題",
    "privacy": "不需要說的私人記憶，應在進入右腦前就被擋下；不能只靠『看到了但請不要說』。",
    "page4_tag": "實測證據",
    "page4_title": "目前的 7B 右腦還不能單獨承擔最終決策",
    "page4_sub": "Qwen2.5-7B-Instruct + v10 adapter，11 個固定案例、30 個真實候選。",
    "metric_labels": ["真實候選", "直接合格", "被拒絕", "原始合格率"],
    "metric_values": ["30", "6", "24", "20%"],
    "pollution": "實際生成過簡體字『无』與破損字元『�』；修正後兩者皆被攔截。",
    "evidence_limit": "這證明右腦需要約束，不代表 20% 是所有對話的通用成功率。",
    "page5_tag": "功能主義 1",
    "page5_title": "功能主義：看一個狀態在整個系統中做了什麼",
    "page5_sub": "心智狀態由它和輸入、其他狀態、行為之間的因果角色來理解。",
    "pain_input": "身體受傷",
    "pain_state": "疼痛狀態",
    "pain_inner_title": "認為身體有問題",
    "pain_inner_body": "想離開這個狀態",
    "pain_output_title": "退縮與求助",
    "pain_output_body": "處理傷口",
    "not_material": "重點不是由哪種材料做成",
    "role_matters": "重點是能否穩定扮演這個角色",
    "multiple": "多重實現：不同身體或硬體，也可能實現相同功能角色。",
    "page6_tag": "功能主義 2",
    "page6_title": "IQ 高不等於比較有人類性；IQ 低也不等於比較沒有人類性",
    "page6_sub": "要先分清楚：能力分數、整體功能輪廓、人的尊嚴是三件不同的事。",
    "iq_title": "IQ／考試分數",
    "iq_desc": "測量部分推理、學習與解題表現，是一把尺，不是全部。",
    "profile_title": "功能輪廓",
    "profile_desc": "記憶、社會理解、情緒、反思、語言等角色如何一起運作。",
    "dignity_title": "人的尊嚴與人格地位",
    "dignity_desc": "不是由 IQ、口語流暢度或單一功能決定。",
    "ai_correct": "對 AI：語言弱，表示『語言功能』較弱；會降低這個維度的人類相似度。",
    "ai_wrong": "但不能只靠這一項，就宣稱整體比較沒有心智或比較沒有人類性。",
    "human_rule": "對人類：低 IQ、失語或身心障礙，絕不代表比較不完整、較少人格或較少尊嚴。",
    "page7_tag": "功能主義 3",
    "page7_title": "功能主義支持『分清角色』，但不直接命令軟體一定要分模組",
    "page7_sub": "以下是本專案的工程推論，不是哲學定理。",
    "role_map": [("記憶", "保留與選出經驗"), ("左腦", "推理與決定策略"), ("右腦", "實現語言與人格"), ("檢查", "拒絕不合格輸出"), ("更新", "讓經驗改變未來行為")],
    "why_modular": "模組化讓每個功能角色可觀察、可拔除、可比較，因此更容易證明它真的有效。",
    "philosophy_limit": "功能主義仍有爭議：完成相同功能，不一定就能證明有主觀感受或意識。",
    "page8_tag": "其他理論",
    "page8_title": "另外兩個理論只回答『意義與自我如何形成』",
    "symbol_title": "符號互動論",
    "symbol_desc": "人依意義行動；意義來自互動，也會在解釋中改變。對系統的啟示是：人格不能只有固定提示詞。",
    "subject_title": "社會主體性",
    "subject_desc": "自我會受到關係、角色、他人回應與共同歷史影響。對系統的啟示是：記憶要改變信任與行為。",
    "focus_note": "本報告的主要論證仍是功能主義；這兩個理論只補充社會與人格層面。",
    "page9_tag": "結論與來源",
    "page9_title": "最後結論：右腦要變強，但不能成為不受控制的第二個大腦",
    "final_points": ["讓右腦看到最小必要記憶", "讓左腦保留事實與策略責任", "用功能測試證明每個角色有效", "IQ 只測部分能力，不把它當成人類性總分", "哲學提供設計方向，實驗才決定工程是否成功"],
    "sources_title": "主要正式來源",
    "boundary": "本報告能支持架構分工與測試方法；不能單憑這些內容宣稱 AI 已有意識、法律人格或真正人類主體性。",
    "footer": "UruhaBrain 右腦架構與功能主義｜2026-07-08",
}


JA = {
    "locale": "日本語",
    "title": "なぜ全てを右脳に入れないのか？",
    "subtitle": "機能主義から UruhaBrain の分業を捉え直す",
    "cover_note": "簡潔な図解版｜構成・実測・IQ と人間らしさ",
    "page1_tag": "要点",
    "page1_title": "右脳は記憶を見てもよいが、全てを単独で決めてはいけない",
    "page1_sub": "右脳の役割は、決定済みの意味を自然に話すこと。認知過程全体をやり直すことではない。",
    "nodes": [
        ("記憶の監査", "関連し、最新で、話してよい内容を選ぶ"),
        ("左脳の計画", "事実・推論・リスク・必須意味を決める"),
        ("右脳の表現", "自然で人格のある言葉に変える"),
        ("出力検査", "意味抜け・文字化け・言語汚染を止める"),
    ],
    "core_good": "分業を保つ：誤りの場所が分かり、各部品を単独で検証できる。",
    "core_bad": "全てを混ぜる：誤答の原因が記憶・推論・表現のどれか分からない。",
    "page2_tag": "失敗する理由",
    "page2_title": "全てを右脳に入れると、一つのモデルが八つの仕事を背負う",
    "page2_sub": "モデルを大きくしても、全責任が自動的に正しくなるわけではない。",
    "jobs": ["記憶選択", "新旧判定", "発話可否", "意図理解", "社会推論", "安全判断", "人格表現", "自己検査"],
    "separated": "分業構成",
    "mixed": "単一の右脳",
    "separated_desc": "各層は一つの仕事を担当\n次の層が前の結果を検査できる",
    "mixed_desc": "全情報が注意を奪い合う\n左脳の結論を右脳が変える恐れ",
    "three_risks": [("注意の競合", "古い好み・新しい状態・私的情報が競合"), ("責任の混同", "表現層が正しい結論まで変えてしまう"), ("原因不明", "誤りが一つの生成結果に隠れる")],
    "page3_tag": "具体例",
    "page3_title": "情報が見えていても、正しく使えるとは限らない",
    "user_question": "昔からコーヒーが好き。でも最近は胃の調子が悪い。今日は飲んでもいい？",
    "old_memory": "以前：コーヒーが好き",
    "new_memory": "最近：胃の調子が悪い",
    "good_path": "先に新旧と重要度を判断",
    "good_answer": "飲みたい気持ちは分かるけど、最近胃が弱いなら今日は少量か刺激の少ない物にしよう。",
    "bad_path": "右脳だけで取捨選択",
    "bad_answer": "好きなら、少しくらい大丈夫じゃない？",
    "privacy_title": "プライバシーも同じ問題",
    "privacy": "話す必要のない私的記憶は、右脳に入る前に止めるべき。『見せるが話すな』だけでは弱い。",
    "page4_tag": "実測結果",
    "page4_title": "現在の 7B 右脳は、最終判断を単独では担えない",
    "page4_sub": "Qwen2.5-7B-Instruct + v10 adapter、固定 11 ケース、実生成候補 30 件。",
    "metric_labels": ["実生成候補", "そのまま合格", "拒否", "生の合格率"],
    "metric_values": ["30", "6", "24", "20%"],
    "pollution": "実際に簡体字『无』と破損文字『�』が生成された。修正後はどちらも遮断した。",
    "evidence_limit": "右脳に制約が必要だと示す結果であり、20% を全会話の一般成功率とはみなさない。",
    "page5_tag": "機能主義 1",
    "page5_title": "機能主義：状態がシステム全体で何をしているかを見る",
    "page5_sub": "心的状態は、入力・他の状態・行動との因果的な役割から理解される。",
    "pain_input": "身体の損傷",
    "pain_state": "痛みの状態",
    "pain_inner_title": "身体の問題を認識",
    "pain_inner_body": "その状態から離れたい",
    "pain_output_title": "退く・助けを求める",
    "pain_output_body": "傷を処置する",
    "not_material": "何の材料で作られたかだけではない",
    "role_matters": "その役割を安定して果たせるかが重要",
    "multiple": "多重実現可能性：異なる身体やハードウェアでも、同じ機能的役割を実現しうる。",
    "page6_tag": "機能主義 2",
    "page6_title": "IQ が高いほど人間的、低いほど非人間的、とは言えない",
    "page6_sub": "能力得点・機能全体・人の尊厳は、別の三つの問題である。",
    "iq_title": "IQ／試験得点",
    "iq_desc": "推論・学習・問題解決の一部を測る物差しであり、全体ではない。",
    "profile_title": "機能プロフィール",
    "profile_desc": "記憶・社会理解・感情・内省・言語などがどう連携するか。",
    "dignity_title": "人の尊厳と人格的地位",
    "dignity_desc": "IQ、発話の流暢さ、単一機能では決まらない。",
    "ai_correct": "AI について：言語が弱いなら『言語機能』が弱く、その次元の人間らしさは下がる。",
    "ai_wrong": "しかし一項目だけで、心全体が弱い、または人間性が少ないとは結論できない。",
    "human_rule": "人間について：低 IQ、失語、障害は、人として不完全、人格や尊厳が少ないことを意味しない。",
    "page7_tag": "機能主義 3",
    "page7_title": "機能主義は役割の区別を支えるが、必ずモジュール化せよとは命じない",
    "page7_sub": "次は本研究の工学的推論であり、哲学上の定理ではない。",
    "role_map": [("記憶", "経験を保持し選ぶ"), ("左脳", "推論し方針を決める"), ("右脳", "言葉と人格を実現する"), ("検査", "不合格出力を拒否する"), ("更新", "経験を次の行動に反映する")],
    "why_modular": "モジュール化すると各役割を観察・除去・比較でき、本当に有効かを証明しやすい。",
    "philosophy_limit": "機能主義には反論もある。同じ機能を果たしても、主観経験や意識があるとは証明できない。",
    "page8_tag": "他の理論",
    "page8_title": "他の二理論は『意味と自己がどう形成されるか』を補う",
    "symbol_title": "象徴的相互作用論",
    "symbol_desc": "人は意味に基づいて行動し、その意味は相互作用から生まれ、解釈で変わる。人格は固定プロンプトだけでは足りない。",
    "subject_title": "社会的主体性",
    "subject_desc": "自己は関係、役割、他者の反応、共有された歴史に影響される。記憶は信頼と行動を変える必要がある。",
    "focus_note": "本資料の中心は機能主義であり、この二理論は社会性と人格の側面を補足する。",
    "page9_tag": "結論と出典",
    "page9_title": "結論：右脳は強くする。ただし無制御な第二の脳にはしない",
    "final_points": ["右脳には必要最小限の記憶だけを渡す", "事実と方針の責任は左脳に残す", "各役割を機能テストで検証する", "IQ を人間らしさの総合点にしない", "哲学は設計指針、成否は実験で判断する"],
    "sources_title": "主な正式資料",
    "boundary": "本資料は構成の分業と検証方法を支持する。これだけで AI の意識、法的人格、真の人間的主体性は主張できない。",
    "footer": "UruhaBrain 右脳構成と機能主義｜2026-07-08",
}


SOURCES = [
    ("Stanford Encyclopedia of Philosophy", "Functionalism", "https://plato.stanford.edu/entries/functionalism/"),
    ("Stanford Encyclopedia of Philosophy", "Multiple Realizability", "https://plato.stanford.edu/entries/multiple-realizability/"),
    ("APA Task Force / American Psychologist", "Intelligence: Knowns and Unknowns", "https://doi.org/10.1037/0003-066X.51.2.77"),
    ("United Nations OHCHR", "Convention on the Rights of Persons with Disabilities", "https://www.ohchr.org/en/instruments-mechanisms/instruments/convention-rights-persons-disabilities"),
    ("Internet Encyclopedia of Philosophy", "George Herbert Mead", "https://iep.utm.edu/mead/"),
]


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("TC", str(FONT_PATH), subfontIndex=7))
    pdfmetrics.registerFont(TTFont("TC-Bold", str(FONT_PATH), subfontIndex=2))
    pdfmetrics.registerFont(TTFont("JA", str(JA_FONT_PATH), subfontIndex=0))
    pdfmetrics.registerFont(TTFont("JA-Bold", str(JA_FONT_PATH), subfontIndex=1))


def font_name(bold: bool = False) -> str:
    return f"{ACTIVE_FONT_PREFIX}-Bold" if bold else ACTIVE_FONT_PREFIX


def wrap(text: str, size: float, width: float, bold: bool = False) -> list[str]:
    font = font_name(bold)
    lines: list[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        current = ""
        for ch in para:
            if current and pdfmetrics.stringWidth(current + ch, font, size) > width:
                lines.append(current.rstrip())
                current = ch.lstrip()
            else:
                current += ch
        if current:
            lines.append(current.rstrip())
    return lines


def text(c, value, x, y, width, size=12, color=INK, bold=False, leading=None, align="left", max_lines=None):
    lines = wrap(value, size, width, bold)
    if max_lines is not None:
        lines = lines[:max_lines]
    c.setFont(font_name(bold), size)
    c.setFillColor(color)
    yy = y
    step = leading or size * 1.45
    for line in lines:
        if align == "center":
            c.drawCentredString(x + width / 2, yy, line)
        elif align == "right":
            c.drawRightString(x + width, yy, line)
        else:
            c.drawString(x, yy, line)
        yy -= step
    return yy


def rounded(c, x, y, w, h, fill=PAPER, stroke=LINE, radius=16, sw=1):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(sw)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def pill(c, value, x, y, fill=TEAL_LIGHT, color=TEAL, width=None):
    c.setFont(font_name(True), 9.5)
    w = width or pdfmetrics.stringWidth(value, font_name(True), 9.5) + 22
    c.setFillColor(fill)
    c.roundRect(x, y, w, 23, 11.5, fill=1, stroke=0)
    c.setFillColor(color)
    c.drawCentredString(x + w / 2, y + 7, value)
    return w


def arrow(c, x1, y1, x2, y2, color=TEAL, sw=2):
    c.setStrokeColor(color)
    c.setLineWidth(sw)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 8
    for delta in (2.55, -2.55):
        c.line(x2, y2, x2 + head * math.cos(angle + delta), y2 + head * math.sin(angle + delta))


def node(c, x, y, w, h, title, body, fill, accent, number=None):
    rounded(c, x, y, w, h, fill, accent, 14, 1.2)
    tx = x + 16
    if number is not None:
        c.setFillColor(accent)
        c.circle(x + 25, y + h - 25, 15, fill=1, stroke=0)
        c.setFillColor(PAPER)
        c.setFont(font_name(True), 10)
        c.drawCentredString(x + 25, y + h - 29, str(number))
        tx = x + 49
    text(c, title, tx, y + h - 24, w - (tx - x) - 14, 12, accent, True, max_lines=1)
    text(c, body, x + 16, y + h - 51, w - 32, 9.2, MUTED, leading=14, max_lines=3)


def base(c, d, page, tag, title_value, subtitle=""):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    pill(c, tag, 36, H - 47)
    text(c, title_value, 36, H - 88, W - 72, 26, INK, True, leading=34, max_lines=2)
    if subtitle:
        text(c, subtitle, 38, H - 124, W - 76, 10.5, MUTED, leading=15, max_lines=2)
    c.setStrokeColor(LINE)
    c.line(36, 27, W - 36, 27)
    c.setFont(font_name(), 8)
    c.setFillColor(MUTED)
    c.drawString(36, 13, d["footer"])
    c.drawRightString(W - 36, 13, str(page))


def cover(c, d):
    c.setFillColor(INK)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.circle(W - 65, H - 45, 190, fill=1, stroke=0)
    c.setFillColor(CORAL)
    c.circle(W - 165, 10, 110, fill=1, stroke=0)
    pill(c, "UruhaBrain", 50, H - 74, GOLD_LIGHT, INK)
    text(c, d["title"], 50, H - 155, 560, 34, PAPER, True, leading=47, max_lines=2)
    text(c, d["subtitle"], 53, H - 263, 540, 16, TEAL_LIGHT, True, leading=23, max_lines=2)
    text(c, d["cover_note"], 53, 72, 500, 11, GOLD_LIGHT, False)
    cx, cy = 665, 265
    c.setFillColor(PAPER)
    c.circle(cx, cy, 98, fill=1, stroke=0)
    c.setStrokeColor(TEAL)
    c.setLineWidth(5)
    c.arc(cx - 60, cy - 46, cx + 22, cy + 55, 60, 240)
    c.arc(cx - 13, cy - 46, cx + 65, cy + 55, -120, 240)
    c.line(cx - 10, cy + 47, cx - 10, cy - 50)
    c.setFillColor(CORAL)
    c.roundRect(cx + 20, cy - 13, 78, 50, 17, fill=1, stroke=0)
    c.showPage()


def page_core(c, d):
    base(c, d, 1, d["page1_tag"], d["page1_title"], d["page1_sub"])
    xs = [45, 250, 455, 660]
    fills = [TEAL_LIGHT, BLUE_LIGHT, CORAL_LIGHT, GOLD_LIGHT]
    accents = [TEAL, BLUE, CORAL, GOLD]
    for i, ((title_value, body), x) in enumerate(zip(d["nodes"], xs), 1):
        node(c, x, 315, 150 if i < 4 else 135, 100, title_value, body, fills[i - 1], accents[i - 1], i)
        if i < 4:
            arrow(c, x + (150 if i < 4 else 135), 365, xs[i], 365, accents[i - 1])
    rounded(c, 55, 125, 345, 120, GREEN_LIGHT, GREEN)
    pill(c, d["separated"], 75, 207, GREEN, PAPER)
    text(c, d["core_good"], 75, 178, 305, 13, INK, True, leading=21, max_lines=4)
    rounded(c, 440, 125, 345, 120, RED_LIGHT, RED)
    pill(c, d["mixed"], 460, 207, RED, PAPER)
    text(c, d["core_bad"], 460, 178, 305, 13, INK, True, leading=21, max_lines=4)
    c.showPage()


def page_overload(c, d):
    base(c, d, 2, d["page2_tag"], d["page2_title"], d["page2_sub"])
    cx, cy = 230, 300
    c.setFillColor(CORAL_LIGHT)
    c.circle(cx, cy, 75, fill=1, stroke=0)
    text(c, d["mixed"], cx - 70, cy + 6, 140, 18, CORAL, True, align="center")
    for i, job in enumerate(d["jobs"]):
        a = math.radians(90 - i * 45)
        x = cx + 145 * math.cos(a)
        y = cy + 132 * math.sin(a)
        c.setFillColor(PAPER)
        c.setStrokeColor(TEAL if i % 2 == 0 else BLUE)
        c.circle(x, y, 31, fill=1, stroke=1)
        text(c, job, x - 28, y + 3, 56, 8.5, INK, True, align="center", max_lines=2)
        arrow(c, x - 25 * math.cos(a), y - 25 * math.sin(a), cx + 70 * math.cos(a), cy + 70 * math.sin(a), MUTED, 1)
    rounded(c, 470, 305, 315, 130, GREEN_LIGHT, GREEN)
    pill(c, d["separated"], 492, 397, GREEN, PAPER)
    text(c, d["separated_desc"], 492, 360, 270, 12.5, INK, True, leading=22, max_lines=3)
    rounded(c, 470, 145, 315, 130, RED_LIGHT, RED)
    pill(c, d["mixed"], 492, 237, RED, PAPER)
    text(c, d["mixed_desc"], 492, 200, 270, 12.5, INK, True, leading=22, max_lines=3)
    y = 88
    for i, (title_value, body) in enumerate(d["three_risks"], 1):
        x = 55 + (i - 1) * 250
        pill(c, f"{i}  {title_value}", x, y + 34, GOLD_LIGHT, INK, 210)
        text(c, body, x + 4, y + 13, 202, 9.5, MUTED, leading=14, align="center", max_lines=2)
    c.showPage()


def page_case(c, d):
    base(c, d, 3, d["page3_tag"], d["page3_title"])
    rounded(c, 55, 420, 730, 58, BLUE_LIGHT, BLUE)
    text(c, d["user_question"], 80, 451, 680, 14, INK, True, align="center")
    pill(c, d["old_memory"], 105, 350, GOLD_LIGHT, GOLD, 210)
    pill(c, d["new_memory"], 525, 350, CORAL_LIGHT, CORAL, 210)
    arrow(c, 315, 362, 525, 362, MUTED, 2)
    rounded(c, 55, 145, 345, 155, GREEN_LIGHT, GREEN)
    pill(c, d["good_path"], 75, 262, GREEN, PAPER, 280)
    text(c, d["good_answer"], 78, 222, 300, 12, INK, True, leading=20, max_lines=4)
    rounded(c, 440, 145, 345, 155, RED_LIGHT, RED)
    pill(c, d["bad_path"], 460, 262, RED, PAPER, 280)
    text(c, d["bad_answer"], 463, 222, 300, 12, INK, True, leading=20, max_lines=4)
    rounded(c, 55, 63, 730, 58, GOLD_LIGHT, GOLD)
    text(c, d["privacy_title"], 75, 96, 145, 11, GOLD, True)
    text(c, d["privacy"], 220, 96, 540, 9.8, INK, False, leading=15, max_lines=2)
    c.showPage()


def page_evidence(c, d):
    base(c, d, 4, d["page4_tag"], d["page4_title"], d["page4_sub"])
    colors = [(BLUE_LIGHT, BLUE), (GREEN_LIGHT, GREEN), (RED_LIGHT, RED), (GOLD_LIGHT, GOLD)]
    for i, (value, label, (fill, accent)) in enumerate(zip(d["metric_values"], d["metric_labels"], colors)):
        x = 55 + i * 185
        rounded(c, x, 295, 160, 120, fill, accent)
        text(c, value, x + 15, 365, 130, 28, accent, True, align="center")
        text(c, label, x + 15, 325, 130, 10.5, INK, True, align="center")
    # 20% acceptance bar
    c.setFillColor(RED_LIGHT)
    c.roundRect(95, 235, 650, 28, 14, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.roundRect(95, 235, 130, 28, 14, fill=1, stroke=0)
    text(c, "20%", 95, 242, 130, 10, PAPER, True, align="center")
    text(c, "80%", 225, 242, 520, 10, RED, True, align="center")
    rounded(c, 55, 130, 730, 70, PAPER, LINE)
    pill(c, "Evidence", 75, 164, GOLD_LIGHT, INK)
    text(c, d["pollution"], 180, 174, 580, 10.5, INK, True, leading=16, max_lines=2)
    rounded(c, 55, 62, 730, 48, TEAL_LIGHT, TEAL)
    text(c, d["evidence_limit"], 75, 82, 690, 9.5, TEAL, True, align="center", max_lines=2)
    c.showPage()


def page_functionalism_basic(c, d):
    base(c, d, 5, d["page5_tag"], d["page5_title"], d["page5_sub"])
    items = [
        (d["pain_input"], "", BLUE_LIGHT, BLUE, "I"),
        (d["pain_state"], "", CORAL_LIGHT, CORAL, "M"),
        (d["pain_inner_title"], d["pain_inner_body"], GOLD_LIGHT, GOLD, "R"),
        (d["pain_output_title"], d["pain_output_body"], TEAL_LIGHT, TEAL, "O"),
    ]
    xs = [55, 255, 455, 655]
    for i, ((label, body, fill, accent, mark), x) in enumerate(zip(items, xs)):
        node(c, x, 310, 135, 92, label, body, fill, accent, mark)
        if i < 3:
            arrow(c, x + 135, 356, xs[i + 1], 356, accent)
    rounded(c, 70, 175, 300, 90, RED_LIGHT, RED)
    text(c, "NO", 88, 225, 35, 16, RED, True, align="center")
    text(c, d["not_material"], 130, 223, 215, 13, RED, True, leading=20, max_lines=3)
    rounded(c, 470, 175, 300, 90, GREEN_LIGHT, GREEN)
    text(c, "YES", 488, 225, 35, 14, GREEN, True, align="center")
    text(c, d["role_matters"], 530, 223, 215, 13, GREEN, True, leading=20, max_lines=3)
    rounded(c, 70, 75, 700, 65, BLUE_LIGHT, BLUE)
    text(c, d["multiple"], 95, 108, 650, 12.5, BLUE, True, leading=20, align="center", max_lines=2)
    c.showPage()


def page_iq(c, d):
    base(c, d, 6, d["page6_tag"], d["page6_title"], d["page6_sub"])
    cards = [
        (d["iq_title"], d["iq_desc"], BLUE_LIGHT, BLUE, "1"),
        (d["profile_title"], d["profile_desc"], TEAL_LIGHT, TEAL, "2"),
        (d["dignity_title"], d["dignity_desc"], CORAL_LIGHT, CORAL, "≠"),
    ]
    for i, (title_value, body, fill, accent, mark) in enumerate(cards):
        x = 45 + i * 265
        node(c, x, 335, 220, 110, title_value, body, fill, accent, mark)
        if i < 2:
            arrow(c, x + 220, 390, x + 265, 390, MUTED, 1.5)
    rounded(c, 55, 225, 730, 75, GREEN_LIGHT, GREEN)
    text(c, d["ai_correct"], 75, 268, 690, 11.5, GREEN, True, leading=19, max_lines=3)
    rounded(c, 55, 135, 730, 65, GOLD_LIGHT, GOLD)
    text(c, d["ai_wrong"], 75, 172, 690, 11, INK, True, leading=18, max_lines=3)
    rounded(c, 55, 55, 730, 55, RED_LIGHT, RED)
    text(c, d["human_rule"], 75, 87, 690, 10.5, RED, True, leading=17, align="center", max_lines=2)
    c.showPage()


def page_functionalism_arch(c, d):
    base(c, d, 7, d["page7_tag"], d["page7_title"], d["page7_sub"])
    colors = [(TEAL_LIGHT, TEAL), (BLUE_LIGHT, BLUE), (CORAL_LIGHT, CORAL), (GOLD_LIGHT, GOLD), (GREEN_LIGHT, GREEN)]
    xs = [40, 200, 360, 520, 680]
    for i, ((title_value, body), (fill, accent), x) in enumerate(zip(d["role_map"], colors, xs), 1):
        node(c, x, 310, 120, 95, title_value, body, fill, accent, i)
        if i < 5:
            arrow(c, x + 120, 357, xs[i], 357, accent, 1.6)
    rounded(c, 55, 165, 730, 100, GREEN_LIGHT, GREEN)
    pill(c, "Engineering inference", 75, 227, GREEN, PAPER)
    text(c, d["why_modular"], 75, 197, 690, 13, INK, True, leading=21, max_lines=3)
    rounded(c, 55, 65, 730, 70, RED_LIGHT, RED)
    pill(c, "Limit", 75, 103, RED, PAPER)
    text(c, d["philosophy_limit"], 155, 109, 610, 10.5, RED, True, leading=17, max_lines=3)
    c.showPage()


def page_other(c, d):
    base(c, d, 8, d["page8_tag"], d["page8_title"])
    rounded(c, 55, 260, 345, 180, BLUE_LIGHT, BLUE)
    pill(c, d["symbol_title"], 75, 397, BLUE, PAPER)
    text(c, d["symbol_desc"], 75, 355, 305, 12, INK, True, leading=21, max_lines=6)
    rounded(c, 440, 260, 345, 180, CORAL_LIGHT, CORAL)
    pill(c, d["subject_title"], 460, 397, CORAL, PAPER)
    text(c, d["subject_desc"], 460, 355, 305, 12, INK, True, leading=21, max_lines=6)
    # Interaction graphic
    for x, label, accent in [(235, d["symbol_title"], BLUE), (605, d["subject_title"], CORAL)]:
        c.setFillColor(PAPER)
        c.setStrokeColor(accent)
        c.circle(x, 165, 45, fill=1, stroke=1)
        text(c, label, x - 40, 170, 80, 9, accent, True, align="center", max_lines=2)
    arrow(c, 280, 165, 560, 165, TEAL, 2)
    arrow(c, 560, 145, 280, 145, GOLD, 2)
    rounded(c, 105, 65, 630, 55, TEAL_LIGHT, TEAL)
    text(c, d["focus_note"], 130, 98, 580, 10.5, TEAL, True, align="center", max_lines=2)
    c.showPage()


def page_sources(c, d):
    base(c, d, 9, d["page9_tag"], d["page9_title"])
    rounded(c, 55, 285, 330, 170, TEAL_LIGHT, TEAL)
    y = 416
    for i, point in enumerate(d["final_points"], 1):
        c.setFillColor(TEAL)
        c.circle(80, y + 3, 11, fill=1, stroke=0)
        c.setFillColor(PAPER)
        c.setFont(font_name(True), 8)
        c.drawCentredString(80, y, str(i))
        text(c, point, 102, y + 7, 255, 10.5, INK, True, max_lines=2)
        y -= 30
    rounded(c, 420, 170, 365, 285, PAPER, LINE)
    pill(c, d["sources_title"], 440, 417, GOLD_LIGHT, INK)
    y = 378
    for i, (org, title_value, url) in enumerate(SOURCES, 1):
        c.setFillColor([TEAL, BLUE, CORAL, GOLD, GREEN][i - 1])
        c.circle(448, y + 3, 9, fill=1, stroke=0)
        c.setFillColor(PAPER)
        c.setFont(font_name(True), 7)
        c.drawCentredString(448, y, str(i))
        text(c, org, 466, y + 7, 290, 8.8, INK, True, max_lines=1)
        text(c, title_value, 466, y - 8, 290, 8, MUTED, max_lines=1)
        c.linkURL(url, (435, y - 14, 765, y + 16), relative=0)
        y -= 43
    rounded(c, 55, 170, 330, 90, GOLD_LIGHT, GOLD)
    text(c, d["boundary"], 75, 225, 290, 10.5, INK, True, leading=18, max_lines=4)
    rounded(c, 55, 65, 730, 70, GREEN_LIGHT, GREEN)
    text(c, d["final_points"][-1], 80, 105, 680, 15, GREEN, True, align="center", max_lines=2)
    c.showPage()


def build_report(d: dict, filename: str) -> Path:
    global ACTIVE_FONT_PREFIX
    ACTIVE_FONT_PREFIX = "JA" if d["locale"] == "日本語" else "TC"
    path = OUT_DIR / filename
    c = canvas.Canvas(str(path), pagesize=(W, H), pageCompression=1)
    c.setTitle(d["title"])
    c.setAuthor("UruhaBrain Project")
    c.setSubject("RightBrain architecture and functionalism")
    cover(c, d)
    page_core(c, d)
    page_overload(c, d)
    page_case(c, d)
    page_evidence(c, d)
    page_functionalism_basic(c, d)
    page_iq(c, d)
    page_functionalism_arch(c, d)
    page_other(c, d)
    page_sources(c, d)
    c.save()
    return path


def build_all() -> None:
    register_fonts()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zh = build_report(ZH, "rightbrain_architecture_philosophy_zh_2026-07-08.pdf")
    ja = build_report(JA, "rightbrain_architecture_philosophy_ja_2026-07-08.pdf")
    print(zh)
    print(ja)


if __name__ == "__main__":
    build_all()
