"""C journeys reuse the bounded original-loop driver and real event queue."""
from c_cases import fixture, make, check_owner


def run_journey(ev):
    import pygame
    from b1_journey import run_journey as drive
    from generation.floor_object_utils import place_floor_object,place_container
    def actions(e,key,capture,choose):
        fixture(e)
        p,inv=e.player,e.player.inventory
        variant=ev.job['variant']
        if variant=='equipment':
            for iid,slot in [('crude_blade','weapon'),('leather_jack','armor_torso'),('tallow_torch','offhand')]:
                item=make(e,iid);place_floor_object(e.local_map,20,20,item)
                yield key(pygame.K_COMMA,',')
                check_owner(ev,e,item,'inventory',case='C-08')
                yield key(pygame.K_i,'i');yield from choose(e,item)
                yield key(pygame.K_RETURN,'\r')
                check_owner(ev,e,item,'inventory',[slot],case='C-08')
                yield key(pygame.K_d,'d')
                check_owner(ev,e,item,'floor',case='C-08')
                ev.check('C-08','drop removes armor and light',[0,None],[p.fighter.effective_av,p.light_source])
                capture('c-drop-'+iid)
                yield key(pygame.K_i,'i')
                yield key(pygame.K_COMMA,',')
                check_owner(ev,e,item,'inventory',case='C-08')
            yield key(pygame.K_F5)
            ev.check('C-08','event save published',True,e.save_manager.generation is not None)
            yield key(pygame.K_F9)
            ev.check('C-08','event reload retains three unequipped items',3,len(p.inventory.items))
        elif variant=='take-all':
            a=make(e,'crow_jerky',weight=1,name='fits')
            b=make(e,'crude_blade',weight=5,name='too heavy')
            corpse=make(e,'corpse',source_creature='hollow_revenant')
            inv.capacity=1
            for item in (a,b,corpse):place_floor_object(e.local_map,20,20,item)
            yield key(pygame.K_COMMA,',')
            for _ in range(3):yield key(pygame.K_DOWN)
            yield key(pygame.K_RETURN,'\r')
            check_owner(ev,e,a,'inventory',case='C-08')
            check_owner(ev,e,b,'floor',case='C-08')
            check_owner(ev,e,corpse,'floor',case='C-08')
            ev.check('C-08','take-all retains rejected and skipped items',2,len(e.local_map.floor_objects[(20,20)]))
            capture('c-take-all-partial')
        elif variant=='container':
            a,b=[make(e,'tallow_torch',turns_lit=n,name='torch '+str(n)) for n in (11,77)]
            decor=next(k for k,v in e.data.decoratives.items() if v.get('interactable')=='container')
            place_container(e.local_map,20,19,decor,[a,b])
            # The normal interaction key opens a cursor; choose the north tile.
            yield key(pygame.K_e,'e')
            yield key(pygame.K_UP)
            yield key(pygame.K_RETURN,'\r')
            ev.check('C-08','normal container browse opened',True,e.interaction_cursor._selection_prompt is not None)
            yield key(pygame.K_DOWN)
            yield key(pygame.K_RETURN,'\r')
            check_owner(ev,e,b,'inventory',case='C-08')
            check_owner(ev,e,a,'container',case='C-08')
            ev.check('C-08','selected duplicate preserves own fuel',77,b.turns_lit)
            capture('c-container-second-instance')
        elif variant=='craft':
            wood=[make(e,'wood_bundle') for _ in range(2)]
            blade=make(e,'crude_blade');inv.items=wood+[blade]
            for cancel in (True,False):
                yield key(pygame.K_c,'c')
                for _ in range(80):
                    flat=e.craft_screen._build_flat_items(e.craft_screen._get_recipes(e))
                    index=next(n for n,row in enumerate(flat) if row.get('recipe',{}).get('id')=='campfire')
                    if e.craft_screen.selected==index:break
                    yield key(pygame.K_DOWN if e.craft_screen.selected<index else pygame.K_UP)
                yield key(pygame.K_RETURN,'\r')
                ev.check('C-08','craft UI opens placement without spending materials',True,inv.items==wood+[blade] and e.mode.value=='placement_cursor')
                if cancel:
                    yield key(pygame.K_ESCAPE)
                    ev.check('C-08','app-local cancellation retains exact owners',True,inv.items==wood+[blade])
                    capture('c-craft-cancelled')
                else:
                    yield key(pygame.K_RETURN,'\r')
                    ev.check('C-08','app-local confirmation consumes fuel once',True,inv.items==[blade] and e.local_map.decor.get((20,19))=='campfire_unlit')
                    capture('c-craft-completed')
    drive(ev,actions)
