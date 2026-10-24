"""Dispatch on actual saved scene revision as well as unchanged plan origin."""
from generation.context import GenerationError

ADAPTERS={('wg4',1):'g3-to-g4-v1',('wg4',2):'g4-v1',
          ('wg5',1):'g3-to-g5-v1',('wg5',2):'g4-to-g5-v1',('wg5',3):'g5-v1',
          ('wg6',1):'g3-to-g6-v1',('wg6',2):'g4-to-g6-v1',('wg6',3):'g5-to-g6-v1',('wg6',4):'g6-v1',
          ('wg7',1):'g3-to-g7-v1',('wg7',2):'g4-to-g7-v1',('wg7',3):'g5-to-g7-v1',('wg7',4):'g6-to-g7-v1',('wg7',5):'g7-v1'}


def adapter(scene_revision, plan_version):
    try:return ADAPTERS[scene_revision,plan_version]
    except KeyError:raise GenerationError(f'unsupported scene/plan adapter: {scene_revision}/{plan_version}') from None
