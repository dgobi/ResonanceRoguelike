"""Fixed native settlement membership. Game selection remains the rule owner."""
import copy
import json
from pathlib import Path, PurePosixPath
from engine.pool_authoring import issue, locations
from generation.context import GenerationError
from generation.structure_contract import Diagnostic, StructureError
from generation import settlement_selection

PROFILE = 'roguelike/data/generation/settlement_profiles.json'
DOCUMENT_ID = 'settlement_profiles'
IDENTITY_POLICY = 'fixed-file'
CONTRACT = 'settlement-membership-1'
PRODUCTION_ROUTE = 'settlement_selection'
VIEWS = ['settlement-membership']
TABLES = {'grid': ('residential', 'commercial', 'support'),
          'roadside': ('residential', 'commercial', 'support'), 'landmark': ('landmark',)}
PUBLICATION_NOTE = ('Membership edits affect new world plans. Existing saved plans retain their captured selection, base weights, '
    'IDs, roles and transforms; generated scene caches retain physical state. Same-ID consumed building/pool/item edits still face '
    'the separate pending-surface dependency gate. Save and byte-check reopen before sampling; parked drafts are excluded.')
LIMITATIONS = ('Ordinary saved-input generation and revealed initial construction only. No player use, FOV, discovery frequency, '
    'balance or fit guarantee. Absence alone gives no rejection cause. Landmark is the existing featured one-site consumer.')
SCHEMA = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object',
          'properties': {'version': {'type': 'integer', 'readOnly': True}}, 'additionalProperties': True}


def read_source(path):
    # Match DataLoader._load's UTF-8 decoding, while retaining authoring's strict
    # unique-key/non-finite checks. Never strip a BOM on this native route.
    try:
        text = path.read_bytes().decode('utf-8')
        if text.startswith('\ufeff'):
            raise ValueError('UTF-8 BOM rejected: DataLoader._load uses UTF-8, not UTF-8-sig.')
        def pairs(rows):
            result = {}
            for key, value in rows:
                if key in result: raise ValueError(f'duplicate object key {key!r}')
                result[key] = value
            return result
        def constant(value): raise ValueError('non-finite number '+value)
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, OSError) as error:
        raise StructureError([Diagnostic(**issue(str(path), 'SELECTION_JSON', '', str(error)))]) from error


def load_authoring_data(data_root):
    """Inspection snapshot only: keep a decoder-rejected original inspectable.

    No generation uses this fallback. Preview reloads the strict game loader.
    Invalid editable values do not need a fallback or world generation.
    """
    from engine.data_loader import DataLoader
    class InspectionData(DataLoader):
        def _load(self, relative_path):
            if relative_path == 'generation/settlement_profiles.json':
                try: return super()._load(relative_path)
                except (ValueError, UnicodeError): return {}
            return super()._load(relative_path)
    return InspectionData(str(data_root))


def capability(raw, path, pointer=''):
    supported = path == PROFILE and not pointer and isinstance(raw, dict) and set(raw) == {'version', 'profiles'} \
        and type(raw.get('version')) is int and raw['version'] == 1 and isinstance(raw.get('profiles'), dict) \
        and set(raw['profiles']) == set(TABLES)
    if supported:
        for profile, roles in TABLES.items():
            p = raw['profiles'][profile]
            supported = supported and isinstance(p, dict) and set(p) == {'id', 'roles', 'minimum', 'schedule', 'repeat_multiplier', 'required_fit_budget'} \
                and isinstance(p.get('roles'), dict) and set(p['roles']) == set(roles) | ({'civic'} if profile == 'grid' else set())
    reason = ('Fixed edit-only native version-1 file; only the seven non-civic membership tables may change.' if supported else
              'Requires the exact fixed version-1 {version, profiles} source and native profile/role shape; unsupported originals remain inspect-only.')
    return dict(editable=bool(supported), reason=reason, operations=['edit'] if supported else [])


def source_index(data_root):
    path = data_root / 'generation/settlement_profiles.json'
    try: raw = read_source(path)
    except StructureError: raw = {}
    return {DOCUMENT_ID: [dict(path=PROFILE, pointer='', definition=raw)]} if path.is_file() else {}


def discover_paths(root): return [root / PROFILE] if (root / PROFILE).is_file() else []


def path_problems(data_root):
    # Shared validation stages the data tree at scratch/data, not at a second
    # project root. Check its actual native relative path there as well.
    current = data_root
    parts = PurePosixPath(PROFILE).parts[2:]
    if data_root.parent.name == 'roguelike':
        current = data_root.parent.parent
        parts = PurePosixPath(PROFILE).parts
    for part in parts:
        peers = [p.name for p in current.iterdir() if p.name.casefold() == part.casefold()] if current.is_dir() else []
        if peers != [part]:
            return [issue(PROFILE, 'SOURCE_CASE', '', 'Fixed source is missing or case-ambiguous at '+str(current / part))]
        current = current / part
    return []


