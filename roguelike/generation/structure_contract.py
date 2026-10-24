"""Current structure formats, shared by loaders, stampers and offline authoring.

Validation never repairs or mutates a source document. Compiled defaults live in
a separate copy; unknown fields remain available. No campaign state is read here.
"""
from __future__ import annotations
import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from generation.context import GenerationError

CONTRACT_VERSION = 'g2-1'
ROUTES = ('ordinary_building', 'plaza', 'interior_entrance', 'authored_submap')
ELIGIBILITY = {
    'civic': ['C'], 'religious': ['C'], 'commercial': ['C','N','S','E','W'],
    'residential': ['N','S','E','W','NW','NE','SW','SE'],
    'storage': ['N','S','E','W','NW','NE','SW','SE'],
    'ruins': ['NW','NE','SW','SE'], 'wilderness': ['NW','NE','SW','SE'], 'plaza': ['C'],
}
CAPABILITIES = {
    'ordinary_building': {'active': ['layers','legend','decor_layer','special_tiles'],
        'selection': 'Folder category; row packing uniform among fitting definitions. Corner scatter uses weight.',
        'transforms': ['normal','vertical mirror'],
        'inactive': ['allowed_in','facing','rotatable','tags','interior_loot_table','district_weights','condition','submap','legend_weights','player_start']},
    'plaza': {'active': ['layers','layout','legend','weight'], 'selection': 'Weighted plaza pool in centre C.',
        'transforms': ['normal'], 'inactive': ['allowed_in','decor_layer','special_tiles','rotatable','tags','player_start']},
    'interior_entrance': {'active': ['layers','legend','legend_weights','entrance_type'],
        'selection': 'Uniform variants of entrance_type for supported surface submaps.',
        'transforms': ['normal'], 'inactive': ['variant','connection_point','spawn_offset','edges','decor_layer','special_tiles','player_start']},
    'authored_submap': {'active': ['layers','legend','special_tiles','player_start','exit_direction','exit_x','exit_y'],
        'selection': 'Explicit SubMap.layout_id; no ordinary placement pool.',
        'transforms': ['normal'], 'inactive': ['type','stairs_up','decor_layer','legend_weights','inscription','rotatable','tags']},
}


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    path: str
    asset: str
    field: str
    message: str
    correction: str

    def json(self):
        return asdict(self)


class StructureError(GenerationError):
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        super().__init__('\n'.join(f'{d.path} [{d.asset}] {d.field}: {d.code}: {d.message} Fix: {d.correction}'
                                  for d in diagnostics if d.severity == 'error'))


def read_document(path):
    path = Path(path)
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError(f'duplicate object key {key!r}')
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f'non-finite number {value}')
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, OSError) as error:
        raise StructureError([Diagnostic('error','JSON_READ',str(path),'','',str(error),
                                         'Use UTF-8 JSON with unique keys and finite supported numbers.')]) from error


@dataclass
class CompiledStructure:
    raw: dict
    definition: dict
    route: str
    path: str
    category: str | None
    width: int
    height: int
    diagnostics: list


