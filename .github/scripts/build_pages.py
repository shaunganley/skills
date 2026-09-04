#!/usr/bin/env python3
"""Generate docs/index.html listing every skill's name and description.

Scans the repo for SKILL.md files, reads their YAML front matter (name,
description), and renders a static HTML page. Run this whenever skills
change, or let the "Deploy GitHub Pages" workflow run it automatically.
"""
import html
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


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


def render_html(skills) -> str:
    rows = "\n".join(
        f"""      <tr>
        <td><a href="https://github.com/shaunganley/skills/tree/main/{html.escape(s['path'])}">{html.escape(s['name'])}</a></td>
        <td>{html.escape(s['description'])}</td>
      </tr>"""
        for s in skills
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Skills</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
           max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #1f2328; }}
    h1 {{ border-bottom: 1px solid #d0d7de; padding-bottom: 0.5rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
    th, td {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid #d0d7de; vertical-align: top; }}
    th {{ background: #f6f8fa; }}
    a {{ color: #0969da; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .count {{ color: #57606a; font-size: 0.95rem; }}
    footer {{ margin-top: 2rem; color: #57606a; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>Skills</h1>
  <p class="count">A repo for useful skills &mdash; {len(skills)} skill{'s' if len(skills) != 1 else ''} available.</p>
  <table>
    <thead>
      <tr><th>Skill</th><th>Description</th></tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
  <footer>Generated from <code>SKILL.md</code> files in the repo. See the <a href="https://github.com/shaunganley/skills">source repository</a>.</footer>
</body>
</html>
"""


def main():
    skills = find_skills()
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(render_html(skills), encoding="utf-8")
    print(f"Wrote docs/index.html with {len(skills)} skill(s).")


if __name__ == "__main__":
    main()
