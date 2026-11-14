'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/../webroot/catalog.js','utf8');
const page=fs.readFileSync(__dirname+'/../webroot/index.html','utf8');
const ctx={window:{}};
vm.runInNewContext(source,ctx,{timeout:2000});
const list=ctx.window.FINGERSTORE_CATALOG;
const make=ctx.window.FINGERSTORE_DEMO_FP;
assert.equal(list.length,100,'exactly 100 device entries');
assert.equal(new Set(Array.from(list,d=>d.id)).size,100,'catalog identifiers unique');
assert.equal(new Set(Array.from(list,d=>d.fingerprint)).size,100,'exactly 100 unique baseline fingerprint examples');
assert(list.some(d=>d.model==='Pixel 5'));
assert(list.some(d=>d.model==='Pixel 4 XL'));
assert(!list.some(d=>d.model==='Pixel 5 XL'),'nonexistent device must not appear');
const format=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+:(user|userdebug|eng)\/[A-Za-z0-9_.-]+$/;
for(const d of list){
 assert(Object.isFrozen(d));
 assert.equal(d.fingerprint,make(d,14));
 assert(d.device.startsWith('demo_')&&d.product.startsWith('demo_'));
 for(let v=8;v<=16;v++){
  const fp=make(d,v);
  assert(format.test(fp),fp);
  assert(fp.includes(':'+v+'/'),fp);
  assert(fp.includes('/DEMO'),fp);
  assert.notEqual(fp,make(d,v===16?15:v+1));
 }
}
assert(Object.isFrozen(list));
assert(page.includes('Google+Sans+Flex'));
assert(page.includes('@material/web/'));
assert(page.includes('<md-outlined-select'));
assert(page.includes('<md-filled-button'));
assert(!page.includes('id="ssaidTitle"')&&!page.includes('id="keyboxTitle"'));
assert(!page.includes('ssaidctl.sh')&&!page.includes('keyboxctl.sh'));
console.log('PASS: exactly 100 synthetic device fingerprints; Android 8-16 variants; Material Web 3; no SSAID/keybox UI');
