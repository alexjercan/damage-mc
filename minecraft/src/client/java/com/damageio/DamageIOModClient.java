package com.damageio;

import com.fazecast.jSerialComm.SerialPort;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import java.io.IOException;
import java.io.InputStream;
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
    private static final int MODE_NORMAL = 0;
    private static final int MODE_PROPORTIONAL = 1;

    private int currentMode = MODE_PROPORTIONAL;
    private int pulseMs = 1000;
    private int normalLevel = 1;
    private final DamageCounter damageCounter = new DamageCounter();
    private final DamageSequencer sequencer = new DamageSequencer();
    private SerialPort port;
    private InputStream input;
    private OutputStream output;
    private ClientPlayerEntity lastPlayer;
    private long readyAt;
    private boolean closing;

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
                            pulseMs = IntegerArgumentType.getInteger(context, "milliseconds");
                            context.getSource().sendFeedback(Text.literal("Delay at target level: " + pulseMs + " ms"));
                            return 1;
                        })))
                .then(ClientCommandManager.literal("level")
                    .then(ClientCommandManager.argument("presses", IntegerArgumentType.integer(1, 50))
                        .executes(context -> {
                            normalLevel = IntegerArgumentType.getInteger(context, "presses");
                            context.getSource().sendFeedback(Text.literal("Normal-mode target level: " + normalLevel));
                            return 1;
                        })))
                .then(ClientCommandManager.literal("mode")
                    .then(ClientCommandManager.argument("name", StringArgumentType.word())
                        .suggests((context, builder) -> {
                            builder.suggest("NORMAL");
                            builder.suggest("PROPORTIONAL");
                            return builder.buildFuture();
                        })
                        .executes(context -> {
                            String name = StringArgumentType.getString(context, "name");
                            int mode;
                            if (name.equalsIgnoreCase("NORMAL")) mode = MODE_NORMAL;
                            else if (name.equalsIgnoreCase("PROPORTIONAL")) mode = MODE_PROPORTIONAL;
                            else {
                                context.getSource().sendError(Text.literal("Mode must be NORMAL or PROPORTIONAL."));
                                return 0;
                            }
                            if (mode != currentMode) sequencer.cancel();
                            currentMode = mode;
                            context.getSource().sendFeedback(Text.literal("Mode: " + name.toUpperCase(java.util.Locale.ROOT)));
                            return 1;
                        })))
                .then(ClientCommandManager.literal("close")
                    .executes(context -> {
                        closing = true;
                        sequencer.cancel();
                        if (sequencer.isIdle()) closePort();
                        context.getSource().sendFeedback(Text.literal("Stopping output and closing serial port"));
                        return 1;
                    }))));

        ClientTickEvents.END_CLIENT_TICK.register(this::onClientTick);
        ClientLifecycleEvents.CLIENT_STOPPING.register(client -> closePort());
        LOGGER.info("jSerialComm version {}", SerialPort.getVersion());
    }

    private void onClientTick(MinecraftClient client) {
        if (output == null) {
            lastPlayer = null;
            damageCounter.reset();
            return;
        }
        if (port == null || !port.isOpen()) {
            reportConnectionLost(new IOException("Serial port is closed"));
            return;
        }
        try {
            long now = System.nanoTime();
            while (port.bytesAvailable() > 0) {
                int status = input.read();
                if (status < 0) throw new IOException("Serial ACK stream ended");
                sequencer.acknowledge(status, System.nanoTime());
            }

            ClientPlayerEntity player = client.player;
            if (player == null || closing) {
                lastPlayer = null;
                damageCounter.reset();
                sequencer.cancel();
            } else {
                if (player != lastPlayer) {
                    lastPlayer = player;
                    damageCounter.reset();
                }
                int wholeDamage = damageCounter.observe(player.getHealth());
                if (wholeDamage > 0 && !sequencer.addDamage(wholeDamage,
                        currentMode == MODE_PROPORTIONAL, normalLevel, pulseMs)) {
                    LOGGER.warn("DamageIO event queue full; dropping {} health points", wholeDamage);
                }
            }

            if (now >= readyAt) {
                Integer target = sequencer.nextTarget(now);
                if (target != null) SerialProtocol.writeTarget(output, 0, target); // Minecraft uses P1 only.
            }
            if (closing && sequencer.isIdle()) closePort();
        } catch (IOException | IllegalStateException e) {
            reportConnectionLost(e);
        }
    }

    private boolean openPort(String name) {
        // Do not abandon an active level change. Use /damageio close first.
        if (output != null) return false;
        try {
            for (SerialPort available : SerialPort.getCommPorts()) {
                if (!available.getSystemPortName().equals(name)) continue;
                if (!available.openPort()) return false;
                port = available;
                port.setComPortTimeouts(SerialPort.TIMEOUT_NONBLOCKING, 0, 0);
                input = port.getInputStream();
                output = port.getOutputStream();
                // Opening the port resets many Arduino boards; do not send to the bootloader.
                readyAt = System.nanoTime() + 2_000_000_000L;
                sequencer.reset();
                currentMode = MODE_PROPORTIONAL;
                lastPlayer = null;
                closing = false;
                return true;
            }
            LOGGER.error("Serial port not found: {}", name);
        } catch (Exception e) {
            LOGGER.error("Could not open serial port {}", name, e);
            closePort();
        }
        return false;
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
        if (input != null) {
            try { input.close(); } catch (IOException e) { LOGGER.error("Failed to close serial input", e); }
            input = null;
        }
        if (output != null) {
            try { output.close(); } catch (IOException e) { LOGGER.error("Failed to close serial output", e); }
            output = null;
        }
        if (port != null) {
            if (port.isOpen() && !port.closePort()) LOGGER.error("Failed to close serial port {}", port.getSystemPortName());
            port = null;
        }
        lastPlayer = null;
        closing = false;
        sequencer.reset();
        damageCounter.reset();
    }
}
