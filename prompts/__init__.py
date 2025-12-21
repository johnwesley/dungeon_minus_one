from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent
SKILLS_DIR = PROMPTS_DIR.parent / "skills"


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    """Load a prompt file by name (without .md extension)."""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {name}")
    return prompt_path.read_text(encoding="utf-8").strip()


def render_prompt(name: str, **variables) -> str:
    """Load prompt and substitute {{KEY}} placeholders."""
    prompt = load_prompt(name)
    for key, value in variables.items():
        prompt = prompt.replace("{{" + key.upper() + "}}", str(value))
    return prompt


@lru_cache(maxsize=1)
def load_all_skills() -> str:
    """Load all skill files and concatenate into a single string.

    Returns:
        Concatenated skill content with section headers.
    """
    if not SKILLS_DIR.exists():
        return ""

    skills_content = []

    # Get all skill directories sorted by name
    skill_dirs = sorted([
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    ])

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8").strip()

        # Remove YAML frontmatter if present (it's metadata, not instructions)
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx != -1:
                content = content[end_idx + 3:].strip()

        skills_content.append(content)

    return "\n\n".join(skills_content)


# Prompt name constants
NARRATOR_PROMPT = "narrator"
