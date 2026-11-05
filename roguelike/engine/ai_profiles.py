"""Game-owned discriminated composite recipes (no executable profile content)."""
from __future__ import annotations
import copy

DEFAULTS = dict(version=1, recipe='strike_and_withdraw', capability='melee',
                trigger='hit', retreat_distance=2, hold_opportunities=1,
                withdrawal_budget=6, cornered='defensive_melee', scene_scope='active_scene')
BOUNDS = {'retreat_distance': (2, 8), 'hold_opportunities': (0, 12),
          'withdrawal_budget': (1, 32), 'pursuit_timeout': (0, 10000)}
PROFILE_FIELDS = list(DEFAULTS)
OBSERVATION_DEFAULTS = dict(version=2, recipe='observation_averse', capability='melee',
    observer='normal_player_vision', exposure_response='seek_concealment',
    concealment_policy='reachable_unobserved', concealment_budget=8,
    unseen_extra_step=1, no_cover='defensive_melee', pursuit_budget=32,
    scene_scope='active_scene')
OBSERVATION_BOUNDS = {'concealment_budget': (1, 32), 'unseen_extra_step': (0, 1),
                      'pursuit_budget': (1, 64), 'pursuit_timeout': (0, 10000)}
from engine.venom import DEFAULTS as VENOM_TIMINGS, BOUNDS as VENOM_BOUNDS
VENOM_DEFAULTS = dict(DEFAULTS, version=3, recipe='venom_strike_and_withdraw',
                      capability='numbing_melee', trigger='accepted_application',
                      effect='numbing_venom', **VENOM_TIMINGS)
HUNT_DEFAULTS = dict(VENOM_DEFAULTS, version=4, recipe='patient_venom_hunt',
                     return_policy='observed_paralysis')
TERRITORY_DEFAULTS = dict(DEFAULTS, version=5, recipe='territorial_guard',
    engagement='direct_melee', defended_radius=4, excursion_radius=6, pursuit_budget=32)
TERRITORY_BOUNDS = dict(BOUNDS, defended_radius=(1, 7), excursion_radius=(2, 8), pursuit_budget=(1, 64))
ESCORT_DEFAULTS = dict(version=6, recipe='protective_escort', capability='melee',
    initial_order='follow', follow_spacing=2, protection_radius=4, excursion_radius=6,
    pursuit_budget=18, scene_scope='active_scene')
ESCORT_BOUNDS = dict(follow_spacing=(1, 2), protection_radius=(1, 7),
    excursion_radius=(2, 8), pursuit_budget=(1, 32), pursuit_timeout=(0, 10000))
RECIPES = {'strike_and_withdraw': DEFAULTS, 'observation_averse': OBSERVATION_DEFAULTS,
           'venom_strike_and_withdraw': VENOM_DEFAULTS, 'patient_venom_hunt': HUNT_DEFAULTS,
           'territorial_guard': TERRITORY_DEFAULTS, 'protective_escort': ESCORT_DEFAULTS}


def profile_defaults(profile):
    if (not isinstance(profile, dict) or not isinstance(profile.get('recipe', 'strike_and_withdraw'), str)
            or profile.get('recipe', 'strike_and_withdraw') not in RECIPES):
        raise ValueError('ai_profile.recipe: unsupported registered recipe')
    return RECIPES[profile.get('recipe', 'strike_and_withdraw')]


def validate_binding(raw):
    """The registered consumer requires an ordinary melee Actor definition.

    A saved behavioural profile can outlive same-ID profile tuning, but cannot
    turn a player, NPC, configuration or special-bound definition into its host.
    Unrelated metadata and legacy definitions without this opt-in stay untouched.
    """
    from engine.creature_abilities import ABILITY_REGISTRY
    identifier = raw.get('id')
    if (not isinstance(identifier, str) or not identifier or identifier.casefold() == 'player'
            or identifier in ABILITY_REGISTRY
            or not isinstance(raw.get('fighter'), dict)
            or not isinstance(raw.get('perception'), dict) or not raw['perception']
            or any(k in raw for k in ('npc','dialogue','is_player','spawn_trigger','ranged_attack','abilities','effects','statuses'))):
        raise ValueError('composite: binding requires an ordinary melee Actor with fighter/perception; player, NPC, ranged and ID-bound special hosts are unsupported')


