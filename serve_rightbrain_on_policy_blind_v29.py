#!/usr/bin/env python3
"""Serve the compact V29 blind comparison and atomically autosave each vote."""

import argparse
import hashlib
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
    RIGHTBRAIN_ON_POLICY_V29_RATINGS_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
CHOICES = {"left_better", "tie", "right_better", "both_bad"}
CHOICE_LABELS = {
    "left_better": "左邊比較好",
    "tie": "兩邊差不多",
    "right_better": "右邊比較好",
    "both_bad": "兩邊都不好",
}
BLIND_UI_CSS = """
:root { --paper: #f4efe3; --ink: #1f2926; --rust: #bb573a; --moss: #53675d; }
.gradio-container {
  background: radial-gradient(circle at 12% 8%, #fff9e9 0, transparent 34%),
              linear-gradient(145deg, var(--paper), #e8e2d3);
  color: var(--ink); font-family: "Yu Mincho", "Hiragino Mincho ProN", serif;
}
.hero { max-width: 1040px; margin: 0 auto; padding: 18px 0 4px; }
.hero h1 { letter-spacing: .04em; font-size: 2rem; margin-bottom: .25rem; }
.response-card { border: 1px solid #c8bfac !important; box-shadow: 0 8px 24px #594f3c18; }
.choice-row button { min-height: 52px; font-weight: 700; }
#left-choice, #right-choice { background: var(--ink); color: #fff; }
#both-bad { border-color: var(--rust); color: #8f3525; }
"""


