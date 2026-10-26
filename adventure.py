#!/usr/bin/env python3
"""The Lost Crown - a small text adventure for the command line."""

import copy
import random
import textwrap

DIRECTIONS = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "u": "up", "d": "down",
}

ROOMS = {
    "cottage": {
        "name": "Old Cottage",
        "desc": "You stand in a dusty cottage. A trapdoor in the floor leads down, "
                "and the front door opens north onto a forest path.",
        "exits": {"north": "forest", "down": "cellar"},
        "items": ["lantern"],
    },
    "cellar": {
        "name": "Cellar",
        "desc": "A damp cellar lined with empty shelves. Stairs lead back up.",
        "exits": {"up": "cottage"},
        "items": ["key", "potion"],
        "dark": True,
    },
    "forest": {
        "name": "Forest Path",
        "desc": "Tall pines whisper around you. The cottage lies south. "
                "You hear running water to the east, and see an iron gate to the north.",
        "exits": {"south": "cottage", "east": "river", "north": "gate"},
        "items": [],
    },
    "river": {
        "name": "Riverbank",
        "desc": "A clear river rushes past. Someone has abandoned a picnic here. "
                "The forest path is west.",
        "exits": {"west": "forest"},
        "items": ["bread"],
    },
    "gate": {
        "name": "Iron Gate",
        "desc": "A towering iron gate blocks the way north into a ruined castle. "
                "The forest path is south.",
        "exits": {"south": "forest", "north": "courtyard"},
        "items": [],
        "locked": {"north": "The gate is locked. There's a keyhole crusted with rust."},
    },
    "courtyard": {
        "name": "Castle Courtyard",
        "desc": "Weeds sprout between cracked flagstones. A crumbling tower rises to the east, "
                "and a collapsed armory lies to the west. The gate is south.",
        "exits": {"south": "gate", "east": "tower", "west": "armory"},
        "items": [],
        "locked": {"east": "A hungry troll blocks the tower door, growling at you."},
    },
    "armory": {
        "name": "Ruined Armory",
        "desc": "Broken racks and rusted helmets litter the floor. A few pieces "
                "look like they might still be useful. The courtyard is east.",
        "exits": {"east": "courtyard"},
        "items": ["sword", "shield"],
    },
    "tower": {
        "name": "Tower Chamber",
        "desc": "Moonlight streams through a broken window onto a stone pedestal. "
                "The courtyard is west.",
        "exits": {"west": "courtyard"},
        "items": ["crown"],
    },
}

ITEMS = {
    "lantern": "An old oil lantern. It still has some oil in it.",
    "key": "A heavy, rusty iron key.",
    "bread": "A crusty loaf of bread. Smells delicious.",
    "crown": "The Lost Crown, glittering with rubies. Bring it home!",
    "potion": "A small vial of glowing red liquid. Drinking it would heal you.",
    "sword": "A knight's longsword. Still sharp despite the years.",
    "shield": "A dented steel shield. It would soften a blow.",
}

PLAYER_MAX_HP = 25
BOSS_MAX_HP = 30

COMBAT_HELP = """
You are in combat! Commands:
  attack          strike with your weapon
  defend          brace yourself and block
  shine lantern   blast the shadows with lantern light
  drink potion    restore your health
  flee            retreat east into the tower
  inventory (i)   see what you carry
  status          check health
"""

HELP = """
Commands:
  go <direction>  (or n, s, e, w, up, down)
  look            describe the room again
  examine <item>  look closely at something
  take <item>     pick something up
  drop <item>     put something down
  inventory (i)   see what you carry
  light lantern   light your lantern
  unlock gate     use a key on a locked gate
  give <item>     give an item to someone
  drink <item>    drink something
  status          check your health
  help            show this message
  quit            leave the game
"""


def say(text):
    print(textwrap.fill(text, width=72))


