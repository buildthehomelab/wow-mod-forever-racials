/*
 * mod-forever-racials
 *
 * Racials for utility, classes for power. Every race keeps one active and one passive, none of
 * which add damage, healing, hit, crit, haste or resources. What used to make a race the "best"
 * pick for a class (weapon specializations, Blood Fury, Berserking, Heroic Presence...) moves to
 * the classes instead, so every member of a class gets it whatever their race:
 *
 *   Class mastery   +2% hit and +2% crit with the weapons the class uses (casters: +4% spell hit
 *                   and +2% spell crit, plus the physical bonus with wands). Hybrids get both.
 *                   Druids get the physical bonus in Cat and Bear Form, whatever they hold.
 *   Class cooldown  a 2 min, 15 sec burst in the class's own style, tuned to about the same
 *                   average gain as stock Berserking.
 *
 *   Human     Every Man for Himself | Perception (stock 3.3.5 passive)
 *   Dwarf     Stoneform (also 10% less physical damage) | Find Treasure
 *   Night Elf Shadowmeld | Quickness (also 2% run speed); Wisp Spirit, Elusiveness
 *   Gnome     Escape Artist (then 3 sec immune to roots and snares) | Engineering 25% faster
 *   Orc       Shatter Curse | Hardiness (20% shorter stuns)
 *   Undead    Will of the Forsaken | Touch of the Grave (heals you for part of a hit's damage);
 *             Underwater Breathing
 *   Tauren    War Stomp | Endurance (5% health); Herbalism 25% faster
 *   Troll     Rapid Regeneration | Regeneration; Da Voodoo Shuffle
 *   Blood Elf Arcane Torrent | Enchanting 25% faster
 *   Draenei   Gift of the Naaru | Jewelcrafting 25% faster
 *
 * Every racial resistance is gone, and profession racials make the profession faster instead of
 * adding skill. The stock racials a race loses are taken off its characters at login, and the
 * core is stopped from teaching them again (their SkillLineAbility rows are changed in memory).
 *
 * The new spells come from spell_dbc on the server and patch-P on the client
 * (tools/build_patch.py). The kept stock racials are changed in memory when the server starts;
 * patch-P updates their tooltips. Races and classes can each be switched off in the config.
 *
 * Released under the MIT License.
 */

#include "Config.h"
#include "DBCStores.h"
#include "ItemTemplate.h"
#include "Log.h"
#include "Pet.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "Spell.h"
#include "SpellAuraEffects.h"
#include "SpellAuras.h"
#include "SpellInfo.h"
#include "SpellMgr.h"
#include "SpellScript.h"
#include "SpellScriptLoader.h"
#include "StringConvert.h"
#include "Tokenize.h"

#include <algorithm>
#include <string>
#include <unordered_map>
#include <unordered_set>

namespace
{
    // --- Spells -----------------------------------------------------------------------------------
    // New spells: must match the SQL and tools/build_patch.py.

    // Racials.
    constexpr uint32 SPELL_ESCAPE_ARTIST_IMMUNITY = 90102;
    constexpr uint32 SPELL_SHATTER_CURSE = 90105;
    constexpr uint32 SPELL_TOUCH_OF_THE_GRAVE = 90106;
    constexpr uint32 SPELL_TOUCH_OF_THE_GRAVE_HEAL = 90107;
    constexpr uint32 SPELL_RAPID_REGENERATION = 90111;

    // Class masteries (passive).
    constexpr uint32 SPELL_MASTERY_WARRIOR = 90140;
    constexpr uint32 SPELL_MASTERY_PALADIN = 90141;
    constexpr uint32 SPELL_MASTERY_HUNTER = 90142;
    constexpr uint32 SPELL_MASTERY_ROGUE = 90143;
    constexpr uint32 SPELL_MASTERY_DEATH_KNIGHT = 90144;
    constexpr uint32 SPELL_MASTERY_SHAMAN = 90145;
    constexpr uint32 SPELL_MASTERY_WAND = 90146;    // priests, mages, warlocks
    constexpr uint32 SPELL_MASTERY_SPELL = 90147;   // every class that casts
    constexpr uint32 SPELL_MASTERY_FERAL = 90148;   // druids in Cat and Bear Form

