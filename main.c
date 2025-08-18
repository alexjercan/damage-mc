#define DELAY_MS 100.0
#define F_CPU 16000000UL
#include <avr/io.h>
#include <avr/interrupt.h>

#define BAUD 9600
#define MY_UBRR F_CPU/16/BAUD-1

volatile uint16_t blink_delay = 500;
volatile uint16_t counter = 0;

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

ISR(TIMER1_COMPA_vect) {
    counter++;
    if (counter >= blink_delay) {
        PORTB ^= (1 << PB5); // toggle LED
        counter = 0;
    }
}

void timer1_init(void) {
    TCCR1B |= (1 << WGM12);
    OCR1A = 16000;
    TIMSK1 |= (1 << OCIE1A);
    TCCR1B |= (1 << CS10);
    sei();
}

int main(void) {
    DDRB |= (1 << PB5);
    uart_init();
    timer1_init();

    while (1) {
        if (UCSR0A & (1 << RXC0)) {
            uint8_t value = uart_read();
            if (value == 0) value = 1;
            blink_delay = value * 100;
        }
    }
}
