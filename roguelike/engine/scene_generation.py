"""Complete native scene construction, staged before cache/metadata publication."""
from __future__ import annotations
import copy
from dataclasses import dataclass, field

from generation.context import GenerationContext, GenerationError, GENERATION_REVISION, map_context
from generation.spawn_specs import resolve_special


def populate(data, item_factory, creature_factory, local_map, specs, *, map_text=False, receipts=None, authored_arrival=None):
    """Validate/materialize all content before mutating the candidate's object layers."""
    from generation.floor_object_utils import place_floor_object, place_container
    from engine.loot_roller import roll_pools
    context = map_context(local_map)
    plans, actors, deferred, observations = [], [], [], []
    containers = set(local_map.container_state)
    from generation.structure_contract import Validator, StructureError
    route = 'authored_submap' if authored_arrival is not None else None
    validation = Validator(data, '<scene population>', str(context.address), route)
    for index, raw in enumerate(specs):
        if route or not isinstance(raw, dict) or raw.get('kind', raw.get('type')) != 'creature':
            source = raw.get('source', f'spawns[{index}]') if isinstance(raw, dict) else f'spawns[{index}]'
            validation.special(raw, source, local_map.width, local_map.height)
    if any(d.severity == 'error' for d in validation.diagnostics):
        raise StructureError(validation.diagnostics)

    resolved = []
    for index, raw in enumerate(specs):
        source = raw.get('source', f'scene {context.address} spawn[{index}]')
        spec = (dict(raw) if not route and raw.get('kind', raw.get('type')) == 'creature'
                else resolve_special(raw, context.rng('weighted-special-adapter', index), source, route=route))
        resolved.append((source, spec))
    if route:
        decor_slots = {xy: 'existing decor' for xy in local_map.decor}
        for source, spec in resolved:
            if spec['kind'] not in ('decor', 'container'):
                continue
            xy = spec['x'], spec['y']
            if xy in decor_slots or xy in containers:
                raise GenerationError(f'{source}: decor slot {xy} conflicts with {decor_slots.get(xy, "existing container")}')
            decor_slots[xy] = source
        blocked = {xy for xy, decor in local_map.decor.items()
                   if data.decoratives.get(decor, {}).get('blocks_movement', False)}
        blocked.update((s['x'], s['y']) for _, s in resolved if s['kind'] in ('container', 'decor')
                       and data.decoratives[s.get('decor_id', 'crate')].get('blocks_movement', False))
        for source, spec in resolved:
            if spec['kind'] == 'decor' and (spec['x'], spec['y']) in blocked:
                xy = spec['x'], spec['y']
                if xy == tuple(authored_arrival) or str(local_map.tiles[xy]['terrain']) in ('stairs_up', 'stairs_down'):
                    raise GenerationError(f'{source}: blocking decor at realized {xy} invalidates actual arrival or usable return')
        occupied = set()
        for source, spec in resolved:
            if spec['kind'] != 'creature':
                continue
            xy = spec['x'], spec['y']
            terrain = str(local_map.tiles[xy]['terrain'])
            if (not local_map.walkable[xy] or xy in blocked or
                    (not data.terrain.get(terrain, {}).get('creature_passable', True)
                     and not data.entities[spec['creature_id']].get('can_swim', False))):
                raise GenerationError(f'{decor_slots.get(xy, source)}: creature at {xy} is blocked by terrain/decor or creature_passable restriction ({source})')
            if xy in occupied or xy == tuple(authored_arrival) or terrain in ('stairs_up', 'stairs_down'):
                raise GenerationError(f'{source}: creature at {xy} overlaps an actor, player arrival or physical stair')
            occupied.add(xy)

    def item(item_id, x, y, source, text_id=''):
        if text_id and map_text:
            item_id = data.text_item_map.get(text_id, 'letter')
        if item_id not in data.items:
            raise GenerationError(f'{source}: missing item {item_id!r}')
        value = item_factory.create(item_id, x, y)
        if value is None:
            raise GenerationError(f'{source}: item factory rejected {item_id!r}')
        if text_id:
            value.text_id = text_id
        return value

    for index, (source, spec) in enumerate(resolved):
        kind, x, y = spec['kind'], spec['x'], spec['y']
        observation = dict(record_id=spec.get('record_id', f'spawn[{index}]'), source=source,
                           kind=kind, source_xy=spec.get('source_xy', [x,y]), selected_branch=spec.get('selected_branch'), objects=[])
        observation.update(source_index=index, item_id=spec.get('item_id'), text_id=spec.get('text_id'),
                           text_override_present='text_id' in spec, decor_id=spec.get('decor_id'), loot_pools=spec.get('loot_pools'))
        observations.append(observation)
        if kind in ('body', 'stele'):
            deferred.append(dict(source=source, kind=kind, x=x, y=y))
            continue
        if kind == 'empty':
            continue
        if type(x) is not int or type(y) is not int:
            raise GenerationError(f'{source}: {kind} coordinates must be integers')
        valid = local_map.in_bounds(x, y) and local_map.walkable[x, y]
        # Retain the existing bounded item relocation, never apply it to scene anchors.
        if not valid and kind == 'item':
            positions = [(x + dx, y + dy) for r in range(1, 4)
                         for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                         if local_map.in_bounds(x + dx, y + dy) and local_map.walkable[x + dx, y + dy]]
            if positions:
                x, y = positions[0]
                valid = True
        if not valid:
            raise GenerationError(f'{source}: {kind} anchor ({x},{y}) is out of bounds or not walkable')
        observation['xy'] = [x,y]
        observation['relocated'] = [x,y] != [spec['x'],spec['y']]
        first_plan = len(plans)
        if kind == 'item':
            plans.append(('item', x, y, item(spec.get('item_id', ''), x, y, source, spec.get('text_id', ''))))
        elif kind == 'decor':
            from generation.authored_decor import admission
            decor = spec['decor_id']
            observation['realized_decor'] = dict(id=decor, xy=[x,y], **admission(data,decor)['properties'])
            plans.append(('decor', x, y, decor))
        elif kind == 'container':
            if (x, y) in containers:
                raise GenerationError(f'{source}: duplicate container at ({x},{y})')
            decor = spec.get('decor_id', 'crate')
            if decor not in data.decoratives:
                raise GenerationError(f'{source}: missing container decor {decor!r}')
            pool_ids = spec.get('loot_pools', [])
            if not isinstance(pool_ids, list):
                raise GenerationError(f'{source}: loot_pools must be a list')
            for pool_id in pool_ids:
                if pool_id not in data.loot_pools:
                    raise GenerationError(f'{source}: missing loot pool {pool_id!r}')
                for row in data.loot_pools[pool_id].get('items', []):
                    if row.get('item_id') not in data.items:
                        raise GenerationError(f'{source}: pool {pool_id!r} has missing item {row.get("item_id")!r}')
            contents = roll_pools(pool_ids, data.loot_pools, item_factory,
                                  context.rng('container-loot', x, y, decor))
            plans.append(('container', x, y, (decor, contents)))
            containers.add((x, y))
        elif kind == 'scene':
            scene_id = spec.get('scene_id', '')
            scene = data.scenes.get(scene_id)
            if scene is None:
                raise GenerationError(f'{source}: missing scene {scene_id!r}')
            for n, row in enumerate(scene.get('floor_objects', [])):
                plans.append(('item', x, y, item(row.get('item_id', ''), x, y,
                                                f'{source} scene {scene_id} floor_objects[{n}]')))
        elif kind == 'creature':
            creature_id = spec.get('creature_id')
            if creature_id not in data.entities:
                raise GenerationError(f'{source}: missing creature {creature_id!r}')
            actor = creature_factory.spawn(creature_id, x, y, context.rng('native-actor', x, y, creature_id))
            if actor is None:
                raise GenerationError(f'{source}: creature factory rejected {creature_id!r}')
            actors.append(actor)
            observation['actors'] = [actor]
            from generation.placement import digest
            observation['creature_definition'] = dict(id=creature_id, sha256=digest(data.entities[creature_id]))
        observation['objects'] = [p[3] for p in plans[first_plan:] if p[0] != 'decor']
    if route and any(s['kind'] == 'decor' for _, s in resolved):
        # Evaluate the complete final layers before any ownership API touches the
        # candidate. Factories have already succeeded; no scene is published yet.
        trial = copy.copy(local_map)
        trial.decor = dict(local_map.decor)
        trial.container_state = dict(local_map.container_state)
        trial.floor_objects = {xy:list(items) for xy,items in local_map.floor_objects.items()}
        apply_plans(trial, plans)
        from generation.structure_preview import direct_access
        failed = [r for r in direct_access(trial,data,observations,authored_arrival) if not r['passed']]
        if failed:
            anchors = '; '.join(f"{source} at realized ({s['x']},{s['y']})" for source,s in resolved if s['kind']=='decor')
            raise GenerationError(f'{anchors}: final furnishing/access failure: {failed}')
    # These ownership APIs are reached only after every record and factory succeeds.
    apply_plans(local_map, plans)
    if deferred:
        local_map.deferred_generation_records = deferred
    if receipts is not None:
        receipts.extend(observations)
    return actors


