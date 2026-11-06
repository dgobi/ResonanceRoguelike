"""Adjacent interruptible work, exact-dose application and the ordinary chooser."""
import copy
from engine import access_objects as objects


def context(e):
    return e.local_map, e.world_x, e.world_y, e.current_submap_id, e.player.x, e.player.y


def cutters(e):
    from engine.harvesting import owned_cutters
    return tuple(owned_cutters(e.player))


def dose_state(item):
    from entities.item import use_capability
    from engine.coating_doses import validate
    if use_capability(item) != 'apply_to_weapon' or not hasattr(item,'coating_dose'):
        return None
    try: return copy.deepcopy(validate(item.coating_dose,item))
    except (ValueError,TypeError,KeyError): return None


def qualifies(item, p):
    d = dose_state(item)
    return bool(d and d['essence']=='Dissolution' and d['strength'] >= p['dissolution_threshold']
                and type(item.count) is int and item.count > 0 and not item.equipped)


def intent(e, xy):
    row = objects.at(e.local_map,xy)
    return dict(context=context(e), xy=xy, owner=row, observed=copy.deepcopy(row),
                cutters=cutters(e), equipment=tuple(e.player.equipment.slots.items()))


def current(e, token):
    from engine.interaction_cursor import InteractionCursor
    from engine.venom import fully_paralysed
    row = token['owner']
    if (context(e)!=token['context'] or fully_paralysed(e.player)
            or tuple(e.player.equipment.slots.items())!=token['equipment']
            or objects.at(e.local_map,token['xy']) is not row or row!=token['observed']
            or row is None or row['completed_by'] is not None
            or not InteractionCursor.can_reach(e,*token['xy'])
            or not e.local_map.walkable[e.player.x,e.player.y]):
        return False
    try: objects.validate_map(e.local_map)
    except (ValueError,TypeError,KeyError): return False
    return True


def perform(e, token, method, dose=None, expected_dose=None):
    """Commit once; the caller alone pays the ordinary action after success."""
    if method not in ('careful','force','dissolution') or not current(e,token): return False
    row, xy, m = token['owner'], token['xy'], e.local_map
    p = row['profile']
    if not p['allow_'+method]: return False
    if method=='careful' and (cutters(e)!=token['cutters'] or not any(t>=p['cutting_tier'] for _,t in cutters(e))):
        from engine.palette import MSG_DEFAULT
        e.log.add(f"Equip an owned cutting tool (tier {p['cutting_tier']} or higher).",MSG_DEFAULT)
        return False
    if method=='dissolution' and (dose is None or not e.player.inventory.contains(dose)
            or any(i is dose for i in e.player.equipment.slots.values())
            or not qualifies(dose,p) or expected_dose != (dose_state(dose),dose.count)):
        return False
    completing = method!='careful' or row['progress']+1==p['work_steps']
    wood = None
    if completing and method=='careful' and row['host']=='screen' and p['screen_careful_yield']:
        from engine.harvesting import validate_output
        try: wood = validate_output(e.item_factory.create(p['screen_careful_yield'],*xy),p['screen_careful_yield'])
        except Exception: return False
    # Snapshots retain exact item owners; rollback does not reconstruct instances.
    old_row, old_tile = copy.deepcopy(row), m.tiles[xy].copy()
    old_floor = list(m.floor_objects.get(xy,[])); had_floor = xy in m.floor_objects
    inv = e.player.inventory
    old_inventory = list(inv.items)
    old_count = dose.count if dose is not None else None
    try:
        if wood is not None:
            from generation.floor_object_utils import place_floor_object
            if not place_floor_object(m,*xy,wood): raise ValueError('Wood output could not be placed.')
        if method=='careful': row['progress'] += 1
        if completing: objects.complete(m,xy,row,method)
        if method=='dissolution':
            from engine.item_transfers import consume_throw_unit
            if not consume_throw_unit(e,dose): raise ValueError('Dose owner changed.')
        objects.validate_map(m)
    except Exception:
        row.clear();row.update(old_row);m.tiles[xy] = old_tile
        if had_floor: m.floor_objects[xy] = old_floor
        else: m.floor_objects.pop(xy,None)
        inv.items[:] = old_inventory
        if dose is not None:dose.count = old_count
        return False
    from engine.palette import MSG_DEFAULT
    if completing:
        message = {'careful':'The last binding parts.', 'force':'The fastening gives with a dry crack.',
                   'dissolution':'The pale cord softens and slips apart.'}[method]
        if wood is not None: message += ' One wood bundle lies on the floor.'
    else: message = f"You cut into the binding. {row['progress']}/{p['work_steps']}."
    e.log.add(message,MSG_DEFAULT)
    if method!='dissolution':
        from engine.sound import emit
        emit(e,token['context'][-2],token['context'][-1], 'access_work' if method=='careful' else 'dismantle',maker=e.player)
    return True


def offer(e, xy):
    row = objects.at(e.local_map,xy)
    if row is None or row['completed_by'] is not None:return False
    from engine.vessel_menu import show, paid
    token = intent(e,xy);p = row['profile'];options=[]
    if p['allow_careful']:
        label = 'Continue cutting' if row['progress'] else 'Careful cutting'
        options.append((f"{label} — {row['progress']}/{p['work_steps']}; equipped cutting {p['cutting_tier']}; 1 turn, quiet",lambda:paid(e,lambda:perform(e,token,'careful'))))
    if p['allow_force']:
        options.append(('Quick force — 1 turn, loud; no salvage',lambda:paid(e,lambda:perform(e,token,'force'))))
    if p['allow_dissolution']:
        def choose():
            if not current(e,token):return
            choices=[]
            for dose in e.player.inventory.items:
                if not qualifies(dose,p):continue
                d = dose_state(dose);expected=(d,dose.count)
                label=f"{dose.name}: {d['strength']:g} strength, {d['hits']} weapon contacts; spend whole dose"
                choices.append((label,lambda dose=dose,expected=expected:paid(e,lambda:perform(e,token,'dissolution',dose,expected))))
            show(e,'Dissolution — whole dose; 1 turn; no work sound or salvage',choices)
        options.append((f"Dissolution ≥ {p['dissolution_threshold']:g} — choose one whole dose",choose))
    show(e,p['name']+' — secured' if row['host']=='container' else p['name']+' — opaque screen',options)
    return True
