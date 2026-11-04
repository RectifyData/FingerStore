# FingerStore

**A KernelSU build identity editor with a local WebUI, persistent fingerprints, SSAID controls, and diagnostic utilities.**

FingerStore is the publishing name for the existing **Build Identity** module. The internal module ID remains `build_fingerprint_date`, so installing updates over v1.4.x preserves saved settings and rollback data. The source is provided so the module can be audited before installation.

## Features

- Editable Android build fingerprint, date, patch *property*, brand, device, model, product and manufacturer.
- Opt-in fingerprint-to-identity autofill; partition property mirroring remains off unless enabled.
- Saved values persist across reboots and in-place upgrades; Restore and Reboot controls in a mobile-first WebUI.
- Experimental opt-in **per-app SSAID** edits staged for early boot, with original backups and conflict detection.
- Local keybox XML profiles and optional deployment to a **separately installed** software KeyMint provider; no provider modification unless explicitly requested.
- Read-only build-property stability comparisons for investigating changing Play Integrity results.

### Security and accuracy

**This does not guarantee any Play Integrity level, hardware-backed attestation, or secure device identity.** Google determines verdicts remotely. Changing a reported patch property does not install security patches; changing the system fingerprint does not change physical device hardware. The optional keybox manager does not convert software attestations into hardware-rooted attestations.

Per-app SSAID modifications **change Android's SettingsProvider user data**, unlike systemless build-property overrides; restoring the app's original ID before uninstall is important. Device compatibility, early boot database timing and attestation-provider behavior have not been validated on all supported Android ROMs. Always keep a known-working module ZIP and device backup, especially on a primary phone.

**Never publish real keybox XML files, private keys, certificate bundles, `ssaid-data`, `config.conf`, or device-derived identifiers.** These are intentionally excluded from release ZIPs and ignored by Git.

## Installation

1. Obtain `FingerStore-v1.4.2-module.zip` from [Releases](https://github.com/WatchFact/fingerstore/releases) **once the repository and release are published**.
2. In KernelSU Manager, choose **Modules → Install from storage** and select the ZIP (not the source ZIP).
3. Reboot, open the **FingerStore** WebUI, and edit your selected fingerprint and other settings.
4. Use **Apply** and then **Reboot**. FingerStore never reboots automatically.

Do **not** flash this ZIP through a custom recovery. Disabling/removing the module returns systemless build overrides to ROM defaults after reboot, but it does not automatically undo SSAID database edits or external provider deployments.

## Build, check, and release

```sh
# Requires Python 3, Node.js and standard shell utilities. No pip dependencies.
python3 scripts/build.py --check
for t in tests/test_*.py; do python3 "$t"; done
for t in tests/test_*.cjs; do node "$t"; done
python3 scripts/build.py
python3 tests/test_release.py
(cd dist && sha256sum -c SHA256SUMS)
```

`dist/FingerStore-v1.4.2-module.zip` is the installable module; the separate `-source.zip` contains source, CI and tests. Checksums are in `dist/SHA256SUMS`. Packaging is reproducible (stable entry order, timestamps and file modes).

GitHub Actions validates every PR and commits on `main`; pushing a `v1.4.2` tag runs KernelSU's official release validator and creates an **immutable GitHub prerelease**, with the installable ZIP normalized to `build_fingerprint_date-142-1.4.2.zip`. Each published version has an immutable tag by convention: bump both `version` and `versionCode` before any new release. The action will not overwrite an existing release. The local `update.json` points to the manually packaged module ZIP and is usable once it is separately attached to a published release; when catalog-listed, the official KernelSU update endpoint can replace it. See [Publishing instructions](docs/PUBLISHING.md).

To submit for the KernelSU Modules catalog, maintain `module.yaml`, enable release immutability on GitHub, and follow the official [KernelSU Modules release criteria](https://developers.kernelsu.org/docs/releasing). A GitHub release is not the same thing as catalog approval.

## Documentation

- [Full technical reference and recovery instructions](docs/TECHNICAL.md)
- [GitHub publishing and versioning](docs/PUBLISHING.md)
- [Security and responsible reporting](SECURITY.md)
- [Release history](CHANGELOG.md)

## Platform references

- [KernelSU module format](https://kernelsu.org/guide/module.html)
- [KernelSU WebUI](https://kernelsu.org/guide/module-webui.html)
- [Android `Build` API](https://developer.android.com/reference/android/os/Build)
- [Google Play Integrity verdicts](https://developer.android.com/google/play/integrity/verdicts)
