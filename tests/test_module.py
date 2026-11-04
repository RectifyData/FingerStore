#!/usr/bin/env python3
"""Host-side simulation of KernelSU getprop/resetprop, not a device test."""
import os, tempfile, subprocess, pathlib, shutil, textwrap
from datetime import datetime, timezone

SOURCE = pathlib.Path(__file__).resolve().parents[1]
FP1 = 'samsung/beyond1ltexx/beyond1:12/SP1A.210812.016/G973FXXUGHWE5:user/release-keys'
FP2 = 'google/redfin/redfin:13/TQ3A.230805.001/10256344:user/release-keys'
ORIGINAL_FP = 'samsung/beyond1ltexx/beyond1:11/RP1A.200720.012/G973FXXU9FUBD:user/release-keys'

with tempfile.TemporaryDirectory() as tmp:
    root=pathlib.Path(tmp); m=root/'build_fingerprint_date';shutil.copytree(SOURCE,m,ignore=shutil.ignore_patterns('tests'))
    cmd=m/'bin'/'fpctl.sh'
    bindir=root/'mockbin';bindir.mkdir()
    state=root/'props'
    props={
        'ro.build.fingerprint':ORIGINAL_FP,
        'ro.build.date':'Wed Sep 01 00:00:00 UTC 2021',
        'ro.build.date.utc':'1630454400',
        'ro.build.version.security_patch':'2021-09-01',
        'ro.system.build.fingerprint':ORIGINAL_FP,
        'ro.system.build.date':'Wed Sep 01 00:00:00 UTC 2021',
        'ro.system.build.date.utc':'1630454400',
        'ro.vendor.build.fingerprint':'vendor/original/vendor:11/RP1A.200720.012/old:user/release-keys',
        'ro.vendor.build.date.utc':'1630454400',
        'ro.vendor.build.date':'Wed Sep 01 00:00:00 UTC 2021',
    }
    def save(d):state.write_text(''.join(k+'='+v+'\n' for k,v in d.items()))
    def load(): return dict(line.split('=',1) for line in state.read_text().splitlines() if '=' in line)
    save(props)
    (bindir/'getprop').write_text("""#!/bin/sh
awk -v k="$1" 'index($0,k"=")==1 {print substr($0,length(k)+2);exit}' "$FAKE_PROP_FILE"
""")
    (bindir/'resetprop').write_text("""#!/bin/sh
[ "$1" = '-n' ] || exit 2
key=$2
val=$3
awk -v k="$key" -v v="$val" 'BEGIN{found=0} index($0,k"=")==1 {print k"="v;found=1;next} {print} END{if(!found)print k"="v}' "$FAKE_PROP_FILE" > "$FAKE_PROP_FILE.tmp" || exit 3
mv "$FAKE_PROP_FILE.tmp" "$FAKE_PROP_FILE"
""")
    for f in bindir.iterdir():f.chmod(0o755)
    env=dict(os.environ,PATH=f'{bindir}:'+os.environ.get('PATH',''),FAKE_PROP_FILE=str(state))
    def run(*args, ok=True):
        p=subprocess.run(['sh',str(cmd),*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
        if ok: assert p.returncode==0,(args,p.returncode,p.stdout,p.stderr)
        return p
    assert run('status').stdout.startswith('enabled=0\n')
    assert run('set',FP1,'1754006400','-','0').returncode==0
    d=load()
    assert d['ro.build.fingerprint']==FP1
    assert d['ro.build.date.utc']=='1754006400'
    assert 'UTC' in d['ro.build.date']
    assert d['ro.build.version.security_patch']=='2021-09-01'
    assert 'ro.build.fingerprint='+FP1 in (m/'system.prop').read_text()
    assert 'ro.system.build.fingerprint' not in (m/'system.prop').read_text()
    assert d['ro.system.build.fingerprint']==ORIGINAL_FP
    assert run('apply').returncode==0
    assert run('set',FP2,'1704067200','2024-01-01','1').returncode==0
    d=load()
    for part in ('system','vendor'):
        assert d[f'ro.{part}.build.fingerprint']==FP2,part
        assert d[f'ro.{part}.build.date.utc']=='1704067200'
    assert d['ro.build.version.security_patch']=='2024-01-01'
    assert 'ro.system.build.fingerprint='+FP2 in (m/'system.prop').read_text()
    assert 'ro.product.build.fingerprint' not in d, 'Absent partition properties must not be created'
    assert run('set',FP2,'1704067200','-','0').returncode==0
    d=load()
    assert d['ro.system.build.fingerprint']==ORIGINAL_FP
    assert d['ro.vendor.build.fingerprint']==props['ro.vendor.build.fingerprint']
    assert d['ro.build.version.security_patch']=='2021-09-01'
    injection=[
        ['set',FP1+';rm -rf /','1704067200','-','0'],
        ['set',FP1,'1704067200','2024-99-99','1'],
        ['set',FP1,'0','-','0'],
        ['set',FP1,'1704067200','-','2'],
        ['set','bad-fingerprint','1704067200','-','0'],
    ]
    for args in injection:
        p=run(*args,ok=False)
        assert p.returncode==2,(args,p.stderr)
    assert run('disable').returncode==0
    d=load()
    assert d==props,(d,props)
    assert not (m/'system.prop').read_text().strip()
    assert 'enabled=0' in run('status').stdout
    # Reboot simulation: emulate restored ROM values before post-fs-data.
    save(props)
    assert run('apply').returncode==0
    assert load()==props
    assert run('set',FP1,'1704067200','-','0').returncode==0
    selected = (m/'config.conf').read_text()
    earlyprops = (m/'system.prop').read_text()
    # Repeated boots retain exactly the last manually saved selection.
    for boot in range(1, 6):
        save(props)
        assert run('apply').returncode==0
        assert load()['ro.build.fingerprint']==FP1
        assert load()['ro.build.date.utc']=='1704067200'
        assert (m/'config.conf').read_text()==selected
        assert (m/'system.prop').read_text()==earlyprops
    assert 'persistence=until_changed' in run('status').stdout
    # Simulate an OEM rewriting the properties after late_start service:
    # KernelSU's boot-completed.sh must reassert the saved values.
    save(props)
    p=subprocess.run(['sh',str(m/'boot-completed.sh')],env=env,text=True,capture_output=True,timeout=15)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert load()['ro.build.fingerprint']==FP1
    # Simulate upgrade/install migration: current settings and original props
    # are preserved while system.prop is regenerated, replacing a stale file.
    upgrade=root/'upgrade'; shutil.copytree(SOURCE,upgrade,ignore=shutil.ignore_patterns('tests'))
    for name in ('config.conf','original.props'):
        shutil.copy2(m/name, upgrade/name)
    (upgrade/'system.prop').write_text('ro.build.fingerprint=obsolete-value\n')
    p=subprocess.run(['sh',str(upgrade/'bin'/'fpctl.sh'),'generate'],env=env,text=True,capture_output=True,timeout=15)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert (upgrade/'config.conf').read_text()==selected
    assert (upgrade/'system.prop').read_text()==earlyprops
    assert 'obsolete-value' not in (upgrade/'system.prop').read_text()
    # An explicit user change is retained on each subsequent reboot.
    assert run('set',FP2,'1754006400','2025-08-01','0').returncode==0
    for boot in range(3):
        save(props)
        assert run('apply').returncode==0
        assert load()['ro.build.fingerprint']==FP2
        assert load()['ro.build.date.utc']=='1754006400'
    assert run('disable').returncode==0
    assert 'persistence=disabled' in run('status').stdout
    assert load()==props
    print('PASS: apply, 5 boots, boot-completed, retained upgrade settings, change, disable/rollback, validation')
