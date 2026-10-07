-- mod-forever-racials: take the module's spells away from every character. Run it by hand on the
-- characters database, with the worldserver stopped: a running server saves online characters
-- over these tables. AzerothCore doesn't run it automatically.
--
-- While the module is still installed, ForeverRacials.Races.Enable = 0 or
-- ForeverRacials.Classes.Enable = 0 does the same thing for that half at each character's next
-- login. Run this after removing the module (with mod_forever_racials_uninstall_world.sql), or
-- characters keep spells the server no longer has.
--
-- 20600 is the old active Perception, which only the first version taught. 90100-90111 and
-- 90140-90161 are the module's own spells. Also clears them from action bars, saved cooldowns and
-- saved auras. The stock racials the module took away come back by themselves: the core teaches
-- them again at the next login. Idempotent: safe to run again.

DELETE FROM `character_spell` WHERE `spell` = 20600 OR `spell` BETWEEN 90100 AND 90111 OR `spell` BETWEEN 90140 AND 90161;
DELETE FROM `character_action` WHERE `type` = 0 -- 0 = spell button
    AND (`action` = 20600 OR `action` BETWEEN 90100 AND 90111 OR `action` BETWEEN 90140 AND 90161);
DELETE FROM `character_spell_cooldown` WHERE `spell` = 20600 OR `spell` BETWEEN 90100 AND 90111 OR `spell` BETWEEN 90140 AND 90161;
DELETE FROM `character_aura` WHERE `spell` = 20600 OR `spell` BETWEEN 90100 AND 90111 OR `spell` BETWEEN 90140 AND 90161;
DELETE FROM `pet_aura` WHERE `spell` BETWEEN 90150 AND 90161;
