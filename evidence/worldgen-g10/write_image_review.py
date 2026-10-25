"""Bind the agent's visual review notes to exact produced PNGs."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
NOTES={
    'forest':'The scattered G9 trees become a substantial stand with exterior clearings. The retained isolated-arrival finding led to selecting a real boundary component; the dense core and its decorative pockets remain intact.',
    'plains':'Open grass dominates. Tall grass forms larger irregular patches and trees gather at a margin, leaving readable open travel ground.',
    'heath':'Open ground remains dominant with gravel patches and a sparse rock group. Neighboring living cover appears at the deliberate biome transition.',
    'swamp':'Small scattered puddles become broad coherent pools separated by firm ground. The water is the existing walkable, chilling and drinkable shallow-water terrain.',
    'drowned_wood':'Tree stands and large wet patches coexist; the visible open ground between them provides a different route choice from plain forest.',
    'ash_wastes':'Gravel dominates the scene, with the existing ash sprite in patches and rock outcrops. Living cover is restricted to the deliberately blended edge. The interior plant/tree prohibition is checked behaviorally.',
    'mountain':'Independent per-tile rocks become joined rock masses around broken walkable ground. The existing assets and metadata are preserved.',
    'deep_mountain':'Larger rock masses and mineral gaps replace checkerboard rock/gravel. No peak or dungeon content is added; VUKH retains its coarse ownership.'
}


def main():
    p=argparse.ArgumentParser();p.add_argument('--final',type=Path,required=True);a=p.parse_args();final=a.final.resolve()
    run=json.loads((final/'g10/diagnostic/run.json').read_text())
    release=json.loads((final/'release.json').read_text())
    def identity(path):
        raw=path.read_bytes();return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    scenes=[]
    for row in next(r for r in run['runs'] if r['seed']==20261023)['scenes']:
        scenes.append(dict(biome=row['biome'],chunk=row['chunk'],review=NOTES[row['biome']],
            before=identity(ROOT/row['before_image']),after=identity(final/'g10/diagnostic'/row['after_image'])))
    areas=[]
    for row in json.loads((final/'g10/diagnostic/areas.json').read_text())['areas']:
        areas.append(dict(name=row['name'],origin=row['origin'],
            before=identity(final/'g10/diagnostic'/row['before_image']),after=identity(final/'g10/diagnostic'/row['after_image']),
            review='Inspected as a spatial 2x2 production view. Natural masses/patches cross storage boundaries; original roads, authored entrance and coarse river geometry retain their visible authority where present.'))
    normal=[identity(p) for p in sorted((final/'g10/expedition').glob('*normal-fov.png'))]
    result=dict(passed=True,frozen_input_commit=release['frozen_head'],
        method='Visual inspection of actual production PNGs, full-size selected scenes and multi-chunk/contact views. This is a bounded aesthetic judgment, not a checksum/connectivity-derived art pass.',
        visibility='Before/after comparisons explicitly reveal the full scene. The separate ordinary expedition captures retain normal FOV and exploration state.',
        limitations='Saved coarse biome edges and original rectangular river geometry remain visible in places; this arc does not redesign macro geography. Decorative pockets need not all connect. One scripted live outing is not a claim of whole-world fun or survival balance.',
        scenes=scenes,areas=areas,ordinary_normal_fov=normal,
        contact_sheets=[identity(final/'all-biomes-comparison.png'),identity(final/'multi-chunk-comparison.png')])
    (final/'image-review.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
