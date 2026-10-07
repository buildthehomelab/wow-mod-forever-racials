#!/usr/bin/env python3
"""
mod-forever-racials: write the module's client changes into a 3.3.5a (12340) client's Spell.dbc
and pack it into an MPQ, and print the server's spell_dbc rows for the new spells.

The 3.3.5 client only casts spells in its own Spell.dbc, and a patch MPQ replaces the whole file,
so the changes have to go into the Spell.dbc your realm patch already ships (patch-P on this
server). Start from that patch so its other spell changes are kept:

    python3 build_patch.py --from-mpq patch-P.MPQ --out patch-P.MPQ.new
    python3 build_patch.py --dbc Spell.dbc --out-dir DBFilesClient
    python3 build_patch.py --sql --from-mpq patch-P.MPQ   # the server's spell_dbc rows

What it changes:

- The class spells: a mastery for every class (90140-90148) and a class cooldown (90150-90159),
  plus the pet halves of Pack Fury and Fel Frenzy (90160, 90161).
- The racials that are new spells: Escape Artist's immunity (90102), Shatter Curse (90105),
  Touch of the Grave and its heal (90106, 90107) and Rapid Regeneration (90111). The server gets
  the same rows from spell_dbc.
- The kept stock racials the server changes, so their tooltips match: Stoneform, Quickness,
  Escape Artist, Hardiness, Endurance (back to stock, without the previous version's hit), and
  the profession racials (Engineering Specialization, Gemcutting, Arcane Affinity, Cultivation),
  which now make their profession faster.
- Each race shows one active and one passive: the extra kept racials (Wisp Spirit, Elusiveness,
  Underwater Breathing, Da Voodoo Shuffle, Cultivation) are hidden from the spellbook and listed
  in the tooltip of the passive they're folded into. They keep working.

The stock racials the module removes need no client change: the server takes them off.

Running it again gives the same result, so it's safe to rebuild. Packing needs StormLib
(libstorm). Point STORMLIB at it if it isn't /usr/local/lib/libstorm.dylib.

Released under the MIT License.
"""

import argparse
import ctypes
import os
import shutil
import struct
import sys
import tempfile

# Must match src/ForeverRacials.cpp and the defaults in conf/mod_forever_racials.conf.dist. If you
# change those settings, change these and build the patch again.
MASTERY_HIT_PERCENT = 2
MASTERY_CRIT_PERCENT = 2
MASTERY_SPELL_HIT_PERCENT = 4
MASTERY_SPELL_CRIT_PERCENT = 2
PROFESSION_SPEED_PERCENT = 25
STONEFORM_PHYSICAL_REDUCTION = 10
QUICKNESS_SPEED_PERCENT = 2
HARDINESS_PERCENT = 20
TOUCH_WEAPON_CHANCE = 5
TOUCH_SPELL_CHANCE = 10
TOUCH_HEAL_PERCENT = 25
TOUCH_MAX_HEALTH_PERCENT = 5

# Class cooldowns: 2 min, 15 sec each.
COOLDOWN_MS = 120000
POWER_PERCENT = 15        # attack power, spell power, healing, the demon's damage
HASTE_PERCENT = 10        # attack or casting speed
ENERGY_REGEN_PERCENT = 20
RAGE = 10                 # Battle Fury, and Wild Instinct in Bear Form
RUNIC_POWER = 15

# The weapons each physical mastery counts (item subclasses; the server reads them from the
# config, ForeverRacials.Mastery.<Class>.Weapons, so keep both the same).
WEAPONS = {
    "Warrior": [0, 1, 4, 5, 6, 7, 8, 13],
    "Paladin": [0, 1, 4, 5, 6, 7, 8],
    "Hunter": [2, 3, 18],
    "Rogue": [0, 4, 7, 13, 15],
    "DeathKnight": [0, 1, 4, 5, 6, 7, 8],
    "Shaman": [0, 1, 4, 5, 13, 15],
    "Caster": [19],
}

# --- Spells: must match the SQL (printed by --sql) and src/ForeverRacials.cpp -------------------
SPELL_ESCAPE_ARTIST_IMMUNITY = 90102
SPELL_SHATTER_CURSE = 90105
SPELL_TOUCH_OF_THE_GRAVE = 90106
SPELL_TOUCH_OF_THE_GRAVE_HEAL = 90107
SPELL_RAPID_REGENERATION = 90111

SPELL_MASTERY = {   # physical masteries, by the WEAPONS key
    "Warrior": 90140,
    "Paladin": 90141,
    "Hunter": 90142,
    "Rogue": 90143,
    "DeathKnight": 90144,
    "Shaman": 90145,
    "Caster": 90146,
}
SPELL_MASTERY_SPELL = 90147
SPELL_MASTERY_FERAL = 90148

SPELL_BATTLE_FURY = 90150
SPELL_CRUSADERS_ZEAL = 90151
SPELL_PACK_FURY = 90152
SPELL_CUTTHROAT_RUSH = 90153
SPELL_INNER_FERVOR = 90154
SPELL_GRAVE_FURY = 90155
SPELL_ANCESTRAL_FURY = 90156
SPELL_ARCANE_FERVOR = 90157
SPELL_FEL_FRENZY = 90158
SPELL_WILD_INSTINCT = 90159
SPELL_PACK_FURY_PET = 90160     # cast by the server only when there's a pet
SPELL_FEL_FRENZY_PET = 90161

# Kept stock racials the module changes.
SPELL_STONEFORM = 20594
SPELL_STONEFORM_BUFF = 65116
SPELL_QUICKNESS = 20582
SPELL_ESCAPE_ARTIST = 20589
SPELL_HARDINESS = 20573
SPELL_ENDURANCE = 20550
SPELL_REGENERATION = 20555
SPELL_ENGINEERING_SPEC = 20593
SPELL_GEMCUTTING = 28875
SPELL_ARCANE_AFFINITY = 28877
SPELL_CULTIVATION = 20552
PROFESSION_RACIALS = (SPELL_ENGINEERING_SPEC, SPELL_GEMCUTTING, SPELL_ARCANE_AFFINITY, SPELL_CULTIVATION)

