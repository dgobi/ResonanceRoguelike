"""Narrow ordinary held-light Item authoring; use/heat/ownership stay protected."""
import math
from pathlib import PurePosixPath
from engine.held_light import MAX_RADIUS, MAX_FUEL

FIELDS = ['name', 'description', 'tile', 'weight', 'light_radius', 'burn_turns', 'light']
SCHEMA = {
    'light_radius': dict(type='integer', title='Mechanical light reach (tiles)', minimum=1,
        maximum=MAX_RADIUS, **{'x-view':'held light'},
        description='Inclusive obstructed reach. Lights the bearer even at narrow reach; no stealth bonus. Saved with each new owned instance.'),
    'burn_turns': dict(type='integer', title='Held fuel (charged phases)', minimum=1,
        maximum=MAX_FUEL, **{'x-view':'held light'},
        description='One fuel per charged active offhand phase. Consumed on expiry. Free inspection and saves spend none.'),
    'light': dict(type='object', title='Cosmetic light', **{'x-view':'held light','x-control':'bounded-record'},
        properties=dict(falloff=dict(type='number',title='Cosmetic falloff',minimum=.25,maximum=4),
            flicker=dict(type='boolean',title='Cosmetic flicker'))),
}


def supported(raw, path, pointer, forbidden):
    parts=PurePosixPath(path).parts
    return (not pointer and isinstance(raw,dict) and len(parts)==5
        and parts[:4]==('roguelike','data','items','tools')
        and raw.get('category')=='tool' and raw.get('on_use')=='equip_light'
        and raw.get('stackable',False) is False and raw.get('consumed_on_use') is False
        and isinstance(raw.get('light'),dict)
        and not raw.keys() & (forbidden-{'light','light_radius','burn_turns','provides_burning'})
        and not raw.get('qualities') and not raw.get('text_id'))


def authorize(original, candidate):
    problems=[]
    for key in original.keys() | candidate.keys():
        if key in set(FIELDS) | {'id'}:continue
        if (key in original)!=(key in candidate) or original.get(key)!=candidate.get(key):
            problems.append((key,'Keep the source use, offhand role, heat, consumption, tags and metadata unchanged.'))
    old,new=original.get('light',{}),candidate.get('light',{})
    if not isinstance(new,dict):return problems+[('light','Retain the cosmetic light record.')]
    for key in old.keys() | new.keys():
        if key in {'falloff','flicker'}:continue
        if (key in old)!=(key in new) or old.get(key)!=new.get(key):
            problems.append(('light.'+key,'Retain inherited color, visual radius and unsupported visual metadata; mechanical reach is a separate control.'))
    return problems


def validate(raw):
    problems=[]
    for field,maximum in [('light_radius',MAX_RADIUS),('burn_turns',MAX_FUEL)]:
        value=raw.get(field)
        if type(value) is not int or not 1<=value<=maximum:
            problems.append((field,f'Use an integer from 1 to {maximum}.'))
    visual=raw.get('light',{})
    value=visual.get('falloff',1.8)
    if type(value) not in (int,float) or not math.isfinite(value) or not .25<=value<=4:
        problems.append(('light.falloff','Cosmetic falloff must be finite, from 0.25 to 4.'))
    if type(visual.get('flicker',False)) is not bool:
        problems.append(('light.flicker','Cosmetic flicker must be boolean.'))
    return problems
