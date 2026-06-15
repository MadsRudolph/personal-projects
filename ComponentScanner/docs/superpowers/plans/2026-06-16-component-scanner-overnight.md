# Component Scanner — Overnight Completion Work Order

> Executed autonomously. Goal: a code-complete app whose ONLY remaining manual steps are
> (a) paste Anthropic + Nexar keys into the backend and deploy it, (b) set the backend URL
> in one place, (c) build + device-test. Every batch must end with `assembleDebug` =
> BUILD SUCCESSFUL and all unit tests passing.

**Repo:** `C:\Users\Mads2\Documents\Projects` (git, branch `main`, commit directly).
**App:** `ComponentScanner/app` (Kotlin/Compose/Hilt). **Backend:** `ComponentScanner/backend` (done).
**Gradle:** run from `ComponentScanner/app` via `./gradlew.bat`; if no compiler, set
`$env:JAVA_HOME="C:\Program Files\Java\jdk-17"`. JVM unit tests: `testDebugUnitTest`.
Compile gate: `assembleDebug`.

---

## Batch 1 — Turnkey config + image capture + deep-scan button (single mode)

### 1a. Backend URL from `local.properties` (no source edits for the user)
In `app/app/build.gradle.kts`, read `backend.url` from the project's `local.properties`
(git-ignored) with a clear placeholder default, and expose it as `BACKEND_BASE_URL`:

```kotlin
import java.util.Properties
// near top of the android {} or before defaultConfig:
val localProps = Properties().apply {
    val f = rootProject.file("local.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}
val backendUrl = (localProps.getProperty("backend.url")
    ?: "https://REPLACE-WITH-YOUR-BACKEND-URL.workers.dev/")
// in defaultConfig:
buildConfigField("String", "BACKEND_BASE_URL", "\"$backendUrl\"")
```
Acceptance: building with no `backend.url` set still compiles and uses the placeholder.

### 1b. Client image util — downscale + JPEG + base64
Create `app/src/main/java/com/dtu/componentscanner/util/ImageEncoding.kt`:
- A **pure, JVM-testable** function `fun encodeBase64(bytes: ByteArray): String` (use
  `java.util.Base64` NO_WRAP) — write a unit test `util/ImageEncodingTest.kt` (round-trip a
  small byte array, assert decode matches). Use `android.util.Base64`? NO — use
  `java.util.Base64` so it runs on the JVM.
- An Android function `fun downscaleJpegBase64(jpegBytes: ByteArray, maxDim: Int = 1280, quality: Int = 85): String`
  that decodes with `BitmapFactory`, scales so the longest side ≤ maxDim (keep aspect),
  compresses to JPEG, and returns `encodeBase64(...)`. (Not unit-tested — Android graphics.)

### 1c. ImageCapture + deep-scan button in ScanScreen
- Add an `ImageCapture` use case to the CameraX binding in `ScanScreen.kt`'s `CameraPreview`.
  Hoist the `ImageCapture` instance up so a button can trigger it (e.g. pass a
  `onCaptureReady: (ImageCapture) -> Unit` from `CameraPreview`, store it in screen state, or
  build the use case in the screen and hand it to `CameraPreview`). Keep the existing
  `ImageAnalysis`/OCR path.
- Add a "Deep scan" button (e.g. a `FloatingActionButton` with a camera icon). On tap:
  `imageCapture.takePicture(executor, OnImageCapturedCallback)` → from the `ImageProxy`
  (JPEG format) read the buffer to a `ByteArray` → `downscaleJpegBase64(...)` on
  `Dispatchers.Default`/IO → call `viewModel.deepScan(base64, "image/jpeg")`. Close the
  `ImageProxy`. Show the existing `isScanning` spinner during the call.
- `ScanViewModel.deepScan` already exists and is tested; leave its signature, but generalize
  it to use the current scan mode (see Batch 2) — for Batch 1 it stays "single".

Build gate + run unit tests. Commit:
`feat(app): turnkey backend URL config + deep-scan image capture`.

---

## Batch 2 — Shelf-scan mode (the "wall of components" feature)

### 2a. ScanViewModel: mode + shelf results (TDD)
Edit `ui/scan/ScanViewModel.kt`:
- Add `enum class ScanMode { SINGLE, SHELF }` (top-level in the file or a small file).
- Add `scanMode: ScanMode = ScanMode.SINGLE` to `ScanUiState`.
- Add `fun setMode(mode: ScanMode)` updating state and clearing prior `candidates`.
- Change `deepScan(base64, mime)` to send `if (state.scanMode == SHELF) "shelf" else "single"`.
  Keep the method name/signature so existing tests pass (default mode SINGLE → "single").
- Keep `candidates` as the result list for both modes.

Add tests to `ui/ScanViewModelTest.kt` (keep existing 3 passing):
- `setMode switches mode and clears candidates`.
- `deepScan in SHELF mode requests shelf and stores all candidates` — use a fake repo whose
  `ApiService.identify` asserts `body.mode == "shelf"` and returns 2 candidates; assert both
  land in `state.candidates`.

