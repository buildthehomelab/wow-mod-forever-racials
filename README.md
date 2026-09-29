# Forever Racials

An [AzerothCore](https://www.azerothcore.org/) (WotLK 3.3.5a) module that brings WoW Forever's
racial rework to a 3.3.5 server, **as buffs**: every race keeps what it has in 3.3.5 and gains
what WoW Forever gives it. Where WoW Forever weakens a racial (Every Man for Himself only
breaking stuns, Berserking at 10%) or drops one (Command, resistances, gun and bow
specializations), the 3.3.5 version stays. The one removal is the Humans' **Diplomacy**, which
goes as in WoW Forever.

Blood Elves and Draenei aren't in WoW Forever and are left alone. WoW Forever's Skyborne race
isn't possible on a 3.3.5 client.

Players need the client patch (`tools/build_patch.py`) for the new spells; without it they can't
see or cast them. The changes to existing racials work without it, but their tooltips stay stock.

## What each race gets

| Race | Changed | New |
|------|---------|-----|
| **Human** | Sword and Mace Specialization: **2% crit** instead of 3 expertise. The Human Spirit: **5% Spirit** (was 3%). Diplomacy: **removed**. | **Perception** (back from Classic): stealth detection for 20 sec, 3 min cooldown. |
| **Dwarf** | Mace Specialization: **2% crit** instead of 5 expertise. Stoneform: also **10% less physical damage** taken. | **Big Game Hunter** (passive): 5% more damage to Beasts. |
| **Night Elf** | Quickness: also **2% run speed**. | **Elune's Light**: 10% crit for 15 sec, 2 min cooldown. |
| **Gnome** | Escape Artist: leaves you **immune to roots and snares for 3 sec**. Expansive Mind: also **5% max mana, rage, energy and runic power**. | **Eureka!**: your next 3 spells or abilities within 20 sec cost 25% less and deal 10% more damage or healing. 2 min cooldown. |
| **Orc** | Axe Specialization: **2% crit** instead of 5 expertise (still Axes and Fist Weapons). Blood Fury: **attack power and spell power**, 10% of yours or the old flat amount, whichever is more. Hardiness: **20%** (was 15%). | **Shatter Curse**: breaks curses, curse immunity and 10% less magic damage taken for 8 sec. 2 min cooldown. |
| **Undead** | Cannibalize: restores **mana** too, 7% every 2 sec like health. | **Touch of the Grave** (passive): weapon attacks (5%) and harmful spells (10%) can drain the target. |
| **Tauren** | Endurance: also **1% hit** with attacks and spells. | **Plainsrunning** (passive): 1% speed for each second you keep moving, up to 5%. **Cultivation**: grows a herb anyone can gather. 10 min cooldown. |
| **Troll** | — | **Rapid Regeneration**: 50% of max health over 10 sec, 3 min cooldown. |

Everything else is unchanged: Every Man for Himself, Find Treasure, Gun Specialization,
Frost Resistance, Shadowmeld, Wisp Spirit, Nature Resistance, Elusiveness, Arcane Resistance,
Engineering Specialization, Command, Will of the Forsaken, Underwater Breathing, Shadow
Resistance, War Stomp, Cultivation's +15 Herbalism, Berserking, Regeneration, Beast Slaying, Bow
and Throwing Specialization, Da Voodoo Shuffle.

The new actives appear in the General tab of the spellbook, like the other racials. Players learn
them at their next login, at any level.

## Details

**Weapon specializations.** Crit with melee and ranged attacks made with that weapon, plus spell
crit while one is equipped (in either hand). So a Human priest with a mace, or an Orc shaman with
an axe, gets 2% spell crit. WoW Forever gives Dwarves and Orcs 1%; this module gives all three 2%
so their melee doesn't lose out on the old 5 expertise. A Human dual-wielding a sword and a mace
gets both specializations: 2% melee crit per hand, but 4% spell crit (it matters only for death
knights).

**Blood Fury.** Warriors, rogues, hunters and death knights used to get attack power only, mages
and warlocks spell power only, shamans both. Now everyone gets attack power and spell power
(shamans also healing power). Each is 10% of your own, or the old flat amount (6 + 4 per level
attack power, 5 + 2 per level spell power) if that's more, so low-level Orcs lose nothing.

**Touch of the Grave.** Damaging weapon attacks (melee, ranged, wands, weapon abilities) have a
5% chance and harmful spells a 10% chance. Damage over time never procs it. The drain deals
Shadow damage equal to 25% of your attack power or spell power, whichever is higher, never more
than 5% of your own max health, and heals you for what it really dealt. It always hits, can't
crit and doesn't trigger other procs. At most once every 3 seconds (mostly limits area spells).

**Eureka!** Counts spells and abilities that cost something, hurt or heal; mounts, hearthstones
and food don't use a charge. The 10% applies to anything you do while it's up; the charges go
as your spells finish.

**Plainsrunning.** Checked every second: moving adds a stack (1%), standing still removes them
all. Taxi flights don't count.

**Cultivation.** Grows a herb 2 yards in front of you, picked at random from the best herbs for
your level: Peacebloom and Silverleaf at level 1, up to Lichbloom and Icethorn at 77. Anyone can
gather it, with or without Herbalism, and it has the herb's normal loot. It withers after 2
minutes, or when you leave the map. Outdoors only. With
[mod-individual-progression](https://github.com/ZhengPeiRu21/mod-individual-progression), Outland
herbs wait until the player has reached Outland and Northrend herbs until Northrend.

**Diplomacy** can't simply be unlearned, because the core teaches racial passives again from the
Human skill line at every login. It stays learned but gives 0% reputation, and the client patch
hides it from the spellbook. Without the patch it still shows, doing nothing.

**Escape Artist's immunity** is a 3 sec buff named Escape Artist.

**Stoneform's** physical damage cut is on the same 8 sec buff as its armor.

## Numbers WoW Forever hasn't published

WoW Forever's announcements give the effects but not every number. These are the module's own
choices: the cooldowns of the new actives (2 min, or 3 min for Perception and Rapid
Regeneration, 10 min for Cultivation), Escape Artist's 3 sec immunity, Eureka!'s 25% cost cut and
20 sec window, Shatter Curse's 10% magic reduction, Touch of the Grave's damage (25% of attack
power or spell power, capped at 5% of max health) and its 3 sec cooldown, and Plainsrunning's
1% per second up to 5%.

WoW Forever's other Gnome change, more reliable engineering devices, isn't included: the failure
chances are hard-coded in the core's item scripts, one per device.

## Install

Clone it into your AzerothCore `modules` folder **as `mod-forever-racials`**, without the repo's
`wow-` prefix. AzerothCore finds the module's entry point from the folder name.

```bash
cd <azerothcore>/modules
git clone https://github.com/buildthehomelab/wow-mod-forever-racials.git mod-forever-racials
```

Rebuild the worldserver, then copy `conf/mod_forever_racials.conf.dist` to your config folder as
`mod_forever_racials.conf`. The new spells, their script bindings and Cultivation's herbs are
added to the world database on the next start.

## Settings

| Setting | Default | What it does |
|---------|---------|--------------|
| `ForeverRacials.<Race>.Enable` | `1` | One per race (`Human`, `Dwarf`, `NightElf`, `Gnome`, `Orc`, `Undead`, `Tauren`, `Troll`). With `0`, that race keeps its stock racials (Humans get Diplomacy back) and loses the new spells at its next login. Startup only. |
| `ForeverRacials.WeaponSpecialization.CritPercent` | `2` | Crit the weapon specializations give. Startup only. |
| `ForeverRacials.BloodFury.Percent` | `10` | Blood Fury's share of your attack power and spell power. `0` keeps the flat amounts. |
| `ForeverRacials.TouchOfTheGrave.WeaponChance` / `SpellChance` | `5` / `10` | Proc chance in percent. |
| `ForeverRacials.TouchOfTheGrave.PowerPercent` | `25` | Drain as a share of attack power or spell power. |
| `ForeverRacials.TouchOfTheGrave.MaxHealthPercent` | `5` | Cap, as a share of your own max health. |
| `ForeverRacials.TouchOfTheGrave.Cooldown` | `3000` | Minimum milliseconds between drains. `0` for none. |
| `ForeverRacials.Plainsrunning.SecondsPerStack` | `1` | Seconds of moving per 1% speed. |
| `ForeverRacials.Cultivation.DespawnSeconds` | `120` | How long a grown herb lasts. |
| `ForeverRacials.Cultivation.RespectProgression` | `1` | Follow mod-individual-progression's Outland and Northrend unlocks. |

The race switches and the crit setting are read at startup only, because the stock racials are
changed when the server starts. The rest can be reloaded.

If you change a setting the tooltips mention and use the client patch, change the matching
value at the top of `tools/build_patch.py` and rebuild the patch.

## Turning it off

- **One race:** set `ForeverRacials.<Race>.Enable = 0` and restart. That race's stock racials
  come back and its characters lose the new spells as they log in.
- **Remove the module for good:** stop the worldserver, delete the module, rebuild, and run both
  uninstall files:

  - `data/sql/uninstall/mod_forever_racials_uninstall_world.sql` on the world database removes
    the new spells, script bindings and Cultivation's herbs.
  - `data/sql/uninstall/mod_forever_racials_uninstall_characters.sql` on the characters database
    takes the new spells and Perception off every character, their action bars, cooldowns and
    auras.

  If you shipped the client patch, take the module's changes out of it too, or the tooltips and
  spellbook entries stay.

AzerothCore never runs the `uninstall` folder by itself; it only runs the module's `db-world`
folder.

## Client patch

`tools/build_patch.py` changes the client's Spell.dbc: it adds the twelve new spells
(90100-90111) and updates the changed racials so their tooltips match. Only the newest client
patch's Spell.dbc is used, so start from the patch that already ships one (patch-P on this realm)
and the script keeps its other changes:

```bash
tools/build_patch.py --from-mpq patch-P.MPQ --out patch-P.MPQ.new
```

Or write the DBC alone, from a Spell.dbc you have:

```bash
tools/build_patch.py --dbc Spell.dbc --out-dir DBFilesClient
```

`--sql` prints the server's `spell_dbc` rows for the new spells (the module's SQL already has
them). Packing needs StormLib (`brew install stormlib`); point `STORMLIB` at `libstorm` if it
isn't in `/usr/local/lib`.

## How it works

- **New spells** (90100-90111) are rows in `spell_dbc` for the server and in patch-P's Spell.dbc
  for the client, built from stock spells for their flags, icons and visuals (Beast Slaying,
  Perception, Stoneform, and an NPC's instant Shadow health leech for the drain).
- **Stock racials** are changed in memory when the server starts, like the core's own spell
  corrections, so the database's copy of the game data is never touched.
- **Scripts**: Blood Fury's amounts, Touch of the Grave's chance and drain, Eureka!'s charges,
  Plainsrunning's stacks and Cultivation's herb.
- **Cultivation's herbs** are copies of 40 herb nodes (`gameobject_template` 9500700-9500739)
  without the Herbalism lock, with the original herbs' loot.

## License

MIT
