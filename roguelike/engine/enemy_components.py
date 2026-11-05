"""Small host adapters for opt-in enemy components; no scheduler or extra action."""
from __future__ import annotations

RECIPES = ('strike_and_withdraw', 'observation_averse', 'venom_strike_and_withdraw',
           'patient_venom_hunt', 'territorial_guard')


def windows(ai, engine, actor):
    """Pure phase eligibility, after host housekeeping; no perception acquisition."""
    recipe = ai.profile['recipe']
    if recipe not in RECIPES:
        return dict(approach=False, regroup=False, idle=False, reason='unsupported_host')
    if recipe == 'observation_averse':
        watched = bool(engine.normal_player_vision()['visible'][actor.x, actor.y])
        if watched or ai.phase == 'conceal' or ai.covered_phase == engine.world_time.turn:
            return dict(approach=False, regroup=False, idle=False, reason='concealment_commitment')
        return dict(approach=ai.target is not None, regroup=True,
                    idle=ai.target is None, reason='unseen')
    if recipe == 'territorial_guard':
        t = ai.territory
        if t['phase'] in ('return', 'blocked') or t['phase'] == 'engaged' and not t['pursuit_left']:
            return dict(approach=False, regroup=False, idle=False, reason='territorial_return')
    if ai.phase in ('withdraw', 'hold', 'cornered'):
        return dict(approach=False, regroup=False, idle=False, reason='required_defence')
    if recipe == 'patient_venom_hunt':
        return dict(approach=ai.phase == 'approach' and ai.hunt is None,
                    regroup=True, idle=ai.target is None and not ai.hunt and not ai.suppressed,
                    reason='retained_hunt' if ai.hunt or ai.suppressed else 'initial_approach')
    return dict(approach=ai.target is not None and ai.phase in ('approach', 'return'),
                regroup=recipe != 'territorial_guard' or ai.territory['phase'] == 'engaged',
                idle=ai.target is None and (recipe != 'territorial_guard' or ai.territory['phase'] == 'guard'),
                reason='ordinary_approach' if ai.target else 'idle')


def move(ai, engine, actor, destination):
    """One revalidated physical step, including v2's reactions and exposure."""
    if ai.profile['recipe'] != 'observation_averse':
        return ai._move(engine, actor, destination)
    from components.observation_averse import step, route_to_cover
    outcome = step(ai, engine, actor, destination)
    ai.attachment_steps.append(outcome)
    if outcome['moved'] and outcome['observed']:
        if [actor.x, actor.y] not in ai.failed_entries:
            ai.failed_entries = (ai.failed_entries + [[actor.x, actor.y]])[-8:]
        ai.phase = 'conceal'
        route_to_cover(ai, engine, actor, engine.normal_player_vision()['visible'])
        if ai.cover_goal is None or not ai.conceal_left:
            ai.phase = 'cower'
    return outcome['moved']


def choose(ai, engine, actor, observed, ambient):
    """Execute at most one attachment choice, otherwise yield to the base recipe."""
    from engine import enemy_maneuvers as maneuvers, enemy_responses as responses
    flags = windows(ai, engine, actor)
    ai.attachment_steps = []
    maneuvers.refresh(ai, engine, actor, ambient)
    decision = maneuvers.regroup(ai, engine, actor, observed, ambient, flags)
    if decision:
        return decision
    # v1 response semantics stay exact, including its initial approach-only call.
    legacy = ai.response_config and ai.response_config['version'] == 1
    call = (ai.phase == 'approach' if legacy else flags['approach'])
    decision = responses.choose(ai, engine, actor, observed, ambient,
        call=call and ai.target is not None and ai.target['role'] == 'player', idle=flags['idle'])
    if decision:
        return decision
    return maneuvers.lateral(ai, engine, actor, observed, ambient, flags)
