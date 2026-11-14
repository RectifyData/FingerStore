# FingerStore v1.4.3 — Technical reference

## Scope

FingerStore is a KernelSU systemless module whose stable internal ID is `build_fingerprint_date`. It edits build identity only: fingerprint, dates, optional reported patch level, and selected `ro.product.*` identity values. It does **not** change the actual Android build, installed firmware, verified boot state, security patches or Google's Play Integrity verdict.

Android SSAID editing, the keybox XML loader, keybox profiles and external software-provider deployment were removed in v1.4.3. Those old features are no longer invoked by startup or installed in the ZIP. **The module does not attempt to revert external data changed by older releases**.

## WebUI

`webroot/index.html` contains the mobile-first editor with Google Sans Flex and Material 3 theme tokens. Material Web components for the catalog use an optional import-map/CDN loading path. When network access or custom elements are unavailable, native controls remain usable with Material 3 styling.

`webroot/catalog.js` defines 100 fixed demo devices, their synthetic identity slugs and deterministic example fingerprint generator. Each device has one Android 14 baseline example. Android 8–16 choices generate a version-specific fingerprint on demand, without adding catalog records. All outputs use `demo_` product and device fields and `DEMO` incremental tags. They are not copied from manufacturer firmware.

## Save and apply modes

`sh bin/fpctl.sh set <fingerprint> <epoch> <patch-or-dash> <mirror-0|1> <autofill-0|1> <brand> <device> <model> <product> <manufacturer> <runtime|reboot>`

The historical 4-payload-argument and 10-payload-argument forms are retained and default to `runtime` for backward compatibility. The WebUI defaults to `reboot` for a fresh selection.

- **`runtime`**: save validated configuration, regenerate `system.prop`, and apply to live properties through KernelSU `resetprop -n`. This path is explicitly unstable: Java-level cached Build values, existing processes, services or another module may disagree. Saved state remains active after reboot.
- **`reboot`**: snapshot existing values into `original.props` before writing `system.prop`; atomically save config and generate boot-time overrides; do not call `resetprop` to change running properties in this command. The module's boot scripts reassert values after startup. Reboot is user-controlled.
- **`disable`**: disable overrides, clear `system.prop` and restore original live properties from the snapshot when available; reboot is recommended for cached Android identity.

A transaction backup protects saved settings, staged startup properties and snapshots if stage generation fails. At boot, `service.sh` and `boot-completed.sh` call `fpctl.sh apply` if configuration exists, to reassert properties overwritten by ROM services. There is no continuous background daemon.

Configuration remains at `config.conf`, original property snapshot at `original.props` and generated startup values at `system.prop`. User/private state is not included in release assets.

## Catalog and version semantics

The number **100** refers to distinct catalog device entries and baseline example fingerprints. Version changes generate a different **synthetic sample** for the same entry. The Android 8–16 menu is a demonstration tool, not an official update catalog or device-compatibility database.

The sample builds use recognizable Android build ID formats only to demonstrate string structure. Users must independently verify real values for an actual build and the matching security patch level.

## Diagnostics

`bin/integrityctl.sh` takes `report`, `capture`, `compare` and `clear`. It reads only a fixed set of local non-secret properties and stores optional, root-only comparison data under `integrity-data`. It does not inspect a keybox or modify an attestation provider, nor does it retrieve Google's remote verdict.

## Compatibility / recovery

- Requires a KernelSU-compatible module manager and appropriate `resetprop` support for live changes.
- Mirroring does not invent partition properties that the ROM does not expose.
- Reboot-time property application cannot be guaranteed on every ROM without device tests.
- If fingerprint settings cause apps to behave incorrectly, open the WebUI and use **Restore**, then reboot. Keep a known-good ZIP and device backup.
- Users who previously modified SSAID or deployed third-party keybox files through old releases must restore those external changes separately before/after upgrade as appropriate; this release deliberately leaves unrelated settings untouched.

## Validation

`scripts/build.py` checks package identity, version metadata, forbidden private files and deterministic ZIP output. `tests/` covers identity validation, rollback, generated demonstrations, WebUI event wiring, runtime/reboot modes and packaging. GitHub Actions runs Python, Node and shell syntax checks. These are host tests, not evidence of physical-device boot compatibility.
