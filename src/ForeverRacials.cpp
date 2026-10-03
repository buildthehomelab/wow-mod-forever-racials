/*
 * mod-forever-racials
 *
 * WoW Forever's racial rework on a 3.3.5 server, done as buffs: every race keeps what it has in
 * 3.3.5 and gains what WoW Forever gives it. The one removal is the Humans' Diplomacy. Blood
 * Elves and Draenei aren't in WoW Forever and are left alone.
 *
 * Like WoW Forever, each race shows 2 actives and 2 passives. The extra 3.3.5 racials
 * (resistances, Command, Gun, Bow and Throwing Specialization, Elusiveness, Da Voodoo Shuffle,
 * Cultivation's +15 Herbalism) keep working unchanged; patch-P hides them from the spellbook and
 * lists them in the tooltip of the passive they're folded into.
 *
 *   Human     Every Man for Himself, Perception (back, 2 min) | Sword Specialization (2% crit
 *             with swords and maces instead of 3 expertise), The Human Spirit (5% Spirit, was
 *             3%). Diplomacy is gone, as in WoW Forever.
 *   Dwarf     Stoneform (also 10% less physical damage), Find Treasure | Mace Specialization
 *             (2% crit with maces and guns), Big Game Hunter (new: 5% more damage to Beasts).
 *   Night Elf Shadowmeld, Elune's Light (new: 10% crit for 15 sec) | Quickness (adds 2% run
 *             speed), Wisp Spirit.
 *   Gnome     Escape Artist (then 3 sec immune to roots and snares), Eureka! (new: next 3 spells
 *             cost 50% less and deal 30% more) | Expansive Mind (also 5% max mana, rage, energy
 *             and runic power), Engineering Specialization.
 *   Orc       Blood Fury (attack power and spell power: 15% of yours, or the old flat amount if
 *             that's more), Shatter Curse (new: curse immunity, 10% less magic damage, 8 sec) |
 *             Axe Specialization (2% crit instead of 5 expertise), Hardiness (20%, was 15%).
 *   Undead    Will of the Forsaken, Cannibalize (restores mana too) | Touch of the Grave (new:
 *             weapon attacks 5% and harmful spells 10% chance to drain), Underwater Breathing.
 *   Tauren    War Stomp, Cultivation (new: grows a herb for your level that anyone can gather) |
 *             Endurance (adds 1% hit), Plainsrunning (new: 1% speed a second while moving, up to
 *             5%).
 *   Troll     Berserking, Rapid Regeneration (new: 50% of max health over 20 sec) |
 *             Regeneration, Beast Slaying.
 *
 * The new spells (90100-90111) come from spell_dbc on the server and patch-P on the client
 * (tools/build_patch.py). The stock racials are changed in memory when the server starts;
 * patch-P updates their tooltips. Each race can be turned off in the config.
 *
 * Released under the MIT License.
 */

#include "Config.h"
#include "GameObject.h"
#include "Log.h"
#include "Player.h"
#include "QuestDef.h"
#include "Random.h"
#include "ScriptMgr.h"
#include "Spell.h"
#include "SpellAuraEffects.h"
#include "SpellAuras.h"
#include "SpellInfo.h"
#include "SpellMgr.h"
#include "SpellScript.h"
#include "SpellScriptLoader.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <vector>

namespace
{
    // New spells: must match the SQL and tools/build_patch.py.
    constexpr uint32 SPELL_BIG_GAME_HUNTER = 90100;
    constexpr uint32 SPELL_ELUNES_LIGHT = 90101;
    constexpr uint32 SPELL_ESCAPE_ARTIST_IMMUNITY = 90102;
    constexpr uint32 SPELL_EUREKA = 90103;
    constexpr uint32 SPELL_EXPANSIVE_MIND_POWER = 90104;
    constexpr uint32 SPELL_SHATTER_CURSE = 90105;
    constexpr uint32 SPELL_TOUCH_OF_THE_GRAVE = 90106;
    constexpr uint32 SPELL_TOUCH_OF_THE_GRAVE_DRAIN = 90107;
    constexpr uint32 SPELL_PLAINSRUNNING = 90108;
    constexpr uint32 SPELL_PLAINSRUNNING_SPEED = 90109;
    constexpr uint32 SPELL_CULTIVATION = 90110;
    constexpr uint32 SPELL_RAPID_REGENERATION = 90111;

