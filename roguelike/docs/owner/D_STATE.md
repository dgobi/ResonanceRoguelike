# D combat and effect lifecycle

C is owner-accepted at `288c70bb2105fc7770fa2c311cb983617bed933c`. D continues
in production `main`, with `checkpoint/d-start-20261023` before edits. No source
copies, task branches or worktrees were created. Local commits do not authorize push.

## Completed behavior

Marrow seal contributes temporary AV immediately. It refreshes the stronger bonus
and longer remaining hit count instead of stacking indefinitely. Every connecting
incoming attack, including full mitigation/block, spends one charge; dodge,
invincibility and waiting spend none. The last charge protects its own hit.
Expiry recomputes armor. Drop, re-equip and reload use the exact item's remaining
effect through C's equipment ownership rules.

Weapon coatings contribute to normal and moveset attacks and spend one charge
per connecting blow. Misses and blocked targeting retain charges. Expiry uses the
existing status callout API. Shared item definitions are never changed by attacks.
Sprint damage is reduced before applying HP/death, avoiding stale lethal flags
and overkill refunds. Combat uses the engine RNG; full RNG save/replay is not claimed.

Ability suppression disables passive/triggered abilities while ordinary AI can
continue. Disruption pauses creature actions and abilities without banking AI
movement credit or destroying pursuit state. Counters cover N enemy phases,
including the applying action's phase, and age once after simulation. Live and
pending pursuers share that clock. Retiring actors age before serialization;
inactive serialized actor records freeze. Stable creature IDs govern relevant
combat/ability lookups. Knight auras aggregate living, unsuppressed nearby sources;
farther knights cannot clear nearer ones. Suppressed/dead wraiths stop contributing.

Wight concentrate opens a Y/N prompt from inventory without a turn cost. N/Escape
keeps the exact item. Y validates ownership, consumes once, applies the authored
resonance/corruption cost and enables true sight for the authored duration. Other
keys remain modal until resolved. After resolution normal key bindings resume
(including Y's ordinary diagonal movement). Reload clears unfinished prompts.

Musk pellet uses the existing placement cursor, hints and renderer. Arrow/movement
keys aim, Enter confirms, Escape cancels. Targets must be visible, walkable, within
six tiles (unless a definition supplies `throw_range`), and have an unobstructed
flight path, including sealed-corner checks. Invalid/stale targets retain the
pellet and time. A valid throw consumes once and creates the authored radius-three,
six-turn disruption zone on that map. It affects creatures, including knights'
abilities, and covers the application turn. Overlapping zones independently expire.
The initial burst and message provide feedback; this arc adds no persistent cloud art.

Salve adds its authored speed to movement, combined additively with sprint speed.
Six moves at 1.2 speed advance five world turns; eleven at 2.2 advance five.
Fractional movement credit survives save/load. Waits, attacks and inventory uses
still advance time; blocked movement spends no turn or sprint charge. The final
sprint move uses the speed captured before its charge is consumed. Terrain debt
still advances extra world turns. Existing player-timer convention is retained:
the consuming action counts toward duration, so salve starts at 14 after use and
wight sight at 19 after confirmation. Expiry clears the corresponding bonus/flag.

The Severance Blade definition now supplies `equip_toggle` and separates `1d6`
from its +1 bonus. Its existing Disconnect move is therefore reachable using
normal inventory actions and its damage uses the existing dice parser correctly.
This is the only content-definition change; art and other data are preserved.

## State and compatibility

Existing B2 fields own armor/coating charges, actor counters, player timers and
movement credit. `LocalMap.disruption_zones` adds map-owned dictionaries with x/y,
radius and remaining turns. The existing trusted local scene pickle carries them
through B3 checkpoints. Missing fields in older maps are treated as empty; no
personal-save migration occurs. Active/hot maps age once per world turn (identity
deduplicated); cold maps freeze. Old binaries are not promised forward compatibility.
UI commands and the per-turn deduplication set are transient and not saved.

## Boundaries

This fulfills the D scope proposed after C: armor contacts, suppression/disruption,
wight confirmation, throwing and salve timing, plus the directly related combat
consistency fixes above. It is not a claim that every moveset/content feature is
complete. Heavy Blade's free-move-on-kill flag and Dissolution Blade's pool lifetime
remain separate, pre-existing moveset work. Also separate: UI-TEXT-HEIGHT, carried
decay, all butchery content, full RNG replay, personal-save migration and checkpoint
pruning. No owner testing, desktop control or personal-save fixtures are required.
