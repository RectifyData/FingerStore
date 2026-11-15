# FingerStore independent GitHub publishing

**KernelSU Modules catalog eligibility is NOT required.**

The multi-source offline catalog is generated with `python3 scripts/refresh_catalog.py`, with the companion refresh workflow `.github/workflows/catalog-sync.yml`. Refreshing data must not invent fingerprints from Flash Index build IDs or firmware-partition values. New snapshot changes go through CI and a new versioned prerelease. FingerStore is distributed through its own GitHub repository, using GitHub Releases. The ZIP is compatible with Magisk and KernelSU.

1. Keep `module.prop`, `update.json`, and `CHANGELOG.md` versioned together: current release **1.4.7**, `versionCode=147`.
2. Open a pull request, and require its GitHub Actions workflow to pass before merging.
3. GitHub Actions runs syntax checks, full host regression tests, builds all four Zygisk libraries with Android NDK r27, and creates a deterministic ZIP with published SHA256 checksums. Build failures abort release.
4. After verified changes land in `main`, CI uploads a standalone GitHub prerelease tagged `v1.4.7` with the installable module, source ZIP and SHA256SUMS. The installer ZIP has the normalized name `build_fingerprint_date-147-1.4.7.zip` matching `update.json`.
5. Existing tags/releases are not overwritten. Bump both the module version and `versionCode` for a new release.
6. Test on physical devices before claiming stable compatibility. Zygisk's runtime Java field injection is experimental until proven on target Android versions.

Never publish `config.conf`, `original.props`, `zygisk.conf`, `integrity-data/`, `keybox-vault/` or `ssaid-data/`. Packaging excludes user state.

The original module ID remains `build_fingerprint_date` to preserve install continuity. This release never requires KSU catalog approval or a third-party publishing token.
