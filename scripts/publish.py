#!/usr/bin/env python3
"""Publish (or update) an app in the marketplace from an APK.

  python3 scripts/publish.py path/to/app-release.apk --changelog "What changed"
  ... --github      also create a GitHub release (tag <slug>-v<ver>) and use its URL
  ... --no-commit   skip the git commit

Reads packageName/versionName/versionCode/minSdk from the APK via aapt2, moves
the previous version into `history`, stages the APK under releases/<slug>/ and
rewrites apps.json. The entry for the package must already exist in apps.json
(add new apps there once, by hand or with --new).
"""
import argparse
import datetime
import glob
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / "apps.json"


def find_aapt2():
    cands = sorted(glob.glob(str(pathlib.Path.home() / "Android/Sdk/build-tools/*/aapt2")))
    if not cands:
        sys.exit("aapt2 not found under ~/Android/Sdk/build-tools")
    return cands[-1]


def badging(apk):
    out = subprocess.run([find_aapt2(), "dump", "badging", str(apk)],
                         capture_output=True, text=True).stdout
    pkg = re.search(r"package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", out)
    sdk = re.search(r"minSdkVersion:'(\d+)'", out)
    label = re.search(r"application-label:'([^']+)'", out)
    if not pkg:
        sys.exit("could not parse APK badging output")
    return {
        "package": pkg.group(1),
        "versionCode": int(pkg.group(2)),
        "versionName": pkg.group(3),
        "minSdk": int(sdk.group(1)) if sdk else None,
        "label": label.group(1) if label else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apk")
    ap.add_argument("--changelog", default="")
    ap.add_argument("--github", action="store_true",
                    help="create GitHub release + use its download URL")
    ap.add_argument("--no-commit", action="store_true")
    args = ap.parse_args()

    apk = pathlib.Path(args.apk).resolve()
    if not apk.is_file():
        sys.exit(f"no such APK: {apk}")
    meta = badging(apk)
    reg = json.loads(REG.read_text())
    app = next((a for a in reg["apps"] if a["id"] == meta["package"]), None)
    if not app:
        sys.exit(f"{meta['package']} not in apps.json — add the app entry first")

    prev = app.get("latest") or {}
    if prev.get("versionCode") and meta["versionCode"] <= prev["versionCode"] and prev.get("apk"):
        sys.exit(f"versionCode {meta['versionCode']} <= published {prev['versionCode']} — "
                 "bump versionCode in the app and rebuild")

    slug = app["slug"]
    fname = f"{slug}-v{meta['versionName']}.apk"
    dest = ROOT / "releases" / slug / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(apk, dest)
    url = f"releases/{slug}/{fname}"  # local/dev URL

    if args.github:
        tag = f"{slug}-v{meta['versionName']}"
        notes = args.changelog or f"{app['name']} {meta['versionName']}"
        r = subprocess.run(["gh", "release", "create", tag, str(dest),
                            "--title", f"{app['name']} {meta['versionName']}",
                            "--notes", notes], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("gh release failed: " + r.stderr.strip())
        remote = subprocess.run(["gh", "repo", "view", "--json", "url", "-q", ".url"],
                                cwd=ROOT, capture_output=True, text=True).stdout.strip()
        url = f"{remote}/releases/download/{tag}/{fname}"

    if prev.get("apk"):
        app.setdefault("history", []).insert(0, prev)
    app["latest"] = {
        "versionName": meta["versionName"],
        "versionCode": meta["versionCode"],
        "apk": url,
        "size": dest.stat().st_size,
        "minSdk": meta["minSdk"],
        "released": datetime.date.today().isoformat(),
        "changelog": args.changelog or prev.get("changelog", ""),
    }
    reg["updated"] = datetime.date.today().isoformat()
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n")
    print(f"published {app['name']} {meta['versionName']} (code {meta['versionCode']}) -> {url}")

    if not args.no_commit:
        subprocess.run(["git", "add", "apps.json"], cwd=ROOT)
        subprocess.run(["git", "commit", "-q", "-m",
                        f"publish {slug} v{meta['versionName']}"], cwd=ROOT)
        print("committed apps.json")


if __name__ == "__main__":
    main()
