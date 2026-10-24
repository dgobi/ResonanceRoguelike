# Country-network tuning and previews (G9)

Fresh worlds use plan format 7, origin `wg9`, and planning settings version 4.
The planner first completes and validates the G8 baseline: geography, country
backbone, crossings, towns, layouts, commons, buildings, rural parents and all
ownership. It then adds at most two optional country connections. It preserves
every original record and assigned arrival/frontage/attachment reference.

The separate policy is `roguelike/data/generation/country_network.json`. Planning
settings in `g3_config.json` select `country_network_version: 1`, alongside
`settlement_layout_version: 1` and `selection_profile_version: 1`. The old filename
is intentional. Explicit settings version 3 still requests historical G8 layout
planning. Settings 1 and 2 retain their existing historical paths.

## Complete policy and units

```json
{
  "version": 1,
  "max_shortcuts": 2,
  "max_added_fraction": 0.25,
  "min_saved_steps": 500,
  "min_relative_improvement": 0.25,
  "candidate_pair_limit": 8,
  "search_expansion_limit": 8192,
  "world_expansion_budget": 32768
}
```

| Field | Allowed range | Meaning |
|---|---|---|
| `version` | Integer 1 | Complete policy schema; unknown/missing fields reject. |
| `max_shortcuts` | Integer 0–2 | Shared per-world limit; zero explicitly disables additions. |
| `max_added_fraction` | Finite 0–0.25 | Shared new unique country-centerline edge budget divided by the complete baseline union length; the integer cap is rounded down. |
| `min_saved_steps` | Integer 1–100000 | Minimum marginal four-neighbour physical tile steps saved for the named pair. Default 500. |
| `min_relative_improvement` | Finite 0.01–1 | Minimum marginal saving divided by the pair's current physical distance. Default 0.25. |
| `candidate_pair_limit` | Integer 1–32 | Number of primary pairs admitted to the finite proposal set. Default 8. |
| `search_expansion_limit` | Integer 1–16384 | Maximum expanded macro nodes per pair search. Default 8192. |
| `world_expansion_budget` | Integer 1–65536 | Shared expanded-node budget across this world's searches. Default 32768. |

Booleans are not integers. NaN, infinity, negative budgets, unsupported versions
and partial policies fail before publishing a world. Disabling augmentation does
not bypass required baseline validation.

Construction counts distinct cardinal **unit centerline edges**, including shared
runs only once. Reusing old edges costs zero new construction. Overlap between two
accepted shortcuts also counts once. The denominator stays fixed at the complete
G8 country union. A macro step spans **80 horizontal or 43 vertical tiles**.

Travel is shortest **four-neighbour tile steps on full-width road, bridge deck and
access cells**. It excludes off-road opportunities and transient actor behavior.
It differs from route-record length, macro hops, Manhattan distance, and real input
counts (the game supports diagonal movement). Primary endpoints are the saved
`start`, every `settlement-*`, `capital-gateway`, and `landmark` coordinate. Reports
keep all unordered pairs and the exact denominator. Crossing banks are infrastructure;
rural owners retain their separate required access checks.

## Bounded decisions and geometry

Candidate pairs are ordered by existing physical distance / Manhattan lower bound,
then potential saved distance, a dedicated deterministic network tie stream and
canonical pair ID. Bounded A* searches existing chunk centers with positive 80/43
travel costs, an admissible Manhattan heuristic and fixed neighbour ordering.
Reused roads retain their real traversal cost. The search uses hard geography and
ownership exclusions; it has no extra biome preference or speed model. A finite
proposal set and greedy admission are not a claim of global optimality.

Candidates are evaluated against the current staged network. Qualifying routes
rank by reduction of the worst primary-pair detour ratio, aggregate pair saving per
new edge, named-pair saving, lower construction, then canonical pair ID. After an
acceptance, all physical pair distances and marginal construction are recalculated.
Previously searched proposals may be reevaluated; their queues and graphs are not
saved in campaigns. The JSON preview retains the complete bounded decision trace.

No new full-width road cells may enter settlement, capital, building-owner,
compound-owner or submap chunks. Existing legal road geometry can be reused there.
Private lots, approaches, commons and reserved paths retain their exact protection.
New physical river crossings are forbidden. Existing owned decks may be reused
with explicit new route/water ownership rows; such rows are **not new bridges**.
Every touched chunk's complete road slice must connect locally. Geometry is replayed
through the normal reservation validator; new road rows precede private approaches
without changing their permissions or the relative order of original records.

