package com.damageio;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class DamageCounterTest {
    @Test
    void halfHeartIsOneHealthPoint() {
        DamageCounter counter = new DamageCounter();
        assertEquals(0, counter.observe(20));
        assertEquals(1, counter.observe(19));
        assertEquals(2, counter.observe(17));
    }

    @Test
    void fractionalLossAccumulatesAcrossTicks() {
        DamageCounter counter = new DamageCounter();
        counter.observe(20);
        assertEquals(0, counter.observe(19.75f));
        assertEquals(0, counter.observe(19.5f));
        assertEquals(1, counter.observe(19));
        assertEquals(0, counter.observe(18.75f));
        assertEquals(0, counter.observe(18.5f));
        assertEquals(1, counter.observe(18));
    }

    @Test
    void healingDoesNotCountAsDamage() {
        DamageCounter counter = new DamageCounter();
        counter.observe(20);
        assertEquals(0, counter.observe(19.5f));
        assertEquals(0, counter.observe(20));
        assertEquals(1, counter.observe(19.5f));
    }

    @Test
    void resetClearsOldHealthAndFractionalLoss() {
        DamageCounter counter = new DamageCounter();
        counter.observe(20);
        counter.observe(19.5f);
        counter.reset();
        assertEquals(0, counter.observe(10));
        assertEquals(0, counter.observe(9.5f));
        assertEquals(1, counter.observe(9));
    }
}
