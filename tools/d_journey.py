"""D actual Engine.run/render journeys; only paired app-local Pygame events."""
from d_cases import fixture,equip,enemy,make


def run_journey(ev):
    import pygame
    from b1_journey import run_journey as drive
    def actions(e,key,capture,choose):
        fixture(e);p=e.player;inv=p.inventory;v=ev.job['variant']
        if v=='confirmation':
            item=make(e,'wight_concentrate');inv.add(item);start=e.world_time.turn
            for cancel in (True,False):
                yield key(pygame.K_i,'i');yield from choose(e,item);yield key(pygame.K_RETURN,'\r')
                ev.check('D-11','inventory yields to confirmation without spending a turn',[False,start],[e.inventory_screen.open,e.world_time.turn])
                capture('d-confirm-prompt')
                yield key(pygame.K_n if cancel else pygame.K_y,'n' if cancel else 'y')
                ev.check('D-11','app-local confirm/cancel ownership',cancel,inv.contains(item))
            ev.check('D-11','app-local confirmation sight and clock',[True,19,start+1],[p.true_sight,e.true_sight_turns,e.world_time.turn])
            yield key(pygame.K_h,'h');capture('d-true-sight-health');yield key(pygame.K_h,'h')
            yield key(pygame.K_F5);yield key(pygame.K_F9)
            ev.check('D-11','event save/load retains effect',[True,19],[e.player.true_sight,e.true_sight_turns])
        elif v=='throw':
            item=make(e,'musk_pellet');inv.add(item);a=enemy(e, x=20,y=18);start=e.world_time.turn;hp=p.fighter.hp
            for cancel in (True,False):
                yield key(pygame.K_i,'i');yield from choose(e,item);yield key(pygame.K_RETURN,'\r')
                ev.check('D-11','throw targeting is a free modal',[start,'placement_cursor'],[e.world_time.turn,e.mode.value])
                capture('d-throw-cursor')
                if cancel:yield key(pygame.K_ESCAPE)
                else:
                    yield key(pygame.K_UP);yield key(pygame.K_RETURN,'\r')
            ev.check('D-11','throw applies zone and pauses enemy',[False,5,hp],[inv.contains(item),e.local_map.disruption_zones[0]['turns_remaining'],p.fighter.hp])
            capture('d-zone-active')
            yield key(pygame.K_F5);yield key(pygame.K_F9)
            for _ in range(5):yield key(pygame.K_z,'z')
            ev.check('D-11','loaded zone expires through real events',[],e.local_map.disruption_zones)
            capture('d-zone-expired')
        elif v=='movement':
            item=make(e,'stalker_unguent');inv.add(item)
            yield key(pygame.K_i,'i');yield from choose(e,item);yield key(pygame.K_RETURN,'\r');yield key(pygame.K_i,'i')
            start=e.world_time.turn
            for k in [pygame.K_RIGHT,pygame.K_LEFT]*3:yield key(k)
            ev.check('D-11','real event salve movement earns one skipped phase',[5,9],[e.world_time.turn-start,e.player_speed_bonus_turns])
            capture('d-salve-movement')
            yield key(pygame.K_F5);yield key(pygame.K_F9)
            for _ in range(9):yield key(pygame.K_z,'z')
            ev.check('D-11','salve expires via real waits',[0,0],[e.player_speed_bonus,e.player_speed_bonus_turns])
        elif v=='combat':
            armor=equip(e,'leather_jack');blade=equip(e,'binding_knife');a=enemy(e,'barrow_wight')
            seal=make(e,'marrow_seal');inv.add(seal)
            yield key(pygame.K_i,'i');yield from choose(e,seal);yield key(pygame.K_RETURN,'\r');yield key(pygame.K_i,'i')
            ev.check('D-11','armor charges spent by real AI contact',True,armor._temp_av_hits<20)
            blade.temporary_essence=[dict(essence='Revelation',strength=.5,hits_remaining=1)]
            yield key(e.display.MOVESET_KEY_1,'q')
            ev.check('D-11','moveset real event applies suppression and coating expiry',[4,[]],[a._ability_suppressed_turns,blade.temporary_essence])
            capture('d-combat-suppressed')
            yield key(pygame.K_F5);yield key(pygame.K_F9)
            ev.check('D-11','event combat checkpoint restores active counter',4,next(a for a in e.entities if a is not e.player)._ability_suppressed_turns)
        else:raise AssertionError(v)
    drive(ev,actions)
