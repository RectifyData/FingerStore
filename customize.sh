#!/system/bin/sh
# Compatible Magisk / KernelSU module installer. Not a recovery ZIP.
ui_print '- Installing FingerStore for Magisk / KernelSU'
if [ -n "${MAGISK_VER:-}" ]; then ui_print "- Magisk detected: $MAGISK_VER"; fi
if [ -n "${KSU:-}" ]; then ui_print '- KernelSU detected'; fi
ui_print '- No properties will be changed until you choose Apply.'
# Preserve settings on upgrades; don't import someone else's system properties.
OLD=/data/adb/modules/build_fingerprint_date
if [ -f "$OLD/config.conf" ]; then
  cp -f "$OLD/config.conf" "$MODPATH/config.conf" || abort '! Could not preserve configuration'
fi
if [ -f "$OLD/original.props" ]; then
  cp -f "$OLD/original.props" "$MODPATH/original.props" || abort '! Could not preserve rollback snapshot'
fi
if [ -f "$OLD/zygisk.conf" ]; then
  cp -f "$OLD/zygisk.conf" "$MODPATH/zygisk.conf" || abort '! Cannot migrate optional Zygisk preference'
fi
if [ ! -f "$MODPATH/zygisk.conf" ]; then
  printf 'enabled=0\n' > "$MODPATH/zygisk.conf" || abort '! Cannot initialize optional Zygisk preference'
fi
chmod 0600 "$MODPATH/zygisk.conf" || abort '! Cannot protect Zygisk preference'
if [ -f "$OLD/system.prop" ]; then
  cp -f "$OLD/system.prop" "$MODPATH/system.prop" || abort '! Could not preserve early-boot properties'
fi
# Preserve local read-only diagnostic baseline across module upgrades.
if [ -d "$OLD/integrity-data" ]; then
  cp -R "$OLD/integrity-data" "$MODPATH/integrity-data" || abort '! Failed to preserve integrity diagnostic baseline'
  chmod 0700 "$MODPATH/integrity-data" || abort '! Failed to secure integrity baseline'
  find "$MODPATH/integrity-data" -type f -exec chmod 0600 {} \;
fi
set_perm "$MODPATH/bin/integrityctl.sh" 0 0 0755
set_perm "$MODPATH/bin/fpctl.sh" 0 0 0755
set_perm "$MODPATH/action.sh" 0 0 0755
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm "$MODPATH/boot-completed.sh" 0 0 0755
[ ! -f "$MODPATH/config.conf" ] || chmod 0600 "$MODPATH/config.conf"
[ ! -f "$MODPATH/original.props" ] || chmod 0600 "$MODPATH/original.props"
# If this is an upgrade with saved settings, regenerate early-boot properties
# from the authoritative saved configuration (not any stale system.prop).
if [ -f "$MODPATH/config.conf" ]; then
  sh "$MODPATH/bin/fpctl.sh" generate || abort '! Failed to migrate saved build properties'
fi
ui_print '- Use the WebUI in compatible managers or the Magisk root CLI.'
ui_print '- Optional runtime-only Zygisk injection is disabled by default.'
ui_print '- CLI: sh /data/adb/modules/build_fingerprint_date/bin/fpctl.sh status'
ui_print '- Your selection remains active across restarts and updates until you edit or restore it.'
ui_print '- Live application is unstable; use after-reboot mode where possible.'
ui_print '- Previous SSAID/third-party provider changes are NOT reverted by upgrading.'