def effective_profile(raw):
    """Validate without coercion; definition pursuit_timeout is the evidence clock."""
    p = raw.get('ai_profile')
    if 'id' in raw:
        validate_binding(raw)
    if not isinstance(p, dict):
        raise ValueError('ai_profile: composite requires an embedded registered profile')
    defaults = profile_defaults(p)
    bounds = (ESCORT_BOUNDS if defaults is ESCORT_DEFAULTS else
              TERRITORY_BOUNDS if defaults is TERRITORY_DEFAULTS else
              OBSERVATION_BOUNDS if defaults is OBSERVATION_DEFAULTS else
              {**BOUNDS, **VENOM_BOUNDS} if defaults in (VENOM_DEFAULTS, HUNT_DEFAULTS) else BOUNDS)
    unknown = set(p) - set(defaults)
    if unknown:
        raise ValueError('ai_profile: unsupported fields: ' + ', '.join(sorted(unknown)))
    result = {**defaults, **copy.deepcopy(p), 'pursuit_timeout': raw.get('pursuit_timeout', 20)}
    for key, expected in defaults.items():
        if key in ('no_cover', *bounds) or (key == 'initial_order' and defaults is ESCORT_DEFAULTS) or (key == 'engagement' and defaults is TERRITORY_DEFAULTS) or (key == 'return_policy' and defaults is HUNT_DEFAULTS) or (key == 'trigger' and defaults in (DEFAULTS, TERRITORY_DEFAULTS)):
            continue
        if type(result[key]) is not type(expected) or result[key] != expected:
            raise ValueError(f'ai_profile.{key}: supported value is {expected!r}')
    if defaults in (DEFAULTS, TERRITORY_DEFAULTS) and result['trigger'] not in ('hit', 'committed_attack'):
        raise ValueError('ai_profile.trigger: choose hit or committed_attack')
    if defaults is OBSERVATION_DEFAULTS and result['no_cover'] not in ('defensive_melee', 'cower'):
        raise ValueError('ai_profile.no_cover: choose defensive_melee or cower')
    if defaults is HUNT_DEFAULTS and result['return_policy'] not in ('observed_paralysis', 'after_hold'):
        raise ValueError('ai_profile.return_policy: choose observed_paralysis or after_hold')
    for key, (lo, hi) in bounds.items():
        if type(result[key]) is not int or not lo <= result[key] <= hi:
            raise ValueError(f'ai_profile.{key}: expected integer {lo}..{hi}; booleans are not numbers')
    if defaults is ESCORT_DEFAULTS:
        if result['initial_order'] not in ('follow', 'hold'):
            raise ValueError('ai_profile.initial_order: choose follow or hold')
        if result['excursion_radius'] <= result['protection_radius']:
            raise ValueError('ai_profile.excursion_radius: must exceed protection_radius')
        if 'id' in raw:
            validate_escort_alignment(raw.get('perception'))
    if defaults is TERRITORY_DEFAULTS:
        if result['engagement'] not in ('direct_melee', 'strike_and_withdraw'):
            raise ValueError('ai_profile.engagement: choose direct_melee or strike_and_withdraw')
        if result['excursion_radius'] <= result['defended_radius']:
            raise ValueError('ai_profile.excursion_radius: must exceed defended_radius')
        if result['retreat_distance'] > result['excursion_radius']:
            raise ValueError('ai_profile.retreat_distance: cannot exceed excursion_radius')
        if result['engagement'] == 'direct_melee' and any(result[k] != DEFAULTS[k] for k in ('trigger', 'retreat_distance', 'hold_opportunities', 'withdrawal_budget')):
            raise ValueError('ai_profile: direct melee requires canonical inactive withdrawal defaults; select strike_and_withdraw to tune them')
    for key in ('can_cross_chunks', 'can_use_stairs'):
        if key in raw and raw[key] is not False:
            raise ValueError(f'{key}: composite is active-scene only; must be false')
    for key in ('ranged_attack', 'abilities', 'effects', 'statuses'):
        if key in raw:
            raise ValueError(f'{key}: unsupported with composite ordinary melee')
    from engine.creature_abilities import ABILITY_REGISTRY
    if raw.get('id') in ABILITY_REGISTRY:
        raise ValueError('ai_profile: ID-bound special actors cannot use composite')
    if 'enemy_responses' in raw:
        from engine.enemy_responses import configuration
        if raw['enemy_responses'] is None:
            raise ValueError('enemy_responses: omit an absent attachment')
        configuration(raw['enemy_responses'], result, raw.get('perception'))
    if 'enemy_maneuvers' in raw:
        from engine.enemy_maneuvers import configuration
        if raw['enemy_maneuvers'] is None:
            raise ValueError('enemy_maneuvers: omit an absent attachment')
        configuration(raw['enemy_maneuvers'], result, raw.get('perception'))
    return result


