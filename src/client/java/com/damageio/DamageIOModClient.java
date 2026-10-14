package com.damageio;

import com.fazecast.jSerialComm.SerialPort;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import java.io.IOException;
import java.io.OutputStream;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandManager;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLifecycleEvents;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.text.Text;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class DamageIOModClient implements ClientModInitializer {
    private static final Logger LOGGER = LoggerFactory.getLogger("damageio");
    private static final int DEFAULT_PULSE_MS = 1000;

    private SerialPort port;
    private OutputStream output;
    private ClientPlayerEntity lastPlayer;
    private final DamageCounter damageCounter = new DamageCounter();

    @Override
    public void onInitializeClient() {
        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) ->
            dispatcher.register(ClientCommandManager.literal("damageio")
                .then(ClientCommandManager.literal("open")
                    .then(ClientCommandManager.argument("port", StringArgumentType.string())
                        .suggests((context, builder) -> {
                            for (SerialPort available : SerialPort.getCommPorts()) {
                                builder.suggest(available.getSystemPortName());
                            }
                            return builder.buildFuture();
                        })
                        .executes(context -> {
                            String name = StringArgumentType.getString(context, "port");
                            if (openPort(name)) {
                                context.getSource().sendFeedback(Text.literal("Opened serial port: " + name));
                                return 1;
                            }
                            context.getSource().sendError(Text.literal("Could not open serial port: " + name));
                            return 0;
                        })))
                .then(ClientCommandManager.literal("pulse")
                    .then(ClientCommandManager.argument("milliseconds", IntegerArgumentType.integer(1))
                        .executes(context -> {
                            if (output == null) {
                                context.getSource().sendFeedback(Text.literal("Open a port with /damageio open <port> first."));
                                return 0;
                            }
                            int milliseconds = IntegerArgumentType.getInteger(context, "milliseconds");
                            if (!sendMessage('B', milliseconds)) return 0;
                            context.getSource().sendFeedback(Text.literal("Requested last + to first - press-start interval: " + milliseconds + " ms"));
                            return 1;
                        })))
                .then(ClientCommandManager.literal("close")
                    .executes(context -> {
                        closePort();
                        context.getSource().sendFeedback(Text.literal("Closed serial port"));
                        return 1;
                    }))));

        ClientTickEvents.END_CLIENT_TICK.register(this::onClientTick);
        ClientLifecycleEvents.CLIENT_STOPPING.register(client -> closePort());
        LOGGER.info("jSerialComm version {}", SerialPort.getVersion());
    }

    private void onClientTick(MinecraftClient client) {
        ClientPlayerEntity player = client.player;
        if (player == null || output == null) {
            lastPlayer = null;
            damageCounter.reset();
            return;
        }
        if (player != lastPlayer) {
            lastPlayer = player;
            damageCounter.reset();
        }
        if (port == null || !port.isOpen()) {
            reportConnectionLost(new IOException("Serial port is closed"));
            return;
        }

        int wholeDamage = damageCounter.observe(player.getHealth());
        if (wholeDamage > 0) {
            LOGGER.info("Player lost {} health points", wholeDamage);
            sendMessage('D', wholeDamage);
        }
    }

    private boolean openPort(String name) {
        closePort();
        try {
            for (SerialPort available : SerialPort.getCommPorts()) {
                if (!available.getSystemPortName().equals(name)) continue;
                if (!available.openPort()) {
                    LOGGER.error("Could not open serial port {}", name);
                    return false;
                }
                port = available;
                output = port.getOutputStream();
                SerialProtocol.writePulse(output, DEFAULT_PULSE_MS);
                lastPlayer = null;
                return true;
            }
            LOGGER.error("Serial port not found: {}", name);
        } catch (Exception e) {
            LOGGER.error("Could not open serial port {}", name, e);
            closePort();
        }
        return false;
    }

    private boolean sendMessage(int type, int value) {
        try {
            if (port == null || !port.isOpen()) throw new IOException("Serial port is closed");
            if (type == 'B') SerialProtocol.writePulse(output, value);
            else SerialProtocol.writeDamage(output, value);
            return true;
        } catch (IOException | RuntimeException e) {
            reportConnectionLost(e);
            return false;
        }
    }

    private void reportConnectionLost(Exception e) {
        LOGGER.error("Serial connection failed", e);
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player != null) {
            client.player.sendMessage(Text.literal("DamageIO serial connection lost. Use /damageio open <port> to reconnect."), false);
        }
        closePort();
    }

    private void closePort() {
        if (output != null) {
            try {
                output.close();
            } catch (IOException e) {
                LOGGER.error("Failed to close serial output", e);
            }
            output = null;
        }
        if (port != null) {
            if (port.isOpen() && !port.closePort()) LOGGER.error("Failed to close serial port {}", port.getSystemPortName());
            port = null;
        }
        lastPlayer = null;
        damageCounter.reset();
    }
}
