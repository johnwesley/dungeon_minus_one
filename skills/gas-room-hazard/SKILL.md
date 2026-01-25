---
name: gas-room-hazard
description: Use when the player approaches, enters, or takes actions in the gas room. Handles explosion mechanics from open flame sources.
---

# Gas Room Hazard Resolution

## When to Apply

Apply this skill when:
- The player moves toward or enters the gas_room
- The player is in the gas_room and interacts with light sources
- The player is carrying the ivory_torch or has the lantern lit near the gas_room

## Core Mechanic

The gas_room is filled with coal gas. Any open flame causes an immediate, fatal explosion.

## Explosion Triggers

The following situations cause an explosion and game restart:

| Trigger | Condition |
|---------|-----------|
| Enter with ivory_torch | `ivory_torch` in inventory when entering gas_room |
| Enter with lit lantern | `flags.lantern_lit = true` when entering gas_room |
| Light lantern inside | Player lights lantern while in gas_room |

## Explosion Sequence

When an explosion is triggered:

1. Describe the explosion dramatically (1-2 sentences):
   - "The gas ignites the moment your flame enters the chamber. The explosion is instantaneous and absolute."
   - "The lit lantern meets the coal gas. Your last thought is that the warning signs weren't decorative."
2. Call `restart_game` immediately
3. Do not continue the scene

## Electric Light System

The gas_room has an electric ceiling light controlled by switches in adjacent rooms:

| Location | Switch | Effect |
|----------|--------|--------|
| smelly_room | light_switch | Toggles `flags.gas_room_light_on` |
| coal_mine | light_switch | Toggles `flags.gas_room_light_on` |

When player flips a switch:
1. Toggle `flags.gas_room_light_on` (true ↔ false)
2. Describe: "You flip the switch. A faint hum indicates something electrical powering [on/off] somewhere nearby."

## Entering the Gas Room

When the player enters gas_room:

### With Open Flame (ivory_torch or lantern_lit = true)
→ Explosion → restart_game

### Without Flame, Electric Light ON (flags.gas_room_light_on = true)
→ Describe the room normally under electric illumination

### Without Flame, Electric Light OFF (flags.gas_room_light_on = false)
1. Allow entry (they're in the room)
2. Describe darkness: "You descend into complete darkness. The smell of gas is overwhelming, but at least nothing here wants to eat you."
3. Do NOT set `flags.in_darkness` (grue mechanic doesn't apply here)
4. Player can:
   - Retreat (go up or east)
   - Grope blindly for items (low chance of success)
   - Light lantern (triggers explosion)

## Key Differences from Grue

- Gas room has `requires_light: false` - standard darkness/grue rules don't apply
- No grue in the gas room (gas keeps creatures away)
- Player can exist safely in gas room darkness (just can't see)
- Lighting any flame is instantly fatal (no warning turn)

## Warning Signs

Both smelly_room and coal_mine have warning signs. When player examines them:

"The sign reads: DANGER - COAL GAS - NO OPEN FLAME. Below it, someone has scrawled: 'The electric light works. Use the switch.'"

## Interactables

| ID | Location | Description |
|----|----------|-------------|
| warning_sign | smelly_room, coal_mine | Warns about gas and suggests using the switch |
| light_switch | smelly_room, coal_mine | Controls electric light in gas_room |
| electric_light | gas_room | Ceiling-mounted electric lamp |
| sapphire_bracelet | gas_room | Treasure item (can be taken) |

## Safe Path to Sapphire Bracelet

1. Player reads warning sign in smelly_room or coal_mine
2. Player flips light_switch (sets `flags.gas_room_light_on = true`)
3. Player ensures no open flame (lantern off, no ivory_torch)
4. Player enters gas_room → sees room lit by electric light
5. Player takes sapphire_bracelet
6. Player exits safely

## State Tracking

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `flags.gas_room_light_on` | boolean | false | Electric ceiling light state |
| `flags.lantern_lit` | boolean | (existing) | Whether brass lantern is lit |

## Never Do

- Never allow open flame into the gas room without explosion
- Never apply grue mechanics to gas_room
- Never describe the grue in gas_room (it doesn't exist there)
- Never give a "warning turn" before explosion (gas ignites instantly)
- Never let player "turn off" the ivory_torch (it's always lit)
