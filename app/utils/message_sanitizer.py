from typing import Optional


INTERNAL_MARKERS = (
    "\n\n---\n[State:",
    "\n\n---\n[Tools used:",
)


def strip_internal_markers(content: Optional[str]) -> str:
    """Remove internal state/tool markers from user-facing content."""
    if not content:
        return ""
    for marker in INTERNAL_MARKERS:
        if marker in content:
            return content.split(marker)[0]
    return content
