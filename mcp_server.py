#!/usr/bin/env python3
"""MCP server for The Lost Crown.

Lets an MCP client (Claude Code, Claude Desktop, ...) play the game through
tools. Runs over stdio, so the game's printed output is captured and returned
as tool results instead of going to stdout, which carries the MCP protocol.
"""

import contextlib
import io

from mcp.server.fastmcp import FastMCP

from adventure import BOSS_MAX_HP, ITEMS, PLAYER_MAX_HP, Game

mcp = FastMCP("the-lost-crown", log_level="WARNING")
game = None


def capture(fn, *args):
    """Run a game method and return everything it printed."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args)
    return buf.getvalue().strip()


def outcome():
    if game.running:
        return "playing"
    if game.hp <= 0:
        return "lost"
    if game.room == "cottage" and "crown" in game.inventory:
        return "won"
    return "quit"


def footer():
    result = outcome()
    if result == "playing":
        return ""
    return f"\n\n[Game {result}. Call new_game to play again.]"


@mcp.tool()
def new_game() -> str:
    """Start a new game of The Lost Crown (discarding any game in progress).

    Returns the opening text and the first room description.
    """
    global game
    game = Game()
    return capture(game.intro)


@mcp.tool()
def play(command: str) -> str:
    """Send one command to the game and return what happens.

    Commands are plain English, as typed in the terminal version: e.g.
    "go north", "n", "take lantern", "examine key", "inventory", "light lantern",
    "unlock gate", "give bread", "drink potion", "help". During the boss fight:
    "attack", "defend", "shine lantern", "drink potion", "flee".
    Starts a new game first if none is running.
    """
    global game
    prefix = ""
    if game is None or not game.running:
        prefix = new_game() + "\n\n> " + command + "\n"
    if not command.strip():
        return prefix + "Type a command, e.g. 'look' or 'help'."
    return prefix + capture(game.handle, command) + footer()


@mcp.tool()
def get_state() -> dict:
    """Return the current game state as structured data: location, exits,
    visible items, inventory, health, and boss status during combat."""
    if game is None:
        return {"status": "no game", "hint": "Call new_game to start."}
    dark = game.is_dark()
    state = {
        "status": outcome(),
        "room": game.here["name"],
        "exits": [] if dark else list(game.here["exits"]),
        "items_here": [] if dark else list(game.here["items"]),
        "dark": bool(dark),
        "inventory": {item: ITEMS[item] for item in game.inventory},
        "lantern_lit": game.lantern_lit,
        "hp": f"{game.hp}/{PLAYER_MAX_HP}",
        "moves": game.moves,
        "in_combat": game.in_combat,
    }
    if game.in_combat:
        state["boss"] = {
            "name": "Shadow Knight",
            "hp": f"{game.boss_hp}/{BOSS_MAX_HP}",
            "shrouded": game.boss_shrouded,
            "charging_heavy_attack": game.boss_charging,
        }
    return state


@mcp.prompt()
def adventure() -> str:
    """Play The Lost Crown as the adventurer."""
    return (
        "Let's play The Lost Crown, a text adventure. Call new_game to begin, "
        "then use the play tool to send one command at a time. Narrate briefly "
        "what happens after each command, and explore, solve puzzles, and try "
        "to bring the crown home. Ask me before making big decisions."
    )


if __name__ == "__main__":
    mcp.run()
