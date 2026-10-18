package com.damageio;

/** Converts health loss into whole health points without discarding fractional hits. */
public final class DamageCounter {
    private boolean hasBaseline;
    private float lastHealth;
    private double pendingDamage;

    public void reset() {
        hasBaseline = false;
        pendingDamage = 0;
    }

    public int observe(float health) {
        if (!hasBaseline) {
            lastHealth = health;
            hasBaseline = true;
            return 0;
        }

        if (health < lastHealth) pendingDamage += lastHealth - health;
        lastHealth = health;
        int wholeDamage = (int) (pendingDamage + 0.00001);
        pendingDamage -= wholeDamage;
        return wholeDamage;
    }
}