    // Class cooldowns.
    constexpr uint32 SPELL_BATTLE_FURY = 90150;       // warrior
    constexpr uint32 SPELL_CRUSADERS_ZEAL = 90151;    // paladin
    constexpr uint32 SPELL_PACK_FURY = 90152;         // hunter
    constexpr uint32 SPELL_CUTTHROAT_RUSH = 90153;    // rogue
    constexpr uint32 SPELL_INNER_FERVOR = 90154;      // priest
    constexpr uint32 SPELL_GRAVE_FURY = 90155;        // death knight
    constexpr uint32 SPELL_ANCESTRAL_FURY = 90156;    // shaman
    constexpr uint32 SPELL_ARCANE_FERVOR = 90157;     // mage
    constexpr uint32 SPELL_FEL_FRENZY = 90158;        // warlock
    constexpr uint32 SPELL_WILD_INSTINCT = 90159;     // druid

    // The previous version's spells, taken off every character at login. 20600 is the old active
    // Perception, which nothing else in 3.3.5 teaches (Humans have the passive one, 58985).
    constexpr uint32 RETIRED_SPELLS[] = {
        20600,  // Perception (active)
        90100,  // Big Game Hunter
        90101,  // Elune's Light
        90103,  // Eureka!
        90104,  // Expansive Mind (hidden power half)
        90108,  // Plainsrunning
        90109,  // Plainsrunning (speed)
        90110,  // Cultivation (active)
    };

    // Stock racials that go: damage, healing, hit, crit, haste and resources move to the classes,
    // and every resistance is dropped. Kept: each race's active and passive (see the top).
    constexpr uint32 REMOVED_RACIALS[] = {
        // Human
        20599, 20597, 20864, 20598,         // Diplomacy, Sword and Mace Specialization, The Human Spirit
        // Dwarf
        20596, 20595, 59224,                // Frost Resistance, Gun and Mace Specialization
        // Night Elf
        20583,                              // Nature Resistance
        // Gnome
        20591, 20592,                       // Expansive Mind, Arcane Resistance
        // Orc
        20572, 33697, 33702,                // Blood Fury (attack power, both, spell power)
        20574,                              // Axe Specialization
        20575, 20576, 21563, 54562, 65222,  // Command
        // Undead
        20577, 20579,                       // Cannibalize, Shadow Resistance
        // Tauren
        20551,                              // Nature Resistance
        // Troll
        26297, 20557, 20558, 26290,         // Berserking, Beast Slaying, Throwing and Bow Specialization
        // Blood Elf
        822,                                // Magic Resistance
        // Draenei
        6562, 28878,                        // Heroic Presence
        59221, 59535, 59536, 59538, 59539, 59540, 59541, // Shadow Resistance (one per class)
    };

    // Kept stock racials the module changes.
    constexpr uint32 SPELL_STONEFORM_BUFF = 65116;
    constexpr uint32 SPELL_QUICKNESS = 20582;
    constexpr uint32 SPELL_ESCAPE_ARTIST = 20589;
    constexpr uint32 SPELL_HARDINESS = 20573;

    // The fixed values the client patch's tooltips show. Changing them means rebuilding patch-P
    // (tools/build_patch.py has the same numbers).
    constexpr int32 STONEFORM_PHYSICAL_REDUCTION = 10;
    constexpr int32 QUICKNESS_SPEED_PERCENT = 2;
    constexpr int32 HARDINESS_PERCENT = 20;
    constexpr int32 WILD_INSTINCT_RAGE = 10;

    struct RaceSpell
    {
        uint8 race;
        uint32 spellId;
    };

    // The racials that are new spells (the rest are stock and come with the race).
    constexpr RaceSpell RACE_SPELLS[] = {
        { RACE_ORC, SPELL_SHATTER_CURSE },
        { RACE_UNDEAD_PLAYER, SPELL_TOUCH_OF_THE_GRAVE },
        { RACE_TROLL, SPELL_RAPID_REGENERATION },
    };

    struct ClassSpell
    {
        uint8 classId;
        uint32 spellId;
    };

