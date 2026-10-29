// Read-only supplementary packaged screenshots of the final native-published room.
import {spawn,execFileSync} from "node:child_process";
import {mkdir,readFile,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {createHash} from "node:crypto";
import assert from "node:assert/strict";
import {chromium} from "playwright-core";
const journey=JSON.parse(await readFile(resolve(process.argv[2]),"utf8"));assert(journey.passed);
const output=resolve(journey.output,"screenshots"),settings=resolve(output,"settings");await mkdir(settings,{recursive:true});await writeFile(resolve(settings,"project.json"),JSON.stringify({version:1,project_root:journey.root}));
const receipt={root:journey.root,package_sha256:createHash("sha256").update(await readFile(resolve("src-tauri/target/release/resonance-workbench.exe"))).digest("hex"),room_sha256:journey.room_revised.sha256};
assert.equal(receipt.package_sha256,journey.package_sha256);
assert.equal(createHash("sha256").update(await readFile(resolve(journey.root,journey.room_revised.path))).digest("hex"),receipt.room_sha256);
const child=spawn(resolve("src-tauri/target/release/resonance-workbench.exe"),[],{cwd:output,windowsHide:true,stdio:"ignore",env:{...process.env,RESONANCE_WORKBENCH_CONFIG_DIR:settings,WEBVIEW2_USER_DATA_FOLDER:resolve(output,"webview"),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:"--remote-debugging-port=9579 --remote-debugging-address=127.0.0.1"}});receipt.pid=child.pid;
let browser,page;
try{
 for(let i=0;;i++){assert.equal(child.exitCode,null);try{if((await (await fetch("http://127.0.0.1:9579/json/list")).json()).length)break;}catch{}assert(i<160);await new Promise(r=>setTimeout(r,250));}
 browser=await chromium.connectOverCDP("http://127.0.0.1:9579");page=browser.contexts()[0].pages()[0];page.setDefaultTimeout(30000);await page.setViewportSize({width:1700,height:1100});await page.getByTestId("startup-ready").waitFor();
 const idle=()=>page.waitForFunction(()=>!document.querySelector(".status-dot.working"));const b=name=>page.getByRole("button",{name,exact:true}).filter({visible:true});
 await idle();await page.getByLabel("Search ID, name or path").fill(journey.room_revised.path);await page.locator(`[data-asset="${journey.room_revised.path}"]`).click();await idle();
 await b("Authored layout").click();await page.getByTestId("layout-map").scrollIntoViewIfNeeded();await b("Fit layout").click();await page.screenshot({path:resolve(output,"completed-source-room.png")});
 await b("Saved production preview").click();await page.getByTestId("map").filter({visible:true}).scrollIntoViewIfNeeded();for(let i=0;i<8;i++)await b("Zoom in").click();
 await page.locator('[data-testid="authoring"]:visible').getByRole("button",{name:"Problems",exact:true}).click();await page.screenshot({path:resolve(output,"completed-realized-room.png")});
 await page.locator(".placement-decor").scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,"completed-decor-receipts.png")});
 await b("Authored layout").click();await page.getByLabel("Placed record",{exact:true}).selectOption("2");await page.locator(".cell-details").scrollIntoViewIfNeeded();await page.screenshot({path:resolve(output,"completed-furnishing-properties.png")});
 receipt.passed=true;
}finally{await writeFile(resolve(output,"receipt.json"),JSON.stringify(receipt,null,2));if(child.exitCode===null){const exited=new Promise(r=>child.once("exit",r));execFileSync("taskkill",["/PID",String(child.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});await exited;}await browser?.close().catch(()=>{});console.log(JSON.stringify({output,...receipt}));}
