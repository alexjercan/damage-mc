package com.damageio;

import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.suggestion.SuggestionProvider;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.suggestion.Suggestions;
import com.mojang.brigadier.suggestion.SuggestionsBuilder;
import net.fabricmc.api.ClientModInitializer;
import com.fazecast.jSerialComm.SerialPort;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.server.command.CommandManager;
import net.minecraft.server.command.ServerCommandSource;
import net.minecraft.text.Text;
import java.io.PrintWriter;
import java.util.concurrent.CompletableFuture;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class DamageIOModClient implements ClientModInitializer {
	public static final String MOD_ID = "damageio";

	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    private static SerialPort port;
    private static PrintWriter writer;

	@Override
	public void onInitializeClient() {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            dispatcher.register(CommandManager.literal("serial")
                .then(CommandManager.literal("set")
                    .then(CommandManager.argument("port", StringArgumentType.string())
                        .suggests(new PortSuggestionProvider())
                        .executes(ctx -> {
                            String portName = StringArgumentType.getString(ctx, "port");

                            if (openPort(portName)) {
                                ctx.getSource().sendFeedback(() -> Text.literal("Opened serial port: " + portName), false);
                            } else {
                                ctx.getSource().sendError(Text.literal("Failed to open port: " + portName));
                            }
                            return 1;
                        })
                    )
                )
                .then(CommandManager.literal("send")
                    .then(CommandManager.argument("value", IntegerArgumentType.integer(0, 255))
                        .executes(ctx -> {
                            int value = IntegerArgumentType.getInteger(ctx, "value");
                            sendToSerial(value);
                            ctx.getSource().sendFeedback(() -> Text.literal("Sent value: " + value), false);
                            return 1;
                        })
                    )
                )
                .then(CommandManager.literal("close")
                    .executes(ctx -> {
                        closePort();
                        ctx.getSource().sendFeedback(() -> Text.literal("Closed serial port"), false);
                        return 1;
                    })
                )
            );
        });

        LOGGER.info("Using Library Version v" + SerialPort.getVersion());
	}

    class PortSuggestionProvider implements SuggestionProvider<ServerCommandSource> {
        @Override
        public CompletableFuture<Suggestions> getSuggestions(CommandContext<ServerCommandSource> context, SuggestionsBuilder builder) throws CommandSyntaxException {
            ServerCommandSource source = context.getSource();

            SerialPort[] availablePorts = SerialPort.getCommPorts();
		    LOGGER.info("Available serial ports:" + availablePorts.length);

            for (SerialPort sp : availablePorts) {
                builder.suggest(sp.getSystemPortName());
		        LOGGER.info("Available port: " + sp.getSystemPortName() + " - " + sp.getDescriptivePortName() + " - " + sp.getPortDescription());
            }

            return builder.buildFuture();
        }
    }

    private static int getPortIndex(String name) {
        SerialPort[] ports = SerialPort.getCommPorts();
        for (int i = 0; i < ports.length; i++) {
            if (ports[i].getSystemPortName().equals(name)) {
                return i;
            }
        }

        return -1;
    }

    private static boolean openPort(String name) {
        closePort();
        int index = getPortIndex(name);
        if (index < 0) {
            LOGGER.error("Port not found: " + name);
            return false;
        }
        LOGGER.info("Opening port: " + name + " at index " + index);

        port = SerialPort.getCommPorts()[index];
        if (port.openPort()) {
            writer = new PrintWriter(port.getOutputStream(), true);
            return true;
        }

        port = null;
        return false;
    }

    private static void closePort() {
        if (writer != null) {
            writer.close();
            writer = null;
        }

        if (port != null && port.isOpen()) {
            port.closePort();
            port = null;
        }
    }

    private static void sendToSerial(int value) {
        if (writer != null) {
            writer.write(value & 0xFF);
            writer.flush();
        }
    }
}
