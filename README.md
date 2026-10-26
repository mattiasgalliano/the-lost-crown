# The Lost Crown

A text adventure game you play in the terminal, written in Python.

Legend says a crown lies hidden in a ruined castle beyond the forest. Explore, solve puzzles, defeat the Shadow Knight, and bring the crown back to your cottage.

```
== Castle Courtyard ==
Weeds sprout between cracked flagstones. A crumbling tower rises to the
east, and a collapsed armory lies to the west. The gate is south.
Exits: south, east, west

> 
```

## How to play

You need Python 3.8 or newer. There's nothing else to install.

```
git clone https://github.com/mattiasgalliano/the-lost-crown.git
cd the-lost-crown
python adventure.py
```

## Commands

| Command | What it does |
|---|---|
| `n`, `s`, `e`, `w`, `up`, `down` (or `go north`) | Move |
| `look` | Describe the room again |
| `examine <item>` (or `x`) | Look closely at something |
| `take <item>` / `drop <item>` | Pick up or put down an item |
| `inventory` (or `i`) | See what you carry |
| `light lantern` | Light your lantern |
| `unlock gate` | Use a key on a locked gate |
| `give <item>` | Give an item to someone |
| `drink <item>` | Drink something |
| `status` | Check your health |
| `help` | List the commands |
| `quit` | Leave the game |

Small words like "the" and "to" are ignored, so `give the bread to the troll` works.

### Combat

When the boss appears, only these commands work:

| Command | What it does |
|---|---|
| `attack` | Strike with your weapon |
| `defend` | Brace yourself and block |
| `shine lantern` | Blast the shadows with lantern light |
| `drink potion` | Restore your health |
| `flee` | Retreat into the tower |

Just attacking won't get you far. Look for the boss's weaknesses, and watch for its warnings.

## Features

- Seven rooms to explore
- Puzzles: a dark cellar, a locked gate and a hungry troll
- A turn-based boss fight with health, a weapon, a shield and a healing potion
- Plain-English commands with shortcuts and synonyms

## How the code works

See [DESIGN.md](DESIGN.md) for how the game is structured: the world data, the command parser, the puzzles, the boss fight, and how to add your own rooms and items.
