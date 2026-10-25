"""C exact-owner and failed-transaction oracles against actual main bootstrap."""
from b1_support import read, hashes
from b1_cases import clean_gear


def fixture(e):
    from b2_cases import quiet
    quiet(e)
    clean_gear(e)
    e.player.inventory.capacity = 100
    e.player.x = e.player.y = 20
    e.local_map.floor_objects.clear()
    e.local_map.container_state.clear()
    for x in range(18, 23):
        for y in range(18, 23):
            e.local_map.set_tile(x, y, 'flagstone', True, True)
            e.local_map.decor.pop((x, y), None)
            e.local_map.processing_layer.pop((x, y), None)
    e._update_fov()


def make(e, item_id, **state):
    item = e.item_factory.create(item_id)
    assert item is not None, item_id
    item.__dict__.update(state)
    return item


def owners(e, item):
    return dict(inventory=sum(i is item for i in e.player.inventory.items),
        floor=sum(i is item for rows in e.local_map.floor_objects.values() for i in rows),
        legacy=sum(i is item for i in e.entities),
        container=sum(i is item for entry in e.local_map.container_state.values() for i in entry['items']),
        slots=[s for s,i in e.player.equipment.slots.items() if i is item], equipped=item.equipped)


def check_owner(ev, e, item, owner, slots=(), case='C-01'):
    wanted=dict(inventory=0,floor=0,legacy=0,container=0,slots=list(slots),equipped=bool(slots))
    if owner: wanted[owner]=1
    ev.check(case, item.name+' exact owner', wanted, owners(e,item))


