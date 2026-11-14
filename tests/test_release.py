#!/usr/bin/env python3
"""Release packaging regression tests; no device interaction, keys, or network calls."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location('fingerstore_build', ROOT / 'scripts/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
version, code = builder.validate()
module = ROOT / 'dist' / f'FingerStore-v{version}-module.zip'
source = ROOT / 'dist' / f'FingerStore-v{version}-source.zip'
compiled = (ROOT / 'zygisk' / 'libs').is_dir()
additional = builder.zygisk_entries(required=compiled)
compile_option = ['--with-zygisk'] if compiled else []
if not module.is_file() or not source.is_file():
    subprocess.run([sys.executable, str(ROOT/'scripts/build.py'), *compile_option], check=True)

with zipfile.ZipFile(module) as archive:
    entries = archive.namelist()
    assert entries == sorted(entries)
    expected = set(builder.RUNTIME) | set(additional)
    assert set(entries) == expected, set(entries) ^ expected
    for abi, source in additional.items():
        assert archive.read(abi) == source.read_bytes()
    assert archive.read('module.prop').decode('utf-8') == (ROOT/'module.prop').read_text()
    assert 'id=build_fingerprint_date' in archive.read('module.prop').decode()
    assert archive.read('skip_mount') == b''
    assert archive.read('webroot/index.html').startswith(b'<!doctype html>')
    assert not any(p.startswith(('tests/', 'scripts/', 'docs/', '.github/')) for p in entries)
    assert len(entries) == len(set(entries))
    assert len(entries) < 100
    assert archive.testzip() is None
    for p in entries:
        meta = archive.getinfo(p)
        assert meta.date_time == builder.ARCHIVE_TIME
        assert (meta.external_attr >> 16) & 0o777 == (0o755 if p.endswith('.sh') else 0o644)
        assert not p.startswith('/') and '..' not in Path(p).parts

with zipfile.ZipFile(source) as archive:
    names = archive.namelist()
    assert 'scripts/build.py' in names and 'tests/test_module.py' in names
    assert 'zygisk/jni/zygisk.hpp' in names and 'zygisk/jni/fingerstore.cpp' in names
    assert not any(x.startswith('zygisk/libs/') or x.startswith('zygisk/obj/') for x in names)
    assert '.github/workflows/release.yml' in names
    assert 'docs/TECHNICAL.md' in names
    assert all('keybox-vault' not in p and not p.startswith('ssaid-data/') and 'config.conf' not in p for p in names)
    assert archive.testzip() is None

checksum_file = ROOT / 'dist/SHA256SUMS'
lines = checksum_file.read_text().splitlines()
assert len(lines) == 2
for line, expected in zip(lines, (module, source)):
    digest, filename = line.split('  ', 1)
    assert filename == expected.name
    assert digest == hashlib.sha256(expected.read_bytes()).hexdigest()

update = json.loads((ROOT/'update.json').read_text())
assert update['version'] == version and update['versionCode'] == code
assert update['zipUrl'].endswith(f'build_fingerprint_date-{code}-{version}.zip')
assert module.stat().st_size < 100 * 1024 * 1024

# Reproduce both archives in a second build and require byte-identical outputs.
old = (module.read_bytes(), source.read_bytes(), checksum_file.read_bytes())
subprocess.run([sys.executable, str(ROOT/'scripts/build.py'), *compile_option], check=True, stdout=subprocess.DEVNULL)
new = (module.read_bytes(), source.read_bytes(), checksum_file.read_bytes())
assert new == old, 'Packaging must be byte-for-byte reproducible'
print('PASS: archive contents, safe filenames, modes, checksum, metadata, deterministic build')