def validate_escort_alignment(perception):
    from engine.local_rivals import TOKEN
    if (not isinstance(perception, dict) or perception.get('faction') != 'player'
            or not isinstance(perception.get('hostile_to'), list)
            or len(perception['hostile_to']) > 16
            or any(not isinstance(v, str) or not TOKEN.fullmatch(v) or v == 'player'
                   for v in perception['hostile_to'])
            or len(set(perception['hostile_to'])) != len(perception['hostile_to'])):
        raise ValueError('protective_escort: requires faction player and explicit distinct hostile factions excluding player')


def saved_profile(profile):
    defaults = profile_defaults(profile)
    if set(profile) != set(defaults) | {'pursuit_timeout'}:
        raise ValueError('composite.profile: complete effective registered profile required')
    return effective_profile(dict(ai_profile={k: v for k, v in profile.items() if k != 'pursuit_timeout'},
                                  pursuit_timeout=profile['pursuit_timeout']))


def local_only(actor):
    from components.composite_ai import CompositeAI
    return type(getattr(actor, 'ai', None)) is CompositeAI


def depart(engine):
    """Call only after destination admission succeeds, before caching the old scene."""
    cursor = getattr(engine, 'interaction_cursor', None)
    if cursor is not None:
        cursor._order_prompt = None
    for actor in engine.entities:
        if local_only(actor):
            actor.ai.cancel(actor, 'scene_departure')
            actor.ai.suppressed = None
            actor.ai.move_accumulator = 0.0


def validate_saved(row, local_map=None):
    _validate_recipe_saved(row, local_map)
    composite = row.get('composite')
    if isinstance(composite, dict) and 'responses' in composite:
        from engine.enemy_responses import validate_saved as validate_responses
        validate_responses(composite['responses'], row, composite['profile'], local_map)
    if isinstance(composite, dict) and 'maneuvers' in composite:
        from engine.enemy_maneuvers import validate_saved as validate_maneuvers
        validate_maneuvers(composite['maneuvers'], row, composite['profile'], local_map)


def _validate_recipe_saved(row, local_map=None):
    composite = row.get('composite')
    if row.get('ai_type') != 'CompositeAI':
        if composite is not None:
            raise ValueError('composite: discriminator must be CompositeAI')
        return
    from engine.creature_abilities import ABILITY_REGISTRY
    if isinstance(row.get('id'), str) and (row['id'].casefold() == 'player' or row['id'] in ABILITY_REGISTRY):
        raise ValueError('composite: saved binding cannot acquire player or ID-bound special behavior')
    if (not isinstance(composite, dict) or not {'profile','state'} <= set(composite)
            or set(composite)-{'profile','state','responses','maneuvers'}):
        raise ValueError('composite: profile and tactical state required')
    p = saved_profile(composite['profile'])
    s = composite['state']
    if p['recipe'] == 'protective_escort':
        from components.protective_escort import validate_state
        validate_state(row, s, p, local_map)
        return
    if p['recipe'] == 'territorial_guard':
        from components.territorial import validate_state
        validate_state(row, s, p, local_map)
        return
    if isinstance(s, dict) and 'withdrawal_told' in s and p['recipe'] != 'observation_averse':
        if type(s['withdrawal_told']) is not bool:
            raise ValueError('composite.state.withdrawal_told: expected boolean')
        s = {k: v for k, v in s.items() if k != 'withdrawal_told'}
    if p['recipe'] == 'observation_averse':
        from components.observation_averse import validate_state
        validate_state(s, p, local_map)
    if p['recipe'] == 'patient_venom_hunt':
        from components.patient_hunt import validate_state
        validate_state(row, s, p, local_map)
        return
    keys = {'phase', 'target', 'withdraw_left', 'hold_left', 'approach_left',
            'no_progress', 'best_distance', 'suppressed', 'route_blocked', 'opportunities'}
    if p['recipe'] != 'observation_averse' and (not isinstance(s, dict) or set(s) != keys):
        raise ValueError('composite.state: incomplete or unsupported tactical state')
    if p['recipe'] == 'observation_averse':
        validate_target_and_intent(row, s, p, local_map, optional_target=True)
        return
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
    validate_target_and_intent(row, s, p, local_map)


def validate_target_and_intent(row, s, p, local_map, *, optional_target=False):
    from engine.local_rivals import OWNER, IDENTITY
    from config import MAP_WIDTH, MAP_HEIGHT
    w, h = (local_map.width, local_map.height) if local_map else (MAP_WIDTH, MAP_HEIGHT)
    t = s['target']
    if not optional_target and (t is None) != (s['phase'] == 'idle'):
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
    if not optional_target and s['suppressed'] is not None and (not isinstance(s['suppressed'], str)
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
