"""Game-owned, deliberately small composite v1 contract (no executable content)."""
from __future__ import annotations
import copy

DEFAULTS = dict(version=1, recipe='strike_and_withdraw', capability='melee',
                trigger='hit', retreat_distance=2, hold_opportunities=1,
                withdrawal_budget=6, cornered='defensive_melee', scene_scope='active_scene')
BOUNDS = {'retreat_distance': (2, 8), 'hold_opportunities': (0, 12),
          'withdrawal_budget': (1, 32), 'pursuit_timeout': (0, 10000)}
PROFILE_FIELDS = list(DEFAULTS)


def effective_profile(raw):
    """Validate without coercion; definition pursuit_timeout is the evidence clock."""
    p = raw.get('ai_profile')
    if not isinstance(p, dict):
        raise ValueError('ai_profile: composite requires an embedded version-1 profile')
    unknown = set(p) - set(DEFAULTS)
    if unknown:
        raise ValueError('ai_profile: unsupported fields: ' + ', '.join(sorted(unknown)))
    result = {**DEFAULTS, **copy.deepcopy(p), 'pursuit_timeout': raw.get('pursuit_timeout', 20)}
    for key, expected in DEFAULTS.items():
        if key in ('trigger', *BOUNDS):
            continue
        if type(result[key]) is not type(expected) or result[key] != expected:
            raise ValueError(f'ai_profile.{key}: supported value is {expected!r}')
    if result['trigger'] not in ('hit', 'committed_attack'):
        raise ValueError('ai_profile.trigger: choose hit or committed_attack')
    for key, (lo, hi) in BOUNDS.items():
        if type(result[key]) is not int or not lo <= result[key] <= hi:
            raise ValueError(f'ai_profile.{key}: expected integer {lo}..{hi}; booleans are not numbers')
    for key in ('can_cross_chunks', 'can_use_stairs'):
        if key in raw and raw[key] is not False:
            raise ValueError(f'{key}: composite v1 is active-scene only; must be false')
    for key in ('ranged_attack', 'abilities', 'effects', 'statuses'):
        if key in raw:
            raise ValueError(f'{key}: unsupported with composite v1 ordinary melee')
    from engine.creature_abilities import ABILITY_REGISTRY
    if raw.get('id') in ABILITY_REGISTRY:
        raise ValueError('ai_profile: ID-bound special actors cannot use composite v1')
    return result


def saved_profile(profile):
    if not isinstance(profile, dict) or set(profile) != set(DEFAULTS) | {'pursuit_timeout'}:
        raise ValueError('composite.profile: complete effective version-1 profile required')
    return effective_profile(dict(ai_profile={k: v for k, v in profile.items() if k != 'pursuit_timeout'},
                                  pursuit_timeout=profile['pursuit_timeout']))


def local_only(actor):
    from components.composite_ai import CompositeAI
    return type(getattr(actor, 'ai', None)) is CompositeAI


def depart(engine):
    """Call only after destination admission succeeds, before caching the old scene."""
    for actor in engine.entities:
        if local_only(actor):
            actor.ai.cancel(actor, 'scene_departure')
            actor.ai.suppressed = None
            actor.ai.move_accumulator = 0.0