# One active and one passive per race: these kept racials are hidden from the spellbook, and the
# passive they're folded into lists them in its tooltip (see TEXTS).
FOLDED = {
    20585: "Quickness",            # Wisp Spirit
    21009: "Quickness",            # Elusiveness
    5227: "Touch of the Grave",    # Underwater Breathing
    58943: "Regeneration",         # Da Voodoo Shuffle
    SPELL_CULTIVATION: "Endurance",
}

# SpellDuration.dbc
DURATION_3_SEC = 27
DURATION_8_SEC = 31
DURATION_15_SEC = 8
DURATION_20_SEC = 18

# SpellRange.dbc
RANGE_100_YARDS = 6

# --- Spell.dbc layout (3.3.5a, build 12340) -------------------------------------------------
FIELDS = 234
F_ID = 0
F_ATTRIBUTES = 4
F_ATTRIBUTES_EX2 = 6
F_ATTRIBUTES_EX3 = 7
F_STANCES = 12
F_STANCES_NOT = 14
F_RECOVERY_TIME = 29
F_PROC_CHARGES = 36
F_MAX_LEVEL = 37
F_BASE_LEVEL = 38
F_SPELL_LEVEL = 39
F_DURATION_INDEX = 40
F_RANGE_INDEX = 46
F_EQUIPPED_ITEM_CLASS = 68
F_EQUIPPED_ITEM_SUBCLASS_MASK = 69
F_EQUIPPED_ITEM_INVENTORY_TYPE_MASK = 70
F_EFFECT = 71             # 3 each from here on
F_EFFECT_DIE_SIDES = 74
F_EFFECT_REAL_POINTS_PER_LEVEL = 77
F_EFFECT_BASE_POINTS = 80
F_EFFECT_TARGET_A = 86
F_EFFECT_TARGET_B = 89
F_EFFECT_RADIUS = 92
F_EFFECT_AURA = 95
F_EFFECT_AMPLITUDE = 98
F_EFFECT_MULTIPLE_VALUE = 101
F_EFFECT_MISC_VALUE = 110
F_EFFECT_TRIGGER_SPELL = 116
F_EFFECT_CLASS_MASK = 122  # 3 words per effect
F_SPELL_VISUAL = 131
F_SPELL_ICON = 133
F_NAME = 136              # 16 locale strings, then a flags field
F_NAME_SUBTEXT = 153
F_DESCRIPTION = 170
F_AURA_DESCRIPTION = 187
F_START_RECOVERY_CATEGORY = 205
F_START_RECOVERY_TIME = 206
F_FAMILY_NAME = 208
F_FAMILY_FLAGS = 209      # 3 words
F_DMG_CLASS = 213
F_SCHOOL_MASK = 225
F_EFFECT_BONUS = 229      # 3 floats

STRING_FIELDS = [F_NAME + i for i in range(16)] + [F_NAME_SUBTEXT + i for i in range(16)] \
    + [F_DESCRIPTION + i for i in range(16)] + [F_AURA_DESCRIPTION + i for i in range(16)]
# Speed, EffectRealPointsPerLevel, EffectPointsCombo, EffectMultipleValue, DmgMultiplier,
# EffectBonusMultiplier: the float columns of AzerothCore's spell_dbc table.
FLOAT_FIELDS = {47, 77, 78, 79, 101, 102, 103, 119, 120, 121, 216, 217, 218, 229, 230, 231}

SPELL_ATTR0_DO_NOT_DISPLAY = 0x80
SPELL_ATTR2_CANT_CRIT = 0x20000000
SPELL_ATTR3_SUPPRESS_CASTER_PROCS = 0x00010000
SPELL_ATTR3_IGNORE_CASTER_MODIFIERS = 0x20000000

SPELL_EFFECT_APPLY_AURA = 6
SPELL_EFFECT_HEAL = 10
SPELL_EFFECT_ENERGIZE = 30
SPELL_EFFECT_TRIGGER_SPELL = 64
TARGET_UNIT_CASTER = 1
TARGET_UNIT_PET = 5

AURA_DUMMY = 4
AURA_MOD_DAMAGE_DONE = 13
AURA_OBS_MOD_HEALTH = 20
AURA_DISPEL_IMMUNITY = 41
AURA_MOD_WEAPON_CRIT_PERCENT = 52
AURA_MOD_HIT_CHANCE = 54
AURA_MOD_SPELL_HIT_CHANCE = 55
AURA_MOD_SPELL_CRIT_CHANCE = 57
AURA_MOD_CASTING_SPEED = 65
AURA_MECHANIC_IMMUNITY = 77
AURA_MOD_DAMAGE_PERCENT_DONE = 79
AURA_MOD_DAMAGE_PERCENT_TAKEN = 87
AURA_MOD_POWER_REGEN_PERCENT = 110
AURA_MOD_SPEED_ALWAYS = 129
AURA_MOD_HEALING_DONE = 135
AURA_MOD_MELEE_HASTE = 138
AURA_MOD_RANGED_HASTE = 140
AURA_MOD_ATTACK_POWER_PCT = 166
AURA_MOD_ATTACK_AND_CAST_SPEED = 193  # SPELL_AURA_MELEE_SLOW: attack and casting speed, like Berserking

MECHANIC_ROOT = 7
MECHANIC_SNARE = 11
DISPEL_CURSE = 2
SCHOOL_MASK_PHYSICAL = 1
SCHOOL_MASK_MAGIC = 126
SCHOOL_MASK_ALL = 127
POWER_RAGE, POWER_ENERGY, POWER_RUNIC_POWER = 1, 3, 6
ITEM_CLASS_WEAPON = 2

# Shapeshift forms, as Stances bits (1 << (form - 1)).
STANCES_CAT_AND_BEAR = (1 << 0) | (1 << 4) | (1 << 7)  # Cat Form 1, Bear Form 5, Dire Bear Form 8

