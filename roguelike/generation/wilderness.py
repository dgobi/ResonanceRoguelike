"""Versioned, bounded world-coordinate wilderness fields.

This domain deliberately does not replace GenerationContext: plants, natives,
structures, entrances and underground generation retain their G9 purpose seeds.
Only saved coarse metadata in a one-chunk halo is read. No scenes are requested.
"""
from __future__ import annotations
import copy
import math
import numpy as np
from config import MAP_WIDTH as W, MAP_HEIGHT as H
from generation.context import GenerationError, stable_seed
from generation.placement import digest

BIOMES = ('forest', 'plains', 'heath', 'swamp', 'drowned_wood',
          'ash_wastes', 'mountain', 'deep_mountain')
ALGORITHM = 'wilderness-fields-v1'
DOMAIN = 'resonance-wilderness-1'
SCHEMA = 1
NATURAL = {'grass', 'varied_grass', 'tall_grass', 'mud', 'packed_earth',
           'gravel', 'ash', 'shallow_water', 'tree', 'rock'}


def _keys(value, expected, where):
    if not isinstance(value, dict) or set(value) != set(expected):
        actual = set(value) if isinstance(value, dict) else set()
        raise GenerationError(f'{where}: expected fields {sorted(expected)}; '
                              f'unknown {sorted(actual-set(expected))}, missing {sorted(set(expected)-actual)}')


def _number(value, low, high, where):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise GenerationError(f'{where}: expected finite number {low}..{high}')


def validate_profiles(raw, data):
    _keys(raw, ('version', 'profiles'), 'wilderness profiles')
    if type(raw['version']) is not int or raw['version'] != 1:
        raise GenerationError('wilderness profiles: unsupported version')
    _keys(raw['profiles'], BIOMES, 'wilderness profiles.profiles')
    for biome, p in raw['profiles'].items():
        label = 'wilderness '+biome
        _keys(p, ('palette', 'scale', 'cover', 'patch_amount', 'wet_amount', 'transition'), label)
        _keys(p['palette'], ('ground', 'patch', 'obstacle'), label+'.palette')
        for role, tid in p['palette'].items():
            if not isinstance(tid, str) or tid not in NATURAL or tid not in data.terrain:
                raise GenerationError(f'{label}.{role}: unavailable/unsupported natural terrain {tid!r}')
            td = data.terrain[tid]
            if role == 'obstacle':
                if tid not in ('tree', 'rock') or td.get('walkable', True):
                    raise GenerationError(f'{label}.obstacle: requires blocking tree or rock')
            elif not td.get('walkable', False) or not td.get('transparent', False):
                raise GenerationError(f'{label}.{role}: requires walkable transparent natural ground')
        _number(p['scale'], 8, 96, label+'.scale')
        _number(p['cover'], 0, .68, label+'.cover')
        _number(p['patch_amount'], 0, 1, label+'.patch_amount')
        _number(p['wet_amount'], 0, .6, label+'.wet_amount')
        _number(p['transition'], 0, 12, label+'.transition')
        if p['wet_amount'] and ('shallow_water' not in data.terrain or
                                not data.terrain['shallow_water'].get('walkable')):
            raise GenerationError(label+': unavailable walkable shallow_water')
        if p['palette']['ground'] == p['palette']['patch']:
            raise GenerationError(label+': identical ground/patch makes patch_amount ineffective')
        if biome == 'ash_wastes' and (p['wet_amount'] or p['palette']['obstacle'] != 'rock' or
                                     any(p['palette'][r] not in ('gravel', 'ash', 'packed_earth') for r in ('ground','patch'))):
            raise GenerationError(label+': barren interior requires mineral ground, rock and no wet/living cover')
    if any('varied_grass' in p['palette'].values() for p in raw['profiles'].values()):
        from rendering.decor import FUNCTIONAL_VARIANTS
        for tid, _ in FUNCTIONAL_VARIANTS['varied_grass']:
            if tid != 'grass' and tid not in data.decoratives:
                raise GenerationError('wilderness: unavailable plant decor '+tid)
    return copy.deepcopy(raw)


def _dependencies(profiles, data):
    names = {tid for p in profiles['profiles'].values() for tid in p['palette'].values()}
    names.add('grass')  # varied_grass resolves to real grass and plant decor
    if any(p['wet_amount'] for p in profiles['profiles'].values()):
        names.add('shallow_water')
    refs = {'terrain:'+tid: digest(data.terrain[tid]) for tid in sorted(names)}
    if 'varied_grass' in names:
        from rendering.decor import FUNCTIONAL_VARIANTS
        refs.update({'decor:'+tid: digest(data.decoratives[tid])
                     for tid, _ in FUNCTIONAL_VARIANTS['varied_grass'] if tid != 'grass'})
    return refs


def make_policy(raw, data, *, access_revision=1):
    profiles = validate_profiles(raw, data)
    p = dict(version=1, algorithm=ALGORITHM, seed_domain=DOMAIN, profiles=profiles,
             dependencies=_dependencies(profiles, data))
    if type(access_revision) is not int or access_revision not in (0, 1):
        raise GenerationError('surface policy: unsupported access revision')
    if access_revision:
        p.update(version=2, access_revision=access_revision)
    return dict(p, identity=digest(p))


