# The Lost Crown: Code Design

This document explains how `adventure.py` is put together. The game is one Python file with no dependencies beyond the standard library (`random`, `textwrap`).

## Overview

The code has three layers:

| Layer | What it is | Where |
|---|---|---|
| **Data** | The world (rooms, items, text, balance numbers) | Module-level constants at the top of the file |
| **State** | Everything that changes while you play | The `Game` instance's attributes |
| **Logic** | Reading commands and changing state | The `Game` methods |

The world is described as data, and the code only reads it. Adding a room or item usually means editing a dictionary, not writing new logic.

## 1. World data

### `ROOMS`

A dictionary that maps a room id (such as `"cottage"`) to a dictionary of properties:

```python
"gate": {
    "name": "Iron Gate",                     # heading shown on entry
    "desc": "A towering iron gate ...",      # room description
    "exits": {"south": "forest", "north": "courtyard"},  # direction -> room id
    "items": [],                             # items currently lying here
    "locked": {"north": "The gate is locked. ..."},       # optional: blocked exits
},
```

Optional keys:

- **`dark`**: the room can't be seen into, and the only way out is `up`, until the player carries a lit lantern.
- **`locked`**: maps a direction to the message shown when the player tries to go that way. An exit is open again when its entry is deleted. The locked gate and the troll both use this mechanism.

The map is a graph: rooms are the nodes and `exits` are the links between them. Links go one way, so a two-way passage is written in both rooms.

```
                 [tower] ── crown
                    │ east
   [armory] ── [courtyard] ── troll / Shadow Knight
     west           │ south
                 [gate] ── locked
                    │ south
                 [forest] ── east ── [river] ── bread
                    │ south
                 [cottage] ── lantern (start / goal)
                    │ down
                 [cellar] ── dark; key, potion
```

### `ITEMS`

Maps an item name to its `examine` text. Item names double as their ids, which is why the player types `take key`. The item's location is not stored here. It's tracked by which list the name is in: a room's `items` or the player's `inventory`.

### Other constants

- `DIRECTIONS`: one-letter shortcuts (`n` → `north`, and so on).
- `HELP`, `COMBAT_HELP`: the help screens.
- `PLAYER_MAX_HP`, `BOSS_MAX_HP`: balance numbers kept in one place.

> **Note:** `ROOMS` is a template. Each `Game` makes its own copy with `copy.deepcopy(ROOMS)` and changes only that copy (moving items, deleting `locked` entries). That way a new game always starts fresh, even in a long-running process like the MCP server.

## 2. Game state

All state that changes during play lives on the `Game` object:

| Attribute | Purpose |
|---|---|
| `rooms` | This game's copy of `ROOMS` |
| `room` | Id of the room the player is in |
| `inventory` | List of item names the player carries |
| `lantern_lit` | Whether the lantern is lit |
| `moves` | Move counter shown when you win |
| `running` | The main loop stops when this is `False` |
| `hp` | Player health (only used in combat) |
| `in_combat` | Whether commands go to the combat handler |
| `boss_hp`, `boss_alive` | Shadow Knight health and whether it has been defeated |
| `boss_shrouded` | Whether the shadow shroud is up (50% miss chance, boss heals) |
| `boss_turn`, `boss_charging` | Counter and flag for the heavy-attack pattern |

The `here` property is shorthand for `self.rooms[self.room]`. `is_dark()` puts the darkness rule in one place, so movement, `take` and `examine` all apply it the same way.

## 3. Command processing

```
run()  ──input()──▶  handle(line)  ──▶  in_combat? ──yes──▶ combat(verb, arg)
                                        │
                                        no
                                        ▼
                                  verb dispatch ──▶ go / take / drop / examine / ...
```

### The parser (`handle`)

The parser is a simple verb + object reader:

1. The line is lowercased and split into words.
2. Filler words (`the`, `a`, `an`, `to`, `at`) are dropped, so `give the bread to the troll` becomes `give bread troll`.
3. The first word is the **verb**, and the rest is joined into the **argument**.
4. An `if/elif` chain picks the handler. Synonyms are grouped as tuples, e.g. `("take", "get", "grab")`.

Unknown verbs don't count as moves (`self.moves -= 1`), so typos don't add to your score.

The `if/elif` chain was chosen over a dispatch dictionary because the handlers take different arguments and some verbs have special cases, such as `feed troll bread`. With this few verbs, the chain is easy to read.

### Command handlers

Each command is a method that checks its conditions and prints a message for each way it can fail:

```python
def unlock(self, target):
    if self.room != "gate":                         print("There's nothing to unlock here.")
    elif "north" not in self.here.get("locked", {}): print("The gate is already open.")
    elif "key" not in self.inventory:               print("You need a key.")
    else:                                           # success: remove the lock
```

The guard clauses come first and the success case comes last. This keeps every failure message easy to find.

