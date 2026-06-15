# Component Scanner — Android App

Point the camera at an electronic component; the app reads the marking (on-device OCR,
with a cloud fallback through the backend), resolves the datasheet, and shows it as an
in-app scrollable PDF. Scans are saved to history.

## Requirements
- Android Studio (JDK 17+), Android SDK 34, a device/emulator with a camera (API 26+).
- The Component Scanner backend deployed (see `../backend/README.md`). Set its URL in
  `app/build.gradle.kts` → `BACKEND_BASE_URL`.

## Build & run
```bash
# the Gradle wrapper is committed; just:
./gradlew assembleDebug          # build the debug APK
./gradlew testDebugUnitTest      # run JVM unit tests
./gradlew installDebug           # install on a connected device
```
`local.properties` must point at your SDK (`sdk.dir=...`); it is git-ignored.
On this machine, if Gradle can't find a compiler, set `JAVA_HOME` to a JDK 17 install
(e.g. `C:\Program Files\Java\jdk-17`).

## Architecture
MVVM + Hilt. Pure logic (part-number extraction, repositories, view-models, PDF cache)
is JVM-unit-tested with fakes (19 tests). Camera (CameraX), OCR (ML Kit), Room, the PDF
renderer, and Compose UI are verified by compilation and manual device testing.

## Manual device test checklist (Phase 1)
- Grant camera permission; the live preview shows and a "Detected: <part>" chip appears on
  a clear chip marking.
- Tapping the detected part opens the Result screen with manufacturer + key specs.
- "Open datasheet PDF" renders the datasheet, scrollable.
- The scan appears in History; deleting removes it.

## Known Phase-1.x follow-ups
- Manual part-number entry field (nav + Result screen already accept an arbitrary part).
- "Deep scan" high-res capture button wired to `ImageCapture` (the `deepScan` path exists
  and is unit-tested; live OCR drives identification in the MVP).
- Shelf / multi-component scan mode (Phase 2).
- Pinch-zoom in the PDF viewer (currently scroll + fit-width).
- **Fuller OCR normalisation (deferred):** strip date/lot codes and fix common OCR character
  confusions (0/O, 1/I/l, 5/S, 8/B), plus a fuzzy matcher for near-miss part numbers.
  The MVP delegates robust reads to the backend vision model; this refinement is Phase 1.x.
- **Offline banner + retry-with-backoff (deferred):** show a persistent "no connection"
  banner when the backend is unreachable and retry failed requests with exponential
  back-off rather than surfacing a raw error to the user.
- **Lazy per-page PDF rendering with bitmap recycling (deferred):** currently all pages are
  rasterised eagerly on first open. For very large datasheets this can exhaust memory;
  a future pass will render only visible pages and recycle off-screen bitmaps.
