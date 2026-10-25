# G9 gameplay direction and wilderness observations

Reviewed source: `f9fe901417b360bc1fda84835e0a793eaac2f6df` in the read-only review checkout. This work changed no repository source, policy, scene or save. Small probes and the four rendered scenes are independent observations, not G10 implementation.

## Recommendation

Make G10 a bounded **wilderness character and terrain continuity** arc. Use a shared deterministic field at world-tile coordinates to give existing biomes readable patches, clearings, wet areas and rock masses. Keep the existing macro geography, destinations, country network, town plans, compounds and assets. Then demonstrate a short outing with the real player view, AI and survival running. This gives the next investment a visible player benefit and directly follows the owner's latest objective.

The first pass can cover all eight existing nonurban biome IDs through a handful of related profiles: forest; plains/heath; swamp/drowned wood; ash wastes; mountain/deep mountain. This does not require eight separate generators. Retain the special identity of VUKH and do not redevelop the capital or towns. Existing terrain/sprites suffice; no new art or broad content/encounter expansion is required.

The original proposal already placed variety, terrain adaptation and historical layers after connected composition, before larger-scale/continuous-rendering work. Its §5.2 explicitly proposes continuous environmental fields or shared border strips and rejects beginning with erosion/history simulation. G9 now supplies the bounded country connection milestone; a further network-quality arc would be a poor default after the owner's correction.

## What the current game actually does

`roguelike/generation/planned_scene.py:27–31` prepares a biome base through `generate_region(..., base_only=True)`. The infrastructure and structures are overlaid afterward, and `planned_dressing.dress` adds functional resources/waystones. G9 did not replace the underlying wilderness terrain generator.

`roguelike/generation/region_gen.py:201–228,280–350` makes trees or rocks with independent per-tile random draws: plains 6%, forest 35% before its local cleanup, mountain 45%. The mountain has an extra winding pass through each chunk's center. `_scatter_terrain` makes small locally centered grass/water blobs. These produce genuine visual variation, but broad terrain shapes still restart from a new local scene stream.

There is a particularly direct setting mismatch at `region_gen.py:102–137`: Ash Wastes uses `varied_grass`, 1% trees, and fourteen tall-grass clusters. `rendering/decor.py:47–55` turns that grass into general harvestable flowers and mushrooms. The shipped `data/biomes/ash_wastes.json` instead describes grey stone, the discharge, and land where nothing has grown since the bells. The name is not a license to invent a modern radioactive desert: its own text says the grey ground comes from stone, not literal ash.

The geography layer is also coarse. `world_gen.py:188–199` draws moisture independently for each chunk, and `:566–623` assigns a single biome ID from elevation/moisture. This is relevant to transitions, but replacing the macro climate/geography would reroll sites/roads and is outside this next bounded arc.

## Fresh small probes

`probe_wilderness.py` generated the three ordinary production metadata worlds, then 24 controlled base-only scenes (three scene seeds in each nonurban biome). No scene was created during world planning; the controlled scenes are explicitly not populated-gameplay evidence.

| World seed | Wilderness cardinal neighbor pairs | Different biome labels | Fraction |
|---|---:|---:|---:|
| 0 | 32,310 | 22,155 | 68.57% |
| 20261023 | 32,383 | 22,119 | 68.30% |
| 29417 | 32,382 | 22,206 | 68.58% |

These are label-adjacency counts, not a percentage of broken seams or bad gameplay. They argue for bounded transition handling around existing labels, and against claiming a local terrain patch will eliminate all abrupt regional changes.

`render_wilderness_baseline.py` independently generated ordinary seed `20261023`, selected the nearest unowned scene of each requested biome to the starting chunk, and materialized full native scenes through `create_surface`. Selection excludes rivers, submaps, routes, placements, compounds and public spaces; it does not change biome IDs or force content. The existing production renderer supplies each image. Visibility is deliberately revealed for the comparison; these are not normal-FOV captures.

