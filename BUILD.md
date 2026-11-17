# Bolty Mood Module — Build Guide (order → solder → program → test)

Everything you need is in this folder:

| File | What it's for |
|---|---|
| `fab/bolty-mood-module-gerbers.zip` | Upload to the PCB fab |
| `fab/BOM.csv` | Parts list with buy links |
| `fab/bolty-mood-module-positions.csv` | Part positions (only needed if the fab assembles it) |
| `fab/assembly-back.pdf`, `fab/assembly-front.pdf` | Where every part goes (print these!) |
| `fab/bolty-mood-module-schematic.pdf` | Circuit, for debugging |
| `fab/bolty-mood-module.step` | 3D model, for the robot's head enclosure |
| `firmware/bolty_mood/bolty_mood.ino` | Test firmware |

---

## 1. Order the PCB (JLCPCB)

1. Go to https://jlcpcb.com → **Order now** → **Add gerber file** → upload `fab/bolty-mood-module-gerbers.zip`.
2. It should detect **2 layers, 40 × 40 mm**. Settings:
   - Base material **FR-4**, thickness **1.6 mm**, quantity **5** (minimum).
   - PCB color: **black** or **white** looks best for a face (traces show less than on green).
   - Surface finish: **HASL lead-free** (or ENIG if cheap; nicer for the tiny LED pads).
   - Leave everything else default. "Remove order number": pick *Specify a location* or pay to remove it, or it gets printed somewhere on the face.
3. Check the online Gerber viewer: round board, 12 square LED windows, 2 mounting holes, 4 connector holes at the top.
4. Hack Club grant: order with the grant card / follow the 8-pin / Half Life instructions for paying.

> OSH Park also works: upload the same zip. It's purple, ~$10 for 3 boards, no minimum colour choice.

## 2. Order the parts

Use `fab/BOM.csv`. Buy **spares**: +3 LEDs, +5 of each 0603 part. Tiny parts get lost.
- LEDs (SK6812MINI-E, LCSC `C5149201`) and the switch (LCSC `C319409`) are easiest from LCSC (can ship with the JLCPCB order).
- Everything else: DigiKey / Mouser / LCSC.
- **Don't buy R4/R5** unless your main robot has no I2C pull-ups (most Arduino/ESP boards do).
- You also need: a JST-PH 4-pin cable, and a way to program: **USBasp** (~$5) *or* an **Arduino Uno** as "Arduino as ISP", plus a **2×3 pogo-pin clip** (2.54 mm) or 6 thin wires.

## 3. Tools

Fine-tip soldering iron (~330 °C), thin solder (0.5 mm) or solder paste, **flux** (important), tweezers,
solder wick, multimeter, magnifier / phone camera zoom. Optional: hot-air or hot plate (not needed).

## 4. Solder it — in this order

**Which side?** Almost everything goes on the **BACK** (the side with `BOLTY`, `0x42`, `U1`, `BZ1` printed).
The **FRONT** is the face: only the button SW1 goes there, plus J1's pins poke through.

Rule: solder **small and flat first, tall last**. After each step, look for bridges with magnification.

| Step | Part(s) | Side | Watch out for |
|---|---|---|---|
| 1 | **U1** ATtiny85 | back | **Dot = pin 1** → match the dot/triangle mark on the silkscreen. Tack one corner pin, check alignment, then the rest. Use flux, wick away bridges. |
| 2 | **C2** 100 nF (next to U1), **R1** 10k, **R3** 330 Ω | back | Resistors: 10k = `103` / `01C`, 330 Ω = `331` / `51A`. Caps aren't marked: keep them in their tape until placed. |
| 3 | **Q1** MMBT3904, **R2** 1k | back | Q1 is SOT-23: 1 pin on one side, 2 on the other: matches the footprint only one way. |
| 4 | **D13** 1N4148W | back | **Stripe = cathode = pad 1 (+5V).** Match the bar on the silkscreen outline. Wrong way = +5V shorted through Q1 when the buzzer beeps. |
| 5 | **C1** 10 µF, **C3–C8** 100 nF (the small caps between the LED rows) | back | C3–C8 sit very close to LED pads: small solder blobs only. |
| 6 | **D1–D12** SK6812MINI-E LEDs | back | See LED notes below. |
| 7 | **BZ1** buzzer | back | Pad 1 (+) is marked. Solder all 4 pads (2 are dummy, they just hold it). |
| 8 | **SW1** button | **front** | Centered on the chin. |
| 9 | **J1** JST connector | body on **back**, solder pins on **front** | Opening faces the board edge. Solder from the face side. |

