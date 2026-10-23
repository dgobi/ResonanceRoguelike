> Historical accepted record. Current main-only verification and remaining scope: [B3_VERIFICATION](B3_VERIFICATION.md) and [B3_DEFERRED](B3_DEFERRED.md).

# Boundaries after B2

Four previously reproduced defects remain strict baseline comparisons in the
complete default gate. Their exact underlying values are embedded in
`evidence/b2-results.json` under `b1_regressions.result.defects`.

| ID / next owner | Minimal reproduction and unchanged outcome |
|---|---|
| B3-GENERATIONS / B3 | Save surface grass; mutate to dirt; travel underground, which writes the surface; reload. Dirt is restored because travel changed the persisted scene after the player checkpoint. |
| B3-DIRTY-HOT / B3 | Persist an inactive grass map, change only its hot entry to mud, save elsewhere, read it through a new cold cache. Disk still contains grass. B2 processing changes may likewise remain hot until that map is explicitly stored or evicted. |
| C-DROP-EQUIPPED / C | Normal pickup, inventory equip and D-drop move the exact blade to the floor but leave its equipment reference/flag. B1/B2 refuse to serialize unowned equipped items. Transfer ownership repair remains separate. |
| UI-TEXT-HEIGHT / UI | Read the authored sarcophagus label through the normal inventory handler at 1280×720. The correct body opens but the panel ends at `If`, omitting the final sentence. |

B2 fixes Needs configuration, missing perk registration, omitted timer replacement
and the offscreen cache-owner mistake. Those four are positive regression
assertions now, not expected failures. The repaired processing scope is maps
already in memory; cold-map catch-up and durable dirty-cache flushing remain B3.

Additional source limits are explicitly not claimed as completed gameplay:

* The current engine stores temporary armor hit counters and creature
  suppression/disruption counters, but has no complete consumers for those effects.
  B2 preserves the instance values; later combat/effect work owns their behavior.
* Wight concentrate opens `_pending_consume`; the existing confirmation path is
  unfinished. Tests set sight-duration fixtures directly and verify their actual
  countdown, without claiming the item can currently grant it through the UI.
* The salve's use handler sets a speed bonus and duration, and expiry clears them.
  Ordinary movement does not yet apply that bonus to its timing. B2 verifies
  retention and expiry, not a new movement-speed mechanic.
* Container item encoding, crafting cancellation/refunds, corpse transfer and
  decay while carried, all actor AI policies and arbitrary RNG replay are outside
  this component reconstruction repair. Floor/map state keeps its existing
  pickle owner. No global item/actor UUID or whole-world simulator is introduced.

These additional entries are source-reviewed boundaries, distinguished from the
four dynamically reproduced deferred defects above. B3 should define coherent
save generations, inactive dirty flushing, interrupted-write recovery and
slot/deletion scope before claiming campaign rollback or crash safety. Use only
disposable test roots; personal-save migration remains unauthorised.
