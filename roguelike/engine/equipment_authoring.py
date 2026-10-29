"""Bounded equipment adapter for the registered item family, never gameplay rules.

Source eligibility and candidate publication are separate checks. Definition-owned
statistics are interpreted by the existing consumers, not copied into ITEM_STATE.
"""
from __future__ import annotations
import json
import math
import re
from collections import Counter
from pathlib import PurePosixPath
from components.inventory import CATEGORY_MAP

I32 = 2**31 - 1
ARMOR_SLOTS = ('armor_head', 'armor_torso', 'armor_arms', 'armor_legs')
# Must remain identical to repair_selected_equipment_use's four shipped exceptions.
LEGACY_BINDINGS = frozenset(('revelation_lens', 'leather_satchel', 'herbalist_pouch', 'component_satchel'))
CATEGORIES = tuple(sorted(set(CATEGORY_MAP.values()) | {'Miscellaneous', 'Light Sources'}))
FIELDS = {
    'weapon': ['damage_dice', 'damage_bonus', 'crit_chance'],
    'armour': ['armor_layers'], 'shield': ['block_chance', 'block_value'],
    'satchel': ['weight_reductions'],
}
SCHEMA = {
    'slot': dict(type='string', title='Armour slot (new variant only)', **{'x-view':'armour', 'x-reference':'armour-slots'}, description='Same-ID edits keep their original slot. A new armour variant may use an existing armour slot.'),
    'damage_dice': dict(type='string', title='Base damage dice', default='1d4', **{'x-view':'weapon'}, description='Positive NdM: 1–100 dice, 1–1,000 sides. Declared base damage; not encounter damage or damage per turn.'),
    'damage_bonus': dict(type='integer', title='Base damage bonus', minimum=-I32, maximum=I32, default=0, **{'x-view':'weapon'}),
    'crit_chance': dict(type='number', title='Additional critical chance', minimum=0, maximum=1, default=0, **{'x-view':'weapon'}, description='Added to the current base critical chance and head-hit bonus; not a final universal probability.'),
    'block_chance': dict(type='number', title='Shield block chance', minimum=0, maximum=1, default=0, **{'x-view':'shield'}),
    'block_value': dict(type='integer', title='Shield reduction', minimum=0, maximum=I32, default=0, **{'x-view':'shield'}),
    'armor_layers': dict(type='array', title='Armour layers', **{'x-view':'armour', 'x-control':'ordered-records'}, items=dict(type='object', required=['name','material','armor_value'], properties={
        'name': dict(type='string', title='Layer name', **{'x-initial':'new layer'}),
        'material': dict(type='string', title='Layer material', **{'x-initial':'leather'}, description='Presentation only; no new material physics.'),
        'armor_value': dict(type='integer', title='Layer AV', minimum=0, maximum=I32, **{'x-initial':0}),
    })),
    'weight_reductions': dict(type='object', title='Carried weight reductions', **{'x-view':'satchel', 'x-control':'keyed-number-map', 'x-reference':'carrying-categories'}, properties={}, additionalProperties=dict(type='number', minimum=0, maximum=1), description='Fractions from 0 to 1. A category overrides all, including zero. Missing all means zero fallback; an empty map gives no reduction. Applies only while this exact owned bag is equipped.'),
}


def finite(value):
    return type(value) in (int, float) and -float('inf') < value < float('inf')


