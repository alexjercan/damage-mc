package com.damageio;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import org.junit.jupiter.api.Test;

class SerialProtocolTest {
    @Test
    void targetsAreTwoBytesIncludingZero() throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        SerialProtocol.writeTarget(output, 0, 50);
        SerialProtocol.writeTarget(output, 1, 0);
        assertArrayEquals(new byte[] {0, 50, 1, 0}, output.toByteArray());
        assertThrows(IllegalArgumentException.class, () -> SerialProtocol.writeTarget(output, -1, 5));
        assertThrows(IllegalArgumentException.class, () -> SerialProtocol.writeTarget(output, 2, 5));
        assertThrows(IllegalArgumentException.class, () -> SerialProtocol.writeTarget(output, 0, -1));
        assertThrows(IllegalArgumentException.class, () -> SerialProtocol.writeTarget(output, 1, 51));
    }

    @Test
    void writeFailuresReachTheCaller() {
        OutputStream broken = new OutputStream() {
            @Override
            public void write(int value) throws IOException {
                throw new IOException("disconnected");
            }
        };
        assertThrows(IOException.class, () -> SerialProtocol.writeTarget(broken, 0, 5));
    }
}
