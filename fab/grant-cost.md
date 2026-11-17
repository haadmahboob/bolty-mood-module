# 8-Pin Grant cost estimate

Prices are DigiKey list prices checked on 2026-11-17 (quantity 1 unless noted). Some are estimates, marked ~.
The KiCad BOM export (`bolty-mood-module-bom-kicad.csv`) has a `Part Number` column with the manufacturer
part numbers below, ready to upload to DigiKey's BOM manager.

**Request: parts for 2 assemblies + 1 OSH Park order (3 boards).**

| Ref | Part Number | Qty for 2 boards | Unit | Total |
|---|---|---|---|---|
| U1 | ATTINY85-20SU | 2 | $1.50 | $3.00 |
| D1–D12 | Adafruit 4960 (10× SK6812MINI-E) | 3 packs (30 LEDs, 24 used) | $2.95 | $8.85 |
| BZ1 | CMT-8504-100-SMT-TR | 2 | ~$1.60 | $3.20 |
| SW1 | PTS645SM43SMTR92 LFS | 2 | $0.36 | $0.72 |
| J1 | B4B-PH-K-S(LF)(SN) | 2 | ~$0.21 | $0.42 |
| Q1 | MMBT3904LT1G | 2 | ~$0.16 | $0.32 |
| D13 | 1N4148W-7-F | 2 | ~$0.13 | $0.26 |
| C1 | CL21A106KAYNNNE | 2 | ~$0.10 | $0.20 |
| C2–C8 | CL10B104KB8NNNC | 14 | ~$0.03 | $0.42 |
| R1 | RC0603FR-0710KL | 2 | ~$0.10 | $0.20 |
| R2 | RC0603FR-071KL | 2 | ~$0.10 | $0.20 |
| R3 | RC0603FR-07330RL | 2 | ~$0.10 | $0.20 |
| R4, R5 | RC0603FR-074K7L | 0 (do not place) | | $0.00 |
| | **Parts subtotal** | | | **~$18.00** |
| PCB | OSH Park 2-layer, 40 × 40 mm = 2.48 in² × $5 | 3 boards | | **$12.40** |
| | **Total** | | | **~$30.40** |

3 assemblies would be about $39, which is over the $35 limit, so this asks for 2.
Programming: ISP (USBasp or Arduino-as-ISP) through the 2×3 pads on the back.
