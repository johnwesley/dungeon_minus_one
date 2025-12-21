---
name: npc-blocking
description: Use when an NPC guards an exit, item, or action. Handles bypass flags and NPC behavior enforcement.
---

# NPC Blocking & Bypass Logic

## When to Apply

Apply this skill when:
- The player is in a location with NPCs
- An NPC guards an exit, item, or action
- The player attempts to pass a guarded area
- The player interacts with or attacks an NPC

## Bypass Flags

Before applying NPC blocking behavior, check the current `flags` in game state. If any of these bypass flags are set, the NPC has already been dealt with and **no longer blocks passage or guards items**:

| Flag | NPC | Effect |
|------|-----|--------|
| `troll_incapacitated`, `troll_defeated`, or `troll_persuaded` | Troll | Allows passage |
| `cyclops_defeated`, `cyclops_confused`, or `cyclops_distracted` | Cyclops | Allows passage |
| `thief_defeated` or `thief_distracted` | Thief | Allows taking chalice |
| `bat_pacified` or `bat_persuaded` | Bat | Allows taking jade figurine |
| `spirits_banished` | Spirits | Allows passage to land_of_the_dead |

## Critical Rule: Bypass Flags Do NOT Remove Items

A bypass flag only removes blocking behavior. It does **NOT** mean the treasure was taken.

Never claim an item was already taken unless:
- Its `id` is in `inventory`
- Its `id` is in `flags.trophy_case`
- It is present in `flags.dropped_items[current_location]`

If the item is listed in the location's `interactables` and is not in those places, it is still present and can be taken.

## NPC Behavior Field

If an NPC in the current location data has a `behavior` field AND no bypass flag is set for that NPC, you MUST follow its instructions exactly for:
- Reactions to player actions
- Combat behavior
- Guarding items or exits

The `behavior` field contains specific instructions that override general game logic.

## Checking NPC Status

When the player enters a location with NPCs or attempts an action that might be blocked:

1. Call `get_game_state` to check current flags
2. Check if any relevant bypass flag is set
3. If bypass flag is set: NPC does not block, proceed normally
4. If no bypass flag: Apply NPC behavior rules

## Example: Troll Scenario

**Player at troll_room, tries to go east**

1. Check `flags.troll_incapacitated`, `flags.troll_defeated`, `flags.troll_persuaded`
2. If any is `true`: Allow passage, describe troll as incapacitated/defeated
3. If none set: Troll blocks passage, follow behavior instructions

## NPC Combat & Resolution

When the player defeats or bypasses an NPC:

1. Set the appropriate bypass flag via `update_game_state`
2. Describe the outcome
3. The NPC no longer blocks on future turns

Example state update:
```json
{
  "flags": {
    "troll_defeated": true
  }
}
```

## Never Do

- Never let an NPC block if their bypass flag is set
- Never claim an NPC took an item
- Never invent NPC behavior not in the data
- Never skip checking flags before applying blocking