    // Stock spells.
    constexpr uint32 SPELL_PERCEPTION = 20600;
    constexpr uint32 SPELL_HUMAN_SWORD_SPEC = 20597;
    constexpr uint32 SPELL_HUMAN_MACE_SPEC = 20864;
    constexpr uint32 SPELL_DWARF_MACE_SPEC = 59224;
    constexpr uint32 SPELL_DWARF_GUN_SPEC = 20595;
    constexpr uint32 SPELL_ORC_AXE_SPEC = 20574;
    constexpr uint32 SPELL_HUMAN_SPIRIT = 20598;
    constexpr uint32 SPELL_DIPLOMACY = 20599;
    constexpr uint32 SPELL_STONEFORM_BUFF = 65116;
    constexpr uint32 SPELL_QUICKNESS = 20582;
    constexpr uint32 SPELL_ESCAPE_ARTIST = 20589;
    constexpr uint32 SPELL_EXPANSIVE_MIND = 20591;
    constexpr uint32 SPELL_BLOOD_FURY_AP = 20572;   // warriors, rogues, hunters, death knights
    constexpr uint32 SPELL_BLOOD_FURY_BOTH = 33697; // shamans
    constexpr uint32 SPELL_BLOOD_FURY_SP = 33702;   // mages, warlocks
    constexpr uint32 SPELL_HARDINESS = 20573;
    constexpr uint32 SPELL_CANNIBALIZE_HEAL = 20578;
    constexpr uint32 SPELL_ENDURANCE = 20550;

    // The fixed values the client patch's tooltips show. Changing them means rebuilding patch-P
    // (tools/build_patch.py has the same numbers).
    constexpr int32 HUMAN_SPIRIT_PERCENT = 5;
    constexpr uint32 PERCEPTION_COOLDOWN_MS = 120000;
    constexpr int32 STONEFORM_PHYSICAL_REDUCTION = 10;
    constexpr int32 QUICKNESS_SPEED_PERCENT = 2;
    constexpr int32 EXPANSIVE_MIND_POWER_PERCENT = 5;
    constexpr int32 HARDINESS_PERCENT = 20;
    constexpr int32 CANNIBALIZE_MANA_PERCENT = 7;
    constexpr int32 ENDURANCE_HIT_PERCENT = 1;
    constexpr uint8 PLAINSRUNNING_MAX_STACKS = 5;

    // mod-individual-progression keeps a player's progress as rewarded quests 66000 + state.
    constexpr uint32 IP_PROGRESSION_QUEST_BASE = 66000;
    constexpr uint8 IP_STATE_MAX = 18;
    constexpr uint8 IP_STATE_OUTLAND = 8;
    constexpr uint8 IP_STATE_NORTHREND = 13;

    struct Config
    {
        bool human = true;
        bool dwarf = true;
        bool nightElf = true;
        bool gnome = true;
        bool orc = true;
        bool undead = true;
        bool tauren = true;
        bool troll = true;

        int32 weaponCritPercent = 2;
        float bloodFuryPercent = 15.0f;

        float touchWeaponChance = 5.0f;
        float touchSpellChance = 10.0f;
        float touchPowerPercent = 25.0f;
        float touchMaxHealthPercent = 5.0f;
        uint32 touchCooldown = 3000;

        uint32 plainsrunningSecondsPerStack = 1;

        uint32 cultivationDespawnSeconds = 120;
        bool cultivationRespectProgression = true;
        bool ipEnabled = false;
    };

    Config config;

    bool IsRaceEnabled(uint8 race)
    {
        switch (race)
        {
            case RACE_HUMAN:     return config.human;
            case RACE_DWARF:     return config.dwarf;
            case RACE_NIGHTELF:  return config.nightElf;
            case RACE_GNOME:     return config.gnome;
            case RACE_ORC:       return config.orc;
            case RACE_UNDEAD_PLAYER: return config.undead;
            case RACE_TAUREN:    return config.tauren;
            case RACE_TROLL:     return config.troll;
            default:             return false;
        }
    }

    // --- In-memory changes to the stock racials ------------------------------------------------

    SpellInfo* MutableSpell(uint32 spellId)
    {
        SpellInfo* spellInfo = const_cast<SpellInfo*>(sSpellMgr->GetSpellInfo(spellId));
        if (!spellInfo)
            LOG_ERROR("module", "mod-forever-racials: spell {} is missing; its change is skipped.", spellId);
        return spellInfo;
    }