def run_case(e, ev):
    import pygame
    from engine.item_transfers import drop, take_floor, take_container, exchange, consume
    from generation.floor_object_utils import place_floor_object, place_container, open_container, get_container_items
    from engine.crafting import plan_craft, commit_craft, attempt_craft
    from rendering.craft_screen import CraftScreen
    if ev.job['scenario']=='roundtrip':
        return roundtrip(e,ev)
    fixture(e)
    p, inv = e.player, e.player.inventory
    variant = ev.job['variant']
    if variant=='ownership':
        for iid, slot in [('crude_blade','weapon'),('leather_jack','armor_torso'),('tallow_torch','offhand'),('moist_pebble','talisman_1')]:
            item=make(e,iid); inv.add(item);e.item_system.use(item,e)
            check_owner(ev,e,item,'inventory',[slot])
            armor=p.fighter.effective_av
            if iid=='leather_jack':ev.check('C-01','armor applied before drop',True,armor>0)
            ev.check('C-01','valid drop succeeds',True,drop(e,item))
            check_owner(ev,e,item,'floor')
            ev.check('C-01','drop clears light reference',False,getattr(p.light_source,'_item_ref',None) is item)
            ev.check('C-01','drop removes armor contribution',getattr(p.fighter,'attuned_av_bonus',0),p.fighter.effective_av)
            ev.check('C-01','duplicate drop rejected',False,drop(e,item))
            ev.check('C-01','unowned use has no effect',False,e.item_system.use(item,e))
            check_owner(ev,e,item,'floor')
            ev.check('C-01','pickup exact dropped object',True,take_floor(e,item))
            check_owner(ev,e,item,'inventory')
            ev.check('C-01','duplicate pickup rejected',False,take_floor(e,item))
            ev.check('C-01','duplicate inventory insertion rejected',False,inv.add(item))
            e.item_system.use(item,e)
            p.x=-1
            ev.check('C-02','invalid destination leaves equipped source',False,drop(e,item))
            check_owner(ev,e,item,'inventory',[slot],case='C-02')
            p.x=20
            consume(e,item)
        a,b=make(e,'crude_blade'),make(e,'crude_blade')
        inv.add(a);inv.add(b);e.item_system.use(a,e);e.item_system.use(b,e)
        check_owner(ev,e,a,'inventory')
        check_owner(ev,e,b,'inventory',['weapon'])
        # Floor address, not stale item coordinates, is the source authority.
        legacy=make(e,'crow_jerky',x=21,y=20);e.entities.append(legacy)
        ev.check('C-02','legacy entity pickup',True,take_floor(e,legacy))
        check_owner(ev,e,legacy,'inventory',case='C-02')
        loose=make(e,'crow_jerky');place_floor_object(e.local_map,21,20,loose);loose.x=0
        inv.capacity=inv.current_weight
        ev.check('C-02','overweight pickup keeps floor',False,take_floor(e,loose))
        check_owner(ev,e,loose,'floor',case='C-02')
        inv.capacity=100
        ev.check('C-02','floor key authoritative over stale coordinates',True,take_floor(e,loose))
        check_owner(ev,e,loose,'inventory',case='C-02')
        ev.check('C-02','stale unowned selection rejected',False,take_floor(e,make(e,'crow_jerky')))
    elif variant=='containers':
        a,b=[make(e,'tallow_torch',turns_lit=n,qualities={'nested':{'n':n}}) for n in (11,77)]
        place_container(e.local_map,21,20,'coffer',[a,b])
        ev.check('C-03','closed container refuses transfer',False,take_container(e,21,20,b))
        open_container(e.local_map,21,20)
        first=get_container_items(e.local_map,21,20,e.item_factory)
        second=get_container_items(e.local_map,21,20,e.item_factory)
        ev.check('C-03','browsing retains exact distinct instances',True,first[0] is a and first[1] is b and second[1] is b)
        ev.check('C-03','full instance state retained',[11,77],[first[0].turns_lit,first[1].turns_lit])
        inv.capacity=0
        ev.check('C-03','container capacity failure unchanged',False,take_container(e,21,20,b))
        check_owner(ev,e,b,'container',case='C-03')
        inv.capacity=100
        ev.check('C-03','take second same-definition instance',True,take_container(e,21,20,b))
        check_owner(ev,e,a,'container',case='C-03');check_owner(ev,e,b,'inventory',case='C-03')
        ev.check('C-03','stale container selection rejected',False,take_container(e,21,20,b))
        b.qualities['nested']['n']=99
        ev.check('C-03','remaining nested state independent',11,a.qualities['nested']['n'])
        take_container(e,21,20,a)
        ev.check('C-03','container looted only when empty','looted',e.local_map.container_state[(21,20)]['state'])
        # Read old minimal rows without changing a personal save.
        e.local_map.container_state[(22,20)]={'state':'open','items':[{'item_id':'crow_jerky','text_id':'lab_label_sarcophagus'}]}
        old=get_container_items(e.local_map,22,20,e.item_factory)[0]
        ev.check('C-03','legacy text binding retained','lab_label_sarcophagus',old.text_id)
        ev.check('C-03','legacy row resolves just once',True,old is get_container_items(e.local_map,22,20,e.item_factory)[0])
        e.local_map.container_state[(22,21)]={'state':'open','items':[{'item_id':'missing-c-item'}]}
        try:get_container_items(e.local_map,22,21,e.item_factory)
        except ValueError:rejected=True
        else:rejected=False
        ev.check('C-03','unknown legacy row rejected without erasure',True,rejected and len(e.local_map.container_state[(22,21)]['items'])==1)
    elif variant=='crafting':
        wood=[make(e,'wood_bundle',name='fuel '+str(n)) for n in (1,2)]
        blade=make(e,'crude_blade'); inv.items=wood+[blade]; e.item_system.use(blade,e)
        recipe=e.data.recipes['campfire']
        e.craft_screen._attempt_craft(e,recipe,chosen_items={})
        ev.check('C-04','placement consumes nothing before confirmation',True,inv.items==wood+[blade])
        e._handle_key_placement(pygame.K_ESCAPE)
        ev.check('C-04','cancel retains exact objects and state',True,inv.items==wood+[blade] and e._pending_craft_items is None)
        check_owner(ev,e,blade,'inventory',['weapon'],case='C-04')
        e.craft_screen._attempt_craft(e,recipe,chosen_items={})
        p0=list(inv.items);e._placement_cursor_x=p.x;e._placement_cursor_y=p.y
        e._handle_key_placement(pygame.K_RETURN)
        ev.check('C-04','invalid placement leaves source intact',True,inv.items==p0)
        e._placement_cursor_y=19;e._handle_key_placement(pygame.K_RETURN)
        ev.check('C-04','confirm consumes exactly fuel and places once',[['crude_blade'],'campfire_unlit'],[[i.item_id for i in inv.items],e.local_map.decor[(20,19)]])
        check_owner(ev,e,blade,'inventory',['weapon'],case='C-04')
        # Missing later requirements cannot partially consume earlier components.
        fuel=make(e,'wood_bundle');inv.add(fuel)
        bad={'components':[{'tag':'fuel'},{'tag':'nonexistent'}]}
        ev.check('C-05','invalid pure recipe no partial consumption',False,attempt_craft(bad,inv))
        ev.check('C-05','first requirement still owned',True,inv.contains(fuel))
        simple={'components':[{'tag':'fuel'}],'result_item':'leather_jack'}
        inv.capacity=inv.current_weight
        before=list(inv.items);e.craft_screen._attempt_craft(e,simple,chosen_items={})
        ev.check('C-05','overweight output keeps exact ingredients',True,inv.items==before)
        inv.capacity=100
        missing=dict(simple,result_item='missing-c-output');e.craft_screen._attempt_craft(e,missing,chosen_items={})
        ev.check('C-05','invalid output keeps exact ingredients',True,inv.items==before)
        selected,_=plan_craft(simple,inv);inv.remove(fuel)
        ev.check('C-05','stale pending plan rejected',False,commit_craft(e,simple,selected))
        inv.add(fuel);e.craft_screen._attempt_craft(e,simple,chosen_items={})
        ev.check('C-05','immediate craft commits output and consumed ingredient',[False,1],[inv.contains(fuel),sum(i.item_id=='leather_jack' for i in inv.items)])
        # A consumable equipped ingredient must detach; reusable tools remain.
        blade.consumed_on_use=True
        selected,missing=plan_craft({'components':[{'tag':'cutting'}]},inv)
        ev.check('C-05','equipped ingredient planned',[],missing)
        ev.check('C-05','consume equipped ingredient',True,commit_craft(e,{'components':[{'tag':'cutting'}]},selected))
        check_owner(ev,e,blade,None,case='C-05')
        ambient_recipe={'requires_single_item':[{'tag':'fuel'}],'requires_ambient':[{'tag':'heat'}]}
        inv.add(fuel)
        plan,missing=plan_craft(ambient_recipe,inv,ambient_sources=[{'tag':'heat','tier':1}])
        ev.check('C-05','single-item and ambient plan',True,not missing and plan==[fuel])
        dual=make(e,'wood_bundle',keywords=[{'tag':'fuel','tier':1},{'tag':'cutting','tier':1}])
        preferred=make(e,'crow_jerky',keywords=[{'tag':'fuel','tier':2}])
        inv.items=[dual,preferred]
        overlap={'components':[{'tag':'fuel'},{'tag':'cutting'}]}
        plan,missing=plan_craft(overlap,inv,chosen_items={0:preferred.item_id})
        ev.check('C-05','chosen component keeps overlapping alternative available',True,not missing and plan==[preferred,dual])
        ev.check('C-05','confirmation honors choice instead of greedy substitution',True,commit_craft(e,overlap,plan))
        ev.check('C-05','chosen plan consumes each exact material once',[],inv.items)
        # Processing keeps its exact selected ingredient through cursor/cancel.
        from generation.decor_utils import place_decor, clear_decor
        meat=make(e,'raw_meat_common');inv.items=[meat]
        place_decor(e.local_map,20,19,'campfire_lit')
        cooking=e.data.recipes['cook_meat']
        e.craft_screen._attempt_craft(e,cooking,chosen_items={})
        ev.check('C-05','processing selection remains inventory-owned',True,inv.items==[meat] and e._pending_craft_items==[meat])
        e._handle_key_placement(pygame.K_ESCAPE)
        ev.check('C-05','processing cancellation no refund copies',True,inv.items==[meat] and not e.local_map.processing_layer)
        e.craft_screen._attempt_craft(e,cooking,chosen_items={})
        inv.remove(meat)
        replacement=make(e,'raw_meat_common');inv.add(replacement)
        e._placement_cursor_x=20;e._placement_cursor_y=19
        e._handle_key_placement(pygame.K_RETURN)
        ev.check('C-05','stale processing plan cannot substitute same-definition item',True,inv.items==[replacement] and not e.local_map.processing_layer)
        e.craft_screen._attempt_craft(e,cooking,chosen_items={})
        e._placement_cursor_x=20;e._placement_cursor_y=19
        e._handle_key_placement(pygame.K_RETURN)
        ev.check('C-05','processing confirmation moves material into one job',True,not inv.items and e.local_map.processing_layer[(20,19)]['item_id']=='cooked_meat')
        for _ in range(cooking['processing_turns']):e._advance_turn()
        cooked=[i for i in e.local_map.floor_objects.get((20,19),[]) if i.item_id=='cooked_meat']
        ev.check('C-05','completed processing output has one floor owner',1,len(cooked))
        check_owner(ev,e,cooked[0],'floor',case='C-05')
        # Pending materials are inventory-owned during save; load cancels cursor.
        fuel2=[make(e,'wood_bundle') for _ in range(2)];tool=make(e,'crude_blade')
        inv.items=fuel2+[tool]
        e.craft_screen._attempt_craft(e,recipe,chosen_items={})
        ev.check('C-05','save while placement pending',True,e.save_manager.save(e))
        ev.check('C-05','reload while placement pending',True,e.save_manager.load(e))
        ev.check('C-05','reload clears pending plan and retains ingredients',[None,['wood_bundle','wood_bundle','crude_blade']],
                 [e._pending_craft_items,[i.item_id for i in e.player.inventory.items]])
    elif variant=='production':
        skin=make(e,'water_skin');inv.items=[skin];inv.capacity=skin.weight
        e.item_system.use(skin,e)
        ev.check('C-06','drink releases old weight before adding empty form',['empty_water_skin'],[i.item_id for i in inv.items])
        empty=inv.items[0];inv.capacity=empty.weight
        e.local_map.set_tile(20,20,'shallow_water',True,True)
        # Use authored drinkable terrain, not a guessed tile definition.
        terrain=next(k for k,v in e.data.terrain.items() if v.get('drinkable'))
        e.local_map.set_tile(20,20,terrain,True,True)
        ev.check('C-06','full vessel overweight failure',False,e._interactable_drink_source(20,20))
        ev.check('C-06','failed refill retains exact empty vessel',True,inv.items==[empty])
        inv.capacity=100
        ev.check('C-06','refill commits replacement',True,e._interactable_drink_source(20,20))
        ev.check('C-06','one full vessel',['water_skin'],[i.item_id for i in inv.items])
        # Saturated harvest cannot deplete the source plant.
        from generation.decor_utils import place_decor
        tid,definition=next((k,v) for k,v in e.data.decoratives.items() if v.get('harvestable') and v.get('harvest_item') in e.data.items)
        place_decor(e.local_map,20,20,tid);inv.capacity=inv.current_weight
        before_plant=(str(e.local_map.tiles[20,20]['terrain']),e.local_map.decor.get((20,20)))
        ev.check('C-06','overweight harvest rejected',False,e._try_harvest())
        ev.check('C-06','failed harvest preserves plant',before_plant,(str(e.local_map.tiles[20,20]['terrain']),e.local_map.decor.get((20,20))))
        inv.capacity=100;ev.check('C-06','harvest delivers item',True,e._try_harvest())
        ev.check('C-06','harvest item retained',True,any(i.item_id==definition['harvest_item'] for i in inv.items))


