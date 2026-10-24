"""Small versioned native policy; geometry remains owned by the saved plan.

G3 adapters derive context on a copy. Only fresh G4 publication changes Chunk
semantics. Native definitions intentionally resolve by ID at first creation.
"""
import copy
import math
from generation.context import GenerationError, stable_seed

POLICY = 'native-town-v1'


def semantics(world, settlement, data, plan=None):
    from generation.world_gen import BIOME_ZONES
    from world.name_gen import assign_chunk_name
    name, _ = assign_chunk_name('town', stable_seed(world.seed, settlement['id'], 'name'))
    civic = settlement['civic']
    placement = next((p for p in (plan or world.plan)['placements'] if civic and p['id']==civic['placement']), None)
    civic_chunk = [placement['origin'][0]//80, placement['origin'][1]//43] if placement else None
    rows=[]
    for index, xy in enumerate(settlement['members']):
        ch=world.get(*xy)
        role=('civic' if xy==civic_chunk else 'market' if index==0 else 'residential')
        district={'civic':'bell_quarter','market':'market_quarter','residential':'residential'}[role]
        distance=ch.distance_from_peak / math.hypot(world.width//2, world.height//2)
        biome=data.biomes['town']
        rows.append(dict(chunk=xy, role=role, district=district, waystone=role=='civic',
                         zones=copy.deepcopy(BIOME_ZONES['town']),
                         difficulty=min(1.0,biome['difficulty_base']*max(.3,1-distance*.7)*max(.2,1-distance*.8)*1.3),
                         resonance=min(1.0,biome['base_resonance']*max(.3,1-distance*.7))))
    return dict(policy=POLICY,name=name,members=rows)


def effective_context(world, chunk, data):
    from world.world_map import RegionType
    if chunk.region_type != RegionType.TOWN:
        return None, None
    owners=[s for s in world.plan['settlements'] if [chunk.wx,chunk.wy] in s['members']]
    if len(owners)!=1:
        raise GenerationError(f'town ({chunk.wx},{chunk.wy}): expected exactly one saved settlement owner; restore a coherent checkpoint')
    settlement=owners[0]
    context=settlement.get('semantics')
    if context is None:
        if world.plan.get('version')!=1 or world.plan.get('generation_revision')!='wg3':
            raise GenerationError(f'{settlement["id"]}: missing required G4 settlement semantics')
        context=semantics(world,settlement,data)
    member=next((m for m in context['members'] if m['chunk']==[chunk.wx,chunk.wy]),None)
    if member is None: raise GenerationError(f'{settlement["id"]}: missing member policy')
    return settlement,dict(copy.deepcopy(member),policy=context['policy'],name=context['name'])