    constexpr ClassSpell CLASS_SPELLS[] = {
        { CLASS_WARRIOR, SPELL_MASTERY_WARRIOR },
        { CLASS_WARRIOR, SPELL_BATTLE_FURY },
        { CLASS_PALADIN, SPELL_MASTERY_PALADIN },
        { CLASS_PALADIN, SPELL_MASTERY_SPELL },
        { CLASS_PALADIN, SPELL_CRUSADERS_ZEAL },
        { CLASS_HUNTER, SPELL_MASTERY_HUNTER },
        { CLASS_HUNTER, SPELL_PACK_FURY },
        { CLASS_ROGUE, SPELL_MASTERY_ROGUE },
        { CLASS_ROGUE, SPELL_CUTTHROAT_RUSH },
        { CLASS_PRIEST, SPELL_MASTERY_WAND },
        { CLASS_PRIEST, SPELL_MASTERY_SPELL },
        { CLASS_PRIEST, SPELL_INNER_FERVOR },
        { CLASS_DEATH_KNIGHT, SPELL_MASTERY_DEATH_KNIGHT },
        { CLASS_DEATH_KNIGHT, SPELL_MASTERY_SPELL },
        { CLASS_DEATH_KNIGHT, SPELL_GRAVE_FURY },
        { CLASS_SHAMAN, SPELL_MASTERY_SHAMAN },
        { CLASS_SHAMAN, SPELL_MASTERY_SPELL },
        { CLASS_SHAMAN, SPELL_ANCESTRAL_FURY },
        { CLASS_MAGE, SPELL_MASTERY_WAND },
        { CLASS_MAGE, SPELL_MASTERY_SPELL },
        { CLASS_MAGE, SPELL_ARCANE_FERVOR },
        { CLASS_WARLOCK, SPELL_MASTERY_WAND },
        { CLASS_WARLOCK, SPELL_MASTERY_SPELL },
        { CLASS_WARLOCK, SPELL_FEL_FRENZY },
        { CLASS_DRUID, SPELL_MASTERY_SPELL },
        { CLASS_DRUID, SPELL_MASTERY_FERAL },
        { CLASS_DRUID, SPELL_WILD_INSTINCT },
    };

    // The physical masteries and the config key that lists their weapons.
    struct WeaponMastery
    {
        uint32 spellId;
        char const* configName;
        char const* defaultWeapons;
    };

    // Item subclasses: 0 one-handed axe, 1 two-handed axe, 2 bow, 3 gun, 4 one-handed mace,
    // 5 two-handed mace, 6 polearm, 7 one-handed sword, 8 two-handed sword, 10 staff,
    // 13 fist weapon, 15 dagger, 16 thrown, 18 crossbow, 19 wand. Must match build_patch.py.
    constexpr WeaponMastery WEAPON_MASTERIES[] = {
        { SPELL_MASTERY_WARRIOR,      "Warrior",     "0,1,4,5,6,7,8,13" },
        { SPELL_MASTERY_PALADIN,      "Paladin",     "0,1,4,5,6,7,8" },
        { SPELL_MASTERY_HUNTER,       "Hunter",      "2,3,18" },
        { SPELL_MASTERY_ROGUE,        "Rogue",       "0,4,7,13,15" },
        { SPELL_MASTERY_DEATH_KNIGHT, "DeathKnight", "0,1,4,5,6,7,8" },
        { SPELL_MASTERY_SHAMAN,       "Shaman",      "0,1,4,5,13,15" },
        { SPELL_MASTERY_WAND,         "Caster",      "19" },
    };

    // The profession racials: the stock passive now makes the profession's casts faster.
    struct ProfessionRacial
    {
        uint32 spellId;
        uint32 skill;
    };

    constexpr ProfessionRacial PROFESSION_RACIALS[] = {
        { 20593, SKILL_ENGINEERING },   // Gnome: Engineering Specialization
        { 28875, SKILL_JEWELCRAFTING }, // Draenei: Gemcutting
        { 28877, SKILL_ENCHANTING },    // Blood Elf: Arcane Affinity
        { 20552, SKILL_HERBALISM },     // Tauren: Cultivation
    };

    // An unused spell family, so the profession racials' cast time modifier matches no spell by
    // itself: with family 0 a modifier with an empty class mask would reach every spell. The
    // GlobalScript below lets it reach its profession only.
    constexpr uint32 SPELLFAMILY_FOREVER_RACIALS = 16;

    struct Config
    {
        bool races = true;
        bool classes = true;

        int32 professionSpeed = 25;