def retained_problems(raw, data=None):
    """Validate the inherited consumer payload; no move/essence editing permission."""
    errors = []
    if 'essence' in raw and raw['essence'] is not None:
        if not isinstance(raw['essence'], str) or raw['essence'] not in ('Dissolution','Quickening','Binding','Severance','Consumption','Revelation'):
            errors.append(('essence', 'Retained singular essence must name an existing production essence.'))
    if 'essence_strength' in raw and (not finite(raw['essence_strength']) or not 0 <= raw['essence_strength'] <= I32):
        errors.append(('essence_strength', 'Retained essence strength must be finite and nonnegative.'))
    if 'movesets' not in raw: return errors
    moves = raw['movesets']
    if not isinstance(moves, list) or len(moves) > 2:
        return errors + [('movesets', 'Retained movesets must be an ordered list of at most two Q/R actions.')]
    ids, keys = set(), set()
    strings = {'id','name','description','key','callout'}
    integers = {'cooldown','range'}
    fractions = {'hp_gate'}
    numbers = {'turn_cost','damage_mult'}
    bool_effects = {'ignore_armour','ignore_dodge','free_move_on_kill','on_kill_only','destroy_armour','reveal_knowledge'}
    int_effects = {'reduce_av','suppress_ability_turns','aoe_disrupt_range','aoe_disrupt_turns','pool_turns','screen_shake','ignore_armour_layers'}
    for i, action in enumerate(moves):
        field = f'movesets[{i}]'
        if not isinstance(action, dict):
            errors.append((field, 'Retained action must be an object.')); continue
        for key in action.keys() - strings - integers - fractions - numbers - {'positioning','effects'}:
            errors.append((field+'.'+key, 'Unsupported retained action property.'))
        for key in strings:
            if key in action and not isinstance(action[key], str): errors.append((field+'.'+key, 'Expected retained text.'))
        aid, key = action.get('id'), action.get('key')
        if not isinstance(action.get('name'),str) or not action['name']: errors.append((field+'.name', 'Retained actions require a nonempty name for cooldown feedback.'))
        if not isinstance(aid,str) or not aid or aid in ids: errors.append((field+'.id', 'Retained actions require distinct nonempty IDs.'))
        else: ids.add(aid)
        if not isinstance(key,str) or key.upper() not in ('Q','R') or key.upper() in keys: errors.append((field+'.key', 'Retained actions require distinct Q/R bindings.'))
        else: keys.add(key.upper())
        for key in integers:
            if key in action and (type(action[key]) is not int or not 0 <= action[key] <= I32): errors.append((field+'.'+key, 'Expected a nonnegative retained integer.'))
        for key in fractions | numbers:
            if key in action and (not finite(action[key]) or not 0 <= action[key] <= (1 if key in fractions else I32) or key=='turn_cost' and action[key]==0): errors.append((field+'.'+key, 'Expected a finite retained number in its consumer range.'))
        if 'positioning' in action and action['positioning'] != 'behind': errors.append((field+'.positioning', 'Only the existing behind positioning is supported.'))
        effects = action.get('effects', {})
        if not isinstance(effects, dict): errors.append((field+'.effects', 'Retained effects must be an object.')); continue
        for key, value in effects.items():
            valid = (type(value) is bool if key in bool_effects else type(value) is int and 0 <= value <= I32 if key in int_effects else isinstance(value,str) and bool(value) if key=='place_pool' else False)
            if not valid: errors.append((field+'.effects.'+key, 'Unsupported or malformed retained effect.'))
            elif key=='place_pool' and data is not None and value not in data.decoratives: errors.append((field+'.effects.'+key, 'Retained pool decor reference is unresolved.'))
    return errors