def apply_plans(local_map, plans):
    from generation.floor_object_utils import place_floor_object, place_container
    from generation.decor_utils import place_decor
    for kind, x, y, value in plans:
        if kind == 'item':
            place_floor_object(local_map, x, y, value)
        elif kind == 'decor':
            place_decor(local_map, x, y, value)
        else:
            place_container(local_map, x, y, *value)


@dataclass
class SceneResult:
    local_map: object
    actors: list
    spawn: tuple
    metadata: object
    receipts: list = field(default_factory=list)
    authored_start: tuple | None = None


def create_surface(world, chunk, data, item_factory, creature_factory, width, height):
    if getattr(world,'plan_mode','legacy')=='shared-v1':
        from generation.planned_scene import create_planned_surface
        return create_planned_surface(world,chunk,data,item_factory,creature_factory,width,height)
    from generation.region_gen import generate_region
    from world.world_map import RegionType
    staged = copy.deepcopy(chunk)
    context = GenerationContext(world.seed, chunk.seed, (chunk.wx, chunk.wy, None))
    local_map, spawn = generate_region(staged, width, height, data.terrain, data=data, context=context)
    if (chunk.wx, chunk.wy) == (world.start_wx, world.start_wy):
        _starting_waystone(local_map, data, *spawn)
    actors, receipts = [], []
    if staged.region_type == RegionType.TOWN and staged.town_data:
        td = staged.town_data
        specs = [dict(s, kind='creature') for s in td.creature_spawns] + td.item_spawns
        actors = populate(data, item_factory, creature_factory, local_map, specs, map_text=True, receipts=receipts)
    else:
        for index, (zone, _) in enumerate(staged.zones):
            actors.extend(creature_factory.spawn_for_zone(zone, local_map,
                          context.rng('native-population', zone, index), max_count=3))
    validate_scene(local_map, staged.submaps, data)
    local_map.generation_revision = GENERATION_REVISION
    local_map.generation_complete = True
    return SceneResult(local_map, actors, spawn, staged, receipts)


