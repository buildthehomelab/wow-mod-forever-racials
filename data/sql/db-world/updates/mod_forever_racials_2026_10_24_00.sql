-- mod-forever-racials: Cultivation's herbs can be picked, and Plainsrunning gives 2% a stack.
--
-- Cultivation's herbs (9500700-9500739) had no lock (Data0 = 0), and the core can't open a
-- lockless chest: GameObject::Use has no chest case, and Spell::CheckCast fails an opening spell
-- on a gameobject without a lock. Lock 43 is "open kneeling" with no skill, the lock of hundreds
-- of quest crates and plants anyone can pick, so the herbs need no Herbalism.
--
-- Plainsrunning's speed buff (90109) goes from 1% to 2% a stack. The script also sets it in
-- memory; this keeps the database's copy the same as the client patch's.
--
-- Idempotent: safe to run again.

UPDATE `gameobject_template` SET `Data0` = 43 WHERE `entry` BETWEEN 9500700 AND 9500739;

UPDATE `spell_dbc` SET `EffectBasePoints_1` = 1 WHERE `ID` = 90109;