        int32 masteryHit = 2;
        int32 masteryCrit = 2;
        int32 masterySpellHit = 4;
        int32 masterySpellCrit = 2;
        std::unordered_map<uint32, uint32> weaponMasks; // mastery spell -> item subclass mask

        float touchWeaponChance = 5.0f;
        float touchSpellChance = 10.0f;
        float touchHealPercent = 25.0f;
        float touchMaxHealthPercent = 5.0f;
        uint32 touchCooldown = 3000;
    };

    Config config;

    // Profession racial -> the spells of its profession (from SkillLineAbility).
    std::unordered_map<uint32, std::unordered_set<uint32>> professionSpells;

    uint32 ParseWeaponMask(std::string const& list, char const* configName)
    {
        uint32 mask = 0;
        for (std::string_view token : Acore::Tokenize(list, ',', false))
        {
            std::string trimmed(token);
            trimmed.erase(0, trimmed.find_first_not_of(" \t"));
            trimmed.erase(trimmed.find_last_not_of(" \t") + 1);

            Optional<uint32> subclass = Acore::StringTo<uint32>(trimmed);
            if (!subclass || *subclass >= MAX_ITEM_SUBCLASS_WEAPON)
            {
                LOG_ERROR("module", "mod-forever-racials: ForeverRacials.Mastery.{}.Weapons has '{}', which isn't a weapon type (0-{}); skipped.",
                    configName, trimmed, MAX_ITEM_SUBCLASS_WEAPON - 1);
                continue;
            }
            mask |= 1u << *subclass;
        }
        return mask;
    }

    // --- In-memory changes to the stock racials and the new spells -------------------------------

    SpellInfo* MutableSpell(uint32 spellId)
    {
        SpellInfo* spellInfo = const_cast<SpellInfo*>(sSpellMgr->GetSpellInfo(spellId));
        if (!spellInfo)
            LOG_ERROR("module", "mod-forever-racials: spell {} is missing; its change is skipped.", spellId);
        return spellInfo;
    }

    // Turn an effect into a beneficial aura on the caster. amount is the real value; the game
    // data stores it as base points + 1 (one-sided die).
    void SetAura(SpellInfo* spellInfo, SpellEffIndex effIndex, AuraType aura, int32 amount, int32 misc = 0)
    {
        SpellEffectInfo& effect = spellInfo->Effects[effIndex];
        effect.Effect = SPELL_EFFECT_APPLY_AURA;
        effect.ApplyAuraName = aura;
        effect.BasePoints = amount - 1;
        effect.DieSides = 1;
        effect.RealPointsPerLevel = 0.0f;
        effect.MiscValue = misc;
        effect.MiscValueB = 0;
        effect.Amplitude = 0;
        effect.TriggerSpell = 0;
        effect.TargetA = SpellImplicitTargetInfo(TARGET_UNIT_CASTER);
        effect.TargetB = SpellImplicitTargetInfo();

        // The core worked out at load which effects are harmful; these ones never are.
        spellInfo->AttributesCu &= ~(SPELL_ATTR0_CU_NEGATIVE_EFF0 << effIndex);
        spellInfo->AttributesCu |= (SPELL_ATTR0_CU_POSITIVE_EFF0 << effIndex);
    }

    void ApplyKeptRacialChanges()
    {
        // Stoneform's buff (cast with it through spell_linked_spell) keeps its 10% armor.
        if (SpellInfo* stoneform = MutableSpell(SPELL_STONEFORM_BUFF))
            SetAura(stoneform, EFFECT_1, SPELL_AURA_MOD_DAMAGE_PERCENT_TAKEN, -STONEFORM_PHYSICAL_REDUCTION, SPELL_SCHOOL_MASK_NORMAL);

        // Speed that stacks with everything else, like the other always-on speed bonuses.
        if (SpellInfo* quickness = MutableSpell(SPELL_QUICKNESS))
            SetAura(quickness, EFFECT_2, SPELL_AURA_MOD_SPEED_ALWAYS, QUICKNESS_SPEED_PERCENT);

        // Effect 0 (the core's script) frees you, then effect 1 casts the immunity.
        if (SpellInfo* escapeArtist = MutableSpell(SPELL_ESCAPE_ARTIST))
        {
            SpellEffectInfo& effect = escapeArtist->Effects[EFFECT_1];
            effect.Effect = SPELL_EFFECT_TRIGGER_SPELL;
            effect.ApplyAuraName = SPELL_AURA_NONE;
            effect.TriggerSpell = SPELL_ESCAPE_ARTIST_IMMUNITY;
            effect.TargetA = SpellImplicitTargetInfo(TARGET_UNIT_CASTER);
            effect.TargetB = SpellImplicitTargetInfo();
            escapeArtist->AttributesCu &= ~SPELL_ATTR0_CU_NEGATIVE_EFF1;
        }

        if (SpellInfo* hardiness = MutableSpell(SPELL_HARDINESS))
            hardiness->Effects[EFFECT_0].BasePoints = -HARDINESS_PERCENT - 1;
    }

