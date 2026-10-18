package com.damageio;

import java.util.ArrayDeque;

/** Builds level changes from game damage. Only one command may await an ACK. */
public final class DamageSequencer {
    private static final int MAX_EVENTS = 64;
    private static final long ACK_TIMEOUT_NS = 10_000_000_000L;

    private record Event(int level, int cycles, int holdMs) {}
    private enum Stage { IDLE, UP, HOLD, DOWN }

    private final ArrayDeque<Event> events = new ArrayDeque<>();
    private Event active;
    private Stage stage = Stage.IDLE;
    private boolean awaitingAck;
    private long sentAt;
    private long holdUntil;
    private int rejections;

    public boolean addDamage(int damage, boolean proportional, int normalLevel, int holdMs) {
        if (damage <= 0) return true;
        if (events.size() >= MAX_EVENTS) return false;
        int level = proportional ? 10 + ((Math.min(damage, 20) - 1) * 40 + 9) / 19 : normalLevel;
        events.add(new Event(level, proportional ? 1 : damage, holdMs));
        return true;
    }

    /** Drop pending damage, but finish any outstanding command before returning to zero. */
    public void cancel() {
        events.clear();
        if (active == null) return;
        active = new Event(active.level(), 1, 0);
        if (stage == Stage.HOLD) holdUntil = 0;
    }

    public void reset() {
        events.clear();
        active = null;
        stage = Stage.IDLE;
        awaitingAck = false;
        rejections = 0;
    }

    public boolean isIdle() {
        return stage == Stage.IDLE && events.isEmpty() && !awaitingAck;
    }

    /** Return a target to transmit, or null while waiting for an ACK or hold interval. */
    public Integer nextTarget(long now) {
        if (awaitingAck) {
            if (now - sentAt >= ACK_TIMEOUT_NS) throw new IllegalStateException("Level ACK timed out");
            return null;
        }
        if (stage == Stage.IDLE) {
            active = events.poll();
            if (active == null) return null;
            stage = Stage.UP;
        }
        if (stage == Stage.HOLD) {
            if (now < holdUntil) return null;
            stage = Stage.DOWN;
        }
        awaitingAck = true;
        sentAt = now;
        return stage == Stage.UP ? active.level() : 0;
    }

    public void acknowledge(int status, long now) {
        if (!awaitingAck || (status != 0 && status != 1)) {
            throw new IllegalStateException("Unexpected level ACK: " + status);
        }
        awaitingAck = false;
        if (status == 1) {
            if (++rejections > 3) throw new IllegalStateException("Level command rejected repeatedly");
            return; // Retry the same absolute target.
        }
        rejections = 0;
        if (stage == Stage.UP) {
            stage = Stage.HOLD;
            holdUntil = now + active.holdMs() * 1_000_000L;
        } else if (stage == Stage.DOWN) {
            if (active.cycles() > 1) {
                active = new Event(active.level(), active.cycles() - 1, active.holdMs());
                stage = Stage.UP;
            } else {
                active = null;
                stage = Stage.IDLE;
            }
        }
    }
}