def classify(raw, path, pointer='', *, forbidden=()):
    parts = PurePosixPath(path).parts
    if not isinstance(raw,dict) or pointer or parts[:3] != ('roguelike','data','items'): return None, 'Requires one unique equipment object in its compatible item route.'
    route = parts[3:-1]
    kind = next((kind for kind, prefix, category, slots in (
        ('weapon',('weapons',),'weapon',('weapon',)), ('armour',('armor',),'armor',ARMOR_SLOTS),
        ('shield',('shields',),'shield',('offhand',)), ('satchel',('equipment','satchel'),'equipment',('satchel',)))
        if route[:len(prefix)] == prefix and raw.get('category')==category and raw.get('slot') in slots), None)
    if kind is None: return None, 'Category, route and compatible equipment slot must agree.'
    permitted = {'slot','movesets','essence','essence_strength'} | set(FIELDS[kind])
    blocked = (set(raw) & (set(forbidden) - permitted)) | {k for k in raw if k.startswith('on_') and k!='on_use'}
    if blocked: return None, 'Inspect-only unsupported equipment behavior: '+', '.join(sorted(blocked))+'.'
    declared = raw.get('on_use')
    if declared != 'equip_toggle' and not (declared is None and isinstance(raw.get('id'),str) and raw['id'] in LEGACY_BINDINGS):
        return None, 'Ordinary equipment requires declared equip_toggle; only the four exact shipped IDs have a legacy missing-handler binding.'
    errors = retained_problems(raw)
    if errors: return None, 'Invalid retained behavior at '+errors[0][0]+': '+errors[0][1]
    return kind, 'Ordinary '+kind+'; retained essence/movesets are read-only, with shared action-ID cooldowns.'


def validate(raw, kind, data):
    errors = retained_problems(raw, data)
    if 'weight' in raw and (not finite(raw['weight']) or not 0 <= raw['weight'] <= 2**53-1):
        errors.append(('weight','Use a finite nonnegative physical weight no larger than the exact JavaScript integer boundary 9007199254740991.'))
    def integer(field, value, minimum=0):
        if type(value) is not int or not minimum <= value <= I32:
            errors.append((field, f'Use an integer from {minimum} to {I32}; booleans are not numbers.'))
    def fraction(field, value):
        if not finite(value) or not 0 <= value <= 1: errors.append((field, 'Use a finite fraction from 0 to 1; booleans and null are not numbers.'))
    if kind=='weapon':
        value = raw.get('damage_dice', '1d4')
        match = re.fullmatch(r'([1-9][0-9]{0,2})[dD]([1-9][0-9]{0,3})', value) if isinstance(value,str) else None
        if not match or not (1 <= int(match[1]) <= 100 and 1 <= int(match[2]) <= 1000):
            errors.append(('damage_dice', 'Use positive NdM with 1–100 dice and 1–1,000 sides; parser fallback is not valid authored damage.'))
        integer('damage_bonus', raw.get('damage_bonus',0), -I32)
        fraction('crit_chance', raw.get('crit_chance',0))
        if match and type(raw.get('damage_bonus',0)) is int and int(match[1])*int(match[2])+abs(raw.get('damage_bonus',0)) > I32:
            errors.append(('damage_bonus', 'Dice plus bonus must stay within signed 32-bit magnitude.'))
    elif kind=='shield':
        fraction('block_chance', raw.get('block_chance',0)); integer('block_value', raw.get('block_value',0))
    elif kind=='armour':
        layers = raw.get('armor_layers')
        if not isinstance(layers,list) or not 1 <= len(layers) <= 32:
            return errors + [('armor_layers', 'Use 1–32 ordered armour layer objects.')]
        for i, row in enumerate(layers):
            field = f'armor_layers[{i}]'
            if not isinstance(row,dict): errors.append((field, 'Expected a layer object.')); continue
            for key in ('name','material'):
                if not isinstance(row.get(key),str) or not row[key].strip(): errors.append((field+'.'+key, 'Use a nonempty presentation string.'))
            integer(field+'.armor_value',row.get('armor_value'))
            if 'coverage' in row: fraction(field+'.coverage',row['coverage'])
        if all(isinstance(r,dict) and type(r.get('armor_value')) is int for r in layers) and sum(r['armor_value'] for r in layers)>I32:
            errors.append(('armor_layers', 'The summed AV must fit a signed 32-bit integer.'))
    elif kind=='satchel':
        reductions = raw.get('weight_reductions', {})
        if not isinstance(reductions,dict): return errors + [('weight_reductions','Use a native JSON object keyed by inventory category labels, or {} for no reduction.')]
        for key,value in reductions.items():
            field = 'weight_reductions.'+key
            if key not in (*CATEGORIES,'all'): errors.append((field, 'Use a production inventory label or all. Raw category IDs are not carrying labels: '+', '.join(CATEGORIES)+'.'))
            fraction(field,value)
    return errors


