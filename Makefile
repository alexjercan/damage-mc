MCU = atmega328p
F_CPU = 16000000UL
CC = avr-gcc
CFLAGS = -mmcu=$(MCU) -DF_CPU=$(F_CPU)  -Wall -Wextra -Os -std=gnu11 -g
PORT = /dev/ttyACM0  # or /dev/ttyUSB0 depending on your setup
PROGRAMMER = arduino
BAUD = 115200

main.elf: main.o
	$(CC) $(CFLAGS) -o $@ $^

main.o: main.c
	$(CC) $(CFLAGS) -c $< -o $@

main.hex: main.elf
	avr-objcopy -j .text -j .data -O ihex $< $@

upload: main.hex
	sudo avrdude -v -p $(MCU) -c $(PROGRAMMER) -P $(PORT) -b $(BAUD) -U flash:w:main.hex

clean:
	rm -f *.o *.elf *.hex
