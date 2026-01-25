# Dungeon-1: Minimal-Movement Walkthrough (Victory Only)

This walkthrough wins the game with the fewest movement commands possible. It does **not** visit every location; it only collects all 13 treasures and reaches victory.

- **Movement total:** 74 movement commands from `start` to `living_room` with all treasures (actions like `take`, `attack`, and `put` are not counted).
- After that, deposit everything and `enter vault` to finish.

## Global Rules (Short Version)

- Turn on the brass lantern in the Living Room before entering any dark area.
- Resolve blockers immediately:
  - Troll: `attack troll with elvish sword`
  - Cyclops: `attack cyclops with elvish sword`
  - Thief: `attack thief with elvish sword` (then take the chalice)
  - Bat: explain you are removing the figurine for mitigation
  - Hades spirits: `ring bell`, `read book`, `light candles`

## Treasure Checklist (13/13)

1. jeweled egg (Up a Tree)
2. pot of gold (End of Rainbow)
3. scarab (Sandy Cave)
4. platinum bar (Loud Room)
5. trunk of jewels (Reservoir)
6. crystal trident (Atlantis Room)
7. bag of coins (Maze Skeleton)
8. chalice (Treasure Room)
9. ivory torch (Torch Room)
10. gold coffin (Egyptian Room)
11. crystal skull (Land of the Dead)
12. jade figurine (Bat Room)
13. sapphire bracelet (Gas Room)

## Required Utility Items

- brass lantern (Living Room)
- elvish sword (Living Room)
- shovel (Sandy Beach)
- wrench (Maintenance Room)
- skeleton key (Maze Skeleton)
- brass bell (Temple)
- candles + black book (Altar)

## Walkthrough (Minimal Movement)

Each section includes:
- a copy/paste command block, and
- a **Moves** list showing the destination after each movement command.

### 1) House -> Maze -> Grating (Bag of Coins + Chalice, reach Clearing)

**Start:** `start` (Deferred Intake Zone)  
**Moves:**
- `north` → `north_of_house` (North of House)
- `east` → `behind_house` (Behind House)
- `inside` → `kitchen` (Kitchen)
- `west` → `living_room` (Living Room)
- `down` → `cellar` (Cellar)
- `north` → `troll_room` (The Troll Room)
- `west` → `maze_entrance` (Maze Entrance)
- `south` → `maze_twist` (Maze Twist)
- `up` → `maze_skeleton` (Maze Skeleton)
- `down` → `maze_twist` (Maze Twist)
- `east` → `maze_bones` (Maze Bones)
- `southeast` → `cyclops_room` (Cyclops Room)
- `up` → `treasure_room` (Treasure Room)
- `down` → `cyclops_room` (Cyclops Room)
- `northwest` → `maze_bones` (Maze Bones)
- `down` → `grating_room` (Grating Room)
- `up` → `clearing` (Clearing)

```text
north
east
inside
west
take brass lantern
turn on lantern
take elvish sword
down
north
attack troll with elvish sword
west
south
up
take bag of coins
take skeleton key
down
east
southeast
attack cyclops with elvish sword
up
attack thief with elvish sword
take chalice
down
northwest
down
unlock grating with skeleton key
up
```

### 2) Surface + Dam/Reservoir + Loud Room (Egg, Gold, Scarab, Platinum, Trunk, Trident)

**Start:** `clearing` (Clearing)  
**Moves:**
- `south` → `forest_path` (Forest Path)
- `up` → `up_a_tree` (Up a Tree)
- `down` → `forest_path` (Forest Path)
- `north` → `clearing` (Clearing)
- `east` → `canyon_view` (Canyon View)
- `down` → `rocky_ledge` (Rocky Ledge)
- `down` → `canyon_bottom` (Canyon Bottom)
- `north` → `end_of_rainbow` (End of Rainbow)
- `east` → `aragain_falls` (Upper Spillway)
- `north` → `shore` (Shore)
- `north` → `sandy_beach` (Sandy Beach)
- `northeast` → `sandy_cave` (Sandy Cave)
- `southwest` → `sandy_beach` (Sandy Beach)
- `north` → `dam_base` (Dam Base)
- `up` → `dam` (Dam)
- `north` → `dam_lobby` (Dam Lobby)
- `north` → `maintenance_room` (Maintenance Room)
- `south` → `dam_lobby` (Dam Lobby)
- `south` → `dam` (Dam)
- `west` → `reservoir_south` (Reservoir South)
- `north` → `reservoir` (Reservoir)
- `north` → `reservoir_north` (North Reservoir Access)
- `north` → `atlantis_room` (Submerged Operations Chamber)
- `south` → `reservoir_north` (North Reservoir Access)
- `south` → `reservoir` (Reservoir)
- `south` → `reservoir_south` (Reservoir South)
- `southeast` → `deep_canyon` (Deep Canyon)
- `down` → `loud_room` (Loud Room)
- `west` → `round_room` (Round Room)

```text
south
up
take jeweled egg
down
north
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
north
up
north
north
take wrench
south
south
use wrench on bolt
west
north
take trunk of jewels
north
north
take crystal trident
south
south
south
southeast
down
take platinum bar
west
```

### 3) Temple + Hades -> Mine Entrance (Torch, Coffin, Skull)

**Start:** `round_room` (Round Room)  
**Moves:**
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
- `north` → `mirror_room` (Mirror Room)
- `north` → `cold_passage` (Cold Passage)
- `east` → `mine_entrance` (Mine Entrance)

```text
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
ring bell
read book
light candles
south
take crystal skull
north
up
north
north
east
```

### 4) Mine + Return (Jade Figurine, Sapphire Bracelet, back to Living Room)

**Start:** `mine_entrance` (Mine Entrance)
**Moves:**
- `west` → `squeaky_room` (Squeaky Room)
- `north` → `bat_room` (Bat Room)
- `east` → `shaft_room` (Shaft Room)
- `north` → `smelly_room` (Smelly Room)
- `down` → `gas_room` (Gas Room) ⚠️ **GAS HAZARD - see below**
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
3. Flip the switch to turn on the electric ceiling light
4. Retrieve your items after exiting

```text
west
north
tell bat you are removing the figurine for mitigation
take jade figurine
east
north
drop ivory torch
turn off lantern
flip switch
down
take sapphire bracelet
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

### 5) Final Deposits + Victory

**Start:** `living_room` (Living Room)

```text
put jeweled egg in trophy case
put pot of gold in trophy case
put scarab in trophy case
put platinum bar in trophy case
put trunk of jewels in trophy case
put crystal trident in trophy case
put bag of coins in trophy case
put chalice in trophy case
put ivory torch in trophy case
put gold coffin in trophy case
put crystal skull in trophy case
put jade figurine in trophy case
put sapphire bracelet in trophy case
enter vault
```