def create_submap(world, wx, wy, submap, data, item_factory, creature_factory, width, height):
    from generation.local_gen import generate_submap
    staged = copy.deepcopy(submap)
    context = GenerationContext(world.seed, submap.seed, (wx, wy, submap.submap_id))
    local_map, specs = generate_submap(staged, width, height, data.terrain, data=data, context=context)
    arrival = staged.entry_x, staged.entry_y
    if submap.layout_id:
        # Entry can be a closed door. Share the engine's actual arrival selector
        # (which does not access self), rather than reserving only player_start.
        from engine.engine import Engine
        arrival = Engine._find_walkable_near(None, local_map, *arrival)
    receipts = []
    actors = populate(data, item_factory, creature_factory, local_map, specs, receipts=receipts,
                      authored_arrival=arrival if submap.layout_id else None)
    if not local_map.in_bounds(staged.entry_x, staged.entry_y):
        raise GenerationError(f'{submap.submap_id}: invalid arrival')
    from collections import deque
    if (not local_map.in_bounds(*arrival) or not local_map.walkable[arrival]
            or not _enterable(local_map, arrival, data) or arrival in local_map.container_state
            or any((actor.x,actor.y)==arrival for actor in actors)):
        raise GenerationError(f'{submap.submap_id}: invalid actual player arrival {arrival}')
    reached, pending = {arrival}, deque([arrival])
    while pending:
        x, y = pending.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                xy = x + dx, y + dy
                if local_map.in_bounds(*xy) and xy not in reached and _enterable(local_map, xy, data):
                    reached.add(xy)
                    pending.append(xy)
    if not any(str(local_map.tiles[xy]['terrain']) == 'stairs_up' for xy in reached):
        raise GenerationError(f'{submap.submap_id}: no usable return stair from arrival')
    local_map.generation_revision = GENERATION_REVISION
    local_map.generation_complete = True
    return SceneResult(local_map, actors, arrival, staged, receipts, (staged.entry_x,staged.entry_y))


def _enterable(local_map, xy, data):
    return ((local_map.walkable[xy] or str(local_map.tiles[xy]['terrain']) == 'door_closed')
            and not data.decoratives.get(local_map.decor.get(xy), {}).get('blocks_movement', False))


