# Built-in stock fingerprint catalog: provenance and limitations

FingerStore v1.4.5 replaces the original synthetic `demo_` identities and invented Android release variants with **100 distinct device entries and 186 literal fingerprints copied unchanged** from a public, community-curated historical stock-fingerprint list.

## Original source

- **Project:** [MagiskHide Props Config](https://github.com/Magisk-Modules-Repo/MagiskHidePropsConf)
- **Original data:** [`common/prints.sh`](https://github.com/Magisk-Modules-Repo/MagiskHidePropsConf/blob/master/common/prints.sh)
- **Upstream list marker:** `PRINTSV=137`, published by the upstream project in 2021.
- **Exact source Git blob SHA used for extraction:** `dbddef20bea59e12290b936eb751ed74d38456b0`.
- **Original notice:** Copyright (c) 2018–2021 Didgeridoohan @ XDA Developers; licensed MIT.
- **Scope:** Only entries from the source's `PRINTSLIST` with a structurally valid `user/release-keys` fingerprint were selected. Device names and manufacturer/retail-model metadata come from the same source record.

The original project describes the list as *certified fingerprints* gathered from real stock devices/firmware, but **FingerStore has not independently downloaded or checked all 100 OEM factory images**. These are authentic **recorded** stock-build fingerprints, not freshly validated OEM certificates. They may be outdated, may not match your regional device build or security patch, and do **not** guarantee CTS, Play Integrity or other attestation results.

## Selection and version handling

Each catalog record contains literal full fingerprints for only the Android versions listed in the original source. **No Android release or build ID is fabricated.** The 186 available selections span Android 7.1 through 12 in this historical snapshot. Android 13–16 do not appear because this source snapshot does not contain those builds. For example, the Pixel 5 has historical Android 11 and 12 stock entries; an Android 13 profile is not silently generated.

FingerStore parses the genuine `brand/product/device:version/build-id/incremental:user/release-keys` string and uses its source-provided manufacturer and retail-model data. When an entry has a `__YYYY-MM-DD` suffix in the source list, that value is used only as the security patch value and **never appended** to the fingerprint.

**Build date:** the source does not include a reliable `ro.build.date.utc` value for each fingerprint. FingerStore deliberately empties the date input when a catalog entry is loaded, rather than making one up. Enter the correct stock firmware build timestamp before applying; it is not the same as the security patch date.

## How to independently check one entry

On matching unmodified stock firmware, inspect `adb shell getprop ro.build.fingerprint`, `ro.product.model`, and `ro.build.version.security_patch`. Compare byte-for-byte with the selected source record. Google documents extracting and checking Pixel fingerprints against its [Pixel Binary Transparency log](https://developers.google.com/android/binary_transparency/pixel_verification) for Pixel 6 and later.

This data and the upstream MIT attribution are included in both FingerStore's source archive and its installable module README. If modern devices or Android 13–16 builds are added later, they require new **source-verifiable literal fingerprints**, not templated strings.