    // Turn an effect into a beneficial aura on the caster. amount is the real value; the game
    // data stores it as base points + 1 (one-sided die).
    void SetAura(SpellInfo* spellInfo, SpellEffIndex effIndex, AuraType aura, int32 amount, int32 misc = 0,
        uint32 amplitude = 0, float perLevel = 0.0f)
    {
        SpellEffectInfo& effect = spellInfo->Effects[effIndex];
        effect.Effect = SPELL_EFFECT_APPLY_AURA;
        effect.ApplyAuraName = aura;
        effect.BasePoints = amount - 1;
        effect.DieSides = 1;
        effect.RealPointsPerLevel = perLevel;
        effect.MiscValue = misc;
        effect.MiscValueB = 0;
        effect.Amplitude = amplitude;
        effect.TriggerSpell = 0;
        effect.TargetA = SpellImplicitTargetInfo(TARGET_UNIT_CASTER);
        effect.TargetB = SpellImplicitTargetInfo();

        // The core worked out at load which effects are harmful; these ones never are.
        spellInfo->AttributesCu &= ~(SPELL_ATTR0_CU_NEGATIVE_EFF0 << effIndex);
        spellInfo->AttributesCu |= (SPELL_ATTR0_CU_POSITIVE_EFF0 << effIndex);
    }

    // Expertise becomes crit for the same weapons: effect 0 for melee and ranged attacks (only
    // with the weapon doing the attack), effect 1 for spells (while any such weapon is equipped;
    // the core adds and removes item-dependent passives as you change gear).
    void MakeCritSpecialization(uint32 spellId)
    {
        if (SpellInfo* spellInfo = MutableSpell(spellId))
        {
            SetAura(spellInfo, EFFECT_0, SPELL_AURA_MOD_WEAPON_CRIT_PERCENT, config.weaponCritPercent);
            SetAura(spellInfo, EFFECT_1, SPELL_AURA_MOD_SPELL_CRIT_CHANCE, config.weaponCritPercent);
        }
    }

    void ApplyHumanChanges()
    {
        MakeCritSpecialization(SPELL_HUMAN_SWORD_SPEC);
        MakeCritSpecialization(SPELL_HUMAN_MACE_SPEC);

        if (SpellInfo* spirit = MutableSpell(SPELL_HUMAN_SPIRIT))
            spirit->Effects[EFFECT_0].BasePoints = HUMAN_SPIRIT_PERCENT - 1;

        if (SpellInfo* perception = MutableSpell(SPELL_PERCEPTION))
            perception->RecoveryTime = PERCEPTION_COOLDOWN_MS;

        // Diplomacy can't simply be unlearned: the core teaches racial passives again from the
        // Human skill line at every login. So it stays learned but gives 0% reputation (base
        // points + 1 on a one-sided die), and patch-P hides it from the spellbook.
        if (SpellInfo* diplomacy = MutableSpell(SPELL_DIPLOMACY))
            diplomacy->Effects[EFFECT_0].BasePoints = -1;
    }

    void ApplyDwarfChanges()
    {
        MakeCritSpecialization(SPELL_DWARF_MACE_SPEC);
        MakeCritSpecialization(SPELL_DWARF_GUN_SPEC); // was 1% ranged crit with guns

        // Stoneform's buff (cast with it through spell_linked_spell) keeps its 10% armor.
        if (SpellInfo* stoneform = MutableSpell(SPELL_STONEFORM_BUFF))
            SetAura(stoneform, EFFECT_1, SPELL_AURA_MOD_DAMAGE_PERCENT_TAKEN, -STONEFORM_PHYSICAL_REDUCTION, SPELL_SCHOOL_MASK_NORMAL);
    }

    void ApplyNightElfChanges()
    {
        // Speed that stacks with everything else, like the other always-on speed bonuses.
        if (SpellInfo* quickness = MutableSpell(SPELL_QUICKNESS))
            SetAura(quickness, EFFECT_2, SPELL_AURA_MOD_SPEED_ALWAYS, QUICKNESS_SPEED_PERCENT);
    }

    void ApplyGnomeChanges()
    {
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

        // The mana half; 90104 (hidden) carries rage, energy and runic power.
        if (SpellInfo* expansiveMind = MutableSpell(SPELL_EXPANSIVE_MIND))
            SetAura(expansiveMind, EFFECT_1, SPELL_AURA_MOD_INCREASE_ENERGY_PERCENT, EXPANSIVE_MIND_POWER_PERCENT, POWER_MANA);
    }

