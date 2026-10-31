"""Original creator inputs for historical factory comparisons only.

Never patch loading, serialization, fingerprints, or scene construction. G22's
actual fresh policy is exercised separately; an old synthetic plan envelope must
not accidentally acquire new, foreign report references from its factory shell.
"""
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def historical_start():
    from generation import world_gen
    original = world_gen._place_starting_location
    def laboratory(world, rng):
        original(world, rng)
        lab = world.get(world.start_wx, world.start_wy).submaps[0]
        assert lab.layout_id == 'starting_lab_b'
        lab.layout_id = 'starting_lab'
    with patch.object(world_gen, '_place_starting_location', laboratory), patch(
            'engine.location_reports.bind', return_value=None):
        yield