def _now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def _package_sha256(package):
    payload = {
        key: value for key, value in package.items() if key != "package_sha256"
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_package(path):
    package = json.loads(Path(path).read_text(encoding="utf-8"))
    comparisons = package.get("comparisons") or []
    if not package.get("package_sha256"):
        raise ValueError("Blind package is missing package_sha256")
    if package["package_sha256"] != _package_sha256(package):
        raise ValueError("Blind package SHA does not match its content")
    if package.get("comparison_count") != len(comparisons) or not comparisons:
        raise ValueError("Blind package comparison count is invalid")
    ids = [row.get("comparison_id") for row in comparisons]
    if None in ids or len(ids) != len(set(ids)):
        raise ValueError("Blind package comparison IDs are invalid")
    return package


class RatingStore:
    def __init__(self, path, package):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.package_sha256 = package["package_sha256"]
        self.comparison_ids = [row["comparison_id"] for row in package["comparisons"]]
        self._id_set = set(self.comparison_ids)
        self._lock = threading.Lock()
        self._ratings = {}
        self.created_at = _now()
        if self.path.exists():
            self._load()

    def _load(self):
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("package_sha256") != self.package_sha256:
            raise ValueError(
                "Existing ratings belong to a different blind package; refusing to mix evidence"
            )
        self.created_at = payload.get("created_at") or self.created_at
        for row in payload.get("ratings") or []:
            comparison_id = row.get("comparison_id")
            choice = row.get("choice")
            if comparison_id in self._id_set and choice in CHOICES:
                self._ratings[comparison_id] = row

    def _payload(self):
        return {
            "schema_version": 1,
            "package_sha256": self.package_sha256,
            "created_at": self.created_at,
            "updated_at": _now(),
            "completed": len(self._ratings) == len(self.comparison_ids),
            "rated_count": len(self._ratings),
            "comparison_count": len(self.comparison_ids),
            "ratings": [
                self._ratings[comparison_id]
                for comparison_id in self.comparison_ids
                if comparison_id in self._ratings
            ],
        }

    def _atomic_write(self):
        payload = self._payload()
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    def record(self, comparison_id, choice, note=""):
        if comparison_id not in self._id_set:
            raise ValueError("Unknown comparison_id")
        if choice not in CHOICES:
            raise ValueError("Unknown rating choice")
        note = str(note or "").strip()[:500]
        with self._lock:
            self._ratings[comparison_id] = {
                "comparison_id": comparison_id,
                "choice": choice,
                "choice_label_zh": CHOICE_LABELS[choice],
                "note": note,
                "rated_at": _now(),
            }
            self._atomic_write()

    def rated_count(self):
        with self._lock:
            return len(self._ratings)

    def next_unrated_id(self):
        with self._lock:
            return next(
                (
                    comparison_id
                    for comparison_id in self.comparison_ids
                    if comparison_id not in self._ratings
                ),
                "",
            )


def build_app(package, store):
    import gradio as gr

    comparisons = {
        row["comparison_id"]: row for row in package["comparisons"]
    }
    total = len(comparisons)

    def view(comparison_id=""):
        comparison_id = comparison_id or store.next_unrated_id()
        if not comparison_id:
            return (
                f"## {total} / {total}　評分完成",
                "所有選擇都已經自動儲存。",
                "",
                "",
                "",
                "已完成，可以關閉這個頁面。",
                "",
            )
        row = comparisons[comparison_id]
        progress = store.rated_count() + 1
        return (
            f"## {progress} / {total}",
            row["user_input"],
            row["response_a"],
            row["response_b"],
            comparison_id,
            "選擇比較適合直接對人說的一邊。",
            "",
        )

    def submit(choice, note, comparison_id):
        if not comparison_id:
            return view("")
        store.record(comparison_id, choice, note)
        return view(store.next_unrated_id())

    with gr.Blocks(title="右腦回答盲測") as demo:
        gr.Markdown(
            """<div class="hero"><h1>哪一個回答更像自然聊天？</h1>
            <p>左右都來自同一個右腦。只比較自然度、是否漏掉重點，以及人格語氣是否合理。</p></div>"""
        )
        progress = gr.Markdown()
        user_input = gr.Textbox(label="使用者說", interactive=False, lines=2)
        with gr.Row():
            response_a = gr.Textbox(
                label="左邊回答",
                interactive=False,
                lines=5,
                elem_classes=["response-card"],
            )
            response_b = gr.Textbox(
                label="右邊回答",
                interactive=False,
                lines=5,
                elem_classes=["response-card"],
            )
        status = gr.Markdown()
        note = gr.Textbox(
            label="備註（可不填）",
            placeholder="只有想補充原因時才填",
            lines=1,
        )
        current_id = gr.State("")
        with gr.Row(elem_classes=["choice-row"]):
            left = gr.Button("左邊比較好", elem_id="left-choice")
            tie = gr.Button("兩邊差不多")
            right = gr.Button("右邊比較好", elem_id="right-choice")
            both_bad = gr.Button("兩邊都不好", elem_id="both-bad")

        outputs = [
            progress,
            user_input,
            response_a,
            response_b,
            current_id,
            status,
            note,
        ]
        demo.load(view, outputs=outputs)
        left.click(
            lambda note_value, item_id: submit("left_better", note_value, item_id),
            inputs=[note, current_id],
            outputs=outputs,
        )
        tie.click(
            lambda note_value, item_id: submit("tie", note_value, item_id),
            inputs=[note, current_id],
            outputs=outputs,
        )
        right.click(
            lambda note_value, item_id: submit("right_better", note_value, item_id),
            inputs=[note, current_id],
            outputs=outputs,
        )
        both_bad.click(
            lambda note_value, item_id: submit("both_bad", note_value, item_id),
            inputs=[note, current_id],
            outputs=outputs,
        )
    return demo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", default=RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH)
    parser.add_argument("--ratings", default=RIGHTBRAIN_ON_POLICY_V29_RATINGS_PATH)
    parser.add_argument("--server-name", default="127.0.0.1")
    parser.add_argument(
        "--server-port",
        type=int,
        default=int(os.getenv("URUHA_HUMAN_PREF_PORT", "7872")),
    )
    args = parser.parse_args()
    package = load_package(args.package)
    store = RatingStore(args.ratings, package)
    demo = build_app(package, store)
    print(f"http://{args.server_name}:{args.server_port}", flush=True)
    demo.launch(
        server_name=args.server_name,
        server_port=args.server_port,
        share=False,
        show_error=True,
        inbrowser=False,
        css=BLIND_UI_CSS,
    )


if __name__ == "__main__":
    main()
