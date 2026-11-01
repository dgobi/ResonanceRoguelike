"""Privileged read-only view in the disposable actual-game room session only."""
import copy
from engine.ai_profiles import local_only


def inspect(engine):
    from engine.venom import inspect as inspect_venom
    actors = [a for a in engine.entities if local_only(a)]
    mask = engine.normal_player_vision()['visible'] if actors else None
    return dict(contract='composite-diagnostic-4', view='live saved instance', privileged=True,
                player_condition=inspect_venom(engine.player),
                victims=[dict(id=getattr(a, '_creature_id', None), individual_id=getattr(a, '_individual_id', None),
                              condition=inspect_venom(a)) for a in engine.entities if a is not engine.player][:16],
                turn=engine.world_time.turn, total=len(actors), truncated=len(actors)>16,
                actors=[dict(id=a._creature_id, individual_id=getattr(a, '_individual_id', None),
                             position=[a.x,a.y], profile=copy.deepcopy(a.ai.profile),
                             condition=inspect_venom(a),
                             hunt_observation=copy.deepcopy(a.ai.hunt_evidence),
                             hunt_information='Own delivery provenance and timing are internal; only current direct sight supplies a symptom. Inspection does not refresh either.',
                             return_policy=a.ai.profile.get('return_policy', 'after_hold'),
                             return_assessment=dict(
                                 last_selected_reason=a.ai.trace[-1]['reason'] if a.ai.trace else 'no_resumed_decision_yet',
                                 last_decision_phase=a.ai.trace[-1]['turn'] if a.ai.trace else None,
                                 cue_age=None if a.ai.hunt_evidence is None else engine.world_time.turn-a.ai.hunt_evidence['phase'],
                                 resolution=a.ai.last_cancellation,
                                 note='Latest decision evidence only; every later predatory action rechecks sight. Timed policy has no symptom gate.'),
                             state=a.ai.snapshot()['state'],
                             evidence_age=None if a.ai.target is None else engine.world_time.turn-a.ai.target['seen'],
                             normal_observation=dict(observed=bool(mask[a.x,a.y]), rule='normal_player_vision'),
                             last_cancellation=a.ai.last_cancellation,
                             recent=copy.deepcopy(a.ai.trace)) for a in actors[:16]])
