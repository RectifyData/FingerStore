#!/usr/bin/env python3
"""Reproducible, dependency-free KernelSU release builder for FingerStore."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
RUNTIME = (
    'module.prop', 'customize.sh', 'post-fs-data.sh', 'service.sh',
    'boot-completed.sh', 'action.sh', 'skip_mount',
    'bin/fpctl.sh', 'bin/integrityctl.sh', 'bin/keyboxctl.sh',
    'bin/ssaidctl.sh', 'webroot/index.html', 'README.md',
)
SOURCE_PREFIXES = ('bin/', 'webroot/', 'tests/', 'scripts/', '.github/workflows/', 'docs/')
SOURCE_FILES = {
    'module.prop', 'customize.sh', 'post-fs-data.sh', 'service.sh',
    'boot-completed.sh', 'action.sh', 'skip_mount', 'README.md',
    'CHANGELOG.md', 'SECURITY.md', 'LICENSE', 'module.yaml',
    'update.json', '.gitignore',
}
FORBIDDEN = ('keybox-vault/', 'ssaid-data/', 'integrity-data/', '.git/', 'dist/')
FORBIDDEN_NAMES = {'config.conf', 'original.props', 'system.prop', 'keybox.xml',
                   '.env', 'private.pem', 'provider-original.xml'}
DENY_EXTENSIONS = ('.p12', '.pfx', '.jks', '.keystore', '.key', '.pem', '.pk8')
ARCHIVE_TIME = (2026, 1, 1, 0, 0, 0)


def properties(path: Path) -> dict[str, str]:
    raw = path.read_bytes()
    if b'\r' in raw or b'\0' in raw:
        raise ValueError('module.prop must use LF line endings')
    result: dict[str, str] = {}
    for line in raw.decode('utf-8').splitlines():
        if not line or line.lstrip().startswith('#'):
            continue
        if '=' not in line:
            raise ValueError(f'Invalid module.prop line: {line}')
        key, value = line.split('=', 1)
        if key in result:
            raise ValueError(f'Duplicate module property: {key}')
        result[key] = value
    return result


def collect_source() -> list[str]:
    names = []
    for item in ROOT.rglob('*'):
        if not item.is_file() and not item.is_symlink():
            continue
        name = item.relative_to(ROOT).as_posix()
        if (name.endswith((".pyc", ".pyo", ".tmp", ".bak")) or
                any(part in ("__pycache__", ".pytest_cache", ".git", "dist") for part in Path(name).parts)):
            continue
        if name in SOURCE_FILES or name.startswith(SOURCE_PREFIXES):
            names.append(name)
    return sorted(names)


def safe_file(name: str) -> None:
    if name.startswith('/') or '..' in Path(name).parts or '\\' in name:
        raise ValueError(f'Unsafe archive path: {name}')
    if name in FORBIDDEN_NAMES or Path(name).name in FORBIDDEN_NAMES:
        raise ValueError(f'Secret or runtime state cannot ship: {name}')
    if name.startswith(FORBIDDEN) or name.lower().endswith(DENY_EXTENSIONS):
        raise ValueError(f'Forbidden source path: {name}')
    target = ROOT / name
    if target.is_symlink() or not target.is_file():
        raise ValueError(f'Invalid source file: {name}')


def validate() -> tuple[str, int]:
    meta = properties(ROOT / 'module.prop')
    for field in ('id', 'name', 'version', 'versionCode', 'author', 'description'):
        if not meta.get(field):
            raise ValueError(f'Missing module.prop field {field}')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9._-]{1,63}', meta['id']):
        raise ValueError('Invalid module ID')
    if meta['id'] != 'build_fingerprint_date':
        raise ValueError('Module ID changed: this would lose upgrade compatibility')
    if not re.fullmatch(r'[0-9]+', meta['versionCode']):
        raise ValueError('versionCode is not decimal')
    version_code = int(meta['versionCode'])
    if not 1 <= version_code <= 2147483647:
        raise ValueError('versionCode outside supported Android range')
    if not re.fullmatch(r'1\.4\.[0-9]+', meta['version']):
        raise ValueError('Expected a valid release version')
    if meta.get('updateJson') != 'https://raw.githubusercontent.com/RectifyData/FingerStore/main/update.json':
        raise ValueError('Unexpected KernelSU update URL')
    version = meta['version']
    update = json.loads((ROOT / 'update.json').read_text(encoding='utf-8'))
    expected_url = (f'https://github.com/RectifyData/FingerStore/releases/download/v{version}/'
                    f'build_fingerprint_date-{version_code}-{version}.zip')
    if update.get('version') != version or update.get('versionCode') != version_code:
        raise ValueError('Update manifest must match module.prop')
    if update.get('zipUrl') != expected_url:
        raise ValueError('Invalid update manifest asset URL')
    if not update.get('changelog', '').startswith('https://'):
        raise ValueError('Missing update changelog')
    manifest = (ROOT / 'module.yaml').read_text()
    if f'id: {meta["id"]}' not in manifest or 'assetPattern: "build_fingerprint_date-*.zip"' not in manifest:
        raise ValueError('Invalid module.yaml identity or asset pattern')
    if 'schemaVersion: 1' not in manifest:
        raise ValueError('Unsupported module.yaml schema')
    if not (ROOT / 'webroot/index.html').is_file():
        raise ValueError('KernelSU WebUI entrypoint missing')
    for file in RUNTIME:
        safe_file(file)
        if b'\r\n' in (ROOT / file).read_bytes() and (file.endswith('.sh') or file == 'module.prop'):
            raise ValueError(f'Invalid CRLF shell file: {file}')
    for file in collect_source():
        safe_file(file)
    return version, version_code


def build_zip(target: Path, names: list[str]) -> None:
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9,
                         strict_timestamps=True) as archive:
        for name in sorted(names):
            safe_file(name)
            data = (ROOT / name).read_bytes()
            zinfo = zipfile.ZipInfo(name, date_time=ARCHIVE_TIME)
            zinfo.create_system = 3
            mode = 0o755 if name.endswith('.sh') or name == 'scripts/build.py' else 0o644
            zinfo.external_attr = (stat.S_IFREG | mode) << 16
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(zinfo, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify_zip(path: Path, expected: set[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError(f'Unexpected archive contents in {path.name}')
        if archive.testzip() is not None:
            raise ValueError(f'Corrupt ZIP: {path}')
        if not names or 'module.prop' not in names:
            raise ValueError('ZIP missing root module.prop')
        for file in names:
            safe_file(file)
        if path.name.endswith('-module.zip') and any(x.startswith('tests/') or x.startswith('.github/') for x in names):
            raise ValueError('Installable module ships development files')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='validate source without packaging')
    args = parser.parse_args()
    version, code = validate()
    print(f'Valid FingerStore v{version} (module ID build_fingerprint_date, versionCode {code})')
    if args.check:
        return 0
    DIST.mkdir(exist_ok=True)
    runtime = list(RUNTIME)
    source = collect_source()
    if len(source) != len(set(source)):
        raise ValueError('Duplicate paths in source')
    module_zip = DIST / f'FingerStore-v{version}-module.zip'
    source_zip = DIST / f'FingerStore-v{version}-source.zip'
    build_zip(module_zip, runtime)
    build_zip(source_zip, source)
    verify_zip(module_zip, set(runtime))
    verify_zip(source_zip, set(source))
    hashes = []
    for f in (module_zip, source_zip):
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        hashes.append(f'{digest}  {f.name}')
        print(f'{f}: {f.stat().st_size} bytes, SHA256 {digest}')
    (DIST / 'SHA256SUMS').write_text('\n'.join(hashes) + '\n')
    print('Verified: module, source, checksums and secret exclusion')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