class Validator:
    def __init__(self, data, path, asset):
        self.data, self.path, self.asset = data, str(path), asset
        self.diagnostics = []

    def issue(self, code, field, message, correction, severity='error'):
        self.diagnostics.append(Diagnostic(severity,code,self.path,self.asset,field,message,correction))

    def numeric(self, value, field, nonnegative=False):
        valid = type(value) in (int,float) and abs(value) <= 2**53-1 and math.isfinite(value)
        if nonnegative: valid = valid and value >= 0
        if not valid:
            self.issue('NUMBER',field,f'Unsupported number {value!r}.','Use a finite supported number'+(' >= 0.' if nonnegative else '.'))
        return valid

    def reference(self, value, table, field):
        if not isinstance(value,str) or not value.strip():
            self.issue('REFERENCE',field,f'Expected nonempty {table} ID, got {value!r}.','Select a catalog ID.')
            return False
        if self.data is not None and value not in getattr(self.data,table):
            self.issue('REFERENCE',field,f'Unknown {table} ID {value!r}.','Select an ID from this data root catalog.')
            return False
        return True

    def coordinate(self, row, field, width, height):
        if not isinstance(row,dict):
            self.issue('COORDINATE',field,'Expected an object with integer x and y.','Use source-grid coordinates.')
            return False
        x,y=row.get('x'),row.get('y')
        if type(x) is not int or type(y) is not int or not (0 <= x < width and 0 <= y < height):
            self.issue('COORDINATE',field,f'({x!r},{y!r}) is outside source {width}x{height} or not integer.',
                       'Move the record inside the source grid before stamping.')
            return False
        return True

    def weights(self, rows, field):
        if not isinstance(rows,list) or not rows:
            self.issue('WEIGHTS',field,'Expected a nonempty array.','Add at least one valid alternative with positive total weight.')
            return False
        weights=[]
        for n,row in enumerate(rows):
            if not isinstance(row,dict):
                self.issue('ROW',f'{field}[{n}]','Expected an object.','Use a record object.'); continue
            value=row.get('weight',1)
            if self.numeric(value,f'{field}[{n}].weight',True): weights.append(value)
        if not weights or not math.isfinite(sum(weights)) or sum(weights)<=0:
            self.issue('WEIGHTS',field,'Total weight must be finite and positive.','Give at least one alternative positive weight.')
        return True

    def pool(self, identifier, field):
        if not self.reference(identifier,'loot_pools',field) or self.data is None: return
        pool=self.data.loot_pools[identifier]
        f=f'{field} -> loot_pools/{identifier}'
        if not isinstance(pool,dict):
            self.issue('POOL',f,'Expected pool object.','Use roll_count and items fields.'); return
        count=pool.get('roll_count',[1,1])
        if (not isinstance(count,list) or not 1 <= len(count) <= 2 or
                any(type(n) is not int or n<0 or n>2**53-1 for n in count) or count[0]>count[-1]):
            self.issue('POOL_COUNT',f+'.roll_count','Expected [min,max] nonnegative integer range.','Use a valid ascending range.')
        rows=pool.get('items',[])
        if rows == []: return
        if not self.weights(rows,f+'.items'): return
        for n,row in enumerate(rows):
            if isinstance(row,dict):
                self.reference(row.get('item_id'),'items',f'{f}.items[{n}].item_id')
                for key in set(row)-{'item_id','weight'}:
                    self.issue('INACTIVE_POOL_FIELD',f'{f}.items[{n}].{key}','Retained; loot roller does not consume this field.',
                               'Use a supported item record for explicit text binding.','warning')

    def special(self, row, field, width, height, parent=None):
        if not isinstance(row,dict):
            self.issue('RECORD',field,'Expected special object.','Use item/container/scene/empty/weighted.'); return
        kind=row.get('type',row.get('kind'))
        if 'kind' in row and 'type' in row and row['kind'] != row['type']:
            self.issue('KIND_CONFLICT',field,'type and kind disagree.','Use one matching kind.')
        if parent is None: self.coordinate(row,field,width,height)
        elif any(k in row and row[k] != parent.get(k) for k in ('x','y')) or any(k in row and type(row[k]) is not int for k in ('x','y')):
            self.issue('CHOICE_COORDINATE',field,'Weighted alternative cannot override enclosing coordinates.',
                       'Remove alternative x/y or use the exact enclosing integer coordinates.')
        if kind == 'weighted':
            if parent is not None:
                self.issue('WEIGHTED_NESTING',field,'Nested weighted alternatives are unsupported.','Flatten to one level.'); return
            rows=row.get('spawn_table')
            if self.weights(rows,field+'.spawn_table'):
                for n,choice in enumerate(rows): self.special(choice,f'{field}.spawn_table[{n}]',width,height,row)
        elif kind == 'item':
            self.reference(row.get('item_id'),'items',field+'.item_id')
            if 'text_id' in row:
                ok=self.reference(row['text_id'],'texts',field+'.text_id')
                if ok and self.data is not None:
                    self.reference(self.data.text_item_map.get(row['text_id'],'letter'),'items',field+'.text_item_map')
        elif kind == 'container':
            identifier=row.get('decor_id','crate')
            ok=self.reference(identifier,'decoratives',field+'.decor_id')
            if ok and self.data is not None and self.data.decoratives[identifier].get('container') is not True:
                self.issue('CONTAINER_CAPABILITY',field+'.decor_id',f'{identifier!r} is not container decor.','Choose a catalog container, such as crate.')
            pools=row.get('loot_pools',[])
            if not isinstance(pools,list): self.issue('POOL_LIST',field+'.loot_pools','Expected a list.','Use [] for no loot.')
            else:
                for n,identifier in enumerate(pools): self.pool(identifier,f'{field}.loot_pools[{n}]')
        elif kind == 'scene':
            identifier=row.get('scene_id')
            if self.reference(identifier,'scenes',field+'.scene_id') and self.data is not None:
                scene=self.data.scenes[identifier]
                rows=scene.get('floor_objects',[]) if isinstance(scene,dict) else None
                if not isinstance(rows,list):
                    self.issue('SCENE_ROWS',field+'.floor_objects',f'Scene {identifier!r} needs item rows.','Use an array of {item_id} objects.')
                else:
                    for n,entry in enumerate(rows):
                        f=f'{field} -> scenes/{identifier}.floor_objects[{n}]'
                        if not isinstance(entry,dict): self.issue('SCENE_ROW',f,'Expected an item object.','Use {item_id: catalog ID}.')
                        else:
                            self.reference(entry.get('item_id'),'items',f+'.item_id')
                            if set(entry)-{'item_id'}: self.issue('SCENE_FIELDS',f,'Scene rows only consume item_id.','Remove unsupported row fields or use direct specials.')
        elif kind in ('body','stele') and parent is None:
            self.issue('DEFERRED_SPECIAL',field,f'{kind} physical behavior is deferred; submap stele text metadata is retained.',
                       'Use supported item/scene records for physical contents.','warning')
            if kind == 'stele' and 'text_id' in row: self.reference(row['text_id'],'texts',field+'.text_id')
        elif kind != 'empty':
            self.issue('SPECIAL_KIND',field,f'Unsupported special kind {kind!r}.','Use item/container/scene/empty or one-level weighted; body/stele only at top level.')