### 2b. ScanScreen: mode toggle + shelf results UI
- Add a mode toggle at the top (Material3 `SingleChoiceSegmentedButtonRow` if available in
  the BOM, else two `FilterChip`s) bound to `viewModel.setMode(...)`.
- In SHELF mode, after a capture populates `candidates`, show a `ModalBottomSheet`
  (or an in-screen list) listing every candidate (partNumber + manufacturer + confidence).
  Tapping a row calls `onPartChosen(part)` → existing Result screen → datasheet.
- In SINGLE mode, keep current behavior (top candidate button / live detected chip).
- Use the SAME deep-scan capture button to trigger identification in both modes (mode
  decides single vs shelf).

Build gate + unit tests. Commit:
`feat(app): add shelf-scan mode for multi-component identification`.

---

## Batch 3 — Manual entry + retry/error UX

### 3a. Manual part-number entry
- On `ScanScreen` (e.g. a small row above the bottom controls, or behind an "Enter part #"
  TextButton that reveals an `OutlinedTextField` + "Look up"), let the user type a part
  number; on submit, normalize via `PartNumberExtractor.normalize` (inject the extractor —
  it's already a Hilt dependency of the VM; expose `fun lookupManual(text): String?` on the
  VM returning the normalized non-blank part, or do trivial trimming in the screen) and call
  `onPartChosen(normalized)`. Ignore blank input.
- If adding `lookupManual` to the VM, add a unit test (blank → null/ignored; "lm358n" →
  "LM358N").

### 3b. Retry on failures
- `ResultScreen`: in the `error` state, add a "Retry" button that calls
  `viewModel.load(partNumber)` again. In the `notFound` state, keep the message and offer
  manual re-entry via back navigation.
- `ScanScreen`: surface `state.error` with a "Dismiss" action (`viewModel.clearError()`).

Build gate + unit tests. Commit:
`feat(app): manual part-number entry and retry on errors`.

---

## Batch 4 — Production PDF viewer (lazy, leak-free, memory-safe)

Rewrite `ui/pdf/PdfViewerScreen.kt` to render pages on demand:
- Create a small holder opened once for the file:
  ```kotlin
  class PdfDocument(file: File) {
      private val pfd = ParcelFileDescriptor.open(file, MODE_READ_ONLY)
      private val renderer = PdfRenderer(pfd)
      private val mutex = Mutex()                  // PdfRenderer is NOT thread-safe
      val pageCount get() = renderer.pageCount
      suspend fun render(index: Int, targetWidthPx: Int): Bitmap = mutex.withLock {
          withContext(Dispatchers.IO) {
              renderer.openPage(index).use { page ->
                  val scale = targetWidthPx.toFloat() / page.width
                  val w = targetWidthPx
                  val h = (page.height * scale).toInt().coerceAtLeast(1)
                  val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
                  bmp.eraseColor(android.graphics.Color.WHITE)
                  page.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                  bmp
              }
          }
      }
      fun close() { runCatching { renderer.close() }; runCatching { pfd.close() } }
  }
  ```
  (`android.graphics.pdf.PdfRenderer.Page` implements Closeable via `.use` on API 26+? If
  `.use` isn't available on `Page`, use try/finally with `page.close()`.)
- In the composable: `remember(filePath)` the `PdfDocument`; `DisposableEffect` to `close()`
  it. A `LazyColumn` with `items(pageCount)`; each item uses `produceState` to render its
  page at the current container width and shows a placeholder/spinner until ready. This fixes
  the eager all-pages allocation and keeps everything off the main thread and leak-free.
- If `PdfDocument` construction throws (corrupt PDF), show a "Could not open datasheet"
  message.

Build gate + unit tests (existing). Commit:
`perf(app): lazy, leak-free, memory-safe PDF rendering`.

---

## Batch 5 — Setup guide, final verification, review

### 5a. Top-level `ComponentScanner/SETUP.md`
A single turnkey guide, in order:
1. Prereqs (Android Studio/JDK17, Node 20, the SDK already installed).
2. Get keys: Anthropic API key; Nexar token (both free-tier links).
3. Backend: `cd backend`, `npm install`, set secrets (local `.dev.vars` for dev OR
   `wrangler secret put` for deploy), `npm test`, `npm run dev` (local) / `npm run deploy`
   (Cloudflare). Note local dev URL `http://localhost:8787` and that a phone needs either a
   deployed URL or the PC's LAN IP (`http://<PC-IP>:8787`).
4. App: put `backend.url=<your backend URL>` in `app/local.properties` (alongside
   `sdk.dir`). `cd app`, `./gradlew assembleDebug`, `./gradlew installDebug`.
5. The ONLY required edits are the two keys (backend) and the one URL (app).
6. Manual device test checklist (single scan, deep scan, shelf scan, datasheet PDF, history).

### 5b. Final verification
- `cd backend && npm test` (expect all pass) — re-confirm backend untouched/green.
- `cd app && ./gradlew testDebugUnitTest assembleDebug` — all unit tests pass, BUILD SUCCESSFUL.

### 5c. Final review
Dispatch a reviewer over the full diff of the night's work for correctness/lifecycle/leaks;
fix any Critical/Important findings; re-verify. Commit docs/fixes.

Commit: `docs: add turnkey SETUP.md for Component Scanner`.
```
