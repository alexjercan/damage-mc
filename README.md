# DamageIO

Really simple mod that writes the damage dealt to the player to the serial
port. An arduino board can read this data and use it to tase the player
when they take damage.

### Quickstart

Build the C code and flash it to the Arduino and then run the mod in Minecraft.

```console
nix develop --show-trace --command fish
make upload
./gradlew runClient
```

You will need to open the serial port from the game using the `/serial`
command.

```
/serial open ttyACM0
```

For more information on how this works, see the [blog
post](https://alexjercan.github.io/0006/).
