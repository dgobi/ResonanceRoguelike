"""Every admitted layout crosses the real compiler, fitter and complete scene."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import unittest
from test_effect_persistence import load_data
from generation.placement import transform, entrance_cells, NORMALS
from generation.structure_preview import preview
from generation.plan_preview import planned_preview

COHORT=('house_small_b','house_two_room_a','house_hearth_a','shop_a','apothecary_a',
        'workshop_a','storehouse_a','tool_shed_a','shrine_a','hunter_cabin',
        'shepherds_hut_a','waymarker_shelter_a')


class G5Cohort(unittest.TestCase):
    def test_every_transform_and_documented_assigned_context(self):
        with contextlib.redirect_stdout(io.StringIO()): data=load_data()
        results=[]
        for aid in COHORT:
            raw=data.structures[aid]
            category=next(e.category for e in data.structure_catalog.entries if e.definition.get('id')==aid)
            row=dict(asset=aid,orientations=[],assigned=[])
            for rotation in raw['placement']['rotations']:
                for mirror in ([False,True] if raw['placement']['mirror_x'] else [False]):
                    with self.subTest(asset=aid,rotation=rotation,mirror=mirror):
                        moved=transform(raw,rotation,mirror); p=moved['placement'];e=p['entrances'][0];dx,dy=NORMALS[e['normal']]
                        targets=p['targets']+[dict(x=x,y=y,kind='floor',required=True) for door in p['entrances'] for x,y in entrance_cells(door)]
                        report,m,actors=preview(moved,'ordinary_building',data,category=category,expectations={
                            'entry':dict(x=e['x']+dx,y=e['y']+dy),'targets':targets})
                        self.assertTrue(report['passed'],report['access'])
                        row['orientations'].append(dict(rotation=rotation,mirror=mirror,access=report['access'],receipts=report.get('receipts')))
            for context in raw['placement']['contexts']:
                if context=='compound':
                    # G7 admits this context only within a complete parent.
                    # Exercise the actual authored parent that consumes the asset.
                    from generation.compound_preview import preview as compound_preview
                    recipe=next(r for r in data.compounds.values() if any(a['asset']==aid for s in r['slots'] for a in s['assets']))
                    with contextlib.redirect_stdout(io.StringIO()):
                        report=compound_preview(data,20261023,recipe,normal='S')
                    selected=[p for p in report['plan']['placements'] if p['asset']==aid and p['context']=='compound']
                    self.assertTrue(selected);self.assertTrue(report['previews'])
                    row['assigned'].append(dict(context=context,controlled_pool=True,placements=len(selected),complete_scenes=len(report['previews']),example=selected[0]))
                    continue
                with self.subTest(asset=aid,context=context):
                    selection=copy.deepcopy(data.settlement_profiles)
                    profile=selection['profiles'][context]
                    role=next(r for r,rows in profile['roles'].items() if any(row['asset']==aid for row in rows))
                    profile['roles'][role]=[dict(asset=aid,weight=1.0,max_per_settlement=128)]
                    with contextlib.redirect_stdout(io.StringIO()):
                        report=planned_preview(data,20261023,raw,category=category,context=context,selection=selection)
                    selected=[p for p in report['plan']['placements'] if p['asset']==aid and p['context']==context]
                    self.assertTrue(selected);self.assertTrue(report['previews'])
                    row['assigned'].append(dict(context=context,controlled_pool=True,placements=len(selected),
                        complete_scenes=len(report['previews']),example=selected[0]))
            results.append(row)
        if os.environ.get('RESONANCE_TEST_EVIDENCE_DIR'):
            (Path(os.environ['RESONANCE_TEST_EVIDENCE_DIR'])/'cohort-certification.json').write_text(json.dumps(results,indent=2)+'\n')
