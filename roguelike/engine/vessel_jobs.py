"""Map-owned preparation; committed inputs are never refunded."""
import copy
from engine import vessels


def validate_recipe(recipe, data=None):
    req=vessels.process_configuration(recipe['vessel_process'])
    wash='material_response' in recipe
    if ((not wash and recipe.get('result_item')!='resonant_bone_tincture')
            or recipe.get('passive_processing') is not True
            or recipe.get('processing_source')!='steeping'
            or type(recipe.get('processing_turns')) is not int or not 1<=recipe['processing_turns']<=10000):
        raise ValueError('vessel process supports bone tincture or a material-sensitive wash in 1..10000 turns')
    if wash:
        from engine.material_response import configuration
        configuration(recipe)
        if not req['heatproof']:raise ValueError('wash requires a heatproof water vessel')
        if not any(r.get('tag')=='burning' and type(r.get('min_tier')) is int and r['min_tier']>=2 for r in recipe.get('requires_ambient',[])):
            raise ValueError('wash requires burning tier two at start')
        if data is not None:
            from engine.coating_doses import defined
            defined(data.items.get(recipe.get('result_item'),{}))
    if not isinstance(recipe.get('processing_decor',''),str):
        raise ValueError('vessel process: marker must be a string')
    from engine.processing_text import validate_completion_template
    validate_completion_template(recipe.get('completion_message',''))
    return req


def start(e,recipe,selected,ambient,xy):
    from components.inventory import Inventory
    from engine.crafting import plan_craft
    from engine.item_transfers import exchange
    from engine.venom import fully_paralysed
    from engine.interaction_cursor import InteractionCursor
    from engine.save_components import serialize_item,validate_item
    from generation.decor_utils import place_decor
    from engine.palette import MSG_DEFAULT
    if (fully_paralysed(e.player) or not e._check_placement_valid(*xy)
            or not InteractionCursor.can_reach(e,*xy)
            or any(a is not e.player and getattr(a,'blocks_movement',False) and (a.x,a.y)==xy for a in e.entities)
            or getattr(e,'_pending_vessel_context',None)!=vessels.context(e)):return False
    try:
        req=validate_recipe(recipe,e.data)
        if selected is None or any(not e.player.inventory.contains(i) for i in selected):return False
        subset=Inventory();subset.items=list(selected)
        checked,missing=plan_craft(recipe,subset,ambient_sources=ambient,chosen_items=getattr(selected,'choices',None))
        if missing or checked.vessel is None:return False
        if 'material_response' in recipe:
            if (checked.roles.get('primary') is not getattr(selected,'roles',{}).get('primary')
                    or checked.primary_state != getattr(selected,'primary_state',None)
                    or checked.allocations != getattr(selected,'allocations',{})):
                return False
        output=e.item_factory.create(recipe['result_item'])
        if output is None:return False
        validate_item(serialize_item(output),'preparation output')
        record=dict(item_id=recipe['result_item'],turns_remaining=recipe['processing_turns'],
            decor_id=recipe.get('processing_decor',''),source='steeping',on_fire=False,
            completion_message=recipe.get('completion_message',''),
            vessel_job=dict(version=1,requirement=req,vessel=checked.vessel))
        if 'material_response' in recipe:
            from engine.material_response import output
            record['vessel_job'].update(version=2,output=output(recipe,checked,e.item_factory),
                                       primary=copy.deepcopy(checked.primary_state))
        if not exchange(e,checked.materials+[checked.vessel]):return False
        vessels.set_water(checked.vessel,0)
        e.local_map.processing_layer[xy]=record
        if record['decor_id'] in e.data.decoratives:place_decor(e.local_map,*xy,record['decor_id'])
        e._free_move_pending=False
        e.log.add(('The wash steeps.' if 'material_response' in recipe else 'The bone steeps.')+
                  ' The vessel must stay with the work.',MSG_DEFAULT)
        return True
    except (ValueError,TypeError,KeyError):return False


def deliver(local_map,xy,items):
    """Preflight every object, then roll back even a partially failed placement."""
    from generation.floor_object_utils import place_floor_object,remove_floor_object
    from engine.save_components import serialize_item,validate_item
    if (not local_map.in_bounds(*xy) or not bool(local_map.walkable[xy])
            or len({id(i) for i in items})!=len(items)
            or any(i is old for i in items for rows in local_map.floor_objects.values() for old in rows)):
        return False
    try:
        for i in items:validate_item(serialize_item(i),'preparation delivery')
    except (ValueError,TypeError,KeyError):return False
    before=[(i.x,i.y) for i in items]
    try:
        for i in items:
            if not place_floor_object(local_map,*xy,i):raise ValueError('destination rejected')
    except Exception:
        for i,pos in zip(items,before):
            remove_floor_object(local_map,*xy,i);i.x,i.y=pos
        return False
    return True


def abandon(e,xy,job,captured):
    from engine.venom import fully_paralysed
    from engine.interaction_cursor import InteractionCursor
    from generation.decor_utils import clear_decor
    from engine.palette import MSG_DEFAULT
    if (fully_paralysed(e.player) or captured!=vessels.context(e)
            or not InteractionCursor.can_reach(e,*xy)
            or e.local_map.processing_layer.get(xy) is not job or 'vessel_job' not in job):return False
    v=job['vessel_job']['vessel']
    # Return at the player's reachable feet if the work tile became unusable.
    if not deliver(e.local_map,(e.player.x,e.player.y),[v]):return False
    del e.local_map.processing_layer[xy]
    if job.get('decor_id') and e.local_map.decor.get(xy)==job['decor_id']:clear_decor(e.local_map,*xy)
    e._free_move_pending=False
    e.log.add('The empty vessel is recovered. The preparation is discarded.',MSG_DEFAULT)
    return True