def compile_structure(raw, route, data=None, *, path='<memory>', category=None):
    v=Validator(data,path,raw.get('id','') if isinstance(raw,dict) else '')
    if route not in ROUTES: v.issue('ROUTE','',f'Unknown route {route!r}.','Select an explicit supported route.')
    if not isinstance(raw,dict):
        v.issue('ROOT','','Structure root must be one JSON object.','Split lists into individual object files.')
        raise StructureError(v.diagnostics)
    identifier=raw.get('id')
    if not isinstance(identifier,str) or not identifier.strip(): v.issue('ID','id','Expected nonempty string ID.','Assign a unique asset ID.')
    # Include unknown metadata in numeric safety without coercing it.
    def numbers(value,field):
        if type(value) in (int,float): v.numeric(value,field)
        elif isinstance(value,dict):
            for k,x in value.items(): numbers(x,field+'.'+k)
        elif isinstance(value,list):
            for n,x in enumerate(value): numbers(x,f'{field}[{n}]')
    numbers(raw,'$')
    if route=='ordinary_building' and (not isinstance(category,str) or category not in ELIGIBILITY.keys()-{'plaza'}):
        v.issue('CATEGORY','category','Ordinary building requires an existing folder category.','Specify the intended category explicitly.')
    if category is not None and 'category' in raw and raw['category'] != category:
        v.issue('FOLDER_CATEGORY','category',f'Folder category {category!r} controls eligibility, metadata is {raw["category"]!r}.',
                'Align metadata deliberately; changing metadata alone does not move a pool.','warning')
    if 'layout' in raw and 'layers' in raw and raw['layout'] != raw['layers']:
        v.issue('LAYOUT_CONFLICT','layout','layout and layers disagree.','Keep one matching terrain grid.')
    if route!='plaza' and 'layers' not in raw and 'layout' in raw:
        v.issue('LAYOUT_ALIAS','layout','Only the plaza route consumes this alias.','Explicitly rename layout to layers, then validate.')
    rows=raw.get('layers',raw.get('layout') if route=='plaza' else None)
    valid_rows=isinstance(rows,list) and bool(rows) and all(isinstance(r,str) and r for r in rows)
    if not valid_rows:
        v.issue('GRID','layers','Expected nonempty array of nonempty strings.','Provide a rectangular character grid.')
        rows=[]
    w,h=max(map(len,rows),default=0),len(rows)
    if rows and any(len(r)!=w for r in rows): v.issue('RAGGED_GRID','layers',f'Row widths differ: {[(n,len(r)) for n,r in enumerate(rows) if len(r)!=w]}; maximum {w}.','Explicitly pad with a null-mapped character; do not crop or floor-fill.')
    for key,size in [('width',w),('height',h)]:
        if key in raw and (type(raw[key]) is not int or raw[key]!=size): v.issue('DIMENSION',key,f'Declared {raw[key]!r}, row-derived {size}.','Set the declared dimension to the actual grid extent.')
    if w>80 or h>43: v.issue('RUNTIME_SIZE','layers',f'{w}x{h} exceeds current 80x43 local map.','Reduce geometry explicitly before installation.')
    legend=raw.get('legend')
    used=set(''.join(rows))
    if not isinstance(legend,dict):
        v.issue('LEGEND','legend','Expected object.','Map one-character keys to terrain IDs or null.'); legend={}
    for char,value in legend.items():
        f=f'legend[{char!r}]'
        if len(char)!=1 or value is not None and not isinstance(value,str):
            v.issue('LEGEND_ENTRY',f,'Expected one-character key and string/null value.','Use full terrain IDs or null.'); continue
        if value is not None and data is not None and value not in data.terrain:
            v.issue('TERRAIN_USED' if char in used else 'TERRAIN_UNUSED',f,f'Unknown terrain {value!r}; '+('used in grid.' if char in used else 'unused legend entry.'),
                    'Select an existing terrain ID.', 'error' if char in used else 'warning')
    for char in sorted(used-set(legend)): v.issue('LEGEND_MISSING','layers',f'Character {char!r} has no legend entry.','Add its terrain or null mapping.')
    if 'decor_layer' in raw:
        decor=raw['decor_layer']
        if not isinstance(decor,list) or len(decor)!=h or any(not isinstance(r,list) or len(r)!=w for r in decor):
            v.issue('DECOR_GRID','decor_layer','Expected matching nested arrays of full IDs/null.','Use one array per terrain row; never strings.')
        else:
            for y,row in enumerate(decor):
                for x,value in enumerate(row):
                    if value is not None: v.reference(value,'decoratives',f'decor_layer[{y}][{x}]')
    weights=raw.get('legend_weights',{})
    if not isinstance(weights,dict): v.issue('LEGEND_WEIGHTS','legend_weights','Expected object.','Map a legend character to weighted {tile,weight} rows.')
    else:
        for char,choices in weights.items():
            field=f'legend_weights[{char!r}]'
            if len(char)!=1 or char not in legend: v.issue('LEGEND_WEIGHTS',field,'Expected a defined legend character.','Define the fixed fallback in legend.')
            if v.weights(choices,field):
                for n,row in enumerate(choices):
                    if isinstance(row,dict):
                        if 'tile' not in row: v.issue('LEGEND_WEIGHT_TILE',f'{field}[{n}].tile','Missing tile.','Supply a terrain ID or explicit null.')
                        elif row['tile'] is not None: v.reference(row['tile'],'terrain',f'{field}[{n}].tile')
    for field in ('player_start','connection_point','spawn_offset'):
        if field in raw: v.coordinate(raw[field],field,w,h)
    if route=='interior_entrance':
        if not isinstance(raw.get('entrance_type'),str) or not raw['entrance_type']: v.issue('ENTRANCE_TYPE','entrance_type','Expected nonempty type.','Use a supported entrance type from the catalog.')
        if 'edges' in raw and (not isinstance(raw['edges'],list) or any(x not in ('north','south','east','west') for x in raw['edges'])):
            v.issue('EDGES','edges','Expected cardinal edge names.','Use an array of north/south/east/west; interior placement ignores it.')
    if route=='authored_submap':
        if 'exit_direction' in raw and raw['exit_direction'] not in ('north','south','east','west'): v.issue('EXIT','exit_direction','Invalid direction.','Choose a cardinal direction.')
        for key,size in [('exit_x',w),('exit_y',h)]:
            if key in raw and (type(raw[key]) is not int or not 0<=raw[key]<size): v.issue('COORDINATE',key,'Exit coordinate outside source.','Use an integer in the source grid.')
    specials=raw.get('special_tiles',[])
    if not isinstance(specials,list): v.issue('SPECIALS','special_tiles','Expected array.','Use ordered special records.')
    else:
        for n,row in enumerate(specials): v.special(row,f'special_tiles[{n}]',w,h)
    if 'weight' in raw: v.numeric(raw['weight'],'weight',True)
    if 'placement' in raw and valid_rows and isinstance(legend,dict):
        from generation.placement import validate_profile
        try: validate_profile(raw,w,h)
        except (GenerationError,KeyError,TypeError) as error:
            v.issue('PLACEMENT','placement',str(error),'Use the documented version-one placement profile.')
    for field in CAPABILITIES.get(route,{}).get('inactive',[]):
        if field in raw: v.issue('INACTIVE_FIELD',field,f'Retained; {route} does not consume this field.',
                                 'See the route capability table; editing it does not activate behavior.','warning')
    if any(d.severity=='error' for d in v.diagnostics): raise StructureError(v.diagnostics)
    definition=copy.deepcopy(raw)
    def defaults(row):
        if row.get('type',row.get('kind'))=='container':
            row.setdefault('decor_id','crate'); row.setdefault('loot_pools',[])
        if row.get('type',row.get('kind'))=='weighted':
            for choice in row['spawn_table']: defaults(choice)
    for row in definition.get('special_tiles',[]): defaults(row)
    return CompiledStructure(copy.deepcopy(raw),definition,route,str(path),category,w,h,v.diagnostics)


