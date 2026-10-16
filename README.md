# DamageIO

A client-side mod that writes the local player's health loss to a serial
port. An Arduino board can read this data and use it to tase the player
when they take damage. One health point (half a heart) sends one damage unit;
fractional losses accumulate until they reach a whole health point.

### Quickstart

Build the C code and flash it to the Arduino and then run the mod in Minecraft.
See [relay wiring](docs/relay-wiring.md) for the Arduino, relay module, and
button-contact schematic.

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
