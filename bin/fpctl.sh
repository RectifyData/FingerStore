#!/system/bin/sh
# Fingerprint/date editor: no 'eval', no shell-sourced user configuration.
set -u
MODDIR=${0%/*}
MODDIR=${MODDIR%/*}
CONFIG="$MODDIR/config.conf"
ORIGINAL="$MODDIR/original.props"
PARTS='system system_ext product vendor odm bootimage'
PRODUCT_PARTS='system system_ext product vendor odm'
IDENTITY_FIELDS='brand device model name manufacturer'

sayerr() { printf '%s\n' "ERROR: $*" >&2; }
propget() { getprop "$1" 2>/dev/null || :; }
reset_cmd() {
  if [ -x /data/adb/ksu/bin/resetprop ]; then
    printf '%s' /data/adb/ksu/bin/resetprop
  elif command -v resetprop >/dev/null 2>&1; then
    printf '%s' resetprop
  elif [ -x /data/adb/magisk/resetprop ]; then
    printf '%s' /data/adb/magisk/resetprop
  else
    return 1
  fi
}
# Validated key/value only. Avoid triggering Android init on ro.* changes.
putprop() { "$RESETPROP" -n "$1" "$2" >/dev/null 2>&1; }
valid_fp() {
  case "$1" in
    ''|*[!a-zA-Z0-9_./:\-]* ) return 1 ;;
  esac
  [ "${#1}" -le 240 ] && [ "${#1}" -ge 16 ] || return 1
  # Form recommended by Android builds: brand/product/device:release/id/incremental:type/tags
  printf '%s\n' "$1" | grep -Eq '^[[:alnum:]_.-]+/[[:alnum:]_.-]+/[[:alnum:]_.-]+:[[:alnum:]_.-]+/[[:alnum:]_.-]+/[[:alnum:]_.-]+:(user|userdebug|eng)/[[:alnum:]_.-]+$'
}
# Android's /system/bin/sh (mksh) can have 32-bit integer arithmetic.
# The old comparison against 4102444800 overflowed on some devices and
# rejected *valid* UI-supplied epoch values. All numeric tests below fit
# safely within signed 32-bit, including on 32-bit Android shells.
valid_epoch() {
  case "$1" in ''|*[!0-9]*) return 1 ;; esac
  case "${#1}" in
    9)
      # 2000-01-01T00:00Z through the last 9-digit timestamp.
      [ "$1" -ge 946684800 ]
      ;;
    10)
      first=${1%?????????}
      remainder=${1#?}
      case "$first" in
        1|2|3) return 0 ;;
        4) [ "$remainder" -le 102444800 ] ;;
        *) return 1 ;;
      esac
      ;;
    *) return 1 ;;
  esac
}
# Android Build.{BRAND, DEVICE, MODEL, PRODUCT, MANUFACTURER} are read from
# ro.product.*. Keep identity data ASCII, single line and bounded. A blank value
# means "do not override / restore if previously changed".
valid_identity() {
  [ "${#1}" -le 90 ] || return 1
  [ -z "$1" ] && return 0
  [ "$(printf '%s\n' "$1" | wc -l | tr -d ' ')" = 1 ] || return 1
  printf '%s\n' "$1" | LC_ALL=C grep -Eq '^[A-Za-z0-9_][A-Za-z0-9_. +()-]*$'
}
# All fingerprints contain brand/product/device. Model is NOT a fingerprint
# component. Infer Samsung's model only for its recognized build-number format;
# other devices keep the explicitly supplied model (possibly blank).
derive_identity() {
  DERIVED_BRAND=${FP%%/*}
  rest=${FP#*/}
  DERIVED_NAME=${rest%%/*}
  rest=${rest#*/}
  DERIVED_DEVICE=${rest%%:*}
  DERIVED_MANUFACTURER=$DERIVED_BRAND
  DERIVED_MODEL=''
  segment=${FP#*:}
  segment=${segment#*/}
  segment=${segment#*/}
  incremental=${segment%%:*}
  if [ "$DERIVED_BRAND" = samsung ]; then
    candidate=$(printf '%s' "$incremental" | cut -c 1-5)
    suffix=${incremental#"$candidate"}
    if printf '%s\n' "$candidate" | grep -Eq '^[A-Z][0-9]{3}[A-Z]$'; then
      case "$suffix" in
        XX[A-Z0-9]*|OX[A-Z0-9]*|UE[A-Z0-9]*|US[A-Z0-9]*) DERIVED_MODEL="SM-$candidate" ;;
      esac
    fi
  fi
}
valid_patch() {
  [ "$1" = '-' ] && return 0
  printf '%s\n' "$1" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' || return 1
  yr=${1%%-*}; rest=${1#*-}; mo=${rest%%-*}; dy=${rest##*-}
  # Two dates aren't treated as equal until the date parser confirms validity.
  case "$mo" in 01|02|03|04|05|06|07|08|09|10|11|12) ;; *) return 1 ;; esac
  case "$dy" in 0[1-9]|[12][0-9]|3[01]) ;; *) return 1 ;; esac
  parsed=$(TZ=UTC0 date -u -d "${1} 00:00:00" '+%Y-%m-%d' 2>/dev/null) || return 1
  [ "$parsed" = "$1" ]
}
valid_partitions() { [ "$1" = 0 ] || [ "$1" = 1 ]; }
human_date() { TZ=UTC0 LC_ALL=C date -u -d "@$1" '+%a %b %d %H:%M:%S UTC %Y' 2>/dev/null; }
read_config() {
  ENABLED=0 FP='' EPOCH='' PATCH='-' PARTITIONS=0 AUTOFILL=0 BRAND='' DEVICE='' MODEL='' NAME='' MANUFACTURER='' APPLY_MODE=runtime
  [ -f "$CONFIG" ] || return 0
  # Parse only supported named keys, never source/unquote file content.
  while IFS='=' read -r key value; do
    case "$key" in
      enabled) ENABLED=$value ;;
      apply_mode) APPLY_MODE=$value ;;
      fingerprint) FP=$value ;;
      epoch) EPOCH=$value ;;
      patch) PATCH=$value ;;
      partitions) PARTITIONS=$value ;;
      autofill) AUTOFILL=$value ;;
      brand) BRAND=$value ;;
      device) DEVICE=$value ;;
      model) MODEL=$value ;;
      name) NAME=$value ;;
      manufacturer) MANUFACTURER=$value ;;
    esac
  done < "$CONFIG"
  [ "$ENABLED" = 1 ] || ENABLED=0
  valid_partitions "$PARTITIONS" || PARTITIONS=0
  valid_partitions "$AUTOFILL" || AUTOFILL=0
  case "$APPLY_MODE" in runtime|reboot) ;; *) APPLY_MODE=runtime ;; esac
}
write_config() {
  umask 077
  temp="$CONFIG.new.$$"
  { printf 'enabled=%s\n' "$ENABLED"
    printf 'apply_mode=%s\n' "$APPLY_MODE"
    printf 'fingerprint=%s\n' "$FP"
    printf 'epoch=%s\n' "$EPOCH"
    printf 'patch=%s\n' "$PATCH"
    printf 'partitions=%s\n' "$PARTITIONS"
    printf 'autofill=%s\n' "$AUTOFILL"
    printf 'brand=%s\n' "$BRAND"
    printf 'device=%s\n' "$DEVICE"
    printf 'model=%s\n' "$MODEL"
    printf 'name=%s\n' "$NAME"
    printf 'manufacturer=%s\n' "$MANUFACTURER"; } > "$temp" || return 1
  mv -f "$temp" "$CONFIG"
}
# Only snapshot properties we actually modify. Keep originals across edits/reboots.
snapshot() {
  key=$1
  [ -f "$ORIGINAL" ] && grep -q "^${key}=" "$ORIGINAL" && return 0
  oldval=$(propget "$key")
  [ -n "$oldval" ] || return 0
  umask 077
  printf '%s=%s\n' "$key" "$oldval" >> "$ORIGINAL"
}
original_for() {
  key=$1
  [ -f "$ORIGINAL" ] || return 0
  grep -F "${key}=" "$ORIGINAL" | tail -n 1 | cut -d '=' -f 2-
}
# Save original live values before preparing boot-time overrides.
# Snapshotting them only at boot can accidentally save already-overridden values.
snapshot_targets() {
  snapshot ro.build.fingerprint || return 1
  snapshot ro.build.date.utc || return 1
  snapshot ro.build.date || return 1
  [ "$PATCH" = '-' ] || snapshot ro.build.version.security_patch || return 1
  for field in $IDENTITY_FIELDS; do
    snapshot "ro.product.$field" || return 1
    if [ "$PARTITIONS" = 1 ]; then
      for part in $PRODUCT_PARTS; do
        snapshot "ro.product.$part.$field" || return 1
      done
    fi
  done
  if [ "$PARTITIONS" = 1 ]; then
    for part in $PARTS; do
      for suffix in fingerprint date.utc date; do
        snapshot "ro.$part.build.$suffix" || return 1
      done
    done
  fi
}
# Track exact props overwritten. If partition mirroring is turned off, restore those.
# Do not touch absent partition properties. This avoids inventing partitions.
apply_one() {
  key=$1
  target=$2
  old=$(original_for "$key")
  if [ -z "$target" ]; then
    [ -z "$old" ] && return 0
    putprop "$key" "$old" || return 1
    return 0
  fi
  current=$(propget "$key")
  if [ -n "$current" ] || [ -n "$old" ]; then
    # Never modify a property if its original value could not be recorded.
    snapshot "$key" || return 1
    putprop "$key" "$target" || return 1
  fi
}
# Only mirror product identity properties which the ROM actually exposes.
# This follows Android's ro.product.<partition>.<field> naming scheme.
apply_identity_props() {
  idresult=0
  if [ -z "$BRAND$DEVICE$MODEL$NAME$MANUFACTURER" ]; then
    [ -f "$ORIGINAL" ] && grep -q '^ro.product\.' "$ORIGINAL" || return 0
  fi
  for field in $IDENTITY_FIELDS; do
    case "$field" in
      brand) value=$BRAND ;; device) value=$DEVICE ;; model) value=$MODEL ;;
      name) value=$NAME ;; manufacturer) value=$MANUFACTURER ;;
    esac
    apply_one "ro.product.$field" "$value" || idresult=1
    for part in $PRODUCT_PARTS; do
      if [ "$PARTITIONS" = 1 ]; then
        apply_one "ro.product.$part.$field" "$value" || idresult=1
      else
        apply_one "ro.product.$part.$field" '' || idresult=1
      fi
    done
  done
  return "$idresult"
}
valid_config_identity() {
  for value in "$BRAND" "$DEVICE" "$MODEL" "$NAME" "$MANUFACTURER"; do
    valid_identity "$value" || return 1
  done
  valid_partitions "$AUTOFILL"
}
apply_config() {
  read_config
  [ "$ENABLED" = 1 ] || return 0
  valid_fp "$FP" && valid_epoch "$EPOCH" && valid_patch "$PATCH" && valid_partitions "$PARTITIONS" && valid_config_identity || { sayerr 'Stored configuration invalid; no changes applied'; return 2; }
  HUMAN=$(human_date "$EPOCH")
  [ -n "$HUMAN" ] || { sayerr 'Date formatter unavailable'; return 2; }
  RESETPROP=$(reset_cmd) || { sayerr 'KernelSU resetprop was not found'; return 2; }
  result=0
  apply_identity_props || result=1
  apply_one ro.build.fingerprint "$FP" || result=1
  apply_one ro.build.date.utc "$EPOCH" || result=1
  apply_one ro.build.date "$HUMAN" || result=1
  if [ "$PATCH" = '-' ]; then
    apply_one ro.build.version.security_patch '' || result=1
  else
    apply_one ro.build.version.security_patch "$PATCH" || result=1
  fi
  for part in $PARTS; do
    prefix="ro.$part.build"
    if [ "$PARTITIONS" = 1 ]; then
      apply_one "$prefix.fingerprint" "$FP" || result=1
      apply_one "$prefix.date.utc" "$EPOCH" || result=1
      apply_one "$prefix.date" "$HUMAN" || result=1
    else
      apply_one "$prefix.fingerprint" '' || result=1
      apply_one "$prefix.date.utc" '' || result=1
      apply_one "$prefix.date" '' || result=1
    fi
  done
  return "$result"
}
# KernelSU imports system.prop before Zygote, avoiding a blocking early shell script.
# Regenerate only on explicit user changes, not on every boot.
generate_system_prop() {
  read_config
  umask 077
  temp="$MODDIR/system.prop.new.$$"
  : > "$temp" || return 1
  if [ "$ENABLED" = 1 ]; then
    valid_fp "$FP" && valid_epoch "$EPOCH" && valid_patch "$PATCH" && valid_partitions "$PARTITIONS" && valid_config_identity || { rm -f "$temp"; return 2; }
    HUMAN=$(human_date "$EPOCH")
    [ -n "$HUMAN" ] || { rm -f "$temp"; return 2; }
    printf 'ro.build.fingerprint=%s\nro.build.date.utc=%s\nro.build.date=%s\n' "$FP" "$EPOCH" "$HUMAN" >> "$temp"
    [ "$PATCH" = '-' ] || printf 'ro.build.version.security_patch=%s\n' "$PATCH" >> "$temp"
    for field in $IDENTITY_FIELDS; do
      case "$field" in
        brand) value=$BRAND ;; device) value=$DEVICE ;; model) value=$MODEL ;;
        name) value=$NAME ;; manufacturer) value=$MANUFACTURER ;;
      esac
      if [ -n "$value" ]; then
        printf 'ro.product.%s=%s\n' "$field" "$value" >> "$temp"
        if [ "$PARTITIONS" = 1 ]; then
          for part in $PRODUCT_PARTS; do
            key="ro.product.$part.$field"
            current=$(propget "$key")
            saved=$(original_for "$key")
            [ -n "$current" ] || [ -n "$saved" ] || continue
            printf '%s=%s\n' "$key" "$value" >> "$temp"
          done
        fi
      fi
    done
    if [ "$PARTITIONS" = 1 ]; then
      for part in $PARTS; do
        prefix="ro.$part.build"
        for suffix in fingerprint date.utc date; do
          key="$prefix.$suffix"
          existing=$(propget "$key")
          snapshot_value=$(original_for "$key")
          [ -n "$existing" ] || [ -n "$snapshot_value" ] || continue
          case "$suffix" in
            fingerprint) val=$FP ;;
            date.utc) val=$EPOCH ;;
            date) val=$HUMAN ;;
          esac
          printf '%s=%s\n' "$key" "$val" >> "$temp"
        done
      done
    fi
  fi
  mv -f "$temp" "$MODDIR/system.prop"
}
restore_originals() {
  [ -s "$ORIGINAL" ] || return 0
  RESETPROP=$(reset_cmd) || { sayerr 'KernelSU resetprop was not found'; return 2; }
  result=0
  while IFS='=' read -r key val; do
    case "$key" in
      ro.build.fingerprint|ro.build.date|ro.build.date.utc|ro.build.version.security_patch|ro.system.build.fingerprint|ro.system.build.date|ro.system.build.date.utc|ro.system_ext.build.fingerprint|ro.system_ext.build.date|ro.system_ext.build.date.utc|ro.product.build.fingerprint|ro.product.build.date|ro.product.build.date.utc|ro.vendor.build.fingerprint|ro.vendor.build.date|ro.vendor.build.date.utc|ro.odm.build.fingerprint|ro.odm.build.date|ro.odm.build.date.utc|ro.bootimage.build.fingerprint|ro.bootimage.build.date|ro.bootimage.build.date.utc|ro.product.brand|ro.product.device|ro.product.model|ro.product.name|ro.product.manufacturer|ro.product.system.brand|ro.product.system.device|ro.product.system.model|ro.product.system.name|ro.product.system.manufacturer|ro.product.system_ext.brand|ro.product.system_ext.device|ro.product.system_ext.model|ro.product.system_ext.name|ro.product.system_ext.manufacturer|ro.product.product.brand|ro.product.product.device|ro.product.product.model|ro.product.product.name|ro.product.product.manufacturer|ro.product.vendor.brand|ro.product.vendor.device|ro.product.vendor.model|ro.product.vendor.name|ro.product.vendor.manufacturer|ro.product.odm.brand|ro.product.odm.device|ro.product.odm.model|ro.product.odm.name|ro.product.odm.manufacturer)
        if [ -n "$val" ]; then putprop "$key" "$val" || result=1; fi ;;
    esac
  done < "$ORIGINAL"
  return "$result"
}
case "${1:-}" in
  set)
    case "$#" in 5|11|12) ;; *) sayerr 'Usage: set <fingerprint> <epoch> <patch-or-dash> <mirror-0-or-1> [<autofill-0-or-1> <brand> <device> <model> <product> <manufacturer>]'; exit 2 ;; esac
    valid_fp "$2" || { sayerr 'Fingerprint format invalid'; exit 2; }
    valid_epoch "$3" || { sayerr 'Unix timestamp must represent a UTC date between 2000-01-01 and 2100-01-01'; exit 2; }
    valid_patch "$4" || { sayerr 'Security patch must be a real YYYY-MM-DD date or -'; exit 2; }
    valid_partitions "$5" || { sayerr 'Partition mirror must be 0 or 1'; exit 2; }
    [ -n "$(human_date "$3")" ] || { sayerr 'Cannot format the UTC date on this Android build'; exit 2; }
    # Legacy five-argument calls still work and retain the v1.2 identity behavior.
    input_autofill=0 input_brand='' input_device='' input_model='' input_name='' input_manufacturer=''
    input_mode=runtime
    if [ "$#" = 11 ] || [ "$#" = 12 ]; then
      input_autofill=$6 input_brand=$7 input_device=$8 input_model=$9
      input_name=${10} input_manufacturer=${11}
    fi
    [ "$#" = 12 ] && input_mode=${12}
    case "$input_mode" in runtime|reboot) ;; *) sayerr 'Apply mode must be runtime or reboot'; exit 2 ;; esac
    valid_partitions "$input_autofill" || { sayerr 'Autofill must be 0 or 1'; exit 2; }
    if [ "$input_autofill" = 1 ]; then
      FP=$2
      derive_identity
      input_brand=$DERIVED_BRAND input_device=$DERIVED_DEVICE
      input_name=$DERIVED_NAME input_manufacturer=$DERIVED_MANUFACTURER
      [ -z "$DERIVED_MODEL" ] || input_model=$DERIVED_MODEL
    fi
    for value in "$input_brand" "$input_device" "$input_model" "$input_name" "$input_manufacturer"; do
      valid_identity "$value" || { sayerr 'Product identity value must be up to 90 safe ASCII characters, single-line'; exit 2; }
    done
    if [ "$input_mode" = runtime ]; then
      RESETPROP=$(reset_cmd) || { sayerr 'KernelSU resetprop was not found; no settings changed'; exit 2; }
    fi
    # Back up both persistent files before changing either. A transient
    # failure must not erase the last working user-selected configuration.
    umask 077
    BACKUP_DIR="$MODDIR/.fpctl-txn.$$"
    mkdir "$BACKUP_DIR" || { sayerr 'Could not start settings transaction'; exit 3; }
    trap 'rm -rf "$BACKUP_DIR"' 0
    if [ -f "$CONFIG" ]; then
      cp "$CONFIG" "$BACKUP_DIR/config.conf" || { sayerr 'Could not back up saved selection'; exit 3; }
    fi
    if [ -f "$MODDIR/system.prop" ]; then
      cp "$MODDIR/system.prop" "$BACKUP_DIR/system.prop" || { sayerr 'Could not back up startup properties'; exit 3; }
    fi
    if [ -f "$ORIGINAL" ]; then
      cp "$ORIGINAL" "$BACKUP_DIR/original.props" || { sayerr 'Could not back up original properties'; exit 3; }
    fi
    FP=$2 EPOCH=$3 PATCH=$4 PARTITIONS=$5 ENABLED=1 APPLY_MODE=$input_mode
    AUTOFILL=$input_autofill BRAND=$input_brand DEVICE=$input_device MODEL=$input_model NAME=$input_name MANUFACTURER=$input_manufacturer
    if [ "$APPLY_MODE" = reboot ]; then
      # Atomic saved selection: no resetprop calls occur in this branch.
      if snapshot_targets && write_config && generate_system_prop; then
        printf '%s\n' 'Saved for next reboot. Running properties unchanged.'
        exit 0
      fi
      if [ -f "$BACKUP_DIR/config.conf" ]; then cp "$BACKUP_DIR/config.conf" "$CONFIG"; else rm -f "$CONFIG"; fi
      if [ -f "$BACKUP_DIR/system.prop" ]; then cp "$BACKUP_DIR/system.prop" "$MODDIR/system.prop"; else rm -f "$MODDIR/system.prop"; fi
      if [ -f "$BACKUP_DIR/original.props" ]; then cp "$BACKUP_DIR/original.props" "$ORIGINAL"; else rm -f "$ORIGINAL"; fi
      sayerr 'Reboot-stage failed; previous selection preserved.'
      exit 4
    fi
    if write_config && generate_system_prop && apply_config; then
      printf '%s\n' 'Applied and saved. The choice persists across reboots until changed or restored. Reboot recommended.'
      exit 0
    fi
    # Restore the old saved selection, early-boot overrides AND live values.
    if [ -f "$BACKUP_DIR/config.conf" ]; then
      cp "$BACKUP_DIR/config.conf" "$CONFIG" || sayerr 'CRITICAL: could not restore saved configuration'
    else
      rm -f "$CONFIG"
    fi
    if [ -f "$BACKUP_DIR/system.prop" ]; then
      cp "$BACKUP_DIR/system.prop" "$MODDIR/system.prop" || sayerr 'CRITICAL: could not restore startup properties'
    else
      rm -f "$MODDIR/system.prop"
    fi
    restore_originals || sayerr 'WARNING: partial live rollback; a reboot may be necessary'
    apply_config || sayerr 'WARNING: previous live override could not be reapplied'
    sayerr 'Apply failed; previous saved selection retained. Reboot if live properties look inconsistent.'
    exit 4
    ;;
  apply)
    apply_config || exit $?
    ;;
  generate)
    generate_system_prop || exit $?
    ;;
  disable)
    read_config
    ENABLED=0
    write_config || exit 3
    generate_system_prop || { sayerr 'Overrides disabled but system.prop could not be cleared'; exit 4; }
    restore_originals || { sayerr 'Disabled at boot; live rollback failed'; exit 4; }
    printf '%s\n' 'Overrides disabled. Original properties restored where available. Reboot recommended.'
    ;;
  status)
    read_config
    printf 'enabled=%s\n' "$ENABLED"
    printf 'apply_mode=%s\n' "$APPLY_MODE"
    printf 'fingerprint=%s\n' "$FP"
    printf 'epoch=%s\n' "$EPOCH"
    printf 'patch=%s\n' "$PATCH"
    printf 'partitions=%s\n' "$PARTITIONS"
    printf 'autofill=%s\n' "$AUTOFILL"
    printf 'brand=%s\n' "$BRAND"
    printf 'device=%s\n' "$DEVICE"
    printf 'model=%s\n' "$MODEL"
    printf 'name=%s\n' "$NAME"
    printf 'manufacturer=%s\n' "$MANUFACTURER"
    for field in $IDENTITY_FIELDS; do
      printf 'current_%s=%s\n' "$field" "$(propget "ro.product.$field")"
    done
    printf 'current_fingerprint=%s\n' "$(propget ro.build.fingerprint)"
    printf 'current_epoch=%s\n' "$(propget ro.build.date.utc)"
    printf 'current_human=%s\n' "$(propget ro.build.date)"
    printf 'current_patch=%s\n' "$(propget ro.build.version.security_patch)"
    if [ "$ENABLED" = 1 ]; then echo 'persistence=until_changed'; else echo 'persistence=disabled'; fi
    if reset_cmd >/dev/null 2>&1; then echo 'resetprop=available'; else echo 'resetprop=missing'; fi
    ;;
  reboot)
    # Invoked only after an explicit confirmation in the WebUI.
    if command -v svc >/dev/null 2>&1 && svc power reboot >/dev/null 2>&1; then exit 0; fi
    if command -v reboot >/dev/null 2>&1 && reboot >/dev/null 2>&1; then exit 0; fi
    sayerr 'Android rejected the reboot command'; exit 5
    ;;
  *)
    printf '%s\n' 'Usage: fpctl.sh {status|reboot|set <fingerprint> <epoch> <YYYY-MM-DD|-> <0|1>|apply|disable}' >&2
    exit 2
    ;;
esac
