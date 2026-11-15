'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/../webroot/index.html','utf8');
const code=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const cat=fs.readFileSync(__dirname+'/../webroot/catalog.js','utf8');
const nodes={};
function node(id){return nodes[id]||={value:id==='catalogVersion'?'14':'',textContent:'',checked:false,disabled:false,readOnly:false,innerHTML:'',style:{},classList:{toggle(){},add(){},remove(){}},addEventListener(type,cb){this['on'+type]=cb}}}
const commands=[];
const ctx={document:{getElementById:node},Date,Promise,Error,console,confirm:()=>true};ctx.window=ctx;
vm.runInNewContext(cat,ctx,{timeout:2500});
ctx.ksu={moduleInfo:()=>JSON.stringify({moduleDir:'/data/adb/modules/build_fingerprint_date'}),exec(cmd,callback){
 commands.push(cmd);
 const text=cmd.includes("'status'")?'enabled=0\nresetprop=available\ncurrent_fingerprint=google/redfin/redfin:12/SP1A.210812.015/111:user/release-keys\ncurrent_epoch=1704067200\n':cmd.includes('integrityctl.sh')?'baseline_present=no':'Saved';
 Promise.resolve().then(()=>ctx[callback](0,text,''));
}};
vm.runInNewContext(code,ctx,{timeout:3000});
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{
 await tick();await tick();
 assert.equal(node('catalogCount').textContent,'100 stock profiles');
 node('catalogSearch').value='Pixel 5';node('catalogSearch').oninput();
 const d=ctx.FINGERSTORE_CATALOG.find(d=>d.model==='Pixel 5');
 assert.equal(node('catalogDevice').value,d.id);
 assert(node('catalogVersion').innerHTML.includes('value="11"'));
 assert(node('catalogVersion').innerHTML.includes('value="12"'));
 assert(!node('catalogVersion').innerHTML.includes('value="13"'));
 node('catalogVersion').value='11';node('catalogVersion').onchange();
 assert(node('catalogPreview').textContent.includes('Android 11'));
 node('catalogLoad').onclick();
 assert.equal(node('fingerprint').value,ctx.FINGERSTORE_CATALOG_FP(d,'11'));
 assert.equal(node('model').value,'Pixel 5');
 assert.equal(node('date').value,'','unknown build timestamp must not be fabricated');
 assert.equal(node('patch').value,d.builds['11'].patch);
 assert.equal(node('applyMode').value,'reboot');
 await node('apply').onclick();await tick();
 assert(!commands.some(c=>c.includes("'set'")),'build date is mandatory');
 node('date').value='2021-12-01'; // test-only manual user input, not a firmware metadata claim
 await node('apply').onclick();await tick();await tick();
 assert(commands.some(c=>c.includes("'set'")&&c.includes("'reboot'")));
 node('applyMode').value='runtime';node('applyMode').onchange();
 assert(node('applyModeWarning').textContent.includes('UNSTABLE'));
 await node('apply').onclick();await tick();await tick();
 assert(commands.some(c=>c.includes("'set'")&&c.includes("'runtime'")));
 console.log('PASS: dynamic genuine OS versions, exact fingerprint/patch, mandatory timestamp, reboot/runtime apply');
})().catch(e=>{console.error(e);process.exitCode=1});
