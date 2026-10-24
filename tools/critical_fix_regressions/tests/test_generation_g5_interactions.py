"""New cohort contents and the authored waystone through production handlers."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import pygame
import test_generation_g4 as gameplay
import test_generation_g4_interactions as interactions
import test_generation_g3_lifecycle as lifecycle
from test_effect_persistence import make_engine
from engine.engine import GameMode
from generation.world_plan import address
from g1_support import fingerprint


class G5Interactions(unittest.TestCase):
    setUpClass=classmethod(gameplay.G4Gameplay.setUpClass.__func__)
    setUp=gameplay.G4Gameplay.setUp
    boot=lifecycle.G3Lifecycle.boot
    visit=interactions.G4Interactions.visit
    interact=interactions.G4Interactions.interact
    render=interactions.G4Interactions.render

    def test_new_container_and_authored_waystone_travel_cold_restore_f9(self):
        e=self.boot();e.debug=False;e.player_invincible=True;e.player.inventory.capacity=100
        plan=e.world_map.plan
        p=next(p for p in plan['placements'] if p['asset']=='apothecary_a');town=address(*p['origin'])[:2]
        self.visit(e,town);target=next(t for t in p['targets'] if t['kind']=='container');xy=(target['x']%80,target['y']%43)
        # Stationary native obstacles isolate the transfer and persistence contract.
        with patch.object(type(e),'_advance_turn',lambda e:e.world_time.advance()):
            before=len(e.local_map.container_state[xy]['items']);self.assertGreater(before,0)
            self.interact(e,xy);self.assertIsNotNone(e.interaction_cursor._selection_prompt)
            e.mode=GameMode.INTERACTION_CURSOR;e._handle_key(pygame.K_RETURN);e.mode=GameMode.LOCAL;e.interaction_cursor._selection_prompt=None
            remaining=len(e.local_map.container_state[xy]['items']);self.assertLess(remaining,before)
            landmark=next(p for p in plan['placements'] if p['asset']=='waymarker_shelter_a');rural=address(*landmark['origin'])[:2]
            out=Path(os.environ['RESONANCE_TEST_EVIDENCE_DIR']) if os.environ.get('RESONANCE_TEST_EVIDENCE_DIR') else self.root
            self.render(e,out/'g5-apothecary-production.png')
            self.visit(e,rural)
            from generation.placement import transform
            from generation.access import enterable
            raw=transform(e.data.structures[landmark['asset']],landmark['rotation'],landmark['mirror'])
            source=next((x,y) for y,row in enumerate(raw['layers']) for x,ch in enumerate(row) if raw['legend'][ch]=='waystone_plinth')
            stone=((landmark['origin'][0]+source[0])%80,(landmark['origin'][1]+source[1])%43)
            self.assertEqual(e.local_map.decor.get(stone),'waystone_plinth')
            self.assertFalse(enterable(e.local_map,stone,e.data));self.interact(e,stone)
            self.assertIn(stone,e.local_map.interacted_waystones);inscription=e.local_map.waystone_inscriptions[stone]
            represented={pos for pos,v in e.local_map.decor.items() if v=='waystone_plinth'}|{stone}
            self.assertEqual(e.local_map.functional_generation['waystones'],len(represented))
            self.render(e,out/'g5-waymarker-production.png')
            self.assertTrue(e.save_manager.save(e),e.save_manager.last_error)
            e.local_map.interacted_waystones.clear()
            reader=make_engine(self.data);self.assertTrue(reader.save_manager.load(reader),reader.save_manager.last_error)
            self.assertIn(stone,reader.local_map.interacted_waystones);self.assertEqual(reader.local_map.waystone_inscriptions[stone],inscription)
            owned=reader._prepare_destination(*town);self.assertEqual(len(owned[0].container_state[xy]['items']),remaining)
            saved=fingerprint(*owned);self.assertIs(reader._prepare_destination(*town)[0],owned[0])
            owned[0].container_state[xy]['items'].clear();reader.debug=False;reader._handle_key_local(pygame.K_F9)
            self.assertEqual(fingerprint(*reader._prepare_destination(*town)),saved)
            (out/'g5-interactions.json').write_text(json.dumps(dict(asset=p['asset'],container=xy,before=before,remaining=remaining,
                landmark=landmark['asset'],authored_waystone=stone,realized_representation='decor (legend terrain converted by layout_stamper._set_tile)',inscription=inscription,cold_load=True,f9=True,
                controls='app-local fixture travel/positioning; stationary AI; production interaction, transfer, save and load handlers'),indent=2)+'\n')
