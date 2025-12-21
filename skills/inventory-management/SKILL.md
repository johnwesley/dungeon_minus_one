---
name: inventory-management
description: Use when the player takes, drops, inspects, stores, or retrieves items. Includes container logic for the brown sack.
---

# Inventory Management

## When to Apply

Apply this skill when the player:
- Takes items: take, get, grab, pick up, acquire
- Drops items: drop, put down, leave, discard
- Inspects items: look at, examine, inspect, check
- Interacts with containers: look in, open, search

## Storing Items

When the player picks up an item, you MUST add the full item object `{id, name, description}` to the `inventory` array using `update_game_state`.

**DO NOT** just store the item ID string. Store the complete object to preserve the item's description even if the player moves to a different location.

Example:
```json
{
  "inventory": [
    {"id": "brass_lantern", "name": "Brass Lantern", "description": "A battery-powered brass lantern."},
    {"id": "sword", "name": "Elvish Sword", "description": "A blade that glows faintly blue."}
  ]
}
```

## Dropping Items

When the player drops an item:

1. Remove the full object from `inventory`
2. Add it to `flags.dropped_items[current_location]` array
3. Create the array if it doesn't exist
4. Use `update_game_state` with both changes
5. Describe the item being set down

Example state update:
```json
{
  "inventory": [...remaining items...],
  "flags": {
    "dropped_items": {
      "hallway": [{"id": "sword", "name": "Elvish Sword", "description": "..."}]
    }
  }
}
```

## Describing Locations with Dropped Items

When describing a location, check `flags.dropped_items[location_id]`:
- If items exist there, mention them naturally: "An elvish sword lies on the ground."
- Integrate with the location description, don't list separately

## Picking Up Dropped Items

When the player takes an item from `flags.dropped_items[current_location]`:

1. Remove it from `flags.dropped_items[current_location]`
2. Add it to `inventory`
3. If the location's dropped_items array becomes empty, remove the key
4. Use `update_game_state` with both changes

## Container Logic: Brown Sack

The brown sack (`brown_sack`) contains hidden items:
- **clove of garlic** (`garlic`)
- **lunch** (`lunch`)

### Hide/Reveal Rules

- These items are **hidden** until the player explicitly inspects the sack
- The player CANNOT take the garlic or lunch until revealed by inspection
- Inspection triggers: "look in sack", "examine sack", "open sack", "search sack"

### Inspection Behavior

When the player inspects the sack:
1. Describe the contents: "Inside the sack you find a clove of garlic and a wrapped lunch."
2. Mark contents as revealed (the player now knows about them)
3. Items become available to take

### Taking Container Items

Once revealed, the player may:
- `take garlic` - Add garlic to main inventory as a separate item
- `take lunch` - Add lunch to main inventory as a separate item

### Dropping the Sack

If the player drops the sack:
- They lose access to any items still inside
- Items explicitly removed (`take garlic`) remain in inventory
- The sack itself goes to `dropped_items`

### Logic Check

If the player has `brown_sack` in inventory and inspects it:
- Treat `garlic` and `lunch` as accessible/takeable
- If they don't have the sack, they cannot access its contents

## Item Existence Verification

Never assume an item is gone unless state confirms it:
- Check if the item ID is in `inventory`
- Check if the item ID is in `flags.trophy_case`
- Check if the item is in `flags.dropped_items[current_location]`

If an item is listed in the location's `interactables` and is NOT in any of these places, it is still present and can be taken.
