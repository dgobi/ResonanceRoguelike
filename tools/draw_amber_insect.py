"""Reproduce the two static 16px insect tiles in the existing sprite convention."""
from pathlib import Path
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame

ROOT=Path(__file__).resolve().parents[1]
# White pixels are tinted by the ordinary renderer. Six legs, antennae,
# head/thorax and a split shell; the second frame is the crumpled remains.
LIVE=[
 '................','....#......#....','.....#....#.....','......####......',
 '......#..#......','..##..####..##..','....###..###....','.....######.....',
 '..####.##.####..','.....##..##.....','....###..###....','..##.##..##.##..',
 '.....######.....','......####......','................','................']
DEAD=[
 '................','................','................','................',
 '...#.......#....','....#.#..##.....','.....######.....','...###.##.###...',
 '.....##..##.....','...####..####...','......####......','.....#....#.....',
 '....#......#....','................','................','................']
surface=pygame.Surface((32,16),pygame.SRCALPHA)
for i,rows in enumerate((LIVE,DEAD)):
    for y,row in enumerate(rows):
        for x,p in enumerate(row):
            if p=='#': surface.set_at((16*i+x,y),(255,255,255,255))
pygame.image.save(surface,str(ROOT/'roguelike/assets/sprites/amber_insect.png'))
