#!/system/bin/sh
# Local, private keybox profile vault and opt-in software-provider bridge.
# This does NOT create hardware-backed attestation or modify vendor KeyMint.
set -u
MODDIR=${0%/*}; MODDIR=${MODDIR%/*}
VAULT=${KEYBOX_TEST_VAULT:-$MODDIR/keybox-vault}
PROVIDER_ROOT=${KEYBOX_TEST_PROVIDER:-/data/misc/keystore/omk}
PROVIDER_MOD=${KEYBOX_TEST_PROVIDER_MODULE:-/data/adb/modules/oh_my_keymint}
ACTIVE="$VAULT/active.xml"
SELECTED="$VAULT/selected.txt"
SAVED="$VAULT/provider-original.xml"
PROVIDER="$PROVIDER_ROOT/keybox.xml"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 2; }
valid_alias(){ printf '%s\n' "$1" | LC_ALL=C grep -Eq '^[A-Za-z0-9_][A-Za-z0-9_-]{0,39}$'; }
store(){ umask 077; mkdir -p "$VAULT/profiles" || fail 'Cannot create private profile vault'; chmod 0700 "$VAULT" "$VAULT/profiles" || fail 'Cannot secure keybox vault'; }
# Only untrusted structure checks here; the software provider is responsible for
# complete cryptographic chain and private-key correspondence checks.
validate(){
  src=$1
  [ -f "$src" ] && [ ! -L "$src" ] || fail 'Regular non-symlink XML file required'
  bytes=$(wc -c < "$src") || fail 'Cannot read keybox'
  [ "$bytes" -ge 128 ] && [ "$bytes" -le 524288 ] || fail 'Keybox size must be 128B–512KiB'
  LC_ALL=C grep -q '<AndroidAttestation' "$src" || fail 'Missing AndroidAttestation XML root'
  LC_ALL=C grep -q '</AndroidAttestation>' "$src" || fail 'Missing AndroidAttestation closing tag'
  LC_ALL=C grep -q '<Key\([[:space:]>]\)' "$src" || fail 'Missing Key element'
  LC_ALL=C grep -q '<PrivateKey\([[:space:]>]\)' "$src" || fail 'Missing PrivateKey'
  LC_ALL=C grep -q '<Certificate\([[:space:]>]\)' "$src" || fail 'Missing Certificate'
  LC_ALL=C grep -Eq -- '-----BEGIN ((RSA|EC) )?PRIVATE KEY-----' "$src" || fail 'Missing PEM private key'
  LC_ALL=C grep -q -- '-----BEGIN CERTIFICATE-----' "$src" || fail 'Missing PEM certificate'
  if LC_ALL=C grep -Eqi '<!DOCTYPE|<!ENTITY|<script' "$src"; then fail 'Active XML/DTD markup forbidden'; fi
}
provider_ok(){
  [ -d "$PROVIDER_MOD" ] && [ ! -e "$PROVIDER_MOD/disable" ] && [ -d "$PROVIDER_ROOT" ] && [ -f "$PROVIDER" ] && [ ! -L "$PROVIDER" ];
}
status(){
  [ -s "$ACTIVE" ] && echo 'keybox_selected=yes' || echo 'keybox_selected=no'
  [ -f "$SELECTED" ] && printf 'keybox_profile=%s\n' "$(head -n 1 "$SELECTED")"
  if provider_ok; then echo 'software_provider=omk_ready'; else echo 'software_provider=unavailable'; fi
  [ -f "$SAVED" ] && echo 'provider_original_backup=yes' || echo 'provider_original_backup=no'
  if provider_ok && [ -s "$ACTIVE" ] && cmp -s "$ACTIVE" "$PROVIDER"; then echo 'software_provider_matches_selection=yes'; else echo 'software_provider_matches_selection=no'; fi
  echo 'attestation_security=software_or_device_defined'
  echo 'provider_runtime_verified=no'
  echo 'google_verdict_verified=no'
  echo 'hardware_attestation_verified=no'
}
# Only root-readable files get stored. WebUI file picker NEVER passes key material
# via a command-line argument or exec log; import via a privileged path instead.
case "${1:-}" in
  status) status ;;
  list)
    store
    for file in "$VAULT"/profiles/*.xml; do [ -f "$file" ] || continue; name=${file##*/}; printf '%s\n' "${name%.xml}"; done
    ;;
  inspect)
    [ "$#" -eq 2 ] || fail 'Usage: inspect <absolute-path>'
    case "$2" in /*) ;; *) fail 'Expected an absolute path' ;; esac
    validate "$2"
    printf '%s\n' 'structure=plausible' 'cryptographic_chain=not_verified' 'private_key_match=not_verified'
    ;;
  import)
    [ "$#" -eq 3 ] || fail 'Usage: import <profile-alias> <absolute-XML-path>'
    valid_alias "$2" || fail 'Profile names: letters, numbers, hyphen, underscore (max 40)'
    case "$3" in /*) ;; *) fail 'Use an absolute source path' ;; esac
    store
    validate "$3"
    [ ! -e "$VAULT/profiles/$2.xml" ] || fail 'Profile already exists; delete it explicitly first'
    tmp="$VAULT/profiles/.import.$$"
    trap 'rm -f "$tmp"' 0 1 2 3 15
    cp "$3" "$tmp" || fail 'Cannot copy keybox'
    chmod 0600 "$tmp" || fail 'Cannot secure imported keybox'
    validate "$tmp"
    mv -f "$tmp" "$VAULT/profiles/$2.xml" || fail 'Cannot save profile'
    printf '%s\n' "imported=$2" 'note=Private material stored locally, root-only; no provider modified'
    ;;
  select)
    [ "$#" -eq 2 ] && valid_alias "$2" || fail 'Usage: select <profile-alias>'
    store
    file="$VAULT/profiles/$2.xml"
    validate "$file"
    tmp="$VAULT/.selected.$$"
    trap 'rm -f "$tmp"' 0 1 2 3 15
    cp "$file" "$tmp" || fail 'Cannot stage selected keybox'
    chmod 0600 "$tmp" || fail 'Cannot secure selected keybox'
    mv -f "$tmp" "$ACTIVE" || fail 'Cannot activate local selection'
    sel_tmp="$VAULT/.selected-name.$$"; printf '%s\n' "$2" > "$sel_tmp"; chmod 0600 "$sel_tmp"; mv -f "$sel_tmp" "$SELECTED"
    printf '%s\n' "selected=$2" 'notice=Selection is local. Provider unchanged until Deploy is explicitly chosen.' 
    ;;
  remove)
    [ "$#" -eq 2 ] && valid_alias "$2" || fail 'Usage: remove <profile-alias>'
    store
    file="$VAULT/profiles/$2.xml"
    [ -f "$file" ] && [ ! -L "$file" ] || fail 'Profile not found'
    if [ -s "$ACTIVE" ] && cmp -s "$file" "$ACTIVE"; then fail 'Cannot remove the currently selected profile'; fi
    rm -f "$file" || fail 'Cannot remove profile'
    echo 'removed=yes'
    ;;
  deploy-omk)
    [ "$#" -eq 1 ] || fail 'Usage: deploy-omk'
    store
    validate "$ACTIVE"
    provider_ok || fail 'Oh My Keymint provider not installed/enabled or canonical keybox unavailable. No changes made.'
    [ ! -L "$PROVIDER_ROOT" ] || fail 'Provider directory is a symbolic link'
    # Save original only once, never silently overwrite the rollback point.
    if [ ! -f "$SAVED" ]; then
      orig="$VAULT/.orig.$$"; trap 'rm -f "$orig"' 0 1 2 3 15
      cp "$PROVIDER" "$orig" || fail 'Could not back up provider keybox'
      chmod 0600 "$orig" || fail 'Could not protect original'
      mv "$orig" "$SAVED" || fail 'Could not finalize original backup'
    fi
    # Keep the original provider file's owner/group/mode. Restore SELinux label
    # before replacing. A failure leaves the original provider file unchanged.
    owner=$(stat -c %u:%g "$PROVIDER" 2>/dev/null) || fail 'Cannot read provider ownership'
    mode=$(stat -c %a "$PROVIDER" 2>/dev/null) || fail 'Cannot read provider mode'
    case "$owner" in *[!0-9:]*|'') fail 'Unrecognized provider owner' ;; esac
    case "$mode" in *[!0-7]*|'') fail 'Unrecognized provider permissions' ;; esac
    tmp="$PROVIDER_ROOT/.keybox.buildidentity.$$"
    trap 'rm -f "$tmp"' 0 1 2 3 15
    cp "$ACTIVE" "$tmp" || fail 'Cannot stage provider file'
    chown "$owner" "$tmp" || fail 'Cannot preserve provider owner'
    chmod "$mode" "$tmp" || fail 'Cannot preserve provider permissions'
    if command -v restorecon >/dev/null 2>&1; then restorecon "$tmp" >/dev/null 2>&1 || fail 'Cannot set candidate SELinux label'; fi
    # If SELinux is enforcing, require reliable context handling.
    if command -v getenforce >/dev/null 2>&1 && [ "$(getenforce 2>/dev/null)" = Enforcing ]; then
      command -v chcon >/dev/null 2>&1 || fail 'SELinux enforcing: chcon required to preserve exact label'
      context=$(ls -Zd "$PROVIDER" 2>/dev/null | awk '{print $1}')
      case "$context" in *:*) chcon "$context" "$tmp" || fail 'Cannot apply provider SELinux context' ;; *) fail 'Cannot read provider SELinux context' ;; esac
    fi
    mv -f "$tmp" "$PROVIDER" || fail 'Provider keybox replacement failed'
    printf '%s\n' 'deployed=yes' 'backend=oh_my_keymint' 'note=Provider file replaced only; reboot before evaluating attestation. Active provider/trust is NOT verified.'
    ;;
  restore-omk)
    [ "$#" -eq 1 ] || fail 'Usage: restore-omk'
    [ -f "$SAVED" ] || fail 'No original provider keybox backup available'
    validate "$SAVED"
    provider_ok || fail 'Provider not available; no changes made'
    # Copy the original back with current file's security metadata.
    owner=$(stat -c %u:%g "$PROVIDER" 2>/dev/null) || fail 'Cannot read provider owner'
    mode=$(stat -c %a "$PROVIDER" 2>/dev/null) || fail 'Cannot read provider permissions'
    tmp="$PROVIDER_ROOT/.keybox.restore.$$"
    trap 'rm -f "$tmp"' 0 1 2 3 15
    cp "$SAVED" "$tmp" || fail 'Cannot stage restoration'
    chown "$owner" "$tmp" && chmod "$mode" "$tmp" || fail 'Cannot preserve provider permissions'
    if command -v restorecon >/dev/null 2>&1; then restorecon "$tmp" >/dev/null 2>&1 || fail 'Cannot restore provider SELinux context'; fi
    if command -v getenforce >/dev/null 2>&1 && [ "$(getenforce 2>/dev/null)" = Enforcing ]; then
      command -v chcon >/dev/null 2>&1 || fail 'SELinux enforcing: chcon required'
      context=$(ls -Zd "$PROVIDER" 2>/dev/null | awk '{print $1}')
      case "$context" in *:*) chcon "$context" "$tmp" || fail 'Cannot apply provider SELinux context' ;; *) fail 'Cannot read provider SELinux context' ;; esac
    fi
    mv -f "$tmp" "$PROVIDER" || fail 'Cannot restore provider keybox'
    echo 'restored_provider_original=yes'
    echo 'provider_runtime_verified=no'
    echo 'reboot_recommended=yes'
    ;;
  *) fail 'Usage: {status|list|inspect <file>|import <alias> <file>|select <alias>|remove <alias>|deploy-omk|restore-omk}' ;;
esac
