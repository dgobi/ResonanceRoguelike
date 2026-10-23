"""B3 behavioral oracles: production bootstrap, filesystem faults and real loop."""
from pathlib import Path
import copy
import json
import os
import pickle
import subprocess
import sys
import time
from b1_support import hashes, dump, read, seed_runtime
from b2_cases import quiet


def committed(sm):
    return {'head': (sm.save_path / 'HEAD.json').read_text(),
            'generation': hashes(sm.checkpoint_path())}


def checkpoint(e, ev, name='save'):
    ev.check('B3-01', name, True, e.save_manager.save(e))


def snapshot(e):
    other = e.save_manager.cache.load(e.world_x+1, e.world_y)
    return {'marker': str(e.local_map.tiles[3, 3]['terrain']), 'hp': e.player.fighter.hp,
            'turn': e.world_time.turn, 'world_name': e.world_map.get(e.world_x,e.world_y).name,
            'timer': e.true_sight_turns, 'inactive': None if other is None else str(other.local_map.tiles[3,3]['terrain'])}


def fixture(e, newer=False):
    from world.local_map import LocalMap
    quiet(e)
    e.local_map.set_tile(3, 3, 'dirt' if newer else 'grass', True, True)
    e.player.fighter.hp = 33 if newer else 41
    e.world_time.turn = 19 if newer else 7
    e.true_sight_turns = 11 if newer else 17
    e.world_map.get(e.world_x,e.world_y).name = 'new checkpoint' if newer else 'old checkpoint'
    wx, wy = e.world_x+1, e.world_y
    other = e.save_manager.cache.load(wx, wy)
    if other is None:
        m = LocalMap(80,43)
        e.save_manager.cache.store(wx,wy,m,[])
        other = e.save_manager.cache.load(wx,wy)
    other.local_map.set_tile(3,3,'mud' if newer else 'grass',True,True)


def reseal(root):
    """Author a malformed but checksum-consistent semantic fixture, never a repair."""
    from engine.checkpoints import record
    manifest = read(root/'manifest.json')
    manifest['files'] = {p.relative_to(root).as_posix():record(p.read_bytes())
                         for p in root.rglob('*') if p.is_file() and p.name!='manifest.json'}
    dump(root/'manifest.json',manifest)


