# Powerkrieger F-Droid repository

Self-hosted [F-Droid](https://f-droid.org) repository for the apps at
[github.com/Powerkrieger](https://github.com/Powerkrieger), served from GitHub Pages:

- Address: `https://powerkrieger.github.io/fdroid/repo`
- Fingerprint: `9B97140E3746038EBAC4079BCB9580334C170BBF29F907094D8F34050059B37C`

## How it works

`.github/workflows/publish.yml` runs daily, on every push and on manual dispatch. It downloads the
APK of each app's latest GitHub release (`scripts/fetch-apks.sh`, apps listed in `apps.txt`),
runs `fdroid update` to build and sign the index, and deploys `repo/` plus `pages/` to GitHub
Pages. Nothing is stored in git except metadata; the APKs stay signed with each app's own key.

App texts live in `metadata/<applicationId>.yml`, categories in `config/categories.yml`. fdroidserver
doesn't take icons from APKs, so each app has `metadata/<applicationId>/en-US/icon.png`, rendered
from its adaptive launcher icon with `scripts/render-icon.py <android-project> <out.png>`. The repo
icon is `icon.svg`/`icon.png`.

To add an app: add a line to `apps.txt`, a `metadata/<applicationId>.yml` and its icon. F-Droid only
offers an update when the release's `versionCode` is higher than the installed one.

## Index signing key

`fdroid-repo.jks` (alias `fdroid-repo`) signs the index; its passwords are in `fdroid-repo.env`.
Both are gitignored. CI uses the repository secrets `KEYSTORE_BASE64`, `KEYSTORE_PASSWORD` and
`KEY_PASSWORD`. Losing the key means every user has to remove and re-add the repository, so keep a
copy in the password manager.

To build the index locally (needs fdroidserver and the Android SDK):

    set -a; source fdroid-repo.env; set +a
    scripts/fetch-apks.sh && mkdir -p repo/icons && cp icon.png repo/icons/
    ANDROID_HOME=~/Android/Sdk fdroid update

## License

MIT, see [LICENSE](LICENSE).
