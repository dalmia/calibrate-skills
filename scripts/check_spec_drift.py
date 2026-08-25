#!/usr/bin/env python3
"""Detect drift between the skills and the live Calibrate OpenAPI spec.

The skills are hand-written prose that hardcode API operations and payload
shapes. They cannot be regenerated from the spec, but they CAN be checked
against it: this script asserts that every operation and schema field the skills
depend on still exists. Run it against a freshly-published `openapi.json`; it is
the guard that would have caught the annotation payload rename.

Usage:
    python3 scripts/check_spec_drift.py --spec openapi.json [--report SPEC_DRIFT.md]

Exit codes: 0 = no drift, 1 = drift found (report written), 2 = usage/spec error.

Declare a new dependency below whenever a SKILL.md starts relying on a new
operation or payload field, so the guard grows with the skills.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Operations the skills invoke, keyed by a stable operationId prefix. If the
# backend renames or drops one, the referencing skill is stale.
REQUIRED_OPERATIONS = {
    "create_agent_endpoint": "agents create (connect-agent)",
    "verify_agent_connection": "agents verify-connection (connect-agent)",
    "resolve_agent_names": "agents resolve (connect-agent)",
    "create_test_endpoint": "tests create (build-test-suite)",
    "bulk_upload_tests": "tests bulk-create (build-test-suite, import-dataset)",
    "create_agent_test_links": "agent-tests link (run-tests)",
    "run_agent_test": "agent-tests run (run-tests)",
    "get_agent_test_run_status": "agent-tests get-run (run-tests)",
    "run_agent_benchmark": "agent-tests benchmark (benchmark-models)",
    "get_benchmark_status": "agent-tests get-benchmark (benchmark-models)",
    "create_evaluator_endpoint": "evaluators create (design-evaluator)",
    "create_version": "evaluators create-version (iterate-evaluator)",
    "create_annotation_task_endpoint": "annotation-tasks create (calibrate-evaluator)",
    "bulk_create_items": "annotation-tasks add-items (calibrate-evaluator)",
    "start_evaluator_run": "annotation-tasks create-evaluator-run (calibrate-evaluator)",
    "task_agreement": "annotation-tasks get-agreement (calibrate-evaluator)",
    "task_summary": "annotation-tasks get-summary (calibrate-evaluator)",
}

# Schema fields the skills document verbatim (config-shapes.md + SKILL bodies).
# (schema_name, field) -> why it matters.
REQUIRED_SCHEMA_FIELDS = {
    ("BulkItemsRequest", "items"): "add-items --items array",
    ("BulkItemsRequest", "annotator_id"): "--annotator-id flag",
    ("AnnotationItemPayload", "payload"): "item.payload (name required)",
    ("AnnotationItemPayload", "annotations"): "item.annotations map (value/reasoning)",
}


def load_spec(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"error: cannot read spec {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)


def operation_ids(spec: dict) -> set[str]:
    ids: set[str] = set()
    for item in spec.get("paths", {}).values():
        for method, op in item.items():
            if method in {"get", "post", "put", "patch", "delete"} and isinstance(op, dict):
                if op.get("operationId"):
                    ids.add(op["operationId"])
    return ids


def schema_props(spec: dict, name: str) -> set[str] | None:
    schema = spec.get("components", {}).get("schemas", {}).get(name)
    if schema is None:
        return None
    return set((schema.get("properties") or {}).keys())


def main() -> int:
    ap = argparse.ArgumentParser(description="Detect skills-vs-spec drift.")
    ap.add_argument("--spec", required=True, help="path to openapi.json")
    ap.add_argument("--report", default="SPEC_DRIFT.md", help="drift report to write on drift")
    args = ap.parse_args()

    spec = load_spec(Path(args.spec))
    ids = operation_ids(spec)
    drifts: list[str] = []

    for prefix, where in REQUIRED_OPERATIONS.items():
        if not any(oid.startswith(prefix) for oid in ids):
            drifts.append(f"operation `{prefix}*` missing from spec — used by {where}")

    for (schema, field), where in REQUIRED_SCHEMA_FIELDS.items():
        props = schema_props(spec, schema)
        if props is None:
            drifts.append(f"schema `{schema}` missing from spec — used by {where}")
        elif field not in props:
            drifts.append(f"`{schema}.{field}` missing from spec — used by {where}")

    report = Path(args.report)
    if not drifts:
        report.unlink(missing_ok=True)
        print("no drift: all referenced operations and payload fields present.")
        return 0

    lines = [
        "# Spec drift detected",
        "",
        "The published Calibrate OpenAPI spec no longer matches what these skills",
        "document. Update the affected `SKILL.md` / reference files, then clear this",
        "file. Each line names the missing operation/field and the skill relying on it.",
        "",
    ]
    lines += [f"- {d}" for d in drifts]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"drift found ({len(drifts)}); wrote {report}:", file=sys.stderr)
    for d in drifts:
        print(f"  - {d}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
