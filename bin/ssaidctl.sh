#!/system/bin/sh
# Scoped Android 8+ ANDROID_ID (SSAID) editor for the primary user.
# Changes are staged and applied by post-fs-data before SettingsProvider starts.
# Deliberately refuses to modify a running SettingsProvider's live database.
set -u
MODDIR=${0%/*}; MODDIR=${MODDIR%/*}
ROOT=${SSAID_TEST_ROOT:-/data/system/users/0}
TARGET="$ROOT/settings_ssaid.xml"
STORAGE="$MODDIR/ssaid-data"
PENDING="$STORAGE/pending.bin"
META="$STORAGE/pending.meta"
PROFILE="$STORAGE/profile.conf"
BACKUP="$STORAGE/original.bin"
SEED="$STORAGE/seed.hex"
ERROR="$STORAGE/last-result.txt"
err(){ printf 'ERROR: %s\n' "$*" >&2; return 1; }
valid_hex(){ printf '%s\n' "$1" | LC_ALL=C grep -Eq '^[0-9a-fA-F]{16}$'; }
valid_pkg(){ printf '%s\n' "$1" | LC_ALL=C grep -Eq '^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$' && [ "${#1}" -le 180 ]; }
read_profile(){ PKG='' MODE='manual' MANUAL=''; [ -f "$PROFILE" ] || return 0; while IFS='=' read -r k v; do case "$k" in package) PKG=$v ;; mode) MODE=$v ;; manual) MANUAL=$v ;; esac; done < "$PROFILE"; }
safe_store(){ umask 077; mkdir -p "$STORAGE" || return 1; chmod 0700 "$STORAGE" || return 1; }
sha(){ command -v sha256sum >/dev/null 2>&1 || { err 'sha256sum not found'; return 1; }; sha256sum "$1" | cut -d ' ' -f 1; }
get_uid(){
  valid_pkg "$1" || { err 'Invalid package name'; return 1; }
  command -v pm >/dev/null 2>&1 || { err 'Package manager not available'; return 1; }
  pm list packages -U --user 0 2>/dev/null | awk -v p="$1" '
    $1 == "package:"p { for(i=2;i<=NF;i++) if($i ~ /^uid:[0-9]+$/) { split($i,a,":");print a[2];exit } }
    $1 == "package:"p"" { for(i=2;i<=NF;i++) if($i ~ /^uid:[0-9]+$/) { split($i,a,":");print a[2];exit } }
  '
}
# pm output is usually `package:com.example uid:10123`, not separate tokens.
resolve_uid(){
  valid_pkg "$1" || { err 'Invalid package name'; return 1; }
  UID_FOUND=$(pm list packages -U --user 0 2>/dev/null | awk -v p="package:$1" '$1==p {for(i=2;i<=NF;i++) if($i~/^uid:[0-9]+$/){sub(/^uid:/,"",$i);print $i;exit}}')
  case "$UID_FOUND" in ''|*[!0-9]*) err 'Package not found for owner user, or pm did not report its UID'; return 1 ;; esac
  [ "$UID_FOUND" -ge 10000 ] || { err 'System UIDs cannot be modified'; return 1; }
}
# Avoid binary-XML corruption. XML conversion takes place while Android is running;
# only an already-validated replacement file is copied by the early boot script.
kind(){ sig=$(dd if="$1" bs=4 count=1 2>/dev/null | od -An -tx1 | tr -d ' \n'); [ "$sig" = '41425800' ] && echo abx || echo xml; }
decode(){
  case "$(kind "$1")" in
    abx) command -v abx2xml >/dev/null 2>&1 || { err 'Android abx2xml not available'; return 1; }; abx2xml "$1" "$2" >/dev/null 2>&1 || { err 'Cannot decode SSAID binary XML'; return 1; } ;;
    xml) cp "$1" "$2" || return 1 ;;
  esac
  grep -q '<settings' "$2" && grep -q '</settings>' "$2" || { err 'SSAID XML structure could not be verified'; return 1; }
}
encode(){
  case "$1" in
    abx) command -v xml2abx >/dev/null 2>&1 || { err 'Android xml2abx not available'; return 1; }; xml2abx "$2" "$3" >/dev/null 2>&1 || { err 'SSAID binary conversion failed'; return 1; } ;;
    xml) cp "$2" "$3" || return 1 ;;
  esac
}
patch_xml(){
  awk -v wanted="$1" -v target="$2" '
    /<setting[[:space:]]/ {
      if(index($0,"name=\"" wanted "\"") > 0) {
        if(!match($0,/value="[^"]*"/)) exit 12;
        sub(/value="[^"]*"/, "value=\"" target "\""); found++;
      }
    }
    {print}
    END {if(found!=1)exit 13}
  ' "$3" > "$4" || { err 'SSAID UID entry missing, ambiguous or malformed; no file staged'; return 1; }
}
extract_id(){
  awk -v wanted="$1" '
    /<setting[[:space:]]/ {
      if(index($0,"name=\"" wanted "\"") > 0) {
        if(match($0,/value="[^"]*"/)) {
          value=substr($0,RSTART+7,RLENGTH-8);print value;found++
        }
      }
    }
    END {if(found!=1)exit 2}
  ' "$2"
}
ensure_seed(){
  [ -s "$SEED" ] && return 0
  safe_store || return 1
  tmp="$SEED.$$"; umask 077
  od -An -tx1 -N 32 /dev/urandom | tr -d ' \n' > "$tmp" || { rm -f "$tmp"; return 1; }
  [ "$(wc -c < "$tmp")" -eq 64 ] || { rm -f "$tmp"; err 'Secure random salt unavailable'; return 1; }
  mv -f "$tmp" "$SEED"
}
current_fp(){
  [ -f "$MODDIR/config.conf" ] || return 1
  sed -n 's/^fingerprint=//p' "$MODDIR/config.conf" | head -n 1
}
derive(){
  ensure_seed || return 1
  fp=$(current_fp)
  [ -n "$fp" ] || { err 'Apply a build fingerprint before enabling SSAID sync'; return 1; }
  (printf 'BuildIdentity-SSAID-v1\n%s\n%s\n%s\n' "$(cat "$SEED")" "$fp" "$UID_FOUND") | sha256sum | cut -c 1-16
}
# stage_change <package> <manual|sync|restore> <value or ->
stage_change(){
  package=$1 mode=$2 desired=${3:--}
  resolve_uid "$package" || return 1
  [ -s "$TARGET" ] || { err 'SSAID data file not found, refusing to create one'; return 1; }
  if [ "$mode" = sync ]; then desired=$(derive) || return 1; fi
  safe_store || return 1
  work="$STORAGE/.txn.$$"; mkdir -m 700 "$work" || return 1
  trap 'rm -rf "$work"' 0 1 2 3 15
  orig_sha=$(sha "$TARGET") || return 1
  base="$TARGET"
  if [ -f "$PENDING" ] && [ -f "$META" ]; then
    old_sha=$(sed -n 's/^source_sha=//p' "$META" | head -n 1)
    if [ "$orig_sha" != "$old_sha" ]; then err 'SSAID database changed since earlier stage; reboot or clear the pending stage'; return 1; fi
    base="$PENDING"
  fi
  type=$(kind "$TARGET")
  decode "$base" "$work/current.xml" || return 1
  if [ "$mode" = restore ]; then
    [ -f "$BACKUP" ] || { err 'No original SSAID backup available'; return 1; }
    decode "$BACKUP" "$work/original.xml" || return 1
    desired=$(extract_id "$UID_FOUND" "$work/original.xml") || { err 'Original app SSAID not found in backup'; return 1; }
  fi
  valid_hex "$desired" || { err 'SSAID must be exactly 16 hexadecimal characters'; return 1; }
  desired=$(printf '%s' "$desired" | tr 'A-F' 'a-f')
  patch_xml "$UID_FOUND" "$desired" "$work/current.xml" "$work/modified.xml" || return 1
  encode "$type" "$work/modified.xml" "$work/new.bin" || return 1
  decode "$work/new.bin" "$work/roundtrip.xml" || return 1
  actual=$(extract_id "$UID_FOUND" "$work/roundtrip.xml") || { err 'Re-encoded SSAID entry not found'; return 1; }
  [ "$actual" = "$desired" ] || { err 'Round-trip verification failed'; return 1; }
  # The original complete file is retained for emergency recovery. It is never
  # replaced with another snapshot, including after later edits or reboots.
  if [ ! -f "$BACKUP" ]; then cp "$TARGET" "$work/original.bin" || return 1; mv "$work/original.bin" "$BACKUP" || return 1; chmod 0600 "$BACKUP"; fi
  printf 'source_sha=%s\nformat=%s\npackage=%s\nuid=%s\nid=%s\n' "$orig_sha" "$type" "$package" "$UID_FOUND" "$desired" > "$work/pending.meta"
  chmod 0600 "$work/new.bin" "$work/pending.meta"
  mv -f "$work/new.bin" "$PENDING" || return 1
  mv -f "$work/pending.meta" "$META" || return 1
  echo 'staged=1'
  echo "package=$package"
  echo "uid=$UID_FOUND"
  echo "next_id=$desired"
  echo 'notice=Reboot to apply before SettingsProvider starts.'
}
save_profile(){
  package=$1 mode=$2 manual=$3
  safe_store || return 1
  tmp="$PROFILE.$$"; umask 077
  printf 'package=%s\nmode=%s\nmanual=%s\n' "$package" "$mode" "$manual" > "$tmp" || return 1
  mv -f "$tmp" "$PROFILE"
}
case "${1:-}" in
  stage)
    [ "$#" -eq 4 ] || { err 'Usage: stage <package> <sync|manual> <16-hex-id|->'; exit 2; }
    valid_pkg "$2" || { err 'Invalid package name'; exit 2; }
    case "$3" in sync|manual) ;; *) err 'Mode must be sync or manual'; exit 2 ;; esac
    stage_change "$2" "$3" "$4" || exit 3
    save_profile "$2" "$3" "$4" || exit 3
    ;;
  resync)
    read_profile
    [ "$MODE" = sync ] && [ -n "$PKG" ] || exit 0
    stage_change "$PKG" sync - || exit 3
    ;;
  restore)
    [ "$#" -eq 2 ] || exit 2
    stage_change "$2" restore - || exit 3
    # Auto-sync must not immediately change the restored value back.
    rm -f "$PROFILE"
    ;;
  clear-pending)
    safe_store || exit 2
    rm -f "$PENDING" "$META"
    echo 'Pending SSAID change cancelled. Applied changes are unaffected.'
    ;;
  status)
    read_profile
    printf 'ssaid_profile_package=%s\nssaid_profile_mode=%s\nssaid_profile_manual=%s\n' "$PKG" "$MODE" "$MANUAL"
    printf 'ssaid_source=%s\n' "$([ -r "$TARGET" ] && echo present || echo unavailable)"
    [ -f "$PENDING" ] && echo 'ssaid_pending=1' || echo 'ssaid_pending=0'
    [ -f "$META" ] && sed -n 's/^id=/ssaid_pending_value=/p;s/^package=/ssaid_pending_package=/p' "$META"
    [ -f "$ERROR" ] && printf 'ssaid_last_result=%s\n' "$(head -n 1 "$ERROR")"
    if command -v settings >/dev/null 2>&1; then
      printf 'ssaid_legacy_id=%s\n' "$(settings --user 0 get secure android_id 2>/dev/null | head -n 1)"
    fi
    ;;
  *) err 'Usage: ssaidctl.sh {status|stage|resync|restore|clear-pending}'; exit 2 ;;
esac
