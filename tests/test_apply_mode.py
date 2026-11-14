#!/usr/bin/env python3
"""Host simulation: staged reboot vs immediate runtime application, rollback and invalid input."""
import os, pathlib, shutil, subprocess, tempfile
src=pathlib.Path(__file__).resolve().parents[1]
fp1='google/redfin/redfin:13/TQ3A.230805.001/10256344:user/release-keys'
fp2='samsung/beyond2ltexx/beyond2:12/SP1A.210812.016/G975FXXS:user/release-keys'
original={
 'ro.build.fingerprint':'google/original/original:12/SP1A.210812.016/ORIGINAL:user/release-keys',
 'ro.build.date.utc':'1704067200',
 'ro.build.date':'Mon Jan 01 00:00:00 UTC 2024',
 'ro.build.version.security_patch':'2024-01-01',
 'ro.product.brand':'google','ro.product.device':'original','ro.product.name':'original',
 'ro.product.model':'Original Device','ro.product.manufacturer':'google'
}
with tempfile.TemporaryDirectory() as td:
 root=pathlib.Path(td);mod=root/'module'
 shutil.copytree(src,mod,ignore=shutil.ignore_patterns('tests','dist'))
 props=root/'props';bin=root/'bin';bin.mkdir()
 def save(d):props.write_text(''.join(k+'='+v+'\n' for k,v in d.items()))
 def load():return dict(line.split('=',1) for line in props.read_text().splitlines() if '=' in line)
 save(original)
 (bin/'getprop').write_text("""#!/bin/sh
awk -v k="$1" 'index($0,k"=")==1{print substr($0,length(k)+2);exit}' "$FP_TEST_PROPS"
""")
 (bin/'resetprop').write_text("""#!/bin/sh
[ "$1" = '-n' ] || exit 2
awk -v k="$2" -v v="$3" 'BEGIN{ok=0} index($0,k"=")==1{print k"="v;ok=1;next}{print} END{if(!ok) print k"="v}' "$FP_TEST_PROPS" > "$FP_TEST_PROPS.tmp" || exit 3
mv "$FP_TEST_PROPS.tmp" "$FP_TEST_PROPS"
""")
 for file in bin.iterdir():file.chmod(0o755)
 env={**os.environ,'FP_TEST_PROPS':str(props),'PATH':str(bin)+':'+os.environ['PATH']}
 def run(*args,rc=0):
  p=subprocess.run(['sh',str(mod/'bin/fpctl.sh'),*args],env=env,capture_output=True,text=True,timeout=20)
  assert p.returncode==rc,(args,p.returncode,p.stdout,p.stderr)
  return p.stdout
 before=load()
 args=['set',fp1,'1704067200','-','0','0','google','redfin','Pixel 5','redfin','Google']
 result=run(*args,'reboot')
 assert 'next reboot' in result.lower()
 assert load()==before,'reboot-staged selection MUST NOT touch live properties'
 assert 'apply_mode=reboot' in run('status')
 assert 'fingerprint='+fp1 in (mod/'config.conf').read_text()
 assert 'ro.build.fingerprint='+fp1 in (mod/'system.prop').read_text()
 assert 'ro.build.fingerprint='+before['ro.build.fingerprint'] in (mod/'original.props').read_text()
 oldcfg=(mod/'config.conf').read_bytes()
 run(*args,'invalid',rc=2)
 assert (mod/'config.conf').read_bytes()==oldcfg and load()==before
 # Simulate KernelSU system.prop being imported during startup, then late reassert.
 after=before.copy()
 for line in (mod/'system.prop').read_text().splitlines():
  if '=' in line:
   k,v=line.split('=',1);after[k]=v
 save(after)
 run('apply')
 assert load()['ro.build.fingerprint']==fp1
 run('disable')
 assert load()==before,'restore after reboot should use the pre-stage original snapshot'
 # Direct runtime writes remain available for backward compatibility.
 run('set',fp2,'1754006400','-','0','0','samsung','beyond2','Galaxy S10+','beyond2ltexx','samsung','runtime')
 assert load()['ro.build.fingerprint']==fp2
 assert 'apply_mode=runtime' in run('status')
 assert 'ro.build.fingerprint='+fp2 in (mod/'system.prop').read_text()
 run('disable')
 assert load()==before
 # Legacy set syntax still applies immediately.
 run('set',fp1,'1704067200','-','0')
 assert load()['ro.build.fingerprint']==fp1
 assert 'apply_mode=runtime' in run('status')
 print('PASS: reboot staging without live edits, pre-stage originals, boot apply, rollback, runtime and legacy modes')