class Game:
    def __init__(self):
        # each game gets its own copy of the world, so items and locks reset
        self.rooms = copy.deepcopy(ROOMS)
        self.room = "cottage"
        self.inventory = []
        self.lantern_lit = False
        self.moves = 0
        self.running = True
        self.hp = PLAYER_MAX_HP
        self.boss_hp = BOSS_MAX_HP
        self.boss_alive = True
        self.boss_shrouded = True
        self.boss_turn = 0
        self.boss_charging = False
        self.in_combat = False

    # --- helpers -----------------------------------------------------------
    @property
    def here(self):
        return self.rooms[self.room]

    def is_dark(self):
        return self.here.get("dark") and not ("lantern" in self.inventory and self.lantern_lit)

    def describe(self):
        print()
        print(f"== {self.here['name']} ==")
        if self.is_dark():
            say("It is pitch black. You can't see a thing. The stairs lead up.")
            return
        say(self.here["desc"])
        if self.room == "courtyard" and "east" in self.here.get("locked", {}):
            say("A huge, hungry-looking troll guards the tower door.")
        if self.here["items"]:
            print("You see: " + ", ".join(self.here["items"]))
        print("Exits: " + ", ".join(self.here["exits"]))

    # --- commands ----------------------------------------------------------
    def go(self, direction):
        direction = DIRECTIONS.get(direction, direction)
        if not direction:
            print("Go where?")
            return
        if direction not in self.here["exits"]:
            print("You can't go that way.")
            return
        if self.is_dark() and direction != "up":
            print("You stumble around in the dark and find nothing.")
            return
        locked = self.here.get("locked", {})
        if direction in locked:
            say(locked[direction])
            return
        self.room = self.here["exits"][direction]
        self.describe()
        if self.room == "courtyard" and "crown" in self.inventory and self.boss_alive:
            self.start_combat()
        self.check_win()

    def take(self, item):
        if self.is_dark():
            print("You fumble in the dark but can't find anything.")
        elif item in self.here["items"]:
            self.here["items"].remove(item)
            self.inventory.append(item)
            print(f"Taken: {item}.")
        else:
            print(f"There is no {item} here.")

    def drop(self, item):
        if item in self.inventory:
            self.inventory.remove(item)
            self.here["items"].append(item)
            print(f"Dropped: {item}.")
        else:
            print(f"You don't have a {item}.")

    def examine(self, item):
        visible = self.inventory + ([] if self.is_dark() else self.here["items"])
        if item in visible:
            say(ITEMS[item])
            if item == "lantern":
                print("It is lit." if self.lantern_lit else "It is not lit.")
        elif item == "troll" and self.room == "courtyard" and "east" in self.here.get("locked", {}):
            say("Its stomach rumbles loudly. Maybe it would accept some food?")
        else:
            print("You don't see that here.")

    def show_inventory(self):
        if self.inventory:
            print("You carry: " + ", ".join(self.inventory))
        else:
            print("You are empty-handed.")

    def light(self, item):
        if item != "lantern":
            print("You can't light that.")
        elif "lantern" not in self.inventory:
            print("You don't have a lantern.")
        elif self.lantern_lit:
            print("It's already lit.")
        else:
            self.lantern_lit = True
            print("The lantern flickers to life, casting a warm glow.")
            if self.here.get("dark"):
                self.describe()

    def unlock(self, target):
        if self.room != "gate":
            print("There's nothing to unlock here.")
        elif "north" not in self.here.get("locked", {}):
            print("The gate is already open.")
        elif "key" not in self.inventory:
            print("You need a key.")
        else:
            del self.here["locked"]["north"]
            say("With a grinding screech, the rusty key turns. The gate swings open!")

    def give(self, item):
        if self.room != "courtyard" or "east" not in self.here.get("locked", {}):
            print("There's no one here to give anything to.")
        elif item not in self.inventory:
            print(f"You don't have a {item}.")
        elif item != "bread":
            print("The troll sniffs it, then shoves it back at you with a snarl.")
        else:
            self.inventory.remove("bread")
            del self.here["locked"]["east"]
            say("The troll snatches the bread, devours it, and wanders off "
                "to nap in the weeds. The tower door is clear!")

    def drink(self, item):
        if item != "potion":
            print("You can't drink that.")
        elif "potion" not in self.inventory:
            print("You don't have a potion.")
        else:
            self.inventory.remove("potion")
            healed = min(15, PLAYER_MAX_HP - self.hp)
            self.hp += healed
            print(f"Warmth floods through you. (+{healed} HP, now {self.hp}/{PLAYER_MAX_HP})")
            return True
        return False

    def status(self):
        print(f"Health: {self.hp}/{PLAYER_MAX_HP}")
        if self.in_combat:
            print(f"Shadow Knight: {self.boss_hp}/{BOSS_MAX_HP}")

    # --- boss fight --------------------------------------------------------
    def start_combat(self):
        self.in_combat = True
        print()
        say("The air turns ice cold. Shadows pour from the cracks in the "
            "flagstones and knit together into a towering armored figure. "
            "THE SHADOW KNIGHT raises its black blade: \"The crown belongs "
            "to the dead. You will not leave with it.\"")
        if self.boss_shrouded:
            say("Its body flickers, wrapped in a shroud of living darkness.")
        print("(Type 'help' for combat commands.)")
        self.status()

    def player_attack(self):
        if self.boss_shrouded and random.random() < 0.5:
            say("Your strike passes straight through the shifting shadows! "
                "If only you could see it clearly...")
            return
        if "sword" in self.inventory:
            dmg = random.randint(5, 9)
            say(f"You slash the Shadow Knight with your sword for {dmg} damage!")
        else:
            dmg = 1
            say("You punch the Shadow Knight's armor. Ouch. It barely notices. "
                "(1 damage - you need a real weapon!)")
        self.boss_hp -= dmg

    def shine(self, item):
        if item != "lantern" or "lantern" not in self.inventory:
            print("You have nothing to shine.")
            return False
        if not self.lantern_lit:
            print("Your lantern isn't lit.")
            return False
        if not self.boss_shrouded:
            say("You wave the lantern. The knight is already fully exposed.")
            return True
        self.boss_shrouded = False
        say("You hold the lantern high. Its glow tears through the shroud, and "
            "the Shadow Knight shrieks as its true, solid form is revealed!")
        return True

    def boss_attack(self, defending):
        self.boss_turn += 1
        if self.boss_shrouded and self.boss_hp < BOSS_MAX_HP:
            self.boss_hp = min(BOSS_MAX_HP, self.boss_hp + 2)
            say("The shadows swirl and knit the Shadow Knight's wounds closed.")
        if self.boss_charging:
            self.boss_charging = False
            if defending:
                say("The Shadow Knight brings its blade crashing down, but you "
                    "block the devastating blow!")
                return
            dmg = 14
            say(f"The Shadow Knight's blade crashes down on you for {dmg} damage!")
        elif self.boss_turn % 3 == 0:
            self.boss_charging = True
            say("The Shadow Knight lifts its blade high, gathering dark energy... "
                "(It's about to strike hard. Defend!)")
            return
        else:
            dmg = random.randint(4, 7)
            if "shield" in self.inventory:
                dmg -= 2
            if defending:
                dmg //= 2
            say(f"The Shadow Knight slashes at you for {dmg} damage.")
        self.hp -= dmg
        if self.hp <= 0:
            print()
            say("You fall to the cold stones as darkness swallows you. The crown "
                "rolls from your hand back into the shadows...")
            print("\n*** GAME OVER ***")
            self.running = False

    def combat(self, verb, arg):
        defending = False
        if verb in ("attack", "hit", "fight", "strike"):
            self.player_attack()
        elif verb in ("defend", "block"):
            defending = True
            print("You raise your guard.")
        elif verb in ("shine", "light"):
            if not self.shine(arg or "lantern"):
                return
        elif verb == "drink":
            if not self.drink(arg or "potion"):
                return
        elif verb in ("flee", "run"):
            self.in_combat = False
            self.boss_charging = False
            self.room = "tower"
            say("You flee back into the tower. The Shadow Knight waits in the courtyard.")
            self.describe()
            return
        elif verb in ("inventory", "i", "inv"):
            self.show_inventory()
            return
        elif verb in ("status", "hp", "health"):
            self.status()
            return
        elif verb in ("help", "h", "?"):
            print(COMBAT_HELP)
            return
        elif verb in ("quit", "exit", "q"):
            print("Farewell, adventurer.")
            self.running = False
            return
        else:
            print("No time for that! Type 'help' for combat commands.")
            return

        if self.boss_hp <= 0:
            self.in_combat = False
            self.boss_alive = False
            print()
            say("The Shadow Knight staggers, its armor cracking with light. With a "
                "final howl it bursts into a thousand fading wisps of shadow. "
                "The courtyard is silent. The way home is clear.")
            return
        self.boss_attack(defending)
        if self.running:
            self.status()

    def check_win(self):
        if self.room == "cottage" and "crown" in self.inventory:
            print()
            say("You set the Lost Crown on the cottage table. It gleams in the "
                "lantern light. The kingdom's treasure is home at last!")
            print(f"\n*** YOU WIN in {self.moves} moves! ***")
            self.running = False

    # --- main loop ---------------------------------------------------------
    def handle(self, line):
        words = line.lower().split()
        if not words:
            return
        # drop filler words like "the" and "to"
        words = [w for w in words if w not in ("the", "a", "an", "to", "at")]
        verb, arg = words[0], " ".join(words[1:])
        self.moves += 1

        if self.in_combat:
            self.combat(verb, arg)
            return

        if verb in DIRECTIONS or verb in DIRECTIONS.values():
            self.go(verb)
        elif verb in ("go", "walk", "move"):
            self.go(arg)
        elif verb in ("look", "l"):
            self.describe()
        elif verb in ("take", "get", "grab"):
            self.take(arg)
        elif verb == "drop":
            self.drop(arg)
        elif verb in ("examine", "x", "inspect"):
            self.examine(arg)
        elif verb in ("inventory", "i", "inv"):
            self.show_inventory()
        elif verb in ("light", "ignite"):
            self.light(arg)
        elif verb in ("unlock", "open"):
            self.unlock(arg)
        elif verb in ("give", "feed"):
            # "feed troll bread" / "give bread troll"
            item = "bread" if "bread" in words else arg.replace("troll", "").strip()
            self.give(item)
        elif verb == "drink":
            self.drink(arg)
        elif verb == "shine":
            print("You wave the lantern around. Nothing happens.")
        elif verb in ("status", "hp", "health"):
            self.status()
        elif verb in ("help", "h", "?"):
            print(HELP)
        elif verb in ("quit", "exit", "q"):
            print("Farewell, adventurer.")
            self.running = False
        else:
            print("I don't understand that. Type 'help' for commands.")
            self.moves -= 1

    def intro(self):
        print("=" * 40)
        print("        THE LOST CROWN")
        print("=" * 40)
        say("Legend says a crown lies hidden in the ruined castle beyond the "
            "forest. Find it and bring it back to your cottage.")
        print("Type 'help' for a list of commands.")
        self.describe()

    def run(self):
        self.intro()
        while self.running:
            try:
                line = input("\n> ")
            except (EOFError, KeyboardInterrupt):
                print("\nFarewell, adventurer.")
                break
            self.handle(line)


if __name__ == "__main__":
    Game().run()
