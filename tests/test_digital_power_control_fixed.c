#include "digital_power_control_fixed.h"

#include <limits.h>
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

static DpFixedControlInput nominal_input(void)
{
    DpFixedControlInput in;
    in.enable = true;
    in.clear_fault = false;
    in.vin = 24 * DP_FIXED_ONE;
    in.vout_adc = 0;
    in.iout = 0;
    in.temperature = 45 * DP_FIXED_ONE;
    return in;
}

static void test_format_and_soft_start(void)
{
    DpFixedControlConfig cfg;
    DpFixedControlContext ctx;
    DpFixedControlInput in = nominal_input();
    DpFixedControlOutput out;

    DpFixedControl_DefaultConfig(&cfg);
    DpFixedControl_Init(&ctx, &cfg);

    expect_true("q20_scale_and_soft_start_constant",
                DP_FIXED_FRAC_BITS == 20 &&
                    DP_FIXED_ONE == 1048576 &&
                    cfg.soft_start_step == 1573);

    out = DpFixedControl_Step(&ctx, &cfg, &in);
    expect_true("soft_start_first_step_without_overflow",
                out.state == DP_STATE_SOFT_START &&
                    out.vref_cmd == cfg.soft_start_step &&
                    !out.arithmetic_overflow);
}

static void test_positive_overflow_probe(void)
{
    DpFixedControlConfig cfg;
    DpFixedControlContext ctx;
    DpFixedControlInput in = nominal_input();
    DpFixedControlOutput out;

    DpFixedControl_DefaultConfig(&cfg);
    DpFixedControl_Init(&ctx, &cfg);
    ctx.state = DP_STATE_RUN;
    ctx.vref_cmd = cfg.vref_final;
    ctx.integrator = INT32_MAX;

    out = DpFixedControl_Step(&ctx, &cfg, &in);
    expect_true("positive_overflow_saturates_and_counts",
                out.arithmetic_overflow &&
                    out.arithmetic_overflow_count == 1u &&
                    out.duty_raw == INT32_MAX &&
                    out.duty_cmd == cfg.duty_max);
}

static void test_negative_overflow_probe(void)
{
    DpFixedControlConfig cfg;
    DpFixedControlContext ctx;
    DpFixedControlInput in = nominal_input();
    DpFixedControlOutput out;

    DpFixedControl_DefaultConfig(&cfg);
    DpFixedControl_Init(&ctx, &cfg);
    cfg.vref_final = INT32_MIN;
    cfg.ovp_threshold = INT32_MAX;
    cfg.uvlo_threshold = INT32_MIN;
    cfg.otp_threshold = INT32_MAX;
    ctx.state = DP_STATE_RUN;
    ctx.vref_cmd = cfg.vref_final;
    ctx.integrator = 0;
    in.vout_adc = INT32_MAX - 1;

    out = DpFixedControl_Step(&ctx, &cfg, &in);
    expect_true("negative_overflow_saturates_and_counts",
                out.arithmetic_overflow &&
                    out.arithmetic_overflow_count == 1u &&
                    out.error == INT32_MIN &&
                    out.duty_cmd == cfg.duty_min);
}

int main(void)
{
    test_format_and_soft_start();
    test_positive_overflow_probe();
    test_negative_overflow_probe();

    printf("SUMMARY,%s,failures=%d\n", failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}
