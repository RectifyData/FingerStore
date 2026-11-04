#!/usr/bin/env python3
"""Read-only diagnostic baseline test: no Android keys or real property writes."""
import tempfile, pathlib, shutil, subprocess, os
source=pathlib.Path(__file__).resolve().parents[1]
fp='samsung/g0sxxx/g0s:16/BP2A.250605.031.A3/S906BXXSOGZH3:user/release-keys'
with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    module=root/'module';shutil.copytree(source,module,ignore=shutil.ignore_patterns('tests'))
    mock=root/'bin';mock.mkdir()
    props=root/'props.txt'
    props.write_text('\n'.join([
        'ro.build.fingerprint='+fp,
        'ro.product.brand=samsung',
        'ro.product.model=SM-S906B',
        'ro.build.version.security_patch=2026-08-05',
        'ro.vendor.build.version.security_patch=2026-06-01',
    ])+'\n')
    (module/'config.conf').write_text('enabled=1\nfingerprint='+fp+'\nbrand=samsung\nmodel=SM-S906B\n')
    (mock/'getprop').write_text('#!/bin/sh\nawk -v k="$1" \'index($0,k"=")==1{print substr($0,length(k)+2);exit}\' "$FAKE_PROPERTIES"\n')
    (mock/'getprop').chmod(0o755)
    env=dict(os.environ,PATH=str(mock)+':'+os.environ['PATH'],FAKE_PROPERTIES=str(props))
    sh=module/'bin'/'integrityctl.sh'
    def run(*args,ok=True):
        p=subprocess.run(['sh',str(sh),*args],capture_output=True,text=True,env=env,timeout=10)
        if ok: assert p.returncode==0,(args,p.stdout,p.stderr)
        return p
    assert 'baseline_present=no' in run('report').stdout
    err=run('compare',ok=False)
    assert err.returncode!=0 and 'No baseline' in err.stderr
    assert 'baseline_saved=yes' in run('capture').stdout
    assert 'changed_field_count=0' in run('compare').stdout
    assert 'saved_fingerprint_matches_live=yes' in run('report').stdout
    baseline=module/'integrity-data'/'passing-baseline.txt'
    assert baseline.stat().st_mode & 0o777==0o600
    assert 'PRIVATE KEY' not in baseline.read_text()
    props.write_text(props.read_text().replace('ro.product.model=SM-S906B','ro.product.model=SM-A245F'))
    diff=run('compare').stdout
    assert 'changed_ro.product.model=YES' in diff,diff
    assert 'changed_field_count=2' in diff,diff  # includes saved_identity_matches_live flag
    assert 'saved_identity_matches_live=no' in run('report').stdout
    assert 'baseline_cleared=yes' in run('clear').stdout
    assert 'baseline_present=no' in run('report').stdout
print('PASS integrity diagnostics: baseline, no drift, changed model, root-only snapshot, no private keys, clear')