    void ApplyOrcChanges()
    {
        MakeCritSpecialization(SPELL_ORC_AXE_SPEC);

        // Every Blood Fury gives attack power and spell power. The added effects scale like the
        // stock ones (6 + 4 per level attack power, 5 + 2 per level spell power); the script
        // below raises them to a share of the Orc's own when that's more.
        if (SpellInfo* bloodFury = MutableSpell(SPELL_BLOOD_FURY_AP))
            SetAura(bloodFury, EFFECT_2, SPELL_AURA_MOD_DAMAGE_DONE, 5, SPELL_SCHOOL_MASK_MAGIC, 0, 2.0f);
        if (SpellInfo* bloodFury = MutableSpell(SPELL_BLOOD_FURY_BOTH))
            SetAura(bloodFury, EFFECT_2, SPELL_AURA_MOD_HEALING_DONE, 5, SPELL_SCHOOL_MASK_ALL, 0, 2.0f);
        if (SpellInfo* bloodFury = MutableSpell(SPELL_BLOOD_FURY_SP))
        {
            SetAura(bloodFury, EFFECT_0, SPELL_AURA_MOD_ATTACK_POWER, 6, 0, 0, 4.0f);
            SetAura(bloodFury, EFFECT_2, SPELL_AURA_MOD_RANGED_ATTACK_POWER, 6, 0, 0, 4.0f);
        }

        if (SpellInfo* hardiness = MutableSpell(SPELL_HARDINESS))
            hardiness->Effects[EFFECT_0].BasePoints = -HARDINESS_PERCENT - 1;
    }

    void ApplyUndeadChanges()
    {
        // 7% of max mana every 2 sec next to the 7% of max health. Anything that ends
        // Cannibalize ends both.
        if (SpellInfo* cannibalize = MutableSpell(SPELL_CANNIBALIZE_HEAL))
            SetAura(cannibalize, EFFECT_1, SPELL_AURA_OBS_MOD_POWER, CANNIBALIZE_MANA_PERCENT, POWER_MANA,
                cannibalize->Effects[EFFECT_0].Amplitude);
    }

    void ApplyTaurenChanges()
    {
        if (SpellInfo* endurance = MutableSpell(SPELL_ENDURANCE))
        {
            SetAura(endurance, EFFECT_1, SPELL_AURA_MOD_HIT_CHANCE, ENDURANCE_HIT_PERCENT);
            SetAura(endurance, EFFECT_2, SPELL_AURA_MOD_SPELL_HIT_CHANCE, ENDURANCE_HIT_PERCENT, SPELL_SCHOOL_MASK_ALL);
        }
    }

    // Once, when the server starts: the passives are applied at login from these spells, so a
    // config reload can't change them for players already online.
    bool spellChangesApplied = false;

    void ApplySpellChanges()
    {
        if (spellChangesApplied)
            return;
        spellChangesApplied = true;

        if (config.human)
            ApplyHumanChanges();
        if (config.dwarf)
            ApplyDwarfChanges();
        if (config.nightElf)
            ApplyNightElfChanges();
        if (config.gnome)
            ApplyGnomeChanges();
        if (config.orc)
            ApplyOrcChanges();
        if (config.undead)
            ApplyUndeadChanges();
        if (config.tauren)
            ApplyTaurenChanges();

        // Plainsrunning's speed is rebuilt from scratch as you move, so don't save it.
        if (SpellInfo* speed = MutableSpell(SPELL_PLAINSRUNNING_SPEED))
            speed->AttributesCu |= SPELL_ATTR0_CU_AURA_CANNOT_BE_SAVED;
    }

    // Touch of the Grave's internal cooldown is its spell_proc row's; set it from the config.
    void ApplyProcCooldowns()
    {
        if (SpellProcEntry* procEntry = const_cast<SpellProcEntry*>(sSpellMgr->GetSpellProcEntry(SPELL_TOUCH_OF_THE_GRAVE)))
            procEntry->Cooldown = Milliseconds(config.touchCooldown);
    }

    // --- Learning the new spells -----------------------------------------------------------------

    struct RacialSpell
    {
        uint8 race;
        uint32 spellId;
    };