    // The profession racials lose their skill bonus and become a cast time cut (negative is
    // faster). The class mask stays empty and the family is one no spell has, so the modifier
    // only reaches what the GlobalScript lets it: the spells of that profession.
    void ApplyProfessionRacialChanges()
    {
        professionSpells.clear();

        for (ProfessionRacial const& racial : PROFESSION_RACIALS)
        {
            SpellInfo* spellInfo = MutableSpell(racial.spellId);
            if (!spellInfo)
                continue;

            SetAura(spellInfo, EFFECT_0, SPELL_AURA_ADD_PCT_MODIFIER, -config.professionSpeed, SPELLMOD_CASTING_TIME);
            spellInfo->Effects[EFFECT_0].SpellClassMask = flag96();
            spellInfo->SpellFamilyName = SPELLFAMILY_FOREVER_RACIALS;
            professionSpells[racial.spellId];
        }

        for (uint32 i = 0; i < sSkillLineAbilityStore.GetNumRows(); ++i)
        {
            SkillLineAbilityEntry const* ability = sSkillLineAbilityStore.LookupEntry(i);
            if (!ability)
                continue;

            for (ProfessionRacial const& racial : PROFESSION_RACIALS)
                if (ability->SkillLine == racial.skill)
                    professionSpells[racial.spellId].insert(ability->Spell);
        }
    }

    // The core teaches racials from the race's skill line (on creation and at every login). Taking
    // the removed ones off that list stops it; UpdateSpells takes them off characters that have
    // them.
    void StopTeachingRemovedRacials()
    {
        for (uint32 spellId : REMOVED_RACIALS)
        {
            SkillLineAbilityMapBounds bounds = sSpellMgr->GetSkillLineAbilityMapBounds(spellId);
            for (auto itr = bounds.first; itr != bounds.second; ++itr)
                const_cast<SkillLineAbilityEntry*>(itr->second)->AcquireMethod = 0;
        }
    }

    // Masteries: the amounts, and the weapons each physical one counts. The core adds and removes
    // a passive that needs a weapon as the player changes gear (the aura is on while any weapon
    // slot holds a listed weapon), and the crit effect only counts for the hand doing the attack.
    void ApplyMasteryChanges()
    {
        for (WeaponMastery const& mastery : WEAPON_MASTERIES)
        {
            SpellInfo* spellInfo = MutableSpell(mastery.spellId);
            if (!spellInfo)
                continue;

            spellInfo->Effects[EFFECT_0].BasePoints = config.masteryCrit - 1;
            spellInfo->Effects[EFFECT_1].BasePoints = config.masteryHit - 1;
            spellInfo->EquippedItemSubClassMask = int32(config.weaponMasks[mastery.spellId]);
        }

        if (SpellInfo* feral = MutableSpell(SPELL_MASTERY_FERAL))
        {
            feral->Effects[EFFECT_0].BasePoints = config.masteryCrit - 1;
            feral->Effects[EFFECT_1].BasePoints = config.masteryHit - 1;
        }

        if (SpellInfo* spell = MutableSpell(SPELL_MASTERY_SPELL))
        {
            spell->Effects[EFFECT_0].BasePoints = config.masterySpellHit - 1;
            spell->Effects[EFFECT_1].BasePoints = config.masterySpellCrit - 1;
        }
    }

    // Once, when the server starts: passives are applied at login from these spells, so a config
    // reload can't change them for players already online.
    bool spellChangesApplied = false;

    void ApplySpellChanges()
    {
        if (spellChangesApplied)
            return;
        spellChangesApplied = true;

        if (config.races)
        {
            ApplyKeptRacialChanges();
            ApplyProfessionRacialChanges();
            StopTeachingRemovedRacials();
        }

        if (config.classes)
            ApplyMasteryChanges();
    }

