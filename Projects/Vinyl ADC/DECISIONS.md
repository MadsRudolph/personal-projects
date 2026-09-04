# Vinyl ADC product-render decisions

## Source selection and scope

- The repository checkout contains no loose `*.kicad_pcb`, `*.kicad_sch`, project README, or build README. `Get-ChildItem -Recurse -Filter *.kicad_pcb` therefore returned no result at the repository level. The actual KiCad sources are preserved in KiCad's own backup archives and were read from temporary extraction directories; no KiCad source file was changed.
- `hardware/kicad/vinyl_adc-backups/vinyl_adc-2026-08-23_185144.zip` describes the complete modular design: a channel board built twice, a common board, and a digital board. The schematic title is **“Discrete 3rd-order delta-sigma vinyl ADC - stereo, 48 kHz.”** The channel connector values are `LINE IN L` and `LINE IN R`; the design does not identify them as phono-level inputs.
- The product enclosure and the required singular board export use `vinyl_adc_digital.kicad_pcb` from the newer `hardware/kicad/digital/vinyl_adc_digital-backups/vinyl_adc_digital-2026-09-03_225821.zip`. This is the newest routed board source, it has the only explicit enclosure-ready M3 hole pattern, and it supersedes the older digital-board snapshot. The enclosure is consequently a housing for the digital PCB module rather than an invented single-PCB integration of the older four-board system.
- The digital PCB edge cuts run from `(20.000, 20.000)` to `(120.000, 120.000)` in KiCad coordinates: **100.0 × 100.0 mm**, **1.6 mm** thick.
- The only design-derived sample-rate value is **48 kHz**. A finished PCM word length/bit depth is not specified, so the site says **TBD**. The converter topology is described as third-order delta-sigma, but that is not presented as an invented PCM bit depth.
- RCA, USB, a dedicated power inlet, panel switches, and LEDs do not occur on the selected PCB or in the archived top-level schematic. They were not invented. The digital board has a top-entry 8-pin `TO PI GPIO` header, a top-entry 2×8 `BUS` header, and an internal 1×3 `CLK SEL` jumper. The older channel boards use 2-pin terminal blocks for line input.

## Enclosure geometry

- Material/presentation choice: **warm graphite matte PLA**, with soft render-only edge radii. The manufacturing STLs deliberately omit cosmetic bevel modifiers so boolean boundaries remain simple and slicer-stable.
- Side clearance is **0.5 mm per board side**. The internal plan is therefore 101.0 × 101.0 mm. With **3.0 mm walls**, external plan dimensions are **107.0 × 107.0 mm**.
- The base is 18.0 mm tall with a 3.0 mm floor. The lid plate is 3.0 mm thick; assembled exterior height is **21.0 mm**. Its 2.0 mm locating lip sits inside the base and does not add to the assembled height.
- The board underside is 8.0 mm above the enclosure bottom: 3.0 mm floor plus 5.0 mm standoffs. Bosses are 7.0 mm diameter, bored 3.2 mm for M3 clearance. The hole coordinates checked against the PCB were:

  | Ref | KiCad X | KiCad Y | Enclosure-local X | Enclosure-local Y |
  | --- | ---: | ---: | ---: | ---: |
  | H1 | 26.000 | 26.000 | -44.000 | 44.000 |
  | H2 | 114.000 | 26.000 | 44.000 | 44.000 |
  | H3 | 26.000 | 114.000 | -44.000 | -44.000 |
  | H4 | 114.000 | 114.000 | 44.000 | -44.000 |

- KiCad positive Y is converted to Blender local Y with `local_y = 70 - kicad_y`; local X is `kicad_x - 70`.
- Connector positions/orientations and corresponding lid access checked against the PCB:

  | Ref / function | KiCad centre (mm) | Rotation | Local centre (mm) | Access |
  | --- | --- | ---: | --- | --- |
  | J2 / TO PI GPIO | (60.220, 115.600) | +90° | (-9.780, -45.600) | 22.5 × 5.8 mm lid slot |
  | J4 / 2×8 BUS | (78.890, 30.000) | -90° | (8.890, 40.000) | 22.5 × 5.8 mm lid slot |
  | J1 / CLK SEL | (32.3525, 49.9075) | 180° | (-37.6475, 20.0925) | no cutout; internal configuration jumper |

- J2 and J4 are vertical/top-entry footprints. Their openings are therefore directly above them in the lid, not incorrectly placed in a side wall. The “front” render looks across the front edge toward these labelled top-access interfaces. No side-facing connector exists on the selected PCB.
- Both parts are intended to print without supports. The base prints on its floor with the cavity open upward. The exported lid has its broad exterior face at Z=0 and its locating lip upward. The access slots are vertical through-cuts and create no suspended geometry.

## Board models and render proxies

