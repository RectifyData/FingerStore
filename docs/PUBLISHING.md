# KernelSU Modules publishing guide — FingerStore

Repository: `https://github.com/RectifyData/FingerStore` (created by its owner).

1. Upload all files from the source ZIP at the repository root (including `module.yaml`, `README.md` and `.github/workflows/release.yml`).
2. In GitHub repository **Settings → General → Releases**, enable **release immutability**. This is required by the KernelSU Modules index.
3. Ensure GitHub Actions is enabled and `GITHUB_TOKEN` has permission to create releases (`contents: write` in the publish job).
4. Push `main` and ensure the validation workflow succeeds. This **does not publish** a release.
5. Push the version tag `v1.4.2` to the tested commit. The official KernelSU Modules `module-release` action validates the ZIP using KernelSU's validator and creates an immutable prerelease. Its uploaded asset name becomes `build_fingerprint_date-142-1.4.2.zip`, matching the `module.yaml` assetPattern.
6. A **prerelease is not offered as stable** in the KernelSU catalog. Given unverified physical-device SSAID/KeyMint behavior, keep this prerelease for testing. After sufficient validation you may promote it by unchecking the GitHub prerelease flag, or publish a new stable version with a **higher versionCode**.
7. Submit the public repository through the official KernelSU Developer Portal at https://developers.kernelsu.org/ ; listing approval is separate from release publication.

Do not publish a real private keybox, `config.conf`, `ssaid-data/`, `integrity-data/` or logs with unique device IDs. The build system checks the release archives for secret filenames and excluded directories. Keep `id=build_fingerprint_date` for existing installations.

The `updateJson` entry targets the public repository and the normalized action-generated ZIP asset. Once KernelSU Modules lists the module, prefer `https://modules.kernelsu.org/api/v1/modules/build_fingerprint_date/update.json` in the **next version**; the index provides a verified, correctly named asset URL for stable releases.

Read the authoritative rules: https://developers.kernelsu.org/docs/releasing and https://developers.kernelsu.org/docs/module-yaml .