    // Touch of the Grave's internal cooldown is its spell_proc row's; set it from the config.
    void ApplyProcCooldowns()
    {
        if (SpellProcEntry* procEntry = const_cast<SpellProcEntry*>(sSpellMgr->GetSpellProcEntry(SPELL_TOUCH_OF_THE_GRAVE)))
            procEntry->Cooldown = Milliseconds(config.touchCooldown);
    }

    // --- Learning and unlearning -----------------------------------------------------------------

    void SyncSpell(Player* player, uint32 spellId, bool shouldKnow)
    {
        bool const knows = player->HasSpell(spellId);
        if (shouldKnow && !knows)
            player->learnSpell(spellId);
        else if (!shouldKnow && knows)
            player->removeSpell(spellId, SPEC_MASK_ALL, false);
    }

    // Teach the player their race's new racials and their class's mastery and cooldown, and take
    // away whatever they shouldn't have: the previous version's spells, the stock racials that
    // went, and new spells of another race (after a race change) or of a switched-off half.
    void UpdateSpells(Player* player)
    {
        for (uint32 spellId : RETIRED_SPELLS)
            SyncSpell(player, spellId, false);

        // With races switched off the core teaches the stock racials again by itself.
        if (config.races)
            for (uint32 spellId : REMOVED_RACIALS)
                SyncSpell(player, spellId, false);

        for (RaceSpell const& racial : RACE_SPELLS)
            SyncSpell(player, racial.spellId, config.races && racial.race == player->getRace());

        // A spell can be on several classes' lists (Spell Mastery), so decide per spell.
        std::unordered_map<uint32, bool> classSpells;
        for (ClassSpell const& entry : CLASS_SPELLS)
        {
            bool& shouldKnow = classSpells[entry.spellId];
            shouldKnow = shouldKnow || (config.classes && entry.classId == player->getClass());
        }

        for (auto const& [spellId, shouldKnow] : classSpells)
            SyncSpell(player, spellId, shouldKnow);
    }

    bool IsProfessionSpell(uint32 racialSpellId, uint32 spellId)
    {
        auto itr = professionSpells.find(racialSpellId);
        return itr != professionSpells.end() && itr->second.count(spellId);
    }

    // Wild Instinct's effect for the druid's form: 0 spell haste, 1 energy, 2 attack power.
    SpellEffIndex WildInstinctEffectFor(ShapeshiftForm form)
    {
        switch (form)
        {
            case FORM_CAT:
                return EFFECT_1;
            case FORM_BEAR:
            case FORM_DIREBEAR:
                return EFFECT_2;
            default:
                return EFFECT_0;
        }
    }
}

// 90106 - Touch of the Grave. Weapon attacks have a 5% chance and harmful spells a 10% chance to
// heal the Undead (90107) for 25% of the damage that hit dealt, at most 5% of their max health.
// The target takes nothing extra. spell_proc says which hits count; the chance is rolled here
// because it differs between weapons and spells, and a failed roll (or a full health bar) doesn't
// start the proc cooldown.
class spell_forever_touch_of_the_grave : public AuraScript
{
    PrepareAuraScript(spell_forever_touch_of_the_grave);

    bool Validate(SpellInfo const* /*spellInfo*/) override
    {
        return ValidateSpellInfo({ SPELL_TOUCH_OF_THE_GRAVE_HEAL });
    }

    bool CheckProc(ProcEventInfo& eventInfo)
    {
        Unit* undead = GetTarget();
        Unit* victim = eventInfo.GetActionTarget();
        DamageInfo* damageInfo = eventInfo.GetDamageInfo();
        if (!config.races || !victim || victim == undead || !damageInfo || !damageInfo->GetDamage() || undead->IsFullHealth())
            return false;

        bool const weapon = eventInfo.GetTypeMask() & (PROC_FLAG_DONE_MELEE_AUTO_ATTACK | PROC_FLAG_DONE_SPELL_MELEE_DMG_CLASS
            | PROC_FLAG_DONE_RANGED_AUTO_ATTACK | PROC_FLAG_DONE_SPELL_RANGED_DMG_CLASS);

        return roll_chance_f(weapon ? config.touchWeaponChance : config.touchSpellChance);
    }

