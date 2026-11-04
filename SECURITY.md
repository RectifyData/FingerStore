# FingerStore security policy

Never open an issue containing a private attestation keybox, certificate private keys, app SSAIDs or other identifying device records. Redact them in logs and screenshots.

The app's fingerprint property changes do not authenticate to Google or turn software attestation into hardware-backed attestation. The experimental SSAID staging operates on Android private settings files; it can affect accounts and app data. It must not be used without adequate rollback capability.

For sensitive security reports, contact the repository owner through their private GitHub communication channels, if configured. Ordinary feature requests or reports **without** personal data can be filed in GitHub Issues once the repository exists.
