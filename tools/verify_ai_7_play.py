"""AI-7 actual saved-room entry and ordinary keys. Fixed RNG; no injected combat.

Focused fixtures cover adversarial setup separately. These encounters use shipped
room geometry, ordinary orders/movement/Wait, actual attacks and disposable saves.
"""
import argparse,json,os,sys,tempfile,zipfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools')]
from verify_ai_6_play import setup,snapshot,capture,display,Session,legacy as legacy_v4
import pygame


def order(s,hold):
    before=s.e.world_time.turn
    s.key(pygame.K_e);s.key(pygame.K_RETURN)
    assert s.e.interaction_cursor._order_prompt is not None,'adjacent escort prompt'
    assert s.e.world_time.turn==before,'opening order is free'
    if hold:s.key(pygame.K_DOWN)
    s.key(pygame.K_RETURN)
    assert s.e.world_time.turn==before+1,'one accepted order = one phase'


def lane(out):
    reports=[]
    for hold in (False,True):
        with tempfile.TemporaryDirectory(prefix='resonance-ai7-lane-') as temp:
            s=setup(temp,'ai7_escort_lane',out);e=s.e;a=e.entities[1];origin=[a.x,a.y]
            order(s,hold)
            for _ in range(3):s.key(pygame.K_LEFT)
            s.checkpoint('hold' if hold else 'follow')
            a=e.entities[1]
            assert a.ai.escort['order']==('hold' if hold else 'follow')
            if hold:assert [a.x,a.y]==origin
            else:assert [a.x,a.y]!=origin
            capture(e,out/('hold-lane.png' if hold else 'follow-lane.png'))
            reports.append(s.report())
    return dict(passed=True,comparison=reports)


def threat(out):
    reports=[]
    for hold in (True,False):
        with tempfile.TemporaryDirectory(prefix='resonance-ai7-threat-') as temp:
            s=setup(temp,'ai7_escort_threat',out);e=s.e;a=e.entities[1];ox,oy=a.x-6,a.y-5
            order(s,hold)
            # Approach the existing territorial guard; then withdraw through the
            # escort's physical area. The order changes its resulting exposure.
            s.move(8+ox,5+oy)
            for _ in range(4):s.key(pygame.K_PERIOD)
            # Save/load comparisons are pure state witnesses. Preserve this
            # controlled encounter's fixed combat/AI RNG stream across F9;
            # no attack result or runtime decision is injected.
            combat_rng,ai_rng=e.rng.getstate(),e.ai_system._rng.getstate()
            s.checkpoint('ongoing_threat_hold' if hold else 'ongoing_threat_follow')
            e.rng.setstate(combat_rng);e.ai_system._rng.setstate(ai_rng)
            for _ in range(2):s.key(pygame.K_PERIOD)
            s.move(4+ox,5+oy)
            for _ in range(12):s.key(pygame.K_PERIOD)
            s.checkpoint('threat_hold' if hold else 'threat_follow')
            capture(e,out/('hold-threat.png' if hold else 'follow-threat.png'))
            r=s.report();r['hold']=hold;reports.append(r)
    assert reports[0]['final']!=reports[1]['final']
    assert any('strikes at the' in msg for r in reports for row in r['rows'] for msg in row['logs']),'ordinary nonplayer attack'
    assert any(any(a['fighter']['hp']<a['fighter']['max_hp'] or not a['is_alive'] for a in r['final']['actors']) for r in reports),'actual allied/hostile damage'
    return dict(passed=True,comparison=reports,staging='Fixed saved-room entry and RNG 17/19; no attack, damage, perception or AI overrides.')


def passage(out):
    with tempfile.TemporaryDirectory(prefix='resonance-ai7-passage-') as temp:
        s=setup(temp,'ai7_escort_lane',out);e=s.e;a=e.entities[1];hp=a.fighter.hp
        start=[e.player.x,e.player.y];turn=e.world_time.turn
        s.key(pygame.K_RIGHT)
        assert [e.player.x,e.player.y]!=start and e.world_time.turn==turn+1 and a.fighter.hp==hp
        assert (e.player.x,e.player.y)!=(a.x,a.y)
        # Door opens as a paid ordinary action; side route/occlusion is explored
        # with real movement. No hidden coordinate is supplied to the escort.
        ox,oy=e.player.x-6,e.player.y-5
        s.move(9+ox,5+oy)
        s.move(10+ox,2+oy)
        s.move(6+ox,1+oy)
        s.move(5+ox,5+oy)
        s.checkpoint('passage_and_sight_loss')
        # Successful departure keeps the ally in the cached room; ordinary
        # return must not spawn another instance or heal the old one.
        from engine.save_manager import _serialize_entity
        old=[_serialize_entity(x) for x in e.entities if x is not e.player]
        stair=next((x,y) for x in range(e.local_map.width) for y in range(e.local_map.height)
                   if str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
        s.move(*stair)
        old=[_serialize_entity(x) for x in e.entities if x is not e.player]
        e._try_ascend()
        assert e.current_submap_id is None,'ordinary room stair departure'
        assert all(getattr(x,'_creature_id','')!='ash_escort' for x in e.entities)
        for _ in range(3):s.key(pygame.K_PERIOD)
        e._try_descend()
        assert e.current_submap_id=='room-test-instance','ordinary room return'
        a=next(x for x in e.entities if getattr(x,'_creature_id','')=='ash_escort')
        saved=next(x for x in old if x['id']=='ash_escort')
        assert a.fighter.hp==saved['fighter']['hp']
        assert max(abs(a.x-saved['x']),abs(a.y-saved['y']))<=1,'one normal arrival phase only'
        s.checkpoint('revisit')
        return dict(passed=True,play=s.report(),departure_return_preserved=True)


def legacy(out):
    old=ROOT/'evidence/ai-7'
    record=json.loads((old/'legacy-v5-snapshot.json').read_text(encoding='utf8'))
    with tempfile.TemporaryDirectory(prefix='resonance-ai7-v5-read-') as temp:
        with zipfile.ZipFile(old/'legacy-v5-save.zip') as z:z.extractall(temp)
        from room_test import build_engine
        from engine.save_manager import _serialize_entity
        os.chdir(ROOT/'roguelike');config=dict(record['config'],state_root=temp)
        e=build_engine(config,load=True);display(e)
        a=next(a for a in e.entities if getattr(a,'_creature_id','')=='barrow_sentinel')
        assert record['actor']==_serialize_entity(a),'historical v5 actor changed on cold load'
        s=Session(e,config,out);s.checkpoint('historical_source_v5')
        v5=dict(passed=True,actor_exact=True,archive_sha256=hashlib.sha256((old/'legacy-v5-save.zip').read_bytes()).hexdigest(),
            source_revision=record['source_revision'],capture_kind=record['capture_kind'],persistence=s.persistence)
    return dict(passed=True,historical_v5=v5,pre_ai6_v4=legacy_v4(out))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--only',choices=['lane','threat','passage','legacy']);args=ap.parse_args()
    pygame.init();out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    report=dict(passed=False,setup=__doc__,scenarios={})
    for name,fn in [('lane',lane),('threat',threat),('passage',passage),('legacy',legacy)]:
        if args.only and args.only!=name:continue
        report['scenarios'][name]=fn(out)
        (out/'responses.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(name+' passed',flush=True)
    report['passed']=True;(out/'responses.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':main()
