---
name: darkness-and-grue
description: Use when entering dark locations or interacting with light sources. Handles the grue mechanic and player death in darkness.
---

# Darkness, Light, and Grue

## When to Apply

Apply this skill when:
- The player moves to a new location
- The location has `requires_light: true`
- The player interacts with light sources (lantern, torch)
- The player is in darkness (`flags.in_darkness` is true)

## Light Sources

| Item | ID | Behavior |
|------|-----|----------|
| Brass Lantern | `brass_lantern` | Can be turned on/off. Found in living_room. |
| Ivory Torch | `ivory_torch` | Always lit when held. A treasure from torch_room. |
| Old Lantern | `old_lantern` | Useless. Provides no light. |

## Checking for Light

When the player moves to a new location:

1. Check if `requires_light` is `true` in the location data
2. If yes, check for an active light source:
   - `flags.lantern_lit` is `true` (brass lantern is on), OR
   - `ivory_torch` is in inventory (always lit)
3. If player has light: Proceed normally, describe the location
4. If no light: Enter darkness state

## Entering Darkness

If the player enters a `requires_light` location without light:

1. Set `flags.in_darkness = true` via `update_game_state`
2. Describe: "It is pitch black. You are likely to be eaten by a grue."
3. Do not describe the room (they can't see it)

## Death by Grue

On the player's **next action**, if `flags.in_darkness` is still `true`:

1. Describe: "The grue's slavering fangs find their mark. You have died."
2. Call `restart_game` immediately

The player gets exactly ONE action to light their lantern or retreat.

## Lighting the Lantern

When the player says "turn on lantern", "light lantern", etc.:

1. Check if `brass_lantern` is in inventory
2. If yes:
   - Set `flags.lantern_lit = true` via `update_game_state`
   - Clear `flags.in_darkness` if it was set
   - Describe: "The lantern flickers to life, casting a warm glow."
   - If in a dark location, now describe the room
3. If no lantern:
   - "You don't have a lantern to light."

## Turning Off the Lantern

When the player says "turn off lantern", "extinguish lantern", etc.:

1. If in a dark location (`requires_light: true`):
   - Warn: "Turning off your light here would be... inadvisable."
2. If they insist or do it anyway:
   - Set `flags.lantern_lit = false`
   - Set `flags.in_darkness = true`
   - They will be eaten by a grue on their next action

## Grue Behavior

The grue is never seen, only sensed:
- Do NOT describe the grue visually
- Use sounds to foreshadow danger:
  - "Sinister scratching nearby."
  - "Hungry breathing in the darkness."
  - "Something moves just beyond your reach."

The grue cannot exist in light. A lit lantern keeps them at bay.

## State Tracking

The game tracks whether the lantern is lit and whether the player is in lethal darkness internally. These states persist across turns and are checked automatically when entering dark locations.

## Movement to Dark Areas

**Sequence when entering dark location:**

1. `get_location_data` shows `requires_light: true`
2. Check `flags.lantern_lit` or `ivory_torch` in inventory
3. If lit: Update location, describe room
4. If not lit:
   - Update location (they're still there, just in darkness)
   - Set `in_darkness = true`
   - Give the warning

## Retreat Option

If the player says "go back" or moves to a different direction while in darkness:
- Allow the retreat if the direction is valid
- Clear `in_darkness` if new location doesn't require light
- They narrowly escaped

## Never Do

- Never let player explore dark areas without light
- Never describe what's in a dark room (they can't see)
- Never show the grue (it's never seen)
- Never give more than one turn to escape darkness
