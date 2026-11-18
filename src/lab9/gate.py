"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def _ratchet_problems(spec: dict, base_spec: dict) -> list[str]:
    problems = []
    for section, key_fields in (("metrics", ("id",)), ("slices", ("name", "metric"))):
        current_rules = {
            tuple(rule[field] for field in key_fields): rule for rule in spec.get(section, [])
        }
        for old in base_spec.get(section, []):
            key = tuple(old[field] for field in key_fields)
            label = f"ratchet {section}/{ '/'.join(key)}"
            new = current_rules.get(key)
            if new is None:
                problems.append(f"{label}: removed")
                continue
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"{label}: no longer blocking")
            old_limits = old.get("threshold", {}) if section == "metrics" else old
            new_limits = new.get("threshold", {}) if section == "metrics" else new
            for field in ("min", "max", "max_increase"):
                if field not in old_limits:
                    continue
                previous, value = old_limits[field], new_limits.get(field)
                if value is None or not isfinite(value) or (
                    value < previous if field == "min" else value > previous
                ):
                    problems.append(f"{label}: weakened {field}")
            if old_limits.get("no_significant_drop") and not new_limits.get("no_significant_drop"):
                problems.append(f"{label}: removed no_significant_drop")
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = {metric["id"] for metric in spec["metrics"] if metric["id"] in GRADERS}
    coverage = []
    for label, report in (("PR", pr), ("baseline", base)):
        manifest = report["manifest"]
        rows = report["rows"]
        seeds = set(manifest["seeds"])
        if len(rows) != manifest["items"] * len(manifest["seeds"]):
            problems.append(f"{label}: row count does not match manifest items × seeds")
        if not seeds or len(seeds) != len(manifest["seeds"]):
            problems.append(f"{label}: manifest seeds are empty or duplicated")
        if report.get("evaluator_failures"):
            problems.append(f"{label}: evaluator_failures is non-empty")
        for metric, value in report["metrics"].items():
            if isinstance(value, (int, float)) and not isfinite(value):
                problems.append(f"{label}: non-finite aggregate for {metric}")

        pairs = {}
        for row in rows:
            pair = row["item_id"], row["seed"]
            if pair in pairs:
                problems.append(f"{label}: duplicate item/seed {pair}")
            pairs[pair] = frozenset(row.get("slices") or [])
            for metric in sorted(graded):
                value = row.get(metric)
                if not isinstance(value, (int, float)) or not isfinite(value):
                    problems.append(f"{label}: missing or invalid {metric} for {pair}")

        items = {item for item, _ in pairs}
        if len(items) != manifest["items"] or pairs.keys() != {(item, seed) for item in items for seed in seeds}:
            problems.append(f"{label}: item/seed coverage does not match manifest")
        coverage.append(pairs)

    pr_pairs, base_pairs = coverage
    if pr_pairs.keys() != base_pairs.keys():
        problems.append("PR item/seed pairs differ from baseline")
    changed_slices = {item for item, seed in pr_pairs.keys() & base_pairs.keys()
                      if pr_pairs[item, seed] != base_pairs[item, seed]}
    if changed_slices:
        problems.append(f"PR slice tags differ from baseline for {', '.join(sorted(changed_slices))}")

    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        problems.extend(_ratchet_problems(spec, base_spec))
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bootstrap = spec.get("bootstrap", {})
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        check_id = f"slice:{name}/{metric}"
        current = per_item(pr, metric, slice_name=name)
        floor = rule.get("min")
        value = sum(current.values()) / len(current) if current else None
        failed = value is None or (floor is not None and value < floor)
        details = [f"value={value:.3f}" if value is not None else "missing PR scores"]
        if floor is not None:
            details.append(f"min={floor:g}")

        if current and rule.get("no_significant_drop"):
            baseline = per_item(base, metric, slice_name=name)
            keys = sorted(current.keys() & baseline.keys())
            if not keys:
                failed = True
                details.append("no paired baseline scores")
            else:
                delta, lo, hi = stats.paired_bootstrap(
                    [current[key] for key in keys],
                    [baseline[key] for key in keys],
                    n_resamples=bootstrap.get("n_resamples", 1000),
                    rng=bootstrap.get("rng", 2027),
                    confidence=bootstrap.get("confidence", 0.95),
                )
                details.append(f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]")
                failed |= hi < 0

        blocking = rule.get("blocking", False)
        if failed and blocking:
            blocked.append(check_id)
        verdict = ("BLOCK" if blocking else "warn") if failed else "ok"
        lines.append(f"  {check_id}  {'  '.join(details)}  {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
