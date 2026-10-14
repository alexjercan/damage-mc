#define F_CPU 16000000UL
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>

// Message types:
// * B -> damage-output toggle interval in milliseconds (four bytes, little-endian, 1-INT32_MAX)
// * D -> damage in health points (one binary byte, 1-255)
// * U -> unknown message type
typedef struct {
    char type;
    union {
        uint32_t pulse_ms;
        uint8_t damage_value;
    };
} message_t;

#define BAUD 9600
#define MY_UBRR F_CPU/16/BAUD-1

volatile uint32_t damage_counter = 0;
volatile uint32_t damage_delay = 100;
volatile uint8_t damage_active = 0;
volatile int damage_steps = 0;

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

void uart_read_message(message_t *msg) {
    msg->type = uart_read();
    if (msg->type == 'B') {
        uint32_t b0 = uart_read();
        uint32_t b1 = uart_read();
        uint32_t b2 = uart_read();
        uint32_t b3 = uart_read();
        msg->pulse_ms = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24);
    } else if (msg->type == 'D') {
        msg->damage_value = uart_read();
    } else {
        msg->type = 'U';
    }
}

ISR(TIMER1_COMPA_vect) {
    if (damage_active) {
        damage_counter++;
        if (damage_counter >= damage_delay) {
            PORTB ^= (1 << PB5);
            damage_counter = 0;
            damage_steps--;
            if (damage_steps <= 0) {
                damage_active = 0;
                damage_steps = 0;
                PORTB &= ~(1 << PB5);
            }
        }
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
    // ATmega328P Arduino Uno/Nano onboard LED is on PB5 (digital pin 13).
    // Leave PB4 as an input; use the onboard LED for damage pulses only.
    DDRB |= (1 << PB5);
    uart_init();
    timer1_init();

    while (1) {
        if (UCSR0A & (1 << RXC0)) {
            message_t msg = {0};
            uart_read_message(&msg);
            if (msg.type == 'B') {
                if (msg.pulse_ms >= 1 && msg.pulse_ms <= INT32_MAX) {
                    // The 32-bit delay is shared with the timer ISR on an 8-bit MCU.
                    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
                        damage_delay = msg.pulse_ms;
                    }
                }
            } else if (msg.type == 'D') {
                if (msg.damage_value == 0) msg.damage_value = 1;
                damage_steps += msg.damage_value * 2;
                damage_active = 1;
            } else {
                // Handle unknown message type if needed
            }
        }
    }
}
