import {appendValue,removeValue,valueEdit,stringCharacters,layoutModel,recordKind,type Special,type Cell} from './layout';

export type Entrance={id:string;x:number;y:number;normal:string;width:number;role:string;required:boolean};
export type Goal={x:number;y:number;kind:string;required:boolean};
export type Placement={version:number;contexts:string[];weight:number;rotations:number[];mirror_x:boolean;buffer:number;approach:number;road_relation:string;entrances:Entrance[];targets:Goal[]};
export const entranceCells=(e:Entrance):Cell[]=>Array.from({length:Number.isInteger(e.width)&&e.width>0&&e.width<=80?e.width:0},(_,i)=>[e.x+(['N','S'].includes(e.normal)?i:0),e.y+(['E','W'].includes(e.normal)?i:0)]);
export function legendMapping(source:string,glyph:string,terrain:string|null,remove=false):string {
 const {model:m,reason}=layoutModel(source);if(!m)throw Error(reason);
 if(Array.from(glyph).length!==1)throw Error('Choose one Unicode character.');
 if(remove){
  if(m.layers.some(r=>Array.from(r).includes(glyph)))throw Error('Used mapping affects retained terrain cells; repaint them before removal.');
  if(m.legend_weights!==undefined&&(!m.legend_weights||typeof m.legend_weights!=='object'||Array.isArray(m.legend_weights)))throw Error('Opaque inactive legend_weights prevents safe mapping removal; inspect Source.');
  if(glyph in (m.legend_weights??{}))throw Error('Retained inactive legend_weights still references this glyph; remove that reference deliberately in Source first.');
  return removeValue(source,['legend',glyph]);
 }
 return valueEdit(source,['legend',glyph],terrain);
}
export function resizeBuilding(source:string,width:number,height:number,fill:string):string {
 const {model:m,reason}=layoutModel(source);if(!m)throw Error(reason);
 if(![width,height].every(Number.isInteger)||width<1||height<1||width>80||height>43)throw Error('Resize within 1–80 × 1–43.');
 if(!(fill in m.legend))throw Error('Select an existing fill glyph.');
 const raw=JSON.parse(source.replace(/^\uFEFF/,''));
 if(m.decor_limitation)throw Error(m.decor_limitation+' Resize cannot preserve this representation.');
 const inside=(x:unknown,y:unknown,path:string)=>{if(!Number.isInteger(x)||!Number.isInteger(y)||Number(x)<0||Number(y)<0||Number(x)>=width||Number(y)>=height)throw Error(`Resize strands ${path} at (${x}, ${y}); explicitly move/remove it first.`);};
 const coordinateBearing=(v:unknown):boolean=>!!v&&typeof v==='object'&&(Array.isArray(v)?v.some(coordinateBearing):Object.keys(v).some(k=>['x','y','position','points','cells','bounds'].includes(k))||Object.values(v).some(coordinateBearing));
 const supported=new Set(['layers','legend','decor_layer','special_tiles','placement','width','height','player_start','connection_point','spawn_offset','exit_x','exit_y','exit_direction','legend_weights']);
 for(const [k,v] of Object.entries(raw))if(!supported.has(k)&&coordinateBearing(v))throw Error(`Unsupported coordinate-bearing metadata ${k}; resize is limited until explicitly resolved in Source.`);
 for(const key of ['player_start','connection_point','spawn_offset'])if(key in raw)inside(raw[key]?.x,raw[key]?.y,key);
 for(const key of ['exit_x','exit_y'])if(key in raw&&(!Number.isInteger(raw[key])||raw[key]<0||raw[key]>=(key==='exit_x'?width:height)))throw Error(`Resize strands retained ${key}; explicitly correct it first.`);
 const records=(rows:Special[],path:string)=>rows.forEach((r,i)=>{
  inside(r.x,r.y,`${path}[${i}]`);
  for(const [k,v] of Object.entries(r))if(!['x','y','spawn_table'].includes(k)&&coordinateBearing(v))throw Error(`Unsupported coordinate metadata ${path}[${i}].${k}; resize refused.`);
  if(Array.isArray(r.spawn_table))for(const [n,child] of (r.spawn_table as Special[]).entries()){
   if('x' in child||'y' in child)inside(child.x??r.x,child.y??r.y,`${path}[${i}].spawn_table[${n}]`);
   for(const [k,v] of Object.entries(child))if(!['x','y'].includes(k)&&coordinateBearing(v))throw Error(`Unsupported coordinate metadata ${path}[${i}].spawn_table[${n}].${k}`);
  }
 });records(m.special_tiles??[],'special_tiles');
 if(raw.placement!==undefined){
  const p=raw.placement as Placement;
  if(!p||p.version!==1||Object.keys(p).some(k=>!['version','contexts','weight','rotations','mirror_x','buffer','approach','road_relation','entrances','targets'].includes(k)))throw Error('Unsupported placement profile/fields lock resize; retained exactly in Source.');
  if(!Array.isArray(p.entrances)||!Array.isArray(p.targets))throw Error('Repair placement coordinates before resize.');
  p.entrances.forEach((e,i)=>{inside(e.x,e.y,`placement.entrances[${i}]`);for(const [x,y] of entranceCells(e))inside(x,y,`placement.entrances[${i}].span`);});
  p.targets.forEach((t,i)=>inside(t.x,t.y,`placement.targets[${i}]`));
 }
 m.decor_layer?.forEach((row,y)=>row.forEach((v,x)=>{if(v!==null&&(x>=width||y>=height))throw Error(`Resize would discard non-null decor_layer[${y}][${x}]; erase or move it first.`);}));
 for(let y=0;y<Math.min(height,m.height);y++){
  const next=Array.from(m.layers[y]).slice(0,width).join('')+fill.repeat(Math.max(0,width-m.width));
  if(next!==m.layers[y])source=stringCharacters(source,['layers',y],next);
  if(m.decor_layer){
   for(let x=m.width-1;x>=width;x--)source=removeValue(source,['decor_layer',y,x]);
   for(let x=m.width;x<width;x++)source=appendValue(source,['decor_layer',y],null);
  }
 }
 for(let y=m.height-1;y>=height;y--){source=removeValue(source,['layers',y]);if(m.decor_layer)source=removeValue(source,['decor_layer',y]);}
 for(let y=m.height;y<height;y++){source=appendValue(source,['layers'],fill.repeat(width));if(m.decor_layer)source=appendValue(source,['decor_layer'],Array(width).fill(null));}
 if('width' in raw)source=valueEdit(source,['width'],width);
 if('height' in raw)source=valueEdit(source,['height'],height);
 return source;
}
export function matchingGoals(source:string,record:Special):number[]{
 const p=JSON.parse(source.replace(/^\uFEFF/,''))?.placement;
 if(p?.version!==1||!Array.isArray(p.targets))return [];
 const kind=recordKind(record);
 return p.targets.flatMap((g:Goal,i:number)=>g.x===record.x&&g.y===record.y&&(g.kind===kind||kind==='item'&&g.kind==='readable')?[i]:[]);
}
export function companionGoals(source:string,record:Special,xy:Cell|null):string {
 const indices=matchingGoals(source,record);
 for(const i of [...indices].reverse()){
  if(xy){source=valueEdit(source,['placement','targets',i,'x'],xy[0]);source=valueEdit(source,['placement','targets',i,'y'],xy[1]);}
  else source=removeValue(source,['placement','targets',i]);
 }
 return source;
}
