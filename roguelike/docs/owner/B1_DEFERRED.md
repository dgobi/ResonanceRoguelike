> Historical accepted B1 contract. Current B2 status and commands are in [B2_VERIFICATION](B2_VERIFICATION.md). Four B2 defects below are now repaired; the current B1 regression runner asserts those repairs explicitly and retains the remaining baseline comparisons.

# Individually reproduced limits, baseline and B1 candidate

These are separately counted characterizations, not failed B1 acceptance properties
and not gameplay successes. The default gate compares the same exact signatures
on the unchanged Arc A source and the candidate. Source bindings, phase, PID and
values are retained in its worker records.

| ID / owner | Minimal reproduction and measured symptom |
|---|---|
| B2-NEEDS / B2 | Save hunger 0.2. Fresh bootstrap and direct `SaveManager.load` reconstruct `Needs` with `_configured=False`, no configured stages, and fallback label `Hungry`; configured label was `Sated`. Base rates happen to match for this definition, so the measured distinction is the stage behavior. Nondebug F9 actually calls `_configure_player_needs` and restores the configured `Sated` label; it is explicitly tested separately. |
| B2-HOOKS / B2 | Acquire `hardened_step`, register its actual hook and save. Fresh bootstrap restores the acquired perk but not `perk_hardened_step_tile_entered`. The same-process control retains the old hook; it is not fresh reconstruction. |
| B2-TIMER / B2 | Set `true_sight_turns=17`, save, then set it to 3. Direct load leaves 3; fresh bootstrap has 0. That omitted transient timer has no saved replay contract. |
| B3-GENERATIONS / B3 | Save surface grass, mutate it to dirt, descend (which writes the surface cache), then reload. The loaded scene is dirt: travel overwrote a scene record after the player checkpoint. |
| B3-DIRTY-HOT / B3 | Store an inactive scene with grass, change only its hot map to mud, call full save elsewhere, and read the inactive record through a new cache. Disk still has grass. |
| B2-OFFSCREEN-OWNER / B2/B3 simulation | Put a two-turn processing record in an inactive `SaveManager.cache.hot` map, advance one real turn. It remains at 2. `_advance_turn` asks nonexistent `SaveManager.hot`, so the intended offscreen loop does no work. |
| C-DROP-EQUIPPED / C transfers | Normal pickup of a fixture blade, inventory selection/Enter to equip, then D to drop. The exact blade leaves inventory and appears on the floor, but the weapon slot still points to it and its flag remains equipped. B1 rejects saving unowned equipment rather than silently changing its identity. The transfer action itself needs C's ownership fix. |
| UI-TEXT-HEIGHT / UI | Pick up the existing sarcophagus label, open inventory, read through Enter. The correct definition/body opens, but the content-sized panel measures raw newline count before wrapping. At 1280×720 the body is drawn only through `If`; the final sentence ending `do not ring the bells.` is omitted. Actual rendered-span observation and matching baseline/candidate captures establish this separately from successful reader dispatch. |

The supported processing journey uses a placed lit campfire and one acquired
`bitter_herb`, then real recipe/placement/wait inputs. It produces exactly one
`dried_bitter_herb` on the floor after 20 turns. It does not certify ambient
detection from the carried offhand torch, every recipe allocation, cancellation,
inventory-capacity rejection, all UI modes, combat balance or long-run progression.

Proceed to B2 component/derived-state reconstruction next. Plan B3 checkpoint
generations and write-failure handling separately. Personal saves remain outside
this development-format task.
