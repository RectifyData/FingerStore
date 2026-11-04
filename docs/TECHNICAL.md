# Build Identity v1.4.1 — diagnostics and compatibility release

v1.4.1 preserves the v1.4.0 fingerprint/date, SSAID, WebUI, and local keybox-provider code. It adds a **read-only stability comparison** to help investigate fluctuating Play Integrity labels without falsely claiming to validate or change server verdicts. The previous release's user configuration is preserved when upgrading with KernelSU Manager.

## Diagnosing fluctuating Play Integrity

1. When integrity labels are passing, open **Integrity stability diagnostics** in the WebUI and tap **Capture passing baseline**.
2. When a label disappears later, tap **Compare after failure**. Any changed build identity, security patch *property*, or local software-provider file selection is listed. If no fields changed, the issue may be provider activation, attestation trust, Google-side policy, licensing, API/service errors, or actual hardware security patch status.
3. Use **Refresh diagnostics** for a current non-destructive status report.

This module **cannot directly query Play Integrity labels**, validate a private key against Google's trust/revocation status, prove TEE/StrongBox activation, or make a software-generated attestation hardware-backed. The diagnostics NEVER read keybox XML, private keys, SSAID records, or account identifiers. Saved baseline is root-only (`integrity-data/passing-baseline.txt`) and stays on device. To delete it, run `sh /data/adb/modules/build_fingerprint_date/bin/integrityctl.sh clear` from root shell.

In Android 13+ Google requires real device integrity and current security updates on all relevant partitions for `MEETS_STRONG_INTEGRITY`; editing build property dates is not equivalent to installing those updates. See https://developer.android.com/google/play/integrity/verdicts and https://kernelsu.org/guide/module.html. If the checks fluctuate, compare the exact same app/account/version after boot and during steady state; do not send private keyboxes or attestation credentials.

## Terminal diagnostics

```sh
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/integrityctl.sh report'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/integrityctl.sh capture'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/integrityctl.sh compare'
```

---

# Build Identity v1.4.0 — KernelSU module

## New in 1.4.0 — Android ID, SSAID, and local keybox profiles

This update preserves the **working v1.3.1 build-property backend** and adds:

- **Per-app Android ID / SSAID (Android 8+)** editing for an installed package in primary user 0. Because Android assigns SSAID by UID, apps sharing a UID share this change. Only existing entries are editable; the module never creates missing entries.
- **Optional stable fingerprint-linked SSAID**, generated from the saved fingerprint, app UID, and a privately stored random salt. This is not a real device- or Google-signed identity and is not guaranteed to survive uninstall/reinstall or UID reallocation. The editor never changes the underlying app signing certificate.
- **Reboot staging** for SSAID: do not edit the SettingsProvider XML while it is live. The editor round-trips XML (including Android binary XML via available `abx2xml` / `xml2abx`), retains an original copy, and checks the database SHA-256 before replacing it during `post-fs-data.sh`. Any conflicting write fails closed. A reboot is needed for the new ID to be observed. **Unlike systemless properties, an applied SSAID edit modifies Android user-data state and remains after disabling the module. Restore the app ID before uninstalling if you want the original value back.**
- **Private keybox profile vault:** root-only XML files stored under `keybox-vault/profiles`; import, list, select, remove. This keeps PEM private-key content out of UI shell-command strings and log output. The WebUI file picker inspects XML **in memory only**, never copies it to root through the JS bridge.
- **Explicit provider deployment / restore:** when **Oh My Keymint is separately installed and enabled**, an intentionally selected keybox profile can be deployed to its canonical `/data/misc/keystore/omk/keybox.xml`, preserving owner, permissions, security context, and a first-use original backup. Use the provider's own WebUI for the most complete certificate-chain and key-pair validation before using it. Provider deployment is never automatic.

### Hardware attestation and software providers — fundamental limit

