import {describe,it,expect} from "vitest";
import {readFileSync} from "node:fs";
import {membershipEdit,membershipRow,selectionTables} from "./selection";
import {CanvasHistory} from "./layout";
import {familyProblem,type ContentFamily} from "./content";
const policy=readFileSync(new URL('../../roguelike/data/generation/settlement_profiles.json',import.meta.url),'utf8');
describe('fixed native membership commands',()=>{
  it('edits every permitted table without rewriting untouched spans, escaping, ordering or line endings',()=>{
    const source=policy.replace(/\r?\n/g,'\r\n').replace('"house_small_a"','"house_\\u0073mall_a"');
    for(const [profile,roles] of Object.entries(selectionTables))for(const role of roles){
      const before=JSON.parse(source),old=before.profiles[profile].roles[role][0].weight;
      const next=membershipEdit(source,profile,role,0,'weight',2.25);
      const marker=next.indexOf('2.25'),prefix=next.slice(0,marker),suffix=next.slice(marker+4);
      expect(source.startsWith(prefix)).toBe(true);expect(source.endsWith(suffix)).toBe(true);
      expect(next).toContain('house_\\u0073mall_a');expect(next.split('\r\n').length).toBe(source.split('\r\n').length);
      const changed=JSON.parse(next);changed.profiles[profile].roles[role][0].weight=old;expect(changed).toEqual(before);
      const added=membershipRow(next,profile,role,-1,'saved_variant');expect(JSON.parse(added).profiles[profile].roles[role].at(-1)).toEqual({asset:'saved_variant',weight:1,max_per_settlement:1});
      expect(membershipRow(added,profile,role,JSON.parse(added).profiles[profile].roles[role].length-1)).toBe(next);
    }
    expect(()=>membershipEdit(source,'grid','civic',0,'weight',3)).toThrow(/Protected/);
    expect(()=>membershipRow(source,'landmark','support',-1,'other')).toThrow(/Protected/);
  });
  it('preserves invalid values and shares exact Source/control undo and redo',()=>{
    const h=new CanvasHistory();h.record(policy,membershipEdit(policy,'grid','residential',0,'weight',0),'weight');
    const first=h.undoStack[0].after;
    const malformed='{ "exact": "λ\\n",';h.record(first,malformed,'Source');
    expect(h.undo(malformed)).toBe(first);expect(h.undo(first)).toBe(policy);expect(h.redo(policy)).toBe(first);expect(h.redo(first)).toBe(malformed);
    expect(JSON.parse(first).profiles.grid.roles.residential[0].weight).toBe(0);
  });
  it('negotiates a fixed-file identity without inventing a root ID',()=>{
    const family={id:'selection',contract:'settlement-membership-1',descriptor_sha256:'a'.repeat(64),compatible:true,problems:[],references:{},context:null,effective_operations:['edit'],descriptor:{production_route:'settlement_selection',vocabulary:'resonance-controls-1',views:['settlement-membership'],publication_note:'New plans only',policy:{operations:['edit'],root:'roguelike/data/generation/settlement_profiles.json',identity:'fixed-file'},schema:{$schema:'https://json-schema.org/draft/2020-12/schema',type:'object',properties:{}}}} as ContentFamily;
    expect(familyProblem(family)).toBe('');expect(familyProblem({...family,descriptor:{...family.descriptor,policy:{...family.descriptor.policy,identity:'id'}}})).toMatch(/policy/);
    expect(JSON.parse(policy).id).toBeUndefined();
  });
});
