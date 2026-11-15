# FingerStore v1.4.6 — Technical reference

## Scope

FingerStore is a Magisk / KernelSU systemless module whose stable internal ID is `build_fingerprint_date`. It edits build identity only: fingerprint, dates, optional reported patch level, and selected `ro.product.*` identity values. It does **not** change the actual Android build, installed firmware, verified boot state, security patches or Google's Play Integrity verdict.

Android SSAID editing, the keybox XML loader, keybox profiles and external software-provider deployment were removed in v1.4.3. Those old features are no longer invoked by startup or installed in the ZIP. **The module does not attempt to revert external data changed by older releases**.

## Magisk integration and optional Zygisk

The normal systemless implementation uses `module.prop`, `customize.sh`,
`system.prop`, `service.sh`, `action.sh`, and the root CLI at `bin/fpctl.sh`.
Magisk and KernelSU can both install the standard ZIP. Stock Magisk does
not expose the KernelSU WebUI bridge; use the action button and root CLI
or a compatible third-party WebUI host.

The optional Zygisk bridge is **disabled by default**, even though GitHub
release ZIPs contain compiled four-ABI native libraries. The separate private
`zygisk.conf` opt-in is preserved across upgrades. Enable via:
`sh bin/fpctl.sh zygisk enable`, disable with
`sh bin/fpctl.sh zygisk disable`, and inspect with
`sh bin/fpctl.sh zygisk status`.

Zygisk is used **only** for **runtime Java fingerprint injection**. Its
`preAppSpecialize` reads `zygisk.conf`, `config.conf` and the chosen
fingerprint through the module directory file descriptor. It activates only
for an explicitly enabled module with `apply_mode=runtime`, a valid saved
fingerprint, and a non-denylisted application UID (10,000+). In
`postAppSpecialize`, it modifies the new app's
`android.os.Build.FINGERPRINT` static field through JNI. No system_server
callback or hook is registered. The Zygisk module requests unloading after
specialization and does not maintain persistent native hooks.

The native module does **not** change already-running processes, global
native property getters, any other Build fields, cryptographic attestation,
or Google's remote verdict. Magisk's global Zygisk setting must already be
enabled; reboot after turning it on, and restart target apps after opting
into FingerStore's bridge. Runtime injection is experimental and requires
device-level verification.

Native source: `zygisk/jni/fingerstore.cpp` and the official 0BSD Zygisk
API v5 header in `zygisk/jni/zygisk.hpp`. The source build excludes
NDK-generated binary output. Official release CI compiles native libraries for
`armeabi-v7a`, `arm64-v8a`, `x86`, and `x86_64` and verifies each ELF's
architecture before packaging to `zygisk/<abi>.so`.

## WebUI

`webroot/index.html` contains the mobile-first editor with Google Sans Flex and Material 3 theme tokens. Material Web components for the catalog use an optional import-map/CDN loading path. When network access or custom elements are unavailable, native controls remain usable with Material 3 styling.

`webroot/catalog.js` is a generated offline database containing **524 device profiles and 839 exact source fingerprint strings** in the first v1.4.6 snapshot, including Android 13–17 records. It consolidates the entire historical MagiskHide Props Config list, DeviceAnon and OTA-derived Pixel-Props release assets; records list only the Android versions actually found in source data and preserve multiple firmware builds per version. The WebUI exposes a version selector and exact build selector with provenance. ChkDumps dumps and Google's Android Flash Index are integrated as **firmware references**, but partition-only fingerprints and bare build IDs are not turned into spoofable device profiles. See [source provenance](CATALOG_SOURCES.md) and [the refresh importer](../scripts/refresh_catalog.py).

## Save and apply modes

`sh bin/fpctl.sh set <fingerprint> <epoch> <patch-or-dash> <mirror-0|1> <autofill-0|1> <brand> <device> <model> <product> <manufacturer> <runtime|reboot>`

The historical 4-payload-argument and 10-payload-argument forms are retained and default to `runtime` for backward compatibility. The WebUI defaults to `reboot` for a fresh selection.

- **`runtime`**: save validated configuration, regenerate `system.prop`, and apply to live properties through KernelSU `resetprop -n`. This path is explicitly unstable: Java-level cached Build values, existing processes, services or another module may disagree. Saved state remains active after reboot.
- **`reboot`**: snapshot existing values into `original.props` before writing `system.prop`; atomically save config and generate boot-time overrides; do not call `resetprop` to change running properties in this command. The module's boot scripts reassert values after startup. Reboot is user-controlled.
- **`disable`**: disable overrides, clear `system.prop` and restore original live properties from the snapshot when available; reboot is recommended for cached Android identity.

A transaction backup protects saved settings, staged startup properties and snapshots if stage generation fails. At boot, `service.sh` and `boot-completed.sh` call `fpctl.sh apply` if configuration exists, to reassert properties overwritten by ROM services. There is no continuous background daemon.

Configuration remains at `config.conf`, original property snapshot at `original.props` and generated startup values at `system.prop`. User/private state is not included in release assets.

## Catalog and version semantics

The number **100** refers to distinct built-in device profiles. There are **186 recorded source fingerprints** across the available version options (Android 7.1 through 12 in this historical snapshot). Switching versions selects a literal stock fingerprint found in the source; there is no fallback or fabricated version. Unsupported Android versions are absent from the selector. The source's optional `__YYYY-MM-DD` patch suffix is not part of the fingerprint and is transferred to the patch field only when present.

The list does **not** record a trustworthy `ro.build.date.utc` for each build. Selecting any stock entry therefore clears the build date field and requires manual entry of the actual matching firmware timestamp before applying. Neither a security-patch date nor an Android release date is substituted for the build date. This catalog is a historical community-contributed reference and is not a live certification, compatibility or attestation service.

## Diagnostics

`bin/integrityctl.sh` takes `report`, `capture`, `compare` and `clear`. It reads only a fixed set of local non-secret properties and stores optional, root-only comparison data under `integrity-data`. It does not inspect a keybox or modify an attestation provider, nor does it retrieve Google's remote verdict.

## Compatibility / recovery

- Requires a Magisk- or KernelSU-compatible module manager and appropriate `resetprop` support for live changes.
- Mirroring does not invent partition properties that the ROM does not expose.
- Reboot-time property application cannot be guaranteed on every ROM without device tests.
- If fingerprint settings cause apps to behave incorrectly, open the WebUI and use **Restore**, then reboot. Keep a known-good ZIP and device backup.
- Users who previously modified SSAID or deployed third-party keybox files through old releases must restore those external changes separately before/after upgrade as appropriate; this release deliberately leaves unrelated settings untouched.

## Validation

`scripts/build.py` checks package identity, version metadata, forbidden private files and deterministic ZIP output. `tests/` covers identity validation, rollback, generated demonstrations, WebUI event wiring, runtime/reboot modes and packaging. GitHub Actions runs Python, Node and shell syntax checks. These are host tests, not evidence of physical-device boot compatibility.