A keybox XML is **not itself trusted hardware-backed attestation**. A true hardware-backed attestation requires a chain rooted in a trusted provisioning key, protected by TEE or StrongBox, and verified by a service, with revocation and device state. Installing arbitrary files cannot create this secure root. The module does **not** modify TEE firmware, hijack vendor KeyMint HALs, create an attestation bypass, forge Play Integrity labels, or promise MEETS_DEVICE/STRONG_INTEGRITY. The optional external software provider supplies a separate software attestation implementation; this module only safely manages its keybox file. On Android 16-launch devices, Google is migrating to remote-key-provisioning-only attestation rather than user-installable factory keys.

### Android ID / SSAID usage

1. **Back up your device**, especially if it is your only phone. Changing SSAID can log you out of apps, and Android's SettingsProvider XML is safety-critical.
2. Enter an **already installed app's package name** (e.g. `com.example.app`) in the **Android ID / SSAID** card.
3. Leave sync **off** and supply 16 hexadecimal characters, or explicitly toggle **Sync SSAID with saved fingerprint** on.
4. Tap **Stage ID change**, check the pending display, and tap **Reboot** in the floating toolbar. After boot, reopen the app and verify its reported `Settings.Secure.ANDROID_ID`.
5. Use **Restore app ID**, then reboot, to restore its original value; or **Cancel pending** to discard an unapplied change. If the SSAID database changed in the meantime, the module will refuse to overwrite it.

This intentionally does not edit the global `settings secure android_id`, which on Android 8+ is **not** necessarily the ID returned to third-party apps; Android's AOSP SettingsProvider uses the per-UID SSAID table for those apps.

### Keybox profile usage

To import a keybox owned by you, copy it to a private, root-readable absolute path on the device. Do not share it in chat, post it publicly, or leave private keys on public storage. In the WebUI, enter the source XML path and a profile alias, choose **Import into vault**, then **Select profile**. You can inspect an XML file through the picker without saving it. Selecting a profile does not change attestation.

To deploy to a supported **separately installed** software provider, choose **Deploy to software provider** and accept the explicit warning. Only Oh My Keymint's documented canonical path is supported; the provider's native validation/reload implementation is its responsibility. **Restore provider backup** puts the first backed-up keybox back. Other KeyMint software, TEE, and ordinary app signing keys remain untouched by this module. If the provider is not installed, the deploy button fails safely.

Advanced CLI:

```sh
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/ssaidctl.sh status'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/ssaidctl.sh stage com.example.app sync -'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/keyboxctl.sh status'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/keyboxctl.sh import mykey /data/local/tmp/owned-keybox.xml'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/keyboxctl.sh select mykey'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/keyboxctl.sh deploy-omk'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/keyboxctl.sh restore-omk'
```

The keybox manager performs **structural**, not full cryptographic verification; it does not check key/certificate correspondence or revocation itself. A corrupted or incorrectly provisioned keybox can be rejected by the provider and may prevent attestation. Consult the provider's full certificate-validation tools and do not use irreplaceable credentials as a test fixture.

### New tests and limitations

Host simulations cover per-app UID editing, staged early-boot XML replacement, concurrent-file hash mismatches, abort on malformed input, multi-app stages, fingerprint-sync stability, vault permissions, deploy/restore, profile switching, missing provider, script checks, and ZIP integrity. They **cannot prove** a real Samsung firmware's early-boot timing, SSAID binary XML compatibility, SELinux file labels, software provider reload or Play Integrity acceptance. Unlike v1.3.1, the SSAID XML feature is **experimental** and **off until you choose to stage an edit**.

### Additional references

- AOSP SettingsProvider: https://android.googlesource.com/platform/frameworks/base/+/master/packages/SettingsProvider/src/com/android/providers/settings/SettingsProvider.java
- Android hardware-backed attestation: https://developer.android.com/privacy-and-security/security-key-attestation
- KeyMint and attestation security levels: https://source.android.com/docs/security/features/keystore/attestation
- KernelSU module WebUI: https://kernelsu.org/guide/module-webui.html
- External software provider: https://github.com/ITxiao6666/OhMyKeymint

---