# Stock spells the new ones are copied from, for their flags, visuals and icons.
TEMPLATE_RACIAL_PASSIVE = 20557  # Beast Slaying
TEMPLATE_RACIAL_ACTIVE = 20600   # Perception: instant, on the global cooldown, self buff
TEMPLATE_COOLDOWN = 20572        # Blood Fury: instant, off the global cooldown, 2 min, 15 sec
TEMPLATE_STONEFORM = 20594
TEMPLATE_LIFESTEAL = 43125       # an NPC's instant Shadow health leech: the heal's look
ICON_REMOVE_CURSE = 195
ICON_DRAIN_LIFE = 546
ICON_REGENERATION = 149
VISUAL_BLOOD_FURY = 47
VISUAL_RENEW = 280

# (icon, visual) for each new spell: the icon of a stock spell of that class, so the spellbook
# reads at a glance.
LOOKS = {
    SPELL_MASTERY["Warrior"]: (564, 0),        # Mortal Strike
    SPELL_MASTERY["Paladin"]: (2309, 0),       # Crusader Strike
    SPELL_MASTERY["Hunter"]: (2228, 0),        # Steady Shot
    SPELL_MASTERY["Rogue"]: (130, 0),          # Sinister Strike
    SPELL_MASTERY["DeathKnight"]: (2639, 0),   # Obliterate
    SPELL_MASTERY["Shaman"]: (2562, 0),        # Stormstrike
    SPELL_MASTERY["Caster"]: (677, 0),         # Shoot (wand)
    SPELL_MASTERY_SPELL: (125, 0),             # Arcane Intellect
    SPELL_MASTERY_FERAL: (2312, 0),            # Mangle (Cat)
    SPELL_BATTLE_FURY: (86, VISUAL_BLOOD_FURY),     # Bloodrage
    SPELL_CRUSADERS_ZEAL: (301, 298),               # Righteous Fury
    SPELL_PACK_FURY: (1680, VISUAL_BLOOD_FURY),     # Bestial Wrath
    SPELL_CUTTHROAT_RUSH: (515, 254),               # Slice and Dice
    SPELL_INNER_FERVOR: (101, 4372),                # Inner Focus
    SPELL_GRAVE_FURY: (2724, VISUAL_BLOOD_FURY),    # Blood Tap
    SPELL_ANCESTRAL_FURY: (2024, VISUAL_BLOOD_FURY),  # Shamanistic Rage
    SPELL_ARCANE_FERVOR: (62, 4370),                # Arcane Power
    SPELL_FEL_FRENZY: (3174, VISUAL_BLOOD_FURY),    # Demonic Empowerment
    SPELL_WILD_INSTINCT: (1181, 200),               # Tiger's Fury
}

# --- Texts ----------------------------------------------------------------------------------

def weapon_list(subclasses):
    """'Axes, Maces, Swords, Polearms and Fist Weapons' for the tooltips."""
    names = []
    pairs = [(0, 1, "Axes"), (4, 5, "Maces"), (7, 8, "Swords")]
    for one, two, name in pairs:
        if one in subclasses and two in subclasses:
            names.append(name)
        elif one in subclasses:
            names.append("One-Handed " + name)
        elif two in subclasses:
            names.append("Two-Handed " + name)
    single = {6: "Polearms", 10: "Staves", 13: "Fist Weapons", 15: "Daggers", 2: "Bows", 3: "Guns",
              18: "Crossbows", 16: "Thrown Weapons", 19: "Wands"}
    names += [single[s] for s in sorted(single) if s in subclasses]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


MASTERY_NAMES = {
    "Warrior": "Warrior Mastery", "Paladin": "Paladin Mastery", "Hunter": "Hunter Mastery",
    "Rogue": "Rogue Mastery", "DeathKnight": "Death Knight Mastery", "Shaman": "Shaman Mastery",
    "Caster": "Wand Mastery",
}

