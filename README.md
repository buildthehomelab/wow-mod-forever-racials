# Forever Racials

An [AzerothCore](https://www.azerothcore.org/) (WotLK 3.3.5a) module that splits racials in two:
**races for utility, classes for power.**

In stock 3.3.5 a race's passives decide which class it's "best" at: weapon specializations, Blood
Fury, Berserking, Heroic Presence. This module moves all of that to the classes. Every class gets
a mastery (+hit and +crit with its weapons) and a cooldown of its own, whatever its race. Every
race keeps one active and one passive that add no damage, healing, hit, crit, haste or resources.
Racial resistances are gone, and profession racials make the profession faster instead of adding
skill.

That also makes new races (goblin, worgen, pandaren) easy to add: they only need a utility kit.

Players need the client patch (`tools/build_patch.py`) for the new spells; without it they can't
see or cast them.

## Patch Notes

**Racials have been reworked: races now give utility, and the power moved to your class.**

- **Every class** now has a **mastery**: +2% hit and +2% crit with the weapons your class uses.
  Spellcasters get +4% spell hit and +2% spell crit instead (hybrids get both). With the free hit,
  you can trade some hit gear for other stats.
- **Every class** now has its own **2-minute cooldown**: Battle Fury (warrior), Crusader's Zeal
  (paladin), Pack Fury (hunter), Cutthroat Rush (rogue), Inner Fervor (priest), Grave Fury (death
  knight), Ancestral Fury (shaman), Arcane Fervor (mage), Fel Frenzy (warlock) and Wild Instinct
  (druid).
- **Every race** now has **one active and one passive** racial. Blood Fury, Berserking, weapon
  specializations, Heroic Presence, Expansive Mind, The Human Spirit, Command, Beast Slaying,
  Cannibalize, Elune's Light, Eureka!, Big Game Hunter, Plainsrunning and Cultivation are gone.
- **All racial resistances are gone.**
- **Profession racials** now make the profession **25% faster** instead of adding skill: Gnome
  Engineering, Draenei Jewelcrafting, Blood Elf Enchanting, Tauren Herbalism.
- **Touch of the Grave** (Undead) now heals you for part of the damage you deal and no longer
  hurts the target.
- **Perception** (Human) is a passive again, as in 3.3.5.
- Update your client patch (patch-P) to see the new spells and tooltips.

## What each class gets

| Class | Mastery | Cooldown (2 min, 15 sec) |
|-------|---------|--------------------------|
| Warrior | +2% hit and crit with axes, maces, swords, polearms and fist weapons | **Battle Fury**: +15% attack power, 10 rage |
| Paladin | +2% hit and crit with axes, maces, swords and polearms; +4% spell hit, +2% spell crit | **Crusader's Zeal**: +15% attack power, spell power and healing |
| Hunter | +2% hit and crit with bows, guns and crossbows | **Pack Fury**: +10% ranged attack speed for you and +10% attack speed for your pet |
| Rogue | +2% hit and crit with one-handed axes, maces and swords, fist weapons and daggers | **Cutthroat Rush**: +20% energy regeneration |
| Priest | +4% spell hit, +2% spell crit; +2% hit and crit with wands | **Inner Fervor**: +10% casting speed |
| Death Knight | +2% hit and crit with axes, maces, swords and polearms; +4% spell hit, +2% spell crit | **Grave Fury**: +15% attack power, 15 runic power |
| Shaman | +2% hit and crit with axes, maces, fist weapons and daggers; +4% spell hit, +2% spell crit | **Ancestral Fury**: +10% attack and casting speed |
| Mage | +4% spell hit, +2% spell crit; +2% hit and crit with wands | **Arcane Fervor**: +15% spell power |
| Warlock | +4% spell hit, +2% spell crit; +2% hit and crit with wands | **Fel Frenzy**: +15% spell power, and your demon deals 15% more damage |
| Druid | +4% spell hit, +2% spell crit; +2% hit and crit in Cat and Bear Form | **Wild Instinct**: depends on your form. Cat: +20% energy regeneration. Bear: +15% attack power and 10 rage. Any other form: +10% casting speed |

Characters learn them at their next login, at any level. They show in the General tab of the
spellbook.

## What each race gets

| Race | Active | Passive |
|------|--------|---------|
| Human | Every Man for Himself | Perception: stealth detection |
| Dwarf | Stoneform: also **10% less physical damage** taken | Find Treasure |
| Night Elf | Shadowmeld | Quickness: harder to hit, **2% run speed**; Wisp Spirit, Elusiveness |
| Gnome | Escape Artist: then **immune to roots and snares for 3 sec** | Engineering Specialization: **Engineering 25% faster** |
| Orc | **Shatter Curse**: breaks curses, curse immunity and 10% less magic damage taken for 8 sec, 2 min | Hardiness: **20%** shorter stuns |
| Undead | Will of the Forsaken | **Touch of the Grave**: weapon attacks (5%) and harmful spells (10%) can heal you for 25% of the damage they dealt; Underwater Breathing |
| Tauren | War Stomp | Endurance: 5% health; **Herbalism 25% faster** |
| Troll | **Rapid Regeneration**: 50% of max health over 20 sec, 3 min | Regeneration; Da Voodoo Shuffle |
| Blood Elf | Arcane Torrent | Arcane Affinity: **Enchanting 25% faster** |
| Draenei | Gift of the Naaru | Gemcutting: **Jewelcrafting 25% faster** |

The names after a semicolon are stock racials folded into that passive. They work exactly as
before, but the client patch hides them from the spellbook and the passive's tooltip lists them.

**Removed:** Diplomacy, The Human Spirit, Sword and Mace Specialization (Human); Gun and Mace
Specialization (Dwarf); Expansive Mind (Gnome); Blood Fury, Axe Specialization, Command (Orc);
Cannibalize (Undead); Berserking, Beast Slaying, Bow and Throwing Specialization (Troll); Heroic
Presence (Draenei); every racial resistance; and the first version's Big Game Hunter, Elune's
Light, Eureka!, Plainsrunning, Cultivation (the active) and the active Perception.

## Balance

**Mastery.** Against a boss three levels above you the hit cap is 8% for melee and ranged
specials and 17% for spells. 2% hit is a quarter of the melee cap, so casters get 4%, about the
same share of theirs. The free hit is the point: it frees itemization for other stats, and the
weapon lists make weapon choice matter (a warrior with a dagger or a staff gets nothing).

**Cooldowns.** Tuned against stock Berserking (20% haste for 10 sec every 3 min, about 1.1% more
damage on average): 15% attack power or spell power for 15 sec every 2 min is about 1%, and 10%
haste about 1.25%. Energy and rage turn into damage almost one for one, so they're smaller.

**Races.** No racial adds throughput, so the choice of race is about looks, utility and
defensives. Every race keeps a defensive, a crowd control break, a stun or a heal.

## Details

**Physical masteries.** The crit counts for the hand doing the attack: a warrior with a listed
main-hand weapon and an unlisted off-hand weapon gets the crit on the main hand only. Hit is one
number per character in 3.3.5, so it's on while any weapon slot (main hand, off hand or ranged)
holds a listed weapon. The core adds and removes the passive as you change gear. Each class's
list is a setting.

**Feral Mastery** works in Cat, Bear and Dire Bear Form, whatever the druid holds; the core puts
it up and takes it down as the druid shifts.

**Spell power cooldowns** (Crusader's Zeal, Arcane Fervor, Fel Frenzy) give a share of your own
spell power and healing power when you use them. **Wild Instinct** counts the form you're in when
you use it; shifting afterwards doesn't change it.

**Profession speed** is a cut in cast time, 25% for every spell of that profession (crafting,
Herb Gathering, Disenchant, Prospecting). It stacks with mod-gathering-tools' tool bonus.

**Touch of the Grave.** Damaging weapon attacks (melee, ranged, wands, weapon abilities) have a 5%
chance and harmful spells a 10% chance. Damage over time never procs it, and nothing rolls while
you're at full health. The heal is 25% of the damage the hit dealt, never more than 5% of your max
health. It can't crit and doesn't trigger other procs. At most once every 3 seconds (mostly limits
area spells).

**Rapid Regeneration.** 5% of max health every 2 sec for 20 sec. Unlike Cannibalize, moving,
fighting or taking damage doesn't stop it.

**Removed racials** are taken off characters at login. The core normally teaches racials again at
every login, from the race's skill line; the module takes the removed ones off that list in
memory, so they stay gone. Switch the race half off and the core teaches them all back.

## Install

Clone it into your AzerothCore `modules` folder **as `mod-forever-racials`**, without the repo's
`wow-` prefix. AzerothCore finds the module's entry point from the folder name.

```bash
cd <azerothcore>/modules
git clone https://github.com/buildthehomelab/wow-mod-forever-racials.git mod-forever-racials
```

Rebuild the worldserver, then copy `conf/mod_forever_racials.conf.dist` to your config folder as
`mod_forever_racials.conf`. The new spells and their script bindings are added to the world
database on the next start, and the characters update takes the first version's spells off every
character.

## Settings

| Setting | Default | What it does |
|---------|---------|--------------|
| `ForeverRacials.Races.Enable` | `1` | The race half. With `0`, every race gets its stock racials back and loses Shatter Curse, Touch of the Grave and Rapid Regeneration at its next login. Startup only. |
| `ForeverRacials.Classes.Enable` | `1` | The class half. With `0`, characters lose their mastery and class cooldown at their next login. Startup only. |
| `ForeverRacials.Profession.SpeedPercent` | `25` | How much faster the profession racials make their profession. Startup only. |
| `ForeverRacials.Mastery.HitPercent` / `CritPercent` | `2` / `2` | Physical mastery hit and crit. Startup only. |
| `ForeverRacials.Mastery.SpellHitPercent` / `SpellCritPercent` | `4` / `2` | Spell Mastery hit and crit. Startup only. |
| `ForeverRacials.Mastery.<Class>.Weapons` | see the conf | The weapon types each class's mastery counts (`Warrior`, `Paladin`, `Hunter`, `Rogue`, `DeathKnight`, `Shaman`, and `Caster` for wands). Startup only. |
| `ForeverRacials.TouchOfTheGrave.WeaponChance` / `SpellChance` | `5` / `10` | Proc chance in percent. |
| `ForeverRacials.TouchOfTheGrave.HealPercent` | `25` | The heal, as a share of the hit's damage. |
| `ForeverRacials.TouchOfTheGrave.MaxHealthPercent` | `5` | Cap, as a share of your own max health. |
| `ForeverRacials.TouchOfTheGrave.Cooldown` | `3000` | Minimum milliseconds between heals. `0` for none. |

The startup-only settings change spells when the server starts. Touch of the Grave's settings can
be reloaded.

If you change a setting the tooltips mention (or a weapon list) and use the client patch, change
the matching value at the top of `tools/build_patch.py` and rebuild the patch.

## Turning it off

- **One half:** set `ForeverRacials.Races.Enable = 0` or `ForeverRacials.Classes.Enable = 0` and
  restart. Characters change over as they log in.
- **Remove the module for good:** stop the worldserver, delete the module, rebuild, and run both
  uninstall files:

  - `data/sql/uninstall/mod_forever_racials_uninstall_world.sql` on the world database removes
    the new spells and script bindings.
  - `data/sql/uninstall/mod_forever_racials_uninstall_characters.sql` on the characters database
    takes the module's spells off every character, their action bars, cooldowns and auras.

  The stock racials come back by themselves at the next login. If you shipped the client patch,
  take the module's changes out of it too, or the tooltips and spellbook entries stay.

AzerothCore never runs the `uninstall` folder by itself; it only runs the module's `db-world` and
`db-characters` folders.

## Client patch

`tools/build_patch.py` changes the client's Spell.dbc: it adds the new spells (90102-90111,
90140-90159), updates the kept racials so their tooltips match, and hides the folded racials from
the spellbook. Only the newest client patch's Spell.dbc is used, so start from the patch that
already ships one (patch-P on this realm) and the script keeps its other changes:

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

## Character creation screen

The character creation screen doesn't read Spell.dbc: its racial list comes from the
`ABILITY_INFO_<RACE><n>` strings in the client's `Interface\GlueXML\GlueStrings.lua`. So patch-P
doesn't change it. `tools/build_glue_patch.py` rewrites those strings to the one active + one
passive kits (leaving every other string alone) and packs them into their own patch:

```bash
tools/build_glue_patch.py --from-mpq patch-7.MPQ --out patch-R.MPQ   # from a login patch you ship
tools/build_glue_patch.py --glue GlueStrings.lua --out patch-R.MPQ   # from the client's own file
```

The client replaces the whole file, so start from the GlueStrings.lua your players already have
(a login tweak's `patch-7.MPQ`, or the stock one from `locale-enUS.MPQ`), and give the patch a
letter that sorts after that patch's (letters sort after digits).

**The 3.3.5 client may refuse changed interface files** unless it runs a Wow.exe that allows
interface edits. Try the patch on one client first, and ship it as its own optional patch, not
inside patch-P, so players on the stock Wow.exe aren't affected.

## How it works

- **New spells** (90102-90111, 90140-90159) are rows in `spell_dbc` for the server and in
  patch-P's Spell.dbc for the client, built from stock spells for their flags, icons and visuals
  (Beast Slaying for passives, Blood Fury for the class cooldowns).
- **Kept stock racials** are changed in memory when the server starts, like the core's own spell
  corrections, so the database's copy of the game data is never touched.
- **Removed stock racials**: their SkillLineAbility rows stop being "learned with the skill" in
  memory, and characters lose them at login.
- **Profession speed**: the profession racial becomes a cast time modifier that, on its own,
  reaches no spell (empty class mask, unused spell family); a GlobalScript lets it reach the
  spells of its profession only.
- **Scripts**: Touch of the Grave's chance and heal, the spell power cooldowns' share of your
  spell power, and Wild Instinct's form check.

## License

MIT
