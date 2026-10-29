import {it,expect} from 'vitest';
import {resizeBuilding,legendMapping,companionGoals,matchingGoals,entranceCells} from './building';
import {paint,valueEdit,CanvasHistory,editItem,deleteRecord,layoutModel} from './layout';
const source='\ufeff{\r\n "id":"example", "layers":[".\\u0020 ","..."],"legend":{".":"floor"," ":null},"decor_layer":[[null,"dried_herbs",null],[null,null,null]],"special_tiles":[{"type":"item","x":1,"y":1,"item_id":"wood_bundle","nested":{"literal":"a\\nb"}}],"notes":{"keep":[null,"λ"]}\r\n}';
it('resizes complete active decor rows, exact escape spans, absent dimensions and unrelated metadata',()=>{
 const after=resizeBuilding(source,5,3,' '),r=JSON.parse(after.slice(1));
 expect(r.layers).toEqual(['.    ','...  ','     ']);expect(r.decor_layer).toEqual([[null,'dried_herbs',null,null,null],[null,null,null,null,null],[null,null,null,null,null]]);
 expect(after).toContain('.\\u0020 ');expect(after).toContain('"notes":{"keep":[null,"λ"]}');expect(after).toContain('"nested":{"literal":"a\\nb"}');expect(r).not.toHaveProperty('width');expect(after.startsWith('\ufeff{\r\n')).toBe(true);
 const cropped=resizeBuilding(after,3,2,'.');expect(JSON.parse(cropped.slice(1))).toEqual(JSON.parse(source.slice(1)));
});
it('refuses non-null decor, records, full entrance spans, goals and opaque coordinates before changing bytes',()=>{
 expect(()=>resizeBuilding(source,1,2,'.')).toThrow(/special_tiles/);
 const without=valueEdit(source,['special_tiles'],[]);expect(()=>resizeBuilding(without,1,2,'.')).toThrow(/decor_layer/);
 const placement={version:1,contexts:['grid'],weight:1,rotations:[0],mirror_x:false,buffer:0,approach:1,road_relation:'frontage',entrances:[{id:'wide',x:1,y:0,width:2,normal:'N',role:'main',required:true}],targets:[{x:0,y:1,kind:'floor',required:true}]};
 expect(()=>resizeBuilding(valueEdit(without,['placement'],placement),2,2,'.')).toThrow(/span/);
 expect(()=>resizeBuilding(valueEdit(source,['unknown'],{position:[1,2]}),5,3,'.')).toThrow(/unknown/);
 const grown=JSON.parse(resizeBuilding(valueEdit(without,['placement'],placement),4,3,'.').slice(1));expect(grown.placement).toEqual(placement);
});
it('unsupported decor locks only operations needing its representation',()=>{
 const bad=valueEdit(source,['decor_layer'],{opaque:[1,2]});expect(layoutModel(bad).model).not.toBeNull();expect(()=>resizeBuilding(bad,4,3,'.')).toThrow(/representation/);
 expect(()=>paint(bad,[[0,0]],'decor','dried_herbs')).toThrow(/representation/);expect(JSON.parse(paint(bad,[[0,0]],'terrain',' ').slice(1)).decor_layer).toEqual({opaque:[1,2]});
});
it('legend removal checks used and inactive references; mapping rebind deliberately affects every glyph cell',()=>{
 expect(()=>legendMapping(source,'.',null,true)).toThrow(/retained terrain/);
 const added=legendMapping(source,'f','floor');expect(legendMapping(added,'f',null,true)).toBe(source);
 expect(()=>legendMapping(valueEdit(added,['legend_weights'],{f:['wall']}),'f',null,true)).toThrow(/legend_weights/);
 const rebound=JSON.parse(legendMapping(source,'.','flagstone').slice(1));expect(rebound.layers).toEqual(JSON.parse(source.slice(1)).layers);expect(rebound.legend['.']).toBe('flagstone');
});
it('exact matching item/readable companion moves/deletes are one reversible source command',()=>{
 const p={version:1,targets:[{x:1,y:1,kind:'readable',required:true},{x:1,y:1,kind:'container',required:true},{x:0,y:1,kind:'item',required:false}]};
 const before=valueEdit(source,['placement'],p),record=JSON.parse(before.slice(1)).special_tiles[0];expect(matchingGoals(before,record)).toEqual([0]);
 const after=editItem(companionGoals(before,record,[2,1]),0,{x:2,y:1,item_id:'wood_bundle'}),r=JSON.parse(after.slice(1));expect(r.placement.targets[0].x).toBe(2);expect(r.placement.targets.slice(1)).toEqual(p.targets.slice(1));
 const h=new CanvasHistory();h.record(before,after,'move item and exact goal');expect(h.undo(after)).toBe(before);expect(h.redo(before)).toBe(after);
 const deleted=JSON.parse(deleteRecord(companionGoals(before,record,null),0).slice(1));expect(deleted.special_tiles).toEqual([]);expect(deleted.placement.targets).toEqual(p.targets.slice(1));
});
it('entrance overlays include every native span cell in positive source axes',()=>{
 expect(entranceCells({id:'a',x:2,y:3,width:3,normal:'S',role:'main',required:true})).toEqual([[2,3],[3,3],[4,3]]);
 expect(entranceCells({id:'b',x:2,y:3,width:2,normal:'W',role:'service',required:false})).toEqual([[2,3],[2,4]]);
});
