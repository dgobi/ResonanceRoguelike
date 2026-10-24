# Generation changes, saved worlds and diagnosis

When a content edit does not appear, first identify **which stage owns the result**. A source definition, a saved selected placement and a visited scene are different things. Restarting reloads definitions, but it does not discard an existing plan or rebuild an already visited location.

## What an edit changes

| Edit | New world | Saved pending placement | Visited scene |
|---|---|---|---|
| Role/site memberships, weights, caps, counts or repetition | New policy can select differently. | Keeps saved selection and policy. | Keeps actual scene and mutations. |
| Geometry settings, road widths, settlement count or spacing | New plan uses them. | Keeps saved plan geometry. | No road or building reconstruction. |
| Selected layout's consumed geometry, entrances, targets or transform permissions | New plan may fit differently. | Affected placement can fail its dependency/geometry check until matching definitions are restored. | Existing saved terrain/content remains authoritative. |
| A consumed item/container/scene/loot dependency | New materialization uses valid current inputs. | Affected pending placement can be blocked specifically; unrelated pending scenes remain supported. | No automatic refill or respawn. Existing instances follow their own save/runtime policies. |
| Description, unused layout metadata or source formatting | Does not become topology merely by changing. | Structural projection excludes inactive/unconsumed layout metadata. | No regeneration. |
| Current text/presentation looked up by ID | Uses current definitions. | Existing by-ID policy remains. | Can show current text/presentation without rebuilding the map. Keep referenced IDs available. |

Selection-only data and consumed structural dependencies are intentionally separate. The structure dependency projection includes all supported weighted alternatives and referenced item/scene/loot/container semantics, not only the branch sampled in one preview. An unchosen alternative can still matter to compatibility.

## Historical plans

G3 through G7 formats 1 through 5 retain their exact saved values. They do not gain G8 streets or commons on load. Visited scenes retain actual older provenance and mutations. Pending scenes use explicit `g3-to-g8-v1` through `g7-to-g8-v1` adapters without reselecting the plan. New format-6 scenes use `g8-v1`. Current layout and selection recipe removal does not recompose pending saved towns; changed consumed structure or public-surface dependencies can reject only affected slices.

Absent/wg1/wg2 origins keep the legacy/no-plan route. No automatic personal-campaign migration, retrospective population repair or historical seam guarantee is implied. In particular, an already visited G3 starting surface retains its historical contents rather than receiving a new waystone by loading it.

Arrival order should not alter native content ownership. First creation builds the complete scene; revisiting, cold loading and checkpoint loading (F9 with `DEBUG_MODE = False`) restore actual state rather than selecting or populating again. An active/cached owner takes priority over generation. Travel updates the session overlay and **does not advance the explicit F5 checkpoint** (F5 is the save binding only with debug mode off).

## Common symptoms

| Symptom | Likely boundary | Next useful check |
|---|---|---|
| My building validates but never appears | Modern selection membership, context, hard caps or fit | Verify the exact ID in the intended role/site policy; run a planned preview and read its rejections. |
| I changed `weight`, but frequency seems unchanged | Wrong weight field or old saved plan | Modern roles use `placement.weight × policy weight`; legacy top-level weight is not its substitute. Use a fresh plan. |
| A new wilderness file appears only in town-edge legacy tests | Folder versus explicit modern membership | Register it in the featured landmark or additional-site policy with a connected profile. |
| A service door is rejected | Span, transform or access | Declare separate doors; check all cells, outward normal and reachability from the assigned join. |
| A crate looks right but is empty or unusable | Decorative paint versus actual container and interaction access | Add a supported container special, real pools and a required container target. Inspect realized contents. |
| A custom stair does not lead anywhere | Terrain versus travel ownership | Paint stairs and integrate a real submap/link; a normal building's tile does not allocate a level. |
| Loading works but entering one unseen place fails | Saved consumed dependency changed | Read the asset/dependency named in the error. Restore matching consumed definitions or use a new disposable world for the new content. |
| Reopening a place did not show my new floor plan | Visited scene is authoritative | Inspect a new disposable world or direct preview. |
| More rotations made no difference | Asset-first weighting and allowed frontage | Inspect the selected asset, actual normals and fitting geometry. Transform count is not a weight multiplier. |
| `--check-editor-catalog` reports stale | Browser catalog differs from current checkout bytes | Validate catalog, refresh, check again and reload the HTML editor. |
| A fresh required world fails | Impossible geometry/policy or a bounded search limit | Preserve the error; distinguish exhausted alternatives from an exhausted budget before adjusting controls. |

## Read the error category before changing the asset

