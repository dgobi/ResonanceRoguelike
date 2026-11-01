"""Registered numbing venom: victim-owned data, phase clock and melee delivery.

No source polling or AI decisions live here. Queries and diagnostics are pure.
"""
from __future__ import annotations
import copy
import re
import uuid
from dataclasses import dataclass

EFFECT = 'numbing_venom'
DEFAULTS = dict(warning_phases=3, paralysis_phases=3, recovery_phases=4)
BOUNDS = dict(warning_phases=(2, 12), paralysis_phases=(1, 3), recovery_phases=(4, 16))


def dose(actor):
    return getattr(getattr(actor, 'fighter', actor), '_numbing_venom', None)


def fully_paralysed(actor):
    """Pure severe-stage action/active-defence predicate for an actor or Fighter."""
    record = dose(actor)
    return bool(record and record['stage'] == 'paralysis')


def movement_denial(actor):
    return 'numbing_venom_paralysis' if fully_paralysed(actor) else None


def eligible(engine, actor):
    from engine.local_rivals import supported, living
    return living(actor) and (actor is engine.player or supported(actor))


def trait(value):
    if value not in ('susceptible', 'immune') or not isinstance(value, str):
        raise ValueError('numbing_venom_trait: choose susceptible or immune')
    return value


def parameters(values):
    result = {key: values[key] for key in DEFAULTS}
    for key, (lo, hi) in BOUNDS.items():
        if type(result[key]) is not int or not lo <= result[key] <= hi:
            raise ValueError(f'numbing_venom.{key}: expected integer {lo}..{hi}')
    return result


@dataclass(frozen=True)
class ApplicationResult:
    accepted: bool
    reason: str
    application_id: str | None = None
    source_id: str | None = None


def tell(engine, actor, player_text, creature_text):
    from engine.palette import DUSTY_ROSE, UI_TEXT_DIM
    if actor is engine.player:
        engine.log.add(player_text, DUSTY_ROSE)
    elif (any(a is actor for a in engine.entities) and engine.local_map.in_bounds(actor.x, actor.y)
          and engine.normal_player_vision()['visible'][actor.x, actor.y]):
        engine.log.add(f'The {actor.name} {creature_text}.', UI_TEXT_DIM)


def deliver(engine, source, victim, attack):
    """Consume one already-resolved attack result; never execute combat."""
    from engine.effect_lifecycle import ability_enabled, creature_id
    from engine.local_rivals import allocate, owner
    profile = source.ai.profile
    reason = ('attack_rejected' if not attack.committed else
              'miss' if not attack.hit else
              'no_damage' if not attack.damage or attack.damage <= 0 else
              'lethal' if attack.target_dead or not getattr(victim, 'is_alive', False) else
              'source_suppressed' if not ability_enabled(source, engine.local_map) else
              'unsupported_recipient' if not eligible(engine, victim) else
              'immune' if getattr(victim, '_numbing_venom_trait', 'susceptible') == 'immune' else
              ('recovery_protection' if dose(victim)['stage'] == 'recovery' else 'active_venom') if dose(victim) else None)
    if reason:
        return ApplicationResult(False, reason)
    allocate(engine, [source])
    identity = uuid.uuid4().hex
    victim.fighter._numbing_venom = dict(version=1, effect=EFFECT,
        parameters=parameters(profile), stage='warning', remaining=profile['warning_phases'],
        application_id=identity, source=dict(creature=creature_id(source),
        individual=source._individual_id, owner=owner(engine)),
        applied_phase=engine.world_time.turn, aged_phase=engine.world_time.turn)
    tell(engine, victim, 'A strange numbness spreads from the bite. Your limbs feel heavy.',
         'trembles')
    return ApplicationResult(True, 'accepted', identity, source._individual_id)