    constexpr std::array<RacialSpell, 9> RACIAL_SPELLS = {{
        { RACE_HUMAN, SPELL_PERCEPTION },
        { RACE_DWARF, SPELL_BIG_GAME_HUNTER },
        { RACE_NIGHTELF, SPELL_ELUNES_LIGHT },
        { RACE_GNOME, SPELL_EUREKA },
        { RACE_ORC, SPELL_SHATTER_CURSE },
        { RACE_UNDEAD_PLAYER, SPELL_TOUCH_OF_THE_GRAVE },
        { RACE_TAUREN, SPELL_PLAINSRUNNING },
        { RACE_TAUREN, SPELL_CULTIVATION },
        { RACE_TROLL, SPELL_RAPID_REGENERATION },
    }};

    // Teach the player's race its new spells, and take away any the player shouldn't have: their
    // race is turned off, or they changed race (the core only drops racials that are on a skill
    // line, and these aren't).
    void UpdateRacialSpells(Player* player)
    {
        for (RacialSpell const& racial : RACIAL_SPELLS)
        {
            bool const shouldKnow = racial.race == player->getRace() && IsRaceEnabled(racial.race);
            bool const knows = player->HasSpell(racial.spellId);
            if (shouldKnow && !knows)
                player->learnSpell(racial.spellId);
            else if (!shouldKnow && knows)
                player->removeSpell(racial.spellId, SPEC_MASK_ALL, false);
        }

        // Expansive Mind's hidden half is a passive aura, not a spell to learn (learning it would
        // print "You have learned a new spell"). Passive auras aren't saved, so every login adds it.
        if (player->getRace() == RACE_GNOME && config.gnome && !player->HasAura(SPELL_EXPANSIVE_MIND_POWER))
            player->AddAura(SPELL_EXPANSIVE_MIND_POWER, player);
    }

    // --- Cultivation's herbs -----------------------------------------------------------------------

    // The herb nodes Cultivation grows, by the level they're gathered at. Each has a copy in
    // gameobject_template (9500700 + its index here) without the Herbalism lock; the SQL makes
    // them in this order.
    struct Herb
    {
        uint8 minLevel;
        uint8 progression; // mod-individual-progression state the herb's continent needs
    };

    constexpr uint32 CULTIVATED_HERB_FIRST_ENTRY = 9500700;

    constexpr std::array<Herb, 40> HERBS = {{
        {  1, 0 }, {  1, 0 }, {  1, 0 },                                        // Peacebloom, Silverleaf, Earthroot
        { 10, 0 }, { 10, 0 }, { 10, 0 },                                        // Mageroyal, Briarthorn, Bruiseweed
        { 20, 0 }, { 20, 0 }, { 20, 0 }, { 20, 0 },                             // Wild Steelbloom, Kingsblood, Grave Moss, Liferoot
        { 30, 0 }, { 30, 0 }, { 30, 0 }, { 30, 0 },                             // Fadeleaf, Goldthorn, Khadgar's Whisker, Wintersbite
        { 40, 0 }, { 40, 0 }, { 40, 0 }, { 40, 0 }, { 40, 0 }, { 40, 0 }, { 40, 0 }, // Firebloom, Purple Lotus, Arthas' Tears, Sungrass, Blindweed, Ghost Mushroom, Gromsblood
        { 50, 0 }, { 50, 0 }, { 50, 0 }, { 50, 0 }, { 50, 0 },                  // Golden Sansam, Dreamfoil, Mountain Silversage, Plaguebloom, Icecap
        { 58, IP_STATE_OUTLAND }, { 58, IP_STATE_OUTLAND }, { 58, IP_STATE_OUTLAND }, { 58, IP_STATE_OUTLAND },     // Felweed, Dreaming Glory, Ragveil, Terocone
        { 65, IP_STATE_OUTLAND }, { 65, IP_STATE_OUTLAND }, { 65, IP_STATE_OUTLAND }, { 65, IP_STATE_OUTLAND },     // Flame Cap, Ancient Lichen, Netherbloom, Nightmare Vine
        { 71, IP_STATE_NORTHREND }, { 71, IP_STATE_NORTHREND }, { 71, IP_STATE_NORTHREND }, { 71, IP_STATE_NORTHREND }, // Goldclover, Tiger Lily, Talandra's Rose, Adder's Tongue
        { 77, IP_STATE_NORTHREND }, { 77, IP_STATE_NORTHREND },                  // Lichbloom, Icethorn
    }};

    // The player's mod-individual-progression state, walked the same way that module does.
    uint8 GetProgressionState(Player* player)
    {
        uint8 state = 0;
        for (uint8 i = 1; i <= IP_STATE_MAX; ++i)
            if (player->GetQuestStatus(IP_PROGRESSION_QUEST_BASE + i) == QUEST_STATUS_REWARDED)
                state = i;
        return state;
    }

