#!/usr/bin/env python3
"""End-to-end simulated Android SSAID XML edits; no real phone required."""
from pathlib import Path
import os, shutil, subprocess, tempfile
SRC=Path(__file__).resolve().parents[1]
FP='samsung/a24nsxx/a24:16/UP1A.250605.014/A245FXXU9EYK1:user/release-keys'

with tempfile.TemporaryDirectory() as work:
    root=Path(work); mod=root/'mod'; shutil.copytree(SRC,mod,ignore=shutil.ignore_patterns('tests'))
    sysroot=root/'system'/'users'/'0'; sysroot.mkdir(parents=True)
    original=b'''<?xml version="1.0" encoding="utf-8" standalone="yes" ?>\n<settings version="123">\n<setting id="1" name="10123" value="1122334455667788" package="android" defaultValue="1122334455667788" />\n<setting id="2" name="10124" value="2233445566778899" package="android" />\n</settings>\n'''
    target=sysroot/'settings_ssaid.xml'; target.write_bytes(original)
    binds=root/'bin';binds.mkdir()
    (binds/'pm').write_text('#!/bin/sh\nprintf "package:com.example.alpha uid:10123\\npackage:com.example.beta uid:10124\\n"\n')
    (binds/'settings').write_text('#!/bin/sh\necho aaaabbbbccccdddd\n')
    for f in binds.iterdir():f.chmod(0o755)
    (mod/'config.conf').write_text('enabled=1\nfingerprint='+FP+'\nepoch=1754006400\npatch=-\n')
    env={**os.environ,'PATH':str(binds)+':'+os.environ['PATH'],'SSAID_TEST_ROOT':str(sysroot)}
    def run(*args,code=0):
        p=subprocess.run(['sh',str(mod/'bin/ssaidctl.sh'),*args],env=env,capture_output=True,text=True,timeout=15)
        assert p.returncode==code,(args,p.returncode,p.stdout,p.stderr)
        return p.stdout
    assert 'ssaid_source=present' in run('status')
    run('stage','com.example.alpha','manual','abcdef0123456789')
    assert target.read_bytes()==original,'Staging must NEVER modify running SettingsProvider data'
    assert 'abcdef0123456789' in (mod/'ssaid-data'/'pending.bin').read_text()
    assert (mod/'ssaid-data'/'original.bin').read_bytes()==original
    # Second edit in same staged file must preserve the first one.
    run('stage','com.example.beta','manual','ffeeddccbbaa1234')
    queued=(mod/'ssaid-data'/'pending.bin').read_text()
    assert 'abcdef0123456789' in queued and 'ffeeddccbbaa1234' in queued
    assert 'package=com.example.beta' in (mod/'ssaid-data'/'profile.conf').read_text()
    # Unexpected settings-provider writes cause stage failure instead of overwrite.
    target.write_bytes(original.replace(b'version="123"',b'version="124"'))
    run('stage','com.example.alpha','manual','1111222233334444',code=3)
    # Apply rejects changed source database safely in early boot.
    p=subprocess.run(['sh',str(mod/'post-fs-data.sh')],env=env,capture_output=True,text=True,timeout=15)
    assert p.returncode!=0 and b'version="124"' in target.read_bytes()
    assert 'ERROR' in (mod/'ssaid-data'/'last-result.txt').read_text()
    target.write_bytes(original)
    p=subprocess.run(['sh',str(mod/'post-fs-data.sh')],env=env,capture_output=True,text=True,timeout=15)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert 'abcdef0123456789' in target.read_text() and 'ffeeddccbbaa1234' in target.read_text()
    assert not (mod/'ssaid-data'/'pending.bin').exists()
    # First original backup is never replaced; manual restore for either app.
    assert (mod/'ssaid-data'/'original.bin').read_bytes()==original
    run('restore','com.example.alpha')
    assert '1122334455667788' in (mod/'ssaid-data'/'pending.bin').read_text()
    run('clear-pending')
    assert target.read_bytes()!=original,'Cancelling must not revert applied values'
    run('stage','com.example.alpha','sync','-')
    sync=(mod/'ssaid-data'/'pending.meta').read_text().split('\nid=')[1].split('\n')[0]
    assert len(sync)==16 and all(c in '0123456789abcdef' for c in sync)
    run('stage','com.example.alpha','sync','-')
    assert sync in (mod/'ssaid-data'/'pending.meta').read_text(),'Synchronized IDs must be stable'
    # Uninstall/restore users retain original backup and profile data.
    assert 'ssaid_profile_mode=sync' in run('status')
    for bad in ['not-an-id','ffffffffffffffffffff','ZZ00112233445566']:
        run('stage','com.example.alpha','manual',bad,code=3)
    run('stage','com.example.missing','manual','0123456789abcdef',code=3)
    assert 'source_sha=' in (mod/'ssaid-data'/'pending.meta').read_text()
print('PASS SSAID: staging, multi-app edits, no live DB writes, race detection, early-boot apply, restore, sync stability, invalid inputs')
