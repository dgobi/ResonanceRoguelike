"""One bounded idle attachment on two ordinary melee hosts; active scene only."""
from __future__ import annotations
import copy
import hashlib
import re
from types import SimpleNamespace
from engine import flesh_resources as food

DEFAULTS = dict(version=1, approach_opportunities=8, feed_opportunities=3)
BOUNDS = dict(approach_opportunities=(1,16), feed_opportunities=(2,8))
HOSTS = ('strike_and_withdraw','territorial_guard')


def configuration(raw, profile, perception, *, complete=False):
    if raw is None: return None
    from engine.enemy_responses import alignment
    alignment(perception)
    if (profile['recipe'] not in HOSTS or profile['capability'] != 'melee'
            or not isinstance(raw,dict) or set(raw)-set(DEFAULTS)
            or complete and set(raw)!=set(DEFAULTS)):
        raise ValueError('enemy_scavenging: supported ordinary melee host and bounded version-1 configuration required')
    result = dict(DEFAULTS, **raw)
    if type(result['version']) is not int or result['version'] != 1:
        raise ValueError('enemy_scavenging: version must be integer 1')
    for key,(lo,hi) in BOUNDS.items():
        if type(result[key]) is not int or not lo <= result[key] <= hi:
            raise ValueError(f'enemy_scavenging.{key}: exact integer {lo}..{hi} required')
    return result


def initialize(ai, config):
    ai.scavenging_config = copy.deepcopy(config)
    ai.scavenging_state = (dict(owner=None,current=None,retired=[],completed=0,last_reason=None)
                           if config is not None else None)
    ai._scavenging_item = None
    ai._scavenging_bound = False


def retire(ai, reason, *, suppress=None):
    s = ai.scavenging_state
    if s is None: return
    c = s['current']
    if c and suppress is not None:
        row = dict(uid=c['uid'],x=c['x'],y=c['y'],route=suppress)
        s['retired'] = [r for r in s['retired'] if r['uid']!=c['uid']][-15:]+[row]
    if c: s['last_reason'] = reason
    s['current'] = None
    ai._scavenging_item = None
    ai._scavenging_bound = False
    if reason in ('scene_departure','foreign_scene'):
        s['retired'] = []


def current_item(ai, engine):
    c = ai.scavenging_state and ai.scavenging_state['current']
    if not c: return None
    # Look only at the last observed location. Never chase hidden relocation.
    items = [i for i in engine.local_map.floor_objects.get((c['x'],c['y']),[])
             if isinstance(getattr(i,'flesh_resource',None),dict) and i.flesh_resource.get('uid')==c['uid']]
    if len(items)!=1: return None
    item=items[0]
    if ai._scavenging_bound and item is not ai._scavenging_item: return None
    if not food.exposed(engine,item,(c['x'],c['y'])) or item.flesh_resource != c['resource']: return None
    ai._scavenging_item=item;ai._scavenging_bound=True
    return item


def in_domain(ai, xy):
    if ai.profile['recipe']!='territorial_guard':return True
    from components.territorial import distance
    anchor=ai.territory['anchor']
    return anchor is not None and distance(anchor,*xy)<=ai.profile['defended_radius']


def refresh(ai, engine, actor, ambient):
    """Lifecycle only. No progress, paid action, target acquisition or clock tick."""
    if ai.scavenging_state is None:return
    from engine.local_rivals import active, living, owner
    from engine.effect_lifecycle import disrupted
    from engine.venom import fully_paralysed
    s=ai.scavenging_state
    if not active(engine,actor) or not living(actor) or s['owner'] not in (None,owner(engine)):
        retire(ai,'foreign_scene');return
    if disrupted(actor,engine.local_map) or fully_paralysed(actor):
        retire(ai,'action_denied');return
    if not s['current']:return
    if not idle_allowed(ai,engine,actor,ambient):
        retire(ai,'higher_priority');return
    item=current_item(ai,engine)
    c=s['current']
    if item is None or not in_domain(ai,(c['x'],c['y'])):
        retire(ai,'resource_lost');return
    if c['feeding'] and not food.contact(engine,actor,(c['x'],c['y'])):
        retire(ai,'contact_lost')