- `hardware/export/vinyl-adc-board.step` is a real KiCad CLI export with board body, tracks, pads, zones, soldermask, silkscreen, and components. All 13 populated footprints in the selected board reference an installed KiCad STEP model, and KiCad completed the export without a missing-model warning. **No placeholder was required in the STEP deliverable.**
- Blender 4.4 does not natively import STEP, and no STEP-import add-on was assumed. The presentation scene therefore uses a scripted visual proxy tied to the PCB footprint centres. These are render proxies, not replacements inside the KiCad STEP. Every proxy reference is listed here: `U3`, `U4`, `U6`, `U8`, `X1`, `C9`, `C10`, `C11`, `C13`, `C15`, `J1`, `J2`, and `J4`.
- Proxy heights are deliberately plausible and conservative: DIP bodies 4.1 mm above the package base; oscillator body 4.8 mm; disc-cap bodies 4.8 mm; vertical header pins 13.5 mm above the PCB so the accessible pins pass through the lid slots. Exact manufactured part numbers/heights are not present in the repository, so the proxies must not be used for tolerance-critical mechanical checking. The KiCad STEP remains the component-geometry source.
- The render engine is Blender Eevee Next at 1920 × 1080 PNG. A dark neutral studio, scale-independent sun lights, and matte PLA/PCB/metal materials were chosen for predictable headless reproduction.

## Tools found and fallbacks

- The initial required PATH lookup found only `python.exe` at `C:\Users\Mads2\AppData\Local\Microsoft\WindowsApps\python.exe` (a Windows app execution alias; it was not needed).
- `kicad-cli` was not on PATH. The requested typical KiCad 9 path was absent. The installed executable used was `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`, version 10.0.4.
- `blender` was not on PATH. Blender was found at both `C:\Program Files\Blender Foundation\Blender 4.4\blender.exe` and `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`. Version 4.4.3 was used for stable script/API behaviour.
- `openscad` was neither on PATH nor present at `C:\Program Files\OpenSCAD\openscad.exe`. Blender Python was selected for the parametric enclosure.
- A callable Blender MCP endpoint was not exposed in this session, so the documented headless-Blender fallback was used.
- An initial loose-file scan did not locate a PCB because the sources are archived. The fallback was to inspect both KiCad backup ZIPs and extract them to a temporary directory using PowerShell `Expand-Archive`.

## Verification results

- KiCad STEP export completed successfully; the resulting populated STEP is non-empty.
- Blender re-imported both STL files and checked every edge with BMesh:
  - `vinyl-adc-base.stl`: 107.0 × 107.0 × 18.0 mm; 0 boundary edges; 0 non-manifold edges; positive volume 53,578.513 mm³.
  - `vinyl-adc-lid.stl`: 107.0 × 107.0 × 5.0 mm in print orientation (3.0 mm plate + 2.0 mm inward lip); 0 boundary edges; 0 non-manifold edges; positive volume 34,675.038 mm³.
- The three render images and the three copies under `site/assets` decode as PNGs at exactly 1920 × 1080.
- `site/index.html` uses only relative local image paths, inline CSS, system fonts, and no scripts/CDNs. All referenced image files were path-checked and decoded. A headless local-browser screenshot was also used to check the finished offline page at desktop width; the result is intentionally not committed.

## Reproduction from a clean checkout (PowerShell)

Run these commands from the `Vinyl ADC` directory in PowerShell:

```powershell
$ErrorActionPreference = 'Stop'
$kicad = 'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
$blender = 'C:\Program Files\Blender Foundation\Blender 4.4\blender.exe'
$extract = Join-Path $env:TEMP 'vinyl-adc-render-source'

New-Item -ItemType Directory -Path $extract -Force | Out-Null
Expand-Archive -LiteralPath 'hardware\kicad\digital\vinyl_adc_digital-backups\vinyl_adc_digital-2026-09-03_225821.zip' -DestinationPath $extract -Force
New-Item -ItemType Directory -Path 'hardware\export' -Force | Out-Null

& $kicad pcb export step --force --subst-models --include-tracks --include-pads --include-zones --include-silkscreen --include-soldermask --output 'hardware\export\vinyl-adc-board.step' (Join-Path $extract 'vinyl_adc_digital.kicad_pcb')
if ($LASTEXITCODE -ne 0) { throw 'KiCad STEP export failed' }

& $blender -b -P 'render\render.py'
if ($LASTEXITCODE -ne 0) { throw 'Blender generation/render failed' }

& $blender -b -P 'enclosure\verify.py'
if ($LASTEXITCODE -ne 0) { throw 'STL manifold verification failed' }
```

`render/render.py` regenerates both STLs, all three PNGs, `render/vinyl-adc.blend`, and the local gallery copies under `site/assets`.

To verify the offline site references and optionally open it:

```powershell
$site = (Resolve-Path 'site\index.html').Path
$html = Get-Content -LiteralPath $site -Raw
$sources = [regex]::Matches($html, '<img[^>]+src="([^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
foreach ($source in $sources) {
    $asset = Join-Path (Split-Path $site) $source
    if (-not (Test-Path -LiteralPath $asset)) { throw "Missing site image: $source" }
}
Start-Process $site
```
