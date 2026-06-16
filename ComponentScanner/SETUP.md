# Component Scanner — Setup (start here)

This is the only guide you need. The app is **code-complete**; the only things left for you
to do are: **paste two API keys** into the backend, **deploy/run the backend**, and **put the
backend URL** into the app. Then build and run on your phone.

```
Phone app  ──►  Backend (holds your keys)  ──►  Claude (reads the chip)
                                            └─►  Nexar (finds the datasheet)
```

---

## 0. What you need
- **Android Studio** (with JDK 17) and the Android SDK — already installed on this machine
  (`%LOCALAPPDATA%\Android\Sdk`).
- **Node.js 20+** (for the backend).
- Two free API keys (next step).

---

## 1. Get the two keys (free)
1. **Anthropic API key** — https://console.anthropic.com → *API Keys* → create key.
   Looks like `sk-ant-...`. (Used by the backend to read chip markings with Claude vision.)
2. **Nexar Client ID + Secret** — https://nexar.com → sign up → create an **application**
   with the **Supply** scope → copy the **Client ID** and **Client Secret** (the secret is
   shown once). The backend exchanges these for an access token automatically. (Used to look
   up datasheets. Free tier is plenty for classroom use.)

You never put these in the phone app — only in the backend. That's the whole point of the
backend: keys stay off the device.

---

## 2. Run the backend

```bash
cd ComponentScanner/backend
npm install
npm test           # optional: confirms everything is green (41 tests)
```

### Option A — quickest for trying it on the same Wi-Fi (local)
Create a file `ComponentScanner/backend/.dev.vars` (it is git-ignored) with your keys:
```
ANTHROPIC_API_KEY=sk-ant-...your key...
NEXAR_CLIENT_ID=...your nexar client id...
NEXAR_CLIENT_SECRET=...your nexar client secret...
```
Then run it:
```bash
npm run dev        # serves on http://localhost:8787
```
- On the **same PC** the URL is `http://localhost:8787/`.
- For a **physical phone on the same Wi-Fi**, use your PC's LAN IP instead, e.g.
  `http://192.168.1.42:8787/` (find it with `ipconfig`). The phone and PC must be on the
  same network, and Windows Firewall must allow Node on port 8787.

> Note: in local dev the result cache is in-memory (fine for testing). For real shared use,
> deploy (Option B), which uses Cloudflare KV for caching.

### Option B — deploy to the cloud (free, recommended for real use)
```bash
npx wrangler login
npx wrangler secret put ANTHROPIC_API_KEY      # paste your key when prompted
npx wrangler secret put NEXAR_CLIENT_ID        # paste your Nexar Client ID
npx wrangler secret put NEXAR_CLIENT_SECRET    # paste your Nexar Client Secret
# (optional, enables shared caching) create a KV namespace and paste the id into wrangler.toml:
npx wrangler kv namespace create CACHE
npm run deploy
```
Wrangler prints your deployed URL, e.g. `https://component-scanner-backend.<you>.workers.dev`.
That URL is what the app uses.

Quick check the backend is alive (replace the URL):
```bash
curl https://component-scanner-backend.<you>.workers.dev/health
# -> {"status":"ok"}
```

---

## 3. Point the app at your backend
Open `ComponentScanner/app/local.properties` (create it if missing — it's git-ignored) and
make sure it has BOTH lines:
```
sdk.dir=C\:\\Users\\Mads2\\AppData\\Local\\Android\\Sdk
backend.url=https://component-scanner-backend.<you>.workers.dev/
```
Use your local LAN URL here instead if you chose Option A (e.g. `http://192.168.1.42:8787/`).
The trailing slash matters.

> For plain `http://` (local, non-HTTPS) URLs, Android blocks cleartext by default. If you go
> the local route, either deploy (Option B, HTTPS) or add a network-security config allowing
> cleartext to your PC's IP. The deployed Cloudflare URL is HTTPS and needs nothing extra.

---

## 4. Build & install on your phone
Enable USB debugging on the phone and plug it in, then:
```bash
cd ComponentScanner/app
./gradlew assembleDebug      # build the APK
./gradlew installDebug       # install on the connected phone
```
(On Windows use `gradlew.bat`. If Gradle says it can't find a compiler, set
`JAVA_HOME` to a JDK 17, e.g. `C:\Program Files\Java\jdk-17`.)

You can also just open `ComponentScanner/app` in Android Studio and press Run.

---

## 5. Try it (manual checklist)
- **Single scan**: point at one chip; a "Detected: …" chip appears from on-device OCR. Tap it
  to open the datasheet. For a worn/angled marking, tap the **camera button** (deep scan) to
  send one photo to the backend for a better read.
- **Shelf scan**: switch the toggle to **Shelf**, point at a bin/wall of parts, tap the camera
  button — a list of every identified part appears; tap any to open its datasheet.
- **Datasheet**: opens in-app, scrollable.
- **Manual entry**: tap "Enter part #" to type a part number directly.
- **History**: previously scanned parts are saved; swipe into one or delete it.

---

## What's done vs. deferred
**Done & building green:** Android app (single scan, deep scan, shelf scan, datasheet PDF
viewer, history, manual entry) with 27 JVM unit tests; backend (`/identify` single+shelf,
`/datasheet`, caching, rate limiting) with 41 tests.

**Deliberately deferred (see the app/backend READMEs):** offline part database, richer OCR
normalization/fuzzy matching (the backend vision model handles robust reads today), datasheet
URL reachability validation + fallback resolvers, and an offline banner. None block normal use.

**The only things that are truly required from you:** the two keys (step 1–2) and the backend
URL (step 3).
