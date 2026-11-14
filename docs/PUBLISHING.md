# Publishing FingerStore

Repo: https://github.com/RectifyData/FingerStore

1. Use a new semantic version and `versionCode` for each immutable release. The current version is **1.4.3**, code **143**.
2. Keep `module.prop`, `module.yaml`, `update.json` and `CHANGELOG.md` synchronized.
3. Enable GitHub Actions and release immutability in repository Settings. The release job needs `contents: write`.
4. Open a pull request; all Python, Node.js, shell and reproducible ZIP checks must pass.
5. Merge validated changes into `main`. The CI workflow detects an absent `v1.4.3` release and uses the KernelSU Modules validation/release action to publish a GitHub **prerelease**. It does not overwrite an existing immutable release. A push to a tag validates but does not duplicate publication.
6. Confirm the release includes the installable `build_fingerprint_date-143-1.4.3.zip` artifact. The URL must match `update.json`.
7. Physical-device boot behavior has not been verified, so do not claim the prerelease is daily-driver safe. KernelSU catalog inclusion is a separate approval process at https://developers.kernelsu.org/.

The catalog has exactly 100 synthetic demo device entries; it does not ship real OEM fingerprint databases, private keys, prior SSAID state or keybox data. Never publish `config.conf`, `original.props`, `integrity-data/`, old `ssaid-data/` or `keybox-vault/`. These are excluded by the packaging rules.

The internal module ID stays `build_fingerprint_date` for safe upgrades. Old external SSAID or keybox-provider changes must be separately restored if a previous release modified them.

References: https://developers.kernelsu.org/docs/releasing and https://developers.kernelsu.org/docs/module-yaml