    // A random herb from the highest level bracket the player has reached (and, with
    // individual progression, whose continent they've unlocked).
    uint32 PickCultivatedHerb(Player* player)
    {
        uint8 const level = player->GetLevel();
        uint8 const progression = (config.ipEnabled && config.cultivationRespectProgression)
            ? GetProgressionState(player) : IP_STATE_MAX;

        uint8 bracket = 1;
        for (Herb const& herb : HERBS)
            if (herb.minLevel <= level && herb.progression <= progression)
                bracket = std::max(bracket, herb.minLevel);

        std::vector<uint32> choices;
        for (uint32 i = 0; i < HERBS.size(); ++i)
            if (HERBS[i].minLevel == bracket)
                choices.push_back(CULTIVATED_HERB_FIRST_ENTRY + i);

        return choices[urand(0, choices.size() - 1)];
    }
}

// 20572, 33697, 33702 - Blood Fury. Each effect gives the larger of its stock amount (which grows
// with level) and a share of the Orc's attack power, ranged attack power, spell power or healing
// power when it's cast.
class spell_forever_blood_fury : public AuraScript
{
    PrepareAuraScript(spell_forever_blood_fury);

    void CalculateAmount(AuraEffect const* aurEff, int32& amount, bool& /*canBeRecalculated*/)
    {
        Unit* caster = GetCaster();
        if (!config.orc || !caster || config.bloodFuryPercent <= 0.0f)
            return;

        float power = 0.0f;
        switch (aurEff->GetAuraType())
        {
            case SPELL_AURA_MOD_ATTACK_POWER:
                power = caster->GetTotalAttackPowerValue(BASE_ATTACK);
                break;
            case SPELL_AURA_MOD_RANGED_ATTACK_POWER:
                power = caster->GetTotalAttackPowerValue(RANGED_ATTACK);
                break;
            case SPELL_AURA_MOD_DAMAGE_DONE:
                power = float(caster->SpellBaseDamageBonusDone(SPELL_SCHOOL_MASK_MAGIC));
                break;
            case SPELL_AURA_MOD_HEALING_DONE:
                power = float(caster->SpellBaseHealingBonusDone(SPELL_SCHOOL_MASK_ALL));
                break;
            default:
                return;
        }

        amount = std::max(amount, int32(CalculatePct(power, config.bloodFuryPercent)));
    }

    void Register() override
    {
        DoEffectCalcAmount += AuraEffectCalcAmountFn(spell_forever_blood_fury::CalculateAmount, EFFECT_ALL, SPELL_AURA_ANY);
    }
};

// 90106 - Touch of the Grave. Weapon attacks have a 5% chance and harmful spells a 10% chance to
// drain the target (90107): Shadow damage equal to 25% of the Undead's attack power or spell
// power, whichever is higher, capped at 5% of their max health, and a heal for what it really
// dealt. spell_proc says which hits count; the chance is rolled here because it differs between
// weapons and spells, and a failed roll doesn't start the proc cooldown.
class spell_forever_touch_of_the_grave : public AuraScript
{
    PrepareAuraScript(spell_forever_touch_of_the_grave);

    bool Validate(SpellInfo const* /*spellInfo*/) override
    {
        return ValidateSpellInfo({ SPELL_TOUCH_OF_THE_GRAVE_DRAIN });
    }

    bool CheckProc(ProcEventInfo& eventInfo)
    {
        Unit* undead = GetTarget();
        Unit* victim = eventInfo.GetActionTarget();
        DamageInfo* damageInfo = eventInfo.GetDamageInfo();
        if (!config.undead || !victim || victim == undead || !victim->IsAlive() || !damageInfo || !damageInfo->GetDamage())
            return false;

        bool const weapon = eventInfo.GetTypeMask() & (PROC_FLAG_DONE_MELEE_AUTO_ATTACK | PROC_FLAG_DONE_SPELL_MELEE_DMG_CLASS
            | PROC_FLAG_DONE_RANGED_AUTO_ATTACK | PROC_FLAG_DONE_SPELL_RANGED_DMG_CLASS);

        return roll_chance_f(weapon ? config.touchWeaponChance : config.touchSpellChance);
    }