def run_case(e, ev):
    from engine.save_manager import SaveManager, ChunkCache, CachedChunk
    from engine.checkpoints import CheckpointStore, slot_lock
    sm = e.save_manager
    case, phase, variant = ev.job['scenario'], ev.job['phase'], ev.job['variant']
    if case == 'coherence':
        if phase in ('write','same'):
            fixture(e)
            # Mutate inactive layers in place, without any dirty notification.
            other = sm.cache.load(e.world_x+1,e.world_y)
            other.local_map.processing_layer[(6,6)] = dict(item_id='dried_bitter_herb', turns_remaining=2, decor_id='', source='drying')
            other.local_map.floor_objects[(7,7)] = [e.item_factory.create('crow_jerky')]
            other.local_map.container_state[(8,8)] = {'items':['fixture'], 'looted':True}
            other.local_map.decor[(8,8)] = 'shelf'
            other.local_map.explored[2,2] = True
            a=e.creature_factory.spawn('hollow_revenant',10,10)
            a.fighter.hp=7
            sm.cache.store_hot_only(e.world_x+1,e.world_y,other.local_map,[a])
            # A cold, evicted owner must also be included.
            from world.local_map import LocalMap
            cold=LocalMap(80,43);cold.set_tile(3,3,'flagstone',True,True)
            sm.cache.store_hot_only(e.world_x+5,e.world_y,cold,[])
            sm.cache.evict_distant(e.world_x,e.world_y)
            ev.check('B3-02','evicted dirty owner removed from hot',False,(e.world_x+5,e.world_y) in sm.cache.hot)
            checkpoint(e,ev)
            ev.record['expected']=snapshot(e)
            ev.record['checkpoint']=hashes(sm.save_path)
            ev.record['committed']=committed(sm)
            if phase=='write': return
            fixture(e,True)
            # These are actual travel writes; only session files may change.
            e._ascend_from_submap()
            sid=e.world_map.get(e.world_x,e.world_y).submaps[0].submap_id
            e._descend_to_submap(sid)
            ev.check('B3-01','stairs preserve whole committed generation',ev.record['committed'],committed(sm))
            ev.check('B3-01','same-process rollback',True,sm.load(e))
            expected=ev.record['expected']
        else: expected=read(ev.job['expected'])['expected']
        ev.check('B3-01','whole player/world/scene checkpoint',expected,snapshot(e))
        other=sm.cache.load(e.world_x+1,e.world_y)
        ev.check('B3-02','inactive floor/container/decor/exploration/actors retained',
                 ['crow_jerky',{'items':['fixture'],'looted':True},'shelf',True,7],
                 [other.local_map.floor_objects[(7,7)][0].item_id,other.local_map.container_state[(8,8)],other.local_map.decor[(8,8)],bool(other.local_map.explored[2,2]),other.entities[0]['fighter']['hp']])
        ev.check('B3-02','cold evicted scene retained','flagstone',str(sm.cache.load(e.world_x+5,e.world_y).local_map.tiles[3,3]['terrain']))
        e._advance_turn()
        ev.check('B3-02','saved inactive processing resumes',1,other.local_map.processing_layer[(6,6)]['turns_remaining'])
        checkpoint(e,ev,'commit offscreen tick')
        ev.check('B3-02','cold reader sees offscreen tick',1,ChunkCache(sm.save_path).load(e.world_x+1,e.world_y).local_map.processing_layer[(6,6)]['turns_remaining'])
    elif case in ('fault','initial-fault'):
        if phase=='write':
            fixture(e);checkpoint(e,ev)
            ev.record.update(expected=snapshot(e),checkpoint=hashes(sm.save_path))
        elif phase=='crash':
            old=snapshot(e);fixture(e,True);new=snapshot(e)
            def crash(point):
                match=point==variant or (variant=='first_scene' and point.startswith('payload:chunks/'))
                if match:
                    ev.bind_sources(Path(ev.job['game']))
                    dump(ev.job['result'],dict(ev.record,crash_point=point,old=old,new=new,expected_exit=91))
                    os._exit(91)
            sm._checkpoint_fault=crash
            sm.save(e)
            raise AssertionError('Fault boundary not reached: '+variant+' '+str(sm.last_error))
        else:
            record=read(ev.job['expected'])
            ev.check('B3-03','fresh process sees one complete checkpoint',record['new'] if variant=='published' else record['old'],snapshot(e))
            ev.check('B3-03','recovered generation fully validates',True,sm.checkpoint_path().is_dir())
            checkpoint(e,ev,'kernel lock released after killed writer')
    elif case=='recovery':
        fixture(e);checkpoint(e,ev);old=snapshot(e)
        fixture(e,True);checkpoint(e,ev);new=snapshot(e)
        latest=sm.checkpoint_path(); oldgen=read(sm.save_path/'HEAD.json')['previous']
        if variant=='pointer': (sm.save_path/'HEAD.json').write_bytes(b'{truncated')
        elif variant=='active': (latest/'chunks'/f'{e.current_submap_id}.pkl').write_bytes(b'broken')
        elif variant=='inactive': (latest/'chunks'/f'{e.world_x+1}_{e.world_y}.pkl').write_bytes(b'broken')
        elif variant=='manifest':
            manifest=read(latest/'manifest.json');manifest['files']['../escape']={'bytes':0,'sha256':''};dump(latest/'manifest.json',manifest)
        elif variant=='semantic':
            player=read(latest/'player.json');player['weather']=['invalid late weather object']
            dump(latest/'player.json',player);reseal(latest)
        elif variant=='rollback': pass
        elif variant=='all-bad':
            (latest/'player.json').write_bytes(b'broken')
            (sm.save_path/'generations'/oldgen/'player.json').write_bytes(b'broken')
        else: raise ValueError(variant)
        before=hashes(sm.save_path)
        refs=[e.player.inventory,e.player.fighter,e.world_map,e.local_map,e.entities,sm.cache]
        ok=sm.load(e,previous=variant=='rollback')
        if variant=='all-bad':
            ev.check('B3-04','reject when every published generation is bad',False,ok)
            ev.check('B3-04','failed load preserves every live owner',True,all(a is b for a,b in zip(refs,[e.player.inventory,e.player.fighter,e.world_map,e.local_map,e.entities,sm.cache])))
            ev.check('B3-04','failed load preserves current state',new,snapshot(e))
            try: sm.startup_state()
            except ValueError: rejected=True
            else: rejected=False
            ev.check('B3-04','corrupt campaign never becomes a new game',True,rejected)
        else:
            ev.check('B3-04','recover or explicit rollback succeeds',True,ok)
            ev.check('B3-04','recovered complete older state',old,snapshot(e))
            ev.check('B3-04','recovery is visible',True,bool(sm.recovery_notice))
        ev.check('B3-04','recovery/rejection is read-only',before,hashes(sm.save_path))
        if variant!='all-bad':
            checkpoint(e,ev,'save after recovery')
            ev.check('B3-04','new branch derives from recovered checkpoint',oldgen,read(sm.save_path/'HEAD.json')['previous'])
            ev.check('B3-04','fresh startup seed available',('load',e.world_map.seed),sm.startup_state())
    elif case=='io':
        import engine.checkpoints as cp
        fixture(e);checkpoint(e,ev);old=committed(sm)
        fixture(e,True)
        write=cp.write_file
        def failed(path,data):
            if path.name=='player.json':
                write(path,data[:17])
                raise OSError('injected short write / storage full')
            return write(path,data)
        cp.write_file=failed
        try: ev.check('B3-05','write failure returns failure',False,sm.save(e))
        finally: cp.write_file=write
        ev.check('B3-05','failure does not publish',old,committed(sm))
        ev.check('B3-05','failure is reported',True,'storage full' in sm.last_error)
        # Failed eviction must keep the only dirty in-memory owner.
        key=(e.world_x+1,e.world_y);cached=sm.cache.hot[key]
        original=sm.cache._write
        sm.cache._write=lambda *args: (_ for _ in ()).throw(OSError('eviction failure'))
        try: sm.cache.evict_distant(e.world_x+20,e.world_y)
        except OSError: pass
        finally: sm.cache._write=original
        ev.check('B3-05','failed eviction retains dirty entry',True,sm.cache.hot[key] is cached)
        ev.check('B3-05','last committed state survives write error',True,sm.load(e))
        ev.check('B3-05','old player survives write error',41,e.player.fighter.hp)
    elif case=='slots':
        fixture(e);checkpoint(e,ev)
        slot1=SaveManager(1)
        ev.check('B3-06','independent second slot saves',True,slot1.save(e))
        sibling=hashes(slot1.save_path)
        note=sm.save_path.parent/'owner-note.txt';note.write_text('keep')
        e._on_player_death()
        ev.check('B3-06','actual death retires only selected slot',False,sm.save_path.exists())
        ev.check('B3-06','other campaign untouched',sibling,hashes(slot1.save_path))
        ev.check('B3-06','unrelated saves-root file untouched','keep',note.read_text())
        ev.check('B3-06','restart is new in retired slot',('new',None),sm.startup_state())
        import pygame
        try: e._handle_key(pygame.K_n)
        except SystemExit as error: ev.check('B3-06','death N exits normally',2,error.code)
        ev.check('B3-06','death quit does not delete sibling',sibling,hashes(slot1.save_path))
        for bad in (-1,True,'../other',1000):
            try: SaveManager(bad)
            except ValueError: rejected=True
            else: rejected=False
            ev.check('B3-06','invalid slot '+repr(bad),True,rejected)
        # A junction must never turn a slot operation into another directory.
        target=sm.save_path.parent/'protected';target.mkdir();(target/'keep').write_text('keep')
        link=sm.save_path.parent/'slot_7'
        if os.name=='nt':
            proc=subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],capture_output=True,text=True,timeout=10)
            ev.check('B3-06','disposable junction fixture created',0,proc.returncode)
        else: link.symlink_to(target,target_is_directory=True)
        try: SaveManager(7).delete_slot()
        except ValueError: rejected=True
        else: rejected=False
        ev.check('B3-06','redirected slot refused',True,rejected)
        ev.check('B3-06','redirect target intact','keep',(target/'keep').read_text())
        # Remove only the verified junction itself (never recurse into its target).
        assert link.parent==sm.save_path.parent and link.name=='slot_7'
        if os.name=='nt': os.rmdir(link)
        else: link.unlink()
    elif case=='concurrency':
        fixture(e);checkpoint(e,ev)
        stale=SaveManager()
        ev.check('B3-07','unloaded manager cannot overwrite existing slot',False,stale.save(e))
        ev.check('B3-07','second manager can load checkpoint',True,stale.load(e))
        fixture(e,True);checkpoint(e,ev)
        ev.check('B3-07','stale writer cannot overwrite newer checkpoint',False,stale.save(e))
        ev.check('B3-07','stale writer diagnostic',True,'another session' in stale.last_error)
        # Simulate a concurrent published-reference change between reconstruction
        # and installation. No live owner may be replaced from that stale read.
        before=committed(sm); refs=(e.local_map,e.player.inventory,e.world_map)
        prepare=sm._prepare
        def changed_during_read(engine,path):
            staged=prepare(engine,path)
            head=read(sm.save_path/'HEAD.json')
            head['current'],head['previous']=head['previous'],None
            from engine.checkpoints import atomic_write,encoded
            atomic_write(sm.save_path/'HEAD.json',encoded(head))
            return staged
        sm._prepare=changed_during_read
        try: ev.check('B3-07','publication race during load rejected',False,sm.load(e))
        finally:
            sm._prepare=prepare
            (sm.save_path/'HEAD.json').write_bytes(before['head'].encode('utf-8'))
        ev.check('B3-07','publication race keeps live owners',True,all(a is b for a,b in zip(refs,(e.local_map,e.player.inventory,e.world_map))))
        marker=Path(ev.job['result']).parent/'locked'
        code="import sys,time;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from engine.checkpoints import slot_lock\nwith slot_lock(Path(sys.argv[2])):\n Path(sys.argv[3]).write_text('locked');time.sleep(45)"
        proc=subprocess.Popen([sys.executable,'-c',code,ev.job['game'],str(sm.save_path),str(marker)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+10
            while not marker.exists() and time.monotonic()<deadline: time.sleep(.05)
            ev.check('B3-07','separate process holds kernel lock',True,marker.exists())
            ev.check('B3-07','simultaneous writer refused',False,sm.save(e))
            ev.check('B3-07','busy diagnostic',True,'busy' in sm.last_error)
        finally: proc.kill();proc.communicate(timeout=10)
        checkpoint(e,ev,'lock automatically released by process death')
        # A competing writer publishes immediately after our lock is released.
        # The manager must retain its OWN publication token, then reject its
        # next write until it has loaded the intervening checkpoint.
        publish=sm.store.publish
        competing={}
        def publish_then_compete(*args,**kwargs):
            result=publish(*args,**kwargs)
            generation,path,token=result
            payloads={p.relative_to(path).as_posix():p.read_bytes() for p in path.rglob('*') if p.is_file() and p.name!='manifest.json'}
            competing['result']=CheckpointStore(sm.save_path).publish(payloads,generation,token)
            return result
        sm.store.publish=publish_then_compete
        try: checkpoint(e,ev,'original publication returns after competing publication')
        finally: sm.store.publish=publish
        ev.check('B3-07','save retains its own token',False,sm._head_token==sm.store.token())
        ev.check('B3-07','post-publication race cannot overwrite competing save',False,sm.save(e))
        ev.check('B3-07','competing publication remains selected',competing['result'][0],read(sm.save_path/'HEAD.json')['current'])
    elif case=='legacy':
        before=hashes(sm.save_path)
        ev.check('B3-08','real pre-B3 flat checkpoint bootstraps',None,sm.generation)
        ev.check('B3-08','legacy load reconstructs configured Needs',True,e.player.needs._configured)
        ev.check('B3-08','legacy slot is not silently migrated',False,sm.save(e))
        ev.check('B3-08','migration refusal explains policy',True,'read-only' in sm.last_error)
        ev.check('B3-08','legacy bytes unchanged',before,hashes(sm.save_path))
    else: raise ValueError(case)


def first_crash(ev):
    import main  # bind actual bootstrap/Engine source without entering play
    from engine.save_manager import SaveManager
    sm=SaveManager()
    ev.record['evidence_class']='Actual startup-state API, no Engine.run or new-game reconstruction'
    ev.check('B3-03','unpublished first generation never becomes a checkpoint',False,sm.save_exists())
    if ev.job['variant']=='stage_created':
        ev.check('B3-03','partial first-write permits deliberate seed start',('new',20261020),sm.startup_state())
    else:
        try: sm.startup_state()
        except ValueError: rejected=True
        else: rejected=False
        ev.check('B3-03','sealed unpublished generation is preserved, never auto-promoted or erased',True,rejected)


def run_journey(ev):
    """Real F5, stair keys, F9 and wait through the original game loop."""
    import pygame
    import main
    from engine.engine import Engine
    original_run,original_get=Engine.run,pygame.event.get
    current={};done=False;frames=0;started=time.monotonic()
    def key(k,unicode='',mod=0): return dict(key=k,unicode=unicode,mod=mod)
    def actions(e):
        if ev.job['variant']=='debug-delete':
            from engine.save_manager import SaveManager
            fixture(e);checkpoint(e,ev)
            sibling=SaveManager(1)
            ev.check('B3-06','debug journey second campaign saved',True,sibling.save(e))
            other=hashes(sibling.save_path)
            yield key(pygame.K_F1)
            yield None
            image=Path(ev.job['result']).parent/'b3-debug-help.png'
            pygame.image.save(pygame.display.get_surface(),str(image));ev.record['captures']=[str(image)]
            yield key(pygame.K_F11)
            ev.check('B3-06','actual F11 retires selected slot',False,e.save_manager.save_path.exists())
            ev.check('B3-06','actual F11 preserves other campaign',other,hashes(sibling.save_path))
            return
        fixture(e)
        # Position at the real authored stair. Fixtures change no action handlers.
        coords=[(x,y) for x in range(e.local_map.width) for y in range(e.local_map.height)
                if str(e.local_map.tiles[x,y]['terrain'])=='stairs_up']
        assert coords
        e.player.x,e.player.y=coords[0];e._update_fov()
        yield key(pygame.K_F5)
        ev.check('B3-09','real F5 publishes checkpoint',True,e.save_manager.save_exists())
        saved=committed(e.save_manager);expected=snapshot(e)
        fixture(e,True)
        e.player.x,e.player.y=coords[0]
        yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
        ev.check('B3-09','real stair ascent reaches surface',None,e.current_submap_id)
        yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
        ev.check('B3-09','real stair descent reaches lab',True,e.current_submap_id is not None)
        ev.check('B3-09','travel never changes the F5 checkpoint',saved,committed(e.save_manager))
        yield key(pygame.K_F9)
        ev.check('B3-09','real F9 restores coherent checkpoint',expected,snapshot(e))
        # Publish B, corrupt it in this disposable root, then recover A via F9.
        fixture(e,True)
        yield key(pygame.K_F5)
        (e.save_manager.checkpoint_path()/'player.json').write_bytes(b'{interrupted')
        yield key(pygame.K_F9)
        ev.check('B3-09','real F9 recovers old whole checkpoint',expected,snapshot(e))
        ev.check('B3-09','real-loop recovery notice visible',True,bool(e.save_manager.recovery_notice))
        yield None
        image=Path(ev.job['result']).parent/'b3-recovery.png'
        pygame.image.save(pygame.display.get_surface(),str(image));ev.record['captures']=[str(image)]
        before=e.world_time.turn
        yield key(pygame.K_z,'z')
        ev.check('B3-09','recovered game continues actual turns',before+1,e.world_time.turn)
    def run(e):
        current['engine']=e;seed_runtime(e);current['actions']=actions(e)
        return original_run(e)
    def events(*args,**kwargs):
        nonlocal done,frames
        assert frames<100 and time.monotonic()-started<90
        e=current['engine']
        ev.check('B3-09','offscreen original loop','dummy',pygame.display.get_driver())
        ev.record['trace'].append(dict(frame=frames,turn=e.world_time.turn,scene=e.current_submap_id,hp=e.player.fighter.hp))
        try: event=next(current['actions'])
        except StopIteration:
            done=True;pygame.event.post(pygame.event.Event(pygame.QUIT))
        else:
            if event:
                pygame.key.set_mods(event['mod'])
                for kind in (pygame.KEYDOWN,pygame.KEYUP):
                    ev.check('B3-09','app-local event accepted',True,pygame.event.post(pygame.event.Event(kind,**event)))
        frames+=1
        return original_get(*args,**kwargs)
    Engine.run,pygame.event.get=run,events
    try: main.main()
    except SystemExit as error:
        if not done or error.code not in (0,None): raise
    finally:
        Engine.run,pygame.event.get=original_run,original_get
        pygame.quit()
    ev.check('B3-09','original loop completed',True,done)
