#!/usr/bin/env python3
"""
mod-forever-racials: update the racial list the character creation screen shows, and pack it
into its own patch MPQ.

The character creation screen doesn't read Spell.dbc. Its list of racials comes from the
ABILITY_INFO_<RACE><n> strings in the client's Interface\\GlueXML\\GlueStrings.lua, so patch-P
can't change it. This script rewrites those strings to the module's 2 active + 2 passive kits
and leaves every other string alone:

    python3 build_glue_patch.py --glue GlueStrings.lua --out patch-Q.MPQ

Start from the GlueStrings.lua your players already have: on the Evermore client that's the
stock one in Data/enUS/patch-enUS-3.MPQ (--from-mpq reads it straight from there). The whole file
is replaced in the client, so any other changes in it must be in the file you start from, and the
patch's letter has to sort after any other patch that ships GlueStrings.lua.

Heads-up: the 3.3.5 client may refuse changed GlueXML files ("interface files corrupt") unless it
runs a Wow.exe that allows interface edits. Test it on one client before handing it out, and ship
it as its own optional patch rather than inside patch-P.

Packing needs StormLib (libstorm), like build_patch.py.

Released under the MIT License.
"""

import argparse
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_patch  # noqa: E402  (StormLib helpers)

GLUE_STRINGS = "Interface\\GlueXML\\GlueStrings.lua"

# The client's race file names. Undead is "SCOURGE". Blood Elves and Draenei aren't changed by the
# module, so their stock lines stay.
ABILITIES = {
    "HUMAN": [
        "Can break out of speed altering and trapping effects.",
        "Stealth detection increased.",
        "Increased critical chance with Swords and Maces.",
        "Increased Spirit.",
    ],
    "DWARF": [
        "May take on a stone form, reducing physical damage.",
        "Treasure finding.",
        "Increased critical chance with Maces and Guns.",
        "Damage increased versus beasts. Resistant to Frost.",
    ],
    "NIGHTELF": [
        "May fade into the shadows.",
        "May call on Elune's light to increase critical chance.",
        "More difficult to hit. Movement speed increased.",
        "Wisp form while dead for faster movement. Resistant to Nature damage.",
    ],
    "GNOME": [
        "May escape from speed altering effects.",
        "Eureka! Next spells cost less and deal more damage or healing.",
        "Increased Intellect and maximum mana, rage, energy and runic power.",
        "Engineering skill increased. Resistant to Arcane damage.",
    ],
    "ORC": [
        "May enrage to increase attack power and spell power.",
        "May shatter curses and resist magical damage.",
        "Increased critical chance with Axes and Fist weapons.",
        "Resistant to stun effects. Damage done by pets increased.",
    ],
    "SCOURGE": [
        "Can remove fear, sleep, and charm.",
        "May consume corpses to regain health and mana.",
        "Attacks and spells may drain health from the target. Resistant to Shadow damage.",
        "Underwater breathing increased.",
    ],
    "TAUREN": [
        "May stomp, stunning nearby opponents.",
        "May grow herbs anyone can gather. Herbalism skill increased.",
        "Maximum health and chance to hit increased.",
        "Movement speed builds while moving. Resistant to Nature damage.",
    ],
    "TROLL": [
        "Berserk, increasing attack and casting speed.",
        "May rapidly regenerate health.",
        "Regeneration increased. Reduced duration of movement reducing effects.",
        "Damage increased versus beasts. Increased critical chance with Bows and Throwing Weapons.",
    ],
}

LINE = re.compile(r'^ABILITY_INFO_([A-Z]+?)(\d+) = ".*";\r?$')


def lua_string(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def rewrite(text):
    """GlueStrings.lua with the module's races' ABILITY_INFO lines replaced, in the same place."""
    newline = "\r\n" if "\r\n" in text else "\n"
    out = []
    written = set()
    for line in text.split(newline):
        match = LINE.match(line)
        if not match or match.group(1) not in ABILITIES:
            out.append(line)
            continue
        race = match.group(1)
        if race in written:
            continue  # the race's other stock lines (the list stops at the first missing number)
        written.add(race)
        for n, ability in enumerate(ABILITIES[race], 1):
            out.append(f'ABILITY_INFO_{race}{n} = "- {lua_string(ability)}";')

    missing = set(ABILITIES) - written
    if missing:
        sys.exit(f"no ABILITY_INFO lines for {', '.join(sorted(missing))}; is this GlueStrings.lua?")
    return newline.join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--glue", help="the GlueStrings.lua to start from")
    source.add_argument("--from-mpq", help="an MPQ that ships Interface\\GlueXML\\GlueStrings.lua")
    parser.add_argument("--out", required=True, help="MPQ to write, or a .lua file to write the text only")
    args = parser.parse_args()

    folder = tempfile.mkdtemp(prefix="forever-racials-glue-")
    try:
        path = args.glue
        if args.from_mpq:
            found = build_patch.mpq_file(build_patch.extract_all(args.from_mpq, folder), GLUE_STRINGS)
            if found is None:
                sys.exit(f"{args.from_mpq} has no {GLUE_STRINGS}")
            path = found[0]

        with open(path, encoding="utf-8", newline="") as f:
            text = rewrite(f.read())

        if args.out.lower().endswith(".lua"):
            with open(args.out, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            print(f"{args.out}: racial lists updated")
            return

        lua = os.path.join(folder, "GlueStrings.lua")
        with open(lua, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        build_patch.pack(args.out, [(lua, GLUE_STRINGS)])
        print(f"{args.out}: {GLUE_STRINGS} with the racial lists updated")
    finally:
        shutil.rmtree(folder)


if __name__ == "__main__":
    main()
