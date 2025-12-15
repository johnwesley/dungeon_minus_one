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

## Walkthrough (Exact Command Route)

### 1) House Entry + Key Items

From the start of the game, do:

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

```text
east
out
west
north
```

### 3) Forest Loop (Egg + Forest Location)

```text
north
north
up
take jeweled egg
down
east
north
```

You are now in `clearing`. Do **not** go `down` yet (the grating is locked until you have the `skeleton_key`).

### 4) Canyon + Rainbow + River (Pot of Gold, Shovel, Scarab)

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

You are now at `reservoir_south`, and the reservoir should be drainable/enterable.

### 6) Reservoir + Atlantis (Trunk of Jewels, Air Pump, Trident)

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

```text
north
north
east
west
north
take jade figurine
east
north
down
take sapphire bracelet
east
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
west
up
south
west
south
east
south
down
up
```

You should now be back in the `living_room`.

### 12) Final Deposits (5 treasures) + Victory

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
