#define DELAY_MS 100.0
#define F_CPU 16000000UL
#include <avr/io.h>
#include <util/delay.h>

#define BAUD 9600
#define MY_UBRR F_CPU/16/BAUD-1

void uart_init(void) {
    unsigned int ubrr = MY_UBRR;
    UBRR0H = (ubrr >> 8);
    UBRR0L = ubrr;

    UCSR0B = (1 << RXEN0);
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);
}

uint8_t uart_read(void) {
    while (!(UCSR0A & (1 << RXC0)));
    return UDR0;
}

void delay_variable(uint8_t ms) {
    for (uint16_t i = 0; i < ms; i++) {
        _delay_ms(DELAY_MS);
    }
}

int main(void) {
    DDRB |= (1 << PB5);
    uart_init();

    uint8_t delay_ms = 10;
    while (1) {
        if (UCSR0A & (1 << RXC0)) {
            delay_ms = uart_read();
            if (delay_ms == 0) delay_ms = 1;
        }

        PORTB |= (1 << PB5);
        delay_variable(delay_ms);

        PORTB &= ~(1 << PB5);
        delay_variable(delay_ms);
    }
}
