"""Mechanical review layouts only: unchanged exports, exact integer enlargement.

No authored sprite pixels or Aseprite files are generated or modified here.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

LAB = Path(__file__).resolve().parents[2]
PREVIEWS = LAB / 'previews'
STEM = 'player_ritual_base_v002'
old = Image.open(LAB / 'exports/player_ritual_base_v001.png').convert('RGBA')
new = Image.open(LAB / 'exports' / (STEM + '.png')).convert('RGBA')
assert old.size == new.size == (32,32)
assert old.getchannel('A').getbbox()[3] == new.getchannel('A').getbbox()[3] == 30
font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
small = ImageFont.truetype('C:/Windows/Fonts/consola.ttf',13)
panel = Image.new('RGB',(640,720),'#10161C')
d = ImageDraw.Draw(panel)
d.text((24,16),'PLAYER / RIGHT-FACING REVISION',font=font,fill='#E4E2D8')
d.text((24,42),'8x nearest-neighbour | full canvas | baseline y=29',font=small,fill='#A2ADA9')
for y,bg,fg,label in [(80,'#191F26','#B4BFBA','DARK'),(400,'#AAAEA9','#303A3F','NEUTRAL')]:
    d.rectangle((16,y,623,y+303),fill=bg)
    d.text((32,y+12),'v001 / earlier experiment',font=small,fill=fg)
    d.text((336,y+12),'v002 / right-facing',font=small,fill=fg)
    for x,im in [(32,old),(336,new)]:
        scaled=im.resize((256,256),Image.Resampling.NEAREST)
        panel.paste(scaled,(x,y+34),scaled)
        # The guide is below row 29, never part of the sprite.
        d.line((x,y+34+240,x+255,y+34+240),fill=fg)
    d.text((536,y+282),label,font=small,fill=fg)
panel.save(PREVIEWS / (STEM+'_comparison_8x.png'))

# Inspect native and 2x pixels against both backgrounds, with a larger view too.
sheet=Image.new('RGB',(640,360),'#10161C')
d=ImageDraw.Draw(sheet)
for x,bg,fg in [(0,'#191F26','#D0D6CB'),(320,'#AAAEA9','#303A3F')]:
    d.rectangle((x,0,x+319,359),fill=bg)
    for dx,y,scale in [(20,28,1),(100,16,2),(32,96,8)]:
        d.text((x+dx,0 if scale<8 else 78),f'{scale}x',font=small,fill=fg)
        scaled=new.resize((32*scale,32*scale),Image.Resampling.NEAREST)
        sheet.paste(scaled,(x+dx,y),scaled)
sheet.save(PREVIEWS / (STEM+'_background_review.png'))
print('Wrote comparison and background review from unchanged MCP PNG exports.')