| Error or diagnostic | Repair direction |
|---|---|
| `JSON_READ`, `ROOT`, duplicate key | UTF-8 strict JSON, one structure object, unique keys and finite values. |
| `DUPLICATE_ID`, `INSTALL_PATH` | Unique ID in the correct immediate supported folder. |
| `GRID`, `RAGGED_GRID`, `DIMENSION` | Equal row lengths and accurate dimensions; deliberately null-pad rather than crop. |
| `LEGEND_MISSING`, `TERRAIN_USED` | Define the used character and select a real terrain ID. |
| `DECOR_GRID`, `CONTAINER_CAPABILITY` | Full-ID/null nested arrays; actual container-capable decor. |
| `COORDINATE`, `CHOICE_COORDINATE` | Source coordinates inside the grid; weighted child coordinates must agree with their parent. |
| `REFERENCE`, `POOL_COUNT`, `WEIGHTS` | Existing IDs, valid roll range and every valid weighted branch. |
| `LAYOUT_ALIAS`, `LAYOUT_CONFLICT` | Use `layers` for ordinary content; only plazas retain the `layout` alias. |
| `PLACEMENT` | Complete version-one profile, exact supported fields, legal edge spans/normals and goals. |
| `INACTIVE_FIELD`, `INACTIVE_POOL_FIELD` | Retained data that the selected route does not consume; it is not a promise of behavior. |
| `DEFERRED_SPECIAL` | Physical body/stele behavior is deferred. Use a supported record or implement that feature separately. |

Do not remove required targets merely to turn a failure green. Their purpose is to expose an unusable intended feature. Repair the legitimate route or revise the design consciously.

## Validation levels

Use the smallest check that answers the remaining question. For a data author, the usual order is JSON/schema validation, every allowed transform, actual planned/assigned placement, and a new disposable world only when a visual or gameplay question remains. The project already supplies autonomous broader gates; routine verification need not require a desktop takeover or manual owner play.

```powershell
# Historical G6 authoring workflows and actual installed catalog behavior:
& $ResonancePython -X utf8 tools/verify_g6_authoring.py --evidence evidence/authoring/g6-workflows

# Actual headless browser import/edit/download workflows:
& $ResonancePython -X utf8 tools/verify_structure_editor.py --evidence evidence/authoring/browser

# Focused gameplay/generation regressions when the change warrants them:
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --evidence evidence/authoring/focused

# Broader current world diagnostic and real-handler journey:
& $ResonancePython -X utf8 tools/worldgen_g6_diagnostic.py --journey --evidence evidence/authoring/g6-diagnostic

# Full established production gate for an implementation/release boundary:
& $ResonancePython -X utf8 tools/verify_d.py
```

These are distinct from ordinary play. The long journey uses disclosed controls for topology/lifecycle verification; it is not a claim that combat or survival balance was exercised throughout. Diagnostic SVGs and real renderer PNGs should also be labelled distinctly.

## Documentation contradictions resolved in this wiki

| Older wording | Current instruction |
|---|---|
| “No new rotations or rural POIs” in the legacy middle of `STRUCTURE_AUTHORING.md` | Read as G2 history. G6 supports explicit planned transforms and independent roadside sites. |
| Register modern pools in `g3_config.json` | Current version-2 geometry uses separate `settlement_profiles.json`; extra sites use `poi_profiles.json`. |
| A `grid` array and `entities` list define a generic layout | The supported structure contract uses `layers`, `legend` and supported `special_tiles`. |
| `body` creates a corpse; top-level `stairs_up` places stairs | Physical body semantics remain deferred; actual stair terrain/fallback and links are separate. |
| Laboratory is 60 × 35 | Current laboratory is 60 × 16. |
| Low WFC weight guarantees at most one waystone | No uniqueness constraint exists in the solver. |
| WFC palette edits customize all current towns | Fresh shared-plan towns use the planned scene pipeline, separate from legacy WFC fill. |
| Delete saves to see a layout edit | Use a fresh disposable session or authoring preview. |

The original documents remain valuable history and design context. A current tutorial should not send you through an older route without identifying that route.

## Sources

- [Consumed dependencies and pending-placement errors](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/placement.py)
- [Scene adapters](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/scene_adapters.py)
- [Compiler diagnostics](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/generation/structure_contract.py)
- [G6 source-bound recorded verification and limits](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/docs/owner/WORLDGEN_G6.md)

## G7 composition integration

The current mixed parent workflow is documented in [Compounds](#compounds). A building export supplies the consumed child structure; a separate recipe supplies two required slots, an optional third slot, common paths, private bounds and permitted parent/child transforms. The existing painter edits the building, not the recipe. Use actual exported bytes in `--child`. Run `tools/verify_g7_authoring.py` for inherited and compound workflows; direct focused discovery now supplies its own absolute tools import path. Keep previous evidence immutable.

## A country preview added no road

Read `network.outcome` and the candidate trace. `disabled` means `max_shortcuts: 0`; `zero construction budget` means the shared integer edge allowance is zero. `no qualifying candidate` means the bounded examined proposals failed geometry, construction or marginal-benefit admission. Search-limit and global-budget exhaustion report unresolved search explicitly. `pairs_unexamined` is not evidence of infeasibility. The baseline must still be complete and valid.

Gold/green overlaps in the preview show reuse, not duplicate construction. A crossing ownership row is not a new physical bridge. Cut edges are graph edges whose removal disconnects a component, not river bridge objects. Four-neighbour physical distances are not macro search costs or diagonal-capable player input counts. A larger scene checkpoint after a longer coverage journey is not a network storage regression by itself; compare scopes and counts.
