#!/usr/bin/env python3
"""Prepare, run, and analyze the M13 published PUB pragmatics benchmark."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import time
from typing import Any
from urllib import error, request

from longitudinal_human_model.pub_pragmatics import (
    CONDITIONS,
    audit_payload_contract,
    build_case_manifest,
    build_prompt,
    download_verified,
    load_task_rows,
    materialize_case,
    paired_accuracy_comparison,
    parse_answer_index,
    summarize_rows,
)
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    write_json_atomic,
)


ROOT = Path(__file__).resolve().parent
PROTOCOL_PATH = ROOT / "configs/m13_pub_pragmatics_preregistration.json"
AMENDMENT_PATH = ROOT / "configs/m13_1_pub_generation_contract_amendment.json"
MANIFEST_PATH = ROOT / "configs/m13_pub_pragmatics_case_manifest.json"
EXTERNAL_DATA_DIR = ROOT / "external_data/pub_m13"
CHECKPOINT_PATH = ROOT / "analysis/local_m13_pub_pragmatics/checkpoint.json"
RAW_RESULT_PATH = ROOT / "analysis/m13_pub_pragmatics_raw_result.json"
RESULT_PATH = ROOT / "analysis/m13_pub_pragmatics_result.json"
REPORT_PATH = ROOT / "analysis/m13_pub_pragmatics_report_2026-08-17.md"
DASHBOARD_PATH = ROOT / "analysis/m13_pub_pragmatics_dashboard_2026-08-17.html"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OllamaJsonProvider:
    def __init__(self, endpoint: str, timeout: int = 240):
        self.endpoint = endpoint
        self.timeout = timeout

    def __call__(self, *, model: str, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "format": "json",
            "options": dict(options),
        }
        http_request = request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama JSON request failed: {exc}") from exc
        if not isinstance(body, dict) or not isinstance(body.get("response"), str):
            raise RuntimeError("Ollama response did not contain response text")
        return {
            "text": body["response"],
            "latency_seconds": time.perf_counter() - started,
            "prompt_tokens": int(body.get("prompt_eval_count") or 0),
            "completion_tokens": int(body.get("eval_count") or 0),
            "model_reported": body.get("model"),
        }


def prepare_sources(protocol: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    rows = {}
    template = protocol["dataset"]["download_url_template"]
    for task in protocol["dataset"]["tasks"]:
        task_id = int(task["task_id"])
        path = EXTERNAL_DATA_DIR / f"task_{task_id}.zip"
        download_verified(
            template.format(task_id=task_id), path, str(task["zip_sha256"])
        )
        rows[task_id] = load_task_rows(path, task_id)
        if len(rows[task_id]) != int(task["expected_row_count"]):
            raise ValueError(f"task {task_id} row count drift")
    return rows


def prepare_manifest() -> dict[str, Any]:
    protocol = load_json(PROTOCOL_PATH)
    task_rows = prepare_sources(protocol)
    manifest = build_case_manifest(protocol, task_rows)
    write_json_atomic(MANIFEST_PATH, manifest)
    return manifest


def _condition_order(sample_id: str) -> list[str]:
    offset = int(hashlib.sha256(sample_id.encode("utf-8")).hexdigest()[:8], 16) % len(CONDITIONS)
    return list(CONDITIONS[offset:] + CONDITIONS[:offset])


def _load_checkpoint(protocol_sha: str, manifest_sha: str, amendment_sha: str) -> dict[str, Any]:
    if not CHECKPOINT_PATH.is_file():
        return {
            "schema_version": "m13-pub-raw-v1",
            "status": "running",
            "started_at": utc_now(),
            "protocol_sha256": protocol_sha,
            "manifest_sha256": manifest_sha,
            "amendment_sha256": amendment_sha,
            "rows": [],
        }
    checkpoint = load_json(CHECKPOINT_PATH)
    if checkpoint.get("protocol_sha256") != protocol_sha:
        raise ValueError("checkpoint protocol hash differs")
    if checkpoint.get("manifest_sha256") != manifest_sha:
        raise ValueError("checkpoint manifest hash differs")
    if checkpoint.get("amendment_sha256") != amendment_sha:
        raise ValueError("checkpoint amendment hash differs")
    return checkpoint


def run_experiment(provider: OllamaJsonProvider | None = None) -> dict[str, Any]:
    protocol = load_json(PROTOCOL_PATH)
    if not MANIFEST_PATH.is_file():
        raise ValueError("case manifest missing; run --prepare before generation")
    manifest = load_json(MANIFEST_PATH)
    task_rows = prepare_sources(protocol)
    rebuilt = build_case_manifest(protocol, task_rows)
    if rebuilt != manifest:
        raise ValueError("case manifest differs from deterministic rebuild")
    protocol_sha = sha256_file(PROTOCOL_PATH)
    manifest_sha = sha256_file(MANIFEST_PATH)
    amendment = load_json(AMENDMENT_PATH)
    amendment_sha = sha256_file(AMENDMENT_PATH)
    if amendment["parent_protocol"]["sha256"] != protocol_sha:
        raise ValueError("amendment parent protocol hash differs")
    if amendment["case_manifest"]["sha256"] != manifest_sha:
        raise ValueError("amendment case manifest hash differs")
    generation_options = dict(protocol["generation"]["options"])
    generation_options["num_predict"] = int(
        amendment["authorized_changes"]["num_predict"]["after"]
    )
    checkpoint = _load_checkpoint(protocol_sha, manifest_sha, amendment_sha)
    completed = {
        (str(row["sample_id"]), str(row["condition"])) for row in checkpoint["rows"]
    }
    provider = provider or OllamaJsonProvider(protocol["generation"]["endpoint"])
    cases = [materialize_case(case, task_rows) for case in manifest["cases"]]
    total = len(cases) * len(CONDITIONS)
    for case in cases:
        for condition in _condition_order(case["sample_id"]):
            key = (case["sample_id"], condition)
            if key in completed:
                continue
            prompt = build_prompt(case, condition)
            response = provider(
                model=protocol["model"],
                prompt=prompt,
                options=generation_options,
            )
            parsed = parse_answer_index(response["text"], len(case["options"]))
            predicted_index = parsed["answer_index"]
            row = {
                "sample_id": case["sample_id"],
                "task_id": case["task_id"],
                "phenomenon": case["phenomenon"],
                "task_name": case["task_name"],
                "item_id": case["item_id"],
                "condition": condition,
                "pretext": case["pretext"],
                "options": case["options"],
                "correct_index": case["correct_index"],
                "correct_answer": case["correct_answer"],
                "predicted_index": predicted_index,
                "predicted_answer": (
                    case["options"][predicted_index] if predicted_index is not None else None
                ),
                "correct": predicted_index == case["correct_index"],
                "parse_valid": bool(parsed["valid"]),
                "parse_error": parsed["error"],
                "parsed_payload": parsed.get("payload"),
                "raw_response": response["text"],
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "prompt_tokens": response["prompt_tokens"],
                "completion_tokens": response["completion_tokens"],
                "latency_seconds": round(float(response["latency_seconds"]), 6),
                "model_reported": response.get("model_reported"),
            }
            checkpoint["rows"].append(row)
            checkpoint["updated_at"] = utc_now()
            write_json_atomic(CHECKPOINT_PATH, checkpoint)
            completed.add(key)
            print(
                f"M13 {len(completed)}/{total} {case['sample_id']} {condition} "
                f"correct={row['correct']} parse={row['parse_valid']}",
                flush=True,
            )
    checkpoint.update(
        {
            "status": "complete",
            "completed_at": utc_now(),
            "model": protocol["model"],
            "generation": protocol["generation"],
            "effective_generation_options": generation_options,
            "amendment_sha256": amendment_sha,
            "source_bindings": {
                f"task_{task['task_id']}": task["zip_sha256"]
                for task in protocol["dataset"]["tasks"]
            },
            "runtime": runtime_snapshot(),
            "git": git_snapshot(ROOT),
            "production_memory_writes": 0,
            "tool_or_physical_actions": 0,
        }
    )
    write_json_atomic(CHECKPOINT_PATH, checkpoint)
    write_json_atomic(RAW_RESULT_PATH, checkpoint)
    return checkpoint


def analyze(raw: dict[str, Any] | None = None, *, bootstrap_repetitions: int = 20_000) -> dict[str, Any]:
    protocol = load_json(PROTOCOL_PATH)
    manifest = load_json(MANIFEST_PATH)
    raw = raw or load_json(RAW_RESULT_PATH)
    rows = list(raw["rows"])
    expected = int(protocol["sampling"]["total_case_count"]) * len(CONDITIONS)
    if raw.get("status") != "complete" or len(rows) != expected:
        raise ValueError(f"raw result incomplete: {len(rows)}/{expected}")
    keys = [(row["sample_id"], row["condition"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate sample-condition rows")
    rows = [dict(row) for row in rows]
    for row in rows:
        audit = audit_payload_contract(row["condition"], row.get("parsed_payload"))
        row["schema_contract_valid"] = audit["valid"]
        row["schema_contract_audit"] = audit
    summary = summarize_rows(rows)
    comparisons = {
        "ours_vs_generic": paired_accuracy_comparison(
            rows,
            candidate="OURS_PRAGMATIC_LOOP",
            baseline="B1_GENERIC_DELIBERATION",
            bootstrap_repetitions=bootstrap_repetitions,
            seed=20260817,
        ),
        "ours_vs_direct": paired_accuracy_comparison(
            rows,
            candidate="OURS_PRAGMATIC_LOOP",
            baseline="B0_DIRECT",
            bootstrap_repetitions=bootstrap_repetitions,
            seed=20260818,
        ),
    }
    task_deltas = {}
    for task_id in sorted(summary["OURS_PRAGMATIC_LOOP"]["by_task"]):
        task_deltas[task_id] = round(
            summary["OURS_PRAGMATIC_LOOP"]["by_task"][task_id]["accuracy"]
            - summary["B1_GENERIC_DELIBERATION"]["by_task"][task_id]["accuracy"],
            6,
        )
    gate = protocol["success_gate"]
    hypotheses = {
        "H1_all_parse": all(
            summary[condition]["parse_rate"] >= float(gate["all_conditions_parse_rate"])
            for condition in CONDITIONS
        ),
        "H2_primary_accuracy_and_significance": (
            comparisons["ours_vs_generic"]["accuracy_delta"]
            >= float(gate["primary_accuracy_delta_minimum"])
            and comparisons["ours_vs_generic"]["exact_mcnemar_pvalue"]
            <= float(gate["primary_exact_mcnemar_p_maximum"])
        ),
        "H3_no_large_task_regression": min(task_deltas.values())
        >= -float(gate["maximum_allowed_per_task_accuracy_regression"]),
    }
    gate_passed = all(hypotheses.values())
    ours_schema_complete = summary["OURS_PRAGMATIC_LOOP"]["schema_contract_rate"] == 1.0
    paired_rows = {(row["sample_id"], row["condition"]): row for row in rows}
    discordant_cases = []
    for sample_id in sorted({row["sample_id"] for row in rows}):
        ours = paired_rows[(sample_id, "OURS_PRAGMATIC_LOOP")]
        generic = paired_rows[(sample_id, "B1_GENERIC_DELIBERATION")]
        if ours["correct"] != generic["correct"]:
            discordant_cases.append(
                {
                    "sample_id": sample_id,
                    "task_id": ours["task_id"],
                    "ours_correct": ours["correct"],
                    "generic_correct": generic["correct"],
                    "ours_schema_contract_valid": ours["schema_contract_valid"],
                }
            )
    result = {
        "schema_version": "m13-pub-pragmatics-result-v1",
        "created_at": utc_now(),
        "decision": (
            "pass_narrow_pragmatic_gain"
            if gate_passed and ours_schema_complete
            else "fail_narrow_pragmatic_gain_with_implementation_fidelity_gap"
        ),
        "gate_passed": gate_passed,
        "hypotheses": hypotheses,
        "summary": summary,
        "comparisons": comparisons,
        "task_accuracy_delta_ours_minus_generic": task_deltas,
        "posthoc_implementation_fidelity_audit": {
            "status": "posthoc_diagnostic_not_an_added_preregistered_gate",
            "ours_schema_complete_count": sum(
                row["schema_contract_valid"]
                for row in rows
                if row["condition"] == "OURS_PRAGMATIC_LOOP"
            ),
            "ours_schema_total": manifest["case_count"],
            "ours_schema_contract_rate": summary["OURS_PRAGMATIC_LOOP"][
                "schema_contract_rate"
            ],
            "interpretation": "Answer indices were parseable, but the intended decomposition was not consistently instantiated; prompt assignment is not equivalent to implementation fidelity."
        },
        "discordant_cases_ours_vs_generic": discordant_cases,
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "amendment_sha256": sha256_file(AMENDMENT_PATH),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "raw_result_sha256": sha256_file(RAW_RESULT_PATH),
        "case_count": manifest["case_count"],
        "rows": rows,
        "claim_authorized": (
            "a narrow same-model pragmatic-decomposition gain on the frozen PUB subset"
            if gate_passed and ours_schema_complete
            else "reasoning conditions outperform direct answering on this frozen subset; no evidence that the current pragmatic implementation outperforms generic deliberation"
        ),
        "claim_not_authorized": [
            "pretraining-uncontaminated PUB generalization",
            "longitudinal person understanding",
            "human felt-understanding preference",
            "Uruha persona fidelity",
            "human-brain equivalence or mind reading",
        ],
        "evidence_boundary": protocol["evidence_boundary"],
    }
    write_json_atomic(RESULT_PATH, result)
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    DASHBOARD_PATH.write_text(render_dashboard(result), encoding="utf-8")
    return result


def _pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    primary = result["comparisons"]["ours_vs_generic"]
    secondary = result["comparisons"]["ours_vs_direct"]
    task_names = {str(row["task_id"]): row["task_name"] for row in result["rows"]}
    lines = [
        "# M13 PUB Published Pragmatics Benchmark",
        "",
        f"**Decision: `{result['decision']}`**",
        "",
        "## Controlled result",
        "",
        "| Condition | Accuracy | Answer parse | Full schema | Prompt tokens | Completion tokens | Latency |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        item = summary[condition]
        lines.append(
            f"| {condition} | {_pct(item['accuracy'])} | {_pct(item['parse_rate'])} | "
            f"{_pct(item['schema_contract_rate'])} | "
            f"{item['prompt_tokens']:,} | {item['completion_tokens']:,} | "
            f"{item['latency_seconds']:.1f}s |"
        )
    lines.extend(
        [
            "",
            "Primary is Ours versus generic deliberation on the same 64 items and model: "
            f"accuracy delta `{primary['accuracy_delta']:+.3f}`, paired bootstrap 95% CI "
            f"`[{primary['bootstrap_95_ci'][0]:+.3f}, {primary['bootstrap_95_ci'][1]:+.3f}]`, "
            f"exact McNemar `p={primary['exact_mcnemar_pvalue']:.4f}`, "
            f"wins/ties/losses `{primary['candidate_wins']}/{primary['ties']}/{primary['baseline_wins']}`.",
            "",
            "Secondary Ours versus direct: "
            f"delta `{secondary['accuracy_delta']:+.3f}`, CI "
            f"`[{secondary['bootstrap_95_ci'][0]:+.3f}, {secondary['bootstrap_95_ci'][1]:+.3f}]`, "
            f"McNemar `p={secondary['exact_mcnemar_pvalue']:.4f}`.",
            "",
            "## Task-level result",
            "",
            "| Task | Direct | Generic | Ours | Ours - Generic |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for task_id, delta in result["task_accuracy_delta_ours_minus_generic"].items():
        lines.append(
            f"| T{task_id} {task_names[task_id]} | "
            f"{_pct(summary['B0_DIRECT']['by_task'][task_id]['accuracy'])} | "
            f"{_pct(summary['B1_GENERIC_DELIBERATION']['by_task'][task_id]['accuracy'])} | "
            f"{_pct(summary['OURS_PRAGMATIC_LOOP']['by_task'][task_id]['accuracy'])} | "
            f"{delta:+.3f} |"
        )
    lines.extend(
        [
            "",
            "## Locked gate",
            "",
        ]
    )
    for name, passed in result["hypotheses"].items():
        lines.append(f"- `{name}`: {'PASS' if passed else 'FAIL'}")
    lines.extend(
        [
            "",
            "## Honest interpretation",
            "",
            f"Authorized claim: {result['claim_authorized']}.",
            "",
            "The posthoc implementation-fidelity audit found complete Ours schemas in "
            f"`{result['posthoc_implementation_fidelity_audit']['ours_schema_complete_count']}/"
            f"{result['posthoc_implementation_fidelity_audit']['ours_schema_total']}` rows. "
            "Most violations omitted `pragmatic_target`. Therefore this run is evidence about "
            "the actual prompt behavior, not a clean causal test of a fully instantiated cognitive loop.",
            "",
            "This score does not evaluate whether the final Japanese reply makes a person feel understood. "
            "It also does not validate a persistent user model or Uruha persona. Public benchmark exposure "
            "during base-model pretraining cannot be excluded, and the project prompt differs from the "
            "paper's exact MCP implementation.",
            "",
            "## Reproducibility",
            "",
            f"- Protocol SHA-256: `{result['protocol_sha256']}`",
            f"- M13.1 amendment SHA-256: `{result['amendment_sha256']}`",
            f"- Case manifest SHA-256: `{result['manifest_sha256']}`",
            f"- Raw result SHA-256: `{result['raw_result_sha256']}`",
            "- Production memory writes: `0`",
        ]
    )
    return "\n".join(lines) + "\n"


def render_dashboard(result: dict[str, Any], *, stage: str = "M13") -> str:
    payload = json.dumps(result, ensure_ascii=False).replace("</", "<\\/")
    if result["decision"] in {"pass_narrow_pragmatic_gain", "pass_schema_enforced_pragmatic_gain"}:
        decision = "通過窄語用增益"
    elif result["summary"]["OURS_PRAGMATIC_LOOP"]["schema_contract_rate"] == 1.0:
        decision = "未通過：方向有利，但統計與跨類型穩定性不足"
    else:
        decision = "未通過：沒有勝過一般深思，且實作忠實度不足"
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{stage} · PUB Pragmatics</title>
<style>
:root{{--bg:#07101d;--panel:#101c2f;--line:#29415f;--text:#eef6ff;--muted:#94a9c2;--cyan:#4de3ff;--gold:#ffd166;--red:#ff6b7c;--green:#65e6a5}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 15% 0,#16345d 0,transparent 34%),var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}}
main{{max-width:1440px;margin:auto;padding:32px}} h1{{font-size:clamp(30px,5vw,62px);margin:0 0 8px}} h2{{font-size:21px;margin:0 0 18px}} .muted{{color:var(--muted)}}
.hero,.panel{{background:linear-gradient(145deg,rgba(19,35,58,.95),rgba(9,19,34,.94));border:1px solid var(--line);border-radius:22px;padding:24px;box-shadow:0 20px 55px #0007}}
.hero{{display:grid;grid-template-columns:1.4fr .8fr;gap:24px}} .decision{{font-size:28px;color:{'#65e6a5' if result['gate_passed'] else '#ff6b7c'};font-weight:800}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:18px}} .metric{{padding:18px;border:1px solid var(--line);border-radius:16px;background:#0b1728}} .big{{font-size:34px;font-weight:800}}
.flow{{display:grid;grid-template-columns:repeat(7,auto);gap:8px;align-items:center;margin:24px 0}} .node{{padding:14px;border:1px solid #35618d;background:#0c2038;border-radius:14px;text-align:center}} .arrow{{color:var(--cyan);font-size:22px}}
.bars{{display:grid;gap:12px}} .barrow{{display:grid;grid-template-columns:230px 1fr 72px;gap:10px;align-items:center}} .track{{height:18px;background:#07111f;border-radius:20px;overflow:hidden}} .fill{{height:100%;border-radius:20px;background:linear-gradient(90deg,var(--cyan),#8e7dff)}}
.tasks{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}} .task{{border:1px solid var(--line);border-radius:16px;padding:16px;background:#0a1627}} table{{border-collapse:collapse;width:100%}} th,td{{padding:10px;border-bottom:1px solid #233b57;text-align:left}}
.matrix{{display:grid;grid-template-columns:repeat(16,1fr);gap:5px}} .cell{{aspect-ratio:1;border-radius:5px;background:#24405f;cursor:pointer}} .cell.good{{background:var(--green)}} .cell.bad{{background:var(--red)}} .cell.split{{background:var(--gold)}}
select{{background:#0a1627;color:var(--text);border:1px solid var(--line);border-radius:9px;padding:8px}} pre{{white-space:pre-wrap;background:#07111e;padding:16px;border-radius:14px;color:#cfe7ff;max-height:360px;overflow:auto}} .boundary{{border-left:4px solid var(--gold);padding-left:16px}}
@media(max-width:850px){{.hero,.grid,.tasks{{grid-template-columns:1fr}}.flow{{grid-template-columns:1fr}}.arrow{{transform:rotate(90deg)}}.barrow{{grid-template-columns:1fr}}}}
</style></head><body><main>
<section class="hero"><div><div class="muted">{stage} · published external benchmark · 2026-08-17</div><h1>人說的，和人真正表達的，系統分得出來嗎？</h1><p>同一個 qwen3.5:9b、同一批 64 題。只改變回答前的認知程序。</p><div class="decision">{decision}</div></div><div class="panel"><div class="muted">Primary · Ours − Generic</div><div class="big">{result['comparisons']['ours_vs_generic']['accuracy_delta']*100:+.1f} pp</div><div>95% CI [{result['comparisons']['ours_vs_generic']['bootstrap_95_ci'][0]*100:+.1f}, {result['comparisons']['ours_vs_generic']['bootstrap_95_ci'][1]*100:+.1f}]</div><div>McNemar p={result['comparisons']['ours_vs_generic']['exact_mcnemar_pvalue']:.4f}</div></div></section>
<div class="flow"><div class="node">公開語用題</div><div class="arrow">→</div><div class="node">字面訊號</div><div class="arrow">→</div><div class="node">言外目標</div><div class="arrow">→</div><div class="node">答案</div></div>
<section class="grid" id="metrics"></section>
<section class="panel" style="margin-top:18px"><h2>整體準確率</h2><div class="bars" id="bars"></div></section>
<section class="panel" style="margin-top:18px"><h2>四種語用能力</h2><div class="tasks" id="tasks"></div></section>
<section class="panel" style="margin-top:18px;display:none" id="cross"></section>
<section class="panel" style="margin-top:18px"><h2>64 題逐題差異</h2><p class="muted">綠：Ours 對而 Generic 錯；紅：Ours 錯而 Generic 對；黃：兩者不同但同為對或錯。點格子看原題、內部分析和答案。</p><div class="matrix" id="matrix"></div><div style="margin-top:16px"><select id="condition"></select><pre id="case">點一個格子</pre></div></section>
<section class="panel boundary" style="margin-top:18px"><h2>實作忠實度與證據邊界</h2><p><b>Ours 完整認知 schema：</b>{result['posthoc_implementation_fidelity_audit']['ours_schema_complete_count']}/{result['posthoc_implementation_fidelity_audit']['ours_schema_total']}。答案可解析不代表認知步驟真的完整執行。</p><p><b>允許：</b>{html.escape(str(result['claim_authorized']))}</p><p><b>不允許：</b>不是讀心，不是人腦等價，不是長期人物理解，不是 Uruha 人格相似度，也不是「被理解感」的人類偏好證據。</p><p class="muted">公開題可能進過基礎模型預訓練；本研究使用 project-specific prompts 與單一凍結選項排列，並非原論文完整 PPA。</p></section>
</main><script id="data" type="application/json">{payload}</script><script>
const d=JSON.parse(document.getElementById('data').textContent); const names={{B0_DIRECT:'單純 LLM',B1_GENERIC_DELIBERATION:'一般深思',OURS_PRAGMATIC_LOOP:'語用迴路'}};
document.getElementById('metrics').innerHTML=Object.entries(d.summary).map(([k,v])=>`<div class="metric"><div class="muted">${{names[k]}}</div><div class="big">${{(v.accuracy*100).toFixed(1)}}%</div><div>完整 schema ${{(v.schema_contract_rate*100).toFixed(1)}}%</div><div>${{v.prompt_tokens.toLocaleString()}} prompt tokens · ${{v.latency_seconds.toFixed(1)}}s</div></div>`).join('');
document.getElementById('bars').innerHTML=Object.entries(d.summary).map(([k,v])=>`<div class="barrow"><b>${{names[k]}}</b><div class="track"><div class="fill" style="width:${{v.accuracy*100}}%"></div></div><span>${{(v.accuracy*100).toFixed(1)}}%</span></div>`).join('');
const taskNames={{'2':'婉轉／間接回答','6':'反諷或同意','12':'對話預設','13':'指涉解析'}};
document.getElementById('tasks').innerHTML=Object.keys(d.task_accuracy_delta_ours_minus_generic).map(t=>`<div class="task"><b>T${{t}} · ${{taskNames[t]}}</b><table><tr><td>單純 LLM</td><td>${{(d.summary.B0_DIRECT.by_task[t].accuracy*100).toFixed(1)}}%</td></tr><tr><td>一般深思</td><td>${{(d.summary.B1_GENERIC_DELIBERATION.by_task[t].accuracy*100).toFixed(1)}}%</td></tr><tr><td>語用迴路</td><td>${{(d.summary.OURS_PRAGMATIC_LOOP.by_task[t].accuracy*100).toFixed(1)}}%</td></tr></table></div>`).join('');
if(d.cross_split_stability){{const c=d.cross_split_stability,x=document.getElementById('cross');x.style.display='block';x.innerHTML=`<h2>跨樣本穩定性</h2><div class="grid"><div class="metric"><div class="muted">M13 Ours−Generic</div><div class="big">${{(c.m13_ours_minus_generic_accuracy*100).toFixed(1)}} pp</div><div>完整 schema ${{(c.m13_ours_schema_contract_rate*100).toFixed(1)}}%</div></div><div class="metric"><div class="muted">M14 Ours−Generic</div><div class="big">${{(c.m14_ours_minus_generic_accuracy*100).toFixed(1)}} pp</div><div>完整 schema ${{(c.m14_ours_schema_contract_rate*100).toFixed(1)}}%</div></div><div class="metric"><div class="muted">方向重現</div><div class="big">${{c.effect_direction_replicated?'YES':'NO'}}</div><div>不可混池兩個 fidelity 不同的 split</div></div></div>`;}}
const ids=[...new Set(d.rows.map(r=>r.sample_id))].sort(); const by=Object.fromEntries(d.rows.map(r=>[r.sample_id+'|'+r.condition,r])); let active=ids[0];
const matrix=document.getElementById('matrix'); matrix.innerHTML=ids.map(id=>{{const o=by[id+'|OURS_PRAGMATIC_LOOP'],g=by[id+'|B1_GENERIC_DELIBERATION'];const cls=o.correct&&!g.correct?'good':!o.correct&&g.correct?'bad':o.predicted_index!==g.predicted_index?'split':'';return `<div class="cell ${{cls}}" data-id="${{id}}" title="${{id}}"></div>`}}).join('');
const sel=document.getElementById('condition'); sel.innerHTML=Object.entries(names).map(([k,v])=>`<option value="${{k}}">${{v}}</option>`).join('');
function show(){{const r=by[active+'|'+sel.value];document.getElementById('case').textContent=`${{r.sample_id}} · ${{r.task_name}}\n\n${{r.pretext}}\nOPTIONS\n${{r.options.map((x,i)=>'['+i+'] '+x).join('\\n')}}\n\nCORRECT: [${{r.correct_index}}] ${{r.correct_answer}}\nPREDICTED: [${{r.predicted_index}}] ${{r.predicted_answer}}\n\nINTERNAL OUTPUT\n${{r.raw_response}}`;}};
matrix.addEventListener('click',e=>{{if(e.target.dataset.id){{active=e.target.dataset.id;show()}}}});sel.addEventListener('change',show);show();
</script></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not any((args.prepare, args.run, args.analyze, args.all)):
        parser.error("choose --prepare, --run, --analyze, or --all")
    if args.prepare or args.all:
        manifest = prepare_manifest()
        print(f"prepared {manifest['case_count']} cases at {MANIFEST_PATH}")
        print(f"manifest sha256 {sha256_file(MANIFEST_PATH)}")
    if args.run or args.all:
        raw = run_experiment()
        print(f"completed {len(raw['rows'])} rows at {RAW_RESULT_PATH}")
    if args.analyze or args.all:
        result = analyze()
        print(f"decision {result['decision']}")
        print(f"result {RESULT_PATH}")
        print(f"dashboard {DASHBOARD_PATH}")


if __name__ == "__main__":
    main()
