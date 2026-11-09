"""Complete L10–L12 solution, opt-in only in GUIDE-1's disposable process.

Ordinary game startup never imports this module. The installation patch and its
fingerprint contract show the equivalent source integration for deliberate study.
No hidden timer, new status API, or additional save owner is invented here.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

CADENCE = 'guide1_cadence'
SURVEY = 'guide1_survey'
SURVEY_PHASES = 3


def integer(value, minimum=0, maximum=2**31-1):
    return type(value) is int and minimum <= value <= maximum


def validate_states(states):
    """Optional absence is compatible; present inner records must be complete."""
    if CADENCE in states:
        s = states[CADENCE]
        if not isinstance(s, dict) or set(s) != {'version', 'paid'} or type(s['version']) is not int or s['version'] != 1 or not integer(s['paid']):
            raise ValueError('GUIDE-1 cadence: expected version 1 and nonnegative integer paid')
    if SURVEY in states:
        s = states[SURVEY]
        if not isinstance(s, dict) or set(s) != {'version', 'phase', 'left', 'anchor', 'completed'}:
            raise ValueError('GUIDE-1 survey: incomplete state')
        if type(s['version']) is not int or s['version'] != 1 or s['phase'] not in ('idle', 'working', 'ready') or not integer(s['left'], 0, SURVEY_PHASES) or not integer(s['completed']):
            raise ValueError('GUIDE-1 survey: invalid version, phase or counter')
        if s['phase'] == 'working':
            a = s['anchor']
            if s['left'] < 1 or not isinstance(a, list) or len(a) != 5 or not all(integer(a[i]) for i in (0, 1, 3, 4)) or not (a[2] is None or isinstance(a[2], str)):
                raise ValueError('GUIDE-1 survey: working state needs remaining work and scene/position')
        elif s['left'] != 0 or s['anchor'] is not None:
            raise ValueError('GUIDE-1 survey: idle/ready cannot retain unfinished work')


def survey_state(e):
    states = e.player.perks.perk_state
    validate_states(states)
    return states.setdefault(SURVEY, dict(version=1, phase='idle', left=0, anchor=None, completed=0))


def address(e):
    return [e.world_x, e.world_y, e.current_submap_id, e.player.x, e.player.y]


@dataclass(frozen=True)
class ExchangeResult:
    hp: int
    thirst: float
    recovered: int


def parse_exchange(definition):
    """Definition parsing, distinct from checking the current actor's resources."""
    c = definition.get('guide_exchange')
    if not isinstance(c, dict) or set(c) != {'version', 'heal', 'thirst_cost'} or type(c['version']) is not int or c['version'] != 1:
        raise ValueError('GUIDE-1 exchange requires complete version 1 configuration')
    cost = c['thirst_cost']
    if not integer(c['heal'], 1, 20) or type(cost) not in (int, float) or not math.isfinite(cost) or not 0 < cost <= .5:
        raise ValueError('GUIDE-1 exchange requires heal 1..20 and finite thirst_cost (0,.5]')
    return c


def plan_exchange(fighter, needs, config):
    """Pure result calculation: a rejection does not partly spend resources."""
    if fighter is None or needs is None or fighter.is_dead or fighter.hp <= 0 or fighter.hp >= fighter.max_hp or needs.thirst + config['thirst_cost'] > 1:
        return None
    recovered = min(config['heal'], fighter.max_hp - fighter.hp)
    return ExchangeResult(fighter.hp + recovered, needs.thirst + config['thirst_cost'], recovered)


def use_exchange(self, item, e):
    from engine.palette import WORN_STONE
    try:
        config = parse_exchange(e.data.items[item.item_id])
    except (ValueError, KeyError) as error:
        e.log.add(str(error), WORN_STONE)
        return False
    result = plan_exchange(getattr(e.player, 'fighter', None), getattr(e.player, 'needs', None), config)
    if result is None:
        e.log.add('Practice exchange refused: need injury and enough thirst capacity.', WORN_STONE)
        return False
    # Apply the fully checked result once. Dispatcher already checked exact ownership.
    e.player.fighter.hp = result.hp
    e.player.needs.thirst = result.thirst
    self.last_use_committed = True
    e.log.add(f'Practice exchange: recovered {result.recovered} HP; thirst increased.', WORN_STONE)
    return False  # reusable tool; committed use still pays the inventory phase


def cadence_turn(payload):
    e = payload['engine']
    states = e.player.perks.perk_state
    validate_states(states)
    s = states.setdefault(CADENCE, dict(version=1, paid=0))
    s['paid'] = min(2**31-1, s['paid'] + 1)
    if s['paid'] % 3 == 0:
        return {'add_message': f'Practice cadence: {s["paid"]} paid phases.'}
    return None


def use_survey(self, item, e):
    from engine.palette import WORN_STONE
    if not e.player.perks.has(SURVEY):
        e.log.add('Acquire Practice survey on K before using the tool.', WORN_STONE)
        return False
    s = survey_state(e)
    if s['phase'] == 'working':
        e.log.add('Survey already working; wait here or cancel.', WORN_STONE)
        return False
    if s['phase'] == 'ready':
        s.update(phase='idle', completed=min(2**31-1, s['completed'] + 1))
        e.log.add(f'Survey collected: {s["completed"]}.', WORN_STONE)
    else:
        s.update(phase='working', left=SURVEY_PHASES, anchor=address(e))
        e.log.add('Survey started. This action counts as the first phase.', WORN_STONE)
    self.last_use_committed = True
    return False


def survey_turn(payload):
    e = payload['engine']
    s = survey_state(e)
    if s['phase'] != 'working':
        return None
    if address(e) != s['anchor']:
        s.update(phase='idle', left=0, anchor=None)
        return {'add_message': 'Survey cancelled: position or scene changed.'}
    s['left'] -= 1
    if s['left'] == 0:
        s.update(phase='ready', anchor=None)
        return {'add_message': 'Survey ready. Use the tool to collect.'}
    return None


def use_inspect(self, item, e):
    from engine.palette import WORN_STONE
    s = survey_state(e)
    e.log.add(f'Survey: {s["phase"]}; {s["left"]} phases left; {s["completed"]} collected.', WORN_STONE)
    return False  # intentional free inspection, no last_use_committed


def use_cancel(self, item, e):
    from engine.palette import WORN_STONE
    s = survey_state(e)
    if s['phase'] == 'working':
        s.update(phase='idle', left=0, anchor=None)
        e.log.add('Survey voluntarily cancelled. No work refunded.', WORN_STONE)
    return False  # cancelling an unproductive activity is free by this lesson's rule


def install():
    """Idempotent process-local installation at real production extension seams.

    Must run before Engine construction/save loading. SaveManager imports its own
    validator alias, so both names are intentionally bound. No disk mutation.
    """
    from engine.item_system import ItemSystem
    from engine import perk_handlers, save_components, save_manager
    if getattr(ItemSystem, '_guide1_installed', False):
        return
    ItemSystem._use_guide_exchange = use_exchange
    ItemSystem._use_guide_survey = use_survey
    ItemSystem._use_guide_inspect = use_inspect
    ItemSystem._use_guide_cancel = use_cancel
    for name, fn in [('guide_cadence_turn', cadence_turn), ('guide_survey_turn', survey_turn)]:
        fn._is_perk_handler = True
        perk_handlers.HANDLER_MAP[name] = fn
    original = save_components.validate_components
    def validate_components(data):
        result = original(data)
        validate_states((data.get('perks') or {}).get('perk_state', {}))
        return result
    save_components.validate_components = validate_components
    save_manager.validate_components = validate_components
    ItemSystem._guide1_installed = True
