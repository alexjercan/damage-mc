# DamageIO

A client-side mod that writes the local player's health loss to a serial
port. An Arduino board can read this data and use it to tase the player
when they take damage. One health point (half a heart) sends one damage unit;
fractional losses accumulate until they reach a whole health point.

### Quickstart

Build the C code and flash it to the Arduino and then run the mod in Minecraft.

```console
nix develop --show-trace --command fish
make upload
./gradlew runClient
```

Open the serial port from the game using a local client command. It also works
when connected to a server; other players do not control your serial port.

```
/damageio open ttyACM0
/damageio close
```

The default pulse interval is 1000 ms. The mod sends this default when it opens
or reopens a port. Use `/damageio pulse <milliseconds>` to change it while
connected. `pulse` sets the time from the start of the last `+` button press
to the start of the first `-` button press, in milliseconds (1-2147483647). The firmware
clamps values below 100 ms to 100 ms (including a raw `B` value of zero).
Each press lasts 100 ms. Repeated presses of the same button are separated by
10 ms; the press count per damage unit is set in `main.c`. On the wire, a pulse
command is `B` followed by four little-endian bytes; damage commands remain
`D` followed by one byte. Update the mod and firmware together:
older firmware expects a one-byte pulse value.
The mod jar includes jSerialComm. Install Fabric API alongside it. For a real
installation, use `damageio-<version>.jar` from a GitHub Release (not the
sources jar). Releases also include `damageio-atmega328p-<version>.hex` for the
Arduino firmware. Flash the firmware separately on a compatible ATmega328P
board. The mod requires Minecraft 1.21.8, Fabric Loader, and Java 21.

CI runs the Java unit tests on pushes and pull requests. To publish a release,
set `mod_version` in `gradle.properties`, then push the matching `v<mod_version>`
tag (for example, `v1.0.1`).
