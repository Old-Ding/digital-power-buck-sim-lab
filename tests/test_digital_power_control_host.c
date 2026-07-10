#include "digital_power_control.h"

#include <math.h>
#include <stdio.h>

static int g_failures = 0;

static void expect_true(const char *name, int condition)
{
    if (!condition)
    {
        printf("FAIL,%s\n", name);
        g_failures++;
    }
    else
    {
        printf("PASS,%s\n", name);
    }
}

static void expect_close(const char *name, float actual, float expected, float tolerance)
{
    const float error = fabsf(actual - expected);
    if (error > tolerance)
    {
        printf("FAIL,%s,actual=%g,expected=%g,tolerance=%g\n", name, actual, expected, tolerance);
        g_failures++;
    }
    else
    {
        printf("PASS,%s,actual=%g,expected=%g,tolerance=%g\n", name, actual, expected, tolerance);
    }
}

static DpControlInput nominal_input(void)
{
    DpControlInput in;
    in.enable = true;
    in.clear_fault = false;
    in.vin_v = 24.0f;
    in.vout_adc_v = 12.0f;
    in.iout_a = 5.0f;
    in.temperature_c = 45.0f;
    return in;
}

static void test_default_config(void)
{
    DpControlConfig cfg;
    DpControl_DefaultConfig(&cfg);

    expect_close("default_ts_ctrl", cfg.ts_ctrl_s, 5.0e-6f, 1.0e-9f);
    expect_close("default_vref", cfg.vref_final_v, 12.0f, 1.0e-6f);
    expect_close("default_duty_max", cfg.duty_max, 0.65f, 1.0e-6f);
    expect_close("default_ocp", cfg.ocp_threshold_a, 6.5f, 1.0e-6f);
}

static void test_init_state(void)
{
    DpControlConfig cfg;
    DpControlContext ctx;
    DpControl_DefaultConfig(&cfg);
    DpControl_Init(&ctx, &cfg);

    expect_true("init_state_idle", ctx.state == DP_STATE_IDLE);
    expect_true("init_fault_none", ctx.latched_fault == DP_FAULT_NONE);
    expect_close("init_filter_seed", ctx.vout_filter_v, cfg.vref_final_v, 1.0e-6f);
    expect_close("init_integrator_zero", ctx.integrator, 0.0f, 1.0e-6f);
}

static void test_soft_start_first_step(void)
{
    DpControlConfig cfg;
    DpControlContext ctx;
    DpControlInput in = nominal_input();
    DpControlOutput out;
    DpControl_DefaultConfig(&cfg);
    DpControl_Init(&ctx, &cfg);
    in.vout_adc_v = 0.0f;

    out = DpControl_Step(&ctx, &cfg, &in);

    expect_true("soft_start_state", out.state == DP_STATE_SOFT_START);
    expect_true("soft_start_pwm_enabled", out.pwm_enable);
    expect_close("soft_start_vref_first_step", out.vref_cmd_v, cfg.soft_start_ramp_v_per_s * cfg.ts_ctrl_s, 1.0e-7f);
    expect_true("soft_start_duty_small_positive", out.duty_cmd > 0.0f && out.duty_cmd < 0.001f);
}

static void test_ocp_latch_and_clear_path(void)
{
    DpControlConfig cfg;
    DpControlContext ctx;
    DpControlInput in = nominal_input();
    DpControlOutput out;
    DpControl_DefaultConfig(&cfg);
    DpControl_Init(&ctx, &cfg);

    ctx.state = DP_STATE_RUN;
    ctx.vref_cmd_v = cfg.vref_final_v;
    ctx.integrator = 0.0f;

    in.iout_a = 7.2f;
    out = DpControl_Step(&ctx, &cfg, &in);

    expect_true("ocp_enters_fault", out.state == DP_STATE_FAULT);
    expect_true("ocp_latched", out.latched_fault == DP_FAULT_OCP);
    expect_true("ocp_pwm_disabled", !out.pwm_enable);
    expect_close("ocp_duty_zero", out.duty_cmd, 0.0f, 1.0e-6f);

    in.clear_fault = true;
    out = DpControl_Step(&ctx, &cfg, &in);
    expect_true("ocp_clear_while_fault_stays_latched", out.latched_fault == DP_FAULT_OCP);

    in.iout_a = 5.0f;
    out = DpControl_Step(&ctx, &cfg, &in);
    expect_true("ocp_clear_after_fault_removed", out.latched_fault == DP_FAULT_NONE);
    expect_true("ocp_clear_restarts_soft_start", out.state == DP_STATE_SOFT_START);
}

int main(void)
{
    test_default_config();
    test_init_state();
    test_soft_start_first_step();
    test_ocp_latch_and_clear_path();

    if (g_failures != 0)
    {
        printf("SUMMARY,FAIL,failures=%d\n", g_failures);
        return 1;
    }

    printf("SUMMARY,PASS,failures=0\n");
    return 0;
}
