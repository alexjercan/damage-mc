package com.damageio;

import java.io.IOException;
import java.io.OutputStream;

/** One binary byte sets the absolute level (0-50); 0/1 ACK means done/rejected. */
public final class SerialProtocol {
    private SerialProtocol() {}

    public static void writeTarget(OutputStream output, int level) throws IOException {
        if (level < 0 || level > 50) throw new IllegalArgumentException("Target level must be 0-50");
        output.write(level);
        output.flush();
    }
}
