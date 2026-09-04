#!/usr/bin/env python3
"""Generate docs/index.md listing every skill's name and description.

Scans the repo for SKILL.md files, reads their YAML front matter (name,
description), and renders a Markdown page that GitHub Pages builds with
its built-in Jekyll pipeline (no custom HTML/build step required). Run
this whenever skills change, or let the "Update skills page" workflow
run it automatically.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
REPO_URL = "https://github.com/shaunganley/skills"


def parse_front_matter(text: str) -> dict:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def find_skills():
    skills = []
    for skill_md in sorted(REPO_ROOT.glob("**/SKILL.md")):
        if ".git" in skill_md.parts:
            continue
        fields = parse_front_matter(skill_md.read_text(encoding="utf-8"))
        name = fields.get("name", skill_md.parent.name)
        description = fields.get("description", "")
        rel_dir = skill_md.parent.relative_to(REPO_ROOT)
        skills.append({"name": name, "description": description, "path": str(rel_dir)})
    return skills


def escape_pipes(text: str) -> str:
    return text.replace("|", "\\|")


def render_markdown(skills) -> str:
    count = len(skills)
    rows = "\n".join(
        f"| [{escape_pipes(s['name'])}]({REPO_URL}/tree/main/{s['path']}) | {escape_pipes(s['description'])} |"
        for s in skills
    )
    return f"""---
title: Skills
---

# Skills

A repo for useful skills &mdash; {count} skill{'s' if count != 1 else ''} available.

| Skill | Description |
| --- | --- |
{rows}

*Generated from `SKILL.md` files in the repo. See the [source repository]({REPO_URL}).*
"""


def main():
    skills = find_skills()
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.md").write_text(render_markdown(skills), encoding="utf-8")
    print(f"Wrote docs/index.md with {len(skills)} skill(s).")


if __name__ == "__main__":
    main()
