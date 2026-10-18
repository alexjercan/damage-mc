package com.damageio;

import java.io.IOException;
import java.io.OutputStream;

/** Two bytes [channel (0=P1, 1=P2), level (0-50)]; 0/1 ACK means done/rejected. */
public final class SerialProtocol {
    private SerialProtocol() {}

    public static void writeTarget(OutputStream output, int channel, int level) throws IOException {
        if (channel < 0 || channel > 1) throw new IllegalArgumentException("Channel must be 0 or 1");
        if (level < 0 || level > 50) throw new IllegalArgumentException("Target level must be 0-50");
        output.write(new byte[] {(byte) channel, (byte) level});
        output.flush();
    }
}