def validate_policy(policy, data=None):
    version = policy.get('version') if isinstance(policy, dict) else None
    keys = ('version','algorithm','seed_domain','profiles','dependencies','identity')
    _keys(policy, keys + (('access_revision',) if version == 2 else ()), 'surface policy')
    if type(version) is not int or version not in (1, 2) or policy['algorithm'] != ALGORITHM or policy['seed_domain'] != DOMAIN:
        raise GenerationError('surface policy: unsupported algorithm, version or seed domain')
    if version == 2 and (type(policy['access_revision']) is not int or policy['access_revision'] != 1):
        raise GenerationError('surface policy: unsupported access revision')
    if policy['identity'] != digest({k:v for k,v in policy.items() if k != 'identity'}):
        raise GenerationError('surface policy: forged identity')
    if data is not None:
        profiles = validate_profiles(policy['profiles'], data)
        if policy['dependencies'] != _dependencies(profiles, data):
            raise GenerationError('surface policy: required terrain/decor dependencies changed; restore compatible definitions')
    return policy


def world_policy(world, data=None):
    schema = getattr(world, 'surface_schema', 0)
    policy = getattr(world, 'surface_policy', None)
    if type(schema) is not int or schema not in (0, SCHEMA):
        raise GenerationError('unsupported surface schema')
    if schema == 0:
        if policy is not None:
            raise GenerationError('historical surface schema cannot carry a new surface policy')
        return None
    return validate_policy(policy, data)


def provenance(world, chunk):
    p = world_policy(world)
    if p is None:
        return None
    result = dict(version=1, policy_identity=p['identity'], algorithm=ALGORITHM,
                seed_domain=DOMAIN, owner='wilderness' if eligible(chunk) else 'urban-g9',
                biome=chunk.biome_id)
    if p['version'] == 2:
        result['access_revision'] = p['access_revision']
    return result


def eligible(chunk):
    # Original ownership, never planned_scene's copied PLAINS town base.
    from world.world_map import RegionType
    return chunk.region_type not in (RegionType.TOWN, RegionType.CAPITAL) and chunk.biome_id in BIOMES


def _hash(x, y, seed):
    """Unsigned integer lattice mixer, independent of Python hash/RNG state."""
    with np.errstate(over='ignore'):
        v = np.asarray(x, dtype=np.uint64)*np.uint64(0x9E3779B185EBCA87)
        v = v ^ (np.asarray(y, dtype=np.uint64)*np.uint64(0xC2B2AE3D27D4EB4F)) ^ np.uint64(seed)
        v = (v ^ (v >> np.uint64(30)))*np.uint64(0xBF58476D1CE4E5B9)
        v = (v ^ (v >> np.uint64(27)))*np.uint64(0x94D049BB133111EB)
        return ((v ^ (v >> np.uint64(31))) >> np.uint64(11)).astype(np.float64) / 9007199254740992.


def _field(x, y, scale, seed):
    xx, yy = x/scale, y/scale
    ix, iy = np.floor(xx).astype(np.int64), np.floor(yy).astype(np.int64)
    fx, fy = xx-ix, yy-iy
    fx, fy = fx*fx*(3-2*fx), fy*fy*(3-2*fy)
    a = _hash(ix,iy,seed)*(1-fx) + _hash(ix+1,iy,seed)*fx
    b = _hash(ix,iy+1,seed)*(1-fx) + _hash(ix+1,iy+1,seed)*fx
    return a*(1-fy) + b*fy


