# Changelog

## v1.4.3 — Material 3, device demo catalog and apply timing

- Remove SSAID editing, linked SSAID staging, the keybox loader, private profile storage and external software-provider modification code from the installable module and WebUI.
- Add a searchable catalog with **exactly 100 distinct demo device profiles**. Each has a synthetically generated baseline fingerprint, with Android 8–16 versions selectable on demand. These are **examples**, not verified firmware fingerprints, and version choice does not assert an official upgrade path. Pixel 5 XL is not a real Pixel device.
- Use Google Sans Flex, Material 3 design tokens, and Material Web 3 components with offline-compatible native control fallback.
- Add explicit **After reboot (recommended)** and **At runtime (unstable)** apply modes. Reboot staging saves and generates early-boot properties without changing live values; original values are snapshotted before staging to protect Restore.
- Keep the optional read-only local property diagnostics. No device-integrity verdict is guaranteed.
- Upgrades do not automatically reverse SSAID database changes or external provider edits performed by older module versions. Restore those from a backup or the older release if needed.

## v1.4.2 — FingerStore GitHub publishing preparation

- Rebrand the WebUI and module display name to FingerStore while **preserving internal module ID** `build_fingerprint_date` for upgrades.
- Add reproducible installable and source ZIP packaging, checksums, release validation and GitHub Actions CI/release workflow.
- Add official `module.yaml` metadata with a release asset pattern that excludes the source ZIP.
- Add KernelSU update metadata (`updateJson`) and repository documentation.
- Keep v1.4.1's fingerprint, timestamp, SSAID, keybox management and integrity diagnostics implementation unchanged.

The **SSAID edits and optional external software-provider deployment remain experimental**. A physical-device compatibility or Play Integrity verdict is not asserted.

## v1.4.1

- Read-only baseline and comparison diagnostics for changing build identity properties.
- Clarify that copying a provider keybox does not validate or activate trusted hardware attestation.

## v1.4.0

- Opt-in per-app SSAID staging and fingerprint-linked ID generation.
- Local keybox profile vault and explicit external software-provider deployment/restore.

## v1.3.1

- Live-versus-saved property readout, model/product mapping warning, and WebUI restore/copy fixes.

## v1.3.0

- Brand, device, model, product and manufacturer fields; optional autofill; reboot confirmation.

## v1.2.0

- Fix Unix timestamp validation and failure rollback behavior.
