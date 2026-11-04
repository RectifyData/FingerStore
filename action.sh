#!/system/bin/sh
MODDIR=${0%/*}
printf '%s\n' 'Build Fingerprint & Date Editor' 'Open WebUI to edit values. Current settings:'
sh "$MODDIR/bin/fpctl.sh" status
