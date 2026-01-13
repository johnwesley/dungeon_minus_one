#!/usr/bin/env python3
"""Compile skill files into a single prompt artifact.

Usage:
  python scripts/compile_skills.py
"""

from __future__ import annotations

from pathlib import Path


def _strip_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return content
    return content[end_idx + 3 :].strip()


def compile_skills() -> str:
    root = Path(__file__).resolve().parent.parent
    skills_dir = root / "skills"

    if not skills_dir.exists():
        return ""

    skill_dirs = sorted(
        d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    )

    skills_content: list[str] = []
    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8").strip()
        content = _strip_frontmatter(content)
        skills_content.append(content)

    return "\n\n".join(skills_content)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    output_path = root / "prompts" / "skills_compiled.md"
    compiled = compile_skills()

    output_path.write_text(compiled, encoding="utf-8")
    print(f"Wrote {output_path} ({len(compiled)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
