"""Captured, finite flesh on physical items. No hunger or world resource index."""
from __future__ import annotations
import copy
import uuid

TAG = 'flesh'
FIELDS = ('flesh_resource_version', 'flesh_resource')


def value(owner, key, default=None):
    return owner.get(key, default) if isinstance(owner, dict) else getattr(owner, key, default)


def declared(owner):
    return any(isinstance(k, dict) and k.get('tag') == TAG for k in value(owner, 'keywords', []))


def validate_definition(raw):
    rows = [k for k in raw.get('keywords', []) if isinstance(k, dict) and k.get('tag') == TAG]
    if rows and (rows != [dict(tag=TAG, tier=1)] or type(rows[0].get('tier')) is not int or raw.get('id') == 'corpse'
                 or raw.get('on_use') not in (None, 'eat') or raw.get('vessel') is not None):
        raise ValueError('flesh: one tier-1 flesh keyword on ordinary loose edible material is required')


def capture(item, definition):
    validate_definition(definition)
    if declared(definition):
        item.flesh_resource_version = 1
        item.flesh_resource = dict(version=1, kind='portion', uid=uuid.uuid4().hex)
        validate(item)


def validate(owner):
    """True historical absence is inert; malformed modern presence rejects."""
    marker = value(owner, 'flesh_resource_version')
    payload = value(owner, 'flesh_resource')
    present = any((key in owner if isinstance(owner, dict) else hasattr(owner, key)) for key in FIELDS)
    if not present and not declared(owner):
        return None
    if type(marker) is not int or marker != 1 or not isinstance(payload, dict):
        raise ValueError('flesh: missing modern captured resource state')
    kind = payload.get('kind')
    keys = {'version', 'kind', 'uid'} | ({'source', 'recipe', 'state'} if kind == 'corpse' else set())
    if (set(payload) != keys or type(payload.get('version')) is not int or payload['version'] != 1
            or kind not in ('portion', 'corpse') or not isinstance(payload.get('uid'), str)
            or len(payload['uid']) != 32 or any(c not in '0123456789abcdef' for c in payload['uid'])):
        raise ValueError('flesh: invalid version, kind, identity or captured fields')
    count = value(owner, 'count')
    if (type(count) is not int or not 1 <= count <= 2**53 - 1
            or type(value(owner, 'stackable')) is not bool
            or not value(owner, 'stackable') and count != 1):
        raise ValueError('flesh: invalid physical count')
    if kind == 'portion':
        rows=[r for r in value(owner,'keywords',[]) if isinstance(r,dict) and r.get('tag')==TAG]
        if (not declared(owner) or value(owner, 'source_creature') is not None
                or value(owner, 'item_id') == 'corpse' or value(owner, 'on_use') not in (None, 'eat')
                or rows != [dict(tag=TAG,tier=1)] or type(rows[0]['tier']) is not int):
            raise ValueError('flesh: contradictory loose portion')
    else:
        from engine.harvesting import profile_errors
        recipe = payload['recipe']
        if (value(owner, 'item_id') != 'corpse' or count != 1 or value(owner, 'stackable')
                or not isinstance(payload['source'], str) or not payload['source']
                or payload['source'] != value(owner, 'source_creature')
                or payload['state'] not in ('intact', 'stripped') or declared(owner)
                or profile_errors(dict(butcher_yield=recipe))
                or not any(r.get('flesh') is True for t in recipe.get('tiers', []) for r in t.get('yields', []))):
            raise ValueError('flesh: contradictory corpse or invalid captured recipe')
        if (set(recipe) != {'decay_turns','tiers'}
                or any(set(t) != {'min_cutting_tier','yields'} for t in recipe['tiers'])
                or any(set(r) != {'item_id','quantity_min','quantity_max','flesh'}
                       for t in recipe['tiers'] for r in t['yields'])):
            raise ValueError('flesh: incomplete effective harvest recipe')
        timer=value(owner,'decay_timer')
        initial=recipe['decay_turns']
        if ((initial is None and timer is not None) or initial is not None
                and (type(timer) is not int or not 0<=timer<=initial)):
            raise ValueError('flesh: invalid running corpse decay timer')
    return payload


def eligible(item):
    try:
        p = validate(item)
        return bool(p and (p['kind'] == 'portion' or p['state'] == 'intact'))
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def resolve_source(data, source):
    """One supported source, never an ambiguous or ephemeral remains shortcut."""
    matches = [k for k in data.entities if k.casefold() == source.casefold()] if isinstance(source, str) else []
    sources = getattr(data, 'entity_definition_sources', None)
    paths = [p for k, rows in sources.items() if k.casefold() == source.casefold() for p in rows] if sources is not None and isinstance(source, str) else None
    if matches != [source] or paths is not None and len(paths) != 1:
        raise ValueError(f'remains: missing or ambiguous source {source!r}')
    creature = data.entities[source]
    from engine.harvesting import profile_errors, construct_output
    from engine.item_factory import ItemFactory
    errors = profile_errors(creature, lambda key: construct_output(data, ItemFactory(data), key))
    profile = creature.get('butcher_yield')
    if (creature.get('ephemeral', False) or errors or not profile
            or not any(r.get('flesh') is True for t in profile.get('tiers', []) for r in t.get('yields', []))):
        raise ValueError(f'remains: source must have a supported explicit flesh harvest recipe: {source!r}; {errors}')
    return creature


