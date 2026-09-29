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

- Twelve new spells, 90100-90111 (see NEW SPELLS below): Big Game Hunter, Elune's Light, Escape
  Artist's immunity, Eureka!, Expansive Mind's hidden power bonus, Shatter Curse, Touch of the
  Grave (the passive and the drain), Plainsrunning (the passive and the speed buff), Cultivation
  and Rapid Regeneration. The server gets the same rows from spell_dbc.
- The existing racials the server changes: the Human, Dwarf and Orc weapon specializations give
  crit instead of expertise, The Human Spirit gives 5% Spirit, Stoneform also cuts physical damage,
  Quickness adds run speed, Escape Artist adds its immunity, Expansive Mind adds max mana, Blood
  Fury gives attack power and spell power, Hardiness is 20%, Cannibalize restores mana too and
  Endurance adds hit. The client uses these for tooltips; the server decides what they do.

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
WEAPON_CRIT_PERCENT = 2
HUMAN_SPIRIT_PERCENT = 5
STONEFORM_PHYSICAL_REDUCTION = 10
QUICKNESS_SPEED_PERCENT = 2
EXPANSIVE_MIND_POWER_PERCENT = 5
BLOOD_FURY_PERCENT = 10
HARDINESS_PERCENT = 20
CANNIBALIZE_MANA_PERCENT = 7
ENDURANCE_HIT_PERCENT = 1
TOUCH_WEAPON_CHANCE = 5
TOUCH_SPELL_CHANCE = 10
TOUCH_POWER_PERCENT = 25
TOUCH_MAX_HEALTH_PERCENT = 5
PLAINSRUNNING_MAX_STACKS = 5
CULTIVATION_MINUTES = 2

# --- New spells: must match the SQL (printed by --sql) and src/ForeverRacials.cpp ---------------
SPELL_BIG_GAME_HUNTER = 90100
SPELL_ELUNES_LIGHT = 90101
SPELL_ESCAPE_ARTIST_IMMUNITY = 90102
SPELL_EUREKA = 90103
SPELL_EXPANSIVE_MIND_POWER = 90104
SPELL_SHATTER_CURSE = 90105
SPELL_TOUCH_OF_THE_GRAVE = 90106
SPELL_TOUCH_OF_THE_GRAVE_DRAIN = 90107
SPELL_PLAINSRUNNING = 90108
SPELL_PLAINSRUNNING_SPEED = 90109
SPELL_CULTIVATION = 90110
SPELL_RAPID_REGENERATION = 90111

# Existing racials the module changes.
SPELL_HUMAN_SWORD_SPEC = 20597
SPELL_HUMAN_MACE_SPEC = 20864
SPELL_DWARF_MACE_SPEC = 59224
SPELL_ORC_AXE_SPEC = 20574
SPELL_HUMAN_SPIRIT = 20598
SPELL_STONEFORM = 20594
SPELL_STONEFORM_BUFF = 65116
SPELL_QUICKNESS = 20582
SPELL_ESCAPE_ARTIST = 20589
SPELL_EXPANSIVE_MIND = 20591
SPELL_BLOOD_FURY_AP = 20572      # warriors, rogues, hunters, death knights
SPELL_BLOOD_FURY_BOTH = 33697    # shamans
SPELL_BLOOD_FURY_SP = 33702      # mages, warlocks
SPELL_HARDINESS = 20573
SPELL_CANNIBALIZE = 20577
SPELL_CANNIBALIZE_HEAL = 20578
SPELL_ENDURANCE = 20550

# SpellDuration.dbc
DURATION_3_SEC = 27
DURATION_8_SEC = 31
DURATION_10_SEC = 1
DURATION_15_SEC = 8
DURATION_20_SEC = 18
DURATION_INFINITE = 21

# --- Spell.dbc layout (3.3.5a, build 12340) -------------------------------------------------
FIELDS = 234
F_ID = 0
F_DISPEL = 2
F_ATTRIBUTES = 4
F_ATTRIBUTES_EX = 5       # Ex1..Ex7 follow
F_ATTRIBUTES_EX2 = 6
F_ATTRIBUTES_EX3 = 7
F_STANCES = 12
F_STANCES_NOT = 14
F_RECOVERY_TIME = 29
F_CATEGORY_RECOVERY_TIME = 30
F_AURA_INTERRUPT_FLAGS = 32
F_PROC_FLAGS = 34
F_PROC_CHANCE = 35
F_PROC_CHARGES = 36
F_MAX_LEVEL = 37
F_BASE_LEVEL = 38
F_SPELL_LEVEL = 39
F_DURATION_INDEX = 40
F_STACK_AMOUNT = 49
F_EQUIPPED_ITEM_CLASS = 68
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

