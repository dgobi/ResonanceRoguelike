"""One ordinary saved-input plan, optionally one verified selected scene.

No candidate injection, narrowed pools, seed search or generation-setting override.
Inspection deterministically replays the exact verified inputs and plan identity.
"""
import hashlib
import random
import time
from collections import Counter
from generation.context import GenerationError
from generation.placement import digest, entrance_cells, frontage_entrance, transform

MAX_ROWS = 200


def input_binding(root, seed):
    files = {}
    for path in sorted((root / 'roguelike/data').rglob('*.json')):
        files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((root / 'roguelike').rglob('*.py')):
        if {'saves', '__pycache__'} & set(path.relative_to(root / 'roguelike').parts): continue
        files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest(dict(seed=seed, files=files)), files


def preview(root, raw, inputs):
    from engine.selection_authoring import PROFILE, saved_buildings, authoring_validate
    from engine.data_loader import DataLoader
    from generation.settlement_selection import resolve
    from generation.world_gen import generate_world
    from generation.world_plan import address
    from generation.structure_preview import snapshot, receipt_json, receipt_owned, check_access
    from engine.scene_generation import create_surface
    from engine.item_factory import ItemFactory
    from engine.creature_factory import CreatureFactory
    from world.world_map import WorldMap
    allowed = {'seed', 'placement_id', 'plan_identity', 'input_identity'}
    if not isinstance(inputs, dict) or set(inputs) - allowed or type(inputs.get('seed')) is not int or not 0 <= inputs['seed'] <= 2147483647:
        raise GenerationError('Use one explicit integer seed from 0 to 2147483647.')
    inspecting = set(inputs) != {'seed'}
    if inspecting and (set(inputs) != allowed or any(not isinstance(inputs[k], str) or not inputs[k] for k in allowed-{'seed'})):
        raise GenerationError('Placement inspection requires the complete saved-input and plan identity, plus placement identity.')
    saved = (root / PROFILE).read_bytes()
    if saved.decode('utf-8').startswith('\ufeff') or __import__('json').loads(saved.decode('utf-8')) != raw:
        raise GenerationError('Preview uses exact saved selection only. Apply and byte-check reopen first.')
    seed = inputs['seed']; binding, files = input_binding(root, seed)
    if inspecting and inputs['input_identity'] != binding:
        raise GenerationError('Stale saved inputs: sample the saved policy/dependencies again before inspecting a placement.')
    data = DataLoader(str(root / 'roguelike/data'))
    errors = authoring_validate(data.settlement_profiles, data, PROFILE, data.root)
    if errors: raise GenerationError('Invalid saved selection: '+'; '.join(d['field']+': '+d['message'] for d in errors))
    resolved = resolve(data)
    world = WorldMap(128, 128); world.seed = seed; started = time.perf_counter()
    generate_world(world, data, random.Random(seed))
    plan = world.plan
    if not plan or plan.get('selection') != resolved:
        raise GenerationError('Ordinary plan did not capture selection resolved from these freshly loaded saved inputs.')
    plan_identity = digest(plan)
    if inspecting and inputs['plan_identity'] != plan_identity:
        raise GenerationError('Stale plan: placement inspection refused because deterministic replay differs.')
    profiles = {s['id']: s['form'] for s in plan['settlements']}
    profiles['landmark'] = 'landmark'
    owners = {plot['placement']: plot['owner'] for plot in plan['plots'] if plot['owner'] in profiles and plot['placement']}
    selected = [dict(p, owner=owners[p['id']]) for p in plan['placements'] if p['id'] in owners]
    catalogue = saved_buildings(data, data.root); sources = {b['id']: b for b in catalogue}
    rows = []
    for p in selected[:MAX_ROWS]:
        chunk = address(*p['origin'])[:2]
        rows.append({**p, 'profile': profiles[p['owner']], 'path': sources[p['asset']]['path'], 'chunk': list(chunk),
                     'frontage': frontage_entrance(p),
                     'entrance_cells': [dict(id=e['id'], cells=[list(xy) for xy in entrance_cells(e)]) for e in p['entrances']]})
    counts = Counter((profiles[p['owner']], p['role'], p['asset']) for p in selected)
    summary = []
    for profile, policy in resolved['profiles'].items():
        for role, rules in policy['roles'].items():
            for rule in rules:
                summary.append(dict(profile=profile, role=role, **rule, selected=counts[profile, role, rule['asset']],
                                    path=sources[rule['asset']]['path'], eligible=True))
    scene = None
    if inspecting:
        matches = [p for p in selected if p['id'] == inputs['placement_id']]
        if len(matches) != 1: raise GenerationError('Placement is not uniquely present in this verified ordinary plan consumer.')
        p = matches[0]; chunk = address(*p['origin'])[:2]
        result = create_surface(world, world.get(*chunk), data, ItemFactory(data), CreatureFactory(data), 80, 43)
        receipts = [r for r in result.receipts if r['record_id'].startswith(p['id']+':')]
        oriented = transform(data.structures[p['asset']], p['rotation'], p['mirror'])
        direct = oriented.get('special_tiles', [])
        if len(receipts) != len(direct) or not all(receipt_owned(r, result.local_map) for r in receipts):
            raise GenerationError(p['id']+': selected placement production receipts/ownership are incomplete.')
        records = []
        for index, (receipt, native) in enumerate(zip(receipts, data.structures[p['asset']].get('special_tiles', []))):
            row = receipt_json(receipt)
            row.update(native_xy=[native['x'], native['y']], declared_kind=native.get('type', native.get('kind')),
                       transformed_xy=[direct[index]['x'],direct[index]['y']],
                       declared_item_id=native.get('item_id'), declared_text_id=native.get('text_id'), receipt_owned=True)
            records.append(row)
        x0, y0 = chunk[0]*80, chunk[1]*43
        front = frontage_entrance(p); dx, dy = __import__('generation.placement', fromlist=['NORMALS']).NORMALS[front['normal']]
        entry = dict(x=front['x']-x0+dx, y=front['y']-y0+dy)
        targets = [dict(x=x-x0, y=y-y0, kind='floor', name=f'entrance {e["id"]} span[{n}]')
                   for e in p['entrances'] if e['required'] for n, (x, y) in enumerate(entrance_cells(e))]
        access = check_access(result.local_map, data, dict(coordinates='map', entry=entry, targets=targets))
        if not all(a['passed'] for a in access): raise GenerationError(p['id']+': constructed full entrance span failed static access.')
        scene = dict(snapshot(result.local_map, result.actors, data), width=80, height=43, chunk=list(chunk),
                     legend={k:dict(walkable=bool(v.get('walkable',True)),transparent=bool(v.get('transparent',True))) for k,v in data.terrain.items()},
                     placement=p, records=records, access=access, passed=True,
                     scene_address=list(result.local_map.generation_context.address), scene_seed=str(result.local_map.generation_context.scene_seed),
                     note='Entire chunk shown; only records below are attributed to this selected placement. Revealed static scene; no player interaction claim.')
    after, _ = input_binding(root, seed)
    if after != binding: raise GenerationError('Saved inputs changed during ordinary generation/construction; output discarded.')
    diagnostics = plan.get('diagnostics', [])
    recorded = [d for d in diagnostics if d.get('kind') == 'required-role-search']
    return dict(kind='selection-preview', seed=seed, inputs=inputs, width=128, height=128, plan_mode=world.plan_mode,
                generation_revision=world.generation_revision, profile_path=PROFILE, profile_sha256=hashlib.sha256(saved).hexdigest(),
                input_identity=binding, input_files=files, plan_identity=plan_identity, captured_selection=plan['selection'],
                resolved_selection_sha256=digest(resolved), selection_matches_saved_resolve=True,
                selected_count=len(selected), shown_count=len(rows), truncated=len(selected)-len(rows), rows=rows, summary=summary,
                recorded_searches=recorded[:24], recorded_search_count=len(recorded), scene=scene,
                planning_seconds=time.perf_counter()-started,
                setup='Ordinary 128 × 128 world_gen.generate_world with normal saved generation configuration. Full plan generated before filtering. No candidate/policy injection or parked draft overlay.',
                dependencies='Exact saved data and game-code identities in input_files; no campaigns read.',
                consumer='world_gen.generate_world → settlement_selection.resolve → world_plan → create_surface',
                limitations='Eligibility, selection and one materialized placement are distinct. No selected instance is a valid result. Absence alone records no fit/cap rejection cause. Existing saved plans are unchanged.')
