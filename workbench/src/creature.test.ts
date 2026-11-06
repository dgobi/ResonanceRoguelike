import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { creatureModel, creatureValue, responseValue, responseVersion, maneuverValue, scavengingValue } from "./creature";
import { CanvasHistory } from "./layout";
import { sourceDiff } from "./draft";

describe("ordinary creature exact draft", () => {
  it('captures scavenging tuning with no-op and exact undo while retaining unrelated fields',()=>{
    const source='{"id":"new_eater","metadata":{"retain":true}}',defaults={version:1,approach_opportunities:8,feed_opportunities:3};
    const enabled=scavengingValue(source,true,defaults),tuned=scavengingValue(enabled,{field:'feed_opportunities',value:5},defaults);
    expect(scavengingValue(enabled,true,defaults)).toBe(enabled);
    expect(scavengingValue(tuned,{field:'feed_opportunities',value:5},defaults)).toBe(tuned);
    expect(JSON.parse(tuned).enemy_scavenging.feed_opportunities).toBe(5);
    expect(JSON.parse(tuned).metadata).toEqual({retain:true});
    const history=new CanvasHistory();history.record(enabled,tuned,'Feeding work');expect(history.undo(tuned)).toBe(enabled);
    expect(JSON.parse(scavengingValue(enabled,false,defaults))).toEqual(JSON.parse(source));
    expect(()=>scavengingValue(enabled,{field:'hunger',value:1},defaults)).toThrow();
  });
  it('keeps movement and legacy alarm contracts independent through tune/remove/undo',()=>{
    const original='{"id":"sample","tile":"existing","metadata":{"keep":true},"enemy_responses":{"version":1,"modules":[]}}';
    const registry={seek_lateral_approach:{opportunity_budget:8,expiry_phases:16},regroup_when_wounded:{wounded_percent:50,rearm_percent:75}};
    const flank=maneuverValue(original,'seek_lateral_approach',true,registry);
    const both=maneuverValue(flank,'regroup_when_wounded',true,registry);
    const tuned=maneuverValue(both,'regroup_when_wounded',{field:'wounded_percent',value:40},registry);
    expect(JSON.parse(tuned).enemy_responses.version).toBe(1);
    expect(JSON.parse(tuned).metadata).toEqual({keep:true});
    expect(maneuverValue(tuned,'regroup_when_wounded',true,registry)).toBe(tuned);
    const history=new CanvasHistory();history.record(both,tuned,'Tune injury');expect(history.undo(tuned)).toBe(both);expect(history.redo(both)).toBe(tuned);
    const empty=maneuverValue(maneuverValue(tuned,'regroup_when_wounded',false,registry),'seek_lateral_approach',false,registry);
    expect(JSON.parse(empty).enemy_maneuvers).toEqual({version:1,modules:[]});
    const expanded=responseVersion(empty,2,{'1':['strike_and_withdraw'],'2':['observation_averse']});
    expect(JSON.parse(expanded).enemy_responses.version).toBe(2);
    expect(()=>maneuverValue(flank,'seek_lateral_approach',{field:'code',value:1},registry)).toThrow('Unsupported');
  });
  it('independently attaches and tunes registered responses with exact history and preserved metadata',()=>{
    const text='\uFEFF'+readFileSync(new URL('../../roguelike/data/entities/creatures/grave_skirmisher.json',import.meta.url),'utf8').replace(/\r?\n/g,'\r\n');
    const registry={alarm_call_on_sight:{cooldown_phases:24},investigate_allied_alarm:{opportunity_budget:12}};
    const call=responseValue(text,'alarm_call_on_sight',true,registry),both=responseValue(call,'investigate_allied_alarm',true,registry);
    expect(responseValue(both,'alarm_call_on_sight',true,registry)).toBe(both);
    const tuned=responseValue(both,'investigate_allied_alarm',{field:'opportunity_budget',value:4},registry);
    expect(tuned).toBe(both.replace('"opportunity_budget":12','"opportunity_budget":4'));
    const answer=responseValue(tuned,'alarm_call_on_sight',false,registry),parsed=JSON.parse(answer.slice(1));
    expect(parsed.enemy_responses.modules).toEqual([{id:'investigate_allied_alarm',opportunity_budget:4}]);
    delete parsed.enemy_responses;expect(parsed).toEqual(JSON.parse(text.slice(1)));
    const history=new CanvasHistory();history.record(call,both,'Add answer');expect(history.undo(both)).toBe(call);expect(history.redo(call)).toBe(both);
    expect(()=>responseValue(text,'relay',true,registry)).toThrow('defaults');
    expect(()=>responseValue(call,'alarm_call_on_sight',{field:'player_x',value:4},registry)).toThrow('Unsupported');
  });
  it('tunes escort fields without changing art/body/unknown bytes and restores recipe history',()=>{
    const text=readFileSync(new URL('../../roguelike/data/entities/creatures/ash_escort.json',import.meta.url),'utf8');
    const tuned=creatureValue(creatureValue(text,'ai_profile.initial_order','hold'),'ai_profile.follow_spacing',1);
    const a=JSON.parse(text),b=JSON.parse(tuned);delete a.ai_profile;delete b.ai_profile;expect(a).toEqual(b);
    expect(JSON.parse(tuned).ai_profile.initial_order).toBe('hold');
    const history=new CanvasHistory();history.record(text,tuned,'Escort order and spacing');expect(history.undo(tuned)).toBe(text);expect(history.redo(text)).toBe(tuned);
  });
  const source = readFileSync(new URL("../../roguelike/data/entities/creatures/hollow_revenant.json", import.meta.url), "utf8");
  it("changes both HP authorities with only two focused spans and one history entry", () => {
    const history = new CanvasHistory();
    const edited = creatureValue(source, "hp", 19);
    expect(edited).toBe(source.replace('"base_hp": 14', '"base_hp": 19').replace('"max_hp": 14', '"max_hp": 19'));
    history.record(source, edited, "Effective HP");
    expect(history.undo(edited)).toBe(source); expect(history.redo(source)).toBe(edited);
    expect(sourceDiff(source,edited,"source","variant")).toContain('+  "base_hp": 19');
    const value = JSON.parse(edited), original = JSON.parse(source);
    for(const key of Object.keys(original).filter(k=>!["base_hp","fighter"].includes(k))) expect(value[key]).toEqual(original[key]);
  });
  it("leaves no-op bytes, nested metadata, CRLF and literal prose intact", () => {
    const text = source.replace(/\r?\n/g,"\r\n").replace('"base_hp": 14', '"unknown": { "ordered": [true, null, [1, 2]] },\r\n  "base_hp": 14');
    expect(creatureValue(text,"hp",14)).toBe(text);
    expect(creatureValue(text,"name","Hollow Revenant")).toBe(text);
    expect(creatureValue(text,"name","Revenant variant")).toBe(text.replace('"name": "Hollow Revenant"','"name": "Revenant variant"'));
  });
  it("freezes invalid/duplicate JSON and never repairs an unsupported shape implicitly", () => {
    for(const raw of ['{"id":','{"id":"a","id":"b"}','[]']) {
      expect(creatureModel(raw).model).toBeNull(); expect(()=>creatureValue(raw,"hp",19)).toThrow();
    }
    expect(()=>creatureValue('{"base_hp":14}',"hp",19)).toThrow("fighter");
  });
  it("nested sight and prose edits preserve BOM, key order, escaping and sibling bytes",()=>{
    const original='\uFEFF'+source.replace(/\r?\n/g,"\r\n").replace('"base_hp": 14','"metadata": {"exact":[1e2, "λ\\n", null]},\r\n  "base_hp": 14');
    const sight=creatureValue(original,"perception.sight_radius",3);
    expect(sight).toBe(original.replace(/"sight_radius": \d+/, '"sight_radius": 3'));
    const description=creatureValue(sight,"description",'New "literal" prose');
    expect(JSON.parse(description.slice(1)).description).toBe('New "literal" prose');
    expect(description).toContain('"metadata": {"exact":[1e2, "λ\\n", null]}');
    expect(description.startsWith('\uFEFF')).toBe(true);
    expect(()=>creatureValue(description,"tile","barrow_wight")).toThrow("Read-only");
    expect(JSON.parse(creatureValue(description,"perception.faction","outlaw").slice(1)).perception.faction).toBe("outlaw");
  });
  it("preserves explicit empty relationships and exact sibling metadata",()=>{
    const edited=creatureValue(source,"perception.hostile_to",[]);
    expect(JSON.parse(edited).perception.hostile_to).toEqual([]);
    const next=creatureValue(edited,"perception.hostile_to",["stalker","unmatched"]);
    expect(JSON.parse(next).perception.hostile_to).toEqual(["stalker","unmatched"]);
    const a=JSON.parse(next),b=JSON.parse(source);a.perception.hostile_to=b.perception.hostile_to;
    expect(a).toEqual(b);
  });
  it("keeps independent source histories for two creatures",()=>{
    const wight=readFileSync(new URL("../../roguelike/data/entities/creatures/barrow_wight.json",import.meta.url),"utf8");
    const a=new CanvasHistory(),b=new CanvasHistory();
    const one=creatureValue(source,"damage_dice","2d5"),two=creatureValue(wight,"hp",37);
    a.record(source,one,"attack");b.record(wight,two,"hp");
    expect(a.undo(one)).toBe(source);expect(b.undo(two)).toBe(wight);expect(a.redo(source)).toBe(one);
  });
  it("edits hearing through one exact span and undo without changing source siblings",()=>{
    const text='\uFEFF'+source.replace(/\r?\n/g,'\r\n');
    const changed=creatureValue(text,'perception.hearing_radius',0),history=new CanvasHistory();
    expect(changed).toBe(text.replace('"hearing_radius": 6','"hearing_radius": 0'));
    history.record(text,changed,'Hearing radius');
    expect(history.undo(changed)).toBe(text);expect(history.redo(text)).toBe(changed);
  });
  it('creates local composite variants atomically from game defaults and preserves profile siblings on tuning',()=>{
    const defaults={version:1,recipe:'strike_and_withdraw',capability:'melee',trigger:'hit',retreat_distance:2,hold_opportunities:1,withdrawal_budget:6,cornered:'defensive_melee',scene_scope:'active_scene'};
    expect(()=>creatureValue(source,'ai_type','composite')).toThrow('defaults');
    const next=creatureValue(source,'ai_type','composite',defaults),value=JSON.parse(next);
    expect(value.ai_profile).toEqual(defaults);expect(value.can_cross_chunks).toBe(false);expect(value.can_use_stairs).toBe(false);
    const history=new CanvasHistory();history.record(source,next,'Composite variant');expect(history.undo(next)).toBe(source);
    const tuned=creatureValue(next,'ai_profile.hold_opportunities',0);
    expect(tuned).toBe(next.replace('"hold_opportunities":1','"hold_opportunities":0'));
    expect(()=>creatureValue(tuned,'ai_profile.target_id','player')).toThrow('Read-only');
  });
  it('selects the observation recipe atomically, preserving exact unrelated source and undo',()=>{
    const defaults={version:2,recipe:'observation_averse',capability:'melee',observer:'normal_player_vision',concealment_budget:8,unseen_extra_step:1,no_cover:'defensive_melee'};
    const old=creatureValue(source,'ai_type','composite',{version:1,recipe:'strike_and_withdraw'});
    const next=creatureValue(old,'ai_profile.recipe','observation_averse',defaults);
    expect(JSON.parse(next).ai_profile).toEqual(defaults);
    const a=JSON.parse(old),b=JSON.parse(next);delete a.ai_profile;delete b.ai_profile;expect(a).toEqual(b);
    const history=new CanvasHistory();history.record(old,next,'Recipe');expect(history.undo(next)).toBe(old);expect(history.redo(old)).toBe(next);
    const tuned=creatureValue(next,'ai_profile.unseen_extra_step',0);
    expect(tuned).toBe(next.replace('"unseen_extra_step":1','"unseen_extra_step":0'));
    expect(()=>creatureValue(next,'ai_profile.recipe','planner',defaults)).toThrow('defaults');
  });
  it('selects patient hunt and changes only the policy span with reversible history',()=>{
    const defaults={version:4,recipe:'patient_venom_hunt',capability:'numbing_melee',return_policy:'observed_paralysis'};
    const next=creatureValue(source,'ai_profile.recipe','patient_venom_hunt',defaults);
    const changed=creatureValue(next,'ai_profile.return_policy','after_hold');
    expect(changed).toBe(next.replace('"return_policy":"observed_paralysis"','"return_policy":"after_hold"'));
    const history=new CanvasHistory();history.record(next,changed,'Policy');
    expect(history.undo(changed)).toBe(next);expect(history.redo(next)).toBe(changed);
    const a=JSON.parse(next),b=JSON.parse(source);delete a.ai_profile;expect(a).toEqual(b);
  });
  it('selects a fixed post and atomically restores inactive direct-melee defaults',()=>{
    const defaults={version:5,recipe:'territorial_guard',engagement:'direct_melee',trigger:'hit',retreat_distance:2,hold_opportunities:1,withdrawal_budget:6,defended_radius:4,excursion_radius:6,pursuit_budget:32};
    const post=creatureValue(source,'ai_profile.recipe','territorial_guard',defaults);
    const withdraw=creatureValue(creatureValue(post,'ai_profile.engagement','strike_and_withdraw'),'ai_profile.hold_opportunities',3);
    const direct=creatureValue(withdraw,'ai_profile.engagement','direct_melee',defaults);
    expect(JSON.parse(direct).ai_profile).toEqual(defaults);
    const history=new CanvasHistory();history.record(withdraw,direct,'Engagement');expect(history.undo(direct)).toBe(withdraw);
    const tuned=creatureValue(post,'ai_profile.defended_radius',3);
    expect(tuned).toBe(post.replace('"defended_radius":4','"defended_radius":3'));
    expect(()=>creatureValue(post,'ai_profile.anchor_x',4)).toThrow('Read-only');
  });
});