An optional result can be `disabled`, `zero construction budget`, `no qualifying
candidate`, `global expansion budget exhausted`, or `bounded search exhausted
without qualifying candidate`. The report distinguishes individual construction,
geometry, duplicate and marginal-benefit rejections, and counts unexamined pairs.
Exhausted search is not proof that no legal route exists. Invalid required baseline
or malformed policy remains an error.

## Execute the five owner workflows

Use the project's dependency interpreter while importing code from this checkout:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/structure_authoring.py --network-preview --seed 20261023 --output authoring/network-ordinary.json
& $ResonancePython -X utf8 tools/structure_authoring.py --init-network authoring/network-draft --output authoring/network-init.json
& $ResonancePython -X utf8 tools/structure_authoring.py --network-preview --network-policy authoring/network-draft/g9_country_network.json --seed 20261023 --output authoring/network-draft-preview.json
```

1. Inspect the installed-policy preview. JSON contains fixed endpoint distances,
   all pairs, budgets, accepted/rejected candidates, reused/new lengths and graph
   scope. Matching SVG and PNG show exact baseline and augmented road geometry.
   These are diagrams; production scene views are separate evidence.
2. Initialize a complete draft, edit `max_added_fraction` to `0.1`, and preview
   seed `20261023` again. It admits no connection within that reduced budget.
   Repeating initialization preserves every existing draft byte.
3. Set `max_shortcuts` to `0`. The new world remains G9 format 7 with explicit
   disabled network metadata and the exact baseline geometric/content contract.
   It does not become a historical saved G8 world.
4. Use unchanged installed defaults for the positive seed `20261023`; use seed
   `0` for an ordinary no-qualifying-candidate result, or set the draft's global
   expansion budget to `1` for an explicit bounded-search outcome. Do not replace
   unhelpful samples to imply all seeds receive shortcuts.
5. Deliberately install and revert only after preview review. The automated
   workflow makes a disposable **data catalogue** under `.baseline`, copies the
   policy to its `generation/country_network.json`, calls `--data-root`, and restores
   the exact original policy bytes. Sentinels and all unrelated data hashes must
   survive. This is not a second game development checkout.

For a deliberate production installation, inspect `git status` and the policy diff,
make a named checkpoint, copy the reviewed complete draft to the installed policy,
rerun the preview and relevant gates, then commit the accepted policy change. Keep
owner edits separate. To recover, inspect a known checkpoint's policy with `git show`,
save it to a distinct draft, preview it, and deliberately install only that reviewed
file. Never reset the entire production checkout to demonstrate recovery.

All policy inputs, initializer targets and JSON/SVG/PNG outputs use the existing
staged `authoring_outputs.py` collision checks, including aliases/hardlinks and
catalogue refresh. Reports cannot overwrite a draft. Previews create no local scenes,
open no campaigns and do not install policy. The painter continues to edit buildings;
there is no graphical road editor.

## Saved worlds and verification

Saved canonical routes/crossings/reservations own geometry. The compact network
contract retains resolved policy, original-record identities, accepted IDs/pairs,
marginal cost/benefit and bounded work counts. Load/preflight checks references,
baseline identity, geometry, ownership, construction and benefit before installation.
Removing or editing current policy does not reoptimize saved routes. Old visited
scenes keep their actual creator and mutations; pending formats 1–6 use explicit
adapters. Fresh `wg9` scene randomness may differ from `wg8` despite equal baseline
building/geography records.

```powershell
& $ResonancePython -X utf8 tools/verify_g9_authoring.py --evidence evidence/worldgen-g9/owner-workflows
& $ResonancePython -X utf8 tools/worldgen_g9_diagnostic.py --journey --evidence evidence/worldgen-g9/owner-diagnostic
& $ResonancePython -X utf8 tools/verify_g9_release.py --evidence evidence/worldgen-g9/owner-release
```

Use a fresh evidence directory for each release attempt. The unfiltered focused
and production gates remain required; partial development runs are not releases.
No personal campaign is used. The maintained owner wiki and source/evidence binding
are part of delivery. Storage compaction, cache eviction, denser settlements,
organic road curves, new crossings, larger worlds and streaming remain outside G9.
