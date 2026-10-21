# Arduino and four-relay button wiring

[Open the illustrated P1 wiring diagram](relay-wiring.html). P2 uses the same
button-contact pattern with a second two-relay module.

This wiring is for an ATmega328P Arduino (Uno or classic Nano) and two
active-low two-relay modules. Each relay's normally open COM/NO contacts bridge
one button. The device has its own power source; it does not connect to the
Arduino's 5V or GND.

| Device button | Arduino pin | Relay module input | Relay contacts |
| --- | --- | --- | --- |
| P1 + | D8 (PB0) | First module IN1 | Across P1 + button |
| P1 - | D9 (PB1) | First module IN2 | Across P1 - button |
| P2 + | D10 (PB2) | Second module IN1 | Across P2 + button |
| P2 - | D11 (PB3) | Second module IN2 | Across P2 - button |

With the JD-VCC/VCC jumper installed on each **5V-rated** module, connect both
modules' VCC pins to Arduino 5V and both GND pins to Arduino GND, in parallel.
JD-VCC supplies the relay coils; its jumper joins JD-VCC to VCC. These pins
are not a series-power connector. Check the module's own pinout and the
Arduino/USB supply current capacity before wiring. Do not power the coils
from GPIO pins. Removing the jumper to use a separate coil supply requires
checking that specific module's isolation and ground arrangement first.

Each relay's COM/NO contact pair bridges the **two opposite electrical sides**
of one existing button when the relay energizes. A four-leg tactile button
usually has two legs already connected on each side. Confirm the sides with a
continuity meter while the device is unpowered. COM and NO can be swapped
within a contact pair. Do not use NC. Keep the four button circuits separate.

The module inputs are active-low: HIGH is off, LOW energizes a relay. Firmware
holds all four inputs HIGH at idle and drives only one LOW at a time. Each
press lasts 75 ms, with a 25 ms gap between repeated presses. Levels for P1
and P2 are tracked separately in RAM. Opening the serial port can reset the
Arduino and reset its remembered levels to zero even if the device has not
changed level. Return both channels to zero before closing the connection.
During reset, firmware does not control the output pins: test for unexpected
clicks with the device disconnected. D13 is unused because its LED and
bootloader activity can toggle that pin.