def protected(raw):
    value = copy.deepcopy(raw)
    for profile, roles in TABLES.items():
        for role in roles: value['profiles'][profile]['roles'][role] = None
    return value


def authorize_candidate(original, candidate, source, target, *, data=None):
    if source != PROFILE or target != PROFILE or not capability(original, source)['editable']:
        return [issue(source, 'SOURCE_ENTITLEMENT', '', 'Only an admitted original fixed selection file grants edit authority; no variants or alternate targets.')]
    if not capability(candidate, target)['editable']:
        return [issue(target, 'SELECTION_SHAPE', '', 'Preserve native root/version/profile keys and roles; no root id or editor/derived fields.')]
    # Canonical JSON compares types too (True must not equal 1 in policy).
    if json.dumps(protected(original), sort_keys=True) != json.dumps(protected(candidate), sort_keys=True):
        return [issue(target, 'PROTECTED_POLICY', 'profiles', 'Preserve civic membership and every value outside the seven editable role tables.')]
    return []


def saved_buildings(data, data_root):
    from engine.building_authoring import source_index
    from generation.structure_contract import ELIGIBILITY
    index = source_index(data_root); result = []
    for identifier, entries in sorted(index.items()):
        found = locations(index, identifier); source = entries[0]; reason = ''
        loaded = [e for e in data.structure_catalog.entries if e.route == 'ordinary_building' and e.raw.get('id') == identifier]
        if len(found) != 1:
            reason = 'Ambiguous saved building identity: '+', '.join(e['path']+e['pointer'] for e in found)
        elif len(loaded) != 1 or loaded[0].raw != source['definition'] or \
                PurePosixPath(source['path']).parts[3] not in ELIGIBILITY.keys()-{'plaza'} or \
                Path(loaded[0].path).resolve() != (data_root / PurePosixPath(source['path']).relative_to('roguelike/data')).resolve():
            reason = 'Saved ID does not resolve to its exact ordinary-building consumer source.'
        raw = source['definition']; p = raw.get('placement') or {}; contexts = p.get('contexts', [])
        eligible = [c for c in TABLES if c in contexts and p.get('road_relation') != 'remote'] if not reason else []
        result.append(dict(id=identifier, label=str(raw.get('name', raw.get('description', identifier)))+' · '+identifier,
            path=source['path'], pointer=source['pointer'], contexts=contexts, eligible_profiles=eligible,
            placement_weight=p.get('weight'), reason=reason or ('Connected selection rejects remote relation.' if p.get('road_relation') == 'remote' else
                'Missing explicit grid, roadside or landmark placement context.' if not eligible else ''),
            resolved=not bool(reason)))
    return result


def authoring_validate(raw, data, path, data_root):
    errors = path_problems(data_root)
    if path != PROFILE: return errors+[issue(path, 'SOURCE_ENTITLEMENT', '', 'Selection has one fixed target.')]
    try:
        settlement_selection.validate(raw, data)
    except (GenerationError, KeyError, TypeError) as error:
        # Native validator supplies exact context/role/row/field (same consumer).
        message = str(error); location = message.split(': ', 2)[1] if message.startswith('settlement selection: profiles.') else ''
        errors.append(issue(path, 'SELECTION_RULE', location, message))
    refs = {b['id']: b for b in saved_buildings(data, data_root)}
    profiles = raw.get('profiles', {}) if isinstance(raw, dict) else {}
    for profile, p in profiles.items() if isinstance(profiles, dict) else []:
        roles = p.get('roles', {}) if isinstance(p, dict) else {}
        for role, rows in roles.items() if isinstance(roles, dict) else []:
            for n, row in enumerate(rows if isinstance(rows, list) else []):
                aid = row.get('asset') if isinstance(row, dict) else None
                ref = refs.get(aid) if isinstance(aid, str) else None
                if not ref or not ref['resolved']:
                    errors.append(issue(path, 'BUILDING_SOURCE', f'profiles.{profile}.roles.{role}[{n}].asset',
                        f'{aid!r}: '+(ref['reason'] if ref else 'Missing uniquely resolved ordinary saved building source.')))
    return errors


def authoring_context(raw, data, path, data_root, identity, digest, **kwargs):
    cap = capability(raw, path); paths = path_problems(data_root)
    if paths: cap = dict(cap, editable=False, operations=[], reason='; '.join(d['message'] for d in paths))
    return dict(records=[dict(id=DOCUMENT_ID, definition=raw if isinstance(raw, dict) else {}, capability=cap,
                             diagnostics=authoring_validate(raw, data, path, data_root))],
                buildings=saved_buildings(data, data_root), editable_tables=TABLES)


def reference_options(context):
    return {'saved-buildings': [dict(id=b['id'], label=b['label']) for b in context['buildings'] if b['resolved']]}


def authoring_evidence(context):
    return dict(semantic_verified=bool(context and not any(d['severity'] == 'error' for d in context['records'][0]['diagnostics'])))


def authoring_preview(raw, data, root, inputs):
    from generation.selection_preview import preview
    return preview(root, raw, inputs)
