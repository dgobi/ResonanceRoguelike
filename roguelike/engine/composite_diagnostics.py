"""Privileged read-only view in the disposable actual-game room session only."""
import copy
from engine.ai_profiles import local_only


def inspect(engine):
    actors = [a for a in engine.entities if local_only(a)]
    mask = engine.normal_player_vision()['visible'] if actors else None
    return dict(contract='composite-diagnostic-2', view='live saved instance', privileged=True,
                turn=engine.world_time.turn, total=len(actors), truncated=len(actors)>16,
                actors=[dict(id=a._creature_id, individual_id=getattr(a, '_individual_id', None),
                             position=[a.x,a.y], profile=copy.deepcopy(a.ai.profile),
                             state=a.ai.snapshot()['state'],
                             evidence_age=None if a.ai.target is None else engine.world_time.turn-a.ai.target['seen'],
                             normal_observation=dict(observed=bool(mask[a.x,a.y]), rule='normal_player_vision'),
                             last_cancellation=a.ai.last_cancellation,
                             recent=copy.deepcopy(a.ai.trace)) for a in actors[:16]])
