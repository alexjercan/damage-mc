#define F_CPU 16000000UL
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>

// Protocol at 9600 baud: two bytes [channel (0=P1, 1=P2), level (0-50)].
// Reply 0 after reaching the target; reply 1 if rejected (full/invalid).
#define BAUD 9600UL
#define MY_UBRR (F_CPU / 16UL / BAUD - 1UL)
#define MAX_LEVEL 50U
#define QUEUE_SIZE 8U
#define P1_PLUS (1 << PB2)  // D10
#define P1_MINUS (1 << PB4) // D12
#define P2_PLUS (1 << PB0)  // D8
#define P2_MINUS (1 << PB1) // D9
#define BUTTON_MASK (P1_PLUS | P1_MINUS | P2_PLUS | P2_MINUS)

// Tune to the button contacts on the device.
#define PRESS_MS 75U
#define BETWEEN_PRESSES_MS 25U

typedef struct {
    uint8_t channel;
    uint8_t level;
} level_command;

static volatile level_command targets[QUEUE_SIZE];
static volatile uint8_t head = 0;
static volatile uint8_t tail = 0;
static volatile uint8_t completed = 0;
static uint8_t levels[2] = {0, 0};
static uint8_t channel = 0;
static uint8_t target = 0;
static uint8_t active = 0;
static uint8_t pressing = 0;
static uint8_t wait_ms = 0;
static uint8_t press_ms = 0;
static uint8_t direction_up = 0;

static void uart_init(void) {
    UBRR0H = (uint8_t)(MY_UBRR >> 8);
    UBRR0L = (uint8_t)MY_UBRR;
    UCSR0B = (1 << RXEN0) | (1 << TXEN0);
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);
}

static void uart_write(uint8_t value) {
    while (!(UCSR0A & (1 << UDRE0)));
    UDR0 = value;
}

static void timer1_init(void) {
    TCCR1B = (1 << WGM12) | (1 << CS10);
    OCR1A = 15999; // 1 ms at 16 MHz without a prescaler.
    TIMSK1 = (1 << OCIE1A);
    sei();
}

ISR(TIMER1_COMPA_vect) {
    if (!active) {
        if (head == tail) return;
        channel = targets[tail].channel;
        target = targets[tail].level;
        tail = (tail + 1U) % QUEUE_SIZE;
        active = 1;
    }

    if (pressing) {
        if (++press_ms < PRESS_MS) return;
        PORTB |= BUTTON_MASK;
        pressing = 0;
        press_ms = 0;
        levels[channel] += direction_up ? 1 : -1;
        if (levels[channel] == target) {
            active = 0;
            completed++;
        } else {
            wait_ms = BETWEEN_PRESSES_MS;
        }
        return;
    }

    if (wait_ms) {
        wait_ms--;
        return;
    }
    if (levels[channel] == target) {
        active = 0;
        completed++;
        return;
    }
    direction_up = levels[channel] < target;
    // Active-low relay inputs. Never press two buttons at once.
    uint8_t button = channel == 0
        ? (direction_up ? P1_PLUS : P1_MINUS)
        : (direction_up ? P2_PLUS : P2_MINUS);
    PORTB = (PORTB | BUTTON_MASK) & ~button;
    pressing = 1;
    press_ms = 0;
}

int main(void) {
    PORTB |= BUTTON_MASK;
    DDRB |= BUTTON_MASK;
    uart_init();
    timer1_init();
    uint8_t pending_channel = 0;
    uint8_t expecting_level = 0;

    while (1) {
        uint8_t done = 0;
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
            if (completed) {
                completed--;
                done = 1;
            }
        }
        if (done) uart_write(0);

        if (UCSR0A & (1 << RXC0)) {
            uint8_t value = UDR0;
            if (!expecting_level) {
                pending_channel = value;
                expecting_level = 1;
            } else {
                expecting_level = 0;
                if (pending_channel > 1 || value > MAX_LEVEL) {
                    uart_write(1);
                } else {
                    uint8_t accepted = 0;
                    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
                        uint8_t next = (head + 1U) % QUEUE_SIZE;
                        if (next != tail) {
                            targets[head].channel = pending_channel;
                            targets[head].level = value;
                            head = next;
                            accepted = 1;
                        }
                    }
                    if (!accepted) uart_write(1);
                }
            }
        }
    }
}
