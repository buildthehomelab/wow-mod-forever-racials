-- mod-forever-racials: undo the module's world database changes. Run it by hand on the world
-- database after removing the module; AzerothCore doesn't run it automatically (it only runs the
-- module's db-world folder). Run mod_forever_racials_uninstall_characters.sql too.
--
-- Turning a race off doesn't need this: its ForeverRacials.<Race>.Enable = 0 is enough. This is
-- for taking the module out of the server for good, so the core doesn't log missing scripts.
--
-- Removes the new spells (90100-90111) with their spell_proc and script rows, the Blood Fury
-- script binding, and Cultivation's herbs (9500700-9500739). The changes to the stock racials
-- are only made in memory, so there's nothing to undo for them. Idempotent: safe to run again.

DELETE FROM `spell_script_names` WHERE `ScriptName` IN ('spell_forever_blood_fury', 'spell_forever_touch_of_the_grave',
    'spell_forever_eureka', 'spell_forever_plainsrunning', 'spell_forever_cultivation');

DELETE FROM `spell_proc` WHERE `SpellId` IN (90103, 90106);
DELETE FROM `spell_dbc` WHERE `ID` BETWEEN 90100 AND 90111;

DELETE FROM `gameobject_template` WHERE `entry` BETWEEN 9500700 AND 9500739;
