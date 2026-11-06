# Contested remains and local scavenging · SYS-5

Gutter Gleaners and Pale Carrion Beetles spend ordinary decisions approaching
and feeding on exposed flesh. The attachment is shared; their melee hosts remain
strike-and-withdraw and territorial direct melee. Feeding grants no healing,
XP, loot, speed or allegiance change. A threat can interrupt the opportunity.

## Player controls and physical cost

Select eligible loose flesh in inventory and press **P**, then confirm **Place
one portion here**. Success costs one ordinary action. Esc, stale ownership or
position, denied action and failed placement are free. A one-count item itself
moves to the floor. A larger stack loses one count and creates one copied unit
with a fresh resource identity and its captured physical properties. Ordinary
Drop retains its existing behavior. Inventory and Look distinguish portions,
intact remains and stripped remains.

Each completion consumes exactly one count of the remembered floor item, or
marks the exact corpse stripped once. No future harvest rolls are taken.
Inventory, equipment, open or closed containers, processing owners and cached
scenes are ineligible. Pickup can invalidate a commitment; two creatures do not
reserve food or share progress. Exact identity, location, count, ownership and
legal contact are checked again at completion.

A stripped corpse retains its source, complete captured recipe and running
decay. Butchery retains equipped cutting tier, bone-reader bonus, first-row
precedence on equal thresholds, quantity rolls and the paid cost
`max(1, 5 - (actual cutting tier - selected threshold))`. Only outputs captured
as flesh are suppressed. Empty selected yields consume the corpse at normal
cost. Failed output publication or final source removal restores exact floor
ownership and charges no harvest debt. RNG is not rewound.

## Authoring and capture

Loose raw flesh declares exactly one `{"tag":"flesh","tier":1}` keyword. It
must be an ordinary loose item, not a corpse or vessel; a bound use, if present,
must be eating. Fresh Crow Meat, Stalker Meat and Gleaner Flesh have the
capability. Existing instances retain their own copied eligibility.

Creature Harvest controls expose **Flesh removed by scavenging** per output:

```json
{"item_id":"crow_meat","quantity_min":1,"quantity_max":2,"flesh":true}
```

The output must be unique, saved, constructible loose flesh. Repeated item IDs
must have the same designation across every tier. Each fresh eligible corpse
captures the complete effective ordered recipe, including defaults and false
designations. Later item tags, source tiers or quantities do not reinterpret it.
Native death and authored remains share `engine/flesh_resources.py::create_corpse`.

Authored underground rooms support the direct record:

```json
{"type":"remains","x":10,"y":5,"creature_id":"plague_crow"}
```

Use **Placement kind → remains** and a supported saved source: a unique
non-player, non-ephemeral Actor with a valid explicit flesh recipe. No source
Actor is spawned, killed or credited. The common constructor produces a real
intact corpse and captured initial decay. Surface/weighted records, arbitrary
state/recipe payloads, blocked placement, arrival/stair occupation and unsupported
or ambiguous sources reject. Trial construction and final access checks precede
map publication.

## Shared behavior

On an eligible new-ID ordinary hostile melee variant, choose either supported
recipe and enable **Local scavenging**. Original enrollment governs later edits;
raw source cannot promote an incompatible existing creature. Each actor captures:

```json
"enemy_scavenging": {
  "version": 1,
  "approach_opportunities": 8,
  "feed_opportunities": 3
}
```

Approach accepts exact integers 1–16 and feeding 2–8. The Gleaner ships with
five feeding decisions at ordinary speed 0.7; the Beetle uses three at speed 1.
Every feeding step occupies the whole decision. Rendering, inspection and free
input do not advance it; the ordinary speed scheduler controls opportunities.

Priority is action denial/death/scene ownership, actual or retained hostile
commitment, required withdrawal/hold or territorial return, wounded regroup,
attributed alarms, applicable anonymous sound, then food. A territorial guard
acquires inside its original defended radius, routes inside its original
excursion and returns afterward. Food never moves the anchor or relaxes defence.
Hosts without the attachment retain their existing behavior.

Discovery uses shared point sight: current scene light, darkvision, range,
weather and actual geometry. Hearing discloses no food. Select the shortest
reachable route, then stable resource UID for ties. A remembered approach retains
only the observed position and exact captured resource; it never follows an
unseen relocation. Unchanged unreachable/exhausted resources are suppressed until
local geometry/occupancy or the resource changes, or intervening activity brings
the eater into actual legal contact. Mandatory return cannot restart an endless
series of failed territorial excursions.

## Save and scene boundaries

Valid same-scene partial work and captured tuning survive F5/F9 and cold load.
Restoration rebinds only the matching resource identity and capture at its
remembered location. Interruption, lost contact, ownership loss or successful
departure abandons partial work without spending flesh. Inactive scenes do no
food work or additional decay catch-up. Revisit does not restore depletion.

Modern items and actors carry positive version discriminators. Incomplete,
malformed, aliased or contradictory modern state rejects before candidate-session
installation. Genuine pre-feature instances retain absence, including B1 rows
without keywords. Historical corpses retain the older live-table butchery policy.
There is no campaign migration.

## Ordinary content and evidence

`barrow_scavenger_store` combines a light-limited Gleaner, crow remains, two
scarce portions, a fire, shelving cover and a far coffer. `barrow_carrion_sump`
combines a darkvision territorial Beetle, screened stalker remains, quiet/force
access and a southern bypass. Neither requires bait as a key or guarantees safe
passage. The original seven selector rows remain in order; two weight-1 rows are
appended at unchanged 0.35 chance.

`workbench/scripts/run-sys-5.mjs` records packaged creation/publication, source
reopen, native remains and living-host use. Three→five saved feeding, old Reset
and dirty seven exclusion use distinct captures. `tools/verify_sys_5_play.py`
uses actual ordinary assignments and inputs, with disclosed initial surface
approach staging and full-map routing. `tools/verify_sys_5.py` owns the complete
final matrix. The source-bound delivery record reports measured results and
limitations. All witnesses use disposable saves.
