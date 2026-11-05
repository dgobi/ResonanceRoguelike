"""SYS-1: registered water-only vessels and exact physical handling.

Empty weight stays on Item. Water adds 1 kg/litre; a 250 mL serving supplies
250 existing thirst points (divided by the saved needs maximum). No rain hook.
"""
from __future__ import annotations
import copy
import re
import uuid

MAX_ML = 10000
SERVING_ML = 250
CLAY = dict(version=1, capacity_ml=500, contents='water')


def configuration(raw):
    if (not isinstance(raw, dict) or set(raw) != {'version','capacity_ml','contents'}
            or type(raw['version']) is not int or raw['version'] != 1
            or type(raw['capacity_ml']) is not int or not 1 <= raw['capacity_ml'] <= MAX_ML
            or raw['contents'] != 'water'):
        raise ValueError('vessel: version 1, water and integral capacity 1..10000 mL required')
    return copy.deepcopy(raw)


def process_configuration(raw):
    if (not isinstance(raw, dict) or set(raw) != {'version','water_ml','heatproof'}
            or type(raw['version']) is not int or raw['version'] != 1
            or type(raw['water_ml']) is not int or not 1 <= raw['water_ml'] <= MAX_ML
            or type(raw['heatproof']) is not bool):
        raise ValueError('vessel process: version 1, water_ml 1..10000 and heatproof boolean required')
    return copy.deepcopy(raw)


def bound_use(raw):
    from entities.item import use_capability,repair_selected_equipment_use
    from types import SimpleNamespace
    item=SimpleNamespace(item_id=raw.get('item_id',raw.get('id','')),on_use=raw.get('on_use'))
    repair_selected_equipment_use(item)
    return use_capability(item)


def validate_definition(raw):
    if 'vessel' not in raw: return
    configuration(raw['vessel'])
    if (bound_use(raw) or raw.get('stackable',False) is not False or raw.get('consumed_on_use',True) is not False
            or raw.get('on_use') is not None or raw.get('liquid') is not None
            or raw.get('liquid_volume',0) != 0):
        raise ValueError('vessel: reusable nonstackable empty item without another use binding required')


def create(config):
    return dict(config=configuration(config), id=uuid.uuid4().hex, water_ml=0, contents=None)


def legacy(item):
    if (not hasattr(item,'vessel') and not hasattr(item,'vessel_absent_version') and item.item_id == 'clay_pot'
            and getattr(item,'liquid',None) is None and getattr(item,'liquid_volume',0) == 0
            and not item.stackable and item.count == 1
            and getattr(item,'consumed_on_use',True) is False and not bound_use(vars(item))):
        item.vessel = create(CLAY)


def validate(state, row):
    if (not isinstance(state,dict) or set(state) != {'config','id','water_ml','contents'}
            or not isinstance(state['id'],str) or not re.fullmatch('[0-9a-f]{32}',state['id'])):
        raise ValueError('vessel: invalid saved state or identity')
    cfg = configuration(state['config']); ml = state['water_ml']
    if (type(ml) is not int or not 0 <= ml <= cfg['capacity_ml']
            or state['contents'] != ('water' if ml else None)
            or row.get('stackable',False) is not False or row.get('count',1) != 1
            or type(row.get('count',1)) is not int or row.get('liquid') is not None
            or row.get('liquid_volume',0) != 0
            or row.get('consumed_on_use',True) is not False or bound_use(row)):
        raise ValueError('vessel: inconsistent contents or physical instance')


def state(item):
    return getattr(item,'vessel',None)


def label(item):
    s=state(item)
    return (f"{item.name} [{s['id'][:4]}] {s['water_ml']}/{s['config']['capacity_ml']} mL"
            if s else item.name)


def set_water(item, ml):
    item.vessel['water_ml']=ml
    item.vessel['contents']='water' if ml else None


def matches(item, requirement):
    from engine.crafting import _item_has_tag
    s=state(item)
    if s is None: return False
    validate(s,vars(item)); req=process_configuration(requirement)
    return (s['water_ml']==req['water_ml'] and s['config']['capacity_ml']>=req['water_ml']
            and (not req['heatproof'] or _item_has_tag(item,'heatproof',1)))


def context(e):
    return (e.local_map,e.world_x,e.world_y,e.current_submap_id)


def source(e, xy):
    from engine.interaction_cursor import InteractionCursor
    x,y=xy
    return (InteractionCursor.can_reach(e,x,y)
            and e.data.terrain.get(str(e.local_map.tiles[x,y]['terrain']),{}).get('drinkable',False))


