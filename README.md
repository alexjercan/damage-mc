# DamageIO

A client-side mod that turns local player health loss into target levels sent
to an Arduino over serial. The Arduino presses + or - to reach each level.
One health point is half a heart; fractional losses accumulate.

### Quickstart

Build the C code and flash it to the Arduino and then run the mod in Minecraft.
See [relay wiring](docs/relay-wiring.md) for the Arduino, two relay modules,
and button contacts.

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

`PROPORTIONAL` is the default mode in the mod: one damage event maps 1-20
health points to a target level of 10-50. `NORMAL` runs one cycle per health
point at the configured `/damageio level` (1-50). `/damageio pulse <ms>`
sets the hold time after the target is reached, before returning to zero.
Changing modes cancels queued damage and returns to zero after any in-flight
target completes. Closing the port waits for the active cycle to return to zero.

The new firmware protocol is not compatible with older releases. At 9600 baud
each command is two binary bytes: channel `0` (P1) or `1` (P2), followed by an
absolute level from 0 to 50. The Arduino tracks each channel separately and
sends one byte back: `0` after the target is reached (after the last button
release), or `1` if it rejects an invalid command or its seven-entry queue is
full. Only one target is outstanding at a time. Minecraft uses P1 only; P2 is
reserved for other games. The mod starts its hold timer after the
ACK, and reports missing ACKs as a connection error. The board assumes its
physical level is zero at startup; resetting it while the device is at a
nonzero level can lose position. A serial failure or forced game shutdown
cannot guarantee a return to zero. Check the physical device before
reconnecting.

To smoke-test the raw protocol, close the mod's serial port first, then run
this from the dev shell (it triggers the relay):

```console
python3 smoke_test.py /dev/ttyACM0
```

At the prompt, enter a channel and an absolute target level, such as `0 20`
for P1 or `1 20` for P2. The script keeps one connection open, sends one
command per line, and prints each ACK. Enter `0 0` and `1 0` to return both
channels to zero before exiting with Ctrl+C or EOF. Opening the port again can
reset the Arduino and lose its position; a later zero in a new session may not
undo a previous nonzero level.
