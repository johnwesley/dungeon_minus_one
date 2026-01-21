---
name: movement-resolution
description: Use when the player attempts to move between locations, reference directions, entrances, stairs, or passages. Handles exit validation and state updates.
---

# Movement Resolution

## MANDATORY TOOL USE

**YOU MUST CALL TOOLS FOR EVERY MOVEMENT ATTEMPT. NO EXCEPTIONS.**

Before describing ANY location or movement result, you MUST:
1. Call `get_game_state` to verify current position and available exits
2. Call `update_game_state` if moving to a new location

**NEVER describe a room, location, or movement outcome without first calling these tools.**

If you respond to a movement command without calling `get_game_state` and `update_game_state`, the game will desync. This is a critical failure.

## When to Apply

Apply this skill when the player:
- Uses movement verbs: go, move, walk, run, head, proceed, enter, exit, leave, climb, descend
- References directions: north, south, east, west, up, down, n, s, e, w, u, d
- References passages: door, gate, stairs, ladder, tunnel, passage, path, trail
- Uses ANY natural language that implies moving (e.g., "I'd like to head that way", "take me to...", "let's go")

## Critical Rules

### Strict Location Logic
You MUST NOT invent exits or move the player to a location that is not explicitly defined in the `exits` map of the current location data — except for explicit special-case movement rules (e.g., locked grating, reservoir water level).

### Direction Fidelity
If the user types "go up" and the data says `"up": "treasure_room"`, you MUST move them to `treasure_room`, even if the narrative description suggests something else (e.g., a monster fled east) — unless an explicit special-case rule blocks or overrides that move.

### State Update Requirement
**CRITICAL**: When the player moves to a new location, you MUST call `update_game_state` with `current_location` set to the new location ID.

Calling `get_location_data` does NOT move the player. You MUST explicitly call `update_game_state` to persist the new location.

Call `update_game_state` BEFORE or DURING the description of the new room. If you fail to do this, the game state will desync and the player will be stuck in the old location on their next turn.

### No Invented Mechanics
If an exit exists in `available_exits`, the player CAN use it. Do NOT invent additional requirements such as:
- Tying ropes
- Building bridges
- Climbing equipment
- Physical preparation
- Solving puzzles not defined in skills

The ONLY valid reasons to block an exit are:
1. Exit doesn't exist in `available_exits`
2. A specific skill rule blocks it (grating lock, reservoir water, NPC guard)
3. Darkness without light source

If none of these apply, the move MUST succeed. Do not draw on external game knowledge (e.g., Zork mechanics) to invent requirements.

## Movement Sequence

When the player issues a movement command:

1. Call `get_game_state` to get current location and `available_exits`
2. Verify the requested direction exists in `available_exits`
3. If direction is invalid, respond with a grounded denial (e.g., "There's no path that way.")
4. If valid, call `get_location_data` with the target location ID
5. Call `update_game_state` with `current_location` set to the new location ID
6. Describe the new location using the fetched data

## Example

**Player**: "go north"

**Sequence**:
1. `get_game_state` returns `available_exits: {"north": "hallway", "south": "cellar"}`
2. "north" is valid, target is "hallway"
3. `get_location_data("hallway")` to fetch description
4. `update_game_state({"current_location": "hallway"})` to persist the move
5. Describe the hallway

## Invalid Movement Response

When the player tries to move in an invalid direction, do not say "I don't know what you mean." Instead, give a grounded denial:
- "The wall disagrees with your optimism."
- "There's no path that way. Try one of the obvious exits."
- "You can't go that direction from here."

Never invent exits. Never move the player without updating state.

## Never Do

These are critical errors that will break the game:

1. **Never describe a location without calling tools first**
   - BAD: Player says "south" → You immediately describe a new room
   - GOOD: Player says "south" → Call `get_game_state` → Verify exit → Call `update_game_state` → Call `get_location_data` → Describe room

2. **Never use memory or context for location descriptions**
   - BAD: You remember what's south and describe it from memory
   - GOOD: Always fetch fresh data via `get_location_data`

3. **Never skip `update_game_state` when moving**
   - BAD: Describe new location without updating state
   - GOOD: Always call `update_game_state({"current_location": "target_id"})` BEFORE describing

4. **Never assume you know the current location**
   - BAD: You think the player is at location X and respond accordingly
   - GOOD: Always verify via `get_game_state` first

5. **Never narrate your reasoning process**
   - BAD: "Good, reservoir_drained is true, so I can allow passage north"
   - BAD: "Let me check the exits... north is valid"
   - BAD: "Since the grating is unlocked, you can descend"
   - GOOD: Just describe the new location without explaining why movement was allowed

If you follow these rules, the game will stay in sync. If you skip them, the player will be stuck.