### LED notes (most important step)
- The SK6812MINI-E is **reverse-mount**: the LED body drops **into the square hole** from the back, the lens faces out the front, and its 4 legs lie on the back pads.
- **Orientation:** the LED has a marked pin 1 (VDD). The footprint's pin-1 corner has a **small triangle** on the back silkscreen (see `assembly-back.pdf`). **Before soldering, check the LED's pin-1 mark against the datasheet drawing** (https://www.lcsc.com/datasheet/C5149201.pdf) so you know which corner it is. All 12 must match. One backwards LED breaks the chain from that LED onward.
- They're heat-sensitive: ≤ 3 s per pad, iron ≤ 330 °C. Do one leg, check it sits flat, then the other three.
- Order: D1 → D12 is the data chain. Snake order (seen from the front):
  - Left eye: D1 top-left, D2 below it; D3 bottom-middle, D4 above; D5 top-right, D6 below.
  - Right eye: D7 bottom-left, D8 above; D9 top-middle, D10 below; D11 bottom-right, D12 above.

## 5. Check before power (5 minutes, saves boards)

With the multimeter on continuity/resistance:
1. **+5V to GND must NOT beep.** Measure between J1 pin 1 (GND) and pin 2 (+5V). Should read > 1 kΩ (rises as caps charge). A beep = short → find the bridge before going on.
2. Look at every U1 pin and every LED leg under magnification.

First power-up: use a **current-limited** supply set to **5 V, 100 mA** if you have one (or a USB port through a USB-to-pins adapter). Without firmware it should draw only a few mA. If it hits the limit, unplug and look for shorts.

## 6. Program the ATtiny85

1. Install **Arduino IDE** (or arduino-cli) and the **ATTinyCore** board package:
   - File → Preferences → Additional boards manager URLs → add `http://drazzy.com/package_drazzy.com_index.json`
   - Tools → Board → Boards Manager → install **ATTinyCore**.
2. Tools settings: Board **ATtiny25/45/85 (No bootloader)**, Chip **ATtiny85**, Clock **8 MHz (internal)**, Programmer **USBasp** (or **Arduino as ISP**).
3. **Unplug J1** (SDA/SCL share the programming pins).
4. Hold the pogo clip on the 6 ISP pads on the back (pad labels: MISO, VCC, SCK, MOSI, RST, GND; the **square pad is MISO = pin 1**).
   Wiring to a USBasp 10-pin / Arduino-as-ISP:
   | Pad | USBasp | Arduino Uno as ISP |
   |---|---|---|
   | MISO | MISO | D12 |
   | VCC | VCC (5 V) | 5V |
   | SCK | SCK | D13 |
   | MOSI | MOSI | D11 |
   | RST | RST | D10 |
   | GND | GND | GND |
5. **Tools → Burn Bootloader** once (this only sets the 8 MHz fuses).
6. Open `firmware/bolty_mood/bolty_mood.ino` → **Sketch → Upload Using Programmer**.

## 7. Test

On power-up the firmware runs a self-test:
1. **Beep** (4 kHz): buzzer, Q1, R2, D13 OK.
2. One LED at a time **D1 → D12 in red**, then green, then blue.
   - Stops at some LED → that LED (or the one before it) is backwards, not flat, or has a bad DIN/DOUT joint.
   - Wrong colour order everywhere → nothing wrong with the board; change `NEO_GRB` in the sketch.
3. Then both eyes show **idle blue** and blink every 3 s.
4. Press the **button** → green "happy" + chirp.
5. **I2C test** from the main robot (or any Arduino): connect J1 (GND, +5V, SCL, SDA) and send one byte to address `0x42`:
   ```cpp
   Wire.beginTransmission(0x42); Wire.write(3); Wire.endTransmission();  // 3 = angry (red)
   ```
   Moods: 0 idle, 1 happy, 2 sad, 3 angry, 4 sleepy, 5 surprised.

### Troubleshooting
| Symptom | Check |
|---|---|
| Programmer says "target doesn't answer" / signature 0x000000 | J1 unplugged? Clip pressed evenly? U1 pin 1 orientation? R1 + RST pad soldered? |
| No beep, LEDs OK | D13 direction, Q1 pins, R2, buzzer pads 1 & 2 |
| No LEDs at all | R3 joint, D1 orientation, +5V reaching D1 VDD |
| Board resets when LEDs go bright | Power supply too weak: brightness is capped at 25 % (`BRIGHTNESS 64`) for this reason |
| I2C does nothing | Main board needs pull-ups on SDA/SCL (or fit R4/R5 4.7k); check SDA/SCL not swapped |

## 8. Hack Club submission checklist

- [ ] Photos: bare PCB front/back, assembled front/back, LEDs lit (video of the self-test is great)
- [ ] Journal entry for the build (time, what went wrong, how you fixed it). Be honest about AI help
- [ ] Lapse recording of your soldering sessions if your program requires it
- [ ] Push this folder to GitHub (KiCad files, fab/, firmware/, README)