def authorize(original, candidate, source, target, common):
    kind = next((k for k in FIELDS if candidate.get('category')=={'weapon':'weapon','armour':'armor','shield':'shield','satchel':'equipment'}[k]),None)
    if kind is None: return [] # shared category check supplies the located diagnostic
    allowed = set(common) | set(FIELDS[kind]) | {'id'}
    variant = source != target and candidate.get('id') != original.get('id')
    legacy_variant = variant and original.get('id') in LEGACY_BINDINGS and original.get('on_use') is None
    if legacy_variant: allowed.add('on_use')
    if variant and kind=='armour': allowed.add('slot')
    errors=[]
    for key in set(original) | set(candidate):
        if key not in allowed and ((key in original)!=(key in candidate) or original.get(key)!=candidate.get(key)):
            errors.append((key, 'Retain this original category, slot, handler or inherited metadata unchanged.'))
    if legacy_variant and candidate.get('on_use')!='equip_toggle': errors.append(('on_use','A new-ID legacy equipment variant must explicitly declare "on_use": "equip_toggle"; exact-ID repair does not follow the variant.'))
    if kind=='armour':
        metadata = lambda row: json.dumps({k:v for k,v in row.items() if k not in ('name','material','armor_value')},sort_keys=True)
        available=Counter(metadata(r) for r in original.get('armor_layers',[]) if isinstance(r,dict))
        for i,row in enumerate(candidate.get('armor_layers',[]) if isinstance(candidate.get('armor_layers'),list) else []):
            if not isinstance(row,dict): continue
            signature=metadata(row)
            if signature=='{}': continue # explicit new rows have no coverage/metadata
            if available[signature]<=0: errors.append((f'armor_layers[{i}]','Coverage and inherited row metadata are read-only. Preserve the original record metadata; new layers use presentation fields and AV only.'))
            available[signature]-=1
    return errors


def interpretation(raw, kind):
    """Only declared base interpretation; actual ownership/use has separate evidence."""
    from engine.combat import roll_dice
    from engine.item_system import _sum_item_av
    result=dict(equipment_class=kind, slot=raw['slot'], current_definition_fields=FIELDS[kind], retained={k:raw[k] for k in ('essence','essence_strength','movesets') if k in raw},
        scope='Stored definition and validated effective binding. No owner, action, combat or capacity admission was exercised. Statistics below are not copied by ItemFactory into ITEM_STATE.')
    if kind=='weapon':
        class Endpoint:
            def __init__(self, high): self.high=high
            def randint(self,a,b): return b if self.high else a
        dice=raw.get('damage_dice','1d4');bonus=raw.get('damage_bonus',0) if 'damage_dice' in raw else 0
        result.update(base_range=[roll_dice(dice,Endpoint(False))+bonus,roll_dice(dice,Endpoint(True))+bonus], explanation='Declared base damage through combat.roll_dice plus bonus; essence, criticals, mitigation and inherited moves can change contact damage. Critical chance is additional to base 0.05 and the current head-hit bonus.')
    elif kind=='armour': result.update(summed_av=_sum_item_av(raw), explanation='Summed AV through ItemSystem._sum_item_av. Coverage is read-only declaration: current combat does not select protected parts from it. AV recomputes at equip/restore.')
    elif kind=='shield': result.update(explanation='Incoming attacks read the session definition for block_chance (default 0) and block_value (default 0). Actual incoming-route evidence is separate.')
    else: result.update(explanation='Inventory derives reductions from the current definition only for the exact equipped, owned satchel. Category overrides all (including zero); absent all means zero. Copied physical weights remain intact; capacity gain depends on the actual load.')
    return result
