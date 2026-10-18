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
/damageio mode NORMAL
/damageio mode PROPORTIONAL
/damageio close
```

`PROPORTIONAL` is the default mode when the Arduino starts and when the mod
opens a port. Use `/damageio mode NORMAL` to switch to per-point cycles.

To smoke-test proportional damage without Minecraft, close the mod's serial
port first, then run this from the dev shell (it triggers the relay):

```console
python3 smoke_test.py /dev/ttyACM0 5
```

The second argument is damage from 1 to 20. The script selects proportional
mode and sends one damage frame after the Arduino has time to reset.
