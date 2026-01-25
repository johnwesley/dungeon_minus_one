# Dungeon-1: Complete Walkthrough (100% Locations + Victory)

This walkthrough is designed to:
1) visit **every location** defined in `data/locations/` (including `victory`), and  
2) win the game by depositing all **13 treasures** into the **Living Room** trophy case.

It is not the shortest route. It is the one that touches everything.

## Global Rules (So You Don’t Die Pointlessly)

- **Turn the lantern on early and keep it on.** Many locations are dark (`requires_light: true`). If you enter darkness without light, the grue mechanic will kill you.
- **Depositing treasures:** while in the **Living Room**, use `put <treasure> in trophy case`.
- **NPC safety picks used here:**
  - Troll: `throw lunch at troll` (incapacitates her)
  - Cyclops: `attack cyclops with elvish sword`
  - Thief: `attack thief with elvish sword`
  - Bat: `tell bat you’re removing the figurine for mitigation` (do NOT use garlic)
  - Spirits at Hades: complete the bell/candle/book ritual

## Treasure Checklist (13/13)

You will collect and deposit these along the route:

1. `jeweled_egg` (Up a Tree)
2. `pot_of_gold` (End of Rainbow)
3. `scarab` (Sandy Cave)
4. `platinum_bar` (Loud Room)
5. `trunk_of_jewels` (Reservoir)
6. `crystal_trident` (Atlantis Room)
7. `bag_of_coins` (Maze Skeleton Alcove)
8. `chalice` (Treasure Room)
9. `ivory_torch` (Torch Room)
10. `gold_coffin` (Egyptian Room)
11. `crystal_skull` (Land of the Dead)
12. `jade_figurine` (Bat Room)
13. `sapphire_bracelet` (Gas Room)

## Location Checklist (72/72)

If you want to verify 100% completion, this walkthrough visits every location id:

`altar`, `aragain_falls`, `atlantis_room`, `attic`, `bat_room`, `behind_house`, `canyon_bottom`, `canyon_view`, `cave`, `cellar`, `chasm`, `clearing`, `coal_mine`, `cold_passage`, `cyclops_room`, `dam`, `dam_base`, `dam_lobby`, `dead_end`, `deep_canyon`, `dome_room`, `drafty_room`, `east_of_chasm`, `east_west_passage`, `egyptian_room`, `end_of_rainbow`, `engravings_cave`, `entrance_to_hades`, `forest`, `forest_path`, `gallery`, `gas_room`, `grating_room`, `kitchen`, `ladder_bottom`, `ladder_top`, `land_of_the_dead`, `living_room`, `loud_room`, `machine_room`, `maintenance_room`, `maze_bones`, `maze_dead_end`, `maze_entrance`, `maze_skeleton`, `maze_twist`, `mine_entrance`, `mirror_room`, `north_of_house`, `reservoir`, `reservoir_north`, `reservoir_south`, `rocky_ledge`, `round_room`, `sandy_beach`, `sandy_cave`, `shaft_room`, `shore`, `slide_room`, `smelly_room`, `south_of_house`, `squeaky_room`, `start`, `strange_passage`, `studio`, `temple`, `timber_room`, `torch_room`, `treasure_room`, `troll_room`, `up_a_tree`, `victory`.

## Walkthrough (Commands + Location-by-Location Moves)

Each numbered section below includes:
- a copy/paste command block, and
- a **Moves** list showing the **destination location** after each movement command (so you always know where you should be).

### 1) House Entry + Key Items

From the start of the game, do:

**Start:** `start` (Deferred Intake Zone)  
**Moves:**
- `north` → `north_of_house` (North of House)
- `east` → `behind_house` (Behind House)
- `inside` → `kitchen` (Kitchen)
- `up` → `attic` (Attic)
- `down` → `kitchen` (Kitchen)
- `west` → `living_room` (Living Room)

```text
north
east
inside
take brown sack
look in sack
take garlic
take lunch
up
take rope
take nasty knife
down
west
take brass lantern
turn on lantern
take elvish sword
```

### 2) Visit South Side of House (Completion)

**Start:** `living_room` (Living Room)  
**Moves:**
- `east` → `kitchen` (Kitchen)
- `out` → `behind_house` (Behind House)
- `west` → `south_of_house` (South of House)
- `north` → `start` (Deferred Intake Zone)

```text
east
out
west
north
```

### 3) Forest Loop (Egg + Forest Location)

**Start:** `start` (Deferred Intake Zone)  
**Moves:**
- `north` → `north_of_house` (North of House)
- `north` → `forest_path` (Forest Path)
- `up` → `up_a_tree` (Up a Tree)
- `down` → `forest_path` (Forest Path)
- `east` → `forest` (Forest)
- `north` → `clearing` (Clearing)

```text
north
north
up
take jeweled egg
down
east
north
```

