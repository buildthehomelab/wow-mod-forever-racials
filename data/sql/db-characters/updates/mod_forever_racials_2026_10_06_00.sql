-- mod-forever-racials 2.0: take the previous version's racials off every character, with their
-- action bar buttons, saved cooldowns and saved auras.
--
-- 20600 is the old active Perception (Humans keep the stock passive, 58985); 90100, 90101, 90103,
-- 90104, 90108, 90109 and 90110 were Big Game Hunter, Elune's Light, Eureka!, Expansive Mind's
-- hidden half, Plainsrunning and its speed, and Cultivation. The server also does this at each
-- login, along with the stock racials a race no longer has. Idempotent: safe to run again.

DELETE FROM `character_spell` WHERE `spell` IN (20600, 90100, 90101, 90103, 90104, 90108, 90109, 90110);
DELETE FROM `character_action` WHERE `type` = 0 AND `action` IN (20600, 90100, 90101, 90103, 90104, 90108, 90109, 90110); -- 0 = spell button
DELETE FROM `character_spell_cooldown` WHERE `spell` IN (20600, 90100, 90101, 90103, 90104, 90108, 90109, 90110);
DELETE FROM `character_aura` WHERE `spell` IN (20600, 90100, 90101, 90103, 90104, 90108, 90109, 90110);
