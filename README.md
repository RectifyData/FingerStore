# FingerStore

**FingerStore v1.4.5** is a Magisk- and KernelSU-compatible systemless Android build identity module. The internal module ID stays `build_fingerprint_date` so existing configurations can be upgraded.

## Core features

- Edit Android build fingerprint, build timestamp, reported security-patch property, brand, device, retail model, product name and manufacturer.
- Choose **After reboot (recommended)** to stage changes for startup, or **At runtime (unstable)** to apply immediately with root `resetprop -n`. Running apps may retain cached identity, and competing modules can override runtime values.
- Opt-in partition identity mirroring, fingerprint-to-identity autofill and a Restore action.
- Exactly **100 built-in profiles containing 186 recorded stock firmware fingerprints**, copied unchanged from the historical MagiskHide Props Config v137 list (community-curated and described upstream as certified). **No generated or fabricated fingerprints.** The Android picker only offers the actual OS versions recorded for each model. The included builds are historical (currently Android 7.1–12), not independently reverified against OEM firmware or current Play Integrity rules.
- Mobile-first WebUI using Google Sans Flex and Material 3 styling, with optional Material Web controls and a native offline fallback. The WebUI is available in compatible module managers; stock Magisk does not provide KernelSU's WebUI bridge.
- Local read-only property stability diagnostics.

## Built-in stock fingerprints

Select **Built-in fingerprint catalog**, search for a device, and choose one of the Android releases that has an actual recorded stock fingerprint. Selecting a profile fills the exact fingerprint and matching device identity, and sets a source-provided security patch when available. The original list does **not** provide build timestamps, so FingerStore leaves the date blank rather than inventing one: enter the true matching firmware date before applying. Stock fingerprints are historical references, not guarantees of compatibility with a custom ROM or attestation.

## Magisk support

Install the **module ZIP** from [GitHub Releases](https://github.com/RectifyData/FingerStore/releases) through **Magisk → Modules → Install from storage**. Installation is visible in Magisk and does not use a silent setup. Reboot afterward.

Magisk executes the module's `system.prop` and `service.sh` integration and provides `resetprop` for live property application. In the Magisk module screen, the **Action** button prints the saved/active state and CLI usage.

For root-shell control (e.g. Termux with `su`):

```sh
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh status'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh zygisk status'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh disable'
```

To configure a fingerprint without a WebUI, the root CLI accepts:

```text
fpctl.sh set <fingerprint> <UTC-epoch> <patch-or-dash> <mirror-0|1>   <autofill-0|1> <brand> <device> <model> <product> <manufacturer> <reboot|runtime>
```

Existing 4-argument and 10-argument forms remain supported for backward compatibility and retain their historical immediate runtime behavior.

### Optional Zygisk: **only runtime fingerprint injection**

Zygisk is **OFF by default**. FingerStore works normally under Magisk or KernelSU without it. The release module ZIP contains four native ABI libraries, but they do not inject anything unless you explicitly enable the FingerStore toggle.

To use it:

1. In Magisk settings, turn on **Zygisk**, then reboot so Magisk loads Zygisk support.
2. Save a fingerprint in FingerStore using **At runtime (unstable)** mode. Zygisk does nothing in **After reboot** mode.
3. Enable **Optional Zygisk** in a compatible WebUI or run:

   ```sh
   su -c 'sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh zygisk enable'
   ```

4. Completely restart the target app (force stop and reopen) so it starts a new Zygisk-managed process.

Disable it at any time:

```sh
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh zygisk disable'
```

The Zygisk bridge changes **only the process-local Java `android.os.Build.FINGERPRINT` field in newly launched app processes**. It does not modify `system_server`, hook native property APIs, or change other build fields. It does not modify existing app processes. Zygisk is **not** a substitute for the core Magisk/KSU systemless property editor, and it does not guarantee Play Integrity or attestation results.

This is an experimental native feature without physical-device validation. Leave it disabled if you do not specifically need runtime Java fingerprint injection.

## Upgrade safety

Previously included SSAID editing and keybox-loader features were removed in v1.4.3. Upgrading does not reverse external SSAID or attestation-provider changes made with older versions; restore them from appropriate backups if necessary.

No real keyboxes, passwords, user-specific identifiers, `config.conf`, `original.props`, `zygisk.conf` or diagnostics data are published in release ZIPs. The Zygisk bridge does not install hooks in target apps and is automatically unloaded after specialization.

## Build / test / release

Source checks work on any host with Python 3, Node.js and shell tools:

```sh
python3 scripts/build.py --check
for test in tests/test_*.py; do python3 "$test"; done
for test in tests/test_*.cjs; do node "$test"; done
```

To compile the optional Zygisk libraries, use **Android NDK r27+**:

```sh
cd zygisk
"$ANDROID_NDK_HOME/ndk-build"
cd ..
python3 scripts/build.py --with-zygisk
python3 tests/test_release.py
(cd dist && sha256sum -c SHA256SUMS)
```

A source-only module ZIP without native binaries can also be built with `python3 scripts/build.py`, but it cannot enable the optional Zygisk feature. GitHub Actions always compiles, validates and packages all four ABIs for official release assets.

All releases are published as standalone GitHub prereleases, **without requiring acceptance into the KernelSU Modules catalog**. The v1.4.5 installable asset name is `build_fingerprint_date-144-1.4.4.zip`; the release also provides full source and SHA256 checksums.

## References

- [Catalog provenance, authenticity limits and source](docs/CATALOG_SOURCES.md)
- [Technical reference](docs/TECHNICAL.md)
- [Release and publishing instructions](docs/PUBLISHING.md)
- [Optional Zygisk module source](zygisk/README.md)
- [Changelog](CHANGELOG.md)
- [Magisk](https://github.com/topjohnwu/Magisk)
- [Official Zygisk module sample](https://github.com/topjohnwu/zygisk-module-sample)