| Ordinary scene | Terrain observation | Native actors |
|---|---|---:|
| Forest (73,100) | 707 trees; 2,516 grass; 133 tall grass; 25 shallow water; 55 dead wood; 4 flint | 4 |
| Drowned Wood (79,106) | 676 trees; 2,490 mud; 267 shallow water; 7 dead wood | 4 |
| Ash Wastes (72,103) | 3,096 grass + 272 tall grass = **97.91%** of 3,440 cells; 36 trees; 33 flint; 3 dead wood | 4 |
| Mountain (73,93) | 1,502 rock; 1,899 gravel; 39 flint | 3 |

The Ash Wastes scene also contains 125 harvestable plant decor entries: 30 Pilgrim's Woe, 29 Murk Violet, 29 Sulphur Cap and 37 Prophet's Eye. Its terrain is not merely using a misleading color; it is materially green and fertile under the current placement logic. The actual mountain rendering shows pronounced tile-scale rock/gravel noise. Forest and drowned wood are distinct now, but both benefit from larger coherent patches and cross-boundary continuation.

The contact sheet `views/g9-wilderness-baseline.png` was visually inspected. All four source PNGs and the contact sheet verify as complete PNGs. Exact source identities, actor counts, terrain/decor counts, functional records and image hashes are in `views/baseline-views.json`.

## Concrete scope for the next brief

### Intended player result

An ordinary short walk should pass through recognizable thickets and clearings, open heath, wet ground with convincing water/tree relationships, and barren stony wastes according to the existing biome. Mountain rock should read as masses and gaps rather than nearly independent tiles. Patterns should continue across chunk boundaries, and the player should still find and use established roads, stairs and resources.

Use the existing terrain table deliberately. `grass`, `tall_grass`, `mud`, `shallow_water`, `gravel`, `rock`, `ash`, `grey_stone`, `worn_stone` and `ancient_floor` already exist, but have different semantics. `grey_stone` and `rock` block movement; `ancient_floor` means laid ancient stone; literal ash should not become the whole biome merely because its ID is `ash_wastes`. A blanket gray blocking fill would violate playability and lore. Keep the existing depleted/gathered states and native interactions.

A compact active profile can select compatible existing palettes, density/scale ranges and modest transition widths. Use at least two spatial scales only if they visibly improve the result. Do not create a general ecology framework or expose dozens of knobs. Existing wilderness-zone JSON contains aspirational `terrain_palette`, `structures` and `scatter` fields that are not automatically consumed by the present terrain route; do not document them as active controls without implementing and validating a specific route.

### Geometry and continuity

Sample broad forms from world seed, generation/policy identity, absolute tile position and a stable purpose key. Existing chunk seed must not independently restart a broad form at the border. Bounded neighboring metadata is sufficient; do not create/cache neighboring local scenes to decide this scene's terrain.

Soften density/palette transitions over a small declared band using saved surrounding biome information, while retaining recognizable biome cores. Treat intentional ecological contrast separately from accidental borders. A split-rectangle/whole-rectangle test at identical world coordinates is a stronger continuity check than requiring adjacent rows of different physical tiles to be identical.

Keep all planned water/deck/road/approach/common/structure cells authoritative and keep their existing validation. Avoid unplanned deep water or blocking growth that severs the mandatory network. Off-road terrain need not make every rock pocket accessible; required starts, stairs, doors and interactables must be accessible under actual movement rules. Do not clear every edge tile or stamp an artificial cross through every chunk to satisfy a test.

### Important integration hazards

1. `planned_scene.py:29` converts town base terrain to PLAINS before the common base call. A modern wilderness pass gated only on the copied `base.region_type` would silently alter town backgrounds despite excluding towns in the brief. Gate using original ownership/context, or retain an explicit legacy urban base path.
2. Submap surface entrances are not yet resolved in the world plan. `_place_submap_entrance` chooses legal positions during materialization. Preserve submap chunk/ID/type/links and genuine saved entrance locations, but do not demand byte-identical surface entrance coordinates between fresh G9 and G10 scenes unless that is deliberately implemented. Changed natural terrain may change a new world's legal entrance candidate.
3. The terrain table feeds real movement costs, line of sight, plant/resource generation and actor eligibility. This cannot be verified only as a picture. Keep creature roster/probability, survival economy and loot rules outside scope; report consequences of placement changes rather than silently tuning them.
4. Generic `varied_grass` creates plant decor. Ash core treatment must address that consumer, not only paint a different base color afterward. Preserve authored contents rather than running a late indiscriminate cleanup through structures.

