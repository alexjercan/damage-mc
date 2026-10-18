# Minecraft DamageIO mod

Client-side Fabric mod for **Minecraft 1.21.8**. Local player health loss
controls Arduino channel P1. P2 is reserved for other games. One health point
is half a heart; fractional damage accumulates until it reaches a whole point.

## Install

1. Install Java 21 and the [Fabric Loader](https://fabricmc.net/use/installer/)
   for **Minecraft 1.21.8**. Run that Fabric profile once to create its `mods`
   folder.
2. Download [Fabric API for Minecraft 1.21.8](https://modrinth.com/mod/fabric-api/versions?g=1.21.8)
   and put its `.jar` in the Fabric profile's `mods` folder.
3. Download `damageio-2.0.0.jar` from the [v2.0.0 release](https://github.com/alexjercan/damage-mc/releases/tag/v2.0.0)
   (or build this project) and put it in the same `mods` folder. On a default
   Linux installation that is `~/.minecraft/mods/`; a custom launcher may use
   a different game directory.
4. Flash the matching [ATmega328P firmware](../README.md#shared-firmware)
   on your Arduino. The mod and firmware must use the same v2 serial protocol.
5. Start the **Fabric 1.21.8** profile. In game, use `/damageio open ttyACM0`
   (replace `ttyACM0` with your serial port) and `/damageio close` when done.
   Other serial clients must be closed while the mod owns the port.

## Build and configure

From `minecraft/`, in the repository's Nix shell:

```fish
./gradlew build
```

The installable jar is `build/libs/damageio-<version>.jar` (not the sources
jar). For development, run `./gradlew runClient` from this folder.

`PROPORTIONAL` is the default mode: one event maps 1-20 health points to a
level of 10-50 and then returns to zero. `NORMAL` runs one cycle per health
point at the configured level. Commands:

```text
/damageio mode NORMAL
/damageio mode PROPORTIONAL
/damageio level 10
/damageio pulse 1000
/damageio close
```

`/damageio pulse <milliseconds>` sets the hold time after the Arduino ACKs
that it reached the level. Changing modes cancels queued damage; closing
waits for the current cycle to return to zero. If the connection fails or the
game exits abruptly, a return to zero cannot be guaranteed. The Arduino loses
its remembered levels when it resets. Check the physical device before
reconnecting.
