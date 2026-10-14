package com.damageio;

import java.io.IOException;
import java.io.OutputStream;

/** B has a four-byte little-endian value; D has a one-byte value. */
public final class SerialProtocol {
    private SerialProtocol() {}

    public static void writePulse(OutputStream output, int milliseconds) throws IOException {
        if (milliseconds < 1) throw new IllegalArgumentException("Pulse interval must be positive");
        output.write(new byte[] {
            'B',
            (byte) milliseconds,
            (byte) (milliseconds >>> 8),
            (byte) (milliseconds >>> 16),
            (byte) (milliseconds >>> 24)
        });
        output.flush();
    }

    public static void writeDamage(OutputStream output, int healthPoints) throws IOException {
        if (healthPoints < 0) throw new IllegalArgumentException("Damage must not be negative");
        while (healthPoints > 0) {
            int amount = Math.min(healthPoints, 255);
            writeFrame(output, 'D', amount);
            healthPoints -= amount;
        }
    }

    private static void writeFrame(OutputStream output, int type, int value) throws IOException {
        if (value < 1 || value > 255) throw new IllegalArgumentException("Frame value must be 1-255");
        output.write(new byte[] { (byte) type, (byte) value });
        output.flush();
    }
}