def create_corpse(data, factory, source, x, y, *, authored=False, name=None, owned=()):
    """The single native death/authored remains producer. No kill hooks here."""
    creature = resolve_source(data, source) if authored else data.entities.get(source, {})
    if creature.get('ephemeral', False):
        return None
    from engine.harvesting import decay_turns, profile_errors, construct_output
    corpse = factory.create('corpse', x, y)
    from entities.item import Item
    if not isinstance(corpse,Item) or corpse.item_id!='corpse' or any(i is corpse for i in owned):
        raise ValueError('corpse factory must return a fresh unowned corpse')
    corpse.name = f"remains of {name or creature.get('name', source)}"
    corpse.source_creature = source
    corpse.decay_timer = decay_turns(creature)
    recipe = creature.get('butcher_yield', {})
    if isinstance(recipe, dict) and any(r.get('flesh') is True for t in recipe.get('tiers', []) for r in t.get('yields', [])):
        errors = profile_errors(creature, lambda key: construct_output(data, factory, key))
        if errors:
            raise ValueError(f'corpse: invalid flesh declaration: {errors}')
        corpse.flesh_resource_version = 1
        effective = dict(decay_turns=decay_turns(creature), tiers=[dict(
            min_cutting_tier=t.get('min_cutting_tier',1), yields=[dict(
                item_id=r['item_id'], quantity_min=r.get('quantity_min',0),
                quantity_max=r.get('quantity_max',1), flesh=r.get('flesh',False))
                for r in t.get('yields',[])]) for t in recipe.get('tiers',[])])
        corpse.flesh_resource = dict(version=1, kind='corpse', uid=uuid.uuid4().hex,
                                    source=source, recipe=effective, state='intact')
        validate(corpse)
    return corpse


def claim(item, seen):
    p = validate(item)
    if p:
        if p['uid'] in seen:
            raise ValueError('flesh: duplicate physical resource identity/owner')
        seen.add(p['uid'])


def validate_map(local_map, seen=None):
    from engine.held_light import map_items
    seen = set() if seen is None else seen
    for item in map_items(local_map):
        claim(item, seen)
    for item in processing_items(getattr(local_map, 'processing_layer', {})):
        claim(item, seen)
    for xy, rows in local_map.floor_objects.items():
        for item in rows:
            if validate(item) and (not local_map.in_bounds(*xy) or (item.x, item.y) != xy):
                raise ValueError('flesh: floor address and physical coordinates disagree')


def processing_items(node):
    from entities.item import Item
    if isinstance(node, Item) or isinstance(node, dict) and 'item_id' in node and 'item_state_version' in node:
        yield node
    elif isinstance(node, dict):
        for child in node.values(): yield from processing_items(child)
    elif isinstance(node, (list, tuple)):
        for child in node: yield from processing_items(child)


def other_owners(engine):
    """Active owners only. Equipment is a reference, but still rules out exposure."""
    yield from engine.player.inventory.items
    yield from engine.player.equipment.slots.values()
    yield from engine.entities
    for entry in getattr(engine.local_map, 'container_state', {}).values():
        yield from entry.get('items', [])
    yield from processing_items(getattr(engine.local_map, 'processing_layer', {}))


def exposed(engine, item, xy=None):
    if not eligible(item):
        return False
    return floor_owned(engine,item,xy)


def floor_owned(engine,item,xy=None):
    """Exact identity and owner, also usable for a stripped harvestable corpse."""
    try:
        if not validate(item):return False
    except (ValueError,TypeError,KeyError,AttributeError):return False
    m = engine.local_map
    xy = (item.x, item.y) if xy is None else tuple(xy)
    positions = [pos for pos, rows in m.floor_objects.items() for row in rows if row is item]
    if (positions != [xy] or (item.x, item.y) != xy or not m.in_bounds(*xy)
            or any(owned is item or isinstance(value(owned,'flesh_resource'),dict)
                   and value(owned,'flesh_resource').get('uid') == item.flesh_resource['uid']
                   for owned in other_owners(engine))):
        return False
    # A duplicate narrow identity also cannot support a commitment.
    uid = item.flesh_resource['uid']
    return sum(isinstance(value(i,'flesh_resource'),dict) and value(i, 'flesh_resource').get('uid') == uid
               for rows in m.floor_objects.values() for i in rows) == 1


def contact(engine, actor, xy):
    """Legal adjacency, including blocked diagonal corners; never attack food."""
    m = engine.local_map
    if not m.in_bounds(actor.x, actor.y) or not m.in_bounds(*xy):
        return False
    dx, dy = xy[0] - actor.x, xy[1] - actor.y
    if max(abs(dx), abs(dy)) > 1:
        return False
    def walkable(x,y):return m.in_bounds(x,y) and m.walkable[x,y] and not engine._decor_blocks_movement(x,y)
    if not walkable(actor.x,actor.y):
        return False
    if dx and dy and not (walkable(actor.x+dx,actor.y) or walkable(actor.x,actor.y+dy)):
        return False
    return True


