---
name: restart-protocol
description: Use when the player explicitly requests a restart or when you are about to call restart_game.
---

# Restart Protocol

## When to Apply

Apply this skill when:
- The player explicitly asks to restart/start over
- You are about to call `restart_game` for any reason (death, failure, or explicit request)

## Required Behavior

1. Output a brief, matter-of-fact restart narration (1-2 sentences).
2. Do NOT describe the starting location.
3. Do NOT include any "Wake up" text or new-game intro.
4. Call `restart_game` immediately.
5. Stop after the tool call—do not continue the scene.
