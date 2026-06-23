from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports"
FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_NAME = "SongtiReport"


@dataclass(frozen=True)
class PdfTheme:
    bg: colors.Color = colors.HexColor("#F7F3EA")
    ink: colors.Color = colors.HexColor("#1E2428")
    muted: colors.Color = colors.HexColor("#66716F")
    blue: colors.Color = colors.HexColor("#206B8F")
    teal: colors.Color = colors.HexColor("#15836F")
    orange: colors.Color = colors.HexColor("#D1742F")
    red: colors.Color = colors.HexColor("#B7473A")
    card: colors.Color = colors.HexColor("#FFFDF6")
    line: colors.Color = colors.HexColor("#D9D0C2")


THEME = PdfTheme()


def register_fonts() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))


def read_json(path: str) -> dict:
    p = ROOT / path
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def setup_page(c: canvas.Canvas, title: str, page_no: int, total_pages: int) -> None:
    width, height = landscape(A4)
    c.setFillColor(THEME.bg)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(THEME.ink)
    c.setFont(FONT_NAME, 24)
    c.drawString(38, height - 48, title)
    c.setStrokeColor(THEME.line)
    c.setLineWidth(1)
    c.line(38, height - 60, width - 38, height - 60)
    c.setFillColor(THEME.muted)
    c.setFont(FONT_NAME, 9)
    c.drawRightString(width - 38, 24, f"{page_no}/{total_pages}")


def fit_lines(text: str, font_size: int, max_width: float) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        current = ""
        for ch in raw:
            trial = current + ch
            if pdfmetrics.stringWidth(trial, FONT_NAME, font_size) <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def draw_wrapped(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font_size: int = 13,
    leading: float | None = None,
    color: colors.Color | None = None,
) -> float:
    if leading is None:
        leading = font_size + 6
    c.setFont(FONT_NAME, font_size)
    c.setFillColor(color or THEME.ink)
    for line in fit_lines(text, font_size, max_width):
        c.drawString(x, y, line)
        y -= leading
    return y


def card(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    accent: colors.Color,
    big: str | None = None,
) -> None:
    c.setFillColor(THEME.card)
    c.setStrokeColor(THEME.line)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(accent)
    c.roundRect(x, y + h - 9, w, 9, 4, fill=1, stroke=0)
    c.setFillColor(THEME.ink)
    c.setFont(FONT_NAME, 15)
    c.drawString(x + 16, y + h - 32, title)
    if big:
        c.setFillColor(accent)
        c.setFont(FONT_NAME, 30)
        c.drawString(x + 16, y + h - 70, big)
        body_y = y + h - 96
    else:
        body_y = y + h - 58
    draw_wrapped(c, body, x + 16, body_y, w - 32, 11, 16, THEME.muted)


def flow(
    c: canvas.Canvas,
    labels: Iterable[str],
    x: float,
    y: float,
    box_w: float,
    box_h: float,
    gap: float,
    active_until: int,
) -> None:
    labels = list(labels)
    for i, label in enumerate(labels):
        bx = x + i * (box_w + gap)
        color = THEME.teal if i <= active_until else colors.HexColor("#DDD6CC")
        c.setFillColor(color)
        c.setStrokeColor(color)
        c.roundRect(bx, y, box_w, box_h, 9, fill=1, stroke=0)
        c.setFillColor(colors.white if i <= active_until else THEME.muted)
        c.setFont(FONT_NAME, 12)
        lines = fit_lines(label, 12, box_w - 16)[:2]
        ty = y + box_h / 2 + (len(lines) - 1) * 7
        for line in lines:
            c.drawCentredString(bx + box_w / 2, ty, line)
            ty -= 15
        if i < len(labels) - 1:
            c.setStrokeColor(THEME.muted)
            c.setLineWidth(1.5)
            c.line(bx + box_w + 4, y + box_h / 2, bx + box_w + gap - 4, y + box_h / 2)
            c.line(bx + box_w + gap - 10, y + box_h / 2 + 5, bx + box_w + gap - 4, y + box_h / 2)
            c.line(bx + box_w + gap - 10, y + box_h / 2 - 5, bx + box_w + gap - 4, y + box_h / 2)


