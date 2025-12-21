---
name: environmental-state-water
description: Use when movement or interaction depends on water level or the dam/reservoir environmental state.
---

# Environmental State: Water Level

## When to Apply

Apply this skill when:
- The player is near the reservoir or dam
- The player attempts to enter the reservoir
- The player interacts with dam controls
- Water level affects movement or access

## Dam & Reservoir System

The dam can drain the reservoir. Track this with `flags.reservoir_drained` (boolean).

### Default State

If `flags.reservoir_drained` is not `true`, assume the reservoir is **full** (deep water, impassable).

### The Reservoir Location

The `reservoir` location represents the exposed reservoir bed (mud, debris, possibly items). It is only accessible when drained.

## Movement Rules

### Entering the Reservoir

The player can approach the reservoir from:
- `reservoir_south` going `north`
- `reservoir_north` going `south`

If `flags.reservoir_drained` is **not true**:
- Block the move
- Describe deep water preventing travel
- Example: "The reservoir is full of dark, cold water. You'd drown before you made it halfway across."

If `flags.reservoir_drained` is **true**:
- Allow the move
- The reservoir bed is now exposed and traversable

## Draining the Reservoir

### Location
The dam controls are at the `dam` location.

### Trigger Actions
Player attempts to drain: "turn bolt", "use wrench on bolt", "open gates", "drain reservoir", "operate controls"

### Drain Sequence

1. Verify player is in `dam` location
2. Check if player has `wrench` in inventory (by `id`)
3. If no wrench:
   - Block the action
   - Hint: "The bolt is rusted tight. You'd need something with leverage—a wrench, perhaps."
4. If player has wrench and `flags.reservoir_drained` is not true:
   - Set `flags.reservoir_drained = true` via `update_game_state`
   - Describe the bolt turning, gates shifting, water rushing away
   - Visual cue: "The green bubble in the gauge drops as the water level falls."
5. If `flags.reservoir_drained` is already true:
   - Describe that the job is already done
   - "The gates are already open. The reservoir lies empty below."

## State Persistence

Once drained, the reservoir stays drained. There is no mechanism to refill it.

## Description Consistency

**Full reservoir:**
- Dark water stretches across the reservoir
- No way to cross without drowning

**Drained reservoir:**
- Muddy bed exposed
- Debris and items may be visible
- Passage now possible

## Required Tool Calls

When draining:
```json
{
  "flags": {
    "reservoir_drained": true
  }
}
```

## Never Do

- Never let the player swim across a full reservoir
- Never drain without the wrench
- Never forget to persist the drained state
