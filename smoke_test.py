#!/usr/bin/env python3
"""Send absolute levels (0-50) over one serial connection and print ACKs."""

import argparse
import time


def target_level(value):
    try:
        level = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("level must be an integer from 0 to 50") from error
    if not 0 <= level <= 50:
        raise argparse.ArgumentTypeError("level must be between 0 and 50")
    return level


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="serial port path, for example /dev/ttyACM0")
    args = parser.parse_args()

    try:
        import serial
    except ImportError:
        parser.exit(1, "pyserial is required; use the project nix dev shell.\n")

    last_level = 0
    try:
        with serial.Serial(args.port, baudrate=9600, timeout=10, write_timeout=2) as connection:
            time.sleep(2)  # Opening the port usually resets the Arduino.
            while True:
                try:
                    value = input("level (0-50)> ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                try:
                    level = target_level(value)
                except argparse.ArgumentTypeError as error:
                    print(error)
                    continue

                if connection.write(bytes((level,))) != 1:
                    raise serial.SerialTimeoutException("incomplete serial write")
                connection.flush()
                ack = connection.read(1)
                if ack == b"\x00":
                    last_level = level
                    print(f"ACK 0: reached level {level}")
                elif ack == b"\x01":
                    print(f"ACK 1: level {level} rejected")
                elif not ack:
                    raise serial.SerialException("No ACK received before timeout")
                else:
                    raise serial.SerialException(f"Unexpected ACK: {ack!r}")
    except serial.SerialException as error:
        parser.exit(1, f"serial error: {error}\n")
    if last_level:
        print(f"Warning: level {last_level} is still set; closing the port may reset the Arduino's level tracking.")


if __name__ == "__main__":
    main()
