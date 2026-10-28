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

    def frame(self,e,screen):
        from room_test import write_json
        if not self._counting:
            advance=e._advance_turn
            def counted():
                self.action_calls+=1
                return advance()
            e._advance_turn=counted
            self._counting=True
        def observed_item(item):
            return dict(serialize_item(item),instance=str(id(item)))
        m=e.local_map
        inv=e.inventory_screen
        observation=dict(applied=self.applied,pid=__import__('os').getpid(),player=[e.player.x,e.player.y],
            turn=e.world_time.turn,submap=e.current_submap_id,surface_return=[e.surface_return_x,e.surface_return_y],
            dead=e._player_is_dead,mode=e.mode.name,visible=int(m.tiles['visible'].sum()),
            light=bool(getattr(e.player,'light_source',None) and e.player.light_source.active),
            inventory=[observed_item(i) for i in e.player.inventory.items],
            action_calls=self.action_calls,fixture_applied=self.fixture_applied,
            needs=dict(hunger=e.player.needs.hunger,thirst=e.player.needs.thirst),hp=e.player.fighter.hp,max_hp=e.player.fighter.max_hp,
            inventory_open=inv.open,inventory_selected=inv.selected,
            inventory_rows=[dict(item_id=getattr(item,'item_id',None),instance=str(id(item)) if item else None,header=header,label=label) for item,header,label in inv._flat],
            reader=dict(open=e.text_reader.open,text_id=getattr(e.text_reader,'_text_id',None),definition=getattr(e.text_reader,'_def',None)),
            floor=[dict(x=x,y=y,items=[observed_item(i) for i in rows]) for (x,y),rows in m.floor_objects.items()],
            containers=[dict(x=x,y=y,state=c['state'],items=[serialize_item(i) for i in c['items']]) for (x,y),c in m.container_state.items()],
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
        if command.get('capture'):
            pygame.image.save(screen,str(self.root/'frame.png'))
        key=command.get('key')
        if isinstance(key,str):
            code=pygame.key.key_code(key)
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=code,unicode=command.get('text','')))
            pygame.event.post(pygame.event.Event(pygame.KEYUP,key=code))
        self.applied=command.get('id')
