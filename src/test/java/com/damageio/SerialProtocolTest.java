package com.damageio;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import org.junit.jupiter.api.Test;

class SerialProtocolTest {
    @Test
    void pulseUsesFourLittleEndianBytes() throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        SerialProtocol.writePulse(output, 5);
        SerialProtocol.writePulse(output, 0x12345678);
        SerialProtocol.writePulse(output, Integer.MAX_VALUE);
        assertArrayEquals(new byte[] {
            'B', 5, 0, 0, 0,
            'B', 0x78, 0x56, 0x34, 0x12,
            'B', (byte) 0xff, (byte) 0xff, (byte) 0xff, 0x7f
        }, output.toByteArray());
        assertThrows(IllegalArgumentException.class, () -> SerialProtocol.writePulse(output, 0));
        assertThrows(IllegalArgumentException.class, () -> SerialProtocol.writePulse(output, -1));
    }

    @Test
    void levelUsesOneByteAndValidatesRange() throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        SerialProtocol.writeLevel(output, 1);
        SerialProtocol.writeLevel(output, 10);
        assertArrayEquals(new byte[] {'L', 1, 'L', 10}, output.toByteArray());
        assertThrows(IllegalArgumentException.class, () -> SerialProtocol.writeLevel(output, 0));
        assertThrows(IllegalArgumentException.class, () -> SerialProtocol.writeLevel(output, 11));
    }

    @Test
    void damageUsesBinaryHealthPointsAndSplitsLargeAmounts() throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        SerialProtocol.writeDamage(output, 1);
        SerialProtocol.writeDamage(output, 256);
        assertArrayEquals(new byte[] {'D', 1, 'D', (byte) 255, 'D', 1}, output.toByteArray());
        assertThrows(IllegalArgumentException.class, () -> SerialProtocol.writeDamage(output, -1));
    }

    @Test
    void zeroDamageDoesNotWriteAFrame() throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        SerialProtocol.writeDamage(output, 0);
        assertArrayEquals(new byte[0], output.toByteArray());
    }

    @Test
    void writeFailuresReachTheCaller() {
        OutputStream broken = new OutputStream() {
            @Override
            public void write(int value) throws IOException {
                throw new IOException("disconnected");
            }
        };
        assertThrows(IOException.class, () -> SerialProtocol.writePulse(broken, 5));
    }
}