def validate_saved(row, local_map=None):
    composite = row.get('composite')
    if row.get('ai_type') != 'CompositeAI':
        if composite is not None:
            raise ValueError('composite: discriminator must be CompositeAI')
        return
    from engine.creature_abilities import ABILITY_REGISTRY
    if isinstance(row.get('id'), str) and row['id'] in ABILITY_REGISTRY:
        raise ValueError('composite: saved binding cannot acquire an ID-bound special ability')
    if not isinstance(composite, dict) or set(composite) != {'profile', 'state'}:
        raise ValueError('composite: profile and tactical state required')
    p = saved_profile(composite['profile'])
    s = composite['state']
    keys = {'phase', 'target', 'withdraw_left', 'hold_left', 'approach_left',
            'no_progress', 'best_distance', 'suppressed', 'route_blocked', 'opportunities'}
    if not isinstance(s, dict) or set(s) != keys:
        raise ValueError('composite.state: incomplete or unsupported tactical state')
    if s['phase'] not in ('idle', 'approach', 'withdraw', 'hold', 'return', 'cornered'):
        raise ValueError('composite.state.phase: unsupported phase')
    if type(s['route_blocked']) is not bool:
        raise ValueError('composite.state.route_blocked: expected boolean rearm state')
    for key, hi in (('withdraw_left', p['withdrawal_budget']), ('hold_left', p['hold_opportunities']),
                    ('approach_left', 32), ('no_progress', 8), ('opportunities', 2**63-1)):
        if type(s[key]) is not int or not 0 <= s[key] <= hi:
            raise ValueError(f'composite.state.{key}: invalid bounded opportunity counter')
    if s['best_distance'] is not None and (type(s['best_distance']) is not int or not 0 <= s['best_distance'] <= 2**31):
        raise ValueError('composite.state.best_distance: invalid progress')
    if ((s['phase'] == 'hold' and s['hold_left'] == 0)
            or (s['phase'] == 'withdraw' and s['withdraw_left'] == 0)
            or (s['phase'] == 'idle' and any(s[k] != 0 for k in ('withdraw_left','hold_left','approach_left','no_progress')))):
        raise ValueError('composite.state: phase and remaining opportunity counters disagree')
    from engine.local_rivals import OWNER, IDENTITY
    from config import MAP_WIDTH, MAP_HEIGHT
    w, h = (local_map.width, local_map.height) if local_map else (MAP_WIDTH, MAP_HEIGHT)
    t = s['target']
    if (t is None) != (s['phase'] == 'idle'):
        raise ValueError('composite.state: tactical phase requires retained target')
    if t is not None:
        if (row.get('individual_id') is None or not isinstance(t, dict) or set(t) != {'role', 'id', 'owner', 'x', 'y', 'seen', 'deadline', 'provenance'}
                or t['role'] not in ('player', 'creature')
                or not isinstance(t['owner'], str) or not OWNER.fullmatch(t['owner'])
                or (t['role'] == 'player' and t['id'] is not None)
                or (t['role'] == 'creature' and (not isinstance(t['id'], str) or not IDENTITY.fullmatch(t['id']) or t['id'] == row.get('individual_id')))
                or type(t['x']) is not int or not 0 <= t['x'] < w
                or type(t['y']) is not int or not 0 <= t['y'] < h
                or type(t['seen']) is not int or not 0 <= t['seen'] < 2**63
                or type(t['deadline']) is not int or t['deadline'] != t['seen'] + p['pursuit_timeout']
                or t['provenance'] != 'sight'):
            raise ValueError('composite.state.target: invalid local sight evidence')
    if s['suppressed'] is not None and (not isinstance(s['suppressed'], str)
            or (s['suppressed'] != 'player' and not IDENTITY.fullmatch(s['suppressed']))):
        raise ValueError('composite.state.suppressed: invalid encounter reference')
    a = row.get('component_state', {}).get('actor', {})
    ai = row.get('component_state', {}).get('ai', {})
    if (row.get('local_target') is not None or row.get('ai_state') not in ('wandering', 'investigating')
            or any(a.get(k) is not None for k in ('_last_known_px', '_last_known_py', '_pending_stair_use'))
            or any(a.get(k) is not None for k in ('_surface_exit_x','_surface_exit_y','_surface_exit_wx','_surface_exit_wy'))
            or a.get('_just_arrived', False) is not False or a.get('_arrival_cooldown', 0) != 0
            or ai.get('target_x') is not None or ai.get('target_y') is not None
            or (t is not None and ai.get('sound_interest') is not None)):
        raise ValueError('composite: conflicting legacy/transfer intent')
