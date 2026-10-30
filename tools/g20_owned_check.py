"""Cold ownership audit and an isolated real-combat block with the acquired Ward."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--route',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--branch',choices=['lure','musk'],required=True);p.add_argument('--block',action='store_true');a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    import config
    config.DEBUG_MODE=False
    from test_effect_persistence import make_engine,load_data
    from test_gameplay_g12 import use
    from g12_journey import install_checkpoint,snapshot
    from engine.save_manager import _serialize_entity
    route=json.loads(a.route.read_text())['chosen'];target=route['target']
    record=dict(branch=a.branch,pid=os.getpid(),checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),scope='Cold exact checkpoint/owned scene audit; optional block is a separate controlled fixture, not natural encounter balance.')
    with tempfile.TemporaryDirectory(prefix='g20-owned-') as root,patch('engine.save_manager.SAVE_DIR',Path(root)):
        install_checkpoint(a.checkpoint,root);e=make_engine(load_data());e.debug=None
        assert e.save_manager.load(e),e.save_manager.last_error
        expected=json.loads(a.checkpoint.with_suffix('.json').read_text());assert snapshot(e)==expected
        record['cold_snapshot']=snapshot(e)
        inv=e.player.inventory;ward=inv.get_by_id('faceted_ward')
        assert ward and sum(i.item_id=='faceted_ward' for i in inv.items)==1
        assert e.player.equipment.slots['offhand'].item_id=='tallow_torch'
        assert e.player.light_source.active and e.player.light_source._item_ref is e.player.equipment.slots['offhand']
        assert inv.has('musk_pellet')==(a.branch=='lure')
        assert inv.has('flint_shard')==(a.branch=='musk')
        e.save_manager.cache.evict_distant(10,10)
        with patch('engine.scene_generation.create_submap',side_effect=AssertionError('must load altered owned room')):
            m,actors=e._prepare_destination(*target)
        assert not any(i.item_id in ('faceted_ward','letter') for rows in m.floor_objects.values() for i in rows)
        record['altered_room']=dict(actors=[_serialize_entity(x) for x in actors],zones=copy.deepcopy(m.disruption_zones),containers=[dict(position=list(xy),state=row['state'],items=[i.item_id for i in row['items']]) for xy,row in m.container_state.items()],reward_absent=True,clue_absent=True)
        # The finite workshop crate remains depleted after cold return.
        with patch('engine.scene_generation.create_surface',side_effect=AssertionError('must load depleted owned workshop')):
            workshop,_=e._prepare_destination(75,100)
        selected=next(p for p in e.world_map.plan['placements'] if p['asset']=='workshop_c' and p['id']=='settlement-0-cross-market-lot-1-44-S-0-building')
        ox,oy=selected['origin'][0]%80,selected['origin'][1]%43
        assert not workshop.container_state[ox+9,oy+6]['items']
        assert (ox+2,oy+2) not in workshop.container_state
        record['workshop']=dict(travel_crate_empty=True,material_crate_dismantled=True)
        if a.block:
            assert not [x for x in e.entities if x is not e.player],'Controlled positive starts in the genuinely returned empty laboratory'
            # Only this isolated continuation stages a clear patch and attacker.
            # The shield and player HP remain those genuinely returned above.
            use(e,ward);assert e.player.equipment.slots['offhand'] is ward and not e.player.light_source.active
            for x in range(e.player.x-1,e.player.x+3):
                for y in range(e.player.y-1,e.player.y+2):e.local_map.set_tile(x,y,'floor',True,True);e.local_map.decor.pop((x,y),None)
            guard=e.creature_factory.spawn('hollow_revenant',e.player.x+1,e.player.y);e.entities.append(guard)
            e.reality_bubble.update(e.world_x,e.world_y,e.world_map);e.rng=random.Random(29417)
            import engine.combat as combat
            resolve=combat.resolve_attack;results=[]
            def observed(**kwargs):
                result=resolve(**kwargs);results.append(dict(blocked=result.blocked,reduction=result.block_reduction,damage=result.damage_dealt,hit=result.hit));return result
            hp=e.player.fighter.hp;turn=e.world_time.turn
            with patch.object(e.rng,'random',return_value=.1),patch.object(combat,'resolve_attack',new=observed):
                for _ in range(2):e._advance_turn()
            assert len(results)==1 and results[0]['blocked'] and results[0]['reduction']==2,results
            record['controlled_block']=dict(controls='Acquired owned Ward through paid equip. Isolated clear laboratory patch and one factory adjacent Revenant. Actual two normal speed-budget world phases and real attack resolver. RNG.random fixed at 0.1 to select a positive block, ordinary dice RNG retained. No balance claim.',results=results,hp_before=hp,hp_after=e.player.fighter.hp,phases=e.world_time.turn-turn)
    record['passed']=True;a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(passed=True,branch=a.branch,controlled_block=record.get('controlled_block'),output=str(a.output))))


if __name__=='__main__':main()
