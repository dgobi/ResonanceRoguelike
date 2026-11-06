"""Opt-in app-local keyboard fixture for packaged room-test verification.

Enabled only by the native host's process diagnostic flag. Commands are ordinary
pygame key events and frame captures; there is no expression/command execution.
"""
import json
from pathlib import Path
import pygame
from engine.save_components import serialize_item
from engine.effect_lifecycle import creature_id


class DiagnosticEvents:
    def __init__(self,root):
        self.root=Path(root)
        self.applied=None
        self.fixture_applied=False
        self.action_calls=0
        self._counting=False
        self.attacks=[]

    def frame(self,e,screen):
        from room_test import write_json
        if not self._counting:
            advance=e._advance_turn
            def counted():
                self.action_calls+=1
                return advance()
            e._advance_turn=counted
            # Read-only trace around the real resolver, preserving its RNG and
            # result. Both ordinary callers still supply their own definitions.
            from dataclasses import asdict
            from engine import combat
            resolve=combat.resolve_attack
            def observed_attack(*args,**kwargs):
                result=resolve(*args,**kwargs)
                self.attacks.append(dict(attacker=kwargs.get('attacker_name'),defender=kwargs.get('defender_name'),
                    weapon=kwargs.get('weapon'),shield=kwargs.get('shield_def'),
                    equipped={slot:str(id(item)) if item else None for slot,item in e.player.equipment.slots.items()},
                    result=asdict(result)))
                self.attacks=self.attacks[-32:]
                return result
            combat.resolve_attack=observed_attack
            self._counting=True
        def observed_item(item):
            return dict(serialize_item(item),instance=str(id(item)))
        def observed_job(r):
            return {**r,**({'vessel_job':{**r['vessel_job'],'vessel':observed_item(r['vessel_job']['vessel'])}}
                         if 'vessel_job' in r else {})}
        m=e.local_map
        inv=e.inventory_screen
        craft=e.craft_screen
        from engine.illumination import scene_light
        from components.ai import _creature_can_see_player
        illumination=scene_light(e)
        observers=[a for a in e.entities if a is not e.player and getattr(a,'perception',None)]
        observation=dict(applied=self.applied,pid=__import__('os').getpid(),player=[e.player.x,e.player.y],
            turn=e.world_time.turn,submap=e.current_submap_id,surface_return=[e.surface_return_x,e.surface_return_y],
            dead=e._player_is_dead,mode=e.mode.name,visible=int(m.tiles['visible'].sum()),
            light=bool(getattr(e.player,'light_source',None) and e.player.light_source.active),
            illumination=dict(ambient=illumination.ambient,lit=illumination.lit.T.tolist(),
                sources=[dict(kind=k,id=i,x=x,y=y,radius=r) for k,i,x,y,r,_,_ in illumination.sources],
                sight=[dict(observer=creature_id(a),target='player' if t is e.player else creature_id(t),
                    seen=_creature_can_see_player(a,t,m,engine=e)) for a in observers for t in [e.player]+observers if a is not t]),
            lighting=dict(active_radius=e._effective_fov_radius,
                emitters=[dict(x=x,y=y,id=d,radius=e.data.decoratives.get(d,{}).get('light_emit',0),visible=bool(m.visible[x,y])) for (x,y),d in m.decor.items() if e.data.decoratives.get(d,{}).get('light_emit',0)>0],
                visible_beyond_player_circle=[[x,y] for x in range(m.width) for y in range(m.height) if m.visible[x,y] and (x-e.player.x)**2+(y-e.player.y)**2>e._effective_fov_radius**2]),
            interaction=dict(cursor=[e.interaction_cursor.cursor_x,e.interaction_cursor.cursor_y],candidates=e.interaction_cursor.candidates,
                selection=None if e.interaction_cursor._selection_prompt is None else dict(selected=e.interaction_cursor._selection_prompt['selected'],source=e.interaction_cursor._selection_prompt.get('source'),items=[observed_item(i) for i in e.interaction_cursor._selection_prompt['items']])),
            inventory=[observed_item(i) for i in e.player.inventory.items],
            equipment={slot:dict(item_id=item.item_id,instance=str(id(item)),inventory_row=next((i for i,owned in enumerate(e.player.inventory.items) if owned is item),None)) if item else None for slot,item in e.player.equipment.slots.items()},
            carrying=dict(weight=e.player.inventory.current_weight,base_weight=sum(i.weight for i in e.player.inventory.items),capacity=e.player.inventory.capacity,reductions=e.player.inventory.reductions_for()),
            effective_av=e.player.fighter.effective_av,attacks=self.attacks,
            action_calls=self.action_calls,fixture_applied=self.fixture_applied,
            needs=dict(hunger=e.player.needs.hunger,thirst=e.player.needs.thirst),hp=e.player.fighter.hp,max_hp=e.player.fighter.max_hp,
            inventory_open=inv.open,inventory_selected=inv.selected,
            inventory_rows=[dict(item_id=getattr(item,'item_id',None),instance=str(id(item)) if item else None,header=header,label=label) for item,header,label in inv._flat],
            craft=dict(open=craft.open,selected=craft.selected,choosing=craft._choosing,
                choice_selected=craft._choice_selected,choice_index=craft._choice_index,
                prompts=[dict(comp_index=p['comp_index'],options=[dict(item_id=o['item_id'],count=o['count'],name=o['name'],
                    instance=str(id(o['instance'])) if 'instance' in o else None,properties=o.get('kw_display','')) for o in p['options']]) for p in craft._choice_prompts],
                rows=[dict(type=r['type'],id=r.get('recipe',{}).get('id'),category=r.get('category')) for r in craft._build_flat_items(craft._get_recipes(e))]),
            placement=dict(mode=e._placement_mode,cursor=[e._placement_cursor_x,e._placement_cursor_y]),
            processing=[dict(x=x,y=y,**observed_job(r)) for (x,y),r in m.processing_layer.items()],
            vessel_menu=None if not e._vessel_menu else dict(title=e._vessel_menu['title'],selected=e._vessel_menu['selected'],options=[r[0] for r in e._vessel_menu['options']]),
            decor=[dict(x=x,y=y,id=d) for (x,y),d in m.decor.items()],
            reader=dict(open=e.text_reader.open,text_id=getattr(e.text_reader,'_text_id',None),definition=getattr(e.text_reader,'_def',None)),
            floor=[dict(x=x,y=y,items=[observed_item(i) for i in rows]) for (x,y),rows in m.floor_objects.items()],
            containers=[dict(x=x,y=y,state=c['state'],items=[observed_item(i) for i in c['items']]) for (x,y),c in m.container_state.items()],
            actors=[dict(id=creature_id(a),x=a.x,y=a.y,hp=a.fighter.hp if a.fighter else None,ai=str(getattr(getattr(a,'ai',None),'state',None))) for a in e.entities if a is not e.player],
            terrain=[[str(m.tiles[x,y]['terrain']) for x in range(m.width)] for y in range(m.height)],
            walkable=m.walkable.T.tolist(),
            save_path=str(e.save_manager.save_path),save_error=str(e.save_manager.last_error),
            logs=[msg.text for msg in e.log.messages][-8:])
        try:write_json(self.root/'observation.json',observation)
        except PermissionError:return  # A diagnostic reader may briefly lock it on Windows.
        command_path=self.root/'event.json'
        if not command_path.is_file():return
        try: command=json.loads(command_path.read_text(encoding='utf-8'))
        except (ValueError,OSError):return
        if command.get('id')==self.applied:return
        # Disclosed, once-only verification setup. Effects and action accounting
        # after this point run through ordinary game input/handlers unchanged.
        if command.get('fixture')=='supplies-injured' and not self.fixture_applied:
            e.player.needs.hunger=e.player.needs.thirst=.8
            e.player.fighter.hp=max(1,e.player.fighter.max_hp-15)
            self.fixture_applied=True
        if command.get('fixture')=='preparation-heat' and not self.fixture_applied:
            # Focused heat fixture, not room-decor authoring. All subsequent
            # selection, placement, commitment, ticking and use run normally.
            from generation.decor_utils import place_decor
            place_decor(e.local_map,e.player.x,e.player.y-1,'campfire_lit')
            e.player.needs.hunger=e.player.needs.thirst=.8
            e.player.fighter.hp=max(1,e.player.fighter.max_hp-15)
            self.fixture_applied=True
        if (command.get('fixture')=='coating-contact-targets' and not self.fixture_applied
                or command.get('fixture')=='coating-contact-targets-reset'):
            # Disclosed packaged contact/expiry fixture only. Keep real attack,
            # essence, armour and body consumers; remove target movement and
            # extend life so every contact can be observed without replacing RNG.
            for actor in e.entities:
                if actor is not e.player and actor.fighter:
                    actor.ai=None
                    actor.fighter.max_hp=actor.fighter.hp=1000
            self.fixture_applied=True
        if command.get('capture'):
            pygame.image.save(screen,str(self.root/'frame.png'))
        key=command.get('key')
        if isinstance(key,str):
            code=pygame.key.key_code(key)
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=code,unicode=command.get('text','')))
            pygame.event.post(pygame.event.Event(pygame.KEYUP,key=code))
        self.applied=command.get('id')
