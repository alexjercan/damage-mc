# DamageIO

An Arduino firmware and game integrations that control a two-channel device
using relays across its existing + and - buttons. See [relay wiring](docs/relay-wiring.md)
before connecting hardware.

- [Minecraft](minecraft/README.md): Fabric client mod for Minecraft 1.21.8.
  Minecraft uses P1 only.
- [FIFA / EA Sports FC](fifa/README.md): screen-score OCR dry run. It does not
  send serial commands or activate relays.

## Shared firmware

Build from the repository root in the Nix development shell:

```fish
nix develop --command fish
make main.hex
```

Flash the firmware on an ATmega328P Arduino with `make upload` after checking
the port, board, and relay wiring in `Makefile` and
[the wiring guide](docs/relay-wiring.md). Install matching firmware and game
integration versions. The v2 protocol is incompatible with older releases.

At 9600 baud, send two binary bytes: channel `0` (P1) or `1` (P2), followed by
an absolute level from 0 to 50. The Arduino tracks each channel separately
and replies with one byte: `0` after reaching the target (after the last
button release), or `1` if it rejects an invalid command or its seven-entry
queue is full. Send only one target at a time and wait for its ACK. Levels are
stored in RAM. Opening the port can reset the Arduino and lose position if
the physical device is not at zero; check it before reconnecting.

To smoke-test the raw protocol, close any other serial client first. This
script keeps the connection open and **does activate relays**:

```fish
python3 smoke_test.py /dev/ttyACM0
```

At the prompt, enter `0 20` for P1 level 20 or `1 20` for P2 level 20. The
script prints each ACK. Enter `0 0` and `1 0` to return both channels to zero
before exiting with Ctrl+C or EOF. A later zero in a new session may not undo
a previous nonzero level if reopening resets the board.