    void HandleProc(AuraEffect const* aurEff, ProcEventInfo& eventInfo)
    {
        PreventDefaultAction();

        Unit* undead = GetTarget();
        float const heal = CalculatePct(float(eventInfo.GetDamageInfo()->GetDamage()), config.touchHealPercent);
        float const cap = CalculatePct(float(undead->GetMaxHealth()), config.touchMaxHealthPercent);
        int32 const amount = std::max<int32>(1, int32(std::min(heal, cap)));

        undead->CastCustomSpell(SPELL_TOUCH_OF_THE_GRAVE_HEAL, SPELLVALUE_BASE_POINT0, amount, undead, true, nullptr, aurEff);
    }

    void Register() override
    {
        DoCheckProc += AuraCheckProcFn(spell_forever_touch_of_the_grave::CheckProc);
        OnEffectProc += AuraEffectProcFn(spell_forever_touch_of_the_grave::HandleProc, EFFECT_0, SPELL_AURA_DUMMY);
    }
};

// 90151 Crusader's Zeal, 90157 Arcane Fervor, 90158 Fel Frenzy: the spell power and healing
// power effects hold a percent in the game data; this turns it into that share of the caster's
// own spell power or healing power when the buff goes up. Other effects (attack power percent,
// the demon's damage) are left alone.
class spell_forever_class_power_percent : public AuraScript
{
    PrepareAuraScript(spell_forever_class_power_percent);

    void CalculateAmount(AuraEffect const* aurEff, int32& amount, bool& /*canBeRecalculated*/)
    {
        Unit* caster = GetCaster();
        if (!caster || caster != GetUnitOwner())
            return;

        switch (aurEff->GetAuraType())
        {
            case SPELL_AURA_MOD_DAMAGE_DONE:
                amount = int32(CalculatePct(float(caster->SpellBaseDamageBonusDone(SPELL_SCHOOL_MASK_MAGIC)), amount));
                break;
            case SPELL_AURA_MOD_HEALING_DONE:
                amount = int32(CalculatePct(float(caster->SpellBaseHealingBonusDone(SPELL_SCHOOL_MASK_ALL)), amount));
                break;
            default:
                break;
        }
    }

    void Register() override
    {
        DoEffectCalcAmount += AuraEffectCalcAmountFn(spell_forever_class_power_percent::CalculateAmount, EFFECT_ALL, SPELL_AURA_ANY);
    }
};

// 90159 Wild Instinct. One buff with three effects; only the one for the druid's form when it's
// cast counts: spell haste in caster form, Moonkin, Tree of Life and travel forms (effect 0),
// energy regeneration in Cat Form (effect 1), attack power in Bear Form (effect 2, plus rage).
class spell_forever_wild_instinct_aura : public AuraScript
{
    PrepareAuraScript(spell_forever_wild_instinct_aura);

    void CalculateAmount(AuraEffect const* aurEff, int32& amount, bool& /*canBeRecalculated*/)
    {
        if (Unit* caster = GetCaster())
            if (aurEff->GetEffIndex() != WildInstinctEffectFor(caster->GetShapeshiftForm()))
                amount = 0;
    }

    void Register() override
    {
        DoEffectCalcAmount += AuraEffectCalcAmountFn(spell_forever_wild_instinct_aura::CalculateAmount, EFFECT_ALL, SPELL_AURA_ANY);
    }
};

class spell_forever_wild_instinct : public SpellScript
{
    PrepareSpellScript(spell_forever_wild_instinct);

    void HandleAfterCast()
    {
        Unit* caster = GetCaster();
        if (caster && WildInstinctEffectFor(caster->GetShapeshiftForm()) == EFFECT_2)
            caster->ModifyPower(POWER_RAGE, WILD_INSTINCT_RAGE * 10);
    }

    void Register() override
    {
        AfterCast += SpellCastFn(spell_forever_wild_instinct::HandleAfterCast);
    }
};

class ForeverRacialsWorldScript : public WorldScript
{
public:
    ForeverRacialsWorldScript() : WorldScript("ForeverRacialsWorldScript",
        { WORLDHOOK_ON_AFTER_CONFIG_LOAD, WORLDHOOK_ON_BEFORE_WORLD_INITIALIZED }) { }

