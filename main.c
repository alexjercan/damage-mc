#define F_CPU 16000000UL
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>

// NOTE: Message types:
// * B -> last + release to first - press interval in ms (four bytes, little-endian, minimum 100)
// * D -> damage in health points (one binary byte, 1-255)
// * L -> presses per button per cycle (one binary byte, clamped to 1-10)
// * U -> unknown message type
typedef struct {
    char type;
    union {
        uint32_t pulse_ms;
        uint8_t damage_value;
        uint8_t level_value;
    };
} message_t;

#define BAUD 9600
#define MY_UBRR F_CPU/16/BAUD-1

#define BUTTON_MASK ((1 << PB2) | (1 << PB4))

// TODO: Constants that need to be fine tuned for each device
#define MAX_LEVEL 10U
#define PRESS_MS 100UL
#define BETWEEN_PRESSES_MS 50UL

// NOTE: The configurable parameters of the mod: level (presses per cycle) and the delay between level and stop
volatile uint8_t presses_per_cycle = 1;
volatile uint32_t plus_to_minus_delay_ms = 1000UL;

typedef enum {
    IDLE,
    PRESS_PLUS,
    WAIT_MINUS,
    PRESS_MINUS,
    WAIT_PLUS
} button_phase_t;

static uint8_t cycle_press_count = 1;
volatile uint32_t pending_cycles = 0;
static uint8_t plus_remaining = 0;
static uint8_t minus_remaining = 0;
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
    } else if (msg->type == 'L') {
        msg->level_value = uart_read();
    } else {
        msg->type = 'U';
    }
}

static void start_press(button_phase_t next_phase) {
    // Active-low relay inputs: release both, then pull the selected input LOW.
    PORTB = (PORTB | BUTTON_MASK) &
            ~(next_phase == PRESS_PLUS ? (1 << PB2) : (1 << PB4));
    phase = next_phase;
    phase_ms = 0;
    if (next_phase == PRESS_PLUS) plus_remaining--;
    else minus_remaining--;
}

static void start_cycle(void) {
    pending_cycles--;
    cycle_press_count = presses_per_cycle;
    plus_remaining = cycle_press_count;
    minus_remaining = cycle_press_count;
    start_press(PRESS_PLUS);
}

ISR(TIMER1_COMPA_vect) {
    if (phase == IDLE) {
        if (pending_cycles) start_cycle();
        return;
    }

    phase_ms++;
    if (phase == PRESS_PLUS && phase_ms >= PRESS_MS) {
        PORTB |= BUTTON_MASK;
        phase_ms = 0;
        phase = plus_remaining ? WAIT_PLUS : WAIT_MINUS;
    } else if (phase == WAIT_MINUS &&
               phase_ms >= (minus_remaining == cycle_press_count
                            ? plus_to_minus_delay_ms : BETWEEN_PRESSES_MS)) {
        start_press(PRESS_MINUS);
    } else if (phase == PRESS_MINUS && phase_ms >= PRESS_MS) {
        PORTB |= BUTTON_MASK;
        phase_ms = 0;
        phase = minus_remaining ? WAIT_MINUS : (pending_cycles ? WAIT_PLUS : IDLE);
    } else if (phase == WAIT_PLUS && phase_ms >= BETWEEN_PRESSES_MS) {
        if (plus_remaining) start_press(PRESS_PLUS);
        else start_cycle();
    }
}

void timer1_init(void) {
    TCCR1B |= (1 << WGM12);
    OCR1A = 15999; // NOTE: 1 ms at 16 MHz with no prescaler.
    TIMSK1 |= (1 << OCIE1A);
    TCCR1B |= (1 << CS10);
    sei();
}

int main(void) {
    // Set the OFF level before switching the pins to outputs.
    PORTB |= BUTTON_MASK;
    DDRB |= BUTTON_MASK;
    uart_init();
    timer1_init();

    while (1) {
        if (UCSR0A & (1 << RXC0)) {
            message_t msg = {0};
            uart_read_message(&msg);
            if (msg.type == 'B') {
                if (msg.pulse_ms <= INT32_MAX) {
                    uint32_t delay = msg.pulse_ms < PRESS_MS ? PRESS_MS : msg.pulse_ms;
                    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
                        plus_to_minus_delay_ms = delay;
                    }
                }
            } else if (msg.type == 'L') {
                presses_per_cycle = msg.level_value < 1 ? 1 :
                                    (msg.level_value > MAX_LEVEL ? MAX_LEVEL : msg.level_value);
            } else if (msg.type == 'D') {
                if (msg.damage_value == 0) msg.damage_value = 1;
                ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
                    if (pending_cycles <= UINT32_MAX - msg.damage_value) {
                        pending_cycles += msg.damage_value;
                    }
                }
            } else {
                // NOTE: Handle unknown message type if needed
            }
        }
    }
}
