'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/../webroot/index.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const nodes={};
function node(id){return nodes[id] ||= {value:'',checked:false,disabled:false,readOnly:false,textContent:'',style:{},classList:{names:new Set(),toggle(k,on){if(on)this.names.add(k);else this.names.delete(k)},add(...k){k.forEach(x=>this.names.add(x))},remove(...k){k.forEach(x=>this.names.delete(x))}},setAttribute(){},focus(){},addEventListener(ev,cb){this['on'+ev]=cb}}}
const fp='samsung/a24nsxx/a24:16/UP1A.250605.014/A245FXXU9EYK1:user/release-keys';
const record={enabled:'1',fingerprint:fp,epoch:'1762905600',patch:'2025-10-01',partitions:'1',autofill:'1',brand:'samsung',device:'a24',model:'SM-A245F',name:'a24nsxx',manufacturer:'samsung',current_brand:'samsung',current_device:'a24',current_model:'SM-A245F',current_name:'a24nsxx',current_manufacturer:'samsung',current_fingerprint:fp,current_epoch:'1762905600',current_patch:'2025-10-01',resetprop:'available'};
const captured=[];
const ctx={document:{getElementById:node},Date,Promise,Error,console,confirm:()=>true};ctx.window=ctx;
ctx.ksu={moduleInfo:()=>JSON.stringify({moduleDir:'/data/adb/modules/build_fingerprint_date'}),exec(command,callback){
  captured.push(command);const response=Object.entries(record).map(([k,v])=>`${k}=${v}`).join('\n');
  Promise.resolve().then(()=>ctx[callback](0,response,''));
}};
vm.runInNewContext(script,ctx,{timeout:3000});
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{
  await tick();
  assert.equal(node('currentModel').textContent,'SM-A245F');
  assert.equal(node('currentName').textContent,'a24nsxx');
  assert(node('propertyCheck').textContent.includes('Saved values match active Android properties'));
  assert(node('propertyCheck').classList.names.has('success'));
  assert(node('fingerprintGuide').textContent.includes('product a24nsxx'));
  assert(node('fingerprintGuide').textContent.includes('Recognized model SM-A245F'));
  // The earlier screenshot gave reversed advice: detect this with a non-destructive warning.
  node('autofill').checked=false; node('autofill').onchange();
  node('model').value='a24nsxx'; node('model').oninput();
  node('name').value='SM-A245F'; node('name').oninput();
  assert(node('fingerprintGuide').textContent.includes('SWAPPED'));
  assert(node('fingerprintGuide').classList.names.has('error'));
  // Use active should retain security patch and mirror flag, not drop either.
  node('loadCurrent').onclick();
  assert.equal(node('patch').value,'2025-10-01');
  assert.equal(node('partitions').checked,true);
  assert.equal(node('model').value,'SM-A245F');
  assert.equal(node('name').value,'a24nsxx');
  // Only the active readout changes: mismatch must be visible.
  record.current_model='SM-OTHER';
  await node('refresh').onclick();
  assert(node('propertyCheck').textContent.includes('model'));
  assert(node('propertyCheck').classList.names.has('error'));
  assert(!captured.some(x=>x.includes("'set'")),'readouts must not write properties');
  console.log('PASS: screenshot A24 mapping, valid local check, swapped-fields warning, patch/mirror copy, mismatch warning, no unintended property writes');
})().catch(e=>{console.error(e);process.exitCode=1});
