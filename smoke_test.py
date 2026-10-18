#!/usr/bin/env python3
"""Send one proportional damage event to the Arduino serial port."""

import argparse
import time


def damage_amount(value):
    amount = int(value)
    if not 1 <= amount <= 20:
        raise argparse.ArgumentTypeError("damage must be between 1 and 20")
    return amount


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="serial port path, for example /dev/ttyACM0")
    parser.add_argument("damage", type=damage_amount, help="health points lost (1-20)")
    args = parser.parse_args()

    try:
        import serial
    except ImportError:
        parser.exit(1, "pyserial is required; use the project nix dev shell.\n")

    try:
        with serial.Serial(args.port, baudrate=9600, timeout=1, write_timeout=2) as connection:
            # Opening an Arduino serial port usually resets the board.
            time.sleep(2)
            frame = bytes((ord("M"), 1, ord("D"), args.damage))
            if connection.write(frame) != len(frame):
                raise serial.SerialTimeoutException("incomplete serial write")
            connection.flush()
    except serial.SerialException as error:
        parser.exit(1, f"serial error: {error}\n")

    print(f"Sent proportional damage {args.damage} to {args.port}")


if __name__ == "__main__":
    main()
