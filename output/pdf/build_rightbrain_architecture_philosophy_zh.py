#!/usr/bin/env python3
"""Build the visual Chinese report on RightBrain scope and philosophical framing."""

from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib.colors import HexColor, Color
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "pdf" / "rightbrain_architecture_philosophy_zh_2026-07-08.pdf"
FONT_PATH = Path("/System/Library/Fonts/Supplemental/Songti.ttc")

W, H = landscape(A4)

BG = HexColor("#F5F1E8")
PAPER = HexColor("#FFFDF8")
INK = HexColor("#12252B")
MUTED = HexColor("#607176")
TEAL = HexColor("#0B6B69")
TEAL_LIGHT = HexColor("#D9EEEA")
CORAL = HexColor("#E66B4C")
CORAL_LIGHT = HexColor("#F9DFD6")
GOLD = HexColor("#D9A428")
GOLD_LIGHT = HexColor("#F6EAC5")
BLUE = HexColor("#316B9A")
BLUE_LIGHT = HexColor("#DCEAF5")
RED = HexColor("#A43B35")
RED_LIGHT = HexColor("#F2D9D5")
GREEN = HexColor("#388259")
GREEN_LIGHT = HexColor("#DDEEDF")
LINE = HexColor("#CBD3CE")


def register_fonts() -> None:
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"Missing CJK font: {FONT_PATH}")
    # Songti ships as TrueType outlines and embeds reliably in ReportLab PDFs.
    pdfmetrics.registerFont(TTFont("NotoTC", str(FONT_PATH), subfontIndex=7))
    pdfmetrics.registerFont(TTFont("NotoTC-Medium", str(FONT_PATH), subfontIndex=7))
    pdfmetrics.registerFont(TTFont("NotoTC-Bold", str(FONT_PATH), subfontIndex=2))


def set_font(c: canvas.Canvas, size: float, bold: bool = False, medium: bool = False) -> None:
    name = "NotoTC-Bold" if bold else ("NotoTC-Medium" if medium else "NotoTC")
    c.setFont(name, size)


