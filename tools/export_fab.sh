#!/usr/bin/env bash
# Regenerate everything in fab/ (and the renders / netlist / schematic PDF in kicad/) from the KiCad project.
# Run from Git Bash:  bash tools/export_fab.sh
set -euo pipefail
cd "$(dirname "$0")/.."
K="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
SCH=kicad/bolty-mood-module.kicad_sch
PCB=kicad/bolty-mood-module.kicad_pcb
N=bolty-mood-module

rm -rf fab/gerbers && mkdir -p fab/gerbers
"$K" pcb export gerbers --layers "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts" \
     --use-drill-file-origin -o fab/gerbers/ "$PCB"
"$K" pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 \
     -o fab/gerbers/ "$PCB"
(cd fab/gerbers && rm -f ../$N-gerbers.zip && powershell -NoProfile -Command \
     "Compress-Archive -Path * -DestinationPath ..\\$N-gerbers.zip -Force")

"$K" pcb export pos --format csv --units mm --side both -o fab/$N-positions.csv "$PCB"
"$K" sch export bom --fields 'Reference,Value,Footprint,Manufacturer,Part Number,${QUANTITY}' \
     --labels 'Reference,Value,Footprint,Manufacturer,Part Number,Qty' \
     --group-by 'Value,Footprint,Part Number' --exclude-dnp -o fab/$N-bom-kicad.csv "$SCH"
"$K" sch export pdf -o fab/$N-schematic.pdf "$SCH"
cp fab/$N-schematic.pdf kicad/$N.pdf
"$K" sch export netlist -o kicad/$N.net "$SCH"
"$K" pcb export pdf --layers "B.Fab,B.Silkscreen,Edge.Cuts" --mode-single --mirror -o fab/assembly-back.pdf "$PCB"
"$K" pcb export pdf --layers "F.Fab,F.Silkscreen,Edge.Cuts" --mode-single -o fab/assembly-front.pdf "$PCB"
"$K" pcb export step --subst-models --force -o fab/$N.step "$PCB"
"$K" pcb render --side top --quality high -w 1600 -h 1600 -o kicad/render_front.png "$PCB"
"$K" pcb render --side bottom --quality high -w 1600 -h 1600 -o kicad/render_back.png "$PCB"
echo "fab outputs regenerated"