SPELL_ATTR0_PASSIVE = 0x40
SPELL_ATTR0_DO_NOT_DISPLAY = 0x80
SPELL_ATTR0_ONLY_OUTDOORS = 0x8000
SPELL_ATTR2_CANT_CRIT = 0x20000000
SPELL_ATTR3_SUPPRESS_CASTER_PROCS = 0x00010000
SPELL_ATTR3_ALWAYS_HIT = 0x00040000
SPELL_ATTR3_IGNORE_CASTER_MODIFIERS = 0x20000000

SPELL_EFFECT_APPLY_AURA = 6
SPELL_EFFECT_DUMMY = 3
SPELL_EFFECT_TRIGGER_SPELL = 64
TARGET_UNIT_CASTER = 1

AURA_DUMMY = 4
AURA_OBS_MOD_HEALTH = 20
AURA_OBS_MOD_POWER = 21
AURA_MOD_DAMAGE_DONE = 13
AURA_DISPEL_IMMUNITY = 41
AURA_MOD_WEAPON_CRIT_PERCENT = 52
AURA_MOD_HIT_CHANCE = 54
AURA_MOD_SPELL_HIT_CHANCE = 55
AURA_MOD_SPELL_CRIT_CHANCE = 57
AURA_MOD_POWER_COST_SCHOOL_PCT = 72
AURA_MECHANIC_IMMUNITY = 77
AURA_MOD_DAMAGE_PERCENT_DONE = 79
AURA_MOD_DAMAGE_PERCENT_TAKEN = 87
AURA_MOD_ATTACK_POWER = 99
AURA_MOD_RANGED_ATTACK_POWER = 124
AURA_MOD_SPEED_ALWAYS = 129
AURA_MOD_INCREASE_ENERGY_PERCENT = 132
AURA_MOD_HEALING_DONE = 135
AURA_MOD_HEALING_DONE_PERCENT = 136
AURA_MOD_STUN_DURATION = 232  # SPELL_AURA_MECHANIC_DURATION_MOD
AURA_PERIODIC_DUMMY = 226
AURA_MOD_CRIT_PCT = 290

MECHANIC_ROOT = 7
MECHANIC_SNARE = 11
DISPEL_CURSE = 2
SCHOOL_MASK_PHYSICAL = 1
SCHOOL_MASK_MAGIC = 126
SCHOOL_MASK_ALL = 127
POWER_MANA, POWER_RAGE, POWER_ENERGY, POWER_RUNIC_POWER = 0, 1, 3, 6

# Stock spells the new ones are copied from, for their flags, visuals and icons.
TEMPLATE_RACIAL_PASSIVE = 20557  # Beast Slaying
TEMPLATE_RACIAL_ACTIVE = 20600   # Perception: instant, on the global cooldown, self buff
TEMPLATE_STONEFORM = 20594
TEMPLATE_LIFESTEAL = 43125       # an NPC's instant Shadow health leech, range "anywhere"
ICON_TRACK_BEASTS = 179
ICON_ELUNES_BLESSING = 1829
ICON_REMOVE_CURSE = 195
ICON_ENGINEERING = 353
ICON_DRAIN_LIFE = 546
ICON_DASH = 959
ICON_CULTIVATION = 1626
ICON_REGENERATION = 149
VISUAL_ELUNES_BLESSING = 7454
VISUAL_ARCANE_POWER = 4370
VISUAL_BLOOD_FURY = 47
VISUAL_REJUVENATION = 32
VISUAL_RENEW = 280

# --- Texts ----------------------------------------------------------------------------------
# (name, description, aura description); None leaves the stock text.
WEAPON_SPEC = ("Your chance to critically hit with melee and ranged attacks and spells is increased "
               "by {pct}% while you have {weapons} equipped.")

