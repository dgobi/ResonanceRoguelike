"""The singleton typography adapter; the game only imports engine.typography."""
from engine.typography import (CONTRACT, PROFILE, ROLES, TypographyError, diagnostic,
                               discover_resources, load_candidate, shape_diagnostics)

USES_FONT_RESOURCES = True
PUBLICATION_NOTE = ("One active project profile. Publish to the same file; fonts apply at the next game initialization. "
                    "Screens cache fonts and metrics. No per-save profiles or live font replacement.")
LIMITATIONS = "Bounded functional glyph repertoire and representative layouts; no universal Unicode or every-screen layout guarantee."
VIEWS = ["typography-roles", "typography-preview"]
SCHEMA = {"$schema":"https://json-schema.org/draft/2020-12/schema", "type":"object", "properties":{
    "id":{"type":"string", "readOnly":True}, "version":{"type":"integer", "readOnly":True},
    **{key:dict(type="string", title=role[0], description=f"{role[4]}. Retained nominal size: {role[2]}.",
               **{"x-reference":"project-fonts"}) for key, role in ROLES.items()}},
    "required":["id", "version", *ROLES], "additionalProperties":True}


def capability(raw, path, pointer=""):
    supported = path == PROFILE and not pointer and not shape_diagnostics(raw)
    return dict(contract=CONTRACT, editable=supported,
                reason="Eligible fixed typography profile; resource errors can be corrected." if supported else
                "Read-only: expected the canonical game_typography version-1 object with thirteen string assignments.")


def authoring_validate(raw, data, path, data_root, *, resource_root):
    if path != PROFILE: return [diagnostic("", "Typography can only target its canonical file.")]
    if resource_root is None: raise ValueError("Verified project resource root is required.")
    try: return load_candidate(resource_root, raw)["diagnostics"]
    except TypographyError as error: return error.diagnostics


def authoring_context(raw, data, path, data_root, identity, digest, *, observe=False, resource_root):
    diagnostics = authoring_validate(raw, data, path, data_root, resource_root=resource_root)
    try: choices = discover_resources(resource_root)
    except (OSError, ValueError) as error:
        choices=[];diagnostics.append(diagnostic("", str(error)))
    return dict(records=[dict(id="game_typography", pointer="", definition=raw if isinstance(raw, dict) else {},
                              capability=capability(raw, path), diagnostics=diagnostics)], fonts=choices)


def reference_options(context): return {"project-fonts":context["fonts"]}


def authoring_evidence(context):
    return dict(semantic_verified=bool(context and context["records"][0]["capability"]["editable"]
                                      and not any(d["severity"]=="error" for d in context["records"][0]["diagnostics"])))


def authoring_preview(raw, data, root, inputs):
    import base64
    import hashlib
    import io
    import os
    if inputs != {}: raise ValueError("Typography preview takes no view inputs.")
    os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    import pygame
    from engine.display_config import DisplayConfig
    from engine.text_authoring import render_reader
    from engine.palette import UI_BACKGROUND, UI_TEXT_MID, UI_TEXT_BRIGHT, OLD_GOLD
    old = os.getcwd()
    try:
        os.chdir(root / "roguelike");pygame.init();pygame.display.set_mode((1,1))
        display = DisplayConfig.from_config();display.init(project_root=root, typography_candidate=raw)
        screen=pygame.Surface((960,960));screen.fill(UI_BACKGROUND)
        label_font=display.font_ui_small
        screen.blit(label_font.render("Game typography / actual production fonts / retained nominal sizes",True,OLD_GOLD),(24,16))
        samples = {"font_ui_large":"The bells beneath the city", "font_ui_normal":"Ordinary prose — the cold grey stone remembers.",
                   "font_ui_small":"Perk ≥ 2 · Inventory • Map — details", "font_ui_tiny":"› Damage 4 × 2 − 1 → 7   ↑ 3 more",
                   "font_deep":"Known Deep Tongue — stone and silence", "font_callout_damage":"-37", "font_callout_status":"SUPPRESSED",
                   "font_callout_creature":"krrr...", "font_callout_crit":"CRITICAL 74", "font_callout_levelup":"LEVEL 2"}
        rows=[]
        for index, role in enumerate(display.typography["roles"]):
            key=role["role"];y=52+index*68
            label=f"{role['label']} / {role['size']} / {role['requested']}"
            screen.blit(label_font.render(label,True,UI_TEXT_MID),(24,y))
            sample=samples.get(key,"The silence after the bells. Aa Bb 0123456789")
            font=getattr(display,key);surface=font.render(sample,True,UI_TEXT_BRIGHT)
            if surface.get_width()>912 or surface.get_height()>42: raise ValueError(f"{key}: specimen exceeds its bounded row.")
            screen.blit(surface,(24,y+24));rows.append(dict(**role,sample=sample,width=surface.get_width(),height=surface.get_height()))
        output=io.BytesIO();pygame.image.save(screen,output,"specimen.png");png=output.getvalue()
        if len(png)>2*1024*1024: raise ValueError("Typography specimen exceeds 2 MiB.")
        specimen=dict(image="data:image/png;base64,"+base64.b64encode(png).decode(), image_sha256=hashlib.sha256(png).hexdigest(),width=960,height=960)
        diagnostics=display.typography["diagnostics"]
        known=next(iter(data.deep_tongue),None)
        text=dict(id="workbench_typography_specimen",title="The bells beneath the city",condition="worn",pages=[dict(
            text="The cold grey stone remembers.\n\nOrdinary prose — a letter left beside the hearth.\n\n"+
                 (f"Known Deep Tongue: {known}.\n\n" if known else "")+"The last line is [DAMAGED]. Another is [REDACTED].", trailing=True)])
        # Isolated loader instance: this fixture never installs authored content.
        data.texts[text["id"]]=text
        reader=render_reader(text,data,root,dict(page=0,scroll=0),typography_candidate=raw,known_words=[known] if known else [])
        return dict(kind="typography-preview",inputs={},specimen=specimen,reader=reader,roles=rows,diagnostics=diagnostics,
                    setup="Candidate singleton profile; thirteen production roles plus an isolated ordinary-letter reader with one known Deep Tongue word. Saved lexicon/UI; no world, personal save or time.",
                    dependencies="candidate profile; selected project font bytes; saved reader resources",fallback=False)
    finally:
        pygame.quit();os.chdir(old)
