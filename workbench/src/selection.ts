import {itemModel,itemValue} from "./item";
import {recordRow} from "./orderedRecords";
import {findNodeAtLocation} from "jsonc-parser";
import {syntax} from "./draft";
export const selectionPath="roguelike/data/generation/settlement_profiles.json";
export const selectionTables:Record<string,string[]>={grid:["residential","commercial","support"],roadside:["residential","commercial","support"],landmark:["landmark"]};
export type Membership={asset:unknown;weight:unknown;max_per_settlement:unknown};
export function selectionModel(text:string){return itemModel(text).model as {version:number;profiles:Record<string,{id:string;roles:Record<string,Membership[]>;minimum:Record<string,number>;schedule:string[];repeat_multiplier:number;required_fit_budget:number}>}|null;}
export function membershipEdit(text:string,profile:string,role:string,index:number,field:"asset"|"weight"|"max_per_settlement",value:unknown){
  if(!selectionTables[profile]?.includes(role))throw new Error("Protected selection table.");
  return itemValue(text,["profiles",profile,"roles",role,index,field],value);
}
export function membershipRow(text:string,profile:string,role:string,index:number,asset?:string){
  if(!selectionTables[profile]?.includes(role))throw new Error("Protected selection table.");
  const path=["profiles",profile,"roles",role];
  if(asset===undefined)return recordRow(text,path,"remove",index);
  const {tree,bom,diagnostics}=syntax(text),array=tree&&findNodeAtLocation(tree,path);
  if(diagnostics.length||array?.type!=="array")throw new Error("Repair the native membership array in Source first.");
  const children=array.children||[],last=children.at(-1);
  const offset=(last?last.offset+last.length:array.offset+1)+bom;
  return text.slice(0,offset)+(last?",":"")+JSON.stringify({asset,weight:1,max_per_settlement:1})+text.slice(offset);
}
