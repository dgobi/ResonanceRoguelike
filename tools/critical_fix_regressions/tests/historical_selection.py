"""Exact pre-G13 selection input for the finite historical comparisons."""
import copy
import hashlib
import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/g13'


def historical_profiles():
    raw = (FIXTURE / 'historical_settlement_profiles.json').read_bytes()
    provenance = json.loads((FIXTURE / 'provenance.json').read_text())
    assert hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest() == provenance['sha256']
    return json.loads(raw)


def historical_data(data):
    bound = copy.copy(data)
    bound.settlement_profiles = historical_profiles()
    # Frozen macro comparisons consume the exact pre-SYS-1 item definition.
    fixture=FIXTURE.parent/'sys1'
    raw=(fixture/'pre-sys1-clay.json').read_bytes()
    provenance=json.loads((fixture/'provenance.json').read_bytes())
    assert hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()==provenance['sha256']
    bound.items=copy.deepcopy(data.items);bound.items['clay_pot']=json.loads(raw)
    return bound