TEXTS = {
    SPELL_BIG_GAME_HUNTER: ("Big Game Hunter", "Damage dealt versus Beasts increased by $s1%.", ""),
    SPELL_ELUNES_LIGHT: ("Elune's Light",
        "Calls down Elune's light, increasing your chance to critically hit with melee and ranged "
        "attacks and spells by $s1% for $d.",
        "Critical strike chance increased by $s1%."),
    SPELL_ESCAPE_ARTIST_IMMUNITY: ("Escape Artist", "",
        "Immune to immobilization and movement slowing effects."),
    SPELL_EUREKA: ("Eureka!",
        "A flash of gnomish genius makes your next 3 spells or abilities within $d cost $s3% less "
        "and deal $s1% more damage or healing.",
        "Spells and abilities cost $s3% less and deal $s1% more damage or healing."),
    SPELL_EXPANSIVE_MIND_POWER: ("Expansive Mind", "", ""),
    SPELL_SHATTER_CURSE: ("Shatter Curse",
        "Shatters all curses on you and makes you immune to Curses for $d. Magical damage taken is "
        "reduced by $s2% for the duration.",
        "Immune to Curses. Magical damage taken reduced by $s2%."),
    SPELL_TOUCH_OF_THE_GRAVE: ("Touch of the Grave",
        f"Your weapon attacks have a {TOUCH_WEAPON_CHANCE}% chance and your harmful spells a "
        f"{TOUCH_SPELL_CHANCE}% chance to drain the target, dealing Shadow damage equal to "
        f"{TOUCH_POWER_PERCENT}% of your attack power or spell power, whichever is higher, and "
        f"healing you for the same amount. The drain can't exceed {TOUCH_MAX_HEALTH_PERCENT}% of "
        "your maximum health.",
        ""),
    SPELL_TOUCH_OF_THE_GRAVE_DRAIN: ("Touch of the Grave", "", ""),
    SPELL_PLAINSRUNNING: ("Plainsrunning",
        f"Each second you keep moving increases your movement speed by 1%, up to "
        f"{PLAINSRUNNING_MAX_STACKS}%. Stopping resets it.",
        ""),
    SPELL_PLAINSRUNNING_SPEED: ("Plainsrunning", "",
        "Movement speed increased by $s1% for each second spent moving."),
    SPELL_CULTIVATION: ("Cultivation",
        f"Grows a herb out of the ground in front of you, matched to your level. Anyone can gather "
        f"it without Herbalism. It withers after {CULTIVATION_MINUTES} min.",
        ""),
    SPELL_RAPID_REGENERATION: ("Rapid Regeneration",
        "Regenerates $s1% of your maximum health every $t1 sec for $d.",
        "Regenerating $s1% of maximum health every $t1 sec."),

    SPELL_HUMAN_SWORD_SPEC: (None, WEAPON_SPEC.format(pct=WEAPON_CRIT_PERCENT, weapons="a Sword"), None),
    SPELL_HUMAN_MACE_SPEC: (None, WEAPON_SPEC.format(pct=WEAPON_CRIT_PERCENT, weapons="a Mace"), None),
    SPELL_DWARF_MACE_SPEC: (None, WEAPON_SPEC.format(pct=WEAPON_CRIT_PERCENT, weapons="a Mace"), None),
    SPELL_ORC_AXE_SPEC: (None, WEAPON_SPEC.format(pct=WEAPON_CRIT_PERCENT, weapons="an Axe or Fist Weapon"), None),
    SPELL_STONEFORM: (None,
        "Removes all poison, disease and bleed effects, increases your armor by $65116s1% and "
        "reduces physical damage taken by $65116s2% for $65116d.", None),
    SPELL_STONEFORM_BUFF: (None, None, "Armor increased by $s1%. Physical damage taken reduced by $s2%."),
    SPELL_QUICKNESS: (None,
        "Reduces the chance that melee and ranged attackers will hit you by $s1% and increases "
        "your movement speed by $s3%.", None),
    SPELL_ESCAPE_ARTIST: (None,
        "Escape the effects of any immobilization or movement speed reduction effect, and become "
        "immune to them for $90102d.", None),
    SPELL_EXPANSIVE_MIND: (None,
        "Intellect increased by $s1%. Maximum mana, rage, energy and runic power increased by $s2%.", None),
    SPELL_BLOOD_FURY_AP: (None,
        f"Increases attack power and spell power by {BLOOD_FURY_PERCENT}%, or by $s1 attack power and $s3 "
        "spell power if that's more. Lasts $d.",
        "Attack power and spell power increased."),
    SPELL_BLOOD_FURY_BOTH: (None,
        f"Increases attack power and spell power by {BLOOD_FURY_PERCENT}%, or by $s1 attack power and $s2 "
        "spell power if that's more. Lasts $d.",
        "Attack power and spell power increased."),
    SPELL_BLOOD_FURY_SP: (None,
        f"Increases attack power and spell power by {BLOOD_FURY_PERCENT}%, or by $s1 attack power and $s2 "
        "spell power if that's more. Lasts $d.",
        "Attack power and spell power increased."),
    SPELL_CANNIBALIZE: (None,
        "When activated, regenerates $20578s1% of total health and mana every $20578t1 sec for "
        "$20578d.  Only works on Humanoid or Undead corpses within $a1 yds.  Any movement, action, "
        "or damage taken while Cannibalizing will cancel the effect.", None),
    SPELL_CANNIBALIZE_HEAL: (None, None, "Regenerate $s1% of total health and mana every $t1 seconds."),
    SPELL_ENDURANCE: (None, "Base Health increased by $s1%. Chance to hit with all attacks and spells "
                            "increased by $s2%.", None),
}


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


