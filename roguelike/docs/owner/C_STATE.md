# C ownership and transfer contract

The owner accepted B3 and authorized C on production `main`. The starting commit
is `65b02dfa3cd4ade1b2d470646cd46347af2d1d56`, tagged
`checkpoint/c-start-20261023`. No development copy, worktree or task branch was
created. Accepted-work commits remain required; no remote push is implied.

## Ownership

An item instance belongs to inventory, a floor list, a legacy scene entity list,
or a container. Equipment and the active light reference inventory instances;
they are not additional owners. Normal transfer paths use `item_transfers.py`.
Selections refer to exact instances, not item definition IDs. Inventory rejects
duplicate insertion and item use refuses an unowned stale selection.

- Dropping validates the destination first, moves the exact item, clears all its
  equipment slots/flag, recomputes armor including attunement, and releases its
  player light. Picking it up does not equip or relight it automatically.
- Floor pickup resolves the actual source list, including legacy entity items.
  It works with an empty bag and rejects stale/ambiguous sources or excess weight.
  Floor placement synchronizes coordinates and rejects duplicate placement.
- Take-all attempts items in order. Each successful item moves once; items that
  do not fit and corpses that require butchery stay on the floor. This is a
  documented partial transfer, not an all-or-nothing batch.
- Containers retain live items, including mutable instance fields, exactly as
  floor objects do. Browsing returns a list of references; taking the second of
  two same-definition items removes that exact instance. Closed/stale/capacity
  failures do not remove it. Only an empty container becomes looted.
- Old minimal container dictionaries are materialized once when browsed. Existing
  text bindings survive; unknown definitions fail without discarding rows. New
  container objects use the existing pickled scene format and survive checkpoints.
  This is development-format compatibility, not personal-save migration or a
  claim that older binaries can read new container state. Missing instance fields
  already lost by the old minimal encoding cannot be recovered.

`place_container` is a generation/fixture constructor for fresh items, not an
inventory deposit operation. There is no new deposit UI. This work does not add
global owner pointers or promise to repair arbitrary manually corrupted lists.

## Crafting and other producers

Crafting resolves all requirements before mutation. Plans keep exact instances
and chosen component preferences; each physical item fills one slot, with the
existing lowest-tier preference. Reusable tools remain owned and equipped.
Available physical components cover a slot before ambient shortfall; ambient
requirements are rechecked at confirmation.

World placement and passive processing consume nothing before valid confirmation.
Escape discards the plan without minting refund copies. Missing/stale ingredients,
invalid placement/output or insufficient output capacity keep materials intact.
Immediate output and ingredient removal commit together after checking capacity
net of consumed weight. Consumed equipped ingredients clear derived references.
Processing creates one job at confirmation and the existing completion system
delivers the floor output. Save/load while a cursor is pending saves inventory;
load cancels the cursor and releases its temporary references.

Drink-to-empty and empty-to-full vessel exchanges account for the replaced item's
weight. Failed refill leaves the empty vessel. Failed harvest leaves the plant.
Burnout uses the same removal path and clears the expired light owner reference.

These are synchronous transactions on the game event thread, with validation
failures checked before mutation. They are not a general rollback framework for
arbitrary exceptions, process termination during a turn, or multiplayer access.
B3 checkpoint publication and recovery remain the persistence boundary.

## Remaining boundaries

The separate sarcophagus text-height defect remains reproduced. Combat/effect
lifecycle work (temporary armor hit counters, suppression/disruption, wight
confirmation, throw targeting, salve timing), carried decay, and full RNG replay
remain separate. Corpse take-all preservation is tested; all butchery yield tables
and decay behavior are not certified by C. Automatic checkpoint pruning and
personal-save migration retain B3's explicit boundaries.

See [C_VERIFICATION](C_VERIFICATION.md) for actual acceptance evidence and commands.
