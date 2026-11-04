#!/system/bin/sh
# One-shot, fail-closed SSAID update before Android SettingsProvider loads.
# No XML parser or Java runtime is required at this early boot stage.
MODDIR=${0%/*}
DATA="$MODDIR/ssaid-data"
META="$DATA/pending.meta"
PENDING="$DATA/pending.bin"
RESULT="$DATA/last-result.txt"
ROOT=${SSAID_TEST_ROOT:-/data/system/users/0}
TARGET="$ROOT/settings_ssaid.xml"
[ -f "$META" ] && [ -s "$PENDING" ] || exit 0
umask 077
fail(){ printf 'ERROR: %s\n' "$1" > "$RESULT"; exit 1; }
expected=$(sed -n 's/^source_sha=//p' "$META" | head -n 1)
case "$expected" in ''|*[!0-9a-f]*) fail 'invalid pending hash' ;; esac
[ "${#expected}" -eq 64 ] || fail 'invalid pending hash length'
[ -f "$TARGET" ] || fail 'SSAID target missing'
actual=$(sha256sum "$TARGET" | cut -d ' ' -f 1) || fail 'hash read failed'
[ "$actual" = "$expected" ] || fail 'SSAID database changed since staging; skipped safely'
# Preserve inode destination directory, SELinux ownership and mode.
tmp="$TARGET.ksuidentity.$$"
cp "$PENDING" "$tmp" || fail 'cannot create destination temp file'
chown 1000:1000 "$tmp" || { rm -f "$tmp"; fail 'cannot set system ownership'; }
chmod 0600 "$tmp" || { rm -f "$tmp"; fail 'cannot set secure permissions'; }
if command -v restorecon >/dev/null 2>&1; then
  restorecon "$tmp" >/dev/null 2>&1 || :
fi
mv -f "$tmp" "$TARGET" || { rm -f "$tmp"; fail 'cannot atomically install SSAID data'; }
if command -v restorecon >/dev/null 2>&1; then restorecon "$TARGET" >/dev/null 2>&1 || :; fi
new_hash=$(sha256sum "$TARGET" | cut -d ' ' -f 1) || fail 'cannot verify installed file'
expected_new=$(sha256sum "$PENDING" | cut -d ' ' -f 1) || fail 'cannot hash pending file'
[ "$new_hash" = "$expected_new" ] || fail 'installed SSAID content mismatch'
printf '%s\n' 'Applied staged SSAID before SettingsProvider startup' > "$RESULT"
rm -f "$PENDING" "$META"
exit 0
