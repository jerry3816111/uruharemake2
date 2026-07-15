#!/usr/bin/env python3
"""Build a concise, visual Traditional Chinese summary of V33 results."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "reports" / "rightbrain_qwen35_migration_v33_analysis.json"
RAW_PATH = ROOT / "reports" / "rightbrain_qwen35_migration_v33_raw.json"
OUT_PATH = ROOT / "output" / "pdf" / "rightbrain_qwen35_v33_simple_results_zh_tw_2026-07-15.pdf"
FONT_PATH = Path("/System/Library/Fonts/Supplemental/Songti.ttc")

W, H = landscape(A4)
PAGES = 5

BG = HexColor("#F3F0E8")
PAPER = HexColor("#FFFDF8")
INK = HexColor("#173239")
MUTED = HexColor("#62767B")
LINE = HexColor("#CAD5D1")
TEAL = HexColor("#087E78")
TEAL_DARK = HexColor("#075D5A")
TEAL_LIGHT = HexColor("#D7EFEB")
BLUE = HexColor("#3276A8")
BLUE_LIGHT = HexColor("#DCECF6")
CORAL = HexColor("#E26D50")
CORAL_LIGHT = HexColor("#F9E1D8")
GOLD = HexColor("#D7A42E")
GOLD_LIGHT = HexColor("#F6E9BF")
GREEN = HexColor("#3D8A62")
GREEN_LIGHT = HexColor("#DDEEE3")
RED = HexColor("#B64D48")
RED_LIGHT = HexColor("#F4DDDA")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("TC", str(FONT_PATH), subfontIndex=7))
    pdfmetrics.registerFont(TTFont("TC-Bold", str(FONT_PATH), subfontIndex=2))


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def draw_text(c, x, y, text, size=12, color=INK, bold=False, align="left") -> None:
    c.setFillColor(color)
    c.setFont("TC-Bold" if bold else "TC", size)
    if align == "center":
        c.drawCentredString(x, y, text)
    elif align == "right":
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)


def wrapped_lines(text: str, width: float, size: float, bold=False) -> list[str]:
    font = "TC-Bold" if bold else "TC"
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and pdfmetrics.stringWidth(candidate, font, size) > width:
                lines.append(current)
                current = char
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def draw_wrapped(c, x, y, width, text, size=12, leading=None, color=INK, bold=False, max_lines=None):
    leading = leading or size * 1.45
    lines = wrapped_lines(text, width, size, bold=bold)
    if max_lines is not None:
        lines = lines[:max_lines]
    for index, line in enumerate(lines):
        draw_text(c, x, y - index * leading, line, size=size, color=color, bold=bold)
    return y - len(lines) * leading


def box(c, x, y, w, h, fill=PAPER, stroke=LINE, radius=14, line_width=1) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(line_width)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def page_base(c, page_no, tag, title, subtitle=None) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.roundRect(34, H - 56, 94, 24, 12, fill=1, stroke=0)
    draw_text(c, 81, H - 49, tag, 11, PAPER, bold=True, align="center")
    draw_text(c, 34, H - 91, title, 25, INK, bold=True)
    if subtitle:
        draw_text(c, 34, H - 116, subtitle, 12, MUTED)
    draw_text(c, W - 34, 20, f"V33 右腦與 VRM 測試｜{page_no}/{PAGES}", 8.5, MUTED, align="right")


def arrow(c, x1, y1, x2, y2, color=TEAL, width=3) -> None:
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)
    if x2 >= x1:
        points = [(x2, y2), (x2 - 10, y2 + 6), (x2 - 10, y2 - 6)]
    else:
        points = [(x2, y2), (x2 + 10, y2 + 6), (x2 + 10, y2 - 6)]
    path = c.beginPath()
    path.moveTo(*points[0])
    path.lineTo(*points[1])
    path.lineTo(*points[2])
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def speech_icon(c, x, y, scale=1.0, color=TEAL) -> None:
    c.setStrokeColor(color)
    c.setLineWidth(3 * scale)
    c.roundRect(x, y, 56 * scale, 38 * scale, 10 * scale, fill=0, stroke=1)
    c.line(x + 14 * scale, y, x + 8 * scale, y - 9 * scale)
    for offset in (16, 28, 40):
        c.setFillColor(color)
        c.circle(x + offset * scale, y + 20 * scale, 2.2 * scale, fill=1, stroke=0)


def avatar_icon(c, x, y, scale=1.0, color=BLUE) -> None:
    c.setStrokeColor(color)
    c.setFillColor(PAPER)
    c.setLineWidth(3 * scale)
    c.circle(x + 25 * scale, y + 42 * scale, 15 * scale, fill=1, stroke=1)
    c.arc(x, y, x + 50 * scale, y + 35 * scale, 0, 180)
    c.line(x, y + 17 * scale, x, y + 5 * scale)
    c.line(x + 50 * scale, y + 17 * scale, x + 50 * scale, y + 5 * scale)


def clock_icon(c, x, y, scale=1.0, color=CORAL) -> None:
    c.setStrokeColor(color)
    c.setLineWidth(3 * scale)
    c.circle(x, y, 22 * scale, fill=0, stroke=1)
    c.line(x, y, x, y + 12 * scale)
    c.line(x, y, x + 10 * scale, y - 6 * scale)


def model_card(c, x, y, title, subtitle, color, light) -> None:
    box(c, x, y, 150, 100, fill=light, stroke=color, radius=18, line_width=2)
    c.setFillColor(color)
    c.circle(x + 32, y + 50, 20, fill=1, stroke=0)
    draw_text(c, x + 32, y + 43, title.split()[0], 10, PAPER, bold=True, align="center")
    draw_text(c, x + 62, y + 63, title, 15, color, bold=True)
    draw_text(c, x + 62, y + 42, subtitle, 10, MUTED)
    draw_text(c, x + 62, y + 24, "無人格微調", 10, RED, bold=True)


def horizontal_bar(
    c,
    x,
    y,
    w,
    label,
    value,
    color,
    note=None,
    lower_is_better=False,
    display_value=None,
) -> None:
    draw_text(c, x, y + 19, label, 11.5, INK, bold=True)
    c.setFillColor(HexColor("#E5EAE7"))
    c.roundRect(x, y, w, 12, 6, fill=1, stroke=0)
    c.setFillColor(color)
    c.roundRect(x, y, max(4, w * value), 12, 6, fill=1, stroke=0)
    draw_text(c, x + w + 12, y - 1, display_value or pct(value), 15, color, bold=True)
    if note:
        draw_text(c, x + w + 72, y, note, 9.5, MUTED)
    if lower_is_better:
        draw_text(c, x + w - 2, y + 19, "越低越好", 8.5, MUTED, align="right")


def metric_pair(c, x, y, w, title, left_value, right_value, left_label="Qwen2.5", right_label="Qwen3.5"):
    box(c, x, y, w, 96, fill=PAPER, stroke=LINE)
    draw_text(c, x + 14, y + 70, title, 11, INK, bold=True)
    draw_text(c, x + 14, y + 43, left_label, 9.5, MUTED)
    draw_text(c, x + 14, y + 17, left_value, 20, BLUE, bold=True)
    c.setStrokeColor(LINE)
    c.line(x + w / 2, y + 15, x + w / 2, y + 60)
    draw_text(c, x + w / 2 + 14, y + 43, right_label, 9.5, MUTED)
    draw_text(c, x + w / 2 + 14, y + 17, right_value, 20, TEAL, bold=True)


def page_one(c, report) -> None:
    page_base(c, 1, "測試方法", "兩個模型，走同一條考場", "只更換模型；題目、提示、電腦與評分方式保持相同。")
    model_card(c, 42, 338, "2.5  7B", "本機壓縮版", BLUE, BLUE_LIGHT)
    model_card(c, 42, 204, "3.5  9B", "本機壓縮版", TEAL, TEAL_LIGHT)

    box(c, 250, 245, 188, 170, fill=PAPER, stroke=GOLD, radius=22, line_width=2)
    draw_text(c, 344, 382, "相同測試", 18, GOLD, bold=True, align="center")
    draw_text(c, 344, 349, "48 題右腦語言", 14, INK, bold=True, align="center")
    draw_text(c, 344, 323, "每個模型 432 句", 12, MUTED, align="center")
    c.setStrokeColor(LINE)
    c.line(278, 307, 410, 307)
    draw_text(c, 344, 282, "120 題 VRM 動作", 14, INK, bold=True, align="center")
    draw_text(c, 344, 258, "每題只判工具呼叫", 11, MUTED, align="center")

    arrow(c, 194, 388, 244, 366, BLUE)
    arrow(c, 194, 254, 244, 292, TEAL)
    arrow(c, 444, 330, 500, 330, GOLD)

    box(c, 506, 245, 292, 170, fill=TEAL_LIGHT, stroke=TEAL, radius=22, line_width=2)
    speech_icon(c, 530, 331, 0.7, TEAL)
    avatar_icon(c, 535, 263, 0.72, BLUE)
    draw_text(c, 606, 367, "語言：有沒有把重點說出來？", 14, TEAL_DARK, bold=True)
    draw_text(c, 606, 339, "動作：該動才動、不該動就停", 14, TEAL_DARK, bold=True)
    draw_text(c, 606, 306, "速度：個人電腦能不能負擔？", 14, TEAL_DARK, bold=True)
    draw_text(c, 606, 268, "原始輸出直接計分，不先修飾", 11, MUTED)

    box(c, 42, 88, 756, 82, fill=CORAL_LIGHT, stroke=CORAL, radius=18, line_width=2)
    draw_text(c, 64, 139, "這次沒有測什麼？", 14, CORAL, bold=True)
    draw_text(c, 64, 108, "兩邊都沒有掛人格微調，所以這不是『誰更像目標人物』的測試，也不是完整聊天系統總分。", 13, INK, bold=True)


def page_two(c, report) -> None:
    control = report["rightbrain_summary"]["qwen2_5_7b_quantized_control"]
    treatment = report["rightbrain_summary"]["qwen3_5_9b_quantized_treatment"]
    page_base(c, 2, "語言結果", "Qwen3.5 更容易把左腦重點完整說出來", "主要優勢是『少漏重點』，不是每一句都自然。")

    box(c, 34, 305, 470, 160, fill=PAPER, stroke=LINE)
    draw_text(c, 54, 436, "三個候選中，至少一個完整", 15, INK, bold=True)
    horizontal_bar(c, 54, 382, 310, "Qwen2.5", control["raw_semantic_contract_coverage_rate"], BLUE)
    horizontal_bar(c, 54, 330, 310, "Qwen3.5", treatment["raw_semantic_contract_coverage_rate"], TEAL)
    draw_text(c, 54, 313, "119/144 組", 9.5, BLUE)
    draw_text(c, 224, 313, "143/144 組", 9.5, TEAL)

    box(c, 520, 305, 288, 160, fill=GOLD_LIGHT, stroke=GOLD)
    draw_text(c, 540, 436, "99.3% 要怎麼看？", 15, GOLD, bold=True)
    draw_wrapped(c, 540, 405, 248, "每題重跑 3 次；每次產生 3 句。只要其中 1 句把所有必要重點說出來，該組就算成功。", 12, 18, INK, bold=True)
    draw_text(c, 540, 325, "不是每一句都有 99.3 分。", 13, RED, bold=True)

    metric_pair(c, 34, 190, 235, "單句完整率", pct(control["candidate_semantic_contract_pass_rate"]), pct(treatment["candidate_semantic_contract_pass_rate"]))
    metric_pair(c, 282, 190, 235, "必要重點命中", pct(control["v32_semantic_slot_recall"]), pct(treatment["v32_semantic_slot_recall"]))
    metric_pair(c, 530, 190, 278, "嚴重文字問題（越低越好）", pct(control["hard_surface_failure_rate"]), pct(treatment["hard_surface_failure_rate"]))

    box(c, 34, 70, 774, 96, fill=BLUE_LIGHT, stroke=BLUE)
    draw_text(c, 54, 139, "同一題的重點差異：『截止日不是星期五，是星期四』", 13, BLUE, bold=True)
    draw_text(c, 54, 111, "Qwen2.5：金曜日じゃなくて木曜日だよ。", 11.5, INK)
    draw_text(c, 418, 111, "只說星期四，漏掉『截止』與『接受訂正』", 10.5, RED)
    draw_text(c, 54, 84, "Qwen3.5：締切は木曜だったね。訂正して言い直すよ。", 11.5, INK)
    draw_text(c, 418, 84, "三個重點都有說出來", 10.5, GREEN, bold=True)


def page_three(c, report) -> None:
    control = report["action_summary"]["qwen2_5_7b_quantized_control"]
    treatment = report["action_summary"]["qwen3_5_9b_quantized_treatment"]
    page_base(c, 3, "VRM 動作", "Qwen3.5 不是不會動，而是太容易亂動", "需要的動作大多抓得到；真正弱點是『不該動時停不下來』。")

    metric_pair(c, 34, 358, 235, "工具完全正確", pct(control["exact_tool_call_set_and_argument_accuracy"]), pct(treatment["exact_tool_call_set_and_argument_accuracy"]))
    metric_pair(c, 282, 358, 235, "需要動作時有抓到", pct(control["mean_required_action_recall"]), pct(treatment["mean_required_action_recall"]))
    metric_pair(c, 530, 358, 278, "不該動時真的沒動", pct(control["no_action_specificity"]), pct(treatment["no_action_specificity"]))

    box(c, 34, 238, 774, 96, fill=CORAL_LIGHT, stroke=CORAL, radius=20, line_width=2)
    draw_text(c, 56, 303, "造成分數下降的主因", 14, CORAL, bold=True)
    draw_text(c, 56, 270, "多做或做錯動作：Qwen2.5  37/120", 16, BLUE, bold=True)
    draw_text(c, 427, 270, "Qwen3.5  57/120", 19, RED, bold=True)
    draw_text(c, 427, 247, "幾乎每兩題就有一題多做動作", 10.5, RED)

    examples = [
        ("普通聊天", "最近有好玩的遊戲嗎？", "應該不動", "卻切成驚訝表情"),
        ("意思不清楚", "好像想要你指，又好像不想。", "應該先不動", "卻執行指向動作"),
        ("否定命令", "不要指。", "應該不動", "卻真的執行指向"),
    ]
    colors = [(BLUE, BLUE_LIGHT), (GOLD, GOLD_LIGHT), (RED, RED_LIGHT)]
    for index, ((kind, question, expected, actual), (stroke, fill)) in enumerate(zip(examples, colors)):
        x = 34 + index * 258
        box(c, x, 76, 242, 138, fill=fill, stroke=stroke)
        draw_text(c, x + 16, 187, kind, 12, stroke, bold=True)
        draw_wrapped(c, x + 16, 160, 210, f"「{question}」", 11.5, 17, INK, bold=True, max_lines=2)
        draw_text(c, x + 16, 112, expected, 10.5, GREEN, bold=True)
        arrow(c, x + 92, 115, x + 126, 115, stroke, 2)
        draw_wrapped(c, x + 135, 121, 92, actual, 10.5, 15, RED, bold=True, max_lines=2)


def page_four(c, report, raw) -> None:
    control = report["rightbrain_summary"]["qwen2_5_7b_quantized_control"]
    treatment = report["rightbrain_summary"]["qwen3_5_9b_quantized_treatment"]
    page_base(c, 4, "速度與負擔", "Qwen3.5 在這台 Mac 上約慢 4 倍", "模型較大、每句更長，而且提示文字的處理也比較慢。")

    box(c, 34, 292, 774, 167, fill=PAPER, stroke=LINE)
    clock_icon(c, 78, 386, 1.1, CORAL)
    draw_text(c, 118, 440, "每次回答的中間速度", 15, INK, bold=True)
    horizontal_bar(
        c,
        118,
        385,
        420,
        "Qwen2.5",
        control["warm_generation_median_seconds"] / 5.0,
        BLUE,
        display_value="1.10 秒",
    )
    horizontal_bar(
        c,
        118,
        332,
        420,
        "Qwen3.5",
        treatment["warm_generation_median_seconds"] / 5.0,
        TEAL,
        display_value="4.47 秒",
    )
    draw_text(c, 650, 370, "約 4.05 倍", 24, CORAL, bold=True, align="center")
    draw_text(c, 650, 343, "但仍低於 5 秒上限", 10.5, MUTED, align="center")

    cards = [
        ("模型大小（B=十億）", "7.6B", "9.7B", "參數更多"),
        ("模型輸出單位", "22", "38", "Qwen3.5 多約 73%"),
        ("提示處理", "0.04 秒", "2.34 秒", "目前最大的時間差"),
        ("回答生成", "0.87 秒", "1.88 秒", "單次生成也較慢"),
    ]
    for index, (title, left, right, note) in enumerate(cards):
        x = 34 + index * 194
        box(c, x, 112, 180, 160, fill=TEAL_LIGHT if index % 2 else BLUE_LIGHT, stroke=TEAL if index % 2 else BLUE)
        draw_text(c, x + 14, 241, title, 12, INK, bold=True)
        draw_text(c, x + 14, 205, left, 18, BLUE, bold=True)
        draw_text(c, x + 14, 184, "Qwen2.5", 9, MUTED)
        draw_text(c, x + 96, 205, right, 18, TEAL, bold=True)
        draw_text(c, x + 96, 184, "Qwen3.5", 9, MUTED)
        c.setStrokeColor(LINE)
        c.line(x + 14, 166, x + 166, 166)
        draw_wrapped(c, x + 14, 146, 152, note, 10.5, 15, INK, bold=True, max_lines=2)


def page_five(c, report) -> None:
    page_base(c, 5, "最後決定", "不整體替換；把語言與動作分開處理", "這次結果支持『分工』，不支持直接把 Qwen3.5 全面上線。")

    box(c, 34, 305, 774, 160, fill=PAPER, stroke=LINE)
    draw_text(c, 421, 438, "最合理的下一版方向：從同一個規劃分成兩條路", 16, INK, bold=True, align="center")
    box(c, 58, 334, 140, 66, fill=GOLD_LIGHT, stroke=GOLD, radius=15, line_width=2)
    draw_text(c, 128, 373, "認知規劃", 13, GOLD, bold=True, align="center")
    draw_text(c, 128, 352, "先決定意思", 9.5, MUTED, align="center")
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(198, 367, 220, 367)
    c.line(220, 340, 220, 406)
    arrow(c, 220, 406, 240, 406, TEAL, 2)
    arrow(c, 220, 340, 240, 340, BLUE, 2)
    box(c, 246, 383, 154, 46, fill=TEAL_LIGHT, stroke=TEAL, radius=13, line_width=2)
    draw_text(c, 323, 411, "語言：Qwen3.5 候選", 11.5, TEAL, bold=True, align="center")
    draw_text(c, 323, 393, "先改善自然度與長度", 8.5, MUTED, align="center")
    box(c, 246, 317, 154, 46, fill=BLUE_LIGHT, stroke=BLUE, radius=13, line_width=2)
    draw_text(c, 323, 345, "動作：Qwen2.5 或規則", 11.5, BLUE, bold=True, align="center")
    draw_text(c, 323, 327, "先學會不該動就停", 8.5, MUTED, align="center")
    arrow(c, 404, 406, 448, 406, TEAL, 2)
    arrow(c, 404, 340, 448, 340, BLUE, 2)
    box(c, 454, 383, 154, 46, fill=GREEN_LIGHT, stroke=GREEN, radius=13, line_width=2)
    draw_text(c, 531, 411, "文字輸出檢查", 11.5, GREEN, bold=True, align="center")
    draw_text(c, 531, 393, "保留重點、攔截污染", 8.5, MUTED, align="center")
    box(c, 454, 317, 154, 46, fill=CORAL_LIGHT, stroke=CORAL, radius=13, line_width=2)
    draw_text(c, 531, 345, "動作安全檢查", 11.5, CORAL, bold=True, align="center")
    draw_text(c, 531, 327, "否定、模糊、超出範圍", 8.5, MUTED, align="center")
    arrow(c, 612, 406, 666, 406, GREEN, 2)
    arrow(c, 612, 340, 666, 340, CORAL, 2)
    draw_text(c, 718, 400, "文字／語音", 11, GREEN, bold=True, align="center")
    draw_text(c, 718, 334, "VRM 動作", 11, CORAL, bold=True, align="center")

    decisions = [
        ("語言表達", "保留 Qwen3.5 當候選", "它比較少漏掉左腦重點", GREEN, GREEN_LIGHT),
        ("VRM 動作", "暫時不要交給 Qwen3.5", "它太容易在不該動時亂動", RED, RED_LIGHT),
        ("人格微調", "目前先不開始", "先把自然度、長度與速度修好", GOLD, GOLD_LIGHT),
    ]
    for index, (title, decision, reason, stroke, fill) in enumerate(decisions):
        x = 34 + index * 258
        box(c, x, 182, 242, 130, fill=fill, stroke=stroke, radius=18, line_width=2)
        draw_text(c, x + 16, 280, title, 12, stroke, bold=True)
        draw_wrapped(c, x + 16, 252, 210, decision, 13, 19, INK, bold=True, max_lines=2)
        draw_wrapped(c, x + 16, 207, 210, reason, 10.5, 15, MUTED, max_lines=2)

    box(c, 34, 73, 774, 78, fill=CORAL_LIGHT, stroke=CORAL)
    draw_text(c, 54, 123, "這次結果不能證明", 12, CORAL, bold=True)
    draw_text(c, 54, 94, "Qwen3.5 更像目標人物、完整聊天系統已提升，或系統已具有人類心智。它只回答『哪個本機模型適合哪一種工作』。", 11.5, INK, bold=True)


def build() -> Path:
    register_fonts()
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT_PATH), pagesize=(W, H), pageCompression=1)
    c.setTitle("V33 Qwen2.5 與 Qwen3.5 簡易測試結果")
    c.setAuthor("UruhaBrain Project")
    for page in (
        lambda: page_one(c, report),
        lambda: page_two(c, report),
        lambda: page_three(c, report),
        lambda: page_four(c, report, raw),
        lambda: page_five(c, report),
    ):
        page()
        c.showPage()
    c.save()
    return OUT_PATH


if __name__ == "__main__":
    print(build())
