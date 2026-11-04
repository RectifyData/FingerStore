'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/../webroot/index.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const required=['fingerprint','autofill','brand','device','model','name','manufacturer','reboot','apply'];
for(const id of required) assert(html.includes(`id="${id}"`),'Missing '+id);
const nodes={};
function node(id){return nodes[id] ||= {value:'',checked:false,textContent:'',disabled:false,readOnly:false,style:{},classList:{toggle(){},add(){},remove(){}},addEventListener(event,cb){this['on'+event]=cb}}}
const samsung='samsung/r13sxxx/r13s:16/BP2A.250605.031.A3/S731BXXS6AZCH:user/release-keys';
let captures=[],rebootCalls=0,allowed=false;
const initial={enabled:'0',fingerprint:'',epoch:'',patch:'-',partitions:'0',autofill:'0',brand:'',device:'',model:'',name:'',manufacturer:'',current_fingerprint:samsung,current_epoch:'1754006400',current_patch:'2025-08-01',current_brand:'samsung',current_device:'r13s',current_model:'SM-S731B',current_name:'r13sxxx',current_manufacturer:'samsung',resetprop:'available'};
const fake={document:{getElementById:node},Date,Promise,Error,console,confirm(){return allowed}};
fake.window=fake;
fake.ksu={moduleInfo:()=>JSON.stringify({moduleDir:'/data/adb/modules/build_fingerprint_date'}),exec(command,callback){
 captures.push(command);
 let response='',errno=0;
 if(command.includes("'status'")) response=Object.entries(initial).map(([k,v])=>`${k}=${v}`).join('\n');
 else if(command.includes("'set'")){
  initial.enabled='1';initial.autofill=node('autofill').checked?'1':'0';
  for(const field of ['brand','device','model','name','manufacturer'])initial['current_'+field]=node(field).value;
  response='Saved';
 }else if(command.includes("'reboot'")){rebootCalls++;response='Reboot request issued';}
 else if(command.includes("'disable'")){initial.enabled='0';response='Restored';}
 else errno=1;
 Promise.resolve().then(()=>fake[callback](errno,response,errno?'unknown command':''));
}};
vm.runInNewContext(script,fake,{timeout:3000});
const wait=()=>new Promise(r=>setImmediate(r));
(async()=>{
 await wait();
 assert.equal(node('autofill').checked,false,'toggle must default off');
 assert.equal(node('currentModel').textContent,'SM-S731B','active model should show');
 node('fingerprint').value=samsung; node('fingerprint').oninput();
 assert.equal(node('model').readOnly,false);
 node('autofill').checked=true;node('autofill').onchange();
 for(const [k,v] of Object.entries({brand:'samsung',device:'r13s',model:'SM-S731B',name:'r13sxxx',manufacturer:'samsung'})) assert.equal(node(k).value,v,k);
 assert.equal(node('model').readOnly,true);
 // Disabling autofill must release the locked model field, leaving manual edits free.
 node('autofill').checked=false;node('autofill').onchange();
 assert.equal(node('model').readOnly,false,'toggle off should make model editable');
 node('model').value='Custom SM';
 node('apply').onclick(); await wait(); await wait();
 assert(captures.some(x=>x.includes("'set'") && x.includes("'Custom SM'")),'apply must persist model');
 assert.equal(initial.enabled,'1');
 allowed=false;node('reboot').onclick(); await wait();
 assert.equal(rebootCalls,0,'never reboot without confirmation');
 allowed=true;node('reboot').onclick();await wait();await wait();
 assert.equal(rebootCalls,1);
 // Unknown model must remain writable and must not be fabricated by auto-fill.
 node('fingerprint').value='google/redfin/redfin:13/TQ3A.230805.001/10256344:user/release-keys';
 node('autofill').checked=true;node('autofill').onchange();
 assert.equal(node('brand').value,'google');assert.equal(node('device').value,'redfin');
 assert.equal(node('model').readOnly,false);
 assert.equal(node('model').value,'','Changing to an unknown device while autofill is on must not silently retain a mismatched model');
 console.log('PASS: WebUI current identity fields, opt-in autofill, Samsung model, manual editing, saved apply, confirmed reboot and unrecognized-model warning');
})().catch(e=>{console.error(e);process.exitCode=1});
