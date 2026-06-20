# appmarket — personal Android app marketplace

A registry + publish pipeline for all my offline Android apps (plombus, aksess,
az-guide, barcode-scanner, namedays-lv, cleanup). The website renders
`apps.json`; APKs are hosted as GitHub Release assets; publishing an update is
one command.

## Live (deployed 2026-06-20)

- **Website:** https://gvido-berzins.github.io/appmarket/ (GitHub Pages, main/root)
- **Update feed:** https://raw.githubusercontent.com/gvido-berzins/appmarket/main/apps.json
- **APKs:** GitHub Releases on this repo (tags `<slug>-v<ver>`)
- **Update delivery:** in-app banner — each app checks the feed on launch, compares
  `versionCode`, and shows an "Update available" dialog (with changelog) that opens the
  release APK. Android shows its install prompt (signatures match → installs over the top).
  *(No silent/background auto-update: Android reserves that for Play Store / privileged
  stores. F-Droid-client delivery remains a future option — the repo index data exists.)*
- **Versioning (all apps):** `versionName` = semver; `versionCode` derived in Gradle as
  `MAJOR*10000 + MINOR*100 + PATCH` so it always increases. Only ever edit `versionName`.

## Architecture — one source of truth

```
apps.json          ← THE registry. The website reads it. Apps read it for updates.
icons/<slug>.png   ← app icons (small, committed)
screenshots/<slug>/← website screenshots (committed)
releases/<slug>/   ← local APK staging (gitignored — real hosting is GitHub Releases)
scripts/publish.py ← one-command publish (reads APK, updates apps.json, uploads)
web/               ← the website (Vercel) — renders apps.json
```

Every app entry: `id` (package), `slug`, `name`, `summary`, `description`,
`icon`, `latest {versionName, versionCode, apk, size, minSdk, released,
changelog}`, `history[]`, `website?`, `source?`.

## Feasibility — the two things that make or break it

**1. APK hosting: do NOT put APKs on Vercel.**
Our APKs are 25–165 MB. Vercel deployments are not meant for large binaries
(file-size/deploy limits, slow deploys, no versioning). Decision: **GitHub
Releases** hosts every APK (free, up to 2 GB/file, stable URLs of the form
`github.com/<user>/appmarket/releases/download/<slug>-v<ver>/<file>.apk`).
The Vercel site stays tiny: HTML + apps.json + icons + screenshots.
One marketplace repo can carry releases for ALL apps via per-app tags
(`plombus-v0.3.1`, `aksess-v0.2.0`, …) — apps don't each need their own remote.

**2. Signing: updates only install over an app when SIGNATURES MATCH.**
Everything built so far is debug-signed (machine-specific key). If users
install a debug build today and a differently-signed build tomorrow, Android
refuses the update (they'd have to uninstall → lose data). Before the first
public listing: create ONE release keystore, add a `signingConfig` to every
app, and only ever publish release-signed APKs.

```
keytool -genkeypair -v -keystore ~/keys/appmarket.jks -alias appmarket \
  -keyalg RSA -keysize 4096 -validity 10000
```
Back the keystore up — losing it means losing the update path for every app.

## Publishing an update (the easy part)

```
python3 scripts/publish.py path/to/app-release.apk --changelog "Fixed X, added Y"
# add --github once the repo has a GitHub remote: creates the release tag,
# uploads the APK, and writes the public download URL into apps.json
```
The script reads packageName/versionName/versionCode straight from the APK
(aapt2), bumps the registry (previous version moves to `history`), copies the
APK to `releases/<slug>/`, and commits. Vercel redeploys the site on push —
the listing is updated with zero manual editing.

Versioning rule: **always bump `versionCode`** in the app before building, or
Android won't offer the update.

## In-app updates (phase 3)

Tiny `UpdateChecker` shared across the Kotlin apps:
1. `GET https://<market-domain>/apps.json`
2. compare `latest.versionCode` with `BuildConfig.VERSION_CODE`
3. show a snackbar/dialog → open `latest.apk` URL (browser handles download;
   Android prompts install since signatures match).
For az-guide (Capacitor) the same check in JS. No Play Store, no server code.

## The website (you build this part)

Static or Next.js on Vercel, same repo (`web/`):
- index: cards from `apps.json` (icon, name, summary, version, size, updated)
- detail page per slug: screenshots, full description, changelog/history,
  **Download APK** (GitHub Release URL) + QR code for phone scanning
- `apps.json` served from the same origin → no CORS issues; in-app checkers
  use the same URL.

## Roadmap

- [x] Phase 0 — this repo: registry schema, real app entries, publish script
- [x] Phase 1 — release keystore (`~/keys/appmarket.jks`); signingConfig in all apps;
      release APKs published
- [x] Phase 2 — GitHub remote + `--github` publishing; **GitHub Pages** for the site
      (chose Pages over Vercel — same repo, no extra account)
- [x] Phase 3 — UpdateChecker in each app (now shows changelog); deterministic versioning
- [ ] Phase 4 (optional) — sign the F-Droid repo index (`fdroidserver`) so the market can
      be added to the F-Droid client; QR codes + screenshots on the site
