# Bolty Mood Module — Journal

> I joined Half Life 5 weeks late, so this entry catches up on the earlier weeks' work (schematic + PCB design).
> I designed this with an AI assistant (Claude Code). Below I say clearly what I decided and what the AI did.
> Time below is my own time at the computer; no Lapse recording was made for these sessions.

---

## Entry 1 — Catch-up: schematic + PCB design (2026-11-15 → 2026-11-16)

**Time spent:** ___ h (fill in honestly from Hackatime / your own notes)

### What the board is
A small round, 2-layer face module for my Bolty robot. An ATtiny85 drives 12 RGB LEDs (two 3×2 "eyes"),
a buzzer and a pat button, and listens to the main robot over I2C at address `0x42`.

### What I did
- Came up with the Bolty Mood Module idea and the part choices in `DESIGN.md` (ATtiny85, SK6812MINI-E LEDs,
  buzzer, button, JST-PH I2C connector, $30 Tier 1 budget). *(edit if the AI wrote parts of DESIGN.md)*
- Installed KiCad 10 and freed ~25 GB on my C: drive to make room (moved Arduino data to H:, cleared caches).
- Made the design decisions when problems came up:
  - The 6-LED **ring** eyes didn't fit — each SK6812MINI-E footprint is 6.8 mm long. I chose **3×2 grid eyes**.
  - Even grids didn't fit on **30 mm** (parts needed ~675 mm², only ~660 mm² usable), so I chose to grow the board to **40 mm**.
  - Approved downloading the Freerouting autorouter.
- Reviewed the schematic PDF and the 3D renders.

### What the AI (Claude Code) did
- Wrote Python scripts that generated the KiCad schematic from my DESIGN.md, then checked it with ERC (0 errors)
  and compared the netlist pin-by-pin against the design.
- Found that KiCad's built-in SK6812MINI symbol has a different pin order than the MINI-E, and made a custom
  `Bolty:SK6812MINI-E` symbol (checked against the datasheet: 1 VDD, 2 DOUT, 3 GND, 4 DIN).
- Read the buzzer datasheet to find which pads are + / − (pad 1 +, pad 2 −, pads 3/4 dummy).
- Placed all parts on the 40 mm board, added GND pours, ran Freerouting, then fixed DRC problems
  (GND pads not reached by the pour, tracks too close to the LED cut-outs, thin track pieces).
- Final DRC: 0 electrical errors, 0 unconnected, 0 schematic mismatches.

### Problems & what I learned
- **Footprints are bigger than parts.** The LED body is 3.2 × 2.8 mm, but its pads make it 6.8 mm long, which killed the ring layout.
- **Check area before layout.** Adding up courtyard areas showed 30 mm was impossible before any routing.
- **Symbols can lie.** Similar parts (SK6812MINI vs MINI-E) can have different pinouts. Always check the datasheet.
- **Copper pours don't fix everything.** Between tightly packed parts the GND pour breaks into islands, so GND needed real traces.
- **Reverse-mount LEDs** sit on the back and shine through a hole, so the front face stays clean.

### Pictures
- Schematic: `kicad/bolty-mood-module.pdf`
- Front render: `kicad/render_front.png`
- Back render: `kicad/render_back.png`

### Next
Order the PCBs and parts, solder the board, program the ATtiny85 and test it (Build your PCB week).
