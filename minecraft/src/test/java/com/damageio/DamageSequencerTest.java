package com.damageio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class DamageSequencerTest {
    @Test
    void proportionalHoldsFromArrivalAckThenReturnsToZero() {
        DamageSequencer sequencer = new DamageSequencer();
        assertTrue(sequencer.addDamage(20, true, 1, 1000));
        assertEquals(50, sequencer.nextTarget(0));
        assertNull(sequencer.nextTarget(500_000_000L));
        sequencer.acknowledge(0, 2_000_000_000L);
        assertNull(sequencer.nextTarget(2_999_999_999L));
        assertEquals(0, sequencer.nextTarget(3_000_000_000L));
        sequencer.acknowledge(0, 3_001_000_000L);
        assertTrue(sequencer.isIdle());
    }

    @Test
    void mappingRoundsEndpointsAndCapsLargeDamage() {
        DamageSequencer sequencer = new DamageSequencer();
        sequencer.addDamage(1, true, 1, 1);
        sequencer.addDamage(10, true, 1, 1);
        sequencer.addDamage(99, true, 1, 1);
        assertEquals(10, sequencer.nextTarget(0));
        sequencer.acknowledge(0, 0);
        assertEquals(0, sequencer.nextTarget(1_000_000));
        sequencer.acknowledge(0, 1_000_000);
        assertEquals(29, sequencer.nextTarget(2_000_000));
        sequencer.acknowledge(0, 2_000_000);
        assertEquals(0, sequencer.nextTarget(3_000_000));
        sequencer.acknowledge(0, 3_000_000);
        assertEquals(50, sequencer.nextTarget(4_000_000));
    }

    @Test
    void normalRepeatsOneCyclePerDamagePoint() {
        DamageSequencer sequencer = new DamageSequencer();
        sequencer.addDamage(2, false, 7, 1);
        assertEquals(7, sequencer.nextTarget(0));
        sequencer.acknowledge(0, 0);
        assertEquals(0, sequencer.nextTarget(1_000_000));
        sequencer.acknowledge(0, 1_000_000);
        assertEquals(7, sequencer.nextTarget(2_000_000));
        sequencer.acknowledge(0, 2_000_000);
        assertEquals(0, sequencer.nextTarget(3_000_000));
        sequencer.acknowledge(0, 3_000_000);
        assertTrue(sequencer.isIdle());
    }

    @Test
    void rejectedTargetRetriesAndUnexpectedOrMissingAckFails() {
        DamageSequencer sequencer = new DamageSequencer();
        sequencer.addDamage(1, true, 1, 1);
        assertThrows(IllegalStateException.class, () -> sequencer.acknowledge(0, 0));
        assertEquals(10, sequencer.nextTarget(0));
        sequencer.acknowledge(1, 1);
        assertEquals(10, sequencer.nextTarget(2));
        assertThrows(IllegalStateException.class, () -> sequencer.nextTarget(10_000_000_002L));
    }

    @Test
    void cancelDuringHoldReturnsToZeroWithoutWaiting() {
        DamageSequencer sequencer = new DamageSequencer();
        sequencer.addDamage(5, true, 1, 1000);
        assertEquals(18, sequencer.nextTarget(0));
        sequencer.acknowledge(0, 1);
        sequencer.cancel();
        assertEquals(0, sequencer.nextTarget(2));
        sequencer.acknowledge(0, 3);
        assertTrue(sequencer.isIdle());
    }

    @Test
    void cancelDrainsCurrentTargetAndBoundsEventQueue() {
        DamageSequencer sequencer = new DamageSequencer();
        assertTrue(sequencer.addDamage(1, true, 1, 1000));
        assertEquals(10, sequencer.nextTarget(0));
        assertTrue(sequencer.addDamage(20, true, 1, 1000));
        sequencer.cancel();
        sequencer.acknowledge(0, 100);
        assertEquals(0, sequencer.nextTarget(100));
        sequencer.acknowledge(0, 101);
        assertTrue(sequencer.isIdle());
        for (int i = 0; i < 64; i++) assertTrue(sequencer.addDamage(1, true, 1, 1));
        assertFalse(sequencer.addDamage(1, true, 1, 1));
    }
}
