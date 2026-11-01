"""Version-4 commitment and permitted cues; actions use CompositeAI authority.

The source remembers its accepted delivery, never polls the victim's dose link.
Diagnostic observations are transient and cannot authorize a resumed decision.
"""
import copy
import re
from types import SimpleNamespace


def bind(ai, engine, application):
    now = engine.world_time.turn
    ai.hunt = dict(version=1, application_id=application.application_id,
                   source_id=application.source_id, owner=ai.target['owner'],
                   delivery_phase=now, first_observation_phase=now+ai.profile['warning_phases']+1,
                   last_useful_phase=now+ai.profile['warning_phases']+ai.profile['paralysis_phases'])


def observe(ai, engine, actor, prey, ambient):
    """Only a current sight check permits the narrow visible symptom query."""
    from engine.local_rivals import owner
    t = ai.target
    retained = t and t['owner']==owner(engine) and (
        prey is engine.player if t['role']=='player' else
        prey is not None and getattr(prey,'_individual_id',None)==t['id'])
    if not retained or prey is None or not ai.sees(engine, actor, prey, ambient):
        return dict(phase=engine.world_time.turn, provenance='direct_sight', cue=None,
                    reason='prey_not_currently_seen')
    from engine.venom import movement_denial
    return dict(phase=engine.world_time.turn, provenance='direct_sight',
                cue='paralysis' if movement_denial(prey) else 'no_paralysis',
                reason='currently_seen_retained_prey')


def return_reason(ai, now):
    if now > ai.hunt['last_useful_phase']:
        return 'hunt_window_expired'
    if now >= ai.hunt['first_observation_phase'] and ai.hunt_evidence['cue'] == 'no_paralysis':
        return 'expected_impairment_absent'
    return None


def monitor(ai, engine, actor, prey, observed, ambient):
    """Select one wait, defensive bite or legal shared route step, never a loop."""
    from engine.venom import movement_denial
    from engine.spatial import melee_attack_legal, melee_contact
    from components.ai import _monster_attack_result, _creature_can_see_player
    tx, ty = ai.target['x'], ai.target['y']  # lawful memory, never hidden live coordinates
    distance = lambda x,y: max(abs(x-tx), abs(y-ty))
    contacts_now = [a for a in observed if melee_contact(engine.local_map,actor.x,actor.y,a.x,a.y)]
    # An intruder can force defensive positioning without becoming the prey.
    far = lambda x,y: (distance(x,y) >= ai.profile['retreat_distance']
                       and all(max(abs(x-a.x),abs(y-a.y)) >= 2 for a in contacts_now))
    seen = prey in observed
    if seen and far(actor.x, actor.y):
        return 'wait', 'watching_for_paralysis', None
    if movement_denial(actor):
        return 'wait', movement_denial(actor), None
    if seen:
        step, length = ai._route(engine, actor, far)
        ai.withdraw_left = max(0, ai.withdraw_left-1)
        if step and ai._move(engine, actor, step):
            if ai.withdraw_left == 0 and not far(actor.x,actor.y):
                ai._retire_target(actor, 'withdrawal_exhausted')
            return 'move', 'monitoring_distance', None
        # Contact is defensive only when no useful retreat exists. Another
        # hostile cannot replace the retained prey or earn a new commitment.
        contacts = [a for a in observed if melee_attack_legal(engine.local_map, actor, a)]
        result = _monster_attack_result(actor, contacts[0], engine, defensive=True) if contacts else None
        if ai.withdraw_left == 0:
            ai._retire_target(actor, 'withdrawal_exhausted')
        return ('melee' if result else 'wait'), 'cornered_defensive' if result else 'blocked_monitor', result
    # Seek sight of the remembered position outside attack contact. The probe
    # contains only that old location, no current victim state or identity.
    memory = SimpleNamespace(x=tx, y=ty, _in_concealment=False)
    probe = copy.copy(actor)
    def observation_position(x,y):
        if distance(x,y) < 2 or (x,y)==(actor.x,actor.y):
            return False
        probe.x, probe.y = x,y
        return _creature_can_see_player(probe, memory, engine.local_map, ambient, engine=engine)
    step, length = ai._route(engine, actor, observation_position)
    # An empty remembered location permits a bounded change of viewpoint.
    # It is not proof of recovery or permission to follow live coordinates.
    ai.approach_left = max(0, ai.approach_left-1)
    ai.no_progress = 0 if length is not None and (ai.best_distance is None or length < ai.best_distance) else min(8,ai.no_progress+1)
    if length is not None:
        ai.best_distance = length
    if ai.approach_left == 0 or ai.no_progress >= 8:
        ai._retire_target(actor, 'reacquisition_exhausted')
        return 'wait', 'reacquisition_exhausted', None
    return ('move' if ai._move(engine, actor, step) else 'wait'), 'evidence_reacquisition', None


def validate_state(row, s, p, local_map):
    from engine.ai_profiles import validate_target_and_intent
    from engine.local_rivals import IDENTITY, OWNER
    keys = {'phase','target','withdraw_left','hold_left','approach_left','no_progress',
            'best_distance','suppressed','route_blocked','opportunities','hunt'}
    def fail():
        raise ValueError('composite.hunt: malformed commitment, phase, provenance or finite counters')
    if not isinstance(s,dict) or set(s) != keys:
        fail()
    if s['phase'] not in ('idle','approach','withdraw','monitor','hold','return') or type(s['route_blocked']) is not bool:
        fail()
    for k,hi in (('withdraw_left',p['withdrawal_budget']),('hold_left',p['hold_opportunities']),
                 ('approach_left',32),('no_progress',8),('opportunities',2**63-1)):
        if type(s[k]) is not int or not 0 <= s[k] <= hi:
            fail()
    if s['best_distance'] is not None and (type(s['best_distance']) is not int or not 0 <= s['best_distance'] <= 2**31):
        fail()
    validate_target_and_intent(row,s,p,local_map)
    h = s['hunt']
    if (h is None) != (s['phase'] in ('idle','approach')):
        fail()
    if (s['phase']=='idle' and any(s[k] for k in ('withdraw_left','hold_left','approach_left','no_progress'))
            or s['phase']=='withdraw' and s['withdraw_left']==0
            or s['phase']=='hold' and (s['hold_left']==0 or p['return_policy']!='after_hold')
            or s['phase']=='monitor' and p['return_policy']!='observed_paralysis'):
        fail()
    if h is None:
        return
    if (not isinstance(h,dict) or set(h) != {'version','application_id','source_id','owner','delivery_phase','first_observation_phase','last_useful_phase'}
            or type(h['version']) is not int or h['version'] != 1
            or not isinstance(h['application_id'],str) or not re.fullmatch('[0-9a-f]{32}',h['application_id'])
            or not isinstance(h['source_id'],str) or not IDENTITY.fullmatch(h['source_id']) or h['source_id'] != row.get('individual_id')
            or not isinstance(h['owner'],str) or not OWNER.fullmatch(h['owner']) or h['owner'] != s['target']['owner']
            or any(type(h[k]) is not int or not 0 <= h[k] < 2**63 for k in ('delivery_phase','first_observation_phase','last_useful_phase'))
            or h['first_observation_phase'] != h['delivery_phase']+p['warning_phases']+1
            or h['last_useful_phase'] != h['delivery_phase']+p['warning_phases']+p['paralysis_phases']
            or h['delivery_phase'] > s['target']['seen']):
        fail()
