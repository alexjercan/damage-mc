#define DELAY_MS 100.0
#define F_CPU 16000000UL
#include <avr/io.h>
#include <avr/interrupt.h>

// Message types:
// * B -> blink + value for delay in 100ms increments (e.g `B5` for 500ms)
// * D -> damage + value for damage taken (e.g `D10` for 10 damage)
// * U -> unknown message type
typedef struct {
    char type;
    union {
        uint8_t blink_value;
        uint8_t damage_value;
    };
} message_t;

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

void uart_read_message(message_t *msg) {
    msg->type = uart_read();
    if (msg->type == 'B') {
        msg->blink_value = uart_read();
    } else if (msg->type == 'D') {
        msg->damage_value = uart_read();
    } else {
        msg->type = 'U';
    }
}

ISR(TIMER1_COMPA_vect) {
    counter++;
    if (counter >= blink_delay) {
        PORTB ^= (1 << PB5);
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
            message_t msg = {0};
            uart_read_message(&msg);
            if (msg.type == 'B') {
                if (msg.blink_value == 0) msg.blink_value = 1;
                blink_delay = msg.blink_value * 100;
            } else if (msg.type == 'D') {
                // Handle damage value if needed
                // For example, you could log it or take some action
            } else {
                // Handle unknown message type if needed
            }
        }
    }
}
