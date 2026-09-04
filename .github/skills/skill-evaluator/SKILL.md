---
name: skill-evaluator
description: Evaluates whether a target skill measurably improves agent output, by running identical test cases with and without the skill enabled and blind-scoring both against one rubric. User-invoked only.
disable-model-invocation: true
---

Evaluates a target skill by running the same test cases twice — once with it enabled, once without — and blind-scoring both against one rubric, so a skill that only looks helpful gets caught.

## Core principle

Never assume the skill helps. Every test case must land on one of **improved**, **no meaningful difference**, **worse**, or **inconclusive** — decided by a blind comparison, not by grading the skill-enabled output alone.

## Inputs

Gather these; ask the user only for what's genuinely missing.

- **target skill** (required) — path to the skill directory or its `SKILL.md`.
- **test-case count** — if not supplied, ask: "How many test cases would you like the evaluation to include?" Guidance: 5 = smoke test, 10 = normal (default), 20+ = broad. Recommend repeats > 1 when the target skill's output is non-deterministic.
- **fixtures path** — optional supporting project files.
- **categories** — optional subset of [`reference/categories.md`](reference/categories.md); default is whichever categories fit the target skill's actual behaviour.
- **repeats per test case** — default 1.
- **model / agent config** — passed identically to both conditions; default whatever `runSubagent` uses.
- **output directory** — default `skill-evaluation/`.
- **existing test cases** — if supplied, skip Step 3 and validate them against [`schemas/test-case.schema.json`](schemas/test-case.schema.json) instead of generating new ones.
- **pass threshold** — default: mean dimension score ≥ 3 ("acceptable").

Warn, but proceed, above 20 test cases or 3 repeats — the fan-out is `cases × 2 conditions × repeats` `runSubagent` calls plus one evaluator call per case-repeat.

## Steps

### 1. Inspect the target skill

Read the target's `SKILL.md` and everything it references — scripts, templates, examples, schemas. Read-only: never edit the target skill. Write `<output>/skill-profile.md`: stated purpose, intended users, expected inputs/outputs, workflow, tools/scripts used, constraints, likely failure modes, in-scope vs. out-of-scope scenarios. Done when every file the target `SKILL.md` points at has been read, not just skimmed.

### 2. Resolve inputs

Fill in the input list above.

### 3. Generate the evaluation plan

Skip if the user supplied existing test cases (validate those against the schema instead). Otherwise, using the profile from Step 1 and [`reference/categories.md`](reference/categories.md), write one `<output>/test-cases/TC-NNN.json` per case (schema: [`schemas/test-case.schema.json`](schemas/test-case.schema.json)) and a `<output>/evaluation-plan.json` (schema: [`schemas/evaluation-plan.schema.json`](schemas/evaluation-plan.schema.json)) indexing them with their category. Balance categories to what the profile says the skill actually does; don't force a category the skill can't plausibly hit. Done when every planned case has a file conforming to the schema.

### 4. Generate expected outputs

For each test case, write `<output>/expected/TC-NNN.md`: required content, optional content, prohibited content, required structure, factual constraints, acceptable variation. Derive these from the test's own objective and the skill profile — never by running the target skill and calling its answer correct. Done when every case has an expected-output file that cites no output from the target skill as its source.

### 5. Scaffold the run directory

Run:

```
python3 .github/skills/skill-evaluator/scripts/init_run.py <output>
```

before executing anything, to create the fixed tree (`results/with-skill/`, `results/baseline/`, `scores/`, `recommendations/`).

### 6. Execute both conditions

For each test case × repeat:

