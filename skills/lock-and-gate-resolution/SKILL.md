---
name: lock-and-gate-resolution
description: Use when the player interacts with locked passages, keys, or barriers like the grating.
---

# Locks & Gates Resolution

## When to Apply

Apply this skill when:
- The player attempts to move through a locked passage
- The player tries to unlock, open, or manipulate a lock
- The player uses a key on a barrier
- Movement involves the grating between clearing and grating_room

## The Grating (Surface Access)

There is a heavy metal grating that connects `clearing` (above) and `grating_room` (below).

### Default State
The grating is **locked by default**. Track its state in `flags.grating_unlocked` (boolean).

### Movement Rules

**From `clearing` going `down` to `grating_room`:**
- If `flags.grating_unlocked` is `true`: Allow the move
- Otherwise: Block the move and describe the locked grating

**From `grating_room` going `up` to `clearing`:**
- If `flags.grating_unlocked` is `true`: Allow the move
- Otherwise: Block the move and describe the locked grating from below

### Unlocking Rules

If the player is in `clearing` or `grating_room` and tries to unlock/open the grating or lock:

1. Verify the player has `skeleton_key` in inventory (check by `id`)
2. If they have the key:
   - Set `flags.grating_unlocked = true` via `update_game_state`
   - Describe the lock giving way, metal groaning, grating now passable
3. If they don't have the key:
   - Tell them they need a key that actually fits
   - Hint: "The lock seems to want a skeleton key."

### Description Consistency

When describing the grating:
- **Locked (from above)**: Heavy iron grating set into the ground, secured with an old lock
- **Locked (from below)**: Looking up at an iron grating, lock holding it shut
- **Unlocked**: The grating stands open, revealing passage

## Unlock Sequence

1. Player attempts unlock action
2. `get_game_state` to check inventory for `skeleton_key`
3. If key present: `update_game_state` with `flags.grating_unlocked = true`
4. Describe success or failure

## Key Verification

Always check by item `id`, not just by name:
```python
has_key = any(item.get("id") == "skeleton_key" for item in inventory)
```

## Other Locks

For any other locked passages in the game:
1. Track lock state in an appropriate flag
2. Verify key possession by item ID
3. Allow or block movement based on lock state
4. Persist unlocks via `update_game_state`
5. Describe locks consistently from both sides
