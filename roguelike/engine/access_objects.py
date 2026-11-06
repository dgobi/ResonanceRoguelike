"""Map-owned fastening state; no contents, general effects or autonomous clock."""
import copy
import uuid
from engine.access_profiles import validate

SCREEN_TERRAIN = 'access_screen'
FLOORS = frozenset({'floor', 'grass', 'packed_earth', 'dirt_path', 'cobblestone', 'gravel'})
STATE_FIELDS = {'version', 'identity', 'host', 'profile', 'progress', 'completed_by', 'ground', 'decor_id'}


def objects(m):
    return getattr(m, 'access_objects', {})


def at(m, xy):
    return objects(m).get(xy)


def secured(m, xy):
    """Fail closed for any modern owner, even if its associated row was lost."""
    entry = m.container_state.get(xy, {})
    row = at(m, xy)
    modern = 'access_owner' in entry or xy in getattr(m, 'access_manifest', {}).get('owners', {})
    if not modern and row is None:
        return False
    return not (isinstance(row, dict) and row.get('host') == 'container'
                and row.get('identity') == entry.get('access_owner')
                and row.get('completed_by') in ('careful','force','dissolution'))


def install(m, xy, host, profile, *, decor_id=''):
    """Called only on a preflight map or after its complete trial succeeds."""
    p = validate(profile)
    if host not in ('container','screen') or not p['host_'+host] or at(m, xy) is not None:
        raise ValueError('Access object: incompatible or occupied host.')
    if not m.in_bounds(*xy):
        raise ValueError('Access object: out of bounds.')
    ground = None
    if host == 'screen':
        tile = m.tiles[xy]
        if (str(tile['terrain']) not in FLOORS or not tile['walkable'] or not tile['transparent']
                or any(xy in getattr(m, layer, {}) for layer in
                       ('decor','container_state','floor_objects','processing_layer','submap_links','corpse_data'))):
            raise ValueError('Screen requires unoccupied ordinary floor, without decor, items, links or jobs.')
        ground = dict(terrain=str(tile['terrain']), walkable=True, transparent=True)
    else:
        entry = m.container_state.get(xy)
        if not isinstance(entry, dict) or entry.get('decor_id') != decor_id or 'access_owner' in entry:
            raise ValueError('Access object: missing or already owned container.')
    identity = uuid.uuid4().hex
    row = dict(version=1, identity=identity, host=host, profile=p,
               progress=0, completed_by=None, ground=ground, decor_id=decor_id)
    if not hasattr(m, 'access_objects'): m.access_objects = {}
    if not hasattr(m, 'access_manifest'): m.access_manifest = dict(version=1, owners={})
    m.access_objects[xy] = row
    m.access_manifest['owners'][xy] = identity
    if host == 'container':
        entry['access_owner'] = identity
    else:
        m.tiles[xy]['terrain'] = SCREEN_TERRAIN
        m.tiles[xy]['walkable'] = m.tiles[xy]['transparent'] = False
    return row


def validate_map(m):
    rows = objects(m)
    manifest = getattr(m, 'access_manifest', None)
    modern_owners = {xy: entry['access_owner'] for xy,entry in m.container_state.items() if 'access_owner' in entry}
    screens = {(int(x),int(y)) for x,y in zip(*(m.tiles['terrain'] == SCREEN_TERRAIN).nonzero())}
    if manifest is None:
        if rows or modern_owners or screens:
            raise ValueError('Access object: modern host missing its state manifest.')
        return
    if (not isinstance(manifest,dict) or set(manifest) != {'version','owners'}
            or type(manifest['version']) is not int or manifest['version'] != 1
            or not isinstance(rows,dict) or not isinstance(manifest['owners'],dict)
            or set(rows) != set(manifest['owners'])):
        raise ValueError('Access object: invalid manifest or missing durable instance.')
    identities, owned_containers, owned_screens = set(), set(), set()
    for xy,row in rows.items():
        if (not isinstance(xy,tuple) or len(xy)!=2 or any(type(n) is not int for n in xy)
                or not m.in_bounds(*xy) or not isinstance(row,dict) or set(row)!=STATE_FIELDS
                or type(row['version']) is not int or row['version']!=1):
            raise ValueError('Access object: invalid version, position or state fields.')
        identity = row['identity']
        if (not isinstance(identity,str) or len(identity)!=32 or any(c not in '0123456789abcdef' for c in identity)
                or identity in identities or manifest['owners'][xy]!=identity):
            raise ValueError('Access object: ambiguous instance ownership.')
        identities.add(identity)
        p = validate(row['profile'])
        if p != row['profile']:
            raise ValueError('Access object: captured profile must contain its effective settings.')
        host, progress, method = row['host'], row['progress'], row['completed_by']
        if (host not in ('container','screen') or not p['host_'+host]
                or type(progress) is not int or not 0 <= progress <= p['work_steps']
                or method not in (None,'careful','force','dissolution')
                or (method is not None and not p['allow_'+method])
                or (progress == p['work_steps']) != (method == 'careful')):
            raise ValueError('Access object: contradictory progress, method or host.')
        if host == 'container':
            entry = m.container_state.get(xy)
            if (not isinstance(entry,dict) or entry.get('access_owner') != identity
                    or not isinstance(row['decor_id'],str) or not row['decor_id']
                    or entry.get('decor_id') != row['decor_id'] or m.decor.get(xy) != row['decor_id']
                    or row['ground'] is not None or not isinstance(entry.get('items'),list)
                    or entry.get('state') not in ('closed','open','looted')
                    or (method is None and entry['state']!='closed')):
                raise ValueError('Access object: contradictory container owner or access state.')
            owned_containers.add(xy)
        else:
            ground = row['ground']
            if (not isinstance(ground,dict) or set(ground)!= {'terrain','walkable','transparent'}
                    or ground['terrain'] not in FLOORS or ground['walkable'] is not True
                    or ground['transparent'] is not True or row['decor_id'] != ''
                    or xy in m.container_state or xy in m.submap_links):
                raise ValueError('Access object: invalid screen ground or ownership.')
            expected = ground if method else dict(terrain=SCREEN_TERRAIN,walkable=False,transparent=False)
            if any(m.tiles[xy][key] != value for key,value in expected.items()):
                raise ValueError('Access object: screen geometry contradicts its durable state.')
            if method is None:
                if any(xy in getattr(m,layer,{}) for layer in ('decor','floor_objects','processing_layer','corpse_data')):
                    raise ValueError('Access object: intact screen overlaps another owner.')
                owned_screens.add(xy)
    if set(modern_owners) != owned_containers or screens != owned_screens:
        raise ValueError('Access object: orphan modern host.')


def complete(m, xy, row, method):
    """No factories, callbacks or item ownership changes inside this mutation."""
    if at(m,xy) is not row or row['completed_by'] is not None:
        raise ValueError('Access object changed before completion.')
    if row['host'] == 'screen':
        for key,value in row['ground'].items(): m.tiles[xy][key] = value
    row['completed_by'] = method


def trial_map(m):
    trial = copy.copy(m)
    trial.tiles = m.tiles.copy()
    trial.decor = dict(m.decor)
    trial.container_state = {xy:dict(r,items=list(r['items'])) for xy,r in m.container_state.items()}
    trial.floor_objects = {xy:list(items) for xy,items in m.floor_objects.items()}
    trial.access_objects = copy.deepcopy(objects(m))
    if hasattr(m,'access_manifest'):trial.access_manifest = copy.deepcopy(m.access_manifest)
    return trial
