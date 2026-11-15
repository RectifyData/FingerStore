#!/usr/bin/env python3
"""Refresh FingerStore's provenance-aware offline fingerprint catalog.

Data != trust. Import only literal fingerprint fields, never synthesize a new
fingerprint from a build ID, SDK level, device label or firmware download URL.
External sources are read at build-time; the shipped WebUI works offline.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
MH_SHA = "dbddef20bea59e12290b936eb751ed74d38456b0"
DEVICEANON_SHA = "063439d9dc26f4b495d3e514af56a1ecbf5623cb"
FP = re.compile(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+):([0-9]+(?:\.[0-9]+)*)/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.()-]+):(user|userdebug|eng)/([A-Za-z0-9_.-]+)$")
PATCH = re.compile(r"^\d{4}-\d\d-\d\d$")
PARTITION_ONLY = ("ro.system.build.fingerprint", "ro.vendor.build.fingerprint",
                  "ro.product.build.fingerprint", "ro.bootimage.build.fingerprint")
SOURCE_LINKS = [
    {"id": "MagiskHidePropsConf", "label": "MagiskHide Props Config",
     "url": "https://github.com/Magisk-Modules-Repo/MagiskHidePropsConf/blob/master/common/prints.sh",
     "role": "recorded stock fingerprints", "quality": "historical community list"},
    {"id": "DeviceAnon", "label": "DeviceAnon",
     "url": "https://github.com/UYIYUIYUIYUIJ/DeviceAnon/blob/main/app/src/main/assets/profiles.json",
     "role": "additional community fingerprint records", "quality": "upstream seed values, not individually OEM-verified"},
    {"id": "PixelProps", "label": "Pixel-Props/build.prop",
     "url": "https://github.com/Pixel-Props/build.prop/releases",
     "role": "OTA-derived Pixel property bundles", "quality": "extracted from publicly distributed image packages"},
    {"id": "ChkDumps", "label": "ChkDumps",
     "url": "https://github.com/ChkDumps",
     "role": "firmware dumps and partition build.prop cross-checks", "quality": "partition fingerprints are not necessarily the global fingerprint"},
    {"id": "FlashIndex", "label": "Android Flash Index",
     "url": "https://github.com/TsinbeiLabs/android-flash-index",
     "role": "official Google image discovery", "quality": "build IDs/URLs, not fingerprints"},
]
DUMPS = (
    ("ChkDumps/redmi_malachite_dump", "Xiaomi Redmi Note 14 Pro 5G"),
    ("ChkDumps/xiaomi_muyu_dump", "Xiaomi Pad 7 Pro"),
    ("ChkDumps/tecno_km7k_dump", "Tecno Spark Slim"),
    ("ChkDumps/redmi_air_dump", "Redmi 13R/13C 5G"),
    ("ChkDumps/redmi_spring_dump", "Redmi 15 5G"),
)
HEADERS = {"User-Agent": "FingerStore-stock-catalog-sync/1.0",
           "Accept": "application/vnd.github+json"}

def read(url, limit=8_000_000):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Oversized upstream response: " + url)
    return data

def read_json(url):
    return json.loads(read(url).decode("utf-8"))

def props(text):
    result = {}
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result

def ver_key(s):
    return tuple(int(n) for n in s.split("."))

def epoch_day(s):
    try:
        n = int(s)
        if not 946684800 <= n <= 4102444800: return ""
        return datetime.fromtimestamp(n, timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError, OverflowError): return ""

class Catalog:
    def __init__(self):
        self.records = {}
        self.fps = set()
        self.sources = defaultdict(lambda: {"recordsSeen": 0, "added": 0, "duplicates": 0})
        self.refs = []
        self.errors = []

    def add(self, *, source, label, manufacturer, model, fingerprint,
            patch="", date="", origin="", note=""):
        match = FP.fullmatch(fingerprint)
        if not match or match[7] != "user" or match[8] != "release-keys":
            self.errors.append("Invalid or non-stock fingerprint from " + source + ": " + fingerprint[:100])
            return False
        brand, product, device, version = match.group(1, 2, 3, 4)
        if not model or not label: return False
        self.sources[source]["recordsSeen"] += 1
        key = (brand.lower(), product.lower(), device.lower(), model.lower())
        record = self.records.get(key)
        if not record:
            slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
            rid = brand.lower() + ":" + slug
            if any(r["id"] == rid for r in self.records.values()):
                rid += "-" + str(len(self.records))
            record = {
                "id": rid, "label": label, "brand": brand,
                "manufacturer": manufacturer or brand, "model": model,
                "product": product, "device": device, "builds": defaultdict(list),
            }
            self.records[key] = record
        # One exact fingerprint may occur in multiple databases or under
        # multiple model spellings. It is still one underlying firmware build.
        for existing in record["builds"][version]:
            if existing["fingerprint"] == fingerprint:
                if source not in existing["sources"]: existing["sources"].append(source)
                if not existing["patch"] and PATCH.fullmatch(patch): existing["patch"] = patch
                if not existing["date"] and date: existing["date"] = date
                self.sources[source]["duplicates"] += 1
                return False
        variant = {
            "fingerprint": fingerprint,
            "patch": patch if PATCH.fullmatch(patch) else "",
            "date": date if re.fullmatch(r"\d{4}-\d\d-\d\d", date) else "",
            "sources": [source], "origin": origin, "note": note,
        }
        record["builds"][version].append(variant)
        self.fps.add(fingerprint)
        self.sources[source]["added"] += 1
        return True

    def import_historical(self):
        text = read(RAW + "/Magisk-Modules-Repo/MagiskHidePropsConf/master/common/prints.sh").decode("utf-8")
        # Guard the upstream structure and source version to avoid silently
        # interpreting arbitrary script text as trusted profile data.
        if "PRINTSV=137" not in text or 'PRINTSLIST="' not in text:
            raise ValueError("Unknown historical source format")
        block = text.split('PRINTSLIST="', 1)[1].split('\n"', 1)[0]
        for line in block.splitlines():
            if "=" not in line: continue
            header, variants = line.split("=", 1)
            fields = header.split(":")
            if len(fields) < 3: continue
            label, manufacturer, model = (part.strip() for part in fields[:3])
            for item in variants.split(";"):
                fp, _, suffix = item.partition("__")
                self.add(source="MagiskHidePropsConf", label=label,
                         manufacturer=manufacturer, model=model,
                         fingerprint=fp, patch=suffix,
                         origin="https://github.com/Magisk-Modules-Repo/MagiskHidePropsConf/blob/master/common/prints.sh")

    def import_deviceanon(self):
        data = read_json(RAW + "/UYIYUIYUIYUIJ/DeviceAnon/main/app/src/main/assets/profiles.json")
        profiles = data.get("profiles", [])
        if not 25 <= len(profiles) <= 100:
            raise ValueError("Unexpected DeviceAnon catalog size")
        for d in profiles:
            fp = d.get("fingerprint", "")
            parsed = FP.fullmatch(fp)
            if not parsed or parsed[4] != str(d.get("release", "")):
                self.errors.append("DeviceAnon version mismatch: " + str(d.get("id")))
                continue
            self.add(source="DeviceAnon", label=d["label"],
                     manufacturer=d.get("manufacturer", d.get("brand", "")),
                     model=d.get("model", ""), fingerprint=fp,
                     patch=d.get("security_patch", ""), origin=SOURCE_LINKS[1]["url"],
                     note="community seed fingerprint, independently verify if required")

    def import_pixelprops(self, max_releases=0):
        # All published OTA property packages, including A13/A14/A15/A16/A17
        # history, not just the three newest Android 17 collections.
        releases = read_json(API + "/repos/Pixel-Props/build.prop/releases?per_page=100")
        success = 0
        selected = releases[:max_releases] if max_releases > 0 else releases
        visited_assets = set()
        for rel in selected:
            for asset in rel.get("assets", []):
                if not asset.get("name", "").lower().endswith(".zip"): continue
                if asset.get("size", 0) > 250_000: continue
                # Identical firmware package names are republished across
                # release tags; use the newest source URL for each name.
                name_key = asset["name"].lower()
                if name_key in visited_assets: continue
                visited_assets.add(name_key)
                try:
                    data = read(asset["browser_download_url"], limit=300_000)
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        names = [n for n in archive.namelist() if n.endswith("system.prop")]
                        if not names: continue
                        name = min(names, key=lambda n: len(n))
                        if archive.getinfo(name).file_size > 200_000: continue
                        p = props(archive.read(name).decode("utf-8", "replace"))
                    # The extracted stock partition identity is the only
                    # accepted input: never reconstruct a fingerprint from the
                    # zip filename or a build ID in the index.
                    fp = (p.get("ro.product.build.fingerprint") or
                          p.get("ro.system.build.fingerprint") or
                          p.get("ro.build.fingerprint") or "")
                    m = FP.fullmatch(fp)
                    if not m: continue
                    manufacturer = p.get("ro.product.manufacturer") or "Google"
                    model = p.get("ro.product.model") or p.get("ro.product.model_for_attestation")
                    if not model or model.lower() in ("generic", "mainline"): continue
                    self.add(source="PixelProps", label="Google " + model + " — " + asset["name"],
                             manufacturer=manufacturer, model=model, fingerprint=fp,
                             patch=(p.get("ro.build.version.security_patch") or
                                    p.get("ro.product.build.version.security_patch") or ""),
                             date=epoch_day(p.get("ro.product.build.date.utc") or p.get("ro.system.build.date.utc")),
                             origin=asset["browser_download_url"],
                             note="extracted from Pixel-Props OTA-derived release ZIP")
                    success += 1
                except (ValueError, UnicodeDecodeError, urllib.error.URLError,
                        zipfile.BadZipFile, KeyError) as exc:
                    self.errors.append("PixelProps " + asset.get("name", "?") + ": " + str(exc)[:130])
        if success < 8:
            raise ValueError("Pixel-Props import insufficient: " + str(success) + " valid assets")
        return success

    def inspect_dumps(self):
        for repo, label in DUMPS:
            url = API + "/repos/" + repo + "/contents/system/system/build.prop"
            try:
                # DumprX branches are named after the firmware build, not
                # "main". The Contents endpoint resolves the default branch.
                blob = read_json(url)
                if blob.get("encoding") != "base64": raise ValueError("unexpected dump encoding")
                p = props(base64.b64decode(blob["content"]).decode("utf-8"))
                global_fp = p.get("ro.build.fingerprint", "")
                sys_fp = p.get("ro.system.build.fingerprint", "")
                m = FP.fullmatch(global_fp) if global_fp else None
                if m:
                    # Only a full global fingerprint with a matching actual
                    # product/device identity can be a selectable stock build.
                    self.add(source="ChkDumps", label=label,
                             manufacturer=p.get("ro.product.system.manufacturer", ""),
                             model=p.get("ro.product.system.model") or label,
                             fingerprint=global_fp,
                             patch=p.get("ro.build.version.security_patch", ""),
                             date=epoch_day(p.get("ro.build.date.utc")),
                             origin=url)
                    kind = "global"
                else:
                    kind = "partition-only" if sys_fp else "missing-fingerprint"
                self.refs.append({"source": "ChkDumps", "label": label,
                                  "url": "https://github.com/" + repo,
                                  "fingerprintType": kind,
                                  "android": p.get("ro.build.version.release", ""),
                                  "note": "Not selectable unless the global build fingerprint is unambiguous"})
            except (OSError, ValueError, urllib.error.URLError) as exc:
                self.errors.append("ChkDumps " + repo + ": " + str(exc)[:130])
                self.refs.append({"source": "ChkDumps", "label": label,
                                  "url": "https://github.com/" + repo, "fingerprintType": "unavailable"})

    def inspect_flash_index(self):
        try:
            index = read_json(RAW + "/TsinbeiLabs/android-flash-index/main/data/latest.json")
            data = index.get("latest", {})
            for codename in list(data)[:80]:
                latest = data[codename]
                item = latest.get("latestBeta") or latest.get("latestCanary") or {}
                url = item.get("factoryImageUrl", "")
                if url.startswith("https://dl.google.com/"):
                    self.refs.append({"source": "FlashIndex", "label": codename,
                                      "url": url, "fingerprintType": "firmware-url",
                                      "android": item.get("track", ""),
                                      "note": "Firmware index only: build ID cannot be promoted to a fingerprint"})
            self.sources["FlashIndex"]["recordsSeen"] = len(data)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            self.errors.append("FlashIndex: " + str(exc)[:150])

    def emit(self):
        records = []
        for record in self.records.values():
            builds = {}
            for version, variants in record["builds"].items():
                # Deterministic order: newest reported patches then build dates.
                variants.sort(key=lambda x: (x["date"], x["patch"], x["fingerprint"]), reverse=True)
                builds[version] = variants
            versions = sorted(builds, key=ver_key)
            record["builds"] = {v: builds[v] for v in versions}
            record["defaultVersion"] = versions[-1]
            record["fingerprint"] = builds[versions[-1]][0]["fingerprint"]
            records.append(record)
        records.sort(key=lambda r: (r["brand"].lower(), r["model"].lower(), r["label"].lower()))
        source_status = [{**source, **self.sources[source["id"]]} for source in SOURCE_LINKS]
        return records, source_status

def render_js(records, sources, references):
    header = """/* FingerStore offline stock catalog, generated from attributed public upstream data.
 * Never synthesize an Android build fingerprint. Availability is based on
 * source records only; community records are not OEM attestation certificates.
 * Regenerate with python3 scripts/refresh_catalog.py.
 */
