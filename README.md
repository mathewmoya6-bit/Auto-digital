# Auto-D Kenya — Android (TWA) Build & Play Store Guide

This wraps the live site at `https://auto-d.meipressgroup.com` into a real
Android app using a Trusted Web Activity (TWA). Your FastAPI backend,
Supabase auth, and M-Pesa flow all keep working exactly as they do today —
this only builds the Android shell around them.

## What you need locally (not doable in a hosted chat session)
- Node.js 18+
- Java JDK 17
- Android Studio (for the SDK + emulator/device testing) — https://developer.android.com/studio
- A Google Play Developer account (you already have this)

## 0. Real PNG icons
Bubblewrap needs actual PNG files, not the emoji SVG data-URI icon currently
inline in your HTML. Export three PNGs from your logo/branding:
- `icon-192.png` — 192x192
- `icon-512.png` — 512x512
- `icon-maskable-512.png` — 512x512, with the logo kept inside the center
  ~80% "safe zone" (Android crops maskable icons into circles/squircles)

Upload these to `/assets/` on `auto-d.meipressgroup.com`.

## 1. Publish the PWA files to your site
Upload the three files from this folder to your static frontend host:
- `manifest.json` → served at `https://auto-d.meipressgroup.com/manifest.json`
- `sw.js` → served at `https://auto-d.meipressgroup.com/sw.js`

Then add these two lines inside `<head>` of your production `index.html`
(replacing the old inline data-URI manifest link):
```html
<link rel="manifest" href="/manifest.json" />
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
  }
</script>
```

## 2. Install Bubblewrap and initialize the project
```bash
npm install -g @bubblewrap/cli
bubblewrap init --manifest https://auto-d.meipressgroup.com/manifest.json
```
When prompted, you can accept the values already filled into
`twa-manifest.json` in this folder (package ID `com.meipressgroup.autod`,
host `auto-d.meipressgroup.com`) — or copy that file into the generated
project directory to skip the prompts.

Bubblewrap will ask to generate a signing keystore (`android.keystore`).
**Back this file up somewhere safe and permanent** — if you lose it, you
can never update this app listing again and would have to publish under a
new package ID.

## 3. Get your app's SHA256 fingerprint and finish asset links
```bash
keytool -list -v -keystore android.keystore -alias autod
```
Copy the `SHA256:` fingerprint it prints, paste it into
`assetlinks.json` (replacing `REPLACE_WITH_SHA256_FROM_KEYSTORE`), then
upload that file to:
```
https://auto-d.meipressgroup.com/.well-known/assetlinks.json
```
This must be served with `Content-Type: application/json` and be publicly
reachable — it's what tells Android "this app and this website are the
same owner," which is what removes the browser UI in the app. Verify it
resolves correctly before moving on.

## 4. Build the app
```bash
bubblewrap build
```
This produces two files:
- `app-release-signed.apk` — for installing directly on a test device
- `app-release-bundle.aab` — the file Play Store actually wants

Test the APK on a real device or emulator first. Confirm:
- The app opens full-screen with no browser address bar (proves asset
  links verified correctly)
- Login, valuation calculators, and M-Pesa STK push all work as expected
- Back button behaves correctly navigating your site's pages

## 5. Play Console — create the listing
In Play Console → Create app, you'll need:
- **App name / short description / full description**
- **App icon** (512x512), **feature graphic** (1024x500), and at least
  2 phone **screenshots**
- **Privacy Policy URL** — mandatory since you collect email (Supabase
  Auth) and payment data (M-Pesa). If you don't have one hosted yet, this
  needs to exist before Google will let you publish.
- **Data safety form** — declare what's collected (email, phone number for
  M-Pesa, financial transaction data) and whether it's shared with third
  parties (Safaricom Daraja counts as a processor)
- **Content rating questionnaire**
- **Target audience** (adults, given financial transactions)

## 6. Upload and roll out
- Go to **Production** (or start with **Internal testing** / **Closed
  testing** to get real users trying it before a public release — 20
  testers minimum is common for closed testing)
- Upload `app-release-bundle.aab`
- Set countries (Kenya at minimum)
- Submit for review — first review typically takes a few hours to a
  couple of days

## 7. Updating the app later
Because it's a TWA, updating your website content (new calculators, UI
changes, pricing) requires **no new Play Store release** — it's live
instantly. You only need to rebuild and re-upload a new `.aab` if you
change: the app icon, package ID, permissions, or `twa-manifest.json`
settings (bump `appVersionCode` each time you do).

## Files in this folder
| File | Purpose |
|---|---|
| `manifest.json` | Web app manifest — upload to your site root |
| `sw.js` | Minimal service worker — upload to your site root |
| `twa-manifest.json` | Bubblewrap's Android app config |
| `assetlinks.json` | Domain-ownership proof — fill in fingerprint, then upload to `/.well-known/` on your site |