## Compatibility boundary

The current global `GENERATION_REVISION='wg9'` influences all initial-generation RNG streams (`generation/context.py`). `planned_scene.py` uses that default and publishes `wg9` scene provenance for all supported plan origins. `scene_adapters.py` distinguishes actual scene revision from unchanged saved plan origin. The G9 lifecycle tests explicitly demonstrate visited wg8 scenes remaining wg8 while pending format-6 scenes first materialize through the g8-to-g9 adapter.

Therefore, simply changing every `wg9` string to `wg10` is not an adequate compatibility design. Retain a concrete historical terrain path for plans without the new surface contract; decide and document the new scene adapter. Do not relabel old cached content or rerun old world/road/site planning. A saved new-world surface recipe/seed identity must govern pending chunks after installed tuning changes. Keep parameters compact rather than persisting every world tile or field array.

Capture one genuine pre-edit G9 checkpoint containing visited modified wilderness and pending wilderness, plus existing town/road/site state. Verify visited fingerprints, harvest/depletion and independent contents; verify pending materialization under its declared historical policy, then cold load/F9 and a late-generation failure rollback. The existing source has several exact-version tests (`version==7`, `(6,7)`) in plan validation, slicing and save dispatch; audit those if the new contract changes plan version, without weakening old corrupt-save rejection.

## Proportionate evidence

The result should include ordinary scenes and several adjacent-chunk montages for the same three seeds, with equivalent G9/G10 production rendering. Show disclosed complete-reveal diagnostic views and separate normal-FOV player views. Include same-biome and cross-biome seams, a river crossing/road, a town approach, a compound or house, and a real submap entrance. Do not demand every possible biome pair or a huge all-world materialization.

A small controlled fixture should prove the split/whole field invariant, different visit/process hash ordering, bounded halo/no neighbor scenes, bad-profile rejection and protected geometry. Preserve ordinary G9 route and site projections exactly. Record actual per-scene and planning overhead on the existing machine; do not turn the five-second country planner into another optimization project unless this change introduces a concrete regression.

Add one bounded ordinary outing using real movement/interactions with normal AI and survival, no invincibility, from ordinary startup with existing equipment. Use a reachable resource/waystone/entrance and return or reach a nearby safe goal. Capture resources consumed/gained, damage/encounters, and normal FOV. This complements the longer paused/invincible engineering journey; it does not prove whole-game balance or require every unplanned expedition to succeed. Avoid asserting that an 8,063-step required pair is viable solely because the G9 geometry harness can walk it.

Run the established focused and unfiltered production gates once against final source plus the meaningful new cases. Retain a compact change report, bounded evidence, source identity and publication readback. No wiki rebuild, wiki chapter sweep or browser-download matrix belongs in this brief. The owner's latest instruction supersedes the older AGENTS ongoing-wiki rule; one explicit narrow wording correction to that rule would prevent future ambiguity.

## Alternatives deferred

| Candidate | Assessment |
|---|---|
| More road search/efficiency or organic roads | G9 achieved its declared feature. Further metric tuning does not directly address the owner's requested world feel. |
| More roadside POIs/new ruins | Valuable later, but more templates do not fix fertile Ash Wastes or tile-noise mountains. Existing compounds already exercise placement. |
| Storage/cache redesign | Costs are real and worth a separately scoped profile later; G9's larger coverage checkpoint alone is not a newly demonstrated blocker. |
| Climate/hydrology/history simulation | Excessively broad and rerolls established geography/sites. Improve appearance through bounded composition. |
| Continuous viewport | Distinct rendering/visibility/entity-query arc; improve the actual material before presenting it continuously. |
| Wilderness terrain character | Immediate visible payoff, concrete mismatch, existing assets and a clear integration boundary. Recommended. |
