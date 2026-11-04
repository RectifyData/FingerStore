'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const page=fs.readFileSync(__dirname+'/../webroot/index.html','utf8');
for(const id of ['integrityTitle','integrityCapture','integrityCompare','integrityRefresh','integrityStatus']) assert(page.includes('id="'+id+'"'),id);
const code=page.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(code); // parser validation independent of manager bridge
const nodes={};
const $=(id)=>nodes[id]||=( {textContent:'',value:'',disabled:false,checked:false,style:{},classList:{toggle(){},add(){},remove(){}},addEventListener(event,cb){this['on'+event]=cb}});
let baseline=false;let invocations=[];
const w={document:{getElementById:$},Date,Promise,Error,console,confirm:()=>true};
w.window=w;
w.ksu={moduleInfo:()=>JSON.stringify({moduleDir:'/data/adb/modules/build_fingerprint_date'}),exec(cmd,callback){
  invocations.push(cmd);
  let out='';
  if(cmd.includes('integrityctl.sh')){
    if(cmd.includes("'capture'")){baseline=true;out='baseline_saved=yes';}
    else if(cmd.includes("'compare'")){out=baseline?'changed_field_count=0':'baseline_missing=yes';}
    else out='baseline_present='+(baseline?'yes':'no');
  } else if(cmd.includes('fpctl.sh')) out='enabled=0\nresetprop=available\n';
  else if(cmd.includes('ssaidctl.sh'))out='ssaid_pending=0';
  else if(cmd.includes('keyboxctl.sh'))out='software_provider=unavailable';
  Promise.resolve().then(()=>w[callback](0,out,''));
}};
vm.runInNewContext(code,w,{timeout:2000});
(async()=>{
 await new Promise(r=>setImmediate(r));
 assert($('integrityStatus').textContent.includes('baseline_present=no'));
 await $('integrityCapture').onclick();
 assert($('integrityStatus').textContent.includes('baseline_saved=yes'));
 await $('integrityCompare').onclick();
 assert($('integrityStatus').textContent.includes('changed_field_count=0'));
 assert(invocations.some(x=>x.includes('integrityctl.sh')));
 assert(!invocations.some(x=>x.includes('PRIVATE KEY')));
 console.log('PASS integrity WebUI: report, capture, compare; no private key passing');
})().catch(e=>{console.error(e);process.exitCode=1});
