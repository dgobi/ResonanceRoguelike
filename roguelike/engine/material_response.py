"""One finite two-band response from an explicitly allocated physical role."""
import copy
from engine import coating_doses


def tier(item, tag):
    return max((r['tier'] for r in getattr(item,'keywords',[]) if isinstance(r,dict)
                and r.get('tag')==tag and type(r.get('tier')) is int and r['tier']>=0),default=0)


def eligible(item, tag, minimum):
    from entities.item import use_capability
    return use_capability(item)!='apply_to_weapon' and tier(item,tag)>=minimum


def configuration(recipe):
    r=recipe.get('material_response')
    if (not isinstance(r,dict) or set(r)!={'version','primary_role','tag','high_tier','low_hits','high_hits'}
            or type(r['version']) is not int or r['version']!=1 or r['primary_role']!='primary'
            or not isinstance(r['tag'],str) or not r['tag']
            or type(r['high_tier']) is not int or not 2<=r['high_tier']<=100
            or any(type(r[k]) is not int or not 1<=r[k]<=coating_doses.MAX_HITS for k in ('low_hits','high_hits'))
            or r['low_hits']>=r['high_hits'] or 'vessel_process' not in recipe):
        raise ValueError('material response: supported primary role and two increasing bounded contact bands required')
    primary=[(n,c) for n,c in enumerate(recipe.get('components',[])) if c.get('role')=='primary']
    if len(primary)!=1:raise ValueError('material response: exactly one primary component required')
    n,c=primary[0]
    if (c.get('tag')!=r['tag'] or type(c.get('quantity',1)) is not int or c.get('quantity',1)!=1
            or type(c.get('min_tier',1)) is not int or not 1<=c.get('min_tier',1)<r['high_tier']
            or any(c.get('role') not in (None,'','primary') for c in recipe.get('components',[]))
            or any(c.get('role') for c in recipe.get('tools',[]))
            or any(c.get('role') for c in (recipe.get('requires_single_item',[]) if isinstance(recipe.get('requires_single_item',[]),list) else recipe['requires_single_item'].get('tags',[])))):
        raise ValueError('material response: primary must occupy one ordinary matching component slot only')
    return r,n


def contacts(response, selected_tier):
    return response['high_hits'] if selected_tier>=response['high_tier'] else response['low_hits']


def resolution(recipe, primary):
    r,n=configuration(recipe)
    if not eligible(primary,r['tag'],recipe['components'][n].get('min_tier',1)):
        raise ValueError('material response: ineligible exact primary')
    t=tier(primary,r['tag'])
    return dict(role=r['primary_role'],item_id=primary.item_id,tag=r['tag'],tier=t,hits=contacts(r,t))


def output(recipe, plan, factory):
    item=factory.create(recipe['result_item'])
    if item is None:raise ValueError('material response: missing output')
    from engine.save_components import serialize_item,validate_item
    p=coating_doses.defined(factory.data.items[item.item_id])
    p['hits']=resolution(recipe,plan.roles['primary'])['hits']
    item.coating_dose=copy.deepcopy(p)
    row=serialize_item(item);validate_item(row,'resolved wash')
    return row