    void HandleProc(AuraEffect const* aurEff, ProcEventInfo& eventInfo)
    {
        PreventDefaultAction();

        Unit* undead = GetTarget();
        Unit* victim = eventInfo.GetActionTarget();

        float const power = std::max({ undead->GetTotalAttackPowerValue(BASE_ATTACK),
            undead->GetTotalAttackPowerValue(RANGED_ATTACK),
            float(undead->SpellBaseDamageBonusDone(SPELL_SCHOOL_MASK_SHADOW)) });

        float const cap = CalculatePct(float(undead->GetMaxHealth()), config.touchMaxHealthPercent);
        int32 const drain = std::max<int32>(1, int32(std::min(CalculatePct(power, config.touchPowerPercent), cap)));

        undead->CastCustomSpell(SPELL_TOUCH_OF_THE_GRAVE_DRAIN, SPELLVALUE_BASE_POINT0, drain, victim, true, nullptr, aurEff);
    }

    void Register() override
    {
        DoCheckProc += AuraCheckProcFn(spell_forever_touch_of_the_grave::CheckProc);
        OnEffectProc += AuraEffectProcFn(spell_forever_touch_of_the_grave::HandleProc, EFFECT_0, SPELL_AURA_DUMMY);
    }
};

// 90103 - Eureka! Its spell_proc row fires once when each spell the Gnome casts finishes, and
// every proc uses up one of its 3 charges. Only real spells and abilities count: not Eureka
// itself, not auto shots, and not things that cost nothing and neither hurt nor heal (mounts,
// hearthstones, food). Triggered spells never reach here.
class spell_forever_eureka : public AuraScript
{
    PrepareAuraScript(spell_forever_eureka);

    bool CheckProc(ProcEventInfo& eventInfo)
    {
        Spell const* spell = eventInfo.GetProcSpell();
        SpellInfo const* spellInfo = eventInfo.GetSpellInfo();
        if (!spell || !spellInfo || spellInfo->Id == SPELL_EUREKA || spellInfo->IsPassive() || spell->IsAutoRepeat())
            return false;

        return spell->GetPowerCost() > 0 || spellInfo->DmgClass != SPELL_DAMAGE_CLASS_NONE;
    }

    void Register() override
    {
        DoCheckProc += AuraCheckProcFn(spell_forever_eureka::CheckProc);
    }
};

// 90108 - Plainsrunning. Every second, while the Tauren is moving, one more stack of the speed
// buff (90109, 1% each) for every SecondsPerStack seconds of moving, up to 5. Standing still
// (or a taxi) removes it.
class spell_forever_plainsrunning : public AuraScript
{
    PrepareAuraScript(spell_forever_plainsrunning);

    bool Validate(SpellInfo const* /*spellInfo*/) override
    {
        return ValidateSpellInfo({ SPELL_PLAINSRUNNING_SPEED });
    }

    void HandlePeriodic(AuraEffect const* /*aurEff*/)
    {
        Unit* tauren = GetTarget();
        if (!config.tauren || !tauren->IsPlayer() || !tauren->isMoving() || tauren->IsInFlight() || !tauren->IsAlive())
        {
            _secondsMoving = 0;
            tauren->RemoveAurasDueToSpell(SPELL_PLAINSRUNNING_SPEED);
            return;
        }

        ++_secondsMoving;
        uint32 const perStack = std::max<uint32>(1, config.plainsrunningSecondsPerStack);
        uint8 const stacks = uint8(std::min<uint32>(PLAINSRUNNING_MAX_STACKS, _secondsMoving / perStack));
        if (!stacks)
            return;

        Aura* speed = tauren->GetAura(SPELL_PLAINSRUNNING_SPEED);
        if (!speed)
            speed = tauren->AddAura(SPELL_PLAINSRUNNING_SPEED, tauren);
        if (speed && speed->GetStackAmount() != stacks)
            speed->SetStackAmount(stacks);
    }

    void Register() override
    {
        OnEffectPeriodic += AuraEffectPeriodicFn(spell_forever_plainsrunning::HandlePeriodic, EFFECT_0, SPELL_AURA_PERIODIC_DUMMY);
    }

private:
    uint32 _secondsMoving = 0;
};

// 90110 - Cultivation. Grows a herb for the Tauren's level 2 yards in front of them: a copy of
// the herb node without the Herbalism lock, so anyone can gather it. It belongs to the Tauren
// (it goes if they leave the map or log out) and withers after DespawnSeconds.
class spell_forever_cultivation : public SpellScript
{
    PrepareSpellScript(spell_forever_cultivation);

