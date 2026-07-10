#include "digital_power_pwm_map.h"

#include <stdio.h>

static int failures = 0;

static void expect_true(const char *name, bool condition)
{
    if (condition)
    {
        printf("PASS,%s\n", name);
        return;
    }
    printf("FAIL,%s\n", name);
    failures++;
}

static void test_default_timer_contract(void)
{
    DpPwmMapConfig cfg;
    DpPwmMap_DefaultConfig(&cfg);
    expect_true("center_aligned_170mhz_200khz_contract",
                cfg.period_counts == 425u &&
                    cfg.auto_reload == 425u &&
                    cfg.deadtime_counts == 17u);
}

static void test_half_duty_shadow_update(void)
{
    DpPwmMapConfig cfg;
    DpPwmMapState state;
    DpPwmQueueResult result;

    DpPwmMap_DefaultConfig(&cfg);
    DpPwmMap_Init(&state);
    result = DpPwmMap_Queue(&state, &cfg, DP_FIXED_ONE / 2, true);
    expect_true("half_duty_waits_for_update_event",
                result.pending_compare == 213u &&
                    state.active_compare == 0u &&
                    !state.active_enable &&
                    state.update_pending);

    DpPwmMap_ApplyUpdateEvent(&state);
    expect_true("half_duty_applies_at_update_event",
                state.active_compare == 213u &&
                    state.active_enable &&
                    !state.update_pending);
}

static void test_duty_limit_and_immediate_disable(void)
{
    DpPwmMapConfig cfg;
    DpPwmMapState state;
    DpPwmQueueResult result;

    DpPwmMap_DefaultConfig(&cfg);
    DpPwmMap_Init(&state);
    result = DpPwmMap_Queue(&state, &cfg, DP_FIXED_ONE, true);
    DpPwmMap_ApplyUpdateEvent(&state);
    expect_true("duty_above_limit_is_clamped",
                result.duty_clamped &&
                    result.clamped_duty == cfg.duty_max &&
                    state.active_compare == 276u);

    DpPwmMap_Queue(&state, &cfg, cfg.duty_max, false);
    expect_true("disable_is_immediate",
                !state.active_enable &&
                    state.active_compare == 276u &&
                    state.pending_compare == 0u);
}

int main(void)
{
    test_default_timer_contract();
    test_half_duty_shadow_update();
    test_duty_limit_and_immediate_disable();
    printf("SUMMARY,%s,failures=%d\n", failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}