# --- The new spells -------------------------------------------------------------------------

def new_spells(rows):
    spells = []

    # Dwarf passive: Beast Slaying's copy.
    s = copy(rows, TEMPLATE_RACIAL_PASSIVE, SPELL_BIG_GAME_HUNTER, icon=ICON_TRACK_BEASTS)
    set_aura(s, 0, 168, 5, misc=1)  # SPELL_AURA_MOD_DAMAGE_DONE_VERSUS, creature type mask: Beast
    spells.append(s)

    # Night Elf active: +10% crit for 15 sec, 2 min cooldown.
    s = copy(rows, TEMPLATE_RACIAL_ACTIVE, SPELL_ELUNES_LIGHT, icon=ICON_ELUNES_BLESSING,
             visual=VISUAL_ELUNES_BLESSING)
    s[F_RECOVERY_TIME] = 120000
    s[F_DURATION_INDEX] = DURATION_15_SEC
    set_aura(s, 0, AURA_MOD_CRIT_PCT, 10)
    spells.append(s)

    # Gnome: Escape Artist triggers this, 3 sec of root and snare immunity.
    s = copy(rows, TEMPLATE_RACIAL_ACTIVE, SPELL_ESCAPE_ARTIST_IMMUNITY, icon=find(rows, SPELL_ESCAPE_ARTIST)[F_SPELL_ICON],
             visual=0)
    s[F_RECOVERY_TIME] = 0
    s[F_START_RECOVERY_CATEGORY] = s[F_START_RECOVERY_TIME] = 0
    s[F_DURATION_INDEX] = DURATION_3_SEC
    set_aura(s, 0, AURA_MECHANIC_IMMUNITY, 1, misc=MECHANIC_ROOT)
    set_aura(s, 1, AURA_MECHANIC_IMMUNITY, 1, misc=MECHANIC_SNARE)
    spells.append(s)

    # Gnome active: next 3 spells or abilities cost 25% less and do 10% more, 20 sec, 2 min.
    s = copy(rows, TEMPLATE_RACIAL_ACTIVE, SPELL_EUREKA, icon=ICON_ENGINEERING, visual=VISUAL_ARCANE_POWER)
    s[F_RECOVERY_TIME] = 120000
    s[F_DURATION_INDEX] = DURATION_20_SEC
    s[F_PROC_CHARGES] = 3
    set_aura(s, 0, AURA_MOD_DAMAGE_PERCENT_DONE, 10, misc=SCHOOL_MASK_ALL)
    set_aura(s, 1, AURA_MOD_HEALING_DONE_PERCENT, 10)
    set_aura(s, 2, AURA_MOD_POWER_COST_SCHOOL_PCT, -25, misc=SCHOOL_MASK_ALL)
    spells.append(s)

    # Gnome passive, hidden: the rage, energy and runic power half of Expansive Mind (the stock
    # spell carries the mana half; a spell has only three effects).
    s = copy(rows, TEMPLATE_RACIAL_PASSIVE, SPELL_EXPANSIVE_MIND_POWER, icon=find(rows, SPELL_EXPANSIVE_MIND)[F_SPELL_ICON])
    s[F_ATTRIBUTES] |= SPELL_ATTR0_DO_NOT_DISPLAY
    set_aura(s, 0, AURA_MOD_INCREASE_ENERGY_PERCENT, EXPANSIVE_MIND_POWER_PERCENT, misc=POWER_RAGE)
    set_aura(s, 1, AURA_MOD_INCREASE_ENERGY_PERCENT, EXPANSIVE_MIND_POWER_PERCENT, misc=POWER_ENERGY)
    set_aura(s, 2, AURA_MOD_INCREASE_ENERGY_PERCENT, EXPANSIVE_MIND_POWER_PERCENT, misc=POWER_RUNIC_POWER)
    spells.append(s)

    # Orc active, Stoneform's twin: curse immunity (which also removes curses you have, like
    # Stoneform's poison and disease immunity) and 10% less magic damage taken for 8 sec.
    s = copy(rows, TEMPLATE_STONEFORM, SPELL_SHATTER_CURSE, icon=ICON_REMOVE_CURSE, visual=VISUAL_BLOOD_FURY)
    s[F_DURATION_INDEX] = DURATION_8_SEC
    set_aura(s, 0, AURA_DISPEL_IMMUNITY, 0, misc=DISPEL_CURSE)
    set_aura(s, 1, AURA_MOD_DAMAGE_PERCENT_TAKEN, -10, misc=SCHOOL_MASK_MAGIC)
    spells.append(s)

    # Undead passive: the server's script rolls the chance and casts the drain.
    s = copy(rows, TEMPLATE_RACIAL_PASSIVE, SPELL_TOUCH_OF_THE_GRAVE, icon=ICON_DRAIN_LIFE)
    set_aura(s, 0, AURA_DUMMY, 0)
    spells.append(s)

    # The drain: Shadow damage that heals the caster for 100% of it. The server sets the amount;
    # it always hits, can't crit, ignores the caster's damage bonuses and triggers no procs.
    s = list(find(rows, TEMPLATE_LIFESTEAL))
    s[F_ID] = SPELL_TOUCH_OF_THE_GRAVE_DRAIN
    s[F_SPELL_ICON] = ICON_DRAIN_LIFE
    s[F_MAX_LEVEL] = 0
    s[F_BASE_LEVEL] = s[F_SPELL_LEVEL] = 1
    s[F_ATTRIBUTES_EX2] |= SPELL_ATTR2_CANT_CRIT
    s[F_ATTRIBUTES_EX3] |= SPELL_ATTR3_ALWAYS_HIT | SPELL_ATTR3_IGNORE_CASTER_MODIFIERS | SPELL_ATTR3_SUPPRESS_CASTER_PROCS
    s[F_EFFECT_BASE_POINTS] = 0
    s[F_EFFECT_DIE_SIDES] = 0
    s[F_EFFECT_MULTIPLE_VALUE] = f32(1.0)
    s[F_EFFECT_BONUS] = f32(0.0)
    spells.append(s)

    # Tauren passive: the server's script checks every second whether you're moving.
    s = copy(rows, TEMPLATE_RACIAL_PASSIVE, SPELL_PLAINSRUNNING, icon=ICON_DASH)
    set_aura(s, 0, AURA_PERIODIC_DUMMY, 0, amplitude=1000)
    spells.append(s)

    # Its buff: 1% speed per stack, up to 5 stacks, until you stop.
    s = copy(rows, TEMPLATE_RACIAL_ACTIVE, SPELL_PLAINSRUNNING_SPEED, icon=ICON_DASH, visual=0)
    s[F_RECOVERY_TIME] = 0
    s[F_START_RECOVERY_CATEGORY] = s[F_START_RECOVERY_TIME] = 0
    s[F_DURATION_INDEX] = DURATION_INFINITE
    s[F_STACK_AMOUNT] = PLAINSRUNNING_MAX_STACKS
    set_aura(s, 0, AURA_MOD_SPEED_ALWAYS, 1)
    spells.append(s)

    # Tauren active: the server's script picks a herb for your level and grows it. 10 min.
    s = copy(rows, TEMPLATE_RACIAL_ACTIVE, SPELL_CULTIVATION, icon=ICON_CULTIVATION, visual=VISUAL_REJUVENATION)
    s[F_RECOVERY_TIME] = 600000
    s[F_DURATION_INDEX] = 0
    s[F_ATTRIBUTES] |= SPELL_ATTR0_ONLY_OUTDOORS
    s[F_EFFECT] = SPELL_EFFECT_DUMMY
    s[F_EFFECT_TARGET_A] = TARGET_UNIT_CASTER
    spells.append(s)

    # Troll active: 10% of max health every 2 sec for 10 sec, 3 min cooldown. Unlike
    # Cannibalize, moving, acting or taking damage doesn't stop it.
    s = copy(rows, TEMPLATE_RACIAL_ACTIVE, SPELL_RAPID_REGENERATION, icon=ICON_REGENERATION, visual=VISUAL_RENEW)
    s[F_RECOVERY_TIME] = 180000
    s[F_DURATION_INDEX] = DURATION_10_SEC
    set_aura(s, 0, AURA_OBS_MOD_HEALTH, 10, amplitude=2000)
    spells.append(s)

    return spells


