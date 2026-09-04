#!/usr/bin/env python3
"""Deterministic aggregation of skill-evaluator blind scores.

Reads every scores/*.json (excluding *.mapping.json), unmaps each run's Output
A/B labels back to with-skill/baseline using the run's own condition_map, and
writes evaluation-summary.json. This is the only place aggregate arithmetic
happens - the calling skill must not recompute these numbers itself.
"""
import argparse
import datetime
import json
import pathlib
import statistics
from collections import defaultdict

DIFF_EPSILON = 0.3  # smaller than this, on a 0-5 scale, counts as "no meaningful difference"
MIN_CASES_FOR_CONFIDENCE = 10


def load_scores(scores_dir: pathlib.Path):
    runs = []
    for f in sorted(scores_dir.glob("*.json")):
        if f.name.endswith(".mapping.json"):
            continue
        data = json.loads(f.read_text())
        cmap = data["condition_map"]
        with_skill_label = next(k for k, v in cmap.items() if v == "with-skill")
        baseline_label = next(k for k, v in cmap.items() if v == "baseline")
        runs.append({
            "test_id": data["test_id"],
            "run": data.get("run", 1),
            "with_skill_dims": data["scores"][with_skill_label],
            "baseline_dims": data["scores"][baseline_label],
        })
    return runs


def mean_or_none(values):
    return statistics.mean(values) if values else None


def stdev_or_none(values):
    return statistics.stdev(values) if len(values) > 1 else None


def classify_outcome(diff, with_skill_vals, baseline_vals):
    if len(with_skill_vals) > 1:
        spread = max(stdev_or_none(with_skill_vals) or 0, stdev_or_none(baseline_vals) or 0)
        if spread > DIFF_EPSILON and spread > abs(diff):
            return "inconclusive"
    if abs(diff) < DIFF_EPSILON:
        return "no meaningful difference"
    return "improved" if diff > 0 else "worse"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", help="Root directory for this evaluation run.")
    parser.add_argument("--pass-threshold", type=float, help="Override the plan's pass_threshold.")
    args = parser.parse_args()

    root = pathlib.Path(args.output_dir)
    plan_path = root / "evaluation-plan.json"
    category_by_id = {}
    pass_threshold = args.pass_threshold
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        category_by_id = {tc["id"]: tc["category"] for tc in plan.get("test_cases", [])}
        if pass_threshold is None:
            pass_threshold = plan.get("pass_threshold", 3.0)
    if pass_threshold is None:
        pass_threshold = 3.0

    runs = load_scores(root / "scores")
    by_test = defaultdict(list)
    for r in runs:
        by_test[r["test_id"]].append(r)

    per_test = []
    dim_totals = defaultdict(lambda: {"with_skill": [], "baseline": []})

    for test_id, test_runs in sorted(by_test.items()):
        with_skill_means = [mean_or_none(list(r["with_skill_dims"].values())) for r in test_runs]
        baseline_means = [mean_or_none(list(r["baseline_dims"].values())) for r in test_runs]
        for r in test_runs:
            for dim, score in r["with_skill_dims"].items():
                dim_totals[dim]["with_skill"].append(score)
            for dim, score in r["baseline_dims"].items():
                dim_totals[dim]["baseline"].append(score)

        with_skill_score = mean_or_none(with_skill_means)
        baseline_score = mean_or_none(baseline_means)
        diff = with_skill_score - baseline_score
        pct_diff = (diff / baseline_score * 100) if baseline_score else None
        with_skill_pass = with_skill_score >= pass_threshold
        baseline_pass = baseline_score >= pass_threshold

        entry = {
            "test_id": test_id,
            "category": category_by_id.get(test_id, "unknown"),
            "with_skill_score": round(with_skill_score, 3),
            "baseline_score": round(baseline_score, 3),
            "diff": round(diff, 3),
            "pct_diff": round(pct_diff, 1) if pct_diff is not None else None,
            "with_skill_pass": with_skill_pass,
            "baseline_pass": baseline_pass,
            "outcome": classify_outcome(diff, with_skill_means, baseline_means),
        }

        if len(test_runs) > 1:
            per_run_pass = [wm >= pass_threshold for wm in with_skill_means]
            entry["repeats"] = {
                "with_skill": {
                    "mean": round(with_skill_score, 3),
                    "min": round(min(with_skill_means), 3),
                    "max": round(max(with_skill_means), 3),
                    "stdev": round(stdev_or_none(with_skill_means), 3) if stdev_or_none(with_skill_means) is not None else None,
                },
                "baseline": {
                    "mean": round(baseline_score, 3),
                    "min": round(min(baseline_means), 3),
                    "max": round(max(baseline_means), 3),
                    "stdev": round(stdev_or_none(baseline_means), 3) if stdev_or_none(baseline_means) is not None else None,
                },
                "pass_fail_consistent": len(set(per_run_pass)) == 1,
            }

        per_test.append(entry)

    outcome_counts = {"improved": 0, "no meaningful difference": 0, "worse": 0, "inconclusive": 0}
    for e in per_test:
        outcome_counts[e["outcome"]] += 1

    by_category = defaultdict(lambda: {"with_skill": [], "baseline": []})
    for e in per_test:
        by_category[e["category"]]["with_skill"].append(e["with_skill_score"])
        by_category[e["category"]]["baseline"].append(e["baseline_score"])

    aggregate = {
        "avg_with_skill_score": round(mean_or_none([e["with_skill_score"] for e in per_test]) or 0, 3),
        "avg_baseline_score": round(mean_or_none([e["baseline_score"] for e in per_test]) or 0, 3),
        "with_skill_pass_rate": round(mean_or_none([1.0 if e["with_skill_pass"] else 0.0 for e in per_test]) or 0, 3),
        "baseline_pass_rate": round(mean_or_none([1.0 if e["baseline_pass"] else 0.0 for e in per_test]) or 0, 3),
        "improved_count": outcome_counts["improved"],
        "unchanged_count": outcome_counts["no meaningful difference"],
        "worse_count": outcome_counts["worse"],
        "inconclusive_count": outcome_counts["inconclusive"],
        "by_category": {
            cat: {
                "avg_with_skill_score": round(mean_or_none(v["with_skill"]), 3),
                "avg_baseline_score": round(mean_or_none(v["baseline"]), 3),
            }
            for cat, v in sorted(by_category.items())
        },
        "by_dimension": {
            dim: {
                "avg_with_skill_score": round(mean_or_none(v["with_skill"]), 3),
                "avg_baseline_score": round(mean_or_none(v["baseline"]), 3),
            }
            for dim, v in sorted(dim_totals.items())
        },
    }

    num_cases = len(per_test)
    max_repeats = max((len(v) for v in by_test.values()), default=0)
    notes = []
    if num_cases < MIN_CASES_FOR_CONFIDENCE:
        notes.append(f"Only {num_cases} test case(s) - treat aggregate numbers as directional, not statistically significant.")
    if max_repeats < 2:
        notes.append("No repeated runs - variability/consistency cannot be assessed.")

    summary = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pass_threshold": pass_threshold,
        "sample_size_note": " ".join(notes) if notes else "Sample size sufficient for a rough directional signal.",
        "per_test": per_test,
        "aggregate": aggregate,
    }

    out_path = root / "evaluation-summary.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