class StructureCatalog:
    def __init__(self,data):
        self.root=Path(data.root).resolve()
        self.entries=[]
        self.diagnostics=[]
        records=[]; identifiers={}
        for folder,route in [('buildings','ordinary_building'),('entrances','interior_entrance'),('layouts','authored_submap')]:
            for path in sorted((self.root/folder).rglob('*.json')):
                relative=path.relative_to(self.root/folder)
                if len(relative.parts)!=(2 if folder=='buildings' else 1):
                    self.diagnostics.append(Diagnostic('error','INSTALL_PATH',str(path),'','',
                        'Structure is outside an immediate supported catalog folder.',
                        'Use buildings/<existing-category>/<id>.json, entrances/<id>.json or layouts/<id>.json.'))
                    continue
                category=relative.parts[0] if folder=='buildings' else None
                profile='plaza' if category=='plaza' else route
                try: raw=read_document(path)
                except StructureError as e: self.diagnostics.extend(e.diagnostics); continue
                records.append((raw,profile,path,category))
                if isinstance(raw,dict) and isinstance(raw.get('id'),str):
                    identifiers.setdefault((folder,raw['id']),[]).append(path)
        for (_,identifier),paths in sorted(identifiers.items()):
            if len(paths)>1:
                self.diagnostics.append(Diagnostic('error','DUPLICATE_ID','; '.join(map(str,paths)),identifier,'id',
                    'Duplicate ID across these source files.','Give each structure in this namespace a unique ID.'))
        for raw,route,path,category in records:
            try:
                entry=compile_structure(raw,route,data,path=path,category=category)
                self.entries.append(entry); self.diagnostics.extend(entry.diagnostics)
            except StructureError as e: self.diagnostics.extend(e.diagnostics)
        if any(d.severity=='error' for d in self.diagnostics): raise StructureError(self.diagnostics)
        self.by_route={r:{} for r in ROUTES}
        for entry in self.entries: self.by_route[entry.route][entry.raw['id']]=entry
        self.identity=hashlib.sha256(json.dumps([
            (str(p.relative_to(self.root)).replace('\\','/'),hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(self.root.rglob('*.json'))],separators=(',',':')).encode()).hexdigest()

    def manifest(self):
        return {'version':CONTRACT_VERSION,'identity':self.identity,'routes':CAPABILITIES,'eligibility':ELIGIBILITY,
                'assets':[{'id':e.raw['id'],'route':e.route,'category':e.category,'width':e.width,'height':e.height,
                           'path':str(Path(e.path).relative_to(self.root)).replace('\\','/')}
                          for e in self.entries], 'diagnostics':[d.json() for d in self.diagnostics]}
