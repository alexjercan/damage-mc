#define F_CPU 16000000UL
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>

// Message types:
// * B -> last + to first - press-start interval in ms (four bytes, little-endian, minimum 100)
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

#define PRESS_MS 100UL
#define BUTTON_MASK ((1 << PB5) | (1 << PB4))

static const uint32_t BETWEEN_PRESSES_MS = 10UL;
static const uint16_t PRESSES_PER_CYCLE = 1;

typedef enum {
    IDLE,
    PRESS_PLUS,
    WAIT_MINUS,
    PRESS_MINUS,
    WAIT_PLUS
} button_phase_t;

volatile uint32_t reversal_interval_ms = 1000UL;
volatile uint32_t pending_cycles = 0;
static uint16_t plus_remaining = 0;
static uint16_t minus_remaining = 0;
static uint32_t phase_ms = 0;
static button_phase_t phase = IDLE;

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

// Called only from the timer ISR.
static void start_press(button_phase_t next_phase) {
    PORTB = (PORTB & ~BUTTON_MASK) |
            (next_phase == PRESS_PLUS ? (1 << PB5) : (1 << PB4));
    phase = next_phase;
    phase_ms = 0;
    if (next_phase == PRESS_PLUS) plus_remaining--;
    else minus_remaining--;
}

static void start_cycle(void) {
    pending_cycles--;
    plus_remaining = PRESSES_PER_CYCLE;
    minus_remaining = PRESSES_PER_CYCLE;
    start_press(PRESS_PLUS);
}

ISR(TIMER1_COMPA_vect) {
    if (phase == IDLE) {
        if (pending_cycles) start_cycle();
        return;
    }

    phase_ms++;
    if (phase == PRESS_PLUS && phase_ms >= PRESS_MS) {
        PORTB &= ~BUTTON_MASK;
        phase_ms = 0;
        if (plus_remaining) {
            phase = WAIT_PLUS;
        } else if (reversal_interval_ms <= PRESS_MS) {
            start_press(PRESS_MINUS);
        } else {
            phase = WAIT_MINUS;
        }
    } else if (phase == WAIT_MINUS &&
               phase_ms >= (minus_remaining == PRESSES_PER_CYCLE
                            ? reversal_interval_ms - PRESS_MS : BETWEEN_PRESSES_MS)) {
        start_press(PRESS_MINUS);
    } else if (phase == PRESS_MINUS && phase_ms >= PRESS_MS) {
        PORTB &= ~BUTTON_MASK;
        phase_ms = 0;
        phase = minus_remaining ? WAIT_MINUS : (pending_cycles ? WAIT_PLUS : IDLE);
    } else if (phase == WAIT_PLUS && phase_ms >= BETWEEN_PRESSES_MS) {
        if (plus_remaining) start_press(PRESS_PLUS);
        else start_cycle();
    }
}

void timer1_init(void) {
    TCCR1B |= (1 << WGM12);
    OCR1A = 15999; // 1 ms at 16 MHz with no prescaler.
    TIMSK1 |= (1 << OCIE1A);
    TCCR1B |= (1 << CS10);
    sei();
}

int main(void) {
    // PB5 (digital pin 13, onboard LED) drives +; PB4 (pin 12) drives -.
    // Relay-module inputs are assumed active-high. Both start off.
    PORTB &= ~BUTTON_MASK;
    DDRB |= BUTTON_MASK;
    uart_init();
    timer1_init();

    while (1) {
        if (UCSR0A & (1 << RXC0)) {
            message_t msg = {0};
            uart_read_message(&msg);
            if (msg.type == 'B') {
                if (msg.pulse_ms <= INT32_MAX) {
                    // B is measured from the last + press start to the first - press start.
                    uint32_t interval = msg.pulse_ms < PRESS_MS ? PRESS_MS : msg.pulse_ms;
                    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
                        reversal_interval_ms = interval;
                    }
                }
            } else if (msg.type == 'D') {
                if (msg.damage_value == 0) msg.damage_value = 1;
                // The ISR consumes cycles; update the 32-bit queue atomically.
                ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
                    if (pending_cycles <= UINT32_MAX - msg.damage_value) {
                        pending_cycles += msg.damage_value;
                    }
                }
            } else {
                // Handle unknown message type if needed
            }
        }
    }
}
