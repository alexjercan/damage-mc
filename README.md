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
/damageio pulse 5
/damageio close
```

`pulse` sets the time between damage-output toggles in milliseconds (1-255).
The mod jar includes jSerialComm. Install Fabric API alongside it. For a real
installation, use `damageio-<version>.jar` from a GitHub Release (not the
sources jar). Releases also include `damageio-atmega328p-<version>.hex` for the
Arduino firmware. Flash the firmware separately on a compatible ATmega328P
board. The mod requires Minecraft 1.21.8, Fabric Loader, and Java 21.

CI runs the Java unit tests on pushes and pull requests. To publish a release,
set `mod_version` in `gradle.properties`, then push the matching `v<mod_version>`
tag (for example, `v1.0.0`).
