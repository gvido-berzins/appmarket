#!/usr/bin/env python3
"""Generate an F-Droid-compatible repo from apps.json + staged release APKs.

Produces fdroid/repo/ with the APKs and an index-v1.json (F-Droid v1 schema).
NOTE: F-Droid CLIENTS REQUIRE A SIGNED INDEX (index-v1.jar). To make this a real
addable repo, run `fdroid update` (pip install fdroidserver) over fdroid/ with a
repo keystore — that signs the index. This script gives you the data + layout.
"""
import datetime
import glob
import hashlib
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "fdroid" / "repo"
REPO_URL = "https://raw.githubusercontent.com/gvido-berzins/appmarket/main/fdroid/repo"


def sha256(p):
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main():
    reg = json.loads((ROOT / "apps.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    now = int(datetime.datetime.now().timestamp() * 1000)
    apps, packages = [], {}

    for app in reg["apps"]:
        slug = app["slug"]
        apks = sorted(glob.glob(str(ROOT / "releases" / slug / "*.apk")))
        if not apks:
            continue
        L = app.get("latest", {})
        apps.append({
            "packageName": app["id"],
            "name": app["name"],
            "summary": app.get("summary", ""),
            "description": app.get("description", ""),
            "categories": [app.get("category", "Other").capitalize()],
            "license": "Unknown",
            "webSite": app.get("website") or "",
            "added": now, "lastUpdated": now,
            "suggestedVersionName": L.get("versionName"),
            "suggestedVersionCode": str(L.get("versionCode", "")),
        })
        entries = []
        for apk in apks:
            p = pathlib.Path(apk)
            shutil.copy2(p, OUT / p.name)
            entries.append({
                "apkName": p.name,
                "versionName": L.get("versionName"),
                "versionCode": L.get("versionCode"),
                "size": p.stat().st_size,
                "hash": sha256(p), "hashType": "sha256",
                "minSdkVersion": L.get("minSdk"),
                "added": now,
            })
        packages[app["id"]] = entries

    index = {
        "repo": {
            "timestamp": now, "version": 20002,
            "name": reg.get("market", {}).get("name", "Apps"),
            "description": "Personal app repository.",
            "address": REPO_URL,
            "icon": "icon.png",
        },
        "requests": {"install": [], "uninstall": []},
        "apps": apps,
        "packages": packages,
    }
    (OUT / "index-v1.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"wrote {OUT}/index-v1.json with {len(apps)} apps, "
          f"{sum(len(v) for v in packages.values())} packages")
    print("NOTE: sign with `fdroid update` (fdroidserver) to make it client-addable.")


if __name__ == "__main__":
    main()
