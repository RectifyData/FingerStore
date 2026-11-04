# Changelog

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
