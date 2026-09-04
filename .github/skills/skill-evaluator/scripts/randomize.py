#!/usr/bin/env python3
"""Deterministic-but-unpredictable run order and blind A/B label mapping.

Derives its randomness from a per-evaluation seed (created on first use) combined
with the test id and repeat index, so every (test, run) pair gets an independent
assignment while the whole evaluation stays reproducible from the seed file.
"""
import argparse
import json
import pathlib
import random


def get_or_create_seed(seed_file: pathlib.Path) -> int:
    if seed_file.exists():
        return int(seed_file.read_text().strip())
    seed = random.SystemRandom().getrandbits(64)
    seed_file.parent.mkdir(parents=True, exist_ok=True)
    seed_file.write_text(str(seed))
    return seed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-file", required=True, help="Path to the evaluation's persistent seed file.")
    parser.add_argument("--tc", required=True, help="Test case id, e.g. TC-001.")
    parser.add_argument("--run", type=int, default=1, help="Repeat index (1 if repeats == 1).")
    parser.add_argument("--out", help="Optional path to write the mapping JSON to (also printed to stdout).")
    args = parser.parse_args()

    seed = get_or_create_seed(pathlib.Path(args.seed_file))
    rng = random.Random(f"{seed}:{args.tc}:{args.run}")

    run_first = rng.choice(["with-skill", "baseline"])
    with_skill_label = rng.choice(["A", "B"])
    baseline_label = "B" if with_skill_label == "A" else "A"

    mapping = {
        "test_id": args.tc,
        "run": args.run,
        "run_first": run_first,
        "condition_map": {with_skill_label: "with-skill", baseline_label: "baseline"},
    }

    if args.out:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(mapping, indent=2))

    print(json.dumps(mapping, indent=2))


if __name__ == "__main__":
    main()