# (name, description, aura description); None leaves the stock text.
TEXTS = {
    SPELL_ESCAPE_ARTIST_IMMUNITY: ("Escape Artist", "",
        "Immune to immobilization and movement slowing effects."),
    SPELL_SHATTER_CURSE: ("Shatter Curse",
        "Shatters all curses on you and makes you immune to Curses for $d. Magical damage taken is "
        "reduced by $s2% for the duration.",
        "Immune to Curses. Magical damage taken reduced by $s2%."),
    SPELL_TOUCH_OF_THE_GRAVE: ("Touch of the Grave",
        f"Your weapon attacks have a {TOUCH_WEAPON_CHANCE}% chance and your harmful spells a "
        f"{TOUCH_SPELL_CHANCE}% chance to heal you for {TOUCH_HEAL_PERCENT}% of the damage they "
        f"dealt, up to {TOUCH_MAX_HEALTH_PERCENT}% of your maximum health. Underwater breath lasts "
        "$5227s1% longer than normal.",
        ""),
    SPELL_TOUCH_OF_THE_GRAVE_HEAL: ("Touch of the Grave", "", ""),
    SPELL_RAPID_REGENERATION: ("Rapid Regeneration",
        "Regenerates $s1% of your maximum health every $t1 sec for $d.",
        "Regenerating $s1% of maximum health every $t1 sec."),

    SPELL_MASTERY_SPELL: ("Spell Mastery",
        "Increases your chance to hit with spells by $s1% and your chance to critically hit with "
        "spells by $s2%.", ""),
    SPELL_MASTERY_FERAL: ("Feral Mastery",
        "While in Cat Form, Bear Form or Dire Bear Form, increases your chance to hit by $s2% and "
        "your chance to critically hit by $s1%.", ""),

    SPELL_BATTLE_FURY: ("Battle Fury",
        "Increases your attack power by $s1% for $d and generates $/10;s2 rage.",
        "Attack power increased by $s1%."),
    SPELL_CRUSADERS_ZEAL: ("Crusader's Zeal",
        "Increases your attack power, spell power and healing by $s1% for $d.",
        "Attack power, spell power and healing increased by $s1%."),
    SPELL_PACK_FURY: ("Pack Fury",
        "Increases your ranged attack speed and your pet's attack speed by $s1% for $d.",
        "Ranged attack speed increased by $s1%."),
    SPELL_PACK_FURY_PET: ("Pack Fury", "", "Attack speed increased by $s1%."),
    SPELL_CUTTHROAT_RUSH: ("Cutthroat Rush",
        "Increases your energy regeneration by $s1% for $d.",
        "Energy regeneration increased by $s1%."),
    SPELL_INNER_FERVOR: ("Inner Fervor",
        "Increases your casting speed by $s1% for $d.",
        "Casting speed increased by $s1%."),
    SPELL_GRAVE_FURY: ("Grave Fury",
        "Increases your attack power by $s1% for $d and generates $/10;s2 runic power.",
        "Attack power increased by $s1%."),
    SPELL_ANCESTRAL_FURY: ("Ancestral Fury",
        "Increases your attack and casting speed by $s1% for $d.",
        "Attack and casting speed increased by $s1%."),
    SPELL_ARCANE_FERVOR: ("Arcane Fervor",
        "Increases your spell power by $s1% for $d.",
        "Spell power increased by $s1%."),
    SPELL_FEL_FRENZY: ("Fel Frenzy",
        "Increases your spell power and your demon's damage by $s1% for $d.",
        "Spell power increased by $s1%."),
    SPELL_FEL_FRENZY_PET: ("Fel Frenzy", "", "Damage increased by $s1%."),
    SPELL_WILD_INSTINCT: ("Wild Instinct",
        f"Calls on your wild instincts for $d, depending on your form: Cat Form increases energy "
        f"regeneration by $s2%, Bear Form and Dire Bear Form increase attack power by $s3% and "
        f"generate {RAGE} rage, and any other form increases casting speed by $s1%.",
        "Empowered by your wild instincts."),

    SPELL_STONEFORM: (None,
        "Removes all poison, disease and bleed effects, increases your armor by $65116s1% and "
        "reduces physical damage taken by $65116s2% for $65116d.", None),
    SPELL_STONEFORM_BUFF: (None, None, "Armor increased by $s1%. Physical damage taken reduced by $s2%."),
    SPELL_QUICKNESS: (None,
        "Reduces the chance that melee and ranged attackers will hit you by $s1% and increases "
        "your movement speed by $s3%. You are harder to detect while Shadowmelded or stealthed, "
        "and turn into a wisp upon death, increasing speed by $20584s1%.", None),
    SPELL_ESCAPE_ARTIST: (None,
        "Escape the effects of any immobilization or movement speed reduction effect, and become "
        "immune to them for $90102d.", None),
    SPELL_HARDINESS: (None, "Duration of Stun effects reduced by an additional $s1%.", None),
    SPELL_ENDURANCE: (None,
        "Base Health increased by $s1%. You gather herbs $20552s1% faster.", None),
    SPELL_REGENERATION: (None,
        "Health regeneration rate increased by $s1%.  $s2% of total Health regeneration may continue "
        "during combat. The duration of movement impairing effects is reduced by $58943s1%.", None),
    SPELL_ENGINEERING_SPEC: (None, "Engineering is $s1% faster.", None),
    SPELL_GEMCUTTING: (None, "Jewelcrafting is $s1% faster.", None),
    SPELL_ARCANE_AFFINITY: (None, "Enchanting is $s1% faster.", None),
    SPELL_CULTIVATION: (None, "Herb gathering is $s1% faster.", None),
}

for key, spell_id in SPELL_MASTERY.items():
    TEXTS[spell_id] = (MASTERY_NAMES[key],
        f"Increases your chance to hit with {weapon_list(WEAPONS[key])} by $s2% and your chance to "
        "critically hit with them by $s1%.", "")

RACIAL_SUBTEXT = {SPELL_TOUCH_OF_THE_GRAVE: "Racial Passive", SPELL_SHATTER_CURSE: "Racial",
                  SPELL_RAPID_REGENERATION: "Racial"}
PASSIVE_SUBTEXT = set(SPELL_MASTERY.values()) | {SPELL_MASTERY_SPELL, SPELL_MASTERY_FERAL}


# --- DBC helpers ----------------------------------------------------------------------------

def read_dbc(path, field_count):
    with open(path, "rb") as f:
        data = f.read()
    magic, count, fields, size, strsize = struct.unpack_from("<4s4I", data, 0)
    if magic != b"WDBC" or fields != field_count or size != field_count * 4:
        sys.exit(f"{path}: not a 3.3.5a file ({fields} fields)")
    rows = [list(struct.unpack_from(f"<{fields}I", data, 20 + i * size)) for i in range(count)]
    strings = bytearray(data[20 + count * size:20 + count * size + strsize])
    return rows, strings


def write_dbc(path, rows, strings, field_count):
    rows = sorted(rows, key=lambda r: r[0])
    with open(path, "wb") as f:
        f.write(struct.pack("<4s4I", b"WDBC", len(rows), field_count, field_count * 4, len(strings)))
        for row in rows:
            f.write(struct.pack(f"<{field_count}I", *row))
        f.write(strings)


def add_string(strings, text):
    """Offset of text in the string block, appending it if it isn't there yet."""
    if not text:
        return 0
    encoded = text.encode("utf-8") + b"\0"
    at = strings.find(encoded)
    while at > 0 and strings[at - 1] != 0:  # must be a whole string, not the tail of another
        at = strings.find(encoded, at + 1)
    if at >= 0:
        return at
    at = len(strings)
    strings.extend(encoded)
    return at