You are now in `clearing` (Clearing). Do **not** go `down` yet (the grating is locked until you have the `skeleton_key`).

### 4) Canyon + Rainbow + River (Pot of Gold, Shovel, Scarab)

**Start:** `clearing` (Clearing)  
**Moves:**
- `east` → `canyon_view` (Canyon View)
- `down` → `rocky_ledge` (Rocky Ledge)
- `down` → `canyon_bottom` (Canyon Bottom)
- `north` → `end_of_rainbow` (End of Rainbow)
- `east` → `aragain_falls` (Upper Spillway)
- `north` → `shore` (Shore)
- `north` → `sandy_beach` (Sandy Beach)
- `northeast` → `sandy_cave` (Sandy Cave)
- `southwest` → `sandy_beach` (Sandy Beach)

```text
east
down
down
north
take pot of gold
east
north
north
take shovel
northeast
dig sand with shovel
take scarab
southwest
```

### 5) Dam Loop (Drain Reservoir) + Loud Room (Platinum Bar)

**Start:** `sandy_beach` (Sandy Beach)  
**Moves:**
- `north` → `dam_base` (Dam Base)
- `up` → `dam` (Dam)
- `north` → `dam_lobby` (Dam Lobby)
- `north` → `maintenance_room` (Maintenance Room)
- `south` → `dam_lobby` (Dam Lobby)
- `south` → `dam` (Dam)
- `south` → `deep_canyon` (Deep Canyon)
- `down` → `loud_room` (Loud Room)
- `west` → `round_room` (Round Room)
- `west` → `east_west_passage` (East-West Passage)
- `north` → `chasm` (Chasm)
- `northeast` → `reservoir_south` (Reservoir South)

```text
north
take plastic boat
up
north
north
take wrench
take screwdriver
south
south
use wrench on bolt
south
down
take platinum bar
west
west
north
northeast
```

You are now at `reservoir_south` (Reservoir South), and the reservoir should be drainable/enterable.

### 6) Reservoir + Atlantis (Trunk of Jewels, Air Pump, Trident)

**Start:** `reservoir_south` (Reservoir South)  
**Moves:**
- `north` → `reservoir` (Reservoir)
- `north` → `reservoir_north` (North Reservoir Access)
- `north` → `atlantis_room` (Submerged Operations Chamber)
- `south` → `reservoir_north` (North Reservoir Access)
- `south` → `reservoir` (Reservoir)
- `south` → `reservoir_south` (Reservoir South)

```text
north
take trunk of jewels
north
take air pump
north
take crystal trident
south
south
south
```

### 7) First Troll Encounter (Incapacitate) + Return Home + Deposit (6 treasures)

**Start:** `reservoir_south` (Reservoir South)  
**Moves:**
- `southwest` → `chasm` (Chasm)
- `south` → `east_west_passage` (East-West Passage)
- `west` → `troll_room` (The Troll Room)
- `south` → `cellar` (Cellar)
- `up` → `living_room` (Living Room)

```text
southwest
south
west
throw lunch at troll
south
up
```

Deposit what you have so far:

```text
put jeweled egg in trophy case
put pot of gold in trophy case
put scarab in trophy case
put platinum bar in trophy case
put trunk of jewels in trophy case
put crystal trident in trophy case
```

### 8) House Lower Rooms (Studio + Gallery + East of Chasm)

**Start:** `living_room` (Living Room)  
**Moves:**
- `east` → `kitchen` (Kitchen)
- `down` → `studio` (Studio)
- `south` → `gallery` (Gallery)
- `west` → `east_of_chasm` (East of Chasm)
- `east` → `gallery` (Gallery)
- `north` → `studio` (Studio)
- `up` → `kitchen` (Kitchen)
- `west` → `living_room` (Living Room)

```text
east
down
south
west
east
north
up
west
```

### 9) Maze (Coins + Skeleton Key) + Grating Room (Unlock) + Treasure Room (Chalice)

**Start:** `living_room` (Living Room)  
**Moves:**
- `down` → `cellar` (Cellar)
- `north` → `troll_room` (The Troll Room)
- `west` → `maze_entrance` (Maze (Dusty Crossroads))
- `west` → `maze_dead_end` (Maze (Narrow Dead End))
- `east` → `maze_entrance` (Maze (Dusty Crossroads))
- `south` → `maze_twist` (Maze (Twisted Junction))
- `up` → `maze_skeleton` (Maze (Skeleton Alcove))
- `northeast` → `grating_room` (Grating Room)
- `up` → `clearing` (Clearing)
- `down` → `grating_room` (Grating Room)
- `southwest` → `maze_skeleton` (Maze (Skeleton Alcove))
- `down` → `maze_twist` (Maze (Twisted Junction))
- `east` → `maze_bones` (Maze (Bone-Littered Passage))
- `southeast` → `cyclops_room` (Cyclops Room)
- `up` → `treasure_room` (Treasure Room)
- `down` → `cyclops_room` (Cyclops Room)
- `east` → `strange_passage` (Strange Passage)
- `east` → `living_room` (Living Room)

