#!/usr/bin/env python3
"""Secure keybox vault and opt-in provider deploy with rollback. No keys leaked."""
from pathlib import Path
import os, tempfile, shutil, subprocess
SRC=Path(__file__).resolve().parents[1]
XML=b'''<?xml version="1.0" encoding="utf-8"?>\n<AndroidAttestation><NumberOfKeyboxes>1</NumberOfKeyboxes><Keybox DeviceID="testing"><Key algorithm="ecdsa"><PrivateKey format="pem">-----BEGIN PRIVATE KEY-----\nTEST-ONLY-SECRET\n-----END PRIVATE KEY-----</PrivateKey><CertificateChain><NumberOfCertificates>1</NumberOfCertificates><Certificate format="pem">-----BEGIN CERTIFICATE-----\nTEST-ONLY-CERTIFICATE\n-----END CERTIFICATE-----</Certificate></CertificateChain></Key></Keybox></AndroidAttestation>\n'''
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);mod=root/'mod';shutil.copytree(SRC,mod,ignore=shutil.ignore_patterns('tests'))
 active=root/'provider';active.mkdir();(active/'keybox.xml').write_bytes(XML.replace(b'TEST-ONLY-SECRET',b'ORIGINAL-KEY'))
 provider_mod=root/'enabled_provider';provider_mod.mkdir()
 vault=mod/'keybox-vault'
 env={**os.environ,'KEYBOX_TEST_VAULT':str(vault),'KEYBOX_TEST_PROVIDER':str(active),'KEYBOX_TEST_PROVIDER_MODULE':str(provider_mod)}
 def run(*args,code=0):
  p=subprocess.run(['sh',str(mod/'bin/keyboxctl.sh'),*args],env=env,capture_output=True,text=True,timeout=15)
  assert p.returncode==code,(args,p.returncode,p.stdout,p.stderr)
  assert b'TEST-ONLY-SECRET' not in p.stdout.encode() and b'ORIGINAL-KEY' not in p.stdout.encode()
  return p.stdout
 source=root/'incoming.xml'; source.write_bytes(XML)
 assert 'software_provider=omk_ready' in run('status')
 run('import','test_keybox',str(source))
 assert (vault/'profiles'/'test_keybox.xml').read_bytes()==XML
 assert (vault/'profiles'/'test_keybox.xml').stat().st_mode & 0o077 == 0
 assert 'test_keybox' in run('list')
 run('select','test_keybox')
 assert b'ORIGINAL-KEY' in (active/'keybox.xml').read_bytes(), 'select must NOT mutate provider'
 run('deploy-omk')
 assert (active/'keybox.xml').read_bytes()==XML
 assert b'ORIGINAL-KEY' in (vault/'provider-original.xml').read_bytes()
 assert 'provider_original_backup=yes' in run('status')
 source2=root/'incoming2.xml';source2.write_bytes(XML.replace(b'TEST-ONLY-SECRET',b'SECOND-SECRET'))
 run('import','second',str(source2));run('select','second');run('deploy-omk')
 assert b'SECOND-SECRET' in (active/'keybox.xml').read_bytes()
 assert b'ORIGINAL-KEY' in (vault/'provider-original.xml').read_bytes(), 'baseline must never be overwritten'
 run('restore-omk')
 assert b'ORIGINAL-KEY' in (active/'keybox.xml').read_bytes()
 # Fail safely if no provider.
 (provider_mod/'disable').touch()
 run('deploy-omk',code=2)
 assert b'ORIGINAL-KEY' in (active/'keybox.xml').read_bytes()
 (provider_mod/'disable').unlink()
 run('remove','test_keybox')
 run('remove','second',code=2) # selected profile cannot be deleted
 bad=root/'bad.xml';bad.write_text('<!DOCTYPE x><AndroidAttestation>')
 run('import','invalid',str(bad),code=2)
 assert not (vault/'profiles'/'invalid.xml').exists()
 assert 'test_keybox' not in run('list')
print('PASS keybox: secure import, local profiles, opt-in provider deployment, persistent original backup, restore, fail-closed, no secret logging')
