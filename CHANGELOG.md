# Changelog

## v1.4.6 — Multi-source stock fingerprint database

- Expand from 100 devices / 186 builds to a checked-in **524-device, 1,098-entry** offline snapshot with Android 13–17 records. Import the full historical MagiskHide Props Config collection, community DeviceAnon records, and exact OTA-extracted Pixel-Props property values, including 328 imported Pixel records from all 52 available historical release collections.
- Support multiple **real firmware builds per Android version** and choose each exact fingerprint instead of generating synthetic Android/build IDs. Preserve source, original asset URL, known patch and real build date.
- Integrate ChkDumps dump inspections and Google Android Flash Index as **firmware-discovery sources**, without treating partition-only fingerprints or image metadata as verified global device fingerprints.
- Add a source-aware import/refresh script and GitHub Actions snapshot workflow; maintain offline operation and source attribution. Improve import support for valid Huawei/Honor incremental IDs containing parentheses.
- Preserve Magisk/KernelSU compatibility, optional runtime-only Zygisk (disabled by default), the Material 3 WebUI and reboot/runtime modes.
- Entries are source-recorded, not newly OEM-attested; no physical-device boot or injection test has been performed. Release remains experimental.


## v1.4.5 — Authentic built-in stock fingerprints

- Replace the synthetic 100-device `demo_` catalog and generated Android 8–16 strings with **100 actual stock-build profiles and 186 literal source fingerprints** from the historical MIT-licensed MagiskHide Props Config v137 `prints.sh` list.
- Show **only recorded Android version options** for each device; reject absent versions rather than constructing plausible but fictional fingerprints. Stock fingerprint, original product/device identifiers, retail model, manufacturer, and source-reported patch are loaded together.
- Do not invent build timestamps. Clear the date field on catalog selection and require the real matching firmware build date before applying.
- Include provenance, source limitations and new catalog/WebUI validation tests. Historical records are not newly OEM-verified or guaranteed to pass Play Integrity.
- Preserve Magisk, KernelSU, and disabled-by-default optional Zygisk runtime injection from v1.4.4. Still an experimental prerelease pending physical-device validation.

## v1.4.4 — Magisk compatibility and optional Zygisk

- Support standard Magisk installation and boot integration, preserve existing KernelSU support and stable internal module ID.
- Ship native optional Zygisk modules compiled for arm64-v8a, armeabi-v7a, x86 and x86_64.
- **Zygisk is disabled by default**. Users can explicitly opt in via WebUI or root CLI; it only injects the selected Java `android.os.Build.FINGERPRINT` value into newly launched apps **in runtime apply mode**. The bridge does nothing in after-reboot mode, does not alter system_server, and installs no hooks.
- Runtime fingerprint injection is experimental and cannot update already-running apps. Magisk's Zygisk must be enabled separately in Magisk settings; reboot once to load the bridge, then restart target apps.
- Improve Magisk installer messages, provide a useful manager action/CLI, and stop touching deleted legacy installer scripts.
- Replace KernelSU Modules catalog validation and release dependency with independent GitHub Actions testing, Android NDK compilation, deterministic package verification and standalone GitHub prerelease publishing.
- Keep the 100-entry **synthetic** demo catalog from v1.4.3; examples are not verified OEM fingerprints.
- No physical-device Zygisk compatibility or boot testing has been performed. Use this as an experimental prerelease.

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