```text
down
north
west
west
east
south
up
take bag of coins
take skeleton key
northeast
unlock grating with skeleton key
up
down
southwest
down
east
southeast
attack cyclops with elvish sword
up
attack thief with elvish sword
take chalice
down
east
east
```

Deposit the two new treasures:

```text
put bag of coins in trophy case
put chalice in trophy case
```

### 10) Temple + Hades (Torch, Coffin, Ritual, Skull)

**Start:** `living_room` (Living Room)  
**Moves:**
- `down` → `cellar` (Cellar)
- `north` → `troll_room` (The Troll Room)
- `east` → `east_west_passage` (East-West Passage)
- `east` → `round_room` (Round Room)
- `southeast` → `engravings_cave` (Engravings Cave)
- `east` → `dome_room` (Dome Room)
- `down` → `torch_room` (Torch Room)
- `south` → `temple` (Temple)
- `east` → `egyptian_room` (Egyptian Room)
- `west` → `temple` (Temple)
- `south` → `altar` (Altar)
- `down` → `cave` (Cave)
- `down` → `entrance_to_hades` (Entrance to Hades)
- `south` → `land_of_the_dead` (Land of the Dead)
- `north` → `entrance_to_hades` (Entrance to Hades)
- `up` → `cave` (Cave)

```text
down
north
east
east
southeast
east
down
take ivory torch
south
take brass bell
east
take gold coffin
west
south
take candles
take black book
down
down
ring brass bell
light candles
read black book
south
take crystal skull
north
up
```

### 11) Mine Loop (Jade Figurine + Bracelet + Every Mine Location) + Slide Back Home

**Start:** `cave` (Cave)
**Moves:**
- `north` → `mirror_room` (Mirror Room)
- `north` → `cold_passage` (Cold Passage)
- `east` → `mine_entrance` (Mine Entrance)
- `west` → `squeaky_room` (Squeaky Room)
- `north` → `bat_room` (Bat Room)
- `east` → `shaft_room` (Shaft Room)
- `north` → `smelly_room` (Smelly Room)
- `down` → `gas_room` (Gas Room) ⚠️ **GAS HAZARD - see below**
- `east` → `coal_mine` (Coal Mine)
- `down` → `ladder_top` (Ladder Top)
- `down` → `ladder_bottom` (Ladder Bottom)
- `south` → `dead_end` (Dead End)
- `north` → `ladder_bottom` (Ladder Bottom)
- `west` → `timber_room` (Timber Room)
- `west` → `drafty_room` (Drafty Room)
- `south` → `machine_room` (Machine Room)
- `north` → `drafty_room` (Drafty Room)
- `east` → `timber_room` (Timber Room)
- `east` → `ladder_bottom` (Ladder Bottom)
- `up` → `ladder_top` (Ladder Top)
- `up` → `coal_mine` (Coal Mine)
- `west` → `gas_room` (Gas Room) ⚠️ **GAS HAZARD - lantern must be off**
- `up` → `smelly_room` (Smelly Room)
- `south` → `shaft_room` (Shaft Room)
- `west` → `bat_room` (Bat Room)
- `south` → `squeaky_room` (Squeaky Room)
- `east` → `mine_entrance` (Mine Entrance)
- `south` → `slide_room` (Slide Room)
- `down` → `cellar` (Cellar)
- `up` → `living_room` (Living Room)

⚠️ **Gas Room Hazard:** The gas room is filled with coal gas. Any open flame (lit lantern or ivory torch) will cause an explosion and death. You must:
1. Drop the ivory torch in smelly_room before entering
2. Turn off your lantern before entering
3. Flip the switch in smelly_room to turn on the electric ceiling light
4. Turn the lantern back on only after reaching coal_mine (east of gas room)
5. Turn the lantern off again before returning west through gas_room

```text
north
north
east
west
north
tell bat you're removing the jade figurine for mitigation
take jade figurine
east
north
drop ivory torch
turn off lantern
flip switch
down
take sapphire bracelet
east
turn on lantern
down
down
south
north
west
west
south
north
east
east
up
up
turn off lantern
west
up
turn on lantern
take ivory torch
south
west
south
east
south
down
up
```

You should now be back in the `living_room` (Living Room).

### 12) Final Deposits (5 treasures) + Victory

**Location:** `living_room` (Living Room)  
**Move (after all 13 treasures are deposited):**
- `enter vault` → `victory` (The Treasure Vault)

```text
put ivory torch in trophy case
put gold coffin in trophy case
put crystal skull in trophy case
put jade figurine in trophy case
put sapphire bracelet in trophy case
```

After the last deposit, the trophy case mechanism should reveal the vault access. Finish with:

```text
enter vault
```
