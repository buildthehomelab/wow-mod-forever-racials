-- mod-forever-racials: take the module's racial spells away from every character. Run it by
-- hand on the characters database, with the worldserver stopped: a running server saves online
-- characters over these tables. AzerothCore doesn't run it automatically.
--
-- While the module is still installed, ForeverRacials.<Race>.Enable = 0 does the same thing for
-- that race at each character's next login. Run this after removing the module (with
-- mod_forever_racials_uninstall_world.sql), or characters keep spells the server no longer has.
--
-- 20600 is Perception, the old Human racial: nothing in 3.3.5 teaches it, so every character
-- that has it got it from this module (or a GM). 90100-90111 are the module's own spells. Also
-- clears them from action bars, saved cooldowns and saved auras. Idempotent: safe to run again.

DELETE FROM `character_spell` WHERE `spell` = 20600 OR `spell` BETWEEN 90100 AND 90111;
DELETE FROM `character_action` WHERE `type` = 0 AND (`action` = 20600 OR `action` BETWEEN 90100 AND 90111); -- 0 = spell button
DELETE FROM `character_spell_cooldown` WHERE `spell` = 20600 OR `spell` BETWEEN 90100 AND 90111;
DELETE FROM `character_aura` WHERE `spell` = 20600 OR `spell` BETWEEN 90100 AND 90111;