def owned(e,item):
    if not state(item) or sum(i is item for i in e.player.inventory.items)!=1: return False
    validate(state(item),vars(item))
    return True


def handle(e, action, item, amount=0, *, destination=None, xy=None, captured=None):
    """Commit resources only; caller pays exactly one action on True."""
    from engine.venom import fully_paralysed
    from engine.palette import MSG_DEFAULT
    def deny(message):
        e.log.add(message,MSG_DEFAULT); return False
    if fully_paralysed(e.player) or captured is not None and captured != context(e): return False
    try:
        if not owned(e,item): return deny('That vessel is no longer carried.')
        if type(amount) is not int or amount < 0: return False
        s=state(item); ml=s['water_ml']; cap=s['config']['capacity_ml']
        if action=='fill':
            if xy is None or not source(e,xy): return deny('There is no reachable drinking water here.')
            if not amount: return False
            if ml+amount>cap: return deny('That much water will not fit.')
            from components.inventory import effective_weight,item_category
            inv=e.player.inventory; reductions=inv.reductions_for()
            category=item_category(item,inv._definitions)
            added=amount/1000*(1-reductions.get(category,reductions.get('all',0)))
            if inv.current_weight+added>inv.capacity+1e-9: return deny('Too much water to carry.')
            set_water(item,ml+amount)
        elif action=='transfer':
            if destination is item or not amount: return False
            if not owned(e,destination): return deny('The receiving vessel is no longer carried.')
            d=state(destination)
            if amount>ml or d['water_ml']+amount>d['config']['capacity_ml']:
                return deny('There is not enough water or room for that transfer.')
            # Category-specific bag discounts can change effective load.
            from components.inventory import item_category
            inv=e.player.inventory;r=inv.reductions_for()
            rate=lambda i:1-r.get(item_category(i,inv._definitions),r.get('all',0))
            if inv.current_weight+amount/1000*(rate(destination)-rate(item))>inv.capacity+1e-9:
                return deny('Too much to carry in that vessel.')
            set_water(item,ml-amount);set_water(destination,d['water_ml']+amount)
        elif action=='drink':
            serving=min(SERVING_ML,ml)
            if not serving: return deny('The vessel is empty.')
            e.player.needs.drink(serving/e.player.needs._t_max)
            set_water(item,ml-serving)
        elif action=='empty':
            if not ml:return False
            set_water(item,0)
        else:return False
    except (ValueError,TypeError,KeyError):
        return deny('That vessel cannot be handled.')
    e._free_move_pending=False
    e.log.add({'fill':'Water fills the vessel.','transfer':'The water passes between vessels.',
               'drink':'Cool water eases thy thirst.','empty':'The water is discarded.'}[action],MSG_DEFAULT)
    return True


def claim(row, identities):
    s=row.get('vessel')
    if s is not None:
        validate(s,row)
        if s['id'] in identities: raise ValueError('vessel: duplicate ownership')
        identities.add(s['id'])


def validate_map(local_map, identities=None):
    """All pickled owners, including busy implements; no partial installation."""
    from engine.save_components import serialize_item, validate_item
    identities=set() if identities is None else identities
    def item(i):
        row=i if isinstance(i,dict) else serialize_item(i)
        validate_item(row,'map item');claim(row,identities)
    for rows in local_map.floor_objects.values():
        for i in rows:item(i)
    for owner in local_map.container_state.values():
        for i in owner.get('items',[]):item(i)
    for xy,job in local_map.processing_layer.items():
        if 'vessel_job' not in job:continue
        b=job['vessel_job']
        if (not isinstance(b,dict) or set(b)!={'version','requirement','vessel'}
                or type(b['version']) is not int or b['version']!=1
                or type(job.get('turns_remaining')) is not int or not 0<=job['turns_remaining']<=10000
                or job.get('item_id')!='resonant_bone_tincture'
                or job.get('source')!='steeping' or job.get('on_fire') is not False
                or not isinstance(job.get('decor_id'),str)
                or not isinstance(job.get('completion_message'),str)
                or not local_map.in_bounds(*xy)):
            raise ValueError('vessel job: invalid captured preparation')
        from engine.processing_text import validate_completion_template
        validate_completion_template(job['completion_message'])
        req=process_configuration(b['requirement']);v=b['vessel'];item(v)
        if not state(v) or state(v)['water_ml'] or state(v)['config']['capacity_ml']<req['water_ml']:
            raise ValueError('vessel job: empty capable owned implement required')
        from engine.crafting import _item_has_tag
        if req['heatproof'] and not _item_has_tag(v,'heatproof',1):
            raise ValueError('vessel job: heat-suitable implement required')
