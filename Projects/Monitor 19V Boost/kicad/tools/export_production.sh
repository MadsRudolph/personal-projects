#!/bin/sh
# Production files for the CNC mill (and the laser silkscreen), Linux port of
# the kicad-laser-pcb skill's export_production.ps1.
#
#   sh kicad/tools/export_production.sh            (from the project root)
#
# production/gerbers/   copper + edge cuts + Excellon drill -> FlatCAM / CAM.
#                       Isolate B.Cu with the 0.8 mm end mill; do NOT pre-mirror,
#                       the CAM mirrors when you flip the board.
# production/*_silk_top.dxf   silkscreen for the xTool laser, top side, not mirrored.
# production/*.dxf / *_top_cu.dxf   copper outlines, a visual check only.
set -e
cd "$(dirname "$0")/.."
PCB=monitor-boost.kicad_pcb
B=monitor-boost
OUT=production
mkdir -p "$OUT/gerbers"
kicad-cli pcb export gerbers -l "F.Cu,B.Cu,Edge.Cuts,B.Mask,F.Mask,F.Silkscreen,F.Fab" -o "$OUT/gerbers/" "$PCB" >/dev/null
kicad-cli pcb export drill --format excellon -o "$OUT/gerbers/" "$PCB" >/dev/null
kicad-cli pcb export dxf --mode-single -l "F.Silkscreen,Edge.Cuts" --ou mm --drill-shape-opt 0 -o "$OUT/${B}_silk_top.dxf" "$PCB" >/dev/null
kicad-cli pcb export dxf --mode-single -l "B.Cu,Edge.Cuts" --ou mm --drill-shape-opt 1 -o "$OUT/$B.dxf" "$PCB" >/dev/null
kicad-cli pcb export dxf --mode-single -l "F.Cu,Edge.Cuts" --ou mm --drill-shape-opt 1 -o "$OUT/${B}_top_cu.dxf" "$PCB" >/dev/null
TOP=$(grep -A6 '(segment' "$PCB" | grep -c '(layer "F.Cu")' || true)
DRILLS=$(grep -o '(drill [0-9.]*)' "$PCB" | sort -u | sed 's/(drill \(.*\))/\1/' | tr '\n' ' ')
echo "$B: gerbers + drill (CAM) and ${B}_silk_top.dxf (laser) in $OUT/"
echo "  F.Cu segments (wire links to solder on top): $TOP"
echo "  drill sizes present: $DRILLS mm"
echo "  CAM: isolate B.Cu with the 0.8 mm end mill; do NOT pre-mirror."
