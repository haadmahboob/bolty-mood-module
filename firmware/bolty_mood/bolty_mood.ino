// Bolty Mood Module firmware — first bring-up + test version.
// Board: ATtiny85 @ 8 MHz internal (ATTinyCore: "ATtiny25/45/85 (No bootloader)",
//        Clock "8 MHz (internal)", LTO enabled). Burn Bootloader once to set fuses.
// Program over the 2x3 ISP pads with a USBasp or "Arduino as ISP". Unplug J1 first.
//
// Pins (ATTinyCore numbering = PBx):
//   PB0 SDA, PB2 SCL  -> I2C slave at 0x42
//   PB1 LED data      -> D1..D12 SK6812MINI-E chain (through R3 330R)
//   PB3 button (SW1)  -> to GND, internal pull-up
//   PB4 buzzer        -> Q1 base through R2 1k
//
// On power-up it runs a self-test: beep, then lights every LED in chain order
// (D1..D12) red, green, blue. If the walk stops at some LED, check that LED and the
// one before it (DOUT -> DIN).
//
// I2C protocol: master writes one byte: 0 idle, 1 happy, 2 sad, 3 angry, 4 sleepy, 5 surprised.
// No I2C byte for 3 s -> idle blink. Button press -> happy + chirp.

#include <tinyNeoPixel.h>
#include <Wire.h>

#define PIN_LED  PIN_PB1
#define PIN_BTN  PIN_PB3
#define PIN_BUZ  PIN_PB4
#define NUM_LEDS 12
#define I2C_ADDR 0x42
#define BRIGHTNESS 64   // ~25 %: 12 LEDs at full white would draw ~600 mA

tinyNeoPixel strip(NUM_LEDS, PIN_LED, NEO_GRB + NEO_KHZ800);

// Grid as seen from the FRONT: 6 columns (0-2 left eye, 3-5 right eye) x 2 rows (0 top).
// The data chain snakes up/down the columns, so map (col,row) -> chain index.
const uint8_t LED_AT[6][2] = {
  {0, 1}, {3, 2}, {4, 5},     // left eye:  D1/D2, D4/D3, D5/D6
  {7, 6}, {8, 9}, {11, 10},   // right eye: D8/D7, D9/D10, D12/D11
};

enum Mood : uint8_t { IDLE, HAPPY, SAD, ANGRY, SLEEPY, SURPRISED, MOOD_COUNT };

// Per mood: which of the 3x2 cells light in ONE eye (bit = col*2 + row), mirrored to the other eye.
//   bit layout:  col0 col1 col2
//        top      0    2    4
//        bottom   1    3    5
const uint8_t MOOD_SHAPE[MOOD_COUNT] = {
  0b111111,  // IDLE: full eye
  0b100101,  // HAPPY: ^ shape (outer bottoms, middle top)
  0b010010,  // SAD: middle bottom + outer tops... drooping
  0b011001,  // ANGRY: slanted
  0b101010,  // SLEEPY: bottom row only
  0b111111,  // SURPRISED: full, bright
};
const uint32_t MOOD_COLOR[MOOD_COUNT] = {
  0x0040FF,  // idle blue
  0x00FF40,  // happy green
  0x2020FF,  // sad dim blue
  0xFF0000,  // angry red
  0x804000,  // sleepy amber
  0xFFFFFF,  // surprised white
};

volatile uint8_t pendingMood = 0xFF;
volatile uint32_t lastI2cMs = 0;
uint8_t mood = IDLE;

void onReceive(int count) {
  while (Wire.available()) {
    uint8_t b = Wire.read();
    if (b < MOOD_COUNT) pendingMood = b;
  }
  lastI2cMs = millis();
}

void showMood(uint8_t m, bool on = true) {
  strip.clear();
  if (on) {
    for (uint8_t col = 0; col < 6; col++) {
      uint8_t c = (col < 3) ? col : (5 - col);   // mirror right eye
      for (uint8_t row = 0; row < 2; row++) {
        if (MOOD_SHAPE[m] & (1 << (c * 2 + row))) {
          strip.setPixelColor(LED_AT[col][row], MOOD_COLOR[m]);
        }
      }
    }
  }
  strip.show();
}

void chirp() {
  tone(PIN_BUZ, 2000, 60);
  delay(80);
  tone(PIN_BUZ, 3000, 60);
}

void selfTest() {
  tone(PIN_BUZ, 4000, 150);   // CMT-8504 is loudest near 4 kHz
  delay(200);
  const uint32_t colors[3] = {0xFF0000, 0x00FF00, 0x0000FF};
  for (uint8_t c = 0; c < 3; c++) {
    for (uint8_t i = 0; i < NUM_LEDS; i++) {
      strip.clear();
      strip.setPixelColor(i, colors[c]);
      strip.show();
      delay(120);
    }
  }
  strip.clear();
  strip.show();
}

void setup() {
  pinMode(PIN_BTN, INPUT_PULLUP);
  pinMode(PIN_BUZ, OUTPUT);
  digitalWrite(PIN_BUZ, LOW);
  strip.begin();
  strip.setBrightness(BRIGHTNESS);
  selfTest();

  Wire.begin(I2C_ADDR);
  Wire.onReceive(onReceive);
  lastI2cMs = millis();
  showMood(IDLE);
}

void loop() {
  static bool lastBtn = HIGH;
  static uint32_t blinkMs = 0;

  if (pendingMood != 0xFF) {
    noInterrupts();
    mood = pendingMood;
    pendingMood = 0xFF;
    interrupts();
    showMood(mood);
  }

  bool btn = digitalRead(PIN_BTN);
  if (lastBtn == HIGH && btn == LOW) {   // pressed
    mood = HAPPY;
    showMood(mood);
    chirp();
  }
  lastBtn = btn;

  // idle blink when the robot hasn't talked for 3 s
  uint32_t now = millis();
  noInterrupts();
  uint32_t quiet = now - lastI2cMs;
  interrupts();
  if (quiet > 3000 && mood == IDLE) {
    if (now - blinkMs > 3000) {          // blink every 3 s
      showMood(IDLE, false);
      delay(150);
      showMood(IDLE, true);
      blinkMs = now;
    }
  }
  delay(10);
}
