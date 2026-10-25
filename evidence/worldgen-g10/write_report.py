"""Write the concise owner completion report from verified final receipts."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent


def main():
    index=json.loads((TASK/'artifact-index.json').read_text());assert index['passed']
    final=TASK/'final-b';release=json.loads((final/'release.json').read_text());assert release['passed']
    run=json.loads((final/'g10/diagnostic/run.json').read_text());assert run['passed']
    expedition=json.loads((final/'g10/expedition/expedition.json').read_text());assert expedition['passed']
    cold=json.loads((final/'cold-expedition.json').read_text());assert cold['passed']
    boundary=json.loads((final/'boundary-costs.json').read_text());assert boundary['passed']
    logs=(final/'focused/focused-tests.txt').read_text(encoding='utf-8')
    match=re.search(r'Ran (\d+) tests in ([\d.]+)s',logs);assert match
    tests=int(match[1]);totals=index['production']['totals']
    ordinary=next(r for r in run['runs'] if r['seed']==20261023)
    rows='\n'.join(f"| {s['biome']} {tuple(s['chunk'])} | {s['static_reachable_cells']} | {s['reachable_resource_opportunities']} | {s['actors']} | {s['costs']['paired_legacy_complete_seconds']:.3f} → {s['costs']['paired_new_complete_seconds']:.3f} |" for s in ordinary['scenes'])
    plans='\n'.join(f"| {r['seed']} | `{r['plan_identity']}` |" for r in run['runs'])
    boundary_rows=[]
    for axis in ('x','y'):
        means={mode:sum(r['seconds'] for r in boundary['rows'] if r['axis']==axis and r['mode']==mode)/2 for mode in ('legacy','new')}
        boundary_rows.append(f"| {axis.upper()} | {means['legacy']:.3f} | {means['new']:.3f} |")
    boundary_table='\n'.join(boundary_rows)
    final_state=expedition['final'];runtime=index['runtime']
    text=f'''# G10 — Wilderness character and playable exploration

Completed 24 October 2026, America/Edmonton. Work stayed in production `main`.
Reviewed starting source: `f9fe901417b360bc1fda84835e0a793eaac2f6df`.
Final frozen runtime/test/authoring inputs: `{release['frozen_head']}`.
The verified delivery checkpoint is `checkpoint/worldgen-g10-verified-20261024-a`;
its published commit is established by the delivery's external publication receipt.

G10 is complete: all eight existing wilderness biomes use coherent world-coordinate
terrain, existing campaigns retain their explicit terrain route, the preview and
installation/recovery workflow is demonstrated, and an ordinary live expedition
survives save and restoration. See the [tuning/preview guide](../../roguelike/docs/WILDERNESS_TERRAIN.md)
and [seven-criterion evidence index](../../evidence/worldgen-g10/artifact-index.json).

## Visible result and playable access

The [eight-biome comparison](../../evidence/worldgen-g10/final-b/all-biomes-comparison.png)
and [four multi-chunk views](../../evidence/worldgen-g10/final-b/multi-chunk-comparison.png)
use the actual populated production renderer with explicitly revealed visibility.
Forest trees form stands with exterior clearings; plains retain open travel with
broad vegetation patches; heath combines open ground and gravel/outcrops. Swamp
pools and Drowned Wood inundation form coherent wet areas with firmer routes.
Mountains use joined rock masses and mineral gaps. VUKH retains its identity and
saved metadata. Existing coarse biome edges and rectangular river geometry remain
visible in places; this work does not redesign macro geography.

The ordinary Ash Wastes sample `(72,103)` changes from 3,368 grass/tall-grass cells
to 219, all confined to deliberate edge transitions. Gravel, ash, rock and flint
dominate. The tested interior has no living trees or harvestable flowers/mushrooms.
Existing sprites and terrain mechanics supply the palette; no new art or lore was
introduced. The [image review](../../evidence/worldgen-g10/final-b/image-review.json)
binds these bounded visual judgments to the exact PNG bytes.

| Ordinary seed-20261023 scene | Static reachable cells | Reachable resource cells | Native actors | Paired complete scene seconds, G9 route → G10 |
|---|---:|---:|---:|---:|
{rows}

Resource numbers are cell opportunities, not independent supply stocks: many wet
cells belong to the same drinkable pool. Barren interiors intentionally lack living
resources. Native profiles, survival rates, loot, weather and interactions retain
their existing rules. Required roads, crossings, commons, yards, paths, entrances,
containers and authored targets pass the completed populated-scene checks.

Two observed issues were corrected. New-policy waystones avoid gatherable ground,
so their first interaction is unambiguous. Natural default arrivals select the
largest component touching a boundary instead of a small gap inside a tree mass.
The forest `(73,100)` now has 711 reachable cells and 36 resource opportunities at
its default anchor. This selection changes no terrain cells; decorative pockets
remain. The failed waystone attempt and superseded `final-a` audit are retained.

## Geography, continuity and saved contracts

All three complete format-7 G9 plans and all coarse world/owner records agree with
the genuine pre-edit captures. Planning still materializes zero local scenes.

| Ordinary seed | Unchanged complete G9 plan identity |
|---|---|
{plans}

Only two separately validated world-header fields are added: `surface_schema` and
`surface_policy`. The compact policy is {ordinary['policy_bytes']:,} JSON bytes and
owns the algorithm, eight profiles, seed domain and terrain/decor dependencies.
The plan format, geometry, selection and ownership records remain unchanged.
`GENERATION_REVISION` and ordinary population/entrance/underground seed domains
remain `wg9`; terrain uses `resonance-wilderness-1` separately.

Same-coordinate natural-field/base-decision crops agree across both seams and a
four-chunk corner, in independent orders and fresh processes with different Python
hash seeds. Single production scenes read nine coarse metadata chunks; the sampler
never materializes neighbors or allocates world-sized tile fields. Town/capital
exclusion uses original ownership, before the copied town base becomes plains.

The genuine G9 checkpoint was captured before runtime edits, with a real waystone
mutation and exact visited/pending fingerprints. Its pending results reproduce
under the historical route. Inherited historical fixtures pass. Saved new policies
ignore installed tuning edits/removal; missing, malformed, unsupported and forged
contracts reject before state installation. Missing required terrain and injected
post-population failures preserve player/world, scene cache, RNG, files and HEAD,
then recover when the problem is removed.

## Ordinary live expedition

The [actual outing](../../evidence/worldgen-g10/final-b/g10/expedition/expedition.json)
uses ordinary seed 20261023 and the normal lab start. The script equips the shipped
blade/jacket through inventory handlers, ascends, uses the starting waystone,
harvests a sulphur-cap fragment, leaves the road and follows natural gaps through
four adjacent chunks before rejoining the road and returning to the waystone.
All four natural crossings retain their exact opposing-edge coordinate, covering
both axes. It deliberately takes a longer eastward route around nearby threats.

The final run used {expedition['movement_inputs']} movement inputs and {expedition['turns']}
turns. Health stayed 60/60; hunger ended at {final_state['hunger']:.3f} and thirst at
{final_state['thirst']:.6f}. The starting water flask was consumed through the
inventory handler, leaving an empty skin; the acquired fragment remains in inventory.
Bog Wraith, Briar Lurker, Drowned Revenant and Hollow Knight appeared in normal
visibility and were avoided. Native AI, survival, normal FOV and weather stayed
active, invincibility stayed off, and no supplies, positioning or health restoration
were injected. Gameplay RNG uses the unchanged normal-start seed. The itinerary
uses full-state scripted path selection and does not test unaided discovery.

Normal-FOV captures are retained separately from the revealed comparisons. F5 saved
the actual explored and modified checkpoint. New-engine load and F9 match visited
terrain, harvested state, actors and supplies. The additional
[fresh-process normal-startup read](../../evidence/worldgen-g10/final-b/cold-expedition.json)
matches the complete saved player/transport/RNG record, every explored surface and a
subsequent pending scene. The disclosed post-outing wait/F9 reconstruction check
occurs after the final outing measurements. This one success does not establish
whole-world fun or survival balance.

## Costs, owner workflow and final verification

The table above gives serial same-machine legacy/new-policy complete-scene pairs;
the diagnostic also retains genuine pre-edit timings and separate base/field costs.
The field sample takes approximately 6–13 ms in these scenes. Some complete scenes
are slower than the G9 route; the bounded sample remains below 0.4 seconds. Work
depends on the requested rectangle and fixed halo, not previously explored count.
The ordinary cold-boundary maximum is {max(r['seconds'] for r in expedition['boundaries']):.3f}
seconds, including the actual handler and gameplay work.

The additional [boundary pairs](../../evidence/worldgen-g10/final-b/boundary-costs.json)
use the current supported G9 route and G10 on identical genuine pre-edit coarse
metadata, two repetitions per axis. They are controlled real-handler timings with
fixture positioning and paused AI/survival, explicitly separate from ordinary play
and from genuine pre-edit execution:

| Axis | Mean current G9 route seconds | Mean G10 seconds |
|---|---:|---:|
{boundary_table}

The safe preview produces identical policy, terrain, native IDs and PNG bytes from
a draft and its deliberate installation in a disposable data catalog. Backup
recovery restores the installed identity. Draft/installed-file aliases, hard links,
report/image collisions and a Windows junction are rejected. Symbolic-link creation
was unavailable on this Windows account; the junction exercised directory alias
resolution. The complete editable example and guide are shipped. The refreshed
derived catalog passes its check with the existing 64 assets and diagnostics.

Final gates, all on the frozen inputs above:

- Catalog validation and bounded G10 verification: pass, including nine targeted tests.
- Expanded unfiltered focused suite: {tests} tests pass.
- Unfiltered production D gate: {totals['passed']:,}/{totals['checks']:,} checks pass across {totals['workers']} workers.
- Independent actual-checkpoint fresh-process read and paired boundary probe: pass.

The existing `E04 / UI-TEXT-HEIGHT` deferral remains recorded in the production
result. `final-a` was superseded after the arrival audit while its focused run was
in progress; its production gate had not started. Only
[final-b](../../evidence/worldgen-g10/final-b/release.json) supplies the final gates.
The first production launch rejected the new evidence root at its disposable-save
guard. It is retained under `superseded_checks`; the successful unfiltered run uses
the existing allowed `.baseline` root and copies reports into final-b. Runtime and
test inputs stayed unchanged, so the 238-test focused result remains applicable.

The environment reuses the established dependency interpreter: {runtime['python'].splitlines()[0]},
pygame {runtime['libraries']['pygame']}, tcod {runtime['libraries']['tcod']}, numpy
{runtime['libraries']['numpy']}. Game code imports from this production checkout.
All {index['source_files']} frozen inputs reconcile to Git with exact raw hashes or
the recorded uniform newline-only rule. Exact commands, logs and output identities
are retained. Disposable worker save roots are excluded and individually inventoried;
the genuine compatibility fixture and actual explored checkpoint remain included.

## Documentation policy and delivery

The commissioned brief explicitly replaces automatic wiki upkeep in `AGENTS.md`
with separately commissioned targeted wiki work. The existing wiki edition is
intact; no chapters, examples, HTML build or wiki release gate were changed/run.
This feature has its own authoritative guide, editable example and source-bound
completion evidence. Further roads, climate, balance, POIs and G11 remain separate
decisions.

Scoped commits and immutable starting/terrain/verified checkpoints preserve the
reviewed G9 source. The portable delivery includes the original brief/review,
genuine fixture, production images, raw receipts, source patch and per-member
size/SHA-256/CRC32 manifest. `publication.json` in that ZIP and its adjacent external
archive receipt establish exact remote main/tag readback and final archive identity
without a self-referential committed hash.
'''
    (ROOT/'docs/owner/WORLDGEN_G10.md').write_text(text,encoding='utf-8')


if __name__=='__main__':main()