A systemless, offline, mobile-first KernelSU build-property editor. Version 1.4.0 retains the tested v1.3.0 property engine, adds saved-versus-active property checks and fixes copying the currently active security patch and mirror setting. Version 1.3.0 adds editable **brand, device codename, model, product name, and manufacturer**, optional fingerprint-driven auto-fill, and a **confirmation-protected Reboot button** in the floating WebUI toolbar. It retains v1.2.0's working fingerprint/date behavior, 32-bit timestamp fix and persistent settings.

## Install or upgrade

1. Open **KernelSU Manager → Modules → Install from storage**.
2. Choose `KSU-Build-Identity-v1.4.1.zip`. For an existing v1.2.0 or later install, install over the same module ID (`build_fingerprint_date`) rather than uninstalling it first.
3. Reboot if KernelSU requests it; open **Build Fingerprint & Date Editor → WebUI**.
4. Edit the fingerprint, UTC build date, optional patch date, and device identity.
5. Tap **Apply changes**, then tap **Reboot** and explicitly confirm. The chosen values remain in effect across subsequent reboots until you change them or press Restore.

Do not flash this KernelSU manager ZIP through custom recovery.

### Screenshot example

For this fingerprint:

```
samsung/r13sxxx/r13s:16/BP2A.250605.031.A3/S731BXXS6AZCH:user/release-keys
```

Turn on **Auto-fill identity from fingerprint** and the following fields are filled in:

| WebUI field | Inferred value | Android property |
| --- | --- | --- |
| Brand | `samsung` | `ro.product.brand` |
| Device codename | `r13s` | `ro.product.device` |
| Model | `SM-S731B` | `ro.product.model` |
| Product name | `r13sxxx` | `ro.product.name` |
| Manufacturer | `samsung` | `ro.product.manufacturer` |

**Auto-fill is opt-in** and saved with the configuration. Brand, device codename and product name are syntactically encoded in a standard fingerprint. The *model is not*. The module infers the Samsung `SM-...` model **only** from a recognized Samsung build-incremental code; if it cannot safely determine the model, the model input remains editable. When auto-fill is **off**, all five identity fields are editable manually. The WebUI and shell backend both enforce the toggle; a manual model can be entered when inference is unavailable. To avoid mismatched identities, changing to an unrecognized fingerprint while auto-fill is on clears a previously filled model.

The screenshot's **Play Integrity verdict labels** and **TestId** are generated by Google and cannot be controlled by editing `ro.*` build properties. The module does not promise to change Play Integrity levels, KeyMint/TEE evidence, hardware identifiers or actual security-patch status.

## Property coverage

- `ro.build.fingerprint`: Android `Build.FINGERPRINT`.
- `ro.build.date.utc`: Unix seconds for Android `Build.TIME`; valid UTC dates range from 2000-01-01 through 2100-01-01.
- `ro.build.date`: human-readable UTC build date.
- `ro.build.version.security_patch`: optional *reported* security patch (`YYYY-MM-DD`).
- `ro.product.brand`, `.device`, `.model`, `.name`, `.manufacturer`: optional manual or auto-filled product identity.
- Advanced mirror: `ro.{system,system_ext,product,vendor,odm,bootimage}.build.{fingerprint,date.utc,date}` and pre-existing `ro.product.{system,system_ext,product,vendor,odm}.{brand,device,model,name,manufacturer}` properties.

Mirror mode defaults to **off** to minimize cross-partition metadata changes; missing partition properties are not invented. Changing fingerprint/model does **not** change the real OS, installed security updates, hardware, or a cryptographic attestation result.

## Persistence and rollback

- The user selection is stored privately as `config.conf` in the module directory; it never expires by time and survives reboots.
- KernelSU loads the generated `system.prop` at startup. `service.sh` and `boot-completed.sh` reassert the selection after boot when necessary. No always-running daemon is used.
- `original.props` retains the original reported property values that were modified. **Restore** disables overrides and restores saved original values where available; reboot afterward to refresh cached fields.
- Existing `config.conf`, `original.props` and derived `system.prop` are retained across in-place upgrades. v1.2.0's saved configuration is compatible with v1.3.1 without rewriting the original backup.
- The `set` command writes configuration and startup properties transactionally: on an apply error, the previous saved selection is retained and live rollback is attempted.
- These changes remain effective **while this KernelSU module is installed and enabled**. They are not permanent edits to read-only firmware. Disabling/uninstalling the module or removing root can undo them on a reboot.

