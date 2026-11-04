#!/system/bin/sh
# Installed by KernelSU Manager, not by recovery.
ui_print '- Installing Build Fingerprint & Date Editor'
ui_print '- No properties will be changed until you choose Apply.'
# Preserve settings on upgrades; don't import someone else's system properties.
OLD=/data/adb/modules/build_fingerprint_date
if [ -f "$OLD/config.conf" ]; then
  cp -f "$OLD/config.conf" "$MODPATH/config.conf" || abort '! Could not preserve configuration'
fi
if [ -f "$OLD/original.props" ]; then
  cp -f "$OLD/original.props" "$MODPATH/original.props" || abort '! Could not preserve rollback snapshot'
fi
if [ -f "$OLD/system.prop" ]; then
  cp -f "$OLD/system.prop" "$MODPATH/system.prop" || abort '! Could not preserve early-boot properties'
fi
# Preserve staged per-app SSAID and its original backup during updates.
if [ -d "$OLD/ssaid-data" ]; then
  cp -R "$OLD/ssaid-data" "$MODPATH/ssaid-data" || abort '! Could not preserve SSAID data'
  chmod 0700 "$MODPATH/ssaid-data"
  find "$MODPATH/ssaid-data" -type f -exec chmod 0600 {} \;
fi
# Preserve local read-only diagnostic baseline across module upgrades.
if [ -d "$OLD/integrity-data" ]; then
  cp -R "$OLD/integrity-data" "$MODPATH/integrity-data" || abort '! Failed to preserve integrity diagnostic baseline'
  chmod 0700 "$MODPATH/integrity-data" || abort '! Failed to secure integrity baseline'
  find "$MODPATH/integrity-data" -type f -exec chmod 0600 {} \;
fi
# Preserve a locally selected keybox and the first provider rollback snapshot.
if [ -d "$OLD/keybox-vault" ]; then
  cp -R "$OLD/keybox-vault" "$MODPATH/keybox-vault" || abort '! Failed to preserve private keybox vault'
  chmod 0700 "$MODPATH/keybox-vault" "$MODPATH/keybox-vault/profiles" 2>/dev/null || abort '! Failed to protect private vault'
  find "$MODPATH/keybox-vault" -type f -exec chmod 0600 {} \;
fi
set_perm "$MODPATH/bin/integrityctl.sh" 0 0 0755
set_perm "$MODPATH/bin/keyboxctl.sh" 0 0 0755
set_perm "$MODPATH/bin/fpctl.sh" 0 0 0755
set_perm "$MODPATH/bin/ssaidctl.sh" 0 0 0755
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
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
ui_print '- Open the module WebUI to configure your fingerprint and date.'
ui_print '- Your selection remains active across restarts and updates until you edit or restore it.'
ui_print '- SSAID changes are staged safely and require a reboot to apply.'
ui_print '- Optional keybox vault and software-provider bridge: no hardware attestation is forged.'
