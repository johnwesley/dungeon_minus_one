from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


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


# Prompt name constants
NARRATOR_PROMPT = "narrator"
