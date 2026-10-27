import {spawnSync} from "node:child_process";
import {mkdir,readFile,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
const root=resolve(".artifacts/w5c",`data-fixture-${Date.now()}`);
await mkdir(root,{recursive:true});
const fixture=spawnSync(resolve("worker/runtime/python.exe"),["-X","utf8","-B","-c","import sys;sys.path.insert(0,'worker');from test_texts import text_fixture;text_fixture(sys.argv[1])",root],{stdio:"inherit",windowsHide:true});
if(fixture.status!==0)process.exit(fixture.status || 1);
// The shipped corpus has one writable immediate recipe. A second legitimate
// saved source lives only in this disposable runtime fixture.
const recipe=JSON.parse(await readFile(resolve(root,"roguelike/data/recipes/bile_coating.json"),"utf8"));
recipe.id="w5c_recipe_source";recipe.name="Workspace second recipe";
await writeFile(resolve(root,"roguelike/data/recipes/w5c_recipe_source.json"),JSON.stringify(recipe,null,2));
await writeFile(resolve(".artifacts/w5c/native-fixture.json"),JSON.stringify({root}));
const test=spawnSync(process.execPath,["scripts/desktop-test.mjs"],{stdio:"inherit",windowsHide:true,env:{...process.env,WORKBENCH_TEST_MODE:"workspace",WORKBENCH_TEST_ROOT:root}});
process.exitCode=test.status ?? 1;
