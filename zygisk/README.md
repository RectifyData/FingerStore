# Optional FingerStore Zygisk bridge

The bridge is **off by default**, even if the module ZIP includes libraries.
It only changes the process-local Java `android.os.Build.FINGERPRINT` static
field of **newly forked application processes**, when all of the following hold:

- The module is enabled, with `apply_mode=runtime`.
- The root user explicitly runs `fpctl.sh zygisk enable` (or enables it via WebUI).
- Magisk Zygisk is enabled and the appropriate ABI shared library is installed.
- The target process is an ordinary application, and not Magisk-denylisted.

No Zygisk hooks are installed; system_server is not modified. Existing
processes are **not** patched; restart the target app to reload its cached
`Build.FINGERPRINT`. Direct native property queries remain governed by the
module's normal resetprop behavior. The bridge does not try to alter security
attestation, Google verdicts, or other Android identity fields.

Build with Android NDK r27+:

```sh
cd zygisk
"$ANDROID_NDK_HOME/ndk-build" NDK_PROJECT_PATH=. APP_BUILD_SCRIPT=jni/Android.mk
# Outputs: zygisk/libs/<ABI>/libfingerstore.so
```

The release CI builds all four Android ABIs and packages those ELF files
as `zygisk/<ABI>.so`. Source-only host builds intentionally omit binary
zygisk libraries unless `--with-zygisk` is specified.
