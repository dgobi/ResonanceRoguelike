// Run the existing native capture journey with one reviewed SYS-1 identity fix.
// No production source edits. Fresh captures create fresh vessel UUIDs; cold
// restore checks in the inherited journey still compare every UUID exactly.
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFile,writeFile,unlink,mkdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const repo=resolve(dirname(fileURLToPath(import.meta.url)),'..'),workbench=resolve(repo,'workbench');
const path='workbench/scripts/run-room-tests.mjs',revision='c166ec650b98156d53b8ea72e715c028d27db905';
const source=await readFile(resolve(repo,path),'utf8');
const pinned=spawnSync('git',['show',`${revision}:${path}`],{cwd:repo,encoding:'utf8',windowsHide:true});assert.equal(pinned.status,0);
assert.equal(source.replaceAll('\r\n','\n'),pinned.stdout.replaceAll('\r\n','\n'),'Review changed native harness before adapting');
const needle='assert.deepEqual(o.containers[0].items,box.items);';assert.equal(source.split(needle).length,2);
const replacement=`
 const fresh=o.containers[0].items;
 for(let i=0;i<fresh.length;i++)if(fresh[i].vessel&&box.items[i]?.vessel)assert.notEqual(fresh[i].vessel.id,box.items[i].vessel.id,'reset creates a distinct physical vessel');
 const comparable=items=>items.map(item=>{const value=structuredClone(item);if(value.vessel)delete value.vessel.id;return value;});
 assert.deepEqual(comparable(fresh),comparable(box.items));
 receipt.guide1_reset={fresh_vessel_identity:true,all_other_fields_equal:true,cold_uuid_checks_unchanged:true};
 `;
const hash=createHash('sha256').update(source).digest('hex');
const adapted=source.replace(needle,replacement).replace("const receipt={output,root,",`const receipt={guide1_original_harness_sha256:'${hash}',output,root,`);
await mkdir(resolve(workbench,'.artifacts'),{recursive:true});
const helper=resolve(workbench,'.artifacts',`guide1-room-${Date.now()}.mjs`);
await writeFile(helper,adapted);
try{const r=spawnSync(process.execPath,[helper],{cwd:workbench,windowsHide:true,stdio:'inherit',timeout:300000});process.exitCode=r.status??1;}
finally{await unlink(helper);}