    void HandleDummy(SpellEffIndex /*effIndex*/)
    {
        Unit* caster = GetCaster();
        Player* player = caster ? caster->ToPlayer() : nullptr;
        if (!player || !config.tauren)
            return;

        Position const pos = player->GetNearPosition(2.0f, 0.0f);
        float const angle = player->GetOrientation();
        float const rotation2 = std::sin(angle / 2.0f);
        float const rotation3 = std::cos(angle / 2.0f);

        player->SummonGameObject(PickCultivatedHerb(player), pos.GetPositionX(), pos.GetPositionY(), pos.GetPositionZ(),
            angle, 0.0f, 0.0f, rotation2, rotation3, config.cultivationDespawnSeconds);
    }

    void Register() override
    {
        OnEffectHit += SpellEffectFn(spell_forever_cultivation::HandleDummy, EFFECT_0, SPELL_EFFECT_DUMMY);
    }
};

class ForeverRacialsWorldScript : public WorldScript
{
public:
    ForeverRacialsWorldScript() : WorldScript("ForeverRacialsWorldScript") { }

    void OnAfterConfigLoad(bool reload) override
    {
        // The stock racials are changed once, at startup (see ApplySpellChanges).
        if (!reload)
        {
            config.human    = sConfigMgr->GetOption<bool>("ForeverRacials.Human.Enable", true);
            config.dwarf    = sConfigMgr->GetOption<bool>("ForeverRacials.Dwarf.Enable", true);
            config.nightElf = sConfigMgr->GetOption<bool>("ForeverRacials.NightElf.Enable", true);
            config.gnome    = sConfigMgr->GetOption<bool>("ForeverRacials.Gnome.Enable", true);
            config.orc      = sConfigMgr->GetOption<bool>("ForeverRacials.Orc.Enable", true);
            config.undead   = sConfigMgr->GetOption<bool>("ForeverRacials.Undead.Enable", true);
            config.tauren   = sConfigMgr->GetOption<bool>("ForeverRacials.Tauren.Enable", true);
            config.troll    = sConfigMgr->GetOption<bool>("ForeverRacials.Troll.Enable", true);
            config.weaponCritPercent = sConfigMgr->GetOption<int32>("ForeverRacials.WeaponSpecialization.CritPercent", 2);
        }

        config.bloodFuryPercent = sConfigMgr->GetOption<float>("ForeverRacials.BloodFury.Percent", 15.0f);

        config.touchWeaponChance     = sConfigMgr->GetOption<float>("ForeverRacials.TouchOfTheGrave.WeaponChance", 5.0f);
        config.touchSpellChance      = sConfigMgr->GetOption<float>("ForeverRacials.TouchOfTheGrave.SpellChance", 10.0f);
        config.touchPowerPercent     = sConfigMgr->GetOption<float>("ForeverRacials.TouchOfTheGrave.PowerPercent", 25.0f);
        config.touchMaxHealthPercent = sConfigMgr->GetOption<float>("ForeverRacials.TouchOfTheGrave.MaxHealthPercent", 5.0f);
        config.touchCooldown         = sConfigMgr->GetOption<uint32>("ForeverRacials.TouchOfTheGrave.Cooldown", 3000);

        config.plainsrunningSecondsPerStack = sConfigMgr->GetOption<uint32>("ForeverRacials.Plainsrunning.SecondsPerStack", 1);

        config.cultivationDespawnSeconds     = sConfigMgr->GetOption<uint32>("ForeverRacials.Cultivation.DespawnSeconds", 120);
        config.cultivationRespectProgression = sConfigMgr->GetOption<bool>("ForeverRacials.Cultivation.RespectProgression", true);
        config.ipEnabled = sConfigMgr->GetOption<bool>("IndividualProgression.Enable", false, false);

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
    ForeverRacialsPlayerScript() : PlayerScript("ForeverRacialsPlayerScript") { }

    void OnPlayerLogin(Player* player) override
    {
        UpdateRacialSpells(player);
    }
};

void AddForeverRacialsScripts()
{
    new ForeverRacialsWorldScript();
    new ForeverRacialsPlayerScript();
    RegisterSpellScript(spell_forever_blood_fury);
    RegisterSpellScript(spell_forever_touch_of_the_grave);
    RegisterSpellScript(spell_forever_eureka);
    RegisterSpellScript(spell_forever_plainsrunning);
    RegisterSpellScript(spell_forever_cultivation);
}
