"""Owned application settings, separate from an equipped weapon's spent contacts."""
import copy
import math

ESSENCES = ('Dissolution', 'Quickening', 'Binding', 'Severance', 'Consumption', 'Revelation')
MAX_HITS = 100


def validate(payload, owner=None):
    if (not isinstance(payload, dict) or set(payload) != {'version','essence','strength','hits'}
            or type(payload['version']) is not int or payload['version'] != 1
            or payload['essence'] not in ESSENCES
            or type(payload['strength']) not in (int,float)
            or not math.isfinite(payload['strength']) or not 0 < payload['strength'] <= 1
            or type(payload['hits']) is not int or not 1 <= payload['hits'] <= MAX_HITS):
        raise ValueError('coating dose: expected version 1, supported essence, strength (0,1], contacts 1..100')
    if owner is not None:
        use = owner.get('on_use') if isinstance(owner,dict) else getattr(owner,'on_use',None)
        if use != 'apply_to_weapon':
            raise ValueError('coating dose: inconsistent use identity')
    return payload


def defined(raw):
    rows = raw.get('temporary_essence')
    if raw.get('on_use') != 'apply_to_weapon' or not isinstance(rows,list) or len(rows) != 1:
        raise ValueError('coating dose: one ordinary apply_to_weapon effect required')
    row=rows[0]
    if not isinstance(row,dict) or set(row) != {'essence','strength','hits'}:
        raise ValueError('coating dose: unsupported effect fields')
    return copy.deepcopy(validate(dict(version=1,**row)))


def capture(item, definition):
    if hasattr(item,'coating_dose'):
        validate(item.coating_dose,item)
    elif getattr(item,'on_use',None)=='apply_to_weapon':
        item.coating_dose=defined(definition)


def prepare_map(local_map, data=None):
    from engine.held_light import map_items
    from entities.item import Item
    from engine.save_components import serialize_item, validate_item
    for item in map_items(local_map):
        if isinstance(item,dict):
            if 'coating_dose' in item: validate_item(item,'cached coating dose')
        elif isinstance(item,Item):
            if data is not None: capture(item,data.items.get(item.item_id,{}))
            if hasattr(item,'coating_dose'):validate_item(serialize_item(item),'cached coating dose')


def validate_live_owners(engine):
    """Catch live cross-owner aliases before JSON and pickle split their identity."""
    from engine.held_light import map_items
    owned=list(engine.player.inventory.items)
    cache=engine.save_manager.cache
    maps={('surface',wx,wy):c.local_map for (wx,wy),c in cache.hot.items()}
    maps.update({('submap',sid):c.local_map for sid,c in cache.submap_hot.items()})
    active=(('surface',engine.world_x,engine.world_y) if engine.current_submap_id is None
            else ('submap',engine.current_submap_id))
    # Snapshot replaces the active address. Different addresses serialize
    # independently, even when they happen to point to the same live map.
    maps[active]=engine.local_map
    for local_map in maps.values():
        if hasattr(local_map,'floor_objects'):owned.extend(map_items(local_map))
    seen=set()
    for item in owned:
        if not (('coating_dose' in item) if isinstance(item,dict) else hasattr(item,'coating_dose')):continue
        if id(item) in seen:raise ValueError('coating dose: duplicate ownership')
        seen.add(id(item))


def grouping_key(item):
    if not hasattr(item,'coating_dose'):return (item.item_id,None)
    p=validate(item.coating_dose,item)
    return (item.item_id,p['essence'],p['strength'],p['hits'])


def label(item):
    if not hasattr(item,'coating_dose'):return item.name
    p=validate(item.coating_dose,item)
    return f"{item.name} ({p['hits']} contacts; {p['essence']} {p['strength']:g})"


def apply(item, engine):
    from engine.item_transfers import consume_throw_unit
    from engine.venom import fully_paralysed
    from engine.palette import RESONANCE_MID, WORN_STONE
    inv=engine.player.inventory
    weapon=engine.player.equipment.slots.get('weapon') if engine.player.equipment else None
    if (fully_paralysed(engine.player) or not inv.contains(item)
            or type(item.count) is not int or item.count < 1 or weapon is item
            or weapon is None or not inv.contains(weapon) or not weapon.equipped
            or engine.data.items.get(weapon.item_id,{}).get('slot')!='weapon'):
        engine.log.add('An equipped weapon and a usable dose are needed.',WORN_STONE)
        return False
    try:
        capture(item,engine.data.items.get(item.item_id,{}))
        p=validate(item.coating_dose,item)
        from engine.save_components import validate_fields, ITEM_STATE
        rows=copy.deepcopy(getattr(weapon,'temporary_essence',[]))
        validate_fields({'temporary_essence':rows},{'temporary_essence':ITEM_STATE['temporary_essence']},'weapon')
        rows=[r for r in rows if r['essence']!=p['essence']]
        rows.append(dict(essence=p['essence'],strength=p['strength'],hits_remaining=p['hits']))
    except (ValueError,TypeError,KeyError,AttributeError):return False
    if not consume_throw_unit(engine,item):return False
    weapon.temporary_essence=rows
    engine.log.add(f"{item.name.capitalize()} coats the {weapon.name}: {p['hits']} contacts.",RESONANCE_MID)
    return True
