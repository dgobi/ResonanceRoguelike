import { syntax } from "./draft";
import { valueEdit, removeValue } from "./layout";

export function creatureModel(text: string): {model: Record<string, unknown> | null; reason: string} {
  if (syntax(text).diagnostics.length) return {model: null, reason: "Correct JSON in Source to resume creature controls. Draft retained."};
  const model = JSON.parse(text.replace(/^\uFEFF/, ""));
  if (!model || typeof model !== "object" || Array.isArray(model)) return {model: null, reason: "One creature object is required. Source retained."};
  return {model, reason: ""};
}
export function creatureValue(text: string, field: string, value: string | number | boolean | string[], profileDefaults?:Record<string,string|number>): string {
  const {model, reason} = creatureModel(text);
  if (!model) throw new Error(reason);
  if (field === 'ai_profile.recipe') {
    if (!profileDefaults || profileDefaults.recipe !== value) throw new Error('Game-owned recipe defaults are unavailable; reopen the source.');
    return valueEdit(text,['ai_profile'],profileDefaults);
  }
  if (field === 'ai_type' && value === 'composite' && model.ai_type !== 'composite') {
    if (!profileDefaults) throw new Error('Game-owned composite defaults are unavailable; reopen the source.');
    let next=valueEdit(text,['ai_type'],value);
    next=valueEdit(next,['ai_profile'],profileDefaults);
    next=valueEdit(next,['can_cross_chunks'],false);
    return valueEdit(next,['can_use_stairs'],false);
  }
  if (field === 'ai_profile.engagement' && value === 'direct_melee') {
    if (!profileDefaults || profileDefaults.recipe !== 'territorial_guard') throw new Error('Territorial defaults are unavailable.');
    let next=valueEdit(text,['ai_profile','engagement'],value);
    for (const key of ['trigger','retreat_distance','hold_opportunities','withdrawal_budget']) next=valueEdit(next,['ai_profile',key],profileDefaults[key]);
    return next;
  }
  const allowed = ["name","description","armour_value","damage_dice","damage_bonus","attack_verb","perception.sight_radius","perception.hearing_radius","perception.sees_in_dark","wander_radius","pursuit_timeout","speed","ai_type","numbing_venom_trait","ai_profile.warning_phases","ai_profile.paralysis_phases","ai_profile.recovery_phases","ai_profile.return_policy","ai_profile.initial_order","ai_profile.follow_spacing","ai_profile.protection_radius"];
  if (field !== "hp") {
    if (![...allowed,"perception.faction","perception.hostile_to","ai_profile.trigger","ai_profile.retreat_distance","ai_profile.hold_opportunities","ai_profile.withdrawal_budget","ai_profile.concealment_budget","ai_profile.unseen_extra_step","ai_profile.no_cover","ai_profile.pursuit_budget","ai_profile.engagement","ai_profile.defended_radius","ai_profile.excursion_radius"].includes(field)) throw new Error("Read-only creature field");
    const path=field.split(".");
    const current=path.reduce<unknown>((v,k)=>v && typeof v === "object" ? (v as Record<string,unknown>)[k] : undefined,model);
    return current===value ? text : valueEdit(text,path,value);
  }
  if (!model.fighter || typeof model.fighter !== "object" || Array.isArray(model.fighter)) throw new Error("Restore the fighter object in Source.");
  // Two persisted authorities, one undoable operation. Never serialize siblings.
  const fighter = model.fighter as Record<string, unknown>;
  if (model.base_hp === value && fighter.max_hp === value) return text;
  return valueEdit(valueEdit(text, ["base_hp"], value), ["fighter", "max_hp"], value);
}

// Registry/defaults come from the game-owned source capability, never a TS schema.
export function responseValue(text:string,id:string,value:boolean|{field:string;value:number},registry:Record<string,Record<string,number>>):string {
  return attachmentValue(text,'enemy_responses',2,id,value,registry);
}

export function maneuverValue(text:string,id:string,value:boolean|{field:string;value:number},registry:Record<string,Record<string,number>>):string {
  return attachmentValue(text,'enemy_maneuvers',1,id,value,registry);
}

export function scavengingValue(text:string,value:boolean|{field:string;value:number},defaults:Record<string,number>):string {
  const {model,reason}=creatureModel(text);if(!model)throw new Error(reason);
  const current=model.enemy_scavenging as Record<string,number>|undefined;
  if(typeof value==='boolean'){
    if(value===!!current)return text;
    return value?valueEdit(text,['enemy_scavenging'],defaults):removeValue(text,['enemy_scavenging']);
  }
  if(!current||!['approach_opportunities','feed_opportunities'].includes(value.field))throw new Error('Enable the supported scavenging attachment first.');
  return current[value.field]===value.value?text:valueEdit(text,['enemy_scavenging',value.field],value.value);
}

export function responseVersion(text:string,version:number,versions:Record<string,string[]>):string {
  if(!versions[String(version)])throw new Error('Unsupported response version.');
  const {model,reason}=creatureModel(text);if(!model)throw new Error(reason);
  const current=model.enemy_responses as {version:number}|undefined;
  if(!current)return valueEdit(text,['enemy_responses'],{version,modules:[]});
  return current.version===version?text:valueEdit(text,['enemy_responses','version'],version);
}

function attachmentValue(text:string,field:string,version:number,id:string,value:boolean|{field:string;value:number},registry:Record<string,Record<string,number>>):string {
  const {model,reason}=creatureModel(text);if(!model)throw new Error(reason);
  if(!registry[id])throw new Error('Game-owned response defaults unavailable.');
  const attachment=model[field] as {version:number;modules:({id:string}&Record<string,unknown>)[]}|undefined;
  const modules=attachment?.modules||[],index=modules.findIndex(m=>m.id===id);
  if(typeof value==='boolean'){
    if(value===(index>=0))return text;
    const next=value?[...modules,{id,...registry[id]}]:modules.filter(m=>m.id!==id);
    return attachment?valueEdit(text,[field,'modules'],next):valueEdit(text,[field],{version,modules:next});
  }
  if(index<0||!(value.field in registry[id]))throw new Error('Unsupported response field.');
  if(modules[index][value.field]===value.value)return text;
  return valueEdit(text,[field,'modules',index,value.field],value.value);
}
