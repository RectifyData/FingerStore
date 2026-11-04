#!/system/bin/sh
# Reassert any properties that the OEM overwrote after post-fs-data.
MODDIR=${0%/*}
[ -f "$MODDIR/config.conf" ] || exit 0
sh "$MODDIR/bin/fpctl.sh" apply >/dev/null 2>&1 || :
exit 0