def age(engine, actor):
    record = dose(actor)
    if record is None:
        return
    from engine.local_rivals import living
    if not living(actor):
        actor.fighter._numbing_venom = None
        return
    now = engine.world_time.turn
    if record['aged_phase'] == now:
        return
    record['aged_phase'] = now
    record['remaining'] -= 1
    stage = record['stage']
    if record['remaining'] > 0:
        if stage == 'warning' and record['remaining'] == 1:
            tell(engine, actor, 'The numbness deepens.', 'shivers')
        return
    if stage == 'warning':
        record.update(stage='paralysis', remaining=record['parameters']['paralysis_phases'])
        if actor is engine.player:
            engine._free_move_pending = False
        tell(engine, actor, 'Your body will not answer.', 'locks in place, limbs rigid')
    elif stage == 'paralysis':
        record.update(stage='recovery', remaining=record['parameters']['recovery_phases'])
        tell(engine, actor, 'Feeling returns in prickling waves.', 'loosens its rigid limbs')
    else:
        actor.fighter._numbing_venom = None


def cure(engine):
    if fully_paralysed(engine.player):
        return False
    actor = engine.player
    record = dose(actor)
    from engine.local_rivals import living
    if not living(actor) or record is None or record['stage'] == 'recovery':
        from engine.palette import WORN_STONE
        engine.log.add('No active numbing venom to treat; keep the treatment.', WORN_STONE)
        return False
    record.update(stage='recovery', remaining=record['parameters']['recovery_phases'],
                  aged_phase=engine.world_time.turn)
    tell(engine, actor, 'The numbness begins to recede.', '')
    return True


def snapshot(actor):
    value = {}
    if getattr(actor, '_numbing_venom_trait', 'susceptible') != 'susceptible':
        value['trait'] = 'immune'
    if dose(actor) is not None:
        value['dose'] = copy.deepcopy(dose(actor))
    return dict(version=1, **value) if value else None


def validate(record, *, phase=None):
    from engine.local_rivals import OWNER, IDENTITY
    def fail():
        raise ValueError('venom: malformed version, trait, stage, counter or provenance')
    if record is None:
        return
    if (not isinstance(record, dict) or type(record.get('version')) is not int or record['version'] != 1
            or set(record) - {'version', 'trait', 'dose'} or len(record) == 1):
        fail()
    if 'trait' in record:
        trait(record['trait'])
    if 'dose' not in record:
        return
    d = record['dose']
    keys = {'version', 'effect', 'parameters', 'stage', 'remaining', 'application_id', 'source', 'applied_phase', 'aged_phase'}
    if (not isinstance(d, dict) or set(d) != keys or type(d['version']) is not int or d['version'] != 1
            or d['effect'] != EFFECT or d['stage'] not in ('warning', 'paralysis', 'recovery')
            or not isinstance(d['parameters'], dict) or set(d['parameters']) != set(DEFAULTS)):
        fail()
    parameters(d['parameters'])
    if (type(d['remaining']) is not int or not 1 <= d['remaining'] <= d['parameters'][d['stage']+'_phases']
            or any(type(d[k]) is not int or not 0 <= d[k] < 2**63 for k in ('applied_phase', 'aged_phase'))
            or d['aged_phase'] < d['applied_phase']
            or (phase is not None and d['aged_phase'] > phase)
            or not isinstance(d['application_id'], str) or not re.fullmatch('[0-9a-f]{32}', d['application_id'])):
        fail()
    s = d['source']
    if (not isinstance(s, dict) or set(s) != {'creature', 'individual', 'owner'}
            or not isinstance(s['creature'], str) or not re.fullmatch('[A-Za-z0-9_-]{1,100}', s['creature'])
            or not isinstance(s['individual'], str) or not IDENTITY.fullmatch(s['individual'])
            or not isinstance(s['owner'], str) or not OWNER.fullmatch(s['owner'])):
        fail()


def restore(actor, record):
    validate(record)
    actor._numbing_venom_trait = record.get('trait', 'susceptible') if record else 'susceptible'
    if getattr(actor, 'fighter', None) is not None:
        actor.fighter._numbing_venom = copy.deepcopy(record.get('dose')) if record else None


def inspect(actor):
    return dict(trait=getattr(actor, '_numbing_venom_trait', 'susceptible'),
                dose=copy.deepcopy(dose(actor)), movement_denial=movement_denial(actor),
                full_paralysis=fully_paralysed(actor))
