"""Finite fastening responses shared by two explicit world-object operations."""
import copy
import math
import re

DEFAULTS = dict(version=1, host_container=True, host_screen=True,
    allow_careful=True, cutting_tier=1, work_steps=3, allow_force=True,
    allow_dissolution=True, dissolution_threshold=0.4,
    screen_careful_yield='wood_bundle')
FIELDS = set(DEFAULTS) | {'id', 'name', 'description'}


def validate(raw, data=None):
    if not isinstance(raw, dict) or set(raw)-FIELDS:
        raise ValueError('Access profile: unsupported fields or non-object profile.')
    p = dict(DEFAULTS, **copy.deepcopy(raw))
    if type(p['version']) is not int or p['version'] != 1:
        raise ValueError('Access profile: only version 1 is supported.')
    if not isinstance(p.get('id'), str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', p['id']):
        raise ValueError('Access profile: use a lowercase identifier, up to 64 characters.')
    for key in ('name', 'description'):
        if not isinstance(p.get(key), str) or not p[key].strip() or len(p[key]) > (80 if key == 'name' else 500):
            raise ValueError(f'Access profile: {key} needs bounded nonempty text.')
    for key in ('host_container', 'host_screen', 'allow_careful', 'allow_force', 'allow_dissolution'):
        if type(p[key]) is not bool:
            raise ValueError(f'Access profile: {key} must be boolean.')
    if not (p['host_container'] or p['host_screen']) or not any(p['allow_'+m] for m in ('careful','force','dissolution')):
        raise ValueError('Access profile: choose a supported host and at least one method.')
    for key, maximum in (('cutting_tier', 5), ('work_steps', 12)):
        if type(p[key]) is not int or not 1 <= p[key] <= maximum:
            raise ValueError(f'Access profile: {key} must be an integer from 1 to {maximum}.')
    value = p['dissolution_threshold']
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 1:
        raise ValueError('Access profile: Dissolution threshold must be finite, greater than zero and at most one.')
    if p['screen_careful_yield'] not in ('', 'wood_bundle'):
        raise ValueError('Access profile: screen cutting yields one wood_bundle or no output.')
    if p['screen_careful_yield'] and not (p['host_screen'] and p['allow_careful']):
        raise ValueError('Access profile: wood yield requires a screen host and careful method.')
    if data is not None and p['screen_careful_yield']:
        from engine.item_factory import ItemFactory
        from engine.harvesting import validate_output
        sources = getattr(data, 'item_definition_sources', {})
        matches = [s for k, ss in sources.items() if k.casefold() == 'wood_bundle' for s in ss]
        if len(matches) != 1:
            raise ValueError('Access profile: wood_bundle must resolve to one saved item definition.')
        validate_output(ItemFactory(data).create('wood_bundle'), 'wood_bundle')
    return p


def load(root, data):
    """Only this new family is strict; historical catalogues retain their policy."""
    from generation.structure_contract import read_document
    profiles, identities = {}, set()
    for path in sorted((root/'access_profiles').rglob('*.json')):
        try:
            p = validate(read_document(path), data)
            if p['id'].casefold() in identities or path.stem != p['id']:
                raise ValueError(f'Access profile: duplicate, case-ambiguous or mismatched identity at {path}.')
        except ValueError as error:
            from generation.structure_contract import StructureError, Diagnostic
            raise StructureError([Diagnostic('error','ACCESS_PROFILE',str(path),'','',str(error),
                'Use one supported version-one fastening profile with unique identity and valid fields.')]) from error
        identities.add(p['id'].casefold())
        profiles[p['id']] = p
    return profiles


def resolve(data, identifier, host):
    p = validate(getattr(data, 'access_profiles', {}).get(identifier), data)
    if p['id'] != identifier or host not in ('container', 'screen') or not p['host_'+host]:
        raise ValueError('Access profile: incompatible host or identity.')
    return p
