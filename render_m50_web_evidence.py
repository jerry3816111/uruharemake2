"""Render one frozen real-Web M50 turn without rerunning it."""
from __future__ import annotations

import argparse
import gzip
from html import escape
import json
from pathlib import Path

from uruha_current_task_source_bundle_m50 import render_m50


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("log_gz")
    parser.add_argument("--session", required=True); parser.add_argument("--turn", type=int, required=True)
    parser.add_argument("--output", required=True); args = parser.parse_args()
    with gzip.open(args.log_gz, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    row = next(item for item in rows if item.get("session_id") == args.session and item.get("turn_index") == args.turn)
    cognition = row.get("cognition_trace") or {}
    result = {"user_text": row.get("user_text"), "reply": row.get("assistant_reply"),
              "logic": row.get("logic") or {}, "runtime_trace": cognition.get("runtime_trace") or {},
              "runtime_state": cognition.get("runtime_state") or {}, "memory_data": row.get("memory_snapshot") or {}}
    observatory = render_m50(result)
    document = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M50 frozen actual Safari turn</title>
<style>body{{margin:0;background:#0c1220;color:#f4f7ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}.evidence{{max-width:1500px;margin:24px auto;padding:0 22px}}.boundary{{background:#172338;border:1px solid #7396cc;border-radius:14px;padding:16px;margin-bottom:16px;line-height:1.65}}.boundary strong{{display:block;font-size:19px;margin-bottom:5px}}.turn{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}}.turn div{{background:#101a2b;border-radius:10px;padding:12px}}@media(max-width:800px){{.turn{{grid-template-columns:1fr}}}}</style></head>
<body><main class="evidence"><section class="boundary"><strong>凍結的真 Safari 輪次 · M50</strong>這不是重新生成或新成功輪；下方直接渲染 session {escape(args.session)} turn {args.turn} 的原始 runtime trace。
<div class="turn"><div><b>輸入</b><br>{escape(str(row.get('user_text') or ''))}</div><div><b>實際輸出</b><br>{escape(str(row.get('assistant_reply') or ''))}</div></div></section>{observatory}</main></body></html>"""
    Path(args.output).write_text(document, encoding="utf-8"); print(args.output)


if __name__ == "__main__": main()