def idle_allowed(ai,engine,actor,ambient):
    """The same admission predicate governs acquisition and retained work."""
    from engine.enemy_components import windows
    from engine.sound import current_interest
    from engine.local_rivals import active,living
    from engine.effect_lifecycle import disrupted
    from engine.venom import fully_paralysed
    sound=current_interest(ai,engine.world_time.turn)
    return (active(engine,actor) and living(actor)
            and not disrupted(actor,engine.local_map) and not fully_paralysed(actor)
            and windows(ai,engine,actor)['idle'] and ai.target is None
            and not (sound and in_domain(ai,(sound['x'],sound['y'])))
            and not (ai.responses and ai.responses['interest'])
            and not (ai.maneuvers and ai.maneuvers['current'])
            and not any(in_domain(ai,(a.x,a.y)) for a in ai._observed(engine,actor,ambient)))


def signature(engine,actor,xy):
    """Local route-change discriminator; mandatory return cannot rearm it."""
    m=engine.local_map;x,y=xy;r=16
    occupied={(a.x,a.y) for a in engine.entities if a is not actor and getattr(a,'blocks_movement',False)}
    cells=[(px,py,str(m.tiles[px,py]['terrain']),bool(m.walkable[px,py]),
            bool(m.transparent[px,py]),engine._decor_blocks_movement(px,py),(px,py) in occupied)
           for px in range(max(0,x-r),min(m.width,x+r+1))
           for py in range(max(0,y-r),min(m.height,y+r+1))]
    return hashlib.sha256(repr(cells).encode()).hexdigest()


def route(ai,engine,actor,xy):
    return ai._route(engine,actor,lambda x,y: food.contact(engine,SimpleNamespace(x=x,y=y),xy),
                     forbidden=(xy,) if (actor.x,actor.y)!=xy else ())


def choose(ai,engine,actor,ambient):
    """Called after host housekeeping, hostile commitments, reactions and sound."""
    if ai.scavenging_state is None:return None
    from engine.local_rivals import owner,allocate
    from components.ai import creature_can_see_point
    refresh(ai,engine,actor,ambient)
    if not idle_allowed(ai,engine,actor,ambient):return None
    s=ai.scavenging_state
    if s['owner'] is None:
        allocate(engine,[actor]);s['owner']=owner(engine)
    if s['owner']!=owner(engine):return None
    if s['current'] is None:
        candidates=[]
        for xy,items in engine.local_map.floor_objects.items():
            if not in_domain(ai,xy) or not creature_can_see_point(actor,*xy,engine.local_map,ambient,engine=engine):continue
            for item in items:
                if not food.exposed(engine,item,xy):continue
                uid=item.flesh_resource['uid']
                sig=signature(engine,actor,xy)
                old=next((r for r in s['retired'] if r['uid']==uid),None)
                if (old and (old['x'],old['y'],old['route'])==(*xy,sig)
                        and not food.contact(engine,actor,xy)):continue
                step,length=route(ai,engine,actor,xy)
                if length is None:
                    s['retired']=[r for r in s['retired'] if r['uid']!=uid][-15:]+[dict(uid=uid,x=xy[0],y=xy[1],route=sig)]
                    continue
                candidates.append((length,uid,xy,item))
        if not candidates:return None
        _,uid,xy,item=min(candidates,key=lambda row:(row[0],row[1]))
        s['retired']=[r for r in s['retired'] if r['uid']!=uid]
        s['current']=dict(uid=uid,x=xy[0],y=xy[1],left=ai.scavenging_config['approach_opportunities'],
                          feeding=0,resource=copy.deepcopy(item.flesh_resource))
        ai._scavenging_item=item;ai._scavenging_bound=True
    c=s['current'];xy=c['x'],c['y'];item=current_item(ai,engine)
    if item is None:
        retire(ai,'resource_lost');return None
    if food.contact(engine,actor,xy):
        if c['feeding']+1==ai.scavenging_config['feed_opportunities']:
            def completed():
                s['completed']+=1
                retire(ai,'completed')
            if food.consume(engine,actor,item,xy,completed):
                ai._tell(engine,actor,'strips flesh from the carcass' if item.flesh_resource['kind']=='corpse'
                         else 'finishes a portion of flesh',current_vision=True)
                return 'feed','scavenging_completed',None
            retire(ai,'completion_failed')
            return 'wait','scavenging_completion_failed',None
        c['feeding']+=1
        ai._tell(engine,actor,'bends over exposed flesh',current_vision=True)
        return 'feed','scavenging_feeding',None
    if c['feeding']:
        retire(ai,'contact_lost');return None
    if not c['left']:
        retire(ai,'approach_exhausted',suppress=signature(engine,actor,xy));return None
    c['left']-=1
    step,length=route(ai,engine,actor,xy)
    moved=ai._move(engine,actor,step)
    if not moved or not c['left'] and not food.contact(engine,actor,xy):
        retire(ai,'route_failed' if not moved else 'approach_exhausted',suppress=signature(engine,actor,xy))
    if moved:ai._tell(engine,actor,'noses toward exposed flesh',current_vision=True)
    return ('move' if moved else 'wait'),'scavenging_approach',None


