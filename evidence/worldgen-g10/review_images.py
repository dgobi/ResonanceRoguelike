"""Contact sheet from exact retained production pixels, for visual review."""
import argparse
import hashlib
import json
import os
from pathlib import Path
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame

ROOT=Path(__file__).resolve().parents[2]


def main():
    p=argparse.ArgumentParser();p.add_argument('--final',type=Path,required=True);a=p.parse_args()
    final=a.final.resolve();run=json.loads((final/'g10/diagnostic/run.json').read_text())
    scenes=next(r for r in run['runs'] if r['seed']==20261023)['scenes']
    pygame.init();font=pygame.font.SysFont('Arial',20)
    width=800;height=460;sheet=pygame.Surface((width*2,height*8+55));sheet.fill((16,18,22))
    sheet.blit(font.render('REVEALED production comparisons: G9 left / G10 right — seed 20261023',True,(245,245,245)),(12,12))
    for i,row in enumerate(scenes):
        for column,path in enumerate((ROOT/row['before_image'],final/'g10/diagnostic'/row['after_image'])):
            im=pygame.image.load(str(path));im=pygame.transform.smoothscale(im,(width-8,height-30))
            x=column*width;y=55+i*height
            sheet.blit(font.render(f'{row["biome"]} {row["chunk"]} / '+('G9' if column==0 else 'G10'),True,(230,235,240)),(x+8,y))
            sheet.blit(im,(x+4,y+27))
    pygame.image.save(sheet,str(final/'all-biomes-comparison.png'))
    areas=json.loads((final/'g10/diagnostic/areas.json').read_text())['areas']
    sheet=pygame.Surface((1800,1075));sheet.fill((16,18,22))
    sheet.blit(font.render('REVEALED G10 multi-chunk production views — natural tile pixels touch across seams',True,(245,245,245)),(12,12))
    for i,row in enumerate(areas):
        x=(i%2)*900;y=50+(i//2)*510
        sheet.blit(font.render(row['name']+' '+str(row['origin']),True,(230,235,240)),(x+8,y))
        im=pygame.image.load(str(final/'g10/diagnostic'/row['after_image']))
        sheet.blit(pygame.transform.smoothscale(im,(892,480)),(x+4,y+25))
    pygame.image.save(sheet,str(final/'multi-chunk-comparison.png'))


if __name__=='__main__':main()