def consume(engine, actor, item, xy, commit):
    """Resource mutation and actor completion form one rollback boundary."""
    from engine.venom import fully_paralysed
    from engine.local_rivals import active,living
    from engine.effect_lifecycle import disrupted
    if (not active(engine,actor) or not living(actor)
            or fully_paralysed(actor) or disrupted(actor,engine.local_map)
            or not exposed(engine, item, xy) or not contact(engine, actor, xy)):
        return False
    from generation import floor_object_utils as floor
    old_count = item.count
    old_resource = copy.deepcopy(item.flesh_resource)
    old_state = copy.deepcopy(getattr(actor.ai, 'scavenging_state', None))
    old_floor = {pos: list(rows) for pos, rows in engine.local_map.floor_objects.items()}
    try:
        if item.flesh_resource['kind'] == 'corpse':
            item.flesh_resource['state'] = 'stripped'
        elif item.count > 1:
            item.count -= 1
        else:
            floor.remove_floor_object(engine.local_map, *xy, item)
            if any(i is item for rows in engine.local_map.floor_objects.values() for i in rows):
                raise ValueError('flesh: floor removal refused')
        commit()
    except Exception:
        item.count = old_count
        item.flesh_resource = old_resource
        actor.ai.scavenging_state = old_state
        floor.restore_floor_objects(engine.local_map, old_floor)
        return False
    return True


def place_one(engine, item, *, scene=None, address=None, position=None):
    """Transfer the real last unit, or split copied physical properties once."""
    from engine.venom import fully_paralysed
    from generation import floor_object_utils as floor
    inv, m = engine.player.inventory, engine.local_map
    xy = engine.player.x, engine.player.y
    if (fully_paralysed(engine.player) or scene is not None and scene is not m
            or address is not None and address != (engine.world_x, engine.world_y, engine.current_submap_id)
            or position is not None and position != xy or not eligible(item)
            or item.flesh_resource['kind'] != 'portion' or sum(i is item for i in inv.items) != 1
            or item.equipped or any(i is item for i in engine.player.equipment.slots.values())
            or any(i is item for rows in m.floor_objects.values() for i in rows)
            or not m.in_bounds(*xy) or not m.walkable[xy]):
        return False
    original_count, original_xy = item.count, (item.x, item.y)
    from engine.held_light import map_items
    owners = list(inv.items) + list(engine.entities) + list(map_items(m)) + list(processing_items(getattr(m,'processing_layer',{})))
    uid = item.flesh_resource['uid']
    if sum(i is item or isinstance(value(i,'flesh_resource'),dict) and value(i,'flesh_resource').get('uid')==uid for i in owners)!=1:
        return False
    portion = item if item.count == 1 else copy.deepcopy(item)
    if portion is not item:
        portion.count = 1
        portion.flesh_resource['uid'] = uuid.uuid4().hex
    old_floor = {pos: list(rows) for pos, rows in m.floor_objects.items()}
    old_inventory = list(inv.items)
    try:
        if not floor.place_floor_object(m, *xy, portion):
            raise ValueError('portion placement refused')
        if sum(i is portion for rows in m.floor_objects.values() for i in rows) != 1:
            raise ValueError('portion not published exactly once')
        if portion is item:
            if not inv.remove(item):
                raise ValueError('portion inventory owner changed')
        else:
            item.count -= 1
        if not exposed(engine, portion, xy):
            raise ValueError('portion has invalid exposed owner')
    except Exception:
        floor.restore_floor_objects(m, old_floor)
        inv.items[:] = old_inventory
        item.count = original_count
        item.x, item.y = original_xy
        return False
    return True


def description(item):
    p = validate(item)
    if p and p['kind'] == 'corpse':
        return ('The flesh has been stripped; other harvestable material may remain.' if p['state'] == 'stripped'
                else 'Fresh flesh remains on this carcass. Exposed flesh can draw scavengers.')
    return 'Exposed flesh can be eaten by scavengers.' if p else ''


def offer_place(engine,item):
    if not eligible(item) or item.flesh_resource['kind']!='portion':return False
    from engine.vessel_menu import show,paid
    scene=engine.local_map
    address=engine.world_x,engine.world_y,engine.current_submap_id
    position=engine.player.x,engine.player.y
    expected=copy.deepcopy(item.flesh_resource),item.count
    def perform():
        if (item.flesh_resource,item.count)!=expected:return False
        if not place_one(engine,item,scene=scene,address=address,position=position):return False
        from engine.palette import MSG_DEFAULT
        engine.log.add(f'You place one portion of {item.name} on the ground.',MSG_DEFAULT)
        engine.inventory_screen._flat=[]
        return True
    show(engine,f'{item.name} — place one of {item.count}; 1 turn',[
        ('Place one portion here; exposed flesh can be lost',lambda:paid(engine,perform))])
    return True
