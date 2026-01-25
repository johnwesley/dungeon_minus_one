# Dungeon-1 Game Skills

This directory contains modular game mechanic skills that are concatenated into the system prompt.

## Overview

Skills decompose the narrator's game logic into 9 focused instruction sets. Each skill handles a specific game mechanic, allowing Claude to apply relevant rules based on player actions.

When `SKILLS_ENABLED=true`, all SKILL.md files are loaded and appended to the narrator prompt at runtime.

## Skills

| Skill | Description |
|-------|-------------|
| `movement-resolution` | Location movement, direction validation, exit checking |
| `inventory-management` | Take/drop/inspect items, container logic, dropped item persistence |
| `npc-blocking` | NPC guards, bypass flags, behavior enforcement |
| `lock-and-gate-resolution` | Grating lock, skeleton key, lock state tracking |
| `environmental-state-water` | Dam/reservoir water level mechanics |
| `victory-and-trophy` | Trophy case deposits, treasure tracking, victory sequence |
| `darkness-and-grue` | Light sources, requires_light locations, grue death |
| `written-materials` | Verbatim quoting of written content |
| `gas-room-hazard` | Coal gas explosion, electric light switches |

## File Structure

```
skills/
├── README.md                    # This file
├── movement-resolution/
│   └── SKILL.md
├── inventory-management/
│   └── SKILL.md
├── gas-room-hazard/
│   └── SKILL.md
└── ... (6 more skill directories)
```

## SKILL.md Format

Each skill uses YAML frontmatter (metadata) followed by instructions:

```markdown
---
name: skill-name
description: One-line description for Claude to decide when to apply this skill.
---

# Skill Name

## When to Apply
[Trigger conditions]

## Rules
[Step-by-step logic]

## Required Tool Calls
[Which tools to call and when]
```

The YAML frontmatter is stripped when loading - only the body content is included in the prompt.

## Configuration

Add to your `.env` file:

```bash
# Enable skills (default: false)
SKILLS_ENABLED=true
```

### Quick Start

1. **Enable the feature flag** in `.env`:
   ```bash
   SKILLS_ENABLED=true
   ```

2. **Restart the server:**
   ```bash
   make run
   ```

### Disabling Skills

To disable skills and use only the base narrator prompt:

```bash
SKILLS_ENABLED=false
```

Or simply remove/comment out `SKILLS_ENABLED` from `.env` (defaults to false).

## How It Works

When skills are enabled, the system:

1. Loads the base `prompts/narrator.md` prompt
2. Loads all `skills/*/SKILL.md` files
3. Strips YAML frontmatter from each skill
4. Concatenates everything into the system prompt

This approach has zero latency overhead compared to API-based skill loading.