def validate_scene(local_map, submaps, data):
    from generation.access import validate_required_access
    for submap in submaps:
        xy = submap.surface_x, submap.surface_y
        if (not local_map.in_bounds(*xy) or str(local_map.tiles[xy]['terrain']) != 'stairs_down'
                or local_map.submap_links.get(xy) != submap.submap_id):
            raise GenerationError(f'{submap.submap_id}: physical stair and source link disagree at {xy}')
        if not _enterable(local_map, xy, data) or not any(
                local_map.in_bounds(xy[0] + dx, xy[1] + dy)
                and _enterable(local_map, (xy[0] + dx, xy[1] + dy), data)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy):
            raise GenerationError(f'{submap.submap_id}: blocked stair or approach at {xy}')
    provenance = getattr(local_map, 'surface_provenance', {}) or {}
    if submaps or (provenance.get('access_revision') == 1 and provenance.get('owner') == 'wilderness'):
        validate_required_access(local_map, [(s.surface_x, s.surface_y) for s in submaps], data)


def publish_metadata(original, staged):
    """Preserve held SubMap identities; only commit fields generated by this candidate."""
    if hasattr(original, 'submaps'):
        original.town_data = staged.town_data
        for old, new in zip(original.submaps, staged.submaps):
            old.surface_x, old.surface_y = new.surface_x, new.surface_y
    else:
        original.entry_x, original.entry_y = staged.entry_x, staged.entry_y
        original.generated = staged.generated


def _starting_waystone(surface_map, data, start_x, start_y):
    # Place 1 waystone adjacent to road, within 8 tiles of chunk centre.
    # Guard: skip if region_gen already placed one (e.g. forest chunk on a road).
    import math as _math
    rng = surface_map.generation_context.rng("starting-waystone")
    wt_def = data.terrain.get("waystone_plinth", {})
    _existing_wt = any(
        str(surface_map.tiles[_cx, _cy]["terrain"]) == "waystone_plinth"
        for _cx in range(surface_map.width)
        for _cy in range(surface_map.height)
    )
    # Also check decor layer for waystone_plinth (post-conversion)
    if not _existing_wt:
        _existing_wt = any(
            v == "waystone_plinth"
            for v in getattr(surface_map, "decor", {}).values()
        )
    if wt_def and not _existing_wt:
        _road_terrain = {f"road_{i}" for i in range(16)}
        _cx, _cy = surface_map.width // 2, surface_map.height // 2
        # Find road tiles within 8 of centre
        _road_tiles: list[tuple[int, int]] = []
        for _rx in range(max(1, _cx - 8), min(surface_map.width - 1, _cx + 9)):
            for _ry in range(max(1, _cy - 8), min(surface_map.height - 1, _cy + 9)):
                if str(surface_map.tiles[_rx, _ry]["terrain"]) in _road_terrain:
                    _road_tiles.append((_rx, _ry))
        # Find walkable non-road tiles adjacent to road, nearest to centre
        _candidates: list[tuple[int, int, float]] = []
        for _rx, _ry in _road_tiles:
            for _dx, _dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                _ax, _ay = _rx + _dx, _ry + _dy
                if not surface_map.in_bounds(_ax, _ay):
                    continue
                if str(surface_map.tiles[_ax, _ay]["terrain"]) in _road_terrain:
                    continue
                if not surface_map.walkable[_ax, _ay] or (_ax, _ay) in surface_map.decor or (_ax, _ay) in surface_map.submap_links:
                    continue
                _d = _math.sqrt((_ax - _cx) ** 2 + (_ay - _cy) ** 2)
                _candidates.append((_ax, _ay, _d))
        if _candidates:
            from generation.decor_utils import place_decor as _pd_ws_main
            _candidates.sort(key=lambda c: c[2])
            _wx, _wy, _ = _candidates[0]
            _pd_ws_main(surface_map, _wx, _wy, "waystone_plinth")
        else:
            # Fallback: place near player start (original logic)
            _placed = 0
            _attempts = 0
            while _placed < 1 and _attempts < 50:
                _attempts += 1
                _dist  = rng.randint(3, 6)
                _angle = rng.uniform(0, 2 * _math.pi)
                _tx = int(start_x + _math.cos(_angle) * _dist)
                _ty = int(start_y + _math.sin(_angle) * _dist)
                if not surface_map.in_bounds(_tx, _ty):
                    continue
                if not surface_map.walkable[_tx, _ty] or (_tx, _ty) in surface_map.decor or (_tx, _ty) in surface_map.submap_links:
                    continue
                from generation.decor_utils import place_decor as _pd_ws_fb
                _pd_ws_fb(surface_map, _tx, _ty, "waystone_plinth")
                _placed += 1