(function(root){
 'use strict';
"""
    return (header +
        "const records=" + json.dumps(records, ensure_ascii=False, separators=(",", ":")) + ";\n" +
        "const sources=" + json.dumps(sources, ensure_ascii=False, separators=(",", ":")) + ";\n" +
        "const references=" + json.dumps(references, ensure_ascii=False, separators=(",", ":")) + ";\n" +
        """function builds(record, version){
 if(!record||!record.builds)return [];
 return Object.prototype.hasOwnProperty.call(record.builds,String(version))?record.builds[String(version)]:[];
}
function build(record,version,index){
 const list=builds(record,version),n=Number(index||0);
 return Number.isInteger(n)&&n>=0&&n<list.length?list[n]:null;
}
for(const record of records){
 for(const versions of Object.values(record.builds)){
  for(const b of versions){Object.freeze(b.sources);Object.freeze(b);}
  Object.freeze(versions);
 }
 Object.freeze(record.builds);Object.freeze(record);
}
for(const entry of sources)Object.freeze(entry);
for(const entry of references)Object.freeze(entry);
root.FINGERSTORE_CATALOG=Object.freeze(records);
root.FINGERSTORE_CATALOG_BUILDS=builds;
root.FINGERSTORE_CATALOG_BUILD=build;
root.FINGERSTORE_CATALOG_FP=(record,version,index)=>build(record,version,index)?.fingerprint||'';
root.FINGERSTORE_CATALOG_SOURCES=Object.freeze(sources);
root.FINGERSTORE_CATALOG_REFERENCES=Object.freeze(references);
root.FINGERSTORE_CATALOG_SOURCE=sources[0].url;
})(window);
""")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default=str(ROOT / "webroot/catalog.js"))
    ap.add_argument("--pixel-releases", type=int, default=0, help="0 imports all Pixel-Props release assets, else cap release collections")
    ap.add_argument("--skip-pixel", action="store_true", help="development only; disables OTA-import coverage")
    args = ap.parse_args()
    catalog = Catalog()
    catalog.import_historical()
    catalog.import_deviceanon()
    if not args.skip_pixel:
        catalog.import_pixelprops(args.pixel_releases)
    catalog.inspect_dumps()
    catalog.inspect_flash_index()
    records, sources = catalog.emit()
    counts = {entry["id"]: entry["added"] for entry in sources}
    count = sum(len(v) for record in records for v in record["builds"].values())
    if len(records) < 450 or count < 700:
        raise ValueError("Source catalog unexpectedly shrank: " + str((len(records), count)))
    if not args.skip_pixel and not any(v in ("16","17") and
            any(b["sources"][0]=="PixelProps" for b in builds)
            for r in records for v, builds in r["builds"].items()):
        raise ValueError("Modern OTA-sourced Pixel build was not imported")
    if not any("13" in r["builds"] for r in records):
        raise ValueError("Android 13 import missing")
    if not any("16" in r["builds"] for r in records):
        raise ValueError("Android 16 import missing")
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_js(records,sources,catalog.refs), encoding="utf-8")
    print(json.dumps({"profiles": len(records), "fingerprints": count,
                      "added": counts, "pixel_enabled": not args.skip_pixel,
                      "source_references": len(catalog.refs),
                      "warnings": catalog.errors[:15], "written": str(target)}, indent=2))
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except (OSError, ValueError, urllib.error.URLError) as exc:
        print("Catalog refresh failed: " + str(exc), file=sys.stderr)
        sys.exit(1)
