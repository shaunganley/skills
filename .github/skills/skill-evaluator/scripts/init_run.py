#!/usr/bin/env python3
"""Scaffold the fixed skill-evaluation directory tree for a skill-evaluator run."""
import argparse
import pathlib

TREE = [
    "test-cases",
    "expected",
    "results/with-skill",
    "results/baseline",
    "scores",
    "recommendations",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", help="Root directory for this evaluation run.")
    args = parser.parse_args()

    root = pathlib.Path(args.output_dir)
    for rel in TREE:
        (root / rel).mkdir(parents=True, exist_ok=True)

    print(f"Scaffolded {root} with: {', '.join(TREE)}")


if __name__ == "__main__":
    main()