def patch_existing(rows):
    """The stock racials the server changes, so their tooltips (and $s values) match."""
    for spell_id in (SPELL_HUMAN_SWORD_SPEC, SPELL_HUMAN_MACE_SPEC, SPELL_DWARF_MACE_SPEC, SPELL_ORC_AXE_SPEC):
        row = find(rows, spell_id)
        set_aura(row, 0, AURA_MOD_WEAPON_CRIT_PERCENT, WEAPON_CRIT_PERCENT)
        set_aura(row, 1, AURA_MOD_SPELL_CRIT_CHANCE, WEAPON_CRIT_PERCENT)

    find(rows, SPELL_HUMAN_SPIRIT)[F_EFFECT_BASE_POINTS] = i32(HUMAN_SPIRIT_PERCENT - 1)

    set_aura(find(rows, SPELL_STONEFORM_BUFF), 1, AURA_MOD_DAMAGE_PERCENT_TAKEN,
             -STONEFORM_PHYSICAL_REDUCTION, misc=SCHOOL_MASK_PHYSICAL)

    set_aura(find(rows, SPELL_QUICKNESS), 2, AURA_MOD_SPEED_ALWAYS, QUICKNESS_SPEED_PERCENT)

    row = find(rows, SPELL_ESCAPE_ARTIST)
    clear_effect(row, 1)
    row[F_EFFECT + 1] = SPELL_EFFECT_TRIGGER_SPELL
    row[F_EFFECT_TARGET_A + 1] = TARGET_UNIT_CASTER
    row[F_EFFECT_TRIGGER_SPELL + 1] = SPELL_ESCAPE_ARTIST_IMMUNITY

    set_aura(find(rows, SPELL_EXPANSIVE_MIND), 1, AURA_MOD_INCREASE_ENERGY_PERCENT,
             EXPANSIVE_MIND_POWER_PERCENT, misc=POWER_MANA)

    # Blood Fury: every version gives attack power and spell power, with the stock amounts
    # (6 + 4 per level attack power, 5 + 2 per level spell power) as the floor.
    row = find(rows, SPELL_BLOOD_FURY_AP)
    set_aura(row, 2, AURA_MOD_DAMAGE_DONE, 5, misc=SCHOOL_MASK_MAGIC, per_level=2.0)
    row = find(rows, SPELL_BLOOD_FURY_BOTH)
    set_aura(row, 2, AURA_MOD_HEALING_DONE, 5, misc=SCHOOL_MASK_ALL, per_level=2.0)
    row = find(rows, SPELL_BLOOD_FURY_SP)
    set_aura(row, 0, AURA_MOD_ATTACK_POWER, 6, per_level=4.0)
    set_aura(row, 2, AURA_MOD_RANGED_ATTACK_POWER, 6, per_level=4.0)

    find(rows, SPELL_HARDINESS)[F_EFFECT_BASE_POINTS] = i32(-HARDINESS_PERCENT - 1)

    set_aura(find(rows, SPELL_CANNIBALIZE_HEAL), 1, AURA_OBS_MOD_POWER, CANNIBALIZE_MANA_PERCENT,
             misc=POWER_MANA, amplitude=2000)

    row = find(rows, SPELL_ENDURANCE)
    set_aura(row, 1, AURA_MOD_HIT_CHANCE, ENDURANCE_HIT_PERCENT)
    set_aura(row, 2, AURA_MOD_SPELL_HIT_CHANCE, ENDURANCE_HIT_PERCENT, misc=SCHOOL_MASK_ALL)


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
    """New racials read "Racial" or "Racial Passive" under their name, like the stock ones."""
    for i in range(16):
        row[F_NAME_SUBTEXT + i] = 0
    if row[F_ID] in (SPELL_BIG_GAME_HUNTER, SPELL_TOUCH_OF_THE_GRAVE, SPELL_PLAINSRUNNING):
        row[F_NAME_SUBTEXT] = add_string(strings, "Racial Passive")
    elif row[F_ID] in (SPELL_ELUNES_LIGHT, SPELL_EUREKA, SPELL_SHATTER_CURSE, SPELL_CULTIVATION,
                       SPELL_RAPID_REGENERATION):
        row[F_NAME_SUBTEXT] = add_string(strings, "Racial")


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
    print(f"{dst}: new spells {', '.join(str(s[F_ID]) for s in added)}; "
          f"{len([t for t in TEXTS if t < 90000])} stock racials updated")


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