## WebUI and CLI

The WebUI runs completely offline through the KernelSU Manager WebView. Its floating action toolbar contains **Restore**, **Apply changes**, and **Reboot**. Reboot requires explicit confirmation, and warns if you have unapplied edits. Some apps cache `android.os.Build` values; reboot after applying or restoring for consistent reporting.

Advanced root-shell usage:

```sh
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh status'
# Legacy v1.2.0 syntax (no identity override):
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh set "samsung/r13sxxx/r13s:16/BP2A.250605.031.A3/S731BXXS6AZCH:user/release-keys" 1754006400 - 0'
# Extended syntax: fingerprint epoch patch mirror autofill brand device model product manufacturer
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh set "samsung/r13sxxx/r13s:16/BP2A.250605.031.A3/S731BXXS6AZCH:user/release-keys" 1754006400 - 0 1 samsung r13s SM-S731B r13sxxx samsung'
su -c 'sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh disable'
```

`reboot` is also available via CLI; it is intended for deliberate interactive use only, not for installation or boot scripts. The module will **never** reboot automatically when applying values.

## Cautions and recovery

Using build identity data from an incompatible ROM/device can cause app incompatibilities or startup trouble. Keep an offline copy of the v1.2.0 ZIP and make a backup before changing system build metadata. If Android fails to boot, use KernelSU safe mode (see the rescue documentation linked below), or otherwise disable the module via recovery if supported.

## Testing

Automated tests use fake `getprop`, `resetprop`, property stores, and a fake reboot service. They test original fingerprint/date functionality, v1.2.0 migration, opt-in autofill, screenshot Samsung model inference, manual identity fields, partition mirroring, restoration, invalid inputs, a reboot confirmation, failed-apply rollback, 32-bit-safe timestamp bounds and multiple simulated boot cycles. JavaScript WebUI code is checked with Node.

**No physical Samsung/Pixel phone or actual boot has been tested with v1.3.1.** Host simulations cannot guarantee behavior on every ROM, Android version or manager build.

## References

- KernelSU module documentation: https://kernelsu.org/guide/module.html
- KernelSU WebUI documentation: https://kernelsu.org/guide/module-webui.html
- Android Developers, `android.os.Build`: https://developer.android.com/reference/android/os/Build
- Android dynamic fingerprints: https://source.android.com/docs/core/ota/tools
- KernelSU rescue: https://kernelsu.org/guide/rescue-from-bootloop.html
- Community discussion of build identity / integrity (independent reports, not specifications): https://www.reddit.com/r/KernelSU/


## Understanding Samsung identity fields (v1.3.1 clarification)

For `samsung/a24nsxx/a24:16/UP1A.250605.014/A245FXXU9EYK1:user/release-keys`, the correct readouts are `ro.product.brand=samsung`, `ro.product.name=a24nsxx` (the product code), `ro.product.device=a24` (the codename), and `ro.product.model=SM-A245F` (recognized model). **Do not swap the model and product code.** They are distinct Android properties, and `Build.MODEL` reads `ro.product.model`, while `Build.PRODUCT` reads `ro.product.name`. Fingerprint matching doesn't imply Google Play Integrity approval.

**Readout consistency:** A new Current state indicator compares the saved fingerprint, timestamp, optional patch, and nonblank identity fields to the live `getprop` values. It highlights mismatches and potentially inconsistent manually entered fields. It verifies local property values only, not SafetyNet/Play Integrity or hardware-backed attestation. The screen explains the fingerprint layout and flags the specific model/product swap shown in misleading online advice.

**Bug fix:** `Use currently active values` now copies the active security-patch date rather than quietly discarding it, and retains the saved mirror setting instead of always forcing it off.
