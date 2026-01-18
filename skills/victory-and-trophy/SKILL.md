---
name: victory-and-trophy
description: Use when interacting with the trophy case, depositing treasures, or evaluating win conditions.
---

# Victory & Trophy Case

## When to Apply

Apply this skill when:
- The player is in `living_room`
- The player interacts with the trophy case
- The player attempts to deposit or retrieve items from the case
- Checking victory conditions

## Trophy Case Location

The trophy case is in the **Living Room** (id: `living_room`). It only accepts treasure items.

## Required Treasures

The following items are treasures that can be deposited in the trophy case:

- Platinum Bar
- Gold Coffin
- Ivory Torch
- Crystal Trident
- Trunk of Jewels
- Bag of Coins
- Pot of Gold
- Jade Figurine
- Silver Chalice
- Jeweled Egg
- Sapphire Bracelet
- Crystal Skull
- Scarab

## Depositing Treasures

When the player says "put [item] in trophy case", "put [item] in case", "drop [item] in case", etc. while in `living_room`:

1. Verify the item is in `inventory`
2. Verify the item is a treasure (check against the list above by ID)
3. If not a treasure: "The case only accepts treasures."
4. If valid treasure:
   - Remove the item from `inventory`
   - Add the treasure **ID string** (e.g., `platinum_bar`) to `flags.trophy_case` array
   - Create the array if it doesn't exist
   - Use `update_game_state` with both changes
   - Describe with satisfaction: "The [treasure] settles into place with a satisfying click."

## Examining Trophy Case

When the player examines the trophy case:
- List any items in `flags.trophy_case`
- If empty: "The case stands empty, waiting to be filled."
- If partial: "The case holds [items]. Room remains for more."

## Taking from Trophy Case

If the player tries to take a treasure from the trophy case while in `living_room`:

1. Verify the item is in `flags.trophy_case`
2. Remove it from `flags.trophy_case`
3. Add it to `inventory` (as full object with id, name, description)
4. Comment on their questionable decision: "You retrieve the treasure. Progress, reversed."

## Victory Logic

Define `all_treasures_deposited` as: The player is in `living_room` AND **all required treasures** exist in `flags.trophy_case` (order does not matter).

### Vault Reveal

When `all_treasures_deposited` becomes true for the first time (i.e., `flags.vault_revealed` is not true yet):

1. Describe a hidden mechanism clicking into place within the Trophy Case
2. A secret panel slides open, revealing a staircase down to the **Treasure Vault**
3. Set `flags.vault_revealed = true` via `update_game_state`
4. From now on, the Living Room gains a standard exit to the vault (available as `vault`, `panel`, and `down` in `available_exits`).

This reveal persists and isn't re-triggered every turn.

### Entering the Vault

Once `flags.vault_revealed` is true, entering the vault uses **standard movement resolution**:
- Treat "enter vault/panel" or similar phrasing as movement toward the `vault`/`panel`/`down` exit in `available_exits`.
- Follow the normal movement tool sequence (get_game_state → validate exit → get_location_data → update_game_state → describe).

### Game Over State (Hard Stop)

The moment the player arrives in `victory`:

1. Render the victory description (no "congratulations" speech, keep it cold and final)
2. Add a short epilogue (2-4 sentences) that summarizes their run with 1-3 concrete details from this session (items found, NPC encounters, choices made). Keep it dry, specific, and narratively consistent.
3. Print the ending ASCII exactly:
```
[ PROCESS COMPLETE ]
[ NO FURTHER INPUT ]

>
```
4. Set `flags.game_over = true` via `update_game_state`

### Post-Victory Input

If `flags.game_over` is true:
- Do not process commands
- Do not move locations
- Do not change inventory
- Do not update flags (except restart)
- Respond only with the ending ASCII block (exactly, every time)
- If player explicitly requests restart: call `restart_game`