def sample(world, policy, x0, y0, width=W, height=H):
    """Return natural fields and base decisions for a bounded absolute rectangle.

    Crop equality applies before set_tile's existing functional plant resolution,
    infrastructure, authored sites, entrances, dressing and population.
    """
    if any(type(v) is not int for v in (x0,y0,width,height)) or not 1 <= width <= 3*W or not 1 <= height <= 3*H:
        raise GenerationError('wilderness sample: integer rectangle limited to 3x3 chunks')
    profiles = policy['profiles']['profiles']
    x = np.arange(x0,x0+width,dtype=np.int64)[:,None]
    y = np.arange(y0,y0+height,dtype=np.int64)[None,:]
    seed = stable_seed(DOMAIN, world.seed) & ((1<<64)-1)
    weights = {b:np.zeros((width,height)) for b in BIOMES}
    moisture = np.zeros((width,height)); elevation = np.zeros((width,height))
    total = np.zeros((width,height)); reads = 0
    # One metadata halo, including diagonals; no world iteration or scene call.
    for cx in range(x0//W-1,(x0+width-1)//W+2):
        for cy in range(y0//H-1,(y0+height-1)//H+2):
            ch = world.get(cx,cy)
            reads += 1
            if ch is None:
                continue
            biome = ch.biome_id if eligible(ch) else 'plains'
            blend = profiles[biome]['transition']
            if blend:
                wx = np.clip(np.minimum(x-cx*W+blend, (cx+1)*W+blend-x)/(2*blend),0,1)
                wy = np.clip(np.minimum(y-cy*H+blend, (cy+1)*H+blend-y)/(2*blend),0,1)
                weight = wx*wy
            else:
                weight = ((x>=cx*W)&(x<(cx+1)*W))*((y>=cy*H)&(y<(cy+1)*H))
            weights[biome] += weight
            moisture += weight*ch.moisture
            elevation += weight*ch.elevation
            total += weight
    if np.any(total == 0):
        raise GenerationError('wilderness sample: outside saved geography')
    moisture /= total; elevation /= total
    # Smooth selector composes transitions in a shared world-coordinate band.
    selector = _field(x,y,7,seed ^ 101)
    cumulative = np.zeros((width,height)); chosen = np.full((width,height),'',dtype='U16')
    for biome in BIOMES:
        cumulative += weights[biome]/total
        use = (chosen=='') & (selector <= cumulative)
        chosen[use] = biome
    terrain = np.full((width,height),'',dtype='U32')
    cover = np.zeros((width,height)); patch = np.zeros((width,height)); wet = np.zeros((width,height))
    placement = _hash(x,y,seed ^ 401)
    for biome in BIOMES:
        mask = chosen == biome
        if not np.any(mask):
            continue
        p = profiles[biome]; scale = p['scale']
        broad = _field(x,y,scale,seed ^ 503)
        fine = _field(x,y,scale/3,seed ^ 607)
        c = .78*broad+.22*fine
        q = _field(x,y,scale*.73,seed ^ 709)
        water = _field(x,y,scale*.85,seed ^ 809)
        cover[mask]=c[mask]; patch[mask]=q[mask]; wet[mask]=water[mask]
        terrain[mask] = p['palette']['ground']
        terrain[mask & (q > 1-p['patch_amount'])] = p['palette']['patch']
        amount = p['wet_amount']
        if amount:
            # Saved moisture shapes wet margins without changing coarse geography.
            threshold = 1-np.clip(amount+(moisture-.5)*.08,0,.65)
            terrain[mask & (water>threshold)] = 'shallow_water'
        # Individual gaps keep broad stands legible without independent cover draws.
        obstacle = mask & (c > 1-p['cover']) & (placement < (.83 if p['palette']['obstacle']=='tree' else .96))
        # Wet woods retain inundation between trees; pools never become solid rock.
        if p['palette']['obstacle']=='rock':
            obstacle &= terrain != 'shallow_water'
        terrain[obstacle] = p['palette']['obstacle']
    return dict(terrain=terrain, biome=chosen, cover=cover, patch=patch, wet=wet,
                moisture=moisture, elevation=elevation, metadata_reads=reads)


def materialize(world, chunk, data, context, width=W, height=H):
    from world.local_map import LocalMap
    from generation.access import enterable
    from collections import deque
    import time
    policy = world_policy(world, data)
    if policy is None or not eligible(chunk):
        raise GenerationError('wilderness materialization requires a new-policy wilderness owner')
    start = time.perf_counter()
    natural = sample(world, policy, W*chunk.wx, H*chunk.wy, width, height)
    sampled = time.perf_counter()
    m = LocalMap(width,height,generation_context=context)
    for x in range(width):
        for y in range(height):
            tid = str(natural['terrain'][x,y]); td = data.terrain[tid]
            m.set_tile(x,y,tid,td['walkable'],td['transparent'])
    # A natural field must not manufacture a centre clearing. Choose an actual
    # exterior component instead: a lone gap among trees is not a useful arrival
    # or a valid anchor for a pending wilderness entrance.
    seen=set();components=[]
    for x in range(width):
        for y in range(height):
            if (x,y) in seen or not enterable(m,(x,y),data):continue
            component={(x,y)};seen.add((x,y));todo=deque([(x,y)])
            while todo:
                a,b=todo.popleft()
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        q=a+dx,b+dy
                        if q not in seen and enterable(m,q,data):
                            seen.add(q);component.add(q);todo.append(q)
            components.append(component)
    outside=[c for c in components if any(x in (0,width-1) or y in (0,height-1) for x,y in c)]
    if not outside:
        raise GenerationError('wilderness: no natural boundary arrival component')
    def anchor(c):return min(c,key=lambda p:(max(abs(p[0]-width//2),abs(p[1]-height//2)),p))
    component=min(outside,key=lambda c:(-len(c),anchor(c)))
    spawn=anchor(component)
    m.surface_provenance = provenance(world,chunk)
    m.wilderness_generation = dict(policy_identity=policy['identity'],halo_chunks=1,
        metadata_reads=natural['metadata_reads'],base_decision_identity=digest(natural['terrain'].tolist()),
        repairs=[],arrival_policy='largest-natural-boundary-component-v1',arrival_component_cells=len(component),
        field_seconds=sampled-start,base_seconds=time.perf_counter()-start)
    return m, spawn
