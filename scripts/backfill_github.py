#!/usr/bin/env python3
"""One-shot: push every already-staged APK in apps.json to GitHub Releases and
rewrite the local `apk` paths to live download URLs.

Use ONCE after the repo first gets a GitHub remote, to make all existing
entries (latest + history) downloadable and to unblock the in-app update
checks (which require an http(s) apk URL). Idempotent: skips a release/asset
that already exists. After this, routine updates go through `publish.py --github`.

Run from anywhere; needs `gh auth login` done first.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / "apps.json"


def sh(*args, check=True):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}\n{r.stderr.strip()}")
    return r


def repo_url():
    r = sh("gh", "repo", "view", "--json", "url", "-q", ".url", check=False)
    if r.returncode != 0:
        sys.exit("Not in a GitHub repo / not authed. Run: gh auth login && "
                 "git remote add origin <url> && git push -u origin main")
    return r.stdout.strip()


def release_exists(tag):
    return sh("gh", "release", "view", tag, check=False).returncode == 0


def asset_exists(tag, fname):
    r = sh("gh", "release", "view", tag, "--json", "assets",
           "-q", ".assets[].name", check=False)
    return r.returncode == 0 and fname in r.stdout.split()


def ensure_release(tag, title, notes, apk_path):
    fname = apk_path.name
    if not release_exists(tag):
        print(f"  creating release {tag}")
        sh("gh", "release", "create", tag, str(apk_path),
           "--title", title, "--notes", notes or title)
    elif not asset_exists(tag, fname):
        print(f"  uploading {fname} to existing {tag}")
        sh("gh", "release", "upload", tag, str(apk_path), "--clobber")
    else:
        print(f"  ok {tag}/{fname}")


def main():
    base = repo_url()
    reg = json.loads(REG.read_text())
    changed = 0

    for app in reg["apps"]:
        slug = app["slug"]
        name = app["name"]
        for entry in [app.get("latest")] + app.get("history", []):
            if not entry:
                continue
            apk = entry.get("apk", "")
            if apk.startswith("http"):
                continue  # already live
            local = ROOT / apk
            if not local.exists():
                print(f"  SKIP {slug} {entry.get('versionName')}: {apk} missing locally")
                continue
            tag = f"{slug}-v{entry['versionName']}"
            ensure_release(tag, f"{name} {entry['versionName']}",
                           entry.get("changelog", ""), local)
            entry["apk"] = f"{base}/releases/download/{tag}/{local.name}"
            changed += 1

    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n")
    print(f"\nrewrote {changed} apk URLs -> {base}/releases/download/...")
    print("Next: git add apps.json && git commit -m 'go live: GitHub Release URLs' && git push")


if __name__ == "__main__":
    main()
