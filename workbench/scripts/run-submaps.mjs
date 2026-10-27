import {spawnSync} from "node:child_process";
import {mkdir, readFile, writeFile, copyFile} from "node:fs/promises";
import {resolve} from "node:path";
const root=resolve(".artifacts/w4c",`data-fixture-${Date.now()}`);
await mkdir(root,{recursive:true});
const fixture=spawnSync(resolve("worker/runtime/python.exe"),["-X","utf8","-B","-c","import sys;sys.path.insert(0,'worker');from test_authoring import data_fixture;data_fixture(sys.argv[1])",root],{stdio:"inherit",windowsHide:true});
if(fixture.status!==0)process.exit(fixture.status || 1);
await mkdir(resolve(root,"roguelike/docs/examples"),{recursive:true});
for(const name of ["g17_authored_creature_room.json","g17_authored_creature_room.access.json"])
  await copyFile(resolve("../roguelike/docs/examples",name),resolve(root,"roguelike/docs/examples",name));
// Metadata exists before opening; the graphical workflow must preserve it.
const example=resolve(root,"roguelike/docs/examples/g17_authored_creature_room.json");
const raw=await readFile(example,"utf8");
await writeFile(example,raw.replace('"player_start":','"author_metadata": {"nested":[true,null,[2,1]]},\n  "player_start":').replaceAll("\n","\r\n"));
const test=spawnSync(process.execPath,["scripts/desktop-test.mjs"],{stdio:"inherit",windowsHide:true,env:{...process.env,WORKBENCH_TEST_MODE:"submaps",WORKBENCH_TEST_ROOT:root}});
process.exitCode=test.status ?? 1;
