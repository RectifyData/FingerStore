#!/usr/bin/env python3
"""Deep regression checks with injected failures and timezone changes."""
from pathlib import Path
from datetime import datetime, timezone
import os, shutil, subprocess, tempfile, textwrap, re, zipfile

SRC=Path(__file__).resolve().parents[1]
FP_A='samsung/beyond1ltexx/beyond1:12/SP1A.210812.016/G973FXXUGHWE5:user/release-keys'
FP_B='google/redfin/redfin:13/TQ3A.230805.001/10256344:user/release-keys'
START={
 'ro.build.fingerprint':'samsung/orig/orig:11/RP1A.200720.012/original:user/release-keys',
 'ro.build.date':'Wed Sep 01 00:00:00 UTC 2021',
 'ro.build.date.utc':'1630454400',
 'ro.build.version.security_patch':'2021-09-01',
 'ro.system.build.fingerprint':'samsung/orig/orig:11/RP1A.200720.012/original:user/release-keys',
 'ro.system.build.date':'Wed Sep 01 00:00:00 UTC 2021',
 'ro.system.build.date.utc':'1630454400',
}

def make_environment(tmp):
 root=Path(tmp)
 m=root/'module';shutil.copytree(SRC,m,ignore=shutil.ignore_patterns('tests'))
 bindir=root/'bin';bindir.mkdir();props=root/'props';fault=root/'fail-once'
 props.write_text(''.join(f'{k}={v}\n' for k,v in START.items()))
 (bindir/'getprop').write_text('''#!/bin/sh
awk -v k="$1" 'index($0,k"=")==1 { print substr($0,length(k)+2);exit }' "$FAKE_PROP_FILE"
''')
 (bindir/'resetprop').write_text('''#!/bin/sh
[ "$1" = '-n' ] || exit 2
key=$2; val=$3
if [ -f "$FAIL_ONCE" ] && [ "$key" = ro.build.date.utc ]; then
  rm "$FAIL_ONCE"
  echo 'injected failure' >&2
  exit 12
fi
awk -v k="$key" -v v="$val" 'BEGIN {found=0} index($0,k"=")==1 {print k"="v;found=1;next} {print} END{if(!found)print k"="v}' "$FAKE_PROP_FILE" > "$FAKE_PROP_FILE.tmp" || exit 3
mv "$FAKE_PROP_FILE.tmp" "$FAKE_PROP_FILE"
''')
 for f in bindir.iterdir(): f.chmod(0o755)
 env=dict(os.environ,PATH=f'{bindir}:'+os.environ['PATH'],FAKE_PROP_FILE=str(props),FAIL_ONCE=str(fault))
 return m,props,fault,env

def run(m,env,*args,sh='sh'):
 command = [sh, str(m/'bin/fpctl.sh'),*args] if sh!='busybox ash' else ['busybox','ash',str(m/'bin/fpctl.sh'),*args]
 return subprocess.run(command,env=env,capture_output=True,text=True,timeout=25)

def propdict(props):return dict(x.split('=',1) for x in props.read_text().splitlines() if '=' in x)

