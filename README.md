# FingerStore

**FingerStore v1.4.3** is a KernelSU module for editing Android build fingerprints, build dates and identity properties through a mobile-first Material 3 WebUI.

The module ID remains `build_fingerprint_date` to keep updates compatible with previous versions.

## Features

- Edit `ro.build.fingerprint`, `ro.build.date.utc`, the formatted build date, and the reported security patch *property*.
- Manually set brand, device codename, product code, retail model and manufacturer, or opt in to conservative fingerprint-based autofill.
- Mirror existing system, product, vendor, odm, system_ext and bootimage build properties when requested (off by default).
- Choose how to apply a saved identity:
  - **After reboot — recommended:** stage new properties for KernelSU startup. Do **not** change live properties until the next reboot.
  - **At runtime — unstable:** write live properties immediately and persist the selection for future boots. Existing apps can cache the previous values, and ROM services or competing modules can override properties.
- Browse **exactly 100 device demo entries** with an Android 8–16 version selector. Each entry has one baseline demo fingerprint and dynamically generated per-version examples.
- Use Google Sans Flex and Material Web 3 where supported; a local Material 3-styled native fallback keeps the WebUI usable when the phone is offline.
- Read-only local property stability diagnostics, restore original values and request a confirmed reboot.

### Important: device catalog is demonstration data

Every demo fingerprint uses explicit `demo_` device/product identifiers and a `DEMO...` build incremental. None of the example strings is an official or verified fingerprint from OEM firmware. Version selection **does not** establish that the device can run that Android release. For actual use, supply a verified `ro.build.fingerprint` and corresponding identity fields from the exact firmware build.

Google has never released a Pixel 5 XL. The catalog includes the actual Pixel 5 and Pixel 4 XL instead.

## Removed features

As of v1.4.3, **SSAID editing and the keybox loader are removed entirely from the installed code and WebUI.** The module no longer edits the Android SSAID database or installs external attestation-provider files.

If an older version changed app SSAIDs or an external keybox provider, **upgrading does not undo those earlier external modifications.** Restore them from a known-good backup or the previous release before upgrading if necessary. FingerStore will not silently rewrite unrelated Android settings to reverse old edits.

## Accuracy and safety

This module **does not guarantee any Play Integrity verdict or hardware-backed attestation**. Security-patch property changes do not install security fixes. Only already-existing partition properties are mirrored. The WebUI never applies a demo automatically; it requires an explicit action, and warns again before applying a synthetic example.

Keep a backup, particularly when changing identity on a primary phone. Boot-stage mode is preferable to changing identity while applications are running. Actual boot behavior varies by ROM and KernelSU environment and requires hardware testing to verify.

## Install

1. Get the **FingerStore v1.4.3 module ZIP** from [GitHub Releases](https://github.com/RectifyData/FingerStore/releases).
2. In KernelSU Manager, choose **Modules → Install from storage** and select the module ZIP, not the source ZIP. Do not flash through recovery.
3. Reboot, open the FingerStore WebUI, and choose a verified fingerprint or explore the demo catalog.
4. Choose **After reboot (recommended)** or **At runtime (unstable)**, then tap **Apply changes**. Reboots always need your confirmation.

Saved choices survive ordinary restarts and in-place upgrades until you edit or restore them. **Restore** reverts captured build properties where available and disables future overrides.

## Build and test

The build is reproducible and requires Python 3, Node.js and standard shell tools:

```sh
python3 scripts/build.py --check
for t in tests/test_*.py; do python3 "$t"; done
for t in tests/test_*.cjs; do node "$t"; done
python3 scripts/build.py
python3 tests/test_release.py
(cd dist && sha256sum -c SHA256SUMS)
```

The installable archive is `dist/FingerStore-v1.4.3-module.zip`, the complete source archive is `dist/FingerStore-v1.4.3-source.zip`, and checksums are in `dist/SHA256SUMS`.

GitHub Actions validates code and build archives for each pull request. A successful push to `main` can publish the new version as a verified GitHub prerelease, with an installable asset named `build_fingerprint_date-143-1.4.3.zip`.

## Documentation

- [Technical reference](docs/TECHNICAL.md)
- [Publishing](docs/PUBLISHING.md)
- [Changelog](CHANGELOG.md)
- [Security](SECURITY.md)
- [KernelSU modules](https://kernelsu.org/guide/module.html)
- [Material Web](https://github.com/material-components/material-web)
