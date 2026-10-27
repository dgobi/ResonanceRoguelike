import {spawnSync} from "node:child_process";
import {mkdir, readFile, writeFile} from "node:fs/promises";
import {resolve} from "node:path";
const root = resolve(".artifacts/w4a", `data-fixture-${Date.now()}`);
await mkdir(root, {recursive:true});
const fixture = spawnSync(process.env.RESONANCE_PYTHON || resolve("worker/runtime/python.exe"), ["-X","utf8","-B","-c","import sys;sys.path.insert(0,'worker');from test_authoring import data_fixture;data_fixture(sys.argv[1])", root], {stdio:"inherit",windowsHide:true});
if(fixture.status !== 0) process.exit(fixture.status || 1);
// Disposable source metadata is present before opening. The editor must retain it.
const creature=resolve(root,"roguelike/data/entities/creatures/hollow_revenant.json");
const bytes=await readFile(creature,"utf8"), end=bytes.lastIndexOf("}");
await writeFile(creature,bytes.slice(0,end).trimEnd()+',\r\n  "w4a_metadata": {"ordered": [[true, null], ["preserve", 7]]}\r\n'+bytes.slice(end));
const room=JSON.parse(await readFile("../roguelike/docs/examples/g17_authored_creature_room.json","utf8"));room.id="w4a_reference_room";
await writeFile(resolve(root,"roguelike/data/layouts/w4a_reference_room.json"),JSON.stringify(room,null,2));
const test = spawnSync(process.execPath,["scripts/desktop-test.mjs"],{stdio:"inherit",windowsHide:true,env:{...process.env,WORKBENCH_TEST_MODE:"creatures",WORKBENCH_TEST_ROOT:root}});
process.exitCode = test.status || 0;