def f32(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def i32(value):
    return value & 0xFFFFFFFF


def find(rows, spell_id):
    row = next((r for r in rows if r[F_ID] == spell_id), None)
    if row is None:
        sys.exit(f"spell {spell_id} not found in Spell.dbc")
    return row


def clear_effect(row, e):
    for base in (F_EFFECT, F_EFFECT_DIE_SIDES, F_EFFECT_BASE_POINTS, F_EFFECT_TARGET_A,
                 F_EFFECT_TARGET_B, F_EFFECT_RADIUS, F_EFFECT_AURA, F_EFFECT_AMPLITUDE,
                 F_EFFECT_MULTIPLE_VALUE, F_EFFECT_MISC_VALUE, F_EFFECT_TRIGGER_SPELL, F_EFFECT_BONUS):
        row[base + e] = 0
    row[F_EFFECT_REAL_POINTS_PER_LEVEL + e] = 0
    row[83 + e] = 0           # EffectMechanic
    row[104 + e] = 0          # EffectChainTarget
    row[107 + e] = 0          # EffectItemType
    row[113 + e] = 0          # EffectMiscValueB
    row[119 + e] = 0          # EffectPointsPerComboPoint
    for w in range(3):
        row[F_EFFECT_CLASS_MASK + e * 3 + w] = 0


def set_aura(row, e, aura, amount, misc=0, amplitude=0, per_level=0.0):
    """Effect e becomes an aura on the caster worth amount (DBC base points are amount - 1)."""
    clear_effect(row, e)
    row[F_EFFECT + e] = SPELL_EFFECT_APPLY_AURA
    row[F_EFFECT_AURA + e] = aura
    row[F_EFFECT_BASE_POINTS + e] = i32(amount - 1)
    row[F_EFFECT_DIE_SIDES + e] = 1
    row[F_EFFECT_MISC_VALUE + e] = i32(misc)
    row[F_EFFECT_AMPLITUDE + e] = amplitude
    row[F_EFFECT_REAL_POINTS_PER_LEVEL + e] = f32(per_level)
    row[F_EFFECT_TARGET_A + e] = TARGET_UNIT_CASTER


def clear_all_effects(row):
    for e in range(3):
        clear_effect(row, e)


def copy(rows, template, spell_id, icon=None, visual=None):
    row = list(find(rows, template))
    row[F_ID] = spell_id
    row[F_FAMILY_NAME] = 0
    row[F_FAMILY_FLAGS:F_FAMILY_FLAGS + 3] = [0, 0, 0]
    # Perception may only be cast out of form (or in two NPC forms); racials work in any form.
    row[F_STANCES] = row[F_STANCES_NOT] = 0
    if icon is not None:
        row[F_SPELL_ICON] = icon
    if visual is not None:
        row[F_SPELL_VISUAL] = visual
    clear_all_effects(row)
    return row


def set_effect(row, e, effect, amount, misc=0, target=TARGET_UNIT_CASTER):
    """Effect e becomes a non-aura effect worth amount (DBC base points are amount - 1)."""
    clear_effect(row, e)
    row[F_EFFECT + e] = effect
    row[F_EFFECT_BASE_POINTS + e] = i32(amount - 1)
    row[F_EFFECT_DIE_SIDES + e] = 1
    row[F_EFFECT_MISC_VALUE + e] = i32(misc)
    row[F_EFFECT_TARGET_A + e] = target


def set_cooldown(rows, spell_id, effects):
    """A class cooldown: Blood Fury's flags (instant, off the global cooldown), 2 min, 15 sec.
    effects: (aura, amount, misc, target) per effect; aura None means an energize instead."""
    icon, visual = LOOKS[spell_id]
    s = copy(rows, TEMPLATE_COOLDOWN, spell_id, icon=icon, visual=visual)
    s[F_RECOVERY_TIME] = COOLDOWN_MS
    s[F_DURATION_INDEX] = DURATION_15_SEC
    s[F_EQUIPPED_ITEM_CLASS] = i32(-1)
    s[F_EQUIPPED_ITEM_SUBCLASS_MASK] = s[F_EQUIPPED_ITEM_INVENTORY_TYPE_MASK] = 0
    for e, (aura, amount, misc, target) in enumerate(effects):
        if aura is None:
            set_effect(s, e, SPELL_EFFECT_ENERGIZE, amount, misc=misc, target=target)
        else:
            set_aura(s, e, aura, amount, misc=misc)
            s[F_EFFECT_TARGET_A + e] = target
    return s


def set_pet_buff(rows, spell_id, parent_id, aura, amount, misc=0):
    """The pet's half of a class cooldown: the same look, no cooldown of its own, 15 sec."""
    icon, visual = LOOKS[parent_id]
    s = copy(rows, TEMPLATE_COOLDOWN, spell_id, icon=icon, visual=visual)
    s[F_RECOVERY_TIME] = 0
    s[F_DURATION_INDEX] = DURATION_15_SEC
    s[F_EQUIPPED_ITEM_CLASS] = i32(-1)
    s[F_EQUIPPED_ITEM_SUBCLASS_MASK] = s[F_EQUIPPED_ITEM_INVENTORY_TYPE_MASK] = 0
    s[F_RANGE_INDEX] = RANGE_100_YARDS  # like Bestial Wrath and Demonic Empowerment
    set_aura(s, 0, aura, amount, misc=misc)
    s[F_EFFECT_TARGET_A] = TARGET_UNIT_PET
    return s


def set_mastery(rows, spell_id, item_class=-1, subclass_mask=0, stances=0):
    icon, _ = LOOKS[spell_id]
    s = copy(rows, TEMPLATE_RACIAL_PASSIVE, spell_id, icon=icon)
    s[F_EQUIPPED_ITEM_CLASS] = i32(item_class)
    s[F_EQUIPPED_ITEM_SUBCLASS_MASK] = subclass_mask
    s[F_EQUIPPED_ITEM_INVENTORY_TYPE_MASK] = 0
    s[F_STANCES] = stances
    return s


# --- The new spells -------------------------------------------------------------------------

def new_spells(rows):
    spells = []
    C = TARGET_UNIT_CASTER

    # Gnome: Escape Artist triggers this, 3 sec of root and snare immunity.
    s = copy(rows, TEMPLATE_RACIAL_ACTIVE, SPELL_ESCAPE_ARTIST_IMMUNITY, icon=find(rows, SPELL_ESCAPE_ARTIST)[F_SPELL_ICON],
             visual=0)
    s[F_RECOVERY_TIME] = 0
    s[F_START_RECOVERY_CATEGORY] = s[F_START_RECOVERY_TIME] = 0
    s[F_DURATION_INDEX] = DURATION_3_SEC
    set_aura(s, 0, AURA_MECHANIC_IMMUNITY, 1, misc=MECHANIC_ROOT)
    set_aura(s, 1, AURA_MECHANIC_IMMUNITY, 1, misc=MECHANIC_SNARE)
    spells.append(s)

    # Orc active, Stoneform's twin: curse immunity (which also removes curses you have, like
    # Stoneform's poison and disease immunity) and 10% less magic damage taken for 8 sec.
    s = copy(rows, TEMPLATE_STONEFORM, SPELL_SHATTER_CURSE, icon=ICON_REMOVE_CURSE, visual=VISUAL_BLOOD_FURY)
    s[F_DURATION_INDEX] = DURATION_8_SEC
    set_aura(s, 0, AURA_DISPEL_IMMUNITY, 0, misc=DISPEL_CURSE)
    set_aura(s, 1, AURA_MOD_DAMAGE_PERCENT_TAKEN, -10, misc=SCHOOL_MASK_MAGIC)
    spells.append(s)

    # Undead passive: the server's script rolls the chance and casts the heal.
    s = copy(rows, TEMPLATE_RACIAL_PASSIVE, SPELL_TOUCH_OF_THE_GRAVE, icon=ICON_DRAIN_LIFE)
    set_aura(s, 0, AURA_DUMMY, 0)
    spells.append(s)

    # The heal, with the shadowy look of a health leech. The server sets the amount; it can't
    # crit, ignores the caster's healing bonuses and triggers no procs.
    s = list(find(rows, TEMPLATE_LIFESTEAL))
    s[F_ID] = SPELL_TOUCH_OF_THE_GRAVE_HEAL
    s[F_SPELL_ICON] = ICON_DRAIN_LIFE
    s[F_MAX_LEVEL] = 0
    s[F_BASE_LEVEL] = s[F_SPELL_LEVEL] = 1
    s[F_DMG_CLASS] = 0
    s[F_ATTRIBUTES_EX2] |= SPELL_ATTR2_CANT_CRIT
    s[F_ATTRIBUTES_EX3] |= SPELL_ATTR3_IGNORE_CASTER_MODIFIERS | SPELL_ATTR3_SUPPRESS_CASTER_PROCS
    clear_all_effects(s)
    set_effect(s, 0, SPELL_EFFECT_HEAL, 1)
    s[F_EFFECT_DIE_SIDES] = 0
    s[F_EFFECT_MULTIPLE_VALUE] = f32(1.0)
    spells.append(s)

    # Troll active: 5% of max health every 2 sec for 20 sec (50% in all), 3 min cooldown. Unlike
    # Cannibalize, moving, acting or taking damage doesn't stop it.
    s = copy(rows, TEMPLATE_RACIAL_ACTIVE, SPELL_RAPID_REGENERATION, icon=ICON_REGENERATION, visual=VISUAL_RENEW)
    s[F_RECOVERY_TIME] = 180000
    s[F_DURATION_INDEX] = DURATION_20_SEC
    set_aura(s, 0, AURA_OBS_MOD_HEALTH, 5, amplitude=2000)
    spells.append(s)

    # Class masteries. Physical: crit (effect 0) and hit (effect 1) with the class's weapons; the
    # crit only counts for the hand doing the attack. The server sets the weapons from its config.
    for key, spell_id in SPELL_MASTERY.items():
        mask = sum(1 << subclass for subclass in WEAPONS[key])
        s = set_mastery(rows, spell_id, item_class=ITEM_CLASS_WEAPON, subclass_mask=mask)
        set_aura(s, 0, AURA_MOD_WEAPON_CRIT_PERCENT, MASTERY_CRIT_PERCENT)
        set_aura(s, 1, AURA_MOD_HIT_CHANCE, MASTERY_HIT_PERCENT)
        spells.append(s)

    s = set_mastery(rows, SPELL_MASTERY_SPELL)
    set_aura(s, 0, AURA_MOD_SPELL_HIT_CHANCE, MASTERY_SPELL_HIT_PERCENT, misc=SCHOOL_MASK_ALL)
    set_aura(s, 1, AURA_MOD_SPELL_CRIT_CHANCE, MASTERY_SPELL_CRIT_PERCENT)
    spells.append(s)

    # Druids in Cat and Bear Form, whatever they hold: the core puts form passives up and takes
    # them down as the druid shifts.
    s = set_mastery(rows, SPELL_MASTERY_FERAL, stances=STANCES_CAT_AND_BEAR)
    set_aura(s, 0, AURA_MOD_WEAPON_CRIT_PERCENT, MASTERY_CRIT_PERCENT)
    set_aura(s, 1, AURA_MOD_HIT_CHANCE, MASTERY_HIT_PERCENT)
    spells.append(s)

    # Class cooldowns. Spell power and healing amounts are percents; the server's script turns
    # them into that share of the caster's own.
    spells.append(set_cooldown(rows, SPELL_BATTLE_FURY, [
        (AURA_MOD_ATTACK_POWER_PCT, POWER_PERCENT, 0, C),
        (None, RAGE * 10, POWER_RAGE, C)]))
    spells.append(set_cooldown(rows, SPELL_CRUSADERS_ZEAL, [
        (AURA_MOD_ATTACK_POWER_PCT, POWER_PERCENT, 0, C),
        (AURA_MOD_DAMAGE_DONE, POWER_PERCENT, SCHOOL_MASK_MAGIC, C),
        (AURA_MOD_HEALING_DONE, POWER_PERCENT, SCHOOL_MASK_ALL, C)]))
    # The pet halves are spells of their own, cast by the server's script only when there's a
    # pet: an effect aimed at the pet on the main spell would make it fail without one.
    spells.append(set_cooldown(rows, SPELL_PACK_FURY, [
        (AURA_MOD_RANGED_HASTE, HASTE_PERCENT, 0, C)]))
    spells.append(set_pet_buff(rows, SPELL_PACK_FURY_PET, SPELL_PACK_FURY, AURA_MOD_MELEE_HASTE, HASTE_PERCENT))
    spells.append(set_cooldown(rows, SPELL_CUTTHROAT_RUSH, [
        (AURA_MOD_POWER_REGEN_PERCENT, ENERGY_REGEN_PERCENT, POWER_ENERGY, C)]))
    spells.append(set_cooldown(rows, SPELL_INNER_FERVOR, [
        (AURA_MOD_CASTING_SPEED, HASTE_PERCENT, 0, C)]))
    spells.append(set_cooldown(rows, SPELL_GRAVE_FURY, [
        (AURA_MOD_ATTACK_POWER_PCT, POWER_PERCENT, 0, C),
        (None, RUNIC_POWER * 10, POWER_RUNIC_POWER, C)]))
    spells.append(set_cooldown(rows, SPELL_ANCESTRAL_FURY, [
        (AURA_MOD_ATTACK_AND_CAST_SPEED, HASTE_PERCENT, 0, C)]))
    spells.append(set_cooldown(rows, SPELL_ARCANE_FERVOR, [
        (AURA_MOD_DAMAGE_DONE, POWER_PERCENT, SCHOOL_MASK_MAGIC, C)]))
    spells.append(set_cooldown(rows, SPELL_FEL_FRENZY, [
        (AURA_MOD_DAMAGE_DONE, POWER_PERCENT, SCHOOL_MASK_MAGIC, C)]))
    spells.append(set_pet_buff(rows, SPELL_FEL_FRENZY_PET, SPELL_FEL_FRENZY, AURA_MOD_DAMAGE_PERCENT_DONE, POWER_PERCENT,
                               misc=SCHOOL_MASK_ALL))
    # Only the effect for the druid's form counts (the server zeroes the others).
    spells.append(set_cooldown(rows, SPELL_WILD_INSTINCT, [
        (AURA_MOD_CASTING_SPEED, HASTE_PERCENT, 0, C),
        (AURA_MOD_POWER_REGEN_PERCENT, ENERGY_REGEN_PERCENT, POWER_ENERGY, C),
        (AURA_MOD_ATTACK_POWER_PCT, POWER_PERCENT, 0, C)]))

    return spells


def patch_existing(rows):
    """The kept stock racials the server changes, so their tooltips (and $s values) match."""
    for spell_id in FOLDED:
        find(rows, spell_id)[F_ATTRIBUTES] |= SPELL_ATTR0_DO_NOT_DISPLAY

    set_aura(find(rows, SPELL_STONEFORM_BUFF), 1, AURA_MOD_DAMAGE_PERCENT_TAKEN,
             -STONEFORM_PHYSICAL_REDUCTION, misc=SCHOOL_MASK_PHYSICAL)

    set_aura(find(rows, SPELL_QUICKNESS), 2, AURA_MOD_SPEED_ALWAYS, QUICKNESS_SPEED_PERCENT)

    row = find(rows, SPELL_ESCAPE_ARTIST)
    clear_effect(row, 1)
    row[F_EFFECT + 1] = SPELL_EFFECT_TRIGGER_SPELL
    row[F_EFFECT_TARGET_A + 1] = TARGET_UNIT_CASTER
    row[F_EFFECT_TRIGGER_SPELL + 1] = SPELL_ESCAPE_ARTIST_IMMUNITY

    find(rows, SPELL_HARDINESS)[F_EFFECT_BASE_POINTS] = i32(-HARDINESS_PERCENT - 1)

    # Endurance is stock again: the previous version gave it hit in effects 1 and 2.
    row = find(rows, SPELL_ENDURANCE)
    clear_effect(row, 1)
    clear_effect(row, 2)

    # The profession racials: the server turns the skill bonus into a cast time cut. The client
    # only needs the number for the tooltips.
    for spell_id in PROFESSION_RACIALS:
        set_aura(find(rows, spell_id), 0, AURA_DUMMY, PROFESSION_SPEED_PERCENT)


def set_texts(row, strings):
    name, description, aura_description = TEXTS.get(row[F_ID], (None, None, None))
    if name is not None:
        for i in range(16):
            row[F_NAME + i] = 0
        row[F_NAME] = add_string(strings, name)
    if description is not None:
        for i in range(16):
            row[F_DESCRIPTION + i] = 0
        row[F_DESCRIPTION] = add_string(strings, description)
    if aura_description is not None:
        for i in range(16):
            row[F_AURA_DESCRIPTION + i] = 0
        row[F_AURA_DESCRIPTION] = add_string(strings, aura_description)


def set_subtext(row, strings):
    """New racials read "Racial" or "Racial Passive" under their name, like the stock ones, and
    the masteries "Passive"."""
    for i in range(16):
        row[F_NAME_SUBTEXT + i] = 0
    if row[F_ID] in RACIAL_SUBTEXT:
        row[F_NAME_SUBTEXT] = add_string(strings, RACIAL_SUBTEXT[row[F_ID]])
    elif row[F_ID] in PASSIVE_SUBTEXT:
        row[F_NAME_SUBTEXT] = add_string(strings, "Passive")


def build_new_spells(rows, strings):
    """The new spells with their texts. Built from stock rows, so call it before replacing any."""
    added = new_spells(rows)
    for spell in added:
        set_texts(spell, strings)
        set_subtext(spell, strings)
    return added


def patch_spell_dbc(src, dst):
    rows, strings = read_dbc(src, FIELDS)

    added = build_new_spells(rows, strings)
    rows = [r for r in rows if r[F_ID] not in {s[F_ID] for s in added}]
    rows.extend(added)

    patch_existing(rows)
    for spell_id in TEXTS:
        if spell_id not in {s[F_ID] for s in added}:
            set_texts(find(rows, spell_id), strings)

    write_dbc(dst, rows, strings, FIELDS)
    print(f"{dst}: new spells {', '.join(str(s[F_ID]) for s in added)} "
          "and the changed stock racials")


# --- SQL ------------------------------------------------------------------------------------

def sql_value(field, value):
    if field in STRING_FIELDS:
        return "''"
    if field in FLOAT_FIELDS:
        return repr(round(struct.unpack("<f", struct.pack("<I", value))[0], 6))
    return str(struct.unpack("<i", struct.pack("<I", value))[0])


def print_sql(dbc):
    rows, strings = read_dbc(dbc, FIELDS)
    added = build_new_spells(rows, strings)
    print(f"DELETE FROM `spell_dbc` WHERE `ID` IN ({', '.join(str(s[F_ID]) for s in added)});")
    print("INSERT INTO `spell_dbc` VALUES")
    lines = []
    for row in added:
        values = [sql_value(i, v) for i, v in enumerate(row)]
        values[F_NAME] = "'" + TEXTS[row[F_ID]][0].replace("'", "''") + "'"
        lines.append("(" + ", ".join(values) + ")")
    print(",\n".join(lines) + ";")


# --- MPQ ------------------------------------------------------------------------------------

def stormlib():
    lib = ctypes.CDLL(os.environ.get("STORMLIB", "/usr/local/lib/libstorm.dylib"))
    handle = ctypes.c_void_p
    lib.SFileOpenArchive.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(handle)]
    lib.SFileCreateArchive.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(handle)]
    lib.SFileExtractFile.argtypes = [handle, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    lib.SFileAddFileEx.argtypes = [handle, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
    lib.SFileCloseArchive.argtypes = [handle]

    class FindData(ctypes.Structure):
        _fields_ = [("cFileName", ctypes.c_char * 1024), ("szPlainName", ctypes.c_char_p),
                    ("dwHashIndex", ctypes.c_uint), ("dwBlockIndex", ctypes.c_uint),
                    ("dwFileSize", ctypes.c_uint), ("dwFileFlags", ctypes.c_uint),
                    ("dwCompSize", ctypes.c_uint), ("dwFileTimeLo", ctypes.c_uint),
                    ("dwFileTimeHi", ctypes.c_uint), ("lcLocale", ctypes.c_uint)]

    lib.SFileFindFirstFile.argtypes = [handle, ctypes.c_char_p, ctypes.POINTER(FindData), ctypes.c_char_p]
    lib.SFileFindFirstFile.restype = handle
    lib.SFileFindNextFile.argtypes = [handle, ctypes.POINTER(FindData)]
    lib.SFileFindClose.argtypes = [handle]
    return lib, handle, FindData


def extract_all(mpq, folder):
    lib, handle, FindData = stormlib()
    h = handle()
    if not lib.SFileOpenArchive(mpq.encode(), 0, 0x100, ctypes.byref(h)):
        sys.exit(f"can't open {mpq}")

    names = []
    found = FindData()
    search = lib.SFileFindFirstFile(h, b"*", ctypes.byref(found), None)
    while search:
        names.append(found.cFileName.decode())
        if not lib.SFileFindNextFile(search, ctypes.byref(found)):
            break
    if search:
        lib.SFileFindClose(search)

    files = []
    for name in names:
        if name in ("(listfile)", "(attributes)", "(signature)"):
            continue
        dst = os.path.join(folder, *name.split("\\"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not lib.SFileExtractFile(h, name.encode(), dst.encode(), 0):
            sys.exit(f"can't extract {name}")
        files.append((dst, name))
    lib.SFileCloseArchive(h)
    return files


def pack(out, files):
    lib, handle, _ = stormlib()
    if os.path.exists(out):
        os.remove(out)
    h = handle()
    # MPQ v1 with a listfile and attributes; each file zlib-compressed, like the realm's patches.
    if not lib.SFileCreateArchive(out.encode(), 0x00300000, max(16, len(files) * 2), ctypes.byref(h)):
        sys.exit(f"can't create {out}")
    for src, name in files:
        if not lib.SFileAddFileEx(h, src.encode(), name.encode(), 0x80000200, 0x02, 0x02):
            sys.exit(f"can't add {name}")
    lib.SFileCloseArchive(h)


def mpq_file(files, name):
    return next((f for f in files if f[1].lower() == name.lower()), None)


def build_mpq(src_mpq, out):
    folder = tempfile.mkdtemp(prefix="forever-racials-")
    try:
        files = extract_all(src_mpq, folder)
        spell = mpq_file(files, "DBFilesClient\\Spell.dbc")
        if spell is None:
            sys.exit(f"{src_mpq} has no DBFilesClient\\Spell.dbc; use --dbc with the client's own file")
        patch_spell_dbc(spell[0], spell[0])
        # Keep the original order, with Spell.dbc last as the realm's patch-P has it.
        files.sort(key=lambda f: f[1].lower() == "dbfilesclient\\spell.dbc")
        pack(out, files)
        print(f"{out}: {', '.join(name for _, name in files)}")
    finally:
        shutil.rmtree(folder)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-mpq", help="patch MPQ that already ships Spell.dbc")
    parser.add_argument("--out", help="MPQ to write (with --from-mpq)")
    parser.add_argument("--dbc", help="a Spell.dbc to start from")
    parser.add_argument("--out-dir", help="where to write Spell.dbc (with --dbc)")
    parser.add_argument("--sql", action="store_true", help="print the server's spell_dbc SQL")
    args = parser.parse_args()

    if args.sql:
        dbc = args.dbc
        folder = None
        if not dbc and args.from_mpq:
            folder = tempfile.mkdtemp(prefix="forever-racials-")
            dbc = mpq_file(extract_all(args.from_mpq, folder), "DBFilesClient\\Spell.dbc")[0]
        if not dbc:
            sys.exit("--sql needs --dbc or --from-mpq")
        print_sql(dbc)
        if folder:
            shutil.rmtree(folder)
    elif args.from_mpq and args.out:
        build_mpq(args.from_mpq, args.out)
    elif args.dbc and args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)
        patch_spell_dbc(args.dbc, os.path.join(args.out_dir, "Spell.dbc"))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
