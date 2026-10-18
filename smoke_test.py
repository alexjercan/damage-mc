#!/usr/bin/env python3
"""Send [channel, level] commands over one serial connection and print ACKs."""

import argparse
import time


def parse_target(value):
    parts = value.split()
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("enter channel (0=P1, 1=P2) and level (0-50)")
    try:
        channel, level = map(int, parts)
    except ValueError as error:
        raise argparse.ArgumentTypeError("channel and level must be integers") from error
    if channel not in (0, 1):
        raise argparse.ArgumentTypeError("channel must be 0 (P1) or 1 (P2)")
    if not 0 <= level <= 50:
        raise argparse.ArgumentTypeError("level must be between 0 and 50")
    return channel, level


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="serial port path, for example /dev/ttyACM0")
    args = parser.parse_args()

    try:
        import serial
    except ImportError:
        parser.exit(1, "pyserial is required; use the project nix dev shell.\n")

    last_levels = [0, 0]
    try:
        with serial.Serial(args.port, baudrate=9600, timeout=10, write_timeout=2) as connection:
            time.sleep(2)  # Opening the port usually resets the Arduino.
            while True:
                try:
                    value = input("channel level (0/1 0-50)> ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                try:
                    channel, level = parse_target(value)
                except argparse.ArgumentTypeError as error:
                    print(error)
                    continue

                if connection.write(bytes((channel, level))) != 2:
                    raise serial.SerialTimeoutException("incomplete serial write")
                connection.flush()
                ack = connection.read(1)
                if ack == b"\x00":
                    last_levels[channel] = level
                    print(f"ACK 0: P{channel + 1} reached level {level}")
                elif ack == b"\x01":
                    print(f"ACK 1: P{channel + 1} level {level} rejected")
                elif not ack:
                    raise serial.SerialException("No ACK received before timeout")
                else:
                    raise serial.SerialException(f"Unexpected ACK: {ack!r}")
    except serial.SerialException as error:
        parser.exit(1, f"serial error: {error}\n")
    for channel, level in enumerate(last_levels):
        if level:
            print(f"Warning: P{channel + 1} is still at level {level}; reopening the port may reset the Arduino's level tracking.")


if __name__ == "__main__":
    main()
