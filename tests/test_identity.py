#!/usr/bin/env python3
"""Extended identity spoofing, migration, reboot, auto-fill, and rollback tests."""
from pathlib import Path
import os, shutil, subprocess, tempfile

SRC=Path(__file__).resolve().parents[1]
SAMSUNG='samsung/r13sxxx/r13s:16/BP2A.250605.031.A3/S731BXXS6AZCH:user/release-keys'
PIXEL='google/redfin/redfin:13/TQ3A.230805.001/10256344:user/release-keys'
START={
 'ro.build.fingerprint':'samsung/orig/orig:11/RP1A.200720.012/G973FXXS6:user/release-keys',
 'ro.build.date.utc':'1630454400',
 'ro.build.date':'Wed Sep 01 00:00:00 UTC 2021',
 'ro.build.version.security_patch':'2021-09-01',
 'ro.product.brand':'samsung','ro.product.device':'beyond1','ro.product.model':'SM-G973F',
 'ro.product.name':'beyond1ltexx','ro.product.manufacturer':'samsung',
 'ro.product.system.brand':'samsung', 'ro.product.system.model':'SM-G973F',
 'ro.product.vendor.device':'beyond1', 'ro.vendor.build.fingerprint':'vendor/orig/orig:11/RP1A.200720.012/old:user/release-keys',
}
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);m=root/'module';shutil.copytree(SRC,m,ignore=shutil.ignore_patterns('tests'))
 bindir=root/'bin';bindir.mkdir();store=root/'props';reboot_request=root/'reboot-request';failure=root/'fail-once'
 def save(d):store.write_text(''.join(f'{k}={v}\n' for k,v in d.items()))
 def load():return dict(x.split('=',1) for x in store.read_text().splitlines() if '=' in x)
 save(START)
 (bindir/'getprop').write_text('''#!/bin/sh
awk -v k="$1" 'index($0,k"=")==1 {print substr($0,length(k)+2);exit}' "$FAKE_PROP_FILE"
''')
 (bindir/'resetprop').write_text('''#!/bin/sh
[ "$1" = '-n' ] || exit 2
key=$2; val=$3
if [ -f "$FAIL_ONCE" ] && [ "$key" = ro.product.model ]; then rm -f "$FAIL_ONCE"; exit 4; fi
awk -v k="$key" -v v="$val" 'BEGIN{found=0}index($0,k"=")==1{print k"="v;found=1;next}{print}END{if(!found) print k"="v}' "$FAKE_PROP_FILE" > "$FAKE_PROP_FILE.tmp" || exit 3
mv "$FAKE_PROP_FILE.tmp" "$FAKE_PROP_FILE"
''')
 (bindir/'svc').write_text('''#!/bin/sh
[ "$1" = power ] && [ "$2" = reboot ] || exit 1
printf 'reboot' > "$REBOOT_REQUEST"
''')
 for f in bindir.iterdir():f.chmod(0o755)
 env={**os.environ,'PATH':str(bindir)+':'+os.environ['PATH'],'FAKE_PROP_FILE':str(store),'REBOOT_REQUEST':str(reboot_request),'FAIL_ONCE':str(failure)}
 def run(*args,expected=0):
  p=subprocess.run(['sh',str(m/'bin/fpctl.sh'),*args],env=env,capture_output=True,text=True,timeout=30)
  assert p.returncode==expected,(args,p.returncode,p.stdout,p.stderr)
  return p.stdout
 def set_ext(fp,auto,brand='',device='',model='',name='',manufacturer='',mirror='0'):
  return run('set',fp,'1754006400','2025-08-01',mirror,auto,brand,device,model,name,manufacturer)
 # Manual fields work without autofill and can contain spaces.
 set_ext(PIXEL,'0','My Brand','bespoke','Pixel Lab 5','custom_product','Example Inc')
 p=load()
 assert p['ro.product.brand']=='My Brand' and p['ro.product.device']=='bespoke'
 assert p['ro.product.model']=='Pixel Lab 5' and p['ro.product.manufacturer']=='Example Inc'
 assert p['ro.product.name']=='custom_product'
 assert p['ro.product.system.brand']=='samsung' # mirroring off
 assert 'autofill=0' in (m/'config.conf').read_text()
 assert 'ro.product.model=Pixel Lab 5' in (m/'system.prop').read_text()
 # Enabled autofill overrides manual spoofed brand, device, product,
 # manufacturer and matches screenshot Samsung model prefix.
 set_ext(SAMSUNG,'1','WrongBrand','wrong','WrongModel','wrong','WrongMfg',mirror='1')
 p=load()
 for key,val in {'ro.product.brand':'samsung','ro.product.device':'r13s','ro.product.model':'SM-S731B','ro.product.name':'r13sxxx','ro.product.manufacturer':'samsung','ro.product.system.brand':'samsung','ro.product.system.model':'SM-S731B'}.items():
  assert p[key]==val,(key,p.get(key),val)
 assert p['ro.product.vendor.device']=='r13s'
 assert 'ro.product.product.model' not in p # do not create missing partition props
 assert 'autofill=1' in (m/'config.conf').read_text()
 assert 'model=SM-S731B' in (m/'config.conf').read_text()
 assert 'current_model=SM-S731B' in run('status')
 # Reboot reapplication and persistence without timed reset.
 chosen=(m/'config.conf').read_text()
 for _ in range(3):
  save(START)
  run('apply')
  assert load()['ro.product.model']=='SM-S731B'
  assert (m/'config.conf').read_text()==chosen
 # Migrate simulated v1.2 install with only legacy config keys.
 old=root/'upgrade';shutil.copytree(SRC,old,ignore=shutil.ignore_patterns('tests'))
 (old/'config.conf').write_text('enabled=1\nfingerprint='+PIXEL+'\nepoch=1704067200\npatch=-\npartitions=0\n')
 r=subprocess.run(['sh',str(old/'bin/fpctl.sh'),'generate'],env=env,capture_output=True,text=True,timeout=20)
 assert r.returncode==0,r.stderr
 assert 'ro.product.model=' not in (old/'system.prop').read_text()
 assert 'fingerprint='+PIXEL in (old/'config.conf').read_text()
 # Unrecognized brand/device cannot generate an invented model.
 set_ext(PIXEL,'1','Wrong','wrong','Manual Pixel Label','wrong','wrong')
 p=load()
 assert p['ro.product.brand']=='google' and p['ro.product.device']=='redfin'
 assert p['ro.product.model']=='Manual Pixel Label'
 # Empty fields when auto off restore originals, not break config.
 set_ext(PIXEL,'0')
 assert load()['ro.product.brand']==START['ro.product.brand']
 assert load()['ro.product.device']==START['ro.product.device']
 assert load()['ro.product.model']==START['ro.product.model']
 # Error injection: failed identity update must preserve previous state.
 old_properties=load();old_conf=(m/'config.conf').read_bytes();old_prop=(m/'system.prop').read_bytes()
 failure.touch()
 run('set',SAMSUNG,'1754006400','-','1','0','Google','pixel','Pixel 20','pixel20','Google',expected=4)
 assert load()==old_properties and (m/'config.conf').read_bytes()==old_conf and (m/'system.prop').read_bytes()==old_prop
 # Bad shell payloads, newline and equal-sign injections must be rejected.
 for bad in ['evil\nro.build.fingerprint=bad','abc=bad','$(reboot)','a'*91]:
  run('set',SAMSUNG,'1754006400','-','0','0','samsung','r13s',bad,'r13sxxx','samsung',expected=2)
 assert load()==old_properties
 assert not reboot_request.exists()
 run('reboot')
 assert reboot_request.read_text()=='reboot'
 # Restore all identity keys including mirrored partition originals.
 run('disable')
 assert load()==START,(load(),START)
 assert not (m/'system.prop').read_text().strip()
 print('PASS: manual identity, opt-in Samsung autofill, no invented model, partition mirror, old-config migration, reboot request, 3 boot cycles, input security, rollback and full restoration')
