#!/system/bin/sh
MODDIR=${0%/*}
printf '%s\n' 'FingerStore for Magisk / KernelSU' 'Current build identity:'
sh "$MODDIR/bin/fpctl.sh" status
printf '%s\n' '' 'Run in a root shell:' \
  "sh $MODDIR/bin/fpctl.sh zygisk enable" \
  "sh $MODDIR/bin/fpctl.sh zygisk disable" \
  "sh $MODDIR/bin/fpctl.sh zygisk status" \
  "sh $MODDIR/bin/fpctl.sh disable"
printf '%s\n' 'Zygisk is optional; only affects the Java Build.FINGERPRINT in newly launched apps in runtime mode.'
