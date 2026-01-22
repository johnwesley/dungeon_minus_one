from dataclasses import dataclass
import re


MAX_PLAYER_INPUT_CHARS = 1000

DIRECTION_WORDS = {
    "north",
    "south",
    "east",
    "west",
    "n",
    "s",
    "e",
    "w",
    "ne",
    "nw",
    "se",
    "sw",
    "northeast",
    "northwest",
    "southeast",
    "southwest",
    "up",
    "down",
    "in",
    "out",
    "inside",
    "outside",
}

COMMAND_VERBS = {
    "go",
    "move",
    "enter",
    "exit",
    "leave",
    "take",
    "get",
    "grab",
    "drop",
    "attack",
    "hit",
    "kill",
    "fight",
    "open",
    "close",
    "unlock",
    "lock",
    "turn",
    "light",
    "look",
    "examine",
    "read",
    "use",
    "push",
    "pull",
    "climb",
    "inventory",
    "equip",
    "wear",
    "remove",
    "say",
    "talk",
    "ask",
    "give",
    "throw",
    "wait",
}

COMMAND_WORDS = COMMAND_VERBS | DIRECTION_WORDS

LIST_PREFIX_RE = re.compile(r"^\s*(?:\d+[\).]|[-*])\s+")
HARD_SEPARATORS_RE = re.compile(r"\s*(?:;|&&|\|\|?)\s*")
SOFT_SEPARATORS_RE = re.compile(r"\b(?:then|and then|after that|next|afterwards)\b")


@dataclass(frozen=True)
class InputGuardResult:
    soft_reject: bool
    reason: str | None = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _is_command_like(segment: str) -> bool:
    cleaned = LIST_PREFIX_RE.sub("", segment.strip().lower())
    if not cleaned:
        return False
    tokens = _tokenize(cleaned)
    if not tokens:
        return False

    first = tokens[0]
    if first in COMMAND_WORDS:
        return True

    if first in {"i", "we"}:
        for token in tokens[1:6]:
            if token in COMMAND_WORDS:
                return True

    return False


def _count_command_words(text: str) -> int:
    return sum(1 for token in _tokenize(text) if token in COMMAND_WORDS)


def has_multiple_commands(message: str) -> bool:
    text = message.strip().lower()
    if not text:
        return False

    lines = [line for line in re.split(r"[\r\n]+", text) if line.strip()]
    if len(lines) >= 2:
        command_lines = sum(1 for line in lines if _is_command_like(line))
        bullet_lines = sum(1 for line in lines if LIST_PREFIX_RE.match(line))
        if command_lines >= 2:
            return True
        if bullet_lines >= 2 and command_lines >= 1:
            return True

    segments = [seg for seg in re.split(HARD_SEPARATORS_RE, text) if seg.strip()]
    if len(segments) >= 2:
        command_segments = sum(1 for seg in segments if _is_command_like(seg))
        if command_segments >= 2:
            return True

    if SOFT_SEPARATORS_RE.search(text):
        soft_segments = [seg for seg in re.split(SOFT_SEPARATORS_RE, text) if seg.strip()]
        if sum(1 for seg in soft_segments if _is_command_like(seg)) >= 2:
            return True

    command_count = _count_command_words(text)
    if command_count >= 3:
        return True

    if command_count >= 2 and ("," in text or re.search(r"\b(?:and|then)\b", text)):
        return True

    return False


def evaluate_player_input(message: str) -> InputGuardResult:
    trimmed = message.strip()
    if not trimmed:
        return InputGuardResult(False, None)

    if len(trimmed) > MAX_PLAYER_INPUT_CHARS:
        return InputGuardResult(True, "too_long")

    if has_multiple_commands(trimmed):
        return InputGuardResult(True, "multiple_commands")

    return InputGuardResult(False, None)