def fit_lines(text: str, font: str, size: float, width: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if paragraph == "":
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            trial = current + ch
            if current and pdfmetrics.stringWidth(trial, font, size) > width:
                lines.append(current.rstrip())
                current = ch.lstrip()
            else:
                current = trial
        if current:
            lines.append(current.rstrip())
    return lines


def text_block(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    size: float = 12,
    leading: float | None = None,
    color=INK,
    bold: bool = False,
    medium: bool = False,
    max_lines: int | None = None,
    align: str = "left",
) -> float:
    font = "NotoTC-Bold" if bold else ("NotoTC-Medium" if medium else "NotoTC")
    leading = leading or size * 1.45
    lines = fit_lines(text, font, size, width)
    if max_lines is not None:
        lines = lines[:max_lines]
    c.setFillColor(color)
    c.setFont(font, size)
    yy = y
    for line in lines:
        if align == "center":
            c.drawCentredString(x + width / 2, yy, line)
        elif align == "right":
            c.drawRightString(x + width, yy, line)
        else:
            c.drawString(x, yy, line)
        yy -= leading
    return yy


def rounded(c: canvas.Canvas, x: float, y: float, w: float, h: float, fill, stroke=LINE, radius=14, sw=1) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(sw)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def pill(c: canvas.Canvas, text: str, x: float, y: float, fill, color=INK, width: float | None = None) -> float:
    set_font(c, 9.5, bold=True)
    w = width or pdfmetrics.stringWidth(text, "NotoTC-Bold", 9.5) + 22
    c.setFillColor(fill)
    c.roundRect(x, y, w, 23, 11.5, fill=1, stroke=0)
    c.setFillColor(color)
    c.drawCentredString(x + w / 2, y + 7, text)
    return w


def arrow(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float, color=TEAL, sw=2.2) -> None:
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(sw)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 9
    for delta in (2.55, -2.55):
        c.line(x2, y2, x2 + head * math.cos(angle + delta), y2 + head * math.sin(angle + delta))


def node(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str, subtitle: str, fill, accent, icon: str = "") -> None:
    rounded(c, x, y, w, h, fill, stroke=accent, radius=13, sw=1.2)
    if icon:
        c.setFillColor(accent)
        c.circle(x + 24, y + h - 25, 15, fill=1, stroke=0)
        c.setFillColor(PAPER)
        set_font(c, 12, bold=True)
        c.drawCentredString(x + 24, y + h - 29, icon)
        tx = x + 48
        tw = w - 60
    else:
        tx = x + 14
        tw = w - 28
    text_block(c, title, tx, y + h - 23, tw, 12, color=INK, bold=True, max_lines=1)
    text_block(c, subtitle, x + 14, y + h - 48, w - 28, 9.5, leading=13.5, color=MUTED, max_lines=3)


def page_base(c: canvas.Canvas, n: int, section: str, title: str, subtitle: str = "") -> None:
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    pill(c, section, 35, H - 46, TEAL_LIGHT, TEAL)
    text_block(c, title, 35, H - 88, W - 70, 27, leading=34, color=INK, bold=True, max_lines=2)
    if subtitle:
        text_block(c, subtitle, 37, H - 122, W - 74, 11, leading=16, color=MUTED, max_lines=2)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.line(35, 27, W - 35, 27)
    c.setFillColor(MUTED)
    set_font(c, 8.5)
    c.drawString(35, 13, "UruhaBrain 架構說明與哲學基礎 | 2026-07-08")
    c.drawRightString(W - 35, 13, f"{n}")


def source_note(c: canvas.Canvas, label: str, url: str, x: float, y: float, width: float) -> None:
    c.setFillColor(BLUE_LIGHT)
    c.roundRect(x, y, width, 25, 8, fill=1, stroke=0)
    c.setFillColor(BLUE)
    set_font(c, 8.5, medium=True)
    shown = label if len(label) < 58 else label[:56] + "..."
    c.drawString(x + 10, y + 8, shown)
    c.linkURL(url, (x, y, x + width, y + 25), relative=0)


def quote_card(c: canvas.Canvas, quote: str, attribution: str, x: float, y: float, w: float, h: float, fill=TEAL_LIGHT) -> None:
    rounded(c, x, y, w, h, fill, stroke=fill, radius=16)
    c.setFillColor(TEAL)
    c.rect(x, y, 6, h, fill=1, stroke=0)
    text_block(c, quote, x + 24, y + h - 31, w - 48, 14, leading=22, color=INK, medium=True)
    text_block(c, attribution, x + 24, y + 21, w - 48, 9, color=MUTED, align="right")


def draw_cover(c: canvas.Canvas) -> None:
    c.setFillColor(INK)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.circle(W - 80, H - 60, 190, fill=1, stroke=0)
    c.setFillColor(CORAL)
    c.circle(W - 160, 20, 120, fill=1, stroke=0)
    pill(c, "UruhaBrain 研究說明", 48, H - 72, GOLD_LIGHT, INK)
    text_block(c, "為什麼不把所有東西\n都塞進右腦？", 48, H - 150, 550, 34, leading=48, color=PAPER, bold=True)
    text_block(c, "架構分工、實測證據，以及功能主義、IQ、符號互動論與社會主體性的關係", 51, H - 263, 570, 15, leading=23, color=HexColor("#D5E0DD"), max_lines=3)

    # Central visual: audited flow into a speech bubble.
    cx, cy = 640, 270
    c.setFillColor(PAPER)
    c.circle(cx, cy, 105, fill=1, stroke=0)
    c.setStrokeColor(TEAL)
    c.setLineWidth(5)
    c.arc(cx - 62, cy - 48, cx + 24, cy + 58, 60, 240)
    c.arc(cx - 15, cy - 48, cx + 66, cy + 58, -120, 240)
    c.line(cx - 12, cy + 48, cx - 12, cy - 52)
    c.setFillColor(CORAL)
    c.roundRect(cx + 22, cy - 15, 84, 54, 18, fill=1, stroke=0)
    c.setFillColor(PAPER)
    c.wedge(cx + 16, cy - 27, cx + 48, cy + 7, 205, 42, fill=1, stroke=0)
    set_font(c, 13, bold=True)
    c.drawCentredString(cx + 64, cy + 6, "自然表達")
    text_block(c, "不是更大的提示詞\n而是可追蹤的認知分工", 50, 105, 355, 19, leading=29, color=GOLD_LIGHT, bold=True)
    text_block(c, "中文視覺版 | 研究與工程邊界明確標示", 50, 47, 430, 10.5, color=HexColor("#AFC0BC"))
    c.showPage()


def draw_executive(c: canvas.Canvas) -> None:
    page_base(c, 1, "一句話答案", "右腦可以看記憶，但不能獨自決定一切", "正確做法不是封鎖右腦，而是控制它看到什麼、能改什麼、最後如何被檢查。")
    y = 330
    node(c, 45, y, 165, 96, "經審核的記憶", "只送入相關、最新、允許說出的線索。", TEAL_LIGHT, TEAL, "1")
    node(c, 257, y, 165, 96, "左腦回答策略", "決定事實、推理、風險與必須表達的意思。", BLUE_LIGHT, BLUE, "2")
    node(c, 469, y, 165, 96, "右腦自然表達", "把既定意思轉成自然、有人格的語言。", CORAL_LIGHT, CORAL, "3")
    node(c, 681, y, 115, 96, "檢查", "攔截漏意、污染與不當記憶。", GOLD_LIGHT, GOLD, "4")
    arrow(c, 210, y + 48, 257, y + 48)
    arrow(c, 422, y + 48, 469, y + 48)
    arrow(c, 634, y + 48, 681, y + 48)

    rounded(c, 45, 113, 355, 155, GREEN_LIGHT, stroke=GREEN)
    pill(c, "保留分工", 65, 230, GREEN, PAPER)
    text_block(c, "每一層只負責一種可驗證的工作", 65, 204, 315, 15, bold=True)
    text_block(c, "• 記憶層決定相關性、時間與可說性\n• 左腦決定回答策略與必要語意\n• 右腦只負責表面實現與人格口吻\n• 檢查層保留最後拒絕權", 65, 176, 310, 11, leading=21, color=MUTED)

    rounded(c, 440, 113, 356, 155, RED_LIGHT, stroke=RED)
    pill(c, "全部塞入右腦", 460, 230, RED, PAPER)
    text_block(c, "右腦會變成第二個完整大腦", 460, 204, 315, 15, bold=True)
    text_block(c, "• 左腦只剩形式，實際決策被架空\n• 記憶、推理、人格、語言錯誤互相纏結\n• 失敗時無法判斷是哪一層出錯\n• 小模型必須同時承擔過多工作", 460, 176, 310, 11, leading=21, color=MUTED)
    c.showPage()


def draw_architecture_compare(c: canvas.Canvas) -> None:
    page_base(c, 2, "架構比較", "同樣都有輸入，差別在誰負責選擇與承擔責任", "老師提出的方式可以生成回答，但會把記憶選擇、推理與表達重新混合在同一個模型裡。")

    rounded(c, 38, 75, 367, 390, PAPER, stroke=GREEN, radius=20, sw=1.5)
    rounded(c, 436, 75, 367, 390, PAPER, stroke=RED, radius=20, sw=1.5)
    pill(c, "目前架構：分工", 60, 430, GREEN, PAPER)
    pill(c, "全部塞進右腦：混合", 458, 430, RED, PAPER)

    left_nodes = [
        ("使用者輸入", "問題與當下狀態", BLUE_LIGHT, BLUE),
        ("記憶審核", "相關性＋時間更新＋可說性", TEAL_LIGHT, TEAL),
        ("左腦策略", "意圖、推理、風險、必要語意", GOLD_LIGHT, GOLD),
        ("右腦表達", "人格口吻＋自然語言", CORAL_LIGHT, CORAL),
        ("輸出檢查", "語意保留＋污染攔截", GREEN_LIGHT, GREEN),
    ]
    yy = 352
    for i, (t, s, f, a) in enumerate(left_nodes):
        node(c, 75, yy, 292, 55, t, s, f, a, str(i + 1))
        if i < len(left_nodes) - 1:
            arrow(c, 221, yy, 221, yy - 20, color=a)
        yy -= 70

    node(c, 468, 340, 300, 60, "使用者輸入＋全部記憶", "舊偏好、新狀態、私人資訊、人格設定一起送入", BLUE_LIGHT, BLUE, "1")
    arrow(c, 618, 340, 618, 308, color=RED)
    rounded(c, 475, 141, 286, 167, CORAL_LIGHT, stroke=RED, radius=60, sw=2)
    c.setFillColor(RED)
    set_font(c, 18, bold=True)
    c.drawCentredString(618, 265, "右腦一次做 8 件事")
    tasks = ["選記憶", "解衝突", "判可說", "推理", "安全", "人格", "措辭", "自檢"]
    for i, task in enumerate(tasks):
        ang = math.radians(i * 45 + 10)
        tx = 618 + 93 * math.cos(ang)
        ty = 215 + 54 * math.sin(ang)
        c.setFillColor(PAPER)
        c.circle(tx, ty, 23, fill=1, stroke=0)
        c.setFillColor(RED)
        set_font(c, 8.4, bold=True)
        c.drawCentredString(tx, ty - 3, task)
    arrow(c, 618, 141, 618, 110, color=RED)
    pill(c, "最終回答", 568, 84, RED_LIGHT, RED, width=100)

    text_block(c, "可歸因：知道哪一層出錯", 76, 88, 285, 10.5, color=GREEN, bold=True, align="center")
    text_block(c, "不可歸因：錯誤來源混在一起", 478, 88, 280, 10.5, color=RED, bold=True, align="center")
    c.showPage()


def draw_overload(c: canvas.Canvas) -> None:
    page_base(c, 3, "工程原因", "把所有職責交給右腦，等於要求一個模型同時當八種專家", "參數變大只能提高能力上限，不能自動保證記憶時序、隱私、推理與語意保留都正確。")
    cx, cy = 230, 280
    c.setFillColor(CORAL_LIGHT)
    c.circle(cx, cy, 90, fill=1, stroke=0)
    c.setFillColor(CORAL)
    set_font(c, 20, bold=True)
    c.drawCentredString(cx, cy + 8, "單一右腦")
    set_font(c, 12, medium=True)
    c.drawCentredString(cx, cy - 18, "同時承擔全部責任")
    tasks = [
        ("記憶檢索", TEAL), ("時序更新", BLUE), ("隱私判定", RED), ("社會推理", GOLD),
        ("安全路由", RED), ("人格一致", CORAL), ("自然語言", TEAL), ("自我檢查", GREEN),
    ]
    for i, (task, color) in enumerate(tasks):
        ang = math.radians(90 - i * 45)
        tx = cx + 160 * math.cos(ang)
        ty = cy + 150 * math.sin(ang)
        c.setFillColor(PAPER)
        c.setStrokeColor(color)
        c.setLineWidth(1.2)
        c.circle(tx, ty, 36, fill=1, stroke=1)
        c.setFillColor(color)
        set_font(c, 9.5, bold=True)
        c.drawCentredString(tx, ty - 3, task)
        arrow(c, tx - 25 * math.cos(ang), ty - 25 * math.sin(ang), cx + 84 * math.cos(ang), cy + 84 * math.sin(ang), color=color, sw=1.2)

    rounded(c, 470, 120, 315, 320, PAPER, stroke=LINE, radius=20)
    pill(c, "模型變大 ≠ 問題消失", 492, 400, GOLD_LIGHT, INK)
    reasons = [
        ("上下文競爭", "舊偏好、新狀態、私人資料同時搶注意力。"),
        ("責任混淆", "右腦可以改寫，也可能無意中改掉左腦結論。"),
        ("錯誤不可定位", "最後答錯時，不知道是記憶、推理還是措辭。"),
        ("成本與延遲", "更大模型要重做整個認知流程，而不是只說好。"),
        ("抽樣不保證", "提高 temperature 只增加變化，也可能增加污染。"),
    ]
    yy = 354
    for i, (t, b) in enumerate(reasons, 1):
        c.setFillColor(TEAL if i < 4 else CORAL)
        c.circle(512, yy + 4, 13, fill=1, stroke=0)
        c.setFillColor(PAPER)
        set_font(c, 9, bold=True)
        c.drawCentredString(512, yy + 1, str(i))
        text_block(c, t, 536, yy + 10, 220, 11.5, bold=True)
        text_block(c, b, 536, yy - 8, 220, 9.5, leading=14, color=MUTED, max_lines=2)
        yy -= 52
    c.showPage()


def draw_coffee_case(c: canvas.Canvas) -> None:
    page_base(c, 4, "具體案例", "同樣看到『胃不舒服』，仍可能因資訊權重不同而得到不同答案", "問題不是右腦完全沒看到資訊，而是沒有獨立機制保證它正確處理新舊記憶與回答責任。")
    quote_card(c, "我以前很喜歡咖啡，但最近胃不舒服，今天還適合喝嗎？", "使用者當下輸入", 60, 420, 720, 62, fill=BLUE_LIGHT)

    # Timeline
    c.setStrokeColor(LINE)
    c.setLineWidth(4)
    c.line(105, 347, 735, 347)
    events = [
        (130, "較早", "喜歡咖啡", GOLD),
        (355, "最近", "胃不舒服", CORAL),
        (580, "現在", "詢問建議", BLUE),
        (725, "回答", "需整合時序", TEAL),
    ]
    for x, t, b, col in events:
        c.setFillColor(col)
        c.circle(x, 347, 11, fill=1, stroke=0)
        text_block(c, t, x - 45, 315, 90, 10, color=col, bold=True, align="center")
        text_block(c, b, x - 65, 292, 130, 11, color=INK, medium=True, align="center")

    rounded(c, 55, 88, 345, 155, GREEN_LIGHT, stroke=GREEN)
    pill(c, "分工架構", 75, 205, GREEN, PAPER)
    text_block(c, "記憶層先決定：最近狀態優先", 75, 177, 300, 13, bold=True)
    text_block(c, "左腦形成策略：承認偏好，但以胃部狀態為限制。\n右腦只改寫語氣，不得刪掉『胃不舒服』。", 75, 151, 295, 10.5, leading=18, color=MUTED)
    text_block(c, "『想喝可以理解，但最近胃不舒服，今天先選低刺激或少量比較穩。』", 75, 103, 295, 10.5, color=GREEN, medium=True, max_lines=3)

    rounded(c, 440, 88, 345, 155, RED_LIGHT, stroke=RED)
    pill(c, "全部交給右腦", 460, 205, RED, PAPER)
    text_block(c, "所有訊息存在，但權重沒有保證", 460, 177, 300, 13, bold=True)
    text_block(c, "右腦可能重視『喜歡咖啡』，或只給通用建議。\n它也可能在改寫時把限制條件縮短掉。", 460, 151, 295, 10.5, leading=18, color=MUTED)
    text_block(c, "『既然喜歡，少喝一點應該沒問題吧。』", 460, 111, 295, 10.5, color=RED, medium=True, max_lines=2)
    c.showPage()


def draw_privacy(c: canvas.Canvas) -> None:
    page_base(c, 5, "記憶與隱私", "右腦不該直接接觸全部原始記憶", "最安全的設計是先判斷『相關嗎、最新嗎、可以說嗎』，再把最小必要線索送入表達層。")
    memories = [
        ("偏好", "喜歡咖啡", GREEN_LIGHT, GREEN),
        ("更新", "最近胃不舒服", BLUE_LIGHT, BLUE),
        ("敏感", "家庭壓力細節", RED_LIGHT, RED),
        ("無關", "三週前的遊戲話題", GOLD_LIGHT, GOLD),
    ]
    yy = 395
    for t, b, f, a in memories:
        node(c, 55, yy, 205, 57, t, b, f, a)
        yy -= 72

    # Funnel
    c.setFillColor(TEAL_LIGHT)
    p = c.beginPath()
    p.moveTo(305, 450)
    p.lineTo(505, 450)
    p.lineTo(465, 205)
    p.lineTo(345, 205)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    filters = ["相關性", "時間更新", "可說性"]
    fy = 385
    for i, f in enumerate(filters, 1):
        c.setStrokeColor(TEAL)
        c.setLineWidth(2)
        c.line(342, fy, 468, fy)
        c.setFillColor(TEAL)
        set_font(c, 12, bold=True)
        c.drawCentredString(405, fy + 12, f"{i}. {f}")
        fy -= 72
    arrow(c, 260, 300, 320, 300, color=TEAL)
    arrow(c, 405, 205, 405, 163, color=TEAL)

    node(c, 305, 85, 200, 72, "最小必要線索", "『最近胃不舒服，避免刺激性建議』", GREEN_LIGHT, GREEN, "✓")
    arrow(c, 505, 121, 565, 121, color=GREEN)
    node(c, 565, 85, 220, 72, "右腦取得", "能完成表達，但看不到不該洩漏的家庭細節。", CORAL_LIGHT, CORAL, "F")

    rounded(c, 565, 250, 220, 200, PAPER, stroke=RED, radius=18)
    pill(c, "若全部送入", 585, 412, RED_LIGHT, RED)
    text_block(c, "風險不是只有『記憶管理不好』", 585, 380, 180, 12.5, bold=True)
    text_block(c, "即使提示詞寫著不要說，模型仍實際看見敏感內容。只要提示衝突、注意力偏移或生成失誤，就存在洩漏路徑。", 585, 348, 180, 10, leading=17, color=MUTED)
    text_block(c, "原則：不需要知道，就不要送入。", 585, 275, 180, 11, color=RED, bold=True, align="center")
    c.showPage()


def draw_evidence(c: canvas.Canvas) -> None:
    page_base(c, 6, "本專案證據", "真實 7B 右腦目前不能獨自承擔所有最終決策", "以下是 Qwen2.5-7B-Instruct + v10 adapter、11 個固定案例、每題最多 3 個候選的實機結果。")

    # Donut
    cx, cy, r = 180, 308, 92
    c.setFillColor(CORAL_LIGHT)
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.wedge(cx - r, cy - r, cx + r, cy + r, 90, 72, fill=1, stroke=0)
    c.setFillColor(PAPER)
    c.circle(cx, cy, 58, fill=1, stroke=0)
    c.setFillColor(INK)
    set_font(c, 28, bold=True)
    c.drawCentredString(cx, cy + 2, "20%")
    set_font(c, 10, medium=True)
    c.drawCentredString(cx, cy - 22, "原始候選合格")
    text_block(c, "6 個合格", 83, 177, 95, 11, color=GREEN, bold=True, align="center")
    text_block(c, "24 個拒絕", 183, 177, 105, 11, color=RED, bold=True, align="center")

    metrics = [
        ("30", "真實生成候選", BLUE_LIGHT, BLUE),
        ("24", "被品質閘門拒絕", RED_LIGHT, RED),
        ("0", "已知壞候選被選中", GREEN_LIGHT, GREEN),
        ("100%", "使用者輸出未被影子模式改動", TEAL_LIGHT, TEAL),
    ]
    xx, yy = 330, 360
    for i, (num, label, fill, col) in enumerate(metrics):
        x = xx + (i % 2) * 225
        y = yy - (i // 2) * 130
        rounded(c, x, y, 200, 100, fill, stroke=col, radius=18)
        text_block(c, num, x + 15, y + 59, 170, 26, color=col, bold=True, align="center")
        text_block(c, label, x + 20, y + 28, 160, 9.5, color=INK, medium=True, align="center", max_lines=2)

    rounded(c, 55, 70, 730, 82, PAPER, stroke=LINE, radius=14)
    pill(c, "真實污染案例", 75, 112, GOLD_LIGHT, INK)
    text_block(c, "候選曾生成簡體字『无』與 Unicode 破損字元『�』，兩者修正後皆為 1 次生成、0 次通過。", 75, 86, 420, 10.5, color=MUTED, max_lines=2)
    text_block(c, "結論不是右腦無用，而是它目前適合做『受約束的表達器』，不適合做無限制的完整代理。", 510, 115, 250, 11.5, leading=18, color=TEAL, bold=True, max_lines=3, align="center")
    c.showPage()


def draw_functionalism(c: canvas.Canvas) -> None:
    page_base(c, 7, "哲學功能主義", "像不像心智，關鍵在功能角色與因果關係", "功能主義不只看材料或單次分數。此處是心靈哲學的 functionalism，不是社會學的結構功能論。")
    quote_card(c, "一個狀態之所以是某種心理狀態，取決於它在整個認知系統中的功能與因果角色。", "依 Stanford Encyclopedia of Philosophy 的功能主義條目整理", 55, 375, 730, 74)

    # Functional role graph
    node(c, 70, 250, 145, 74, "輸入", "身體、環境、語言刺激", BLUE_LIGHT, BLUE, "I")
    node(c, 270, 250, 145, 74, "內部狀態", "信念、欲望、情緒、記憶", GOLD_LIGHT, GOLD, "M")
    node(c, 470, 250, 145, 74, "其他心智狀態", "相互影響與更新", TEAL_LIGHT, TEAL, "R")
    node(c, 670, 250, 115, 74, "行為", "回答與行動", CORAL_LIGHT, CORAL, "O")
    arrow(c, 215, 287, 270, 287, color=BLUE)
    arrow(c, 415, 287, 470, 287, color=GOLD)
    arrow(c, 615, 287, 670, 287, color=TEAL)
    arrow(c, 542, 250, 342, 210, color=TEAL, sw=1.4)
    arrow(c, 342, 210, 342, 250, color=TEAL, sw=1.4)

    rounded(c, 55, 80, 350, 115, GREEN_LIGHT, stroke=GREEN)
    text_block(c, "對本專案的工程啟示", 75, 162, 310, 13, bold=True, color=GREEN)
    text_block(c, "記憶、推理、表達與更新應保有可觀察的因果角色。若全部壓進同一個右腦生成器，就很難證明每個角色是否真的存在。", 75, 133, 305, 10.5, leading=18, color=MUTED)

    rounded(c, 435, 80, 350, 115, RED_LIGHT, stroke=RED)
    text_block(c, "不能過度推論", 455, 162, 310, 13, bold=True, color=RED)
    text_block(c, "功能主義沒有直接證明：模組越多就越有人性，也沒有證明通過功能測試就一定有主觀感受或意識。這仍是哲學爭議。", 455, 133, 305, 10.5, leading=18, color=MUTED)
    source_note(c, "Stanford Encyclopedia of Philosophy: Functionalism", "https://plato.stanford.edu/entries/functionalism/", 55, 48, 350)
    source_note(c, "Ned Block: Troubles with Functionalism", "https://www.nedblock.us/papers/1981.Troubles.pdf", 435, 48, 350)
    c.showPage()


def draw_iq(c: canvas.Canvas) -> None:
    page_base(c, 8, "IQ 與像不像人", "IQ 是能力尺之一，不是『人類性』的總分", "APA 報告把 intelligence 視為複合能力；個體表現也會隨領域、時機與判準改變。")

    rounded(c, 55, 320, 330, 145, BLUE_LIGHT, stroke=BLUE)
    pill(c, "IQ／認知能力", 75, 426, BLUE, PAPER)
    text_block(c, "主要回答：會不會理解複雜概念、推理、學習、解題與適應。", 75, 392, 290, 12.5, leading=20, bold=True)
    text_block(c, "可用標準化測驗比較某些能力，但不是人格、關係歷史、價值承諾或主觀經驗的完整測量。", 75, 343, 290, 10.5, leading=17, color=MUTED)

    rounded(c, 455, 320, 330, 145, CORAL_LIGHT, stroke=CORAL)
    pill(c, "像不像人", 475, 426, CORAL, PAPER)
    text_block(c, "還包含：記憶連續性、社會理解、角色關係、情緒調節、人格與反思。", 475, 392, 290, 12.5, leading=20, bold=True)
    text_block(c, "它是多維度概念，不能由單一考試或單次對話壓縮成一個官方百分比。", 475, 343, 290, 10.5, leading=17, color=MUTED)

    # Two-axis matrix
    x0, y0, mw, mh = 205, 88, 430, 185
    c.setStrokeColor(INK)
    c.setLineWidth(1.5)
    c.line(x0, y0, x0, y0 + mh)
    c.line(x0, y0, x0 + mw, y0)
    c.setStrokeColor(LINE)
    c.line(x0 + mw / 2, y0, x0 + mw / 2, y0 + mh)
    c.line(x0, y0 + mh / 2, x0 + mw, y0 + mh / 2)
    text_block(c, "高社會／人格連續性", 55, y0 + mh - 4, 140, 9, color=MUTED, align="right")
    text_block(c, "低社會／人格連續性", 55, y0 + 8, 140, 9, color=MUTED, align="right")
    text_block(c, "較低解題能力", x0, y0 - 22, 120, 9, color=MUTED)
    text_block(c, "較高解題能力", x0 + mw - 120, y0 - 22, 120, 9, color=MUTED, align="right")
    labels = [
        (310, 224, "不擅考試但很有人味", TEAL_LIGHT, TEAL),
        (525, 224, "高分且能維持社會自我", GREEN_LIGHT, GREEN),
        (310, 132, "兩者都弱", GOLD_LIGHT, GOLD),
        (525, 132, "高分但不懂關係", RED_LIGHT, RED),
    ]
    for x, y, txt, fill, col in labels:
        pill(c, txt, x - 75, y - 10, fill, col, width=150)

    source_note(c, "APA Task Force: Intelligence: Knowns and Unknowns", "https://doi.org/10.1037/0003-066X.51.2.77", 55, 48, 350)
    source_note(c, "Turing (1950): Computing Machinery and Intelligence", "https://doi.org/10.1093/mind/LIX.236.433", 435, 48, 350)
    c.showPage()


def draw_symbolic_interaction(c: canvas.Canvas) -> None:
    page_base(c, 9, "符號互動論", "人的意義不是固定塞在腦中，而是在互動中形成並被重新解釋", "Blumer 將核心整理為三點；Mead 進一步說明自我是如何從社會過程中形成。")
    steps = [
        ("1", "依意義行動", "人不是只對刺激反射，而是依『這件事對我代表什麼』行動。", BLUE_LIGHT, BLUE),
        ("2", "意義來自互動", "朋友、關係、承諾與冒犯的意義，由共同經驗產生。", TEAL_LIGHT, TEAL),
        ("3", "解釋會修改意義", "新的回應與經驗會改變原本的理解。", CORAL_LIGHT, CORAL),
    ]
    x = 55
    for i, (num, title, body, fill, col) in enumerate(steps):
        rounded(c, x, 325, 220, 130, fill, stroke=col, radius=20)
        c.setFillColor(col)
        c.circle(x + 31, 420, 17, fill=1, stroke=0)
        c.setFillColor(PAPER)
        set_font(c, 12, bold=True)
        c.drawCentredString(x + 31, 416, num)
        text_block(c, title, x + 58, 424, 145, 14, bold=True, color=col)
        text_block(c, body, x + 20, 380, 180, 10.5, leading=18, color=INK, max_lines=4)
        if i < 2:
            arrow(c, x + 220, 390, x + 250, 390, color=col)
        x += 255

    # Interaction loop
    cx, cy = 420, 190
    actors = [
        (cx - 160, cy, "我", BLUE),
        (cx + 160, cy, "他人", CORAL),
        (cx, cy - 90, "共享符號與關係", TEAL),
    ]
    for ax, ay, txt, col in actors:
        c.setFillColor(PAPER)
        c.setStrokeColor(col)
        c.setLineWidth(2)
        c.circle(ax, ay, 45, fill=1, stroke=1)
        c.setFillColor(col)
        set_font(c, 11.5, bold=True)
        c.drawCentredString(ax, ay - 4, txt)
    arrow(c, cx - 112, cy + 12, cx + 112, cy + 12, color=BLUE)
    arrow(c, cx + 112, cy - 12, cx - 112, cy - 12, color=CORAL)
    arrow(c, cx - 25, cy - 37, cx - 6, cy - 48, color=TEAL)
    arrow(c, cx + 6, cy - 48, cx + 25, cy - 37, color=TEAL)
    text_block(c, "互動不是只更新句子，而是更新『這個人、這段關係、這件事』對系統的意義。", 640, 218, 145, 10.5, leading=17, color=INK, bold=True, max_lines=5)
    text_block(c, "因此人格不能只是一段固定 persona prompt；它需要由共同經歷、角色期待與反思持續形成。", 640, 130, 145, 9.2, leading=15, color=MUTED, max_lines=5)
    source_note(c, "Blumer: Symbolic Interactionism: Perspective and Method", "https://books.google.com/books/about/Symbolic_Interactionism.html?id=HVuognZFofoC", 55, 48, 350)
    source_note(c, "IEP: George Herbert Mead", "https://iep.utm.edu/mead/", 435, 48, 350)
    c.showPage()


def draw_subjectivity(c: canvas.Canvas) -> None:
    page_base(c, 10, "社會主體性", "主體在關係、角色與他人回應中形成", "主體不是孤立資料庫，而是持續立場。本文將『社會主體性』作為研究操作概念，不把系統宣稱為法律主體或有意識生命。")
    layers = [
        ("共享語言與符號", "理解稱呼、承諾、拒絕、玩笑與角色規範", 620, BLUE_LIGHT, BLUE),
        ("他人的態度", "能採取他人視角，知道對方如何看待自己", 520, TEAL_LIGHT, TEAL),
        ("關係與歷史", "共同經歷改變信任、期待與可說內容", 420, GOLD_LIGHT, GOLD),
        ("反思性的自我", "把自己的過去行動當成對象，修正下一次選擇", 320, CORAL_LIGHT, CORAL),
    ]
    cx, base_y = 355, 120
    for i, (title, body, width, fill, col) in enumerate(layers):
        y = base_y + i * 76
        x = cx - width / 2
        rounded(c, x, y, width, 62, fill, stroke=col, radius=18)
        text_block(c, title, x + 18, y + 36, 190, 12, color=col, bold=True)
        text_block(c, body, x + 220, y + 36, width - 238, 9.5, leading=14, color=INK, max_lines=2)

    rounded(c, 690, 135, 120, 300, PAPER, stroke=LINE, radius=20)
    pill(c, "Mead", 715, 396, TEAL_LIGHT, TEAL, width=70)
    text_block(c, "Me", 715, 355, 70, 22, color=BLUE, bold=True, align="center")
    text_block(c, "內化的他人態度與社會規範", 705, 325, 90, 9.5, leading=14, color=MUTED, align="center")
    arrow(c, 750, 285, 750, 245, color=TEAL)
    text_block(c, "I", 715, 224, 70, 22, color=CORAL, bold=True, align="center")
    text_block(c, "對規範與情境做出的新回應", 705, 194, 90, 9.5, leading=14, color=MUTED, align="center")
    text_block(c, "自我是一個持續過程", 700, 152, 100, 9.5, color=TEAL, bold=True, align="center")

    source_note(c, "University of Chicago Press: Mind, Self, and Society", "https://press.uchicago.edu/ucp/books/book/chicago/M/bo20099389.html", 55, 48, 350)
    source_note(c, "Stanford Encyclopedia: Social Ontology", "https://plato.stanford.edu/entries/social-ontology/", 435, 48, 350)
    c.showPage()


def draw_theory_to_system(c: canvas.Canvas) -> None:
    page_base(c, 11, "理論如何落到系統", "三種理論不是裝飾，而是對應不同的設計問題", "功能主義處理『角色是否存在』；符號互動論處理『意義如何形成』；社會主體性處理『自我如何延續』。")
    columns = [
        (55, "功能主義", "因果角色", TEAL, TEAL_LIGHT, ["記憶選擇", "左腦規劃", "右腦表達", "更新循環"], "測每個部件拔掉後的差異"),
        (305, "符號互動論", "互動產生意義", BLUE, BLUE_LIGHT, ["共享符號", "關係語境", "對方回應", "意義修正"], "測跨輪互動後行為是否合理改變"),
        (555, "社會主體性", "持續立場", CORAL, CORAL_LIGHT, ["角色記憶", "信任／界線", "I／Me 反思", "經驗整合"], "測人格與關係是否連續而非僵化"),
    ]
    for x, title, sub, col, fill, items, test in columns:
        rounded(c, x, 115, 220, 350, PAPER, stroke=col, radius=20, sw=1.5)
        c.setFillColor(fill)
        c.roundRect(x, 370, 220, 95, 20, fill=1, stroke=0)
        text_block(c, title, x + 18, 430, 184, 17, color=col, bold=True, align="center")
        text_block(c, sub, x + 18, 397, 184, 10.5, color=MUTED, medium=True, align="center")
        yy = 337
        for i, item in enumerate(items, 1):
            c.setFillColor(col)
            c.circle(x + 32, yy + 4, 11, fill=1, stroke=0)
            c.setFillColor(PAPER)
            set_font(c, 8.5, bold=True)
            c.drawCentredString(x + 32, yy + 1, str(i))
            text_block(c, item, x + 52, yy + 9, 145, 11, medium=True)
            yy -= 45
        c.setStrokeColor(LINE)
        c.line(x + 20, 158, x + 200, 158)
        text_block(c, "研究驗證", x + 20, 143, 180, 9, color=col, bold=True, align="center")
        text_block(c, test, x + 24, 124, 172, 9.2, leading=14, color=MUTED, align="center", max_lines=2)
    c.showPage()


def draw_design_principles(c: canvas.Canvas) -> None:
    page_base(c, 12, "最終設計原則", "不是把右腦做小，而是讓它在正確位置變強", "更像人的方向，是讓能力、記憶、關係與表達形成閉環，同時保留每一步的責任。")
    principles = [
        ("1", "右腦看得到必要記憶", "但只看經過相關性、時序與可說性審核的線索。", TEAL, TEAL_LIGHT),
        ("2", "左腦保有決策責任", "右腦不能無聲地改掉事實、風險判斷與必要語意。", BLUE, BLUE_LIGHT),
        ("3", "人格來自歷史與互動", "不只是一段固定提示詞，也不是每次講一樣的句子。", CORAL, CORAL_LIGHT),
        ("4", "IQ 與人類性分開評估", "能力測驗證明某項認知功能；盲評與長期互動檢驗社會表現。", GOLD, GOLD_LIGHT),
        ("5", "哲學提供方向，不代替實驗", "不能因為符合功能主義就直接宣稱有意識或真正主體性。", GREEN, GREEN_LIGHT),
        ("6", "每個部件都可被單獨拔除", "只有 matched ablation 才能說明哪個部件造成改善。", RED, RED_LIGHT),
    ]
    for i, (num, title, body, col, fill) in enumerate(principles):
        x = 55 + (i % 2) * 380
        y = 387 - (i // 2) * 118
        rounded(c, x, y, 350, 96, fill, stroke=col, radius=17)
        c.setFillColor(col)
        c.circle(x + 35, y + 50, 20, fill=1, stroke=0)
        c.setFillColor(PAPER)
        set_font(c, 12.5, bold=True)
        c.drawCentredString(x + 35, y + 46, num)
        text_block(c, title, x + 68, y + 64, 260, 13, color=col, bold=True)
        text_block(c, body, x + 68, y + 38, 260, 9.8, leading=15, color=INK, max_lines=3)
    quote_card(c, "右腦可以知道左腦允許它知道的記憶；但不應自行決定哪些記憶是真的、相關、可說，以及最後要採取什麼策略。", "UruhaBrain 架構原則", 85, 50, 670, 68, fill=TEAL_LIGHT)
    c.showPage()


def draw_references(c: canvas.Canvas) -> None:
    page_base(c, 13, "正式來源與研究邊界", "來源可點擊；理論原文、學術百科與本專案實測分開標示", "『官方』在哲學與社會學中不是單一認證機關，因此採用原典、學術百科、學會期刊與大學出版社。")
    refs = [
        ("1", "Stanford Encyclopedia of Philosophy", "Functionalism", "https://plato.stanford.edu/entries/functionalism/"),
        ("2", "Neisser et al. / APA Task Force", "Intelligence: Knowns and Unknowns", "https://doi.org/10.1037/0003-066X.51.2.77"),
        ("3", "Alan Turing, Mind (1950)", "Computing Machinery and Intelligence", "https://doi.org/10.1093/mind/LIX.236.433"),
        ("4", "University of Chicago Press", "Mead: Mind, Self, and Society", "https://press.uchicago.edu/ucp/books/book/chicago/M/bo20099389.html"),
        ("5", "Internet Encyclopedia of Philosophy", "George Herbert Mead", "https://iep.utm.edu/mead/"),
        ("6", "Herbert Blumer / University of California Press", "Symbolic Interactionism: Perspective and Method", "https://books.google.com/books/about/Symbolic_Interactionism.html?id=HVuognZFofoC"),
        ("7", "Stanford Encyclopedia of Philosophy", "Social Ontology", "https://plato.stanford.edu/entries/social-ontology/"),
        ("8", "Stanford Encyclopedia of Philosophy", "Recognition", "https://plato.stanford.edu/entries/recognition/"),
        ("9", "Ned Block", "Troubles with Functionalism", "https://www.nedblock.us/papers/1981.Troubles.pdf"),
    ]
    yy = 445
    for i, (num, org, title, url) in enumerate(refs):
        col = [TEAL, BLUE, CORAL][i % 3]
        fill = [TEAL_LIGHT, BLUE_LIGHT, CORAL_LIGHT][i % 3]
        c.setFillColor(fill)
        c.circle(66, yy + 3, 13, fill=1, stroke=0)
        c.setFillColor(col)
        set_font(c, 8.5, bold=True)
        c.drawCentredString(66, yy, num)
        text_block(c, org, 90, yy + 9, 260, 10, color=INK, bold=True, max_lines=1)
        text_block(c, title, 360, yy + 9, 350, 10, color=col, medium=True, max_lines=1)
        c.setStrokeColor(LINE)
        c.line(90, yy - 14, 760, yy - 14)
        c.linkURL(url, (50, yy - 17, 780, yy + 18), relative=0)
        yy -= 39

    rounded(c, 55, 42, 730, 63, GOLD_LIGHT, stroke=GOLD, radius=14)
    text_block(c, "證據邊界", 75, 78, 100, 12, color=GOLD, bold=True)
    text_block(c, "本報告可支持架構分工、錯誤可歸因與右腦風險控制；不能單憑這些資料宣稱系統已有人類意識、法律人格或完整社會主體性。", 175, 78, 580, 10.5, leading=17, color=INK, max_lines=2)
    c.showPage()


def build() -> None:
    register_fonts()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(W, H), pageCompression=1)
    c.setTitle("為什麼不把所有東西都塞進右腦？")
    c.setAuthor("UruhaBrain Project")
    c.setSubject("RightBrain architecture, functionalism, IQ, symbolic interactionism, and social subjectivity")
    draw_cover(c)
    draw_executive(c)
    draw_architecture_compare(c)
    draw_overload(c)
    draw_coffee_case(c)
    draw_privacy(c)
    draw_evidence(c)
    draw_functionalism(c)
    draw_iq(c)
    draw_symbolic_interaction(c)
    draw_subjectivity(c)
    draw_theory_to_system(c)
    draw_design_principles(c)
    draw_references(c)
    c.save()
    print(OUT)


if __name__ == "__main__":
    build()
