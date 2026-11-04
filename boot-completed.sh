#!/system/bin/sh
# Some OEM services rewrite ro.* build properties late in startup.
# Reassert the saved user-selected values once when Android has booted.
# This is not a daemon and never changes the stored selection.
MODDIR=${0%/*}
[ -f "$MODDIR/config.conf" ] || exit 0
sh "$MODDIR/bin/fpctl.sh" apply >/dev/null 2>&1 || :
exit 0