for shell in ('sh','bash','busybox ash'):
 with tempfile.TemporaryDirectory() as tmp:
  m,props,fault,env=make_environment(tmp)
  dayseconds=['946684800','999999999','1000000000','1704067200','2147483647','2147483648','3999999999','4102444800']
  for sec in dayseconds:
   r=run(m,env,'set',FP_A,sec,'-','0',sh=shell)
   assert r.returncode==0,(shell,sec,r.stderr)
   assert propdict(props)['ro.build.date.utc']==sec,(shell,sec)
  for sec in ['0','946684799','4102444801','9999999999','1704067200000','-1704067200','0123456789','']:
   oldcfg=(m/'config.conf').read_text()
   r=run(m,env,'set',FP_A,sec,'-','0',sh=shell)
   assert r.returncode==2,(shell,sec,r.stderr)
   assert (m/'config.conf').read_text()==oldcfg
  # Real Huawei/Honor stock incrementals can include parentheses.
  stock_huawei='HONOR/BLN-AL10/HWBLN-H:8.0.0/HONORBLN-AL10/528(C00):user/release-keys'
  r=run(m,env,'set',stock_huawei,'1704067200','-','0',sh=shell)
  assert r.returncode==0,(shell,'parentheses in stock build incremental',r.stderr)
  # Catalog source lacks a build timestamp. Using '-' means apply the
  # genuine fingerprint while leaving the real device build date alone.
  r=run(m,env,'set',FP_B,'-','-','0',sh=shell)
  assert r.returncode==0,(shell,'fingerprint-only runtime',r.stderr)
  assert propdict(props)['ro.build.fingerprint']==FP_B
  assert propdict(props)['ro.build.date.utc']==START['ro.build.date.utc'],(shell,'date incorrectly spoofed')
  assert propdict(props)['ro.build.date']==START['ro.build.date']
  assert 'epoch=-' in (m/'config.conf').read_text()
  assert 'ro.build.date' not in (m/'system.prop').read_text(),(shell,'date emitted for missing source timestamp')
  assert run(m,env,'apply',sh=shell).returncode==0
  assert propdict(props)['ro.build.date.utc']==START['ro.build.date.utc']
  r=run(m,env,'set',FP_B,'-','-','0','0','google','redfin','Pixel 5','redfin','Google','reboot',sh=shell)
  assert r.returncode==0,(shell,'fingerprint-only reboot stage',r.stderr)
  assert 'ro.build.fingerprint='+FP_B in (m/'system.prop').read_text()
  assert 'ro.build.date' not in (m/'system.prop').read_text()
  assert run(m,env,'apply',sh=shell).returncode==0
  assert propdict(props)['ro.build.date.utc']==START['ro.build.date.utc']
  # Switching back to an explicitly documented build timestamp still works.
  r=run(m,env,'set',FP_A,'1704067200','-','0',sh=shell)
  assert r.returncode==0,(shell,'resume full timestamp mode',r.stderr)
  assert propdict(props)['ro.build.date.utc']=='1704067200'
  # Same date must validate independently of local timezone, including leap days.
  for tz in ('Pacific/Auckland','Asia/Kolkata','America/Sao_Paulo','UTC'):
   env['TZ']=tz
   r=run(m,env,'set',FP_A,'1704067200','2024-02-29','1',sh=shell)
   assert r.returncode==0,(shell,tz,r.stderr)
  for bad in ('2023-02-29','2024-02-30','2024-13-01','2024-00-01','2024-04-31'):
   r=run(m,env,'set',FP_A,'1704067200',bad,'0',sh=shell)
   assert r.returncode==2,(shell,bad,r.stderr)
  # New install and upgrade should never mutate settings following a failed apply.
  r=run(m,env,'set',FP_A,'1735689600','2025-01-01','1',sh=shell)
  assert r.returncode==0,r.stderr
  old_cfg=(m/'config.conf').read_text()
  old_sys=(m/'system.prop').read_text()
  old_props=propdict(props)
  fault.touch()
  r=run(m,env,'set',FP_B,'1754006400','-','0',sh=shell)
  assert r.returncode==4,(shell,r.stdout,r.stderr)
  assert (m/'config.conf').read_text()==old_cfg,(shell,'config lost on failure')
  assert (m/'system.prop').read_text()==old_sys,(shell,'boot prop lost on failure')
  assert propdict(props)==old_props,(shell,'live props not rolled back')
  assert list(m.glob('.fpctl-txn.*'))==[],(shell,'transaction backups not cleaned')
  # Retry after transient failure and change should work.
  r=run(m,env,'set',FP_B,'1754006400','-','0',sh=shell)
  assert r.returncode==0,(shell,r.stderr)
  assert propdict(props)['ro.build.fingerprint']==FP_B
  assert run(m,env,'disable',sh=shell).returncode==0
  assert propdict(props)==START,(shell,'restore mismatch')
 print(f'PASS {shell}: timestamp boundaries, patch dates, timezone, transactional rollback, cleanup, retry, restore')

# A broken/unwritable rollback journal must never permit a live property edit.
with tempfile.TemporaryDirectory() as tmp:
 m,props,fault,env=make_environment(tmp)
 (m/'original.props').mkdir()  # forces redirection/snapshot write failure
 before=propdict(props)
 r=run(m,env,'set',FP_A,'1704067200','-','0')
 assert r.returncode==4,(r.stdout,r.stderr)
 assert propdict(props)==before,'mutated props despite snapshot failure'
 assert not (m/'config.conf').exists(),'selection persisted after aborted apply'
 assert not (m/'system.prop').exists(),'boot prop persisted after aborted apply'
print('PASS failure injection: unreadable rollback journal blocks property changes')

# Packaging checks can also be run before the ZIP is built.
assert (SRC/'module.prop').exists()
assert 'version=1.4.6' in (SRC/'module.prop').read_text()
for f in ('service.sh','boot-completed.sh','action.sh','customize.sh','bin/fpctl.sh'):
 assert (SRC/f).read_bytes().startswith(b'#!/system/bin/sh')
print('PASS source: installer and lifecycle entry points')
