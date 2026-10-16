# Arduino and two-relay button wiring

[Open the illustrated HTML/SVG diagram](relay-wiring.html).

This diagram shows the current `main.c` wiring for an ATmega328P Arduino
(such as an Uno or classic Nano). The two relays act as normally open switches
in parallel with the device's existing `+` and `-` buttons. The device uses
its own power source; the Arduino does not supply power to the device.

```text
                     USB / serial
Computer ------------------ Arduino (ATmega328P)
                              5V  ------------------ VCC  Two-relay module
                              GND ------------------ GND
                              D10 (PB2, +) -------- IN1  Relay 1
                              D12 (PB4, -) -------- IN2  Relay 2

Device (own power source; no connection to Arduino power or ground)

  + button, side A  o----[ existing + button ]----o  + button, side B
                     |                             |
                     +---- COM  Relay 1  NO --------+
                                  (open at rest)
                        Relay 1 NC: not connected

  - button, side A  o----[ existing - button ]----o  - button, side B
                     |                             |
                     +---- COM  Relay 2  NO --------+
                                  (open at rest)
                        Relay 2 NC: not connected
```

Each relay's COM/NO contact pair bridges the **two opposite electrical sides**
of one existing button when the relay energizes. A four-leg tactile button
usually has two legs already connected on each side. The two wires for that
button go to opposite sides, not to the two legs that are already connected.
Confirm the sides with a continuity meter while the device is unpowered.
COM and NO can be swapped within a contact pair. Keep the two button circuits
separate; do not connect their contacts to Arduino 5V or GND.

The relay module used here has **active-low inputs**: HIGH is off and LOW turns
a relay on. `main.c` holds D10 and D12 HIGH at idle and pulls one LOW for each
press. Each press lasts 100 ms. The gap between repeated presses and between
cycles is 50 ms. The delay from the last `+` release to the first `-` press
defaults to 1000 ms and can be changed with `/damageio pulse <milliseconds>`.
Level `L` means `L` separate `+` presses and `L` separate `-` presses per cycle.

Opening the serial port can reset the Arduino. During reset, its output pins
are not controlled by `main.c`; test for unexpected relay clicks with the
device disconnected. D13 is deliberately unused because its onboard LED and
bootloader activity can toggle that pin. Verify your module's VCC rating and
COM/NO/NC terminal labels rather than relying on terminal position.
