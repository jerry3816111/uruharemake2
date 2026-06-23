from __future__ import annotations

from build_github_progress_reports_zh import (
    REPORT_DIR,
    THEME,
    bar_chart,
    card,
    draw_wrapped,
    flow,
    read_json,
    register_fonts,
    setup_page,
    simple_table,
    write_markdown,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def build_github_report_ja() -> None:
    total_pages = 3
    pdf_path = REPORT_DIR / "github_upload_progress_report_ja_2026-06-23.pdf"
    md_path = REPORT_DIR / "github_upload_progress_report_ja_2026-06-23.md"
    c = canvas.Canvas(str(pdf_path), pagesize=landscape(A4))
    width, height = landscape(A4)

    setup_page(c, "GitHub 公開進捗レポート", 1, total_pages)
    draw_wrapped(
        c,
        "要点：プロジェクトはローカルだけの雑多な開発状態から、GitHub の Pull Request で管理できる流れに移行した。"
        "今は単にファイルをアップロードする段階ではなく、各変更をブランチ、テスト、レポート、PR として記録できる。",
        48,
        height - 100,
        width - 96,
        16,
        24,
    )
    card(c, 48, 330, 225, 110, "マージ済み", "直近の機能群は PR を通して main に統合済み。", THEME.teal, "PR #16-#25")
    card(c, 306, 330, 225, 110, "直近の main", "現在の main は PR #25 まで反映済み。", THEME.blue, "#25")
    card(c, 564, 330, 225, 110, "現在の分岐", "次の右脳契約整合は独立ブランチで処理。", THEME.orange, "codex/")
    flow(c, ["ローカル修正", "テストと報告", "ブランチ作成", "GitHub へ push", "PR 作成", "main へ merge"], 48, 245, 112, 48, 20, 5)
    draw_wrapped(
        c,
        "一文まとめ：今回の GitHub 化の成功点は、プロジェクトに「追跡できる・戻せる・レビューできる」工程ができたこと。",
        48,
        168,
        width - 96,
        17,
        25,
        THEME.ink,
    )
    c.showPage()

    setup_page(c, "前回報告から現在まで：PR タイムライン", 2, total_pages)
    headers = ["PR", "テーマ", "この進捗が意味すること"]
    rows = [
        ["#20", "選択的記憶評価", "記憶を「覚えているか」だけでなく、「言うべきか・使うべきか」まで評価する段階へ進めた。"],
        ["#21", "Planner 自己修正", "左脳計画を一度生成して終わりにせず、検査と修正のループを入れた。"],
        ["#22", "能動的な対話フォロー", "未完了の会話や後続確認を扱えるようにし、単発応答ではなく継続関係に近づけた。"],
        ["#23", "人間ブラインド評価", "人間の評価と観察をデータに入れ、モデル自身の判定だけに頼らないようにした。"],
        ["#24", "右脳マイクロプランニング", "固定テンプレート感を減らし、左脳の意味をより自然な日本語応答へ変換する方向を補強した。"],
        ["#25", "実モデル候補のゲート", "実際の LoRA 候補に意味と言語の門番を通らせ、不合格なら安全な deterministic 応答へ戻す。"],
    ]
    simple_table(c, headers, rows, 48, height - 92, [70, 205, 485], 55)
    draw_wrapped(
        c,
        "一文まとめ：この期間は単発修正ではなく、記憶、計画、右脳出力、人間評価、GitHub 管理を一本の研究開発ラインにまとめた。",
        48,
        76,
        width - 96,
        15,
        22,
        THEME.ink,
    )
    c.showPage()

    setup_page(c, "現在の GitHub 状態", 3, total_pages)
    card(c, 48, 380, 230, 108, "main", "GitHub と同期済み。直近の統合点は PR #25。", THEME.teal)
    card(c, 304, 380, 230, 108, "clean workspace", "PR 作業用の clean workspace を使用。", THEME.blue)
    card(c, 560, 380, 230, 108, "次の PR", "契約整合、訓練データ、報告を PR 化。", THEME.orange)
    flow(c, ["main 安定版", "feature branch", "関連ファイルだけ commit", "テスト通過", "PR レビュー", "統合"], 48, 288, 112, 48, 20, 2)
    draw_wrapped(
        c,
        "管理原則：dirty file を全部消すのではなく、その変更に関係するファイルだけを PR に入れる。"
        "無関係な旧ファイルは旧作業木に残し、GitHub の履歴を汚さない。",
        48,
        205,
        width - 96,
        15,
        22,
    )
    draw_wrapped(
        c,
        "一文まとめ：現在のプロジェクトは、ローカルフォルダだけで進捗を保存する状態から、GitHub を正式な研究開発記録として使える状態へ移行した。",
        48,
        124,
        width - 96,
        17,
        25,
        THEME.ink,
    )
    c.showPage()
    c.save()

    write_markdown(
        md_path,
        "GitHub 公開進捗レポート",
        [
            ("要点", ["プロジェクトは clean workspace -> branch -> tests/reports -> PR -> merge main の流れを確立した。"]),
            ("完了したこと", ["PR #16-#25 は merge 済み。直近の main は PR #25 Gate real right-brain model candidates。"]),
            ("現在の状態", ["次の右脳 contract alignment は独立ブランチで扱い、main を直接汚さない。"]),
        ],
    )


def build_engineering_report_ja() -> None:
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
    pdf_path = REPORT_DIR / "engineering_progress_since_last_report_ja_2026-06-23.pdf"
    md_path = REPORT_DIR / "engineering_progress_since_last_report_ja_2026-06-23.md"
    c = canvas.Canvas(str(pdf_path), pagesize=landscape(A4))
    width, height = landscape(A4)

    setup_page(c, "技術進捗レポート：右脳と GitHub 化", 1, total_pages)
    draw_wrapped(
        c,
        "前回報告後の主な問題は、左脳がまったく考えられないことではなく、右脳の最終出力が不安定なことだった。"
        "左脳が伝えたい要点が抜ける、不要な文字が混ざる、自然に見えても契約に合わない返答になる可能性があった。",
        48,
        height - 104,
        width - 96,
        15,
        23,
    )
    flow(c, ["問題：答えが消える", "契約補強", "門番補強", "1025件データ", "V8 実験", "結論：切替なし"], 48, 330, 112, 54, 20, 5)
    card(c, 64, 164, 210, 104, "改造前", "実モデル候補は左脳の意味を残しにくい。", THEME.red, f"{raw_accept:.0f}%")
    card(c, 316, 164, 210, 104, "安全出力", "失敗時も fallback が契約を守る。", THEME.teal, f"{final_pass:.0f}%")
    card(c, 568, 164, 210, 104, "今回の判定", "V8 は gate 未通過。既定モデルにしない。", THEME.orange, "切替なし")
    draw_wrapped(
        c,
        "一文まとめ：今回は右脳が完成したという主張ではなく、「実モデルをいつ本番に出してよいか」を測定・遮断・追跡できる形にした。",
        48,
        92,
        width - 96,
        17,
        25,
    )
    c.showPage()

    setup_page(c, "右脳契約整合：何を変えたか", 2, total_pages)
    flow(c, ["左脳 meaning", "v1 契約 payload", "モデル候補生成", "意味/言語 gate", "通過時だけ採用", "失敗時 fallback"], 48, height - 170, 112, 54, 20, 5)
    headers = ["変更点", "目的", "プロジェクト上の意味"]
    rows = [
        ["契約 version v1", "runtime payload と訓練データの欄位を同じ形式にする。", "訓練時は A 形式、実行時は B 形式というズレを減らす。"],
        ["元の中国語入力を隠す", "モデルには左脳が整理した日本語 meaning だけを見せる。", "右脳がユーザーの中国語を直接まねたり、日本語応答へ混ぜたりするのを防ぐ。"],
        ["厳格な候補 gate", "意味スロット、ASCII 漏れ、中国語混入、過剰介入を検査する。", "間違った候補が最終チャット出力に入らないようにする。"],
        ["base-only 対照", "LoRA なしの基準状態も測れるようにする。", "改善が単に base model の能力だけではないか確認できる。"],
    ]
    simple_table(c, headers, rows, 48, height - 245, [150, 250, 360], 58)
    draw_wrapped(
        c,
        "一文まとめ：今回補強したのは右脳の出力契約であり、ToMBench の問題を小テスト対策として覚えさせたわけではない。",
        48,
        65,
        width - 96,
        16,
        24,
    )
    c.showPage()

    setup_page(c, "現在の数値：何を主張できるか", 3, total_pages)
    bar_chart(
        c,
        [
            ["PR #25 実候補合格", raw_accept, f"{raw_accept:.1f}%"],
            ["最終契約通過", final_pass, f"{final_pass:.1f}%"],
            ["fallback 保護", fallback, f"{fallback:.1f}%"],
            ["V8 採用可能性", 0, "0/6"],
        ],
        48,
        290,
        360,
        205,
        100,
        "小型開発セット結果",
    )
    card(c, 438, 390, 160, 105, "データセット", "旧 curriculum を訓練用へ転用。", THEME.blue, str(kept_rows))
    card(c, 620, 390, 170, 105, "訓練分割", f"train {train_rows} / eval {eval_rows}。", THEME.teal)
    card(c, 438, 250, 160, 105, "Eval loss", "数値低下は本番化の証明ではない。", THEME.orange, f"{eval_loss:.2f}")
    card(c, 620, 250, 170, 105, "採用判定", "行動 gate 未通過。", THEME.red, "No")
    draw_wrapped(
        c,
        "現在主張できること：GitHub フローは確立した。右脳を本番投入する前の安全門と契約はできた。V8 は価値のある実験だが、まだ本番基準ではない。",
        48,
        160,
        width - 96,
        15,
        23,
    )
    draw_wrapped(
        c,
        "現在主張できないこと：右脳が正式に自然化した、安定接管できる、または今回の F 改造だけで ToMBench 点数が直接上がる、とはまだ言えない。",
        48,
        96,
        width - 96,
        15,
        23,
        THEME.red,
    )
    c.showPage()
    c.save()

    best_after = align.get("best_observed_after", {}).get("label", "未定")
    write_markdown(
        md_path,
        "技術進捗レポート：右脳と GitHub 化",
        [
            ("主な問題", ["前回報告後の核心問題は、右脳出力が不安定で、左脳の意味が最終応答で消える可能性があることだった。"]),
            ("今回の改造", ["runtime v1 契約、厳格 gate、base-only 対照、1025 件の訓練データ、V8 訓練実験を追加した。"]),
            ("数値", [f"PR #25 gate: raw accept {raw_accept:.1f}%, final contract {final_pass:.1f}%, fallback {fallback:.1f}%.", f"訓練データ {kept_rows} 件。V8 eval loss {eval_loss:.2f}。小型比較での best observed after は {best_after}。"]),
            ("判定", ["V8 はまだ接管基準を満たさないため、既定モデルにはしない。今回の価値は、上線前の測定と遮断基準を作ったこと。"]),
        ],
    )


def main() -> None:
    register_fonts()
    REPORT_DIR.mkdir(exist_ok=True)
    build_github_report_ja()
    build_engineering_report_ja()


if __name__ == "__main__":
    main()
