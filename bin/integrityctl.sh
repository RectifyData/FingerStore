#!/system/bin/sh
# Read-only local attestation/environment stability diagnostics.
# NEVER reads, prints, copies, or fingerprints private-key/certificate content.
set -u
MODDIR=${0%/*}; MODDIR=${MODDIR%/*}
DATA="$MODDIR/integrity-data"
BASELINE="$DATA/passing-baseline.txt"
CONFIG="$MODDIR/config.conf"
err() { printf 'ERROR: %s\n' "$1" >&2; exit 2; }
getp() { getprop "$1" 2>/dev/null | head -n 1 || :; }
configval() {
  [ -f "$CONFIG" ] || return 0
  sed -n "s/^$1=//p" "$CONFIG" | head -n 1
}
# Fixed allowlist; excludes all Android IDs, certificates, PEM, private keys,
# accounts, user identifiers, and SSAID database content.
snapshot() {
  for key in \
    ro.build.fingerprint ro.build.date.utc ro.build.version.release \
    ro.build.version.security_patch ro.vendor.build.version.security_patch \
    ro.system.build.version.security_patch ro.product.brand ro.product.device \
    ro.product.model ro.product.name ro.product.manufacturer \
    ro.vendor.build.fingerprint ro.system.build.fingerprint \
    ro.boot.verifiedbootstate ro.boot.vbmeta.device_state ro.boot.flash.locked
  do
    printf '%s=%s\n' "$key" "$(getp "$key")"
  done
  enabled=$(configval enabled)
  printf 'module_enabled=%s\n' "${enabled:-0}"
  if [ "$enabled" = 1 ]; then
    saved=$(configval fingerprint)
    actual=$(getp ro.build.fingerprint)
    if [ -n "$saved" ] && [ "$saved" = "$actual" ]; then
      echo 'saved_fingerprint_matches_live=yes'
    else
      echo 'saved_fingerprint_matches_live=no'
    fi
    matching=yes
    configured=no
    for field in brand device model name manufacturer; do
      saved=$(configval "$field")
      if [ -n "$saved" ]; then
        configured=yes
        actual=$(getp "ro.product.$field")
        [ "$saved" = "$actual" ] || matching=no
      fi
    done
    if [ "$configured" = no ]; then
      echo 'saved_identity_matches_live=not_configured'
    else
      echo "saved_identity_matches_live=$matching"
    fi
  else
    echo 'saved_fingerprint_matches_live=not_enabled'
    echo 'saved_identity_matches_live=not_enabled'
  fi
  if [ -f "$MODDIR/bin/keyboxctl.sh" ]; then
    state=$(sh "$MODDIR/bin/keyboxctl.sh" status 2>/dev/null) || state=''
    for key in keybox_selected software_provider software_provider_matches_selection hardware_attestation_verified; do
      value=$(printf '%s\n' "$state" | sed -n "s/^$key=//p" | head -n 1)
      printf '%s=%s\n' "$key" "${value:-unknown}"
    done
  else
    echo 'keybox_selected=unavailable'
    echo 'software_provider=unavailable'
    echo 'software_provider_matches_selection=unknown'
    echo 'hardware_attestation_verified=no'
  fi
}
case "${1:-}" in
  report)
    snapshot
    if [ -s "$BASELINE" ]; then echo 'baseline_present=yes'; else echo 'baseline_present=no'; fi
    echo 'play_integrity_verdict=not_accessible_from_module'
    echo 'provider_runtime_attestation=not_verified'
    echo 'security_patch_property_is_not_attested_patch=yes'
    ;;
  capture)
    [ "$#" -eq 1 ] || err 'Usage: capture'
    umask 077
    mkdir -p "$DATA" || err 'Cannot create diagnostics folder'
    chmod 0700 "$DATA" || err 'Cannot secure diagnostics folder'
    candidate="$DATA/.baseline.$$"
    trap 'rm -f "$candidate"' 0 1 2 3 15
    snapshot > "$candidate" || err 'Cannot capture diagnostic baseline'
    chmod 0600 "$candidate" || err 'Cannot protect diagnostic baseline'
    mv -f "$candidate" "$BASELINE" || err 'Cannot save diagnostic baseline'
    echo 'baseline_saved=yes'
    echo 'note=Capture while Play Integrity labels are passing. The API verdict is NOT captured.'
    ;;
  compare)
    [ "$#" -eq 1 ] || err 'Usage: compare'
    [ -s "$BASELINE" ] || err 'No baseline. Capture one while your labels are passing.'
    current=$(snapshot) || err 'Cannot read current device state'
    total=0
    # Comparison is *only* of predefined diagnostic fields, not key material.
    while IFS='=' read -r key old; do
      [ -n "$key" ] || continue
      new=$(printf '%s\n' "$current" | awk -F= -v k="$key" '$1 == k { sub(/^[^=]*=/,"",$0); print; exit }')
      if [ "$old" != "$new" ]; then
        total=$((total+1))
        printf 'changed_%s=YES\n' "$key"
        printf 'previous_%s=%s\n' "$key" "$old"
        printf 'current_%s=%s\n' "$key" "$new"
      fi
    done < "$BASELINE"
    printf 'changed_field_count=%s\n' "$total"
    if [ "$total" -eq 0 ]; then
      echo 'diagnosis=No local property/provider-file drift detected; this does not prove an accepted keybox or stable Google verdict.'
    else
      echo 'diagnosis=Local state changed. Compare fields above and investigate competing modules, ROM updates, and provider reload.'
    fi
    ;;
  clear)
    [ "$#" -eq 1 ] || err 'Usage: clear'
    rm -f "$BASELINE" || err 'Could not clear local baseline'
    echo 'baseline_cleared=yes'
    ;;
  *) err 'Usage: integrityctl.sh {report|capture|compare|clear}' ;;
esac