def bar_chart(
    c: canvas.Canvas,
    items: list[tuple[str, float, str]],
    x: float,
    y: float,
    w: float,
    h: float,
    max_value: float,
    title: str,
) -> None:
    c.setFillColor(THEME.card)
    c.setStrokeColor(THEME.line)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFont(FONT_NAME, 15)
    c.setFillColor(THEME.ink)
    c.drawString(x + 18, y + h - 28, title)
    top = y + h - 58
    row_h = 34
    for idx, (name, value, note) in enumerate(items):
        cy = top - idx * row_h
        c.setFillColor(THEME.ink)
        c.setFont(FONT_NAME, 11)
        c.drawString(x + 18, cy, name)
        bx = x + 150
        bw = max(2, (w - 255) * (value / max_value if max_value else 0))
        c.setFillColor(colors.HexColor("#D8E9E3"))
        c.roundRect(bx, cy - 5, w - 255, 12, 6, fill=1, stroke=0)
        c.setFillColor(THEME.teal if value > 0 else THEME.red)
        c.roundRect(bx, cy - 5, bw, 12, 6, fill=1, stroke=0)
        c.setFillColor(THEME.muted)
        c.setFont(FONT_NAME, 10)
        c.drawRightString(x + w - 18, cy, note)


def simple_table(
    c: canvas.Canvas,
    headers: list[str],
    rows: list[list[str]],
    x: float,
    y: float,
    col_widths: list[float],
    row_h: float,
) -> None:
    total_w = sum(col_widths)
    c.setFillColor(THEME.blue)
    c.roundRect(x, y - row_h, total_w, row_h, 8, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(FONT_NAME, 12)
    cx = x
    for head, width in zip(headers, col_widths):
        c.drawString(cx + 8, y - 22, head)
        cx += width
    c.setStrokeColor(THEME.line)
    cy = y - row_h
    for ridx, row in enumerate(rows):
        c.setFillColor(THEME.card if ridx % 2 == 0 else colors.HexColor("#F1EADF"))
        c.rect(x, cy - row_h, total_w, row_h, fill=1, stroke=0)
        c.setFillColor(THEME.ink)
        c.setFont(FONT_NAME, 10)
        cx = x
        for cell, width in zip(row, col_widths):
            draw_wrapped(c, cell, cx + 8, cy - 18, width - 14, 10, 12, THEME.ink)
            cx += width
        cy -= row_h


def write_markdown(path: Path, title: str, sections: list[tuple[str, list[str]]]) -> None:
    lines = [f"# {title}", ""]
    for head, body in sections:
        lines += [f"## {head}", ""]
        for item in body:
            lines += [item, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_github_report() -> None:
    total_pages = 3
    pdf_path = REPORT_DIR / "github_upload_progress_report_zh_2026-06-23.pdf"
    md_path = REPORT_DIR / "github_upload_progress_report_zh_2026-06-23.md"
    c = canvas.Canvas(str(pdf_path), pagesize=landscape(A4))
    width, height = landscape(A4)

    setup_page(c, "GitHub 上線進度報告", 1, total_pages)
    draw_wrapped(c, "重點：專案已經從本機雜亂開發，整理成可用 GitHub PR 管理的流程。現在不是只把檔案丟上去，而是每次改動都能用分支、測試、報告與 PR 留下紀錄。", 48, height - 100, width - 96, 17, 25)
    card(c, 48, 330, 225, 110, "已成功合併", "最近一批功能已透過 Pull Request 合併到 main，不再只停留在本機。", THEME.teal, "PR #16-#25")
    card(c, 306, 330, 225, 110, "最近主線", "目前 main 已到 PR #25：Gate real right-brain model candidates。", THEME.blue, "#25")
    card(c, 564, 330, 225, 110, "現在分支", "下一輪右腦契約對齊在獨立分支處理，避免直接污染 main。", THEME.orange, "codex/")
    flow(c, ["本機修正", "測試與報告", "建立分支", "Push 到 GitHub", "建立 PR", "Merge main"], 48, 245, 112, 48, 20, 5)
    draw_wrapped(c, "一句話：GitHub 這次的成功點，是專案已經有「可追蹤、可回滾、可審查」的工程路線。", 48, 168, width - 96, 18, 26, THEME.ink)
    c.showPage()

    setup_page(c, "從上次報告到現在：PR 時間線", 2, total_pages)
    headers = ["PR", "主題", "這段進度代表什麼"]
    rows = [
        ["#20", "選擇性記憶評估", "把記憶系統從『有沒有記得』推進到『該不該說、該不該用』。"],
        ["#21", "Planner 自我修正", "讓左腦計畫產生後能被檢查與修正，不只是一次生成。"],
        ["#22", "主動對話後續", "補上未完成對話與後續提醒能力，讓互動更像連續關係。"],
        ["#23", "人類盲測證據", "把人的評分與觀察納入資料，不只靠模型自己判斷。"],
        ["#24", "右腦微規劃", "降低固定模板感，讓左腦語意能被比較自然地轉成日文回覆。"],
        ["#25", "真實右腦模型候選門檻", "讓真實 LoRA 候選必須通過語意與語言門檻，不合格就退回安全回覆。"],
    ]
    simple_table(c, headers, rows, 48, height - 92, [70, 190, 500], 55)
    draw_wrapped(c, "一句話：這一段不是單點修補，而是把記憶、計畫、右腦輸出、人類評分與 GitHub 管理串成同一條研發線。", 48, 76, width - 96, 15, 22, THEME.ink)
    c.showPage()

    setup_page(c, "現在的 GitHub 狀態", 3, total_pages)
    card(c, 48, 380, 230, 108, "主線 main", "已同步到 GitHub，最近合併點是 PR #25。這是目前對外最穩定的版本。", THEME.teal)
    card(c, 304, 380, 230, 108, "乾淨工作樹", "新的 GitHub clean workspace 用來做 PR，舊本機髒檔不再阻礙每次提交。", THEME.blue)
    card(c, 560, 380, 230, 108, "下一個 PR", "右腦 contract alignment、訓練資料、訓練結果與本報告會走下一個 PR。", THEME.orange)
    flow(c, ["main 穩定版", "feature branch", "只提交相關檔", "測試通過", "PR 審查", "合併"], 48, 288, 112, 48, 20, 2)
    draw_wrapped(c, "控制原則：不是看到 dirty file 就全部清掉，而是只把和本次改動有關的檔案放進 PR；無關舊檔保留在舊工作樹，不讓它們干擾 GitHub 歷史。", 48, 205, width - 96, 15, 22)
    draw_wrapped(c, "一句話：現在的專案已經可以用 GitHub 當正式研發紀錄，而不是只靠本機資料夾保存進度。", 48, 124, width - 96, 18, 26, THEME.ink)
    c.showPage()
    c.save()

    write_markdown(
        md_path,
        "GitHub 上線進度報告",
        [
            ("重點", ["專案已經建立 clean workspace -> branch -> tests/reports -> PR -> merge main 的流程。"]),
            ("已完成", ["PR #16-#25 已合併；最近主線是 PR #25 Gate real right-brain model candidates。"]),
            ("目前狀態", ["新的右腦 contract alignment 工作在獨立分支，避免直接污染 main。"]),
        ],
    )


def build_engineering_report() -> None:
    gate = read_json("reports/rightbrain_model_gate_report.json")
    gate_summary = gate.get("summary", {})
    data_summary = read_json("reports/rightbrain_plan_surface_contract_v1_dataset_summary.json")
    train = read_json("reports/rightbrain_contract_v1_training_run.json")
    align = read_json("reports/rightbrain_contract_alignment_report.json")

    raw_accept = gate_summary.get("raw_candidate_acceptance_rate", 0) * 100
    final_pass = gate_summary.get("final_contract_pass_rate", 0) * 100
    fallback = gate_summary.get("fallback_protection_rate", 0) * 100
    kept_rows = data_summary.get("stats", {}).get("kept_rows", data_summary.get("rows", 0))
    train_rows = train.get("train_rows", 0)
    eval_rows = train.get("eval_rows", 0)
    eval_loss = train.get("sampled_eval_loss", 0)

    total_pages = 3
    pdf_path = REPORT_DIR / "engineering_progress_since_last_report_zh_2026-06-23.pdf"
    md_path = REPORT_DIR / "engineering_progress_since_last_report_zh_2026-06-23.md"
    c = canvas.Canvas(str(pdf_path), pagesize=landscape(A4))
    width, height = landscape(A4)

    setup_page(c, "工程進度報告：右腦與 GitHub 化", 1, total_pages)
    draw_wrapped(c, "上次報告後，主要問題不是左腦完全不會想，而是右腦最後輸出不穩：可能漏掉左腦要表達的重點、混入不該出現的字、或產生看似自然但不符合契約的回覆。", 48, height - 104, width - 96, 16, 24)
    flow(c, ["問題：答案會消失", "補契約：左腦語意固定格式", "補門檻：不合格不接管", "補資料：1025 筆訓練集", "補訓練：V8 實驗", "結論：暫不切換"], 48, 330, 112, 54, 20, 5)
    card(c, 64, 164, 210, 104, "改造前", "真實模型候選會產生，但很難穩定保留左腦語意。", THEME.red, f"{raw_accept:.0f}%")
    card(c, 316, 164, 210, 104, "安全輸出", "候選失敗時，fallback 仍能保持最終回覆契約。", THEME.teal, f"{final_pass:.0f}%")
    card(c, 568, 164, 210, 104, "本次判定", "V8 訓練有損失下降，但行為門檻未通過，所以不切換預設。", THEME.orange, "不切換")
    draw_wrapped(c, "一句話：這次不是宣稱右腦已經變強，而是把『真實模型何時可以上線』變成可測、可擋、可追蹤。", 48, 92, width - 96, 17, 25)
    c.showPage()

    setup_page(c, "右腦契約對齊：改了哪裡", 2, total_pages)
    flow(c, ["左腦 meaning", "v1 契約 payload", "模型生成候選", "語意/語言 gate", "通過才接管", "失敗走 fallback"], 48, height - 170, 112, 54, 20, 5)
    headers = ["改動", "目的", "對整體專案的意義"]
    rows = [
        ["契約版本 v1", "讓 runtime payload 和訓練資料使用同一種欄位。", "降低『訓練時看的是 A 格式，上線時收到 B 格式』的錯位。"],
        ["隱藏原始中文輸入", "模型只看左腦整理後的日文 meaning。", "避免右腦直接學使用者中文或把中文混進日文回覆。"],
        ["嚴格候選 gate", "檢查語意槽、ASCII 泄漏、中文混入、過度介入。", "讓錯誤候選不能進入最終聊天輸出。"],
        ["base-only 對照", "可以測沒有 LoRA 時的基準。", "確認改善不是單純 base model 自己會。"],
    ]
    simple_table(c, headers, rows, 48, height - 245, [150, 250, 360], 58)
    draw_wrapped(c, "一句話：這次真正補的是右腦的輸出契約，不是把 ToMBench 題目塞給模型當小抄。", 48, 65, width - 96, 16, 24)
    c.showPage()

    setup_page(c, "目前數據：能主張什麼", 3, total_pages)
    bar_chart(
        c,
        [
            ["PR #25 真實候選合格", raw_accept, f"{raw_accept:.1f}%"],
            ["最終契約通過", final_pass, f"{final_pass:.1f}%"],
            ["fallback 保護", fallback, f"{fallback:.1f}%"],
            ["V8 是否可接管", 0, "0/6"],
        ],
        48,
        290,
        360,
        205,
        100,
        "小型開發集結果",
    )
    card(c, 438, 390, 160, 105, "資料集", "從舊 curriculum 轉成正式訓練資料；不能再當 holdout。", THEME.blue, str(kept_rows))
    card(c, 620, 390, 170, 105, "訓練切分", f"train {train_rows} / eval {eval_rows}。", THEME.teal)
    card(c, 438, 250, 160, 105, "Eval loss", "V8 訓練後有數值下降，但這不等於聊天可上線。", THEME.orange, f"{eval_loss:.2f}")
    card(c, 620, 250, 170, 105, "採用判定", "行為 gate 未通過，所以不切預設。", THEME.red, "No")
    draw_wrapped(c, "目前可以主張：GitHub 流程已建立；右腦上線前的安全門與契約已建立；V8 是一次有價值但未達上線門檻的實驗。", 48, 160, width - 96, 16, 24)
    draw_wrapped(c, "目前不能主張：右腦已經正式自然化、已經能穩定接管、或 ToMBench 分數會因這次 F 改造而直接上升。", 48, 96, width - 96, 16, 24, THEME.red)
    c.showPage()
    c.save()

    best_after = align.get("best_observed_after", {}).get("label", "未定")
    write_markdown(
        md_path,
        "工程進度報告：右腦與 GitHub 化",
        [
            ("主要問題", ["上次報告後的核心問題是右腦輸出不穩，左腦語意可能在最後回覆消失。"]),
            ("本次改造", ["建立 runtime v1 契約、嚴格 gate、base-only 對照、1025 筆訓練資料與 V8 訓練實驗。"]),
            ("數據", [f"PR #25 gate: raw accept {raw_accept:.1f}%, final contract {final_pass:.1f}%, fallback {fallback:.1f}%.", f"訓練資料 {kept_rows} 筆；V8 eval loss {eval_loss:.2f}；小型比較最佳 after 標籤：{best_after}。"]),
            ("判定", ["V8 尚未通過接管門檻，因此不切換預設；這次進度的價值是建立可測與可阻擋的上線標準。"]),
        ],
    )


def main() -> None:
    register_fonts()
    REPORT_DIR.mkdir(exist_ok=True)
    build_github_report()
    build_engineering_report()


if __name__ == "__main__":
    main()