    void OnAfterConfigLoad(bool reload) override
    {
        // The spells are changed once, at startup (see ApplySpellChanges).
        if (!reload)
        {
            config.races   = sConfigMgr->GetOption<bool>("ForeverRacials.Races.Enable", true);
            config.classes = sConfigMgr->GetOption<bool>("ForeverRacials.Classes.Enable", true);

            config.professionSpeed = std::clamp(sConfigMgr->GetOption<int32>("ForeverRacials.Profession.SpeedPercent", 25), 0, 99);

            config.masteryHit       = sConfigMgr->GetOption<int32>("ForeverRacials.Mastery.HitPercent", 2);
            config.masteryCrit      = sConfigMgr->GetOption<int32>("ForeverRacials.Mastery.CritPercent", 2);
            config.masterySpellHit  = sConfigMgr->GetOption<int32>("ForeverRacials.Mastery.SpellHitPercent", 4);
            config.masterySpellCrit = sConfigMgr->GetOption<int32>("ForeverRacials.Mastery.SpellCritPercent", 2);

            for (WeaponMastery const& mastery : WEAPON_MASTERIES)
            {
                std::string const key = std::string("ForeverRacials.Mastery.") + mastery.configName + ".Weapons";
                uint32 mask = ParseWeaponMask(sConfigMgr->GetOption<std::string>(key, mastery.defaultWeapons), mastery.configName);

                // An empty mask would mean "any weapon" to the core.
                if (!mask)
                {
                    LOG_ERROR("module", "mod-forever-racials: {} lists no weapon types; using the default.", key);
                    mask = ParseWeaponMask(mastery.defaultWeapons, mastery.configName);
                }
                config.weaponMasks[mastery.spellId] = mask;
            }
        }

        config.touchWeaponChance     = sConfigMgr->GetOption<float>("ForeverRacials.TouchOfTheGrave.WeaponChance", 5.0f);
        config.touchSpellChance      = sConfigMgr->GetOption<float>("ForeverRacials.TouchOfTheGrave.SpellChance", 10.0f);
        config.touchHealPercent      = sConfigMgr->GetOption<float>("ForeverRacials.TouchOfTheGrave.HealPercent", 25.0f);
        config.touchMaxHealthPercent = sConfigMgr->GetOption<float>("ForeverRacials.TouchOfTheGrave.MaxHealthPercent", 5.0f);
        config.touchCooldown         = sConfigMgr->GetOption<uint32>("ForeverRacials.TouchOfTheGrave.Cooldown", 3000);

        // At startup the spell data isn't loaded yet; OnBeforeWorldInitialized does it then.
        if (reload)
            ApplyProcCooldowns();
    }

    void OnBeforeWorldInitialized() override
    {
        ApplySpellChanges();
        ApplyProcCooldowns();
    }
};

class ForeverRacialsPlayerScript : public PlayerScript
{
public:
    ForeverRacialsPlayerScript() : PlayerScript("ForeverRacialsPlayerScript", { PLAYERHOOK_ON_LOGIN }) { }

    void OnPlayerLogin(Player* player) override
    {
        UpdateSpells(player);
    }
};

// Lets each profession racial's cast time modifier reach its own profession's spells. Returning
// false means "affected"; true leaves the decision to the class mask, which is empty on these
// racials, so they touch nothing else.
class ForeverRacialsGlobalScript : public GlobalScript
{
public:
    ForeverRacialsGlobalScript() : GlobalScript("ForeverRacialsGlobalScript", { GLOBALHOOK_ON_IS_AFFECTED_BY_SPELL_MOD_CHECK }) { }

    bool OnIsAffectedBySpellModCheck(SpellInfo const* affectSpell, SpellInfo const* checkSpell, SpellModifier const* mod) override
    {
        if (mod->op != SPELLMOD_CASTING_TIME || !config.races)
            return true;

        return !IsProfessionSpell(affectSpell->Id, checkSpell->Id);
    }
};

void AddForeverRacialsScripts()
{
    new ForeverRacialsWorldScript();
    new ForeverRacialsPlayerScript();
    new ForeverRacialsGlobalScript();
    RegisterSpellScript(spell_forever_touch_of_the_grave);
    RegisterSpellScript(spell_forever_class_power_percent);
    RegisterSpellScript(spell_forever_wild_instinct_aura);
    RegisterSpellScript(spell_forever_wild_instinct);
}