def round_state(e):
    from generation.floor_object_utils import get_container_items
    container=get_container_items(e.local_map,21,20,e.item_factory)
    return dict(inventory=[(i.item_id,i.turns_lit,i.qualities) for i in e.player.inventory.items],
        floor=[(i.item_id,i.equipped) for i in e.local_map.floor_objects[(20,20)]],
        container=[(i.item_id,i.turns_lit,i.qualities) for i in container],
        slots={s:None if i is None else e.player.inventory.items.index(i) for s,i in e.player.equipment.slots.items()})


def roundtrip(e,ev):
    from engine.item_transfers import drop,take_container
    from generation.floor_object_utils import place_container,open_container,get_container_items
    phase=ev.job['phase']
    if phase!='read':
        fixture(e)
        a,b=[make(e,'tallow_torch',turns_lit=n,qualities={'distinct':n}) for n in (11,77)]
        blade=make(e,'crude_blade');e.player.inventory.add(blade);e.item_system.use(blade,e);drop(e,blade)
        place_container(e.local_map,21,20,'coffer',[a,b]);open_container(e.local_map,21,20)
        take_container(e,21,20,b);e.item_system.use(b,e)
        ev.record['expected']=round_state(e)
        ev.check('C-07','post-transfer checkpoint publishes',True,e.save_manager.save(e))
        ev.record['checkpoint']=hashes(e.save_manager.save_path)
        if phase=='write':return
        ev.check('C-07','same-process post-transfer reload',True,e.save_manager.load(e))
        expected=ev.record['expected']
    else:expected=read(ev.job['expected'])['expected']
    # JSON roundtrip normalizes tuple output for independent comparison.
    import json
    ev.check('C-07','checkpoint retains distinct owners and full container state',json.loads(json.dumps(expected)),json.loads(json.dumps(round_state(e))))
    torch=e.player.inventory.items[0]
    ev.check('C-07','equipment and light bind exact restored owned instance',True,e.player.equipment.slots['offhand'] is torch and e.player.light_source._item_ref is torch)
    item=get_container_items(e.local_map,21,20,e.item_factory)[0]
    ev.check('C-07','post-load exact transfer remains usable',True,take_container(e,21,20,item))
    check_owner(ev,e,item,'inventory',case='C-07')
