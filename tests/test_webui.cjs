'use strict';
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const page=fs.readFileSync(__dirname+'/../webroot/index.html','utf8');
const js=page.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements={};
const get=(id)=>elements[id] ||= {value:'',textContent:'',checked:false,disabled:false,hidden:false,style:{},classList:{toggle(){},add(){},remove(){}},setAttribute(){},focus(){},addEventListener(t,f){this['on'+t]=f}};
const fp='samsung/beyond1ltexx/beyond1:12/SP1A.210812.016/G973FXXUGHWE5:user/release-keys';
let config={enabled:'0',fingerprint:'',epoch:'',patch:'-',partitions:'0'};
const props={current_fingerprint:fp,current_epoch:'1704067200',current_human:'Mon Jan 01 00:00:00 UTC 2024',current_patch:'2024-01-01',resetprop:'available'};
const mock={document:{getElementById:get},console,Date,Promise,Error,confirm:()=>true};
mock.window=mock;
mock.ksu={moduleInfo:()=>JSON.stringify({moduleDir:'/data/adb/modules/build_fingerprint_date'}),exec(command,cbName){
 let response='',code=0;
 if(command.includes("'status'"))response=Object.entries({...config,...props}).map(([k,v])=>k+'='+v).join('\n');
 else if(command.includes("'disable'")){config.enabled='0';response='Disabled';}
 else if(command.includes("'set'")){
   config.enabled='1';config.fingerprint=fp;config.epoch='1735689600';config.patch='-';config.partitions='0';
   props.current_fingerprint=fp;props.current_epoch=config.epoch;response='Applied';
 }
 else code=1;
 Promise.resolve().then(()=>mock[cbName](code,response,code?'Unknown command':''));
}};
vm.runInNewContext(js,mock,{timeout:1000});
(async()=>{
 await new Promise(r=>setImmediate(r));
 assert.equal(get('currentFp').textContent,fp);
 assert.equal(get('panelCatalog').hidden,false);
 assert.equal(get('panelEditor').hidden,true);
 get('tabEditor').onclick();
 assert.equal(get('panelEditor').hidden,false);
 assert.equal(get('date').value,'2024-01-01');
 get('fingerprint').value=fp;
 get('date').value='2025-01-01';
 await get('apply').onclick();
 assert.equal(config.enabled,'1');
 assert.equal(get('currentDate').textContent.includes('2025-01-01'),true);
 await get('reset').onclick();
 assert.equal(config.enabled,'0');
 console.log('PASS: KernelSU bridge callbacks, page hydration, Apply / Restore controls');
})().catch(e=>{console.error(e);process.exitCode=1});