## 4. Puzzles

Each puzzle is a world-data condition plus a command that clears it:

| Puzzle | Blocking mechanism | Solved by |
|---|---|---|
| Dark cellar | `"dark": True` + `is_dark()` | `light lantern` (sets `lantern_lit`) |
| Iron gate | `locked["north"]` in `gate` | `unlock` with `key` in inventory, which deletes the entry |
| Troll | `locked["east"]` in `courtyard` | `give bread`, which deletes the entry |
| Shadow Knight | `in_combat` captures all input | Bring its HP to 0 |

Because locks are just dictionary entries, a new blocked path needs one `locked` entry and one command that deletes it.

## 5. The boss fight

### Trigger

`go()` starts the fight after moving the player, when all three are true: the player is in the courtyard, carries the crown, and the boss is alive. Only the return trip triggers it, so the player first explores the courtyard and finds the armory.

### Combat mode

While `in_combat` is true, `handle()` sends every command to `combat()`. That handler accepts only fight commands, so the player can't walk away mid-fight except with `flee`.

Each player action that uses a turn (attack, defend, shine, drink) is followed by one boss turn. Free actions (`inventory`, `status`, `help`) and failed actions (shining an unlit lantern) `return` early, so the boss doesn't act.

```
player action ──▶ boss dead? ──yes──▶ victory, leave combat
                     │
                     no
                     ▼
                boss_attack(defending) ──▶ player dead? ──yes──▶ game over
```

### Boss behavior (`boss_attack`)

Each boss turn runs in this order:

1. **Regenerate**: if still shrouded, heal 2 HP.
2. **Heavy strike**: if it charged last turn, deal 14 damage, or 0 if the player defended.
3. **Telegraph**: every third turn, start charging instead of attacking.
4. **Normal attack**: 4–7 damage, −2 with a shield, halved when defending.

### Design goals

The fight should reward using the game's mechanics rather than pressing `attack` over and over:

- **Lantern**: the item that solved the first puzzle is also the key to the boss. Shining it removes the miss chance and the healing.
- **Sword and shield**: the sword makes damage possible at all (punches do 1). The shield lowers the knight's normal hits.
- **Warning before the heavy hit**: the charge message gives the player one turn to react. Defending blocks the whole hit.
- **Potion**: one heal, for when a mistake is made.

These rough win rates came from 2,000 simulated fights per setup:

| Setup | Win rate |
|---|---|
| All gear, using shine and defend | 100% |
| All gear, attack only | ~4% |
| Never shining the lantern | ~26% |
| No sword | 0% |

## 6. Output

`say()` wraps prose at 72 columns with `textwrap.fill`, so long descriptions read well in any terminal. Short status lines (`Exits:`, `Health:`) use plain `print`.

## 7. Win and lose conditions

- **Win**: `check_win()` runs after every move. Reaching the cottage with the crown ends the game and shows the move count. The Shadow Knight guards the only way back, so a win always means it was defeated.
- **Lose**: HP drops to 0 in `boss_attack()`.
- **Quit**: `quit`, Ctrl+C or end of input (EOF). All three set `running = False` or break out of the loop cleanly.

## 8. MCP server

`mcp_server.py` lets AI assistants play over the Model Context Protocol. It uses the `FastMCP` helper from the official `mcp` Python SDK and talks over stdio.

It reuses `Game` without changing how the game prints:

- **Output capture:** with stdio, stdout carries the MCP protocol itself. So every game call runs inside `contextlib.redirect_stdout`, and the captured text becomes the tool result. `intro()` was split out of `run()` so the server can show the opening without the input loop.
- **One game per server:** a stdio server serves a single client, so a module-level `game` variable holds the current game.
- **Tools:** `new_game` creates a fresh `Game`. `play` passes a command to `handle()`, starting a game first if none is running, and adds a note when the game ends. `get_state` returns structured data. It respects darkness, so it doesn't reveal what's in an unlit room.
- **End of game:** `outcome()` works out won, lost or quit from existing state (HP, room, inventory) instead of adding new flags to `Game`.

## Extending the game

| To add... | Do this |
|---|---|
| A room | Add an entry to `ROOMS`, and add the return exit in the neighboring room |
| An item | Add it to `ITEMS` and to a room's `items` list |
| A locked path | Add a `locked` entry, plus a command that deletes it |
| A new verb | Add a method and an `elif` branch in `handle()`, and list it in `HELP` |
| Another boss | Turn the `boss_*` attributes into an `Enemy` class so several can exist |

Ideas for when the game grows:

- Move the world data into JSON or YAML so content can change without touching code.
- Add `save` and `load` by writing `room`, `inventory` and the changed `ROOMS` to a file.
- Swap the `if/elif` chain for a `{verb: handler}` dictionary once there are many more commands.
