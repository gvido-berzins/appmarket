# Deploying the marketplace (the auth-gated steps)

Everything else is automated. These three need YOUR accounts (one-time):

## 1. GitHub (hosts the APKs + the repo)
`gh` CLI isn't installed here. Either install it (`sudo pacman -S github-cli`)
or create the repo in the browser, then from `~/code/appmarket`:

```bash
git remote add origin https://github.com/gvido-berzins/appmarket.git
git push -u origin main
```

Then re-run each publish WITH `--github` so the APK is uploaded as a Release
asset and the public URL is written into apps.json:

```bash
python3 scripts/publish.py <path-to-release.apk> --github --changelog "..."
git push     # apps.json now points at github.com/.../releases/download/...
```

(With `gh` installed + `gh auth login` done, `--github` creates the tag, uploads
the APK, and fills the URL automatically.)

## 2. Vercel (hosts the tiny website)
The repo root IS the site (`index.html` + `apps.json` + `icons/`). On Vercel:
- New Project → import `gvido-berzins/appmarket`
- Framework preset: **Other** (no build step), output = root
- Deploy. Every `git push` redeploys; the listing updates automatically.

`apps.json` is served from the same origin, so the in-app update checks and the
website use the same URL with no CORS setup.

## 3. Update feed URL used by the apps
The in-app `UpdateChecker` reads:
`https://raw.githubusercontent.com/gvido-berzins/appmarket/main/apps.json`
(works the moment the repo is pushed — independent of Vercel). Change the
constant in each app if you use a different GitHub user/repo or a custom domain.

## Routine: shipping an update later
1. Bump `versionCode` (and versionName) in the app, build the signed release:
   `JAVA_HOME=/opt/android-studio/jbr ./gradlew :app:assembleRelease -Puniversal`
2. `python3 scripts/publish.py <release.apk> --github --changelog "what changed"`
3. `git push` — website + update feed update themselves.
