# Bolty Mood Module — PCB Design Pack

Round 40 mm, 2-layer board. ATtiny85 drives 12 RGB LEDs (two eyes), a buzzer and a pat button. Talks to the main Bolty controller over I2C at address `0x42`.

Tool: **KiCad 10** (free, https://www.kicad.org/download/). Project files: `kicad/`. Start Lapse before every session.

---

## 1. Schematic (net by net)

### ATtiny85-20SU pinout (SOIC-8)

| Pin | Name | Net | Connects to |
|---|---|---|---|
| 1 | PB5 / RESET | `RST` | 10k pull-up to `+5V`, ISP pad RST |
| 2 | PB3 | `BTN` | Button → `GND` (internal pull-up in firmware; 10k pull-up optional) |
| 3 | PB4 | `BUZ` | 1k resistor → base of Q1 |
| 4 | GND | `GND` | Ground |
| 5 | PB0 | `SDA` | J1 pin 4, ISP pad MOSI, 4.7k pull-up (DNP) |
| 6 | PB1 | `LED_RAW` | 330 Ω resistor → `LED_DIN` (first LED DIN), ISP pad MISO |
| 7 | PB2 | `SCL` | J1 pin 3, ISP pad SCK, 4.7k pull-up (DNP) |
| 8 | VCC | `+5V` | 100 nF to GND, placed right at the pin |

### Connector J1 (JST-PH 4-pin)

| Pin | Net |
|---|---|
| 1 | `GND` |
| 2 | `+5V` |
| 3 | `SCL` |
| 4 | `SDA` |

10 µF bulk capacitor across `+5V`/`GND` next to J1.

### LEDs D1–D12 (SK6812MINI-E)

- Daisy chain: `LED_DIN` → D1 DIN, D1 DOUT → D2 DIN, … D11 DOUT → D12 DIN. D12 DOUT unconnected.
- D1–D6 = left eye, D7–D12 = right eye. Each eye is a 3 × 2 grid (rings of 6 don't fit: each SK6812MINI-E footprint is 6.8 mm long).
- Chain snakes through the columns: left eye D1 top-left ↓ D2, D3 ↑ D4, D5 ↓ D6; right eye D7 bottom-left ↑ D8, D9 ↓ D10, D11 ↑ D12.
- Pinout (datasheet): 1 VDD, 2 DOUT, 3 GND, 4 DIN. KiCad's `LED:SK6812MINI` symbol uses a different order, so the project uses its own `Bolty:SK6812MINI-E` symbol.
- Every LED: VDD to `+5V`, GND to `GND`. One 100 nF cap per column (C3–C8, 6 total), sitting between the column's two LEDs.

### Buzzer driver

- Q1 MMBT3904: base ← 1k ← `BUZ`, emitter → `GND`, collector → buzzer (−).
- Buzzer (+) → `+5V`.
- D13 (1N4148W) across the buzzer: cathode to `+5V`, anode to collector. Stops voltage spikes.

### Pat button

- SW1 6×6 mm tactile: one side `BTN`, other side `GND`.

### ISP programming pads (2×3, bottom side)

```
MISO(PB1)  +5V
SCK(PB2)   MOSI(PB0)
RST        GND
```
Unplug J1 while programming: SDA/SCL share the ISP pins.

---

## 2. BOM

Prices are rough estimates — check DigiKey/Mouser before ordering. Need 3–5 boards' worth of spares for small parts.

| Ref | Qty | Part | Package | Example MPN | ~USD each |
|---|---|---|---|---|---|
| U1 | 1 | ATtiny85 MCU | SOIC-8 | ATtiny85-20SU | 1.50 |
| D1–D12 | 12 | RGB LED, addressable | 3.2×2.8 mm reverse-mount | SK6812MINI-E | 0.20 |
| Q1 | 1 | NPN transistor | SOT-23 | MMBT3904LT1G | 0.10 |
| D13 | 1 | Diode | SOD-123 | 1N4148W | 0.10 |
| BZ1 | 1 | Magnetic buzzer, 5 V, externally driven | SMD 8.5 × 8.5 mm | CMT-8504-100-SMT-TR (pad 1 +, pad 2 −, pads 3/4 dummy) | 1.00 |
| SW1 | 1 | Tactile switch | 6×6 mm SMD | any 6×6 SMD | 0.20 |
| J1 | 1 | JST-PH 4-pin header, vertical | THT | B4B-PH-K-S | 0.20 |
| C1 | 1 | 10 µF ceramic, 10 V+ | 0805 | — | 0.10 |
| C2–C8 | 7 | 100 nF ceramic | 0603 | — | 0.02 |
| R1 | 1 | 10k (RESET pull-up) | 0603 | — | 0.02 |
| R2 | 1 | 1k (Q1 base) | 0603 | — | 0.02 |
| R3 | 1 | 330 Ω (LED data) | 0603 | — | 0.02 |
| R4, R5 | 2 | 4.7k (I2C pull-ups, DNP) | 0603 | — | 0.02 |
| H1, H2 | 2 | M2 mounting holes | 2.2 mm NPTH | — | — |
| PCB | 3 | 40 mm round, 2-layer | — | OSH Park / JLCPCB | ~10 total |

**Estimated total: ~$15–20 for parts + PCBs** (inside Tier 1's $30). Add a JST-PH 4-pin cable.

Why SK6812MINI-E and not WS2812B-2020: the MINI-E has legs you can hand-solder with an iron. The 2020 needs a hot plate.

---

## 3. Layout & routing

**Board outline:** circle, 40 mm diameter, on `Edge.Cuts`.

**Front (F.Cu):** the face. Keep it clean: only SW1 here, at the bottom centre ("chin") or top ("head pat"), plus silkscreen art.

**Back (B.Cu):** everything else — LEDs, U1, Q1, D13, buzzer, J1, passives, ISP pads.
- SK6812MINI-E is reverse-mount: it sits on the back and shines forward through a hole in the board. Use a KiCad footprint that includes the hole.
- Two eye grids (3 columns × 2 rows), centres 7 mm left/right of board centre, 5 mm above middle. Column pitch 4.3 mm, row pitch 9.4 mm.
- ISP: bare 2×3 pads (`Bolty:ISP_Pads_2x3_P2.54mm`) for a pogo-pin clip.

**Rules:**
1. Fill both layers with a `GND` zone. Stitch with vias every ~5 mm.
2. `+5V` traces 0.5 mm wide. Signal traces 0.25 mm.
3. Each 100 nF cap within 2 mm of its LED pair / U1 VCC pin.
4. Keep the LED data chain short and in order: D1→D6, then hop to D7→D12.
5. J1 at the board edge, pointing out.
6. 2 × M2 mounting holes (H1/H2), either side of the eyes.
7. Run DRC with the fab's rules (OSH Park: 6 mil trace / 6 mil space / 10 mil drill min).

**Silkscreen:** board name, your handle, `I2C 0x42`, pin labels on J1 and ISP pads, a tiny Bolty logo.

---

## 4. Firmware plan (for later)

- Arduino IDE + ATTinyCore, 8 MHz internal clock.
- LEDs: `tinyNeoPixel` (in ATTinyCore). Index 0–11 = D1–D12; map grid (x, y) to index using the snake order above. Brightness cap 25 % (12 LEDs at full white ≈ 600 mA).
- I2C slave: `Wire` (ATTinyCore) at `0x42`. Command byte: `0` idle, `1` happy, `2` sad, `3` angry, `4` sleepy, `5` surprised.
- Buzzer: `tone()` on PB4.
- No I2C for 3 s → idle blink. Button press → "happy".

---

## 5. Submission checklist

- [ ] Schematic PDF exported
- [ ] PCB 3D render screenshot (front + back)
- [ ] Gerbers zipped
- [ ] BOM as CSV with DigiKey/Mouser links
- [ ] GitHub repo with KiCad files + README
- [ ] Journal entries + Lapse recordings for every session