1. Run `python3 .github/skills/skill-evaluator/scripts/randomize.py --seed-file <output>/.seed --tc <TC-ID> --run <K> --out <output>/scores/TC-NNN.mapping.json` to get the run order and the Output-A/B label mapping for this case. The mapping file is kept out of the evaluator's sight until after scoring.
2. Spawn the **with-skill** condition via `runSubagent`: prompt = test prompt + fixtures + the target skill's `SKILL.md` and every file it references, inlined in full, with an instruction to follow it.
3. Spawn the **baseline** condition via `runSubagent`: identical prompt + fixtures, explicit statement that it has no access to the target skill or its supporting files. Same model/tools as with-skill.
4. Capture, for each condition: final output, tool calls, errors/warnings, status, duration if available, artefacts — into `<output>/results/{with-skill,baseline}/TC-NNN/` (or `.../run-K/` when repeats > 1) as `output.md` + `meta.json`.

If the target skill is itself conversational (it mandates asking the user questions before proceeding), a subagent can't pause for a human. Give both conditions a written brief of pre-answered facts and instruct them to self-resolve any question immediately, explicitly flagging anything the brief doesn't cover as an open assumption rather than inventing it — never silently invent the answer.

Known limitation: a subagent's tool access may not perfectly mirror a top-level session (for example, it may not itself be able to spawn further subagents) — note this in the final report if it affected a case.

Done when both conditions have `output.md` + `meta.json` for every test case × repeat.

### 7. Blind scoring

The `results/with-skill/` and `results/baseline/` paths from Step 6 name the condition in the path itself — pointing an evaluator straight at them breaks blinding. First build `<output>/results/blind/TC-NNN/{A,B}/` per the Step 6 mapping: copy each condition's `output.md` and artefacts across, then strip any literal `with-skill`/`baseline` occurrences from the copies (e.g. `sed -i '' 's/with-skill/condition-1/g; s/baseline/condition-2/g' <copies>`). Only ever point the evaluator at these scrubbed copies.

Per test case × repeat, spawn one evaluator `runSubagent` call with: the expected-output spec from Step 4, the relevant rubric subset from [`reference/dimensions.md`](reference/dimensions.md), and the two captured outputs labelled only "Output A" / "Output B" per the Step 6 mapping — no mention of which is skill-enabled. Score every dimension 0–5 with a one-line, evidence-based justification quoting the actual output, and separate factual correctness, stylistic quality, target-skill compliance, and task success. Write `<output>/scores/TC-NNN.json` (schema: [`schemas/score.schema.json`](schemas/score.schema.json)), still in A/B terms. Only after it is written, unmap A/B back to with-skill/baseline using the Step 6 mapping file — never before scoring. Done when every case × repeat has a score file and its unmapped condition labels recorded.

### 8. Aggregate

Run:

```
python3 .github/skills/skill-evaluator/scripts/aggregate.py <output>
```

to compute every per-test and aggregate number — diffs, percentage diffs, outcomes, pass rates, by-category and by-dimension breakdowns, and mean/min/max/variability when repeats > 1. Writes `<output>/evaluation-summary.json` (schema: [`schemas/evaluation-summary.schema.json`](schemas/evaluation-summary.schema.json)). The script is the source of truth for this arithmetic — do not compute it yourself; it already refuses to claim significance when the sample is too small.

### 9. Diagnose failures

For every case where the outcome is "worse" or "inconclusive", or either condition missed its threshold, assign a cause from [`reference/failure-causes.md`](reference/failure-causes.md), labelled explicitly **likely** (inferred) or **proven** (directly evidenced in the transcript).

### 10. Recommend

Write `<output>/recommendations/proposed-skill-updates.md`: prioritised, one entry per root cause (schema: [`schemas/recommendation.schema.json`](schemas/recommendation.schema.json)) — affected test cases, observed problem, evidence, root cause, proposed change, target file/section in the *target* skill, an example revision, expected benefit, possible side effects, priority. Do not edit the target skill itself unless the user explicitly asks afterward.

### 11. Assemble the report

Fill [`reference/report-template.md`](reference/report-template.md) using `evaluation-summary.json`, the score files, and the recommendations, and write `<output>/evaluation-report.md`. Done when every section of the template is populated and no placeholder text remains.
