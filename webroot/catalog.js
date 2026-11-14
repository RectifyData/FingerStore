/* FingerStore demo catalog: 100 device entries, one fingerprint example each.
 * All identifiers and fingerprints are synthetic, not OEM build data.
 * Android-version examples are illustrative, not claims of update eligibility. */
(function(root) {
  'use strict';
  const grouped={"google":["Pixel","Pixel XL","Pixel 2","Pixel 2 XL","Pixel 3","Pixel 3 XL","Pixel 3a","Pixel 3a XL","Pixel 4","Pixel 4 XL","Pixel 4a","Pixel 4a (5G)","Pixel 5","Pixel 5a (5G)","Pixel 6","Pixel 6 Pro","Pixel 6a","Pixel 7","Pixel 7 Pro","Pixel 7a","Pixel Fold","Pixel 8","Pixel 8 Pro","Pixel 8a","Pixel 9","Pixel 9 Pro","Pixel 9 Pro XL","Pixel 9 Pro Fold","Pixel 9a","Pixel 10"],"samsung":["Galaxy S8","Galaxy S8+","Galaxy Note8","Galaxy S9","Galaxy S9+","Galaxy Note9","Galaxy S10e","Galaxy S10","Galaxy S10+","Galaxy Note10","Galaxy Note10+","Galaxy S20","Galaxy S20+","Galaxy S20 Ultra","Galaxy Note20","Galaxy Note20 Ultra","Galaxy S21","Galaxy S21+","Galaxy S21 Ultra","Galaxy S21 FE","Galaxy S22","Galaxy S22+","Galaxy S22 Ultra","Galaxy S23","Galaxy S23+","Galaxy S23 Ultra","Galaxy S23 FE","Galaxy S24","Galaxy S24+","Galaxy S24 Ultra","Galaxy S24 FE","Galaxy S25","Galaxy S25+","Galaxy S25 Ultra","Galaxy A20s"],"oneplus":["OnePlus 6","OnePlus 6T","OnePlus 7","OnePlus 7 Pro","OnePlus 7T","OnePlus 8","OnePlus 8 Pro","OnePlus 8T","OnePlus 9","OnePlus 9 Pro","OnePlus 10 Pro","OnePlus 10T","OnePlus 11","OnePlus 12","OnePlus Open"],"xiaomi":["Xiaomi Mi 9","Xiaomi Mi 9T","Xiaomi Mi 10","Xiaomi Mi 10 Pro","Xiaomi Mi 11","Xiaomi Mi 11 Ultra","Xiaomi 11T Pro","Xiaomi 12","Xiaomi 12 Pro","Xiaomi 12T","Xiaomi 12T Pro","Xiaomi 13","Xiaomi 13 Pro","Xiaomi 13 Ultra","Xiaomi 14"],"motorola":["Motorola edge 20","Motorola edge 30","Motorola edge 40","Motorola edge 50 Pro","Motorola moto g84"]};
  const ids={8:'OPR6.170623.011',9:'PPR1.180610.011',10:'QP1A.190711.020',
    11:'RP1A.200720.012',12:'SP1A.210812.016',13:'TP1A.220624.014',
    14:'UP1A.231005.007',15:'AP3A.240905.015',16:'BP2A.250605.031'};
  const devices=[];
  for(const [brand,names] of Object.entries(grouped)){
    for(const model of names){
      const slug=model.toLowerCase().replace(/\+/g,'_plus').replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'');
      devices.push({id:brand+':'+slug,brand,model,device:'demo_'+slug,product:'demo_'+slug});
    }
  }
  function fingerprint(record,android){
    const version=Number(android);
    if(!record||!Object.prototype.hasOwnProperty.call(ids,version))return '';
    const index=devices.indexOf(record);
    if(index<0)return '';
    return record.brand+'/'+record.product+'/'+record.device+':'+version+'/'+ids[version]+
      '/DEMO'+String(index+1).padStart(3,'0')+'V'+version+':user/dev-keys';
  }
  devices.forEach(x=>{x.fingerprint=fingerprint(x,14);});
  root.FINGERSTORE_CATALOG=Object.freeze(devices.map(x=>Object.freeze(x)));
  root.FINGERSTORE_DEMO_FP=fingerprint;
})(window);
