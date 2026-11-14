#!/usr/bin/env python3
"""Magisk-compatible optional Zygisk settings: no writes until explicit opt-in."""
import os
import pathlib
import shutil
import subprocess
import tempfile

SRC=pathlib.Path(__file__).resolve().parents[1]
FP='google/redfin/redfin:13/TQ3A.230805.001/10256344:user/release-keys'
with tempfile.TemporaryDirectory() as tmp:
    root=pathlib.Path(tmp)
    mod=root/'module'
    shutil.copytree(SRC,mod,ignore=shutil.ignore_patterns('tests','dist','libs','obj'))
    binpath=root/'bin'
    binpath.mkdir()
    props=root/'props'
    props.write_text('ro.build.fingerprint=google/orig/orig:12/SP1A.210812.016/ORIG:user/release-keys\nro.build.date.utc=1704067200\nro.build.date=Mon Jan 01 00:00:00 UTC 2024\n')
    (binpath/'getprop').write_text("""#!/bin/sh
awk -v k="$1" 'index($0,k"=")==1 {print substr($0,length(k)+2);exit}' "$TEST_PROPS"
""")
    (binpath/'resetprop').write_text("""#!/bin/sh
[ "$1" = -n ] || exit 3
awk -v k="$2" -v v="$3" 'BEGIN {found=0} index($0,k"=")==1{print k"="v;found=1;next}{print}END{if(!found)print k"="v}' "$TEST_PROPS" > "$TEST_PROPS.tmp" && mv "$TEST_PROPS.tmp" "$TEST_PROPS"
""")
    for file in binpath.iterdir():
        file.chmod(0o755)
    env={**os.environ,'PATH':str(binpath)+':'+os.environ['PATH'],'TEST_PROPS':str(props)}
    def call(*args,returncode=0):
        p=subprocess.run(['sh',str(mod/'bin/fpctl.sh'),*args],env=env,
                         capture_output=True,text=True,timeout=20)
        assert p.returncode==returncode,(args,p.returncode,p.stderr,p.stdout)
        return p.stdout
    assert 'zygisk_enabled=0' in call('zygisk','status')
    assert 'zygisk_available=no' in call('status')
    call('zygisk','enable',returncode=3)
    assert not (mod/'zygisk.conf').exists(),'missing binaries must never opt-in'
    (mod/'zygisk').mkdir(exist_ok=True)
    (mod/'zygisk'/'arm64-v8a.so').write_bytes(b'host-fixture-not-for-release')
    call('zygisk','enable')
    assert 'enabled=1' in (mod/'zygisk.conf').read_text()
    assert (mod/'zygisk.conf').stat().st_mode & 0o777 == 0o600
    assert 'zygisk_ready=no' in call('status'),'runtime mode requires an active fingerprint'
    call('set',FP,'1704067200','-','0','0','google','redfin','Pixel 5','redfin','Google','reboot')
    assert 'zygisk_ready=no' in call('status'),'zygisk must NEVER inject in reboot staging mode'
    call('set',FP,'1704067200','-','0','0','google','redfin','Pixel 5','redfin','Google','runtime')
    assert 'zygisk_ready=yes' in call('status')
    call('zygisk','disable')
    assert 'zygisk_ready=no' in call('status')
    assert 'enabled=0' in (mod/'zygisk.conf').read_text()
    call('zygisk','invalid',returncode=2)
    assert 'enabled=0' in (mod/'zygisk.conf').read_text()
    # Magisk install requires standardized module entrypoints but not KernelSU-only hooks.
    for f in ('module.prop','customize.sh','service.sh','action.sh'):
        assert (SRC/f).is_file()
    installer=(SRC/'customize.sh').read_text()
    assert 'MAGISK_VER' in installer
    assert 'set_perm "$MODPATH/post-fs-data.sh"' not in installer
    assert 'enabled=0' in installer
    native=(SRC/'zygisk/jni/fingerstore.cpp').read_text()
    assert 'postAppSpecialize' in native
    assert 'postServerSpecialize(' not in native
    assert 'android/os/Build' in native and '"FINGERPRINT"' in native
    assert 'is_runtime(' in native and 'is_true(' in native
    assert 'DLCLOSE_MODULE_LIBRARY' in native
print('PASS: Magisk entrypoints, default disabled, explicit Zygisk toggle, runtime-only readiness, no system-server hook')
