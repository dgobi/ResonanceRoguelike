"""Existing inventory/interact input route, with explicit measured choices."""
import copy
import pygame
from engine import vessels


def show(e,title,options):
    e._vessel_menu=dict(title=title,options=options,selected=0)


def paid(e,fn):
    if fn():
        from engine.interaction_cursor import InteractionCursor
        e.inventory_screen.open=False
        InteractionCursor._finish_action(e)


def guarded(e,items,fn):
    """An open choice only authorizes the physical contents shown to the player."""
    captured=vessels.context(e);expected=[copy.deepcopy(vessels.state(i)) for i in items]
    def accept():
        try:
            if captured!=vessels.context(e) or any(not vessels.owned(e,i) or vessels.state(i)!=s for i,s in zip(items,expected)):return
        except (ValueError,TypeError,KeyError):return
        return fn()
    return accept


def amounts(e,item,action,*,destination=None,xy=None,captured=None):
    s=vessels.state(item);batch=e.data.recipes.get('resonant_bone_tincture',{}).get('vessel_process',{}).get('water_ml',250)
    available=(s['config']['capacity_ml']-s['water_ml'] if action=='fill' else
               min(s['water_ml'],vessels.state(destination)['config']['capacity_ml']-vessels.state(destination)['water_ml']))
    rows=[(f'One preparation batch: {batch} mL',batch),('250 mL',250),
          (f'Available room and water: {available} mL',available)]
    if action=='transfer':rows.append((f"All source water: {s['water_ml']} mL",s['water_ml']))
    options=[];seen=set()
    for title,n in rows:
        if n in seen:continue
        seen.add(n)
        options.append((title,guarded(e,[item]+([destination] if destination is not None else []),lambda n=n:paid(e,lambda:vessels.handle(e,action,item,n,destination=destination,xy=xy,captured=captured)))))
    show(e,vessels.label(item),options)


def open_item(e,item):
    captured=vessels.context(e)
    def fill():
        px,py=e.player.x,e.player.y
        points=[(x,y) for x in range(px-1,px+2) for y in range(py-1,py+2) if vessels.source(e,(x,y))]
        show(e,'Choose drinking-water source',[(f'Water at ({x}, {y})',guarded(e,[item],lambda xy=(x,y):amounts(e,item,'fill',xy=xy,captured=captured))) for x,y in points])
    def transfer():
        show(e,'Transfer to carried vessel',[(vessels.label(i),guarded(e,[item,i],lambda i=i:amounts(e,item,'transfer',destination=i,captured=captured)))
             for i in e.player.inventory.items if i is not item and vessels.state(i)])
    def empty():
        show(e,f"Discard all {vessels.state(item)['water_ml']} mL?",[
            ('Discard water permanently',guarded(e,[item],lambda:paid(e,lambda:vessels.handle(e,'empty',item,captured=captured))))])
    show(e,vessels.label(item),[(title,guarded(e,[item],fn)) for title,fn in [
        ('Fill from nearby drinking water',fill),('Transfer measured water',transfer),
        ('Drink up to 250 mL',lambda:paid(e,lambda:vessels.handle(e,'drink',item,captured=captured))),
        ('Empty deliberately (discard water)',empty)]])


def offer_job(e,xy):
    from engine.interaction_cursor import InteractionCursor
    job=e.local_map.processing_layer.get(xy)
    if not job or 'vessel_job' not in job or not InteractionCursor.can_reach(e,*xy):return False
    from engine.vessel_jobs import abandon
    captured=vessels.context(e)
    show(e,f"Busy vessel: {job['turns_remaining']} turns remaining",[
        ('Abandon preparation; lose ingredients and water; recover vessel',
         lambda:paid(e,lambda:abandon(e,xy,job,captured)))])
    return True


def key(e,k):
    p=e._vessel_menu;n=len(p['options'])
    if k==pygame.K_ESCAPE:e._vessel_menu=None
    elif k in (pygame.K_UP,pygame.K_KP8):p['selected']=max(0,p['selected']-1)
    elif k in (pygame.K_DOWN,pygame.K_KP2):p['selected']=min(max(0,n-1),p['selected']+1)
    elif k in (pygame.K_RETURN,pygame.K_KP_ENTER) and n:
        fn=p['options'][p['selected']][1];e._vessel_menu=None;fn()


def render(e,surface):
    p=getattr(e,'_vessel_menu',None)
    if p is None:return
    from config import UI_PANEL_INSET
    from engine.palette import UI_TEXT_MID,RESONANCE_GOLD,DEEP_NOTHING,VOID_PURPLE,UI_PANEL_DARK
    font=e.display.font_ui_normal;small=e.display.font_ui_small
    rect=pygame.Rect(0,0,min(820,surface.get_width()-40),min(420,surface.get_height()-40));rect.center=surface.get_rect().center
    e.ui_registry.draw_panel(surface,rect,'weathered_temple',tint_color=VOID_PURPLE,fill_color=DEEP_NOTHING,fill_alpha=255)
    content=rect.inflate(-2*UI_PANEL_INSET,-2*UI_PANEL_INSET);line=font.get_linesize()+8
    hint_top=content.bottom-small.get_linesize()-8
    def text(value,y,color):
        while font.size(value)[0]>content.width and len(value)>3:value=value[:-4]+'...'
        surface.blit(font.render(value,True,color),(content.left,y))
    text(p['title'],content.top,RESONANCE_GOLD)
    visible=max(1,(hint_top-content.top-line-2)//line);start=max(0,p['selected']-visible+1)
    options=p['options'] or [('No eligible choice here.',None)]
    for n,(title,_) in enumerate(options[start:start+visible],start):
        y=content.top+line*(n-start+1)
        if n==p['selected']:pygame.draw.rect(surface,UI_PANEL_DARK,(content.left,y,content.width,line))
        text(title,y,RESONANCE_GOLD if n==p['selected'] else UI_TEXT_MID)
    pygame.draw.line(surface,VOID_PURPLE,(content.left,hint_top),(content.right,hint_top))
    surface.blit(small.render('Up/Down select  Enter accept  Esc cancel (free)',True,UI_TEXT_MID),(content.left,hint_top+4))