def validate_saved(row, local_map=None):
    composite=row.get('composite',{})
    present='scavenging' in composite or 'scavenging_version' in row
    if not present:return
    if type(row.get('scavenging_version')) is not int or row['scavenging_version']!=1 or 'scavenging' not in composite:
        raise ValueError('scavenging: missing modern attachment')
    b=composite['scavenging']
    if not isinstance(b,dict) or set(b)!={'config','state'} or not isinstance(b.get('config'),dict):
        raise ValueError('scavenging: complete captured config/state required')
    p=configuration(b['config'],composite['profile'],dict(faction=row.get('faction'),hostile_to=row.get('hostile_to')),complete=True)
    s=b['state']
    if not isinstance(s,dict) or set(s)!={'owner','current','retired','completed','last_reason'}:
        raise ValueError('scavenging: incomplete state')
    from engine.local_rivals import OWNER
    from config import MAP_WIDTH,MAP_HEIGHT
    w,h=(local_map.width,local_map.height) if local_map else (MAP_WIDTH,MAP_HEIGHT)
    def point(r):return all(type(r[k]) is int and 0<=r[k]<n for k,n in (('x',w),('y',h)))
    def uid(v):return isinstance(v,str) and re.fullmatch('[0-9a-f]{32}',v) is not None
    if (s['owner'] is not None and (not isinstance(s['owner'],str) or not OWNER.fullmatch(s['owner'])
            or not isinstance(row.get('individual_id'),str) or not row['individual_id'].startswith(s['owner']+':'))
            or type(s['completed']) is not int or not 0<=s['completed']<2**63
            or s['last_reason'] is not None and (not isinstance(s['last_reason'],str) or len(s['last_reason'])>80)
            or not isinstance(s['retired'],list) or len(s['retired'])>16):
        raise ValueError('scavenging: invalid owner, completion or retirement state')
    used=set()
    for r in s['retired']:
        if (not isinstance(r,dict) or set(r)!={'uid','x','y','route'} or not uid(r['uid'])
                or r['uid'] in used or not point(r) or not isinstance(r['route'],str)
                or not re.fullmatch('[0-9a-f]{64}',r['route'])):
            raise ValueError('scavenging: invalid bounded retirement')
        used.add(r['uid'])
    c=s['current']
    if c is not None:
        if (not isinstance(c,dict) or set(c)!={'uid','x','y','left','feeding','resource'} or not uid(c['uid'])
                or not point(c) or type(c['left']) is not int or not 0<=c['left']<=p['approach_opportunities']
                or type(c['feeding']) is not int or not 0<=c['feeding']<p['feed_opportunities']
                or c['uid'] in used or not isinstance(c['resource'],dict) or c['resource'].get('uid')!=c['uid']
                or c['resource'].get('state')=='stripped'
                or s['owner'] is None or composite['state']['target'] is not None
                or composite['state']['phase']!='idle'
                or composite['profile']['recipe']=='territorial_guard' and composite['state']['territory']['phase']!='guard'):
            raise ValueError('scavenging: invalid partial attempt or contradictory host commitment')
        # Validate the captured identity contract without recapturing live tags.
        resource=c['resource'];corpse=resource.get('kind')=='corpse'
        food.validate(dict(item_id='corpse' if corpse else 'saved_portion',count=1,stackable=not corpse,
                           keywords=[] if corpse else [dict(tag='flesh',tier=1)],source_creature=resource.get('source'),
                           decay_timer=resource.get('recipe',{}).get('decay_turns'),
                           flesh_resource_version=1,flesh_resource=resource))
    if s['owner'] is None and (c is not None or s['retired'] or s['completed']):
        raise ValueError('scavenging: unbound state must be fresh')
