package com.damageio;

import java.io.IOException;
import java.io.OutputStream;

/** Two-byte frames consumed by the ATmega328P firmware. */
public final class SerialProtocol {
    private SerialProtocol() {}

    public static void writePulse(OutputStream output, int milliseconds) throws IOException {
        writeFrame(output, 'B', milliseconds);
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
